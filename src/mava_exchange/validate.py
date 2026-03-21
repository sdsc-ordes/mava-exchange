"""
Validate .mediapkg archives against the MAVA specification.

Checks package structure, manifest completeness, and Parquet data integrity.
See spec/SPEC.md for the full specification.
"""

import io
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import numpy as np
import pyarrow.parquet as pq


KNOWN_VERSIONS = {"0.1"}
KNOWN_TRACK_TYPES = {"mava:ObservationSeries", "mava:AnnotationSeries", "mava:AnnotationListSeries"}


@dataclass
class ValidationResult:
    """
    Result of package validation.

    Collects errors and warnings during validation.

    Attributes
    ----------
    errors : list[str]
        Validation errors (make package invalid)
    warnings : list[str]
        Validation warnings (package still valid)
    checks : int
        Total number of validation checks performed
    valid : bool
        True if no errors found
    """
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: int = 0

    def error(self, msg: str) -> None:
        """Record a validation error."""
        self.errors.append(f"  ✗ {msg}")
        self.checks += 1

    def warning(self, msg: str) -> None:
        """Record a validation warning."""
        self.warnings.append(f"  ⚠ {msg}")
        self.checks += 1

    def ok(self) -> None:
        """Record a passed check."""
        self.checks += 1

    @property
    def valid(self) -> bool:
        """True if no errors were found."""
        return len(self.errors) == 0

    def summary(self) -> str:
        """
        Format validation results as a string.

        Returns
        -------
        str
            Human-readable summary with errors, warnings, and counts

        Example
        -------

            >>> print(result.summary())
            Errors:
               ✗ start_seconds has negative values
               ✗ INVALID  —  42 checks, 1 errors, 0 warnings
        """
        lines = []
        if self.errors:
            lines.append("\nErrors:")
            lines.extend(self.errors)
        if self.warnings:
            lines.append("\nWarnings:")
            lines.extend(self.warnings)
        status = "✓ VALID" if self.valid else "✗ INVALID"
        lines.append(
            f"\n{status}  —  "
            f"{self.checks} checks, "
            f"{len(self.errors)} errors, "
            f"{len(self.warnings)} warnings"
        )
        return "\n".join(lines)


# ─────────────────────────────────────────────
# Manifest checks
# ─────────────────────────────────────────────

def _check_top_level_fields(manifest: dict, result: ValidationResult) -> None:
    """Check required top-level manifest fields are present."""
    for f in ["version", "created", "ontology", "context", "tracks", "videos"]:
        if f not in manifest:
            result.error(f"Missing required field '{f}'")
        else:
            result.ok()

    if manifest.get("version") not in KNOWN_VERSIONS:
        result.warning(f"Unknown version '{manifest.get('version')}'")
    else:
        result.ok()

    if "context" in manifest and "@context" not in manifest["context"]:
        result.error("'context' must contain '@context' key")
    else:
        result.ok()


def _check_observation_series_track(
    track_name: str, track: dict, result: ValidationResult, strict: bool
) -> None:
    """Check ObservationSeries has dimensions matching columns."""
    dims = track.get("dimensions", {})
    if not dims:
        result.error(f"ObservationSeries '{track_name}': must declare at least one dimension")
        return
    result.ok()

    declared_cols = set(track.get("columns", []))
    for dim_name in dims:
        if dim_name not in declared_cols:
            result.error(f"Dimension '{dim_name}' in track '{track_name}' not listed in 'columns'")
        else:
            result.ok()

    if strict and "sampling_interval_seconds" not in track:
        result.warning(f"ObservationSeries '{track_name}': no 'sampling_interval_seconds' declared")


def _check_track(track_name: str, track: dict, result: ValidationResult, strict: bool) -> None:
    """Check a single track definition is valid."""
    if track.get("type") not in KNOWN_TRACK_TYPES:
        result.error(f"Track '{track_name}': unknown type '{track.get('type')}'")
    else:
        result.ok()

    if "columns" not in track:
        result.error(f"Track '{track_name}': missing 'columns'")
    else:
        result.ok()

    if not track.get("description"):
        result.warning(f"Track '{track_name}': missing 'description'")
    else:
        result.ok()

    if track.get("type") == "mava:ObservationSeries":
        _check_observation_series_track(track_name, track, result, strict)


def _check_tracks(manifest: dict, result: ValidationResult, strict: bool) -> None:
    """Check all track definitions in the manifest."""
    for track_name, track in manifest.get("tracks", {}).items():
        _check_track(track_name, track, result, strict)


def _check_video(video: dict, zip_names: set[str], manifest: dict, result: ValidationResult) -> None:
    """Check a single video entry is valid and its files exist."""
    vid = video.get("id", "<unknown>")

    for f in ["id", "src", "files"]:
        if f not in video:
            result.error(f"Video '{vid}': missing required field '{f}'")
        else:
            result.ok()

    for track_name, path in video.get("files", {}).items():
        if path not in zip_names:
            result.error(f"Video '{vid}': file '{path}' not found in archive")
        else:
            result.ok()

        if track_name not in manifest.get("tracks", {}):
            result.error(f"Video '{vid}': track '{track_name}' not defined in manifest 'tracks'")
        else:
            result.ok()


def _check_videos(manifest: dict, zip_names: set[str], result: ValidationResult) -> None:
    """Check videos array is non-empty with unique IDs."""
    videos = manifest.get("videos", [])
    if not videos:
        result.error("'videos' must contain at least one entry")
        return
    result.ok()

    ids = [v.get("id") for v in videos]
    if len(ids) != len(set(ids)):
        result.error("Duplicate video IDs in manifest")
    else:
        result.ok()

    for video in videos:
        _check_video(video, zip_names, manifest, result)


def _validate_manifest(manifest: dict, zip_names: set[str], result: ValidationResult, strict: bool) -> None:
    """Validate manifest structure and contents."""
    print("  Top-level fields...")
    _check_top_level_fields(manifest, result)
    print("  Tracks...")
    _check_tracks(manifest, result, strict)
    print("  Videos...")
    _check_videos(manifest, zip_names, result)


# ─────────────────────────────────────────────
# Parquet checks
# ─────────────────────────────────────────────


def _check_columns(path: str, actual_cols: set[str], declared_cols: set[str], result: ValidationResult) -> None:
    """Check Parquet columns match manifest declaration."""
    missing = declared_cols - actual_cols
    extra = actual_cols - declared_cols - {"__index_level_0__"}
    if missing:
        result.error(f"{path}: missing columns: {', '.join(sorted(missing))}")
    else:
        result.ok()
    if extra:
        result.warning(f"{path}: unexpected columns: {', '.join(sorted(extra))}")


def _check_start_seconds(path: str, df: pd.DataFrame, result: ValidationResult) -> None:
    """Check start_seconds is non-null, non-negative, and sorted."""
    if "start_seconds" not in df.columns:
        result.error(f"{path}: missing required column 'start_seconds'")
        return

    if df["start_seconds"].isna().any():
        result.error(f"{path}: 'start_seconds' has null values")
    else:
        result.ok()

    if (df["start_seconds"] < 0).any():
        result.error(f"{path}: 'start_seconds' has negative values")
    else:
        result.ok()

    if not df["start_seconds"].is_monotonic_increasing:
        result.error(f"{path}: rows not ordered by 'start_seconds'")
    else:
        result.ok()


def _check_annotation_series(path: str, df: pd.DataFrame, result: ValidationResult) -> None:
    """Check AnnotationSeries has valid end_seconds."""
    if "end_seconds" not in df.columns:
        result.error(f"{path}: AnnotationSeries missing 'end_seconds'")
        return
    result.ok()

    if df["end_seconds"].isna().any():
        result.error(f"{path}: 'end_seconds' has null values")
    else:
        result.ok()

    if "start_seconds" in df.columns:
        bad = (df["end_seconds"] <= df["start_seconds"]).sum()
        if bad:
            result.error(f"{path}: {bad} row(s) where end_seconds <= start_seconds")
        else:
            result.ok()


def _check_annotation_list_series(path: str, df: pd.DataFrame, result: ValidationResult) -> None:
    """Check AnnotationListSeries has list-valued annotations."""
    _check_annotation_series(path, df, result)

    if "annotations" not in df.columns:
        result.error(f"{path}: AnnotationListSeries missing 'annotations'")
        return
    result.ok()

    col = df["annotations"]

    for val in col.dropna():
        if not isinstance(val, (list, np.ndarray)):
            result.error(
                f"{path}: 'annotations' column must contain lists, not strings. "
                "Use AnnotationSeries for string-valued annotations."
            )
            return
    result.ok()

    for idx, val in enumerate(col):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            continue
        if not all(isinstance(item, str) for item in val):
            result.error(f"{path}: row {idx} annotations list contains non-string values")
            break
    else:
        result.ok()


def _check_observation_series(path: str, df: pd.DataFrame, track_def: dict, result: ValidationResult) -> None:
    """Check ObservationSeries has numeric dimensions."""
    for dim_name in track_def.get("dimensions", {}):
        if dim_name not in df.columns:
            continue
        col = df[dim_name]
        if not pd.api.types.is_numeric_dtype(col):
            result.error(f"{path}: dimension '{dim_name}' is not numeric (dtype: {col.dtype})")
        else:
            result.ok()

        null_count = col.isna().sum()
        if null_count:
            result.warning(f"{path}: dimension '{dim_name}' has {null_count} null value(s)")
        else:
            result.ok()


def _validate_parquet(zf: zipfile.ZipFile, path: str, track_def: dict, result: ValidationResult) -> None:
    """Validate a Parquet file against its track definition."""
    print(f"  {path}...")

    buf = io.BytesIO(zf.read(path))
    pf = pq.ParquetFile(buf)
    actual_cols = set(pf.schema_arrow.names)
    declared_cols = set(track_def.get("columns", []))
    track_type = track_def.get("type", "")

    _check_columns(path, actual_cols, declared_cols, result)

    df = pf.read().to_pandas()
    if len(df) == 0:
        result.warning(f"{path}: 0 rows")
        return

    _check_start_seconds(path, df, result)

    if track_type == "mava:AnnotationSeries":
        _check_annotation_series(path, df, result)

    if track_type == "mava:AnnotationListSeries":
        _check_annotation_list_series(path, df, result)

    if track_type == "mava:ObservationSeries":
        _check_observation_series(path, df, track_def, result)


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────


def validate_mediapkg(pkg_path: str | Path, strict: bool = False) -> ValidationResult:
    """
    Validate a .mediapkg archive.

    Checks package structure, manifest completeness, and Parquet data integrity
    against the MAVA specification.

    Parameters
    ----------
    pkg_path : str or Path
        Path to the .mediapkg file
    strict : bool, optional
        If True, warn about recommended but optional fields

    Returns
    -------
    ValidationResult
        Validation result with errors, warnings, and summary.
        Check result.valid for pass/fail.

    Example::

        from mava_exchange.validate import validate_mediapkg

        result = validate_mediapkg("corpus.mediapkg")

        if result.valid:
            print(f"✓ Package is valid ({result.checks} checks passed)")
        else:
            print(result.summary())
            # Shows errors and exit with error code
    """
    result = ValidationResult()

    print(f"\n{'═' * 60}")
    print(f"  Validating: {pkg_path}")
    print("═" * 60)

    pkg_path = Path(pkg_path)

    if not pkg_path.exists():
        result.error(f"File not found: {pkg_path}")
        return result

    if not zipfile.is_zipfile(pkg_path):
        result.error(f"Not a valid ZIP archive: {pkg_path}")
        return result

    with zipfile.ZipFile(pkg_path, "r") as zf:
        zip_names = set(zf.namelist())

        if "manifest.json" not in zip_names:
            result.error("manifest.json not found at root of archive")
            return result
        result.ok()

        manifest = json.loads(zf.read("manifest.json"))

        print("\nManifest:")
        _validate_manifest(manifest, zip_names, result, strict)

        print("\nParquet files:")
        seen: set[str] = set()
        for video in manifest.get("videos", []):
            for track_name, path in video.get("files", {}).items():
                if path in seen or path not in zip_names:
                    continue
                seen.add(path)
                track_def = manifest.get("tracks", {}).get(track_name, {})
                _validate_parquet(zf, path, track_def, result)

    return result
