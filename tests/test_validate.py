"""
Tests for the validator (validate.py).

Covers:
- Valid packages (no errors)
- Archive-level errors (missing file, not a zip, no manifest)
- Manifest errors (missing fields, bad track/video definitions)
- Parquet data errors (wrong columns, bad values, ordering)
- Strict mode warnings
- Internal sub-check functions (unit tests)
"""

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from mava_exchange.validate import (
    ValidationResult,
    _check_annotation_series,
    _check_columns,
    _check_observation_series,
    _check_start_seconds,
    validate_mediapkg,
)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────


def _write_parquet_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), buf)
    return buf.getvalue()


def _make_minimal_manifest(extra_tracks=None, extra_videos=None) -> dict:
    """A minimal valid manifest."""
    return {
        "version": "0.1",
        "created": "2025-08-12T10:00:00+00:00",
        "ontology": "http://example.org/mava/ontology#",
        "context": {"@context": {"mava": "http://example.org/mava/ontology#"}},
        "tracks": {
            "emotions": {
                "type": "mava:ObservationSeries",
                "description": "Emotion scores",
                "columns": ["start_seconds", "angry"],
                "dimensions": {"angry": {"description": "Anger", "range": "[0,1]"}},
            },
            **(extra_tracks or {}),
        },
        "videos": [
            {
                "id": "v001",
                "src": "https://example.org/v.mp4",
                "files": {"emotions": "v001/emotions.parquet"},
            },
            *(extra_videos or []),
        ],
    }


def _make_emotions_df(n=5, ordered=True) -> pd.DataFrame:
    t = np.arange(n) * 0.5
    if not ordered:
        t = t[::-1]
    return pd.DataFrame({
        "start_seconds": t,
        "angry": np.linspace(0, 1, n),
    })


def _write_pkg(
    tmp_path: Path,
    manifest: dict,
    parquet_files: dict[str, pd.DataFrame],
    pkg_name: str = "test.mediapkg",
) -> Path:
    pkg_path = tmp_path / pkg_name
    with zipfile.ZipFile(pkg_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        for path, df in parquet_files.items():
            zf.writestr(path, _write_parquet_bytes(df))
    return pkg_path


# ─────────────────────────────────────────────
# Unit tests for internal sub-check functions
# These test the building blocks in isolation.
# ─────────────────────────────────────────────


class TestCheckColumns:

    def test_ok_when_columns_match(self):
        result = ValidationResult()
        _check_columns("f.parquet", {"a", "b"}, {"a", "b"}, result)
        assert result.valid
        assert len(result.warnings) == 0

    def test_error_on_missing_column(self):
        result = ValidationResult()
        _check_columns("f.parquet", {"a"}, {"a", "b"}, result)
        assert not result.valid
        assert any("missing" in e for e in result.errors)

    def test_warning_on_extra_column(self):
        result = ValidationResult()
        _check_columns("f.parquet", {"a", "b", "extra"}, {"a", "b"}, result)
        assert result.valid  # extra columns are warnings, not errors
        assert any("unexpected" in w for w in result.warnings)

    def test_index_column_ignored(self):
        """Pandas index column written by older pyarrow should not warn."""
        result = ValidationResult()
        _check_columns(
            "f.parquet",
            {"a", "b", "__index_level_0__"},
            {"a", "b"},
            result,
        )
        assert result.valid
        assert len(result.warnings) == 0


class TestCheckStartSeconds:

    def test_ok_on_valid_column(self):
        result = ValidationResult()
        df = pd.DataFrame({"start_seconds": [0.0, 0.5, 1.0]})
        _check_start_seconds("f.parquet", df, result)
        assert result.valid

    def test_error_on_missing_column(self):
        result = ValidationResult()
        df = pd.DataFrame({"other": [1, 2]})
        _check_start_seconds("f.parquet", df, result)
        assert not result.valid

    def test_error_on_null_values(self):
        result = ValidationResult()
        df = pd.DataFrame({"start_seconds": [0.0, None, 1.0]})
        _check_start_seconds("f.parquet", df, result)
        assert not result.valid

    def test_error_on_negative_values(self):
        result = ValidationResult()
        df = pd.DataFrame({"start_seconds": [-0.5, 0.0, 0.5]})
        _check_start_seconds("f.parquet", df, result)
        assert not result.valid
        assert any("negative" in e for e in result.errors)

    def test_error_on_unordered_rows(self):
        result = ValidationResult()
        df = pd.DataFrame({"start_seconds": [1.0, 0.5, 0.0]})
        _check_start_seconds("f.parquet", df, result)
        assert not result.valid
        assert any("ordered" in e for e in result.errors)


class TestCheckAnnotationSeries:

    def test_ok_on_valid_interval(self):
        result = ValidationResult()
        df = pd.DataFrame({
            "start_seconds": [0.0, 5.0],
            "end_seconds": [4.9, 10.0],
        })
        _check_annotation_series("f.parquet", df, result)
        assert result.valid

    def test_error_on_missing_end_seconds(self):
        result = ValidationResult()
        df = pd.DataFrame({"start_seconds": [0.0]})
        _check_annotation_series("f.parquet", df, result)
        assert not result.valid

    def test_error_when_end_before_start(self):
        result = ValidationResult()
        df = pd.DataFrame({
            "start_seconds": [5.0],
            "end_seconds": [3.0],
        })
        _check_annotation_series("f.parquet", df, result)
        assert not result.valid
        assert any("end_seconds" in e for e in result.errors)

    def test_error_when_end_equals_start(self):
        result = ValidationResult()
        df = pd.DataFrame({
            "start_seconds": [5.0],
            "end_seconds": [5.0],
        })
        _check_annotation_series("f.parquet", df, result)
        assert not result.valid


class TestCheckObservationSeries:

    def test_ok_on_numeric_dimensions(self):
        result = ValidationResult()
        df = pd.DataFrame({"start_seconds": [0.0], "angry": [0.5]})
        track_def = {"dimensions": {"angry": {}}}
        _check_observation_series("f.parquet", df, track_def, result)
        assert result.valid

    def test_error_on_non_numeric_dimension(self):
        result = ValidationResult()
        df = pd.DataFrame({"start_seconds": [0.0], "angry": ["high"]})
        track_def = {"dimensions": {"angry": {}}}
        _check_observation_series("f.parquet", df, track_def, result)
        assert not result.valid
        assert any("not numeric" in e for e in result.errors)

    def test_warning_on_null_dimension_values(self):
        result = ValidationResult()
        df = pd.DataFrame({"start_seconds": [0.0, 0.5], "angry": [0.5, None]})
        track_def = {"dimensions": {"angry": {}}}
        _check_observation_series("f.parquet", df, track_def, result)
        assert result.valid  # nulls are warnings, not errors
        assert any("null" in w for w in result.warnings)

    def test_skips_dimension_not_in_df(self):
        """Missing dimension column is caught by _check_columns, not here."""
        result = ValidationResult()
        df = pd.DataFrame({"start_seconds": [0.0]})
        track_def = {"dimensions": {"angry": {}}}
        _check_observation_series("f.parquet", df, track_def, result)
        assert result.valid  # silently skipped — already caught upstream


# ─────────────────────────────────────────────
# Integration tests — valid packages
# ─────────────────────────────────────────────


class TestValidPackages:

    def test_single_video_valid(self, single_video_pkg):
        result = validate_mediapkg(single_video_pkg)
        assert result.valid, result.summary()

    def test_corpus_valid(self, corpus_pkg):
        result = validate_mediapkg(corpus_pkg)
        assert result.valid, result.summary()

    def test_zero_errors_on_valid_package(self, single_video_pkg):
        result = validate_mediapkg(single_video_pkg)
        assert len(result.errors) == 0


# ─────────────────────────────────────────────
# Archive-level errors
# ─────────────────────────────────────────────


class TestArchiveErrors:

    def test_missing_file(self, tmp_path):
        result = validate_mediapkg(tmp_path / "nonexistent.mediapkg")
        assert not result.valid
        assert any("not found" in e for e in result.errors)

    def test_not_a_zip(self, tmp_path):
        bad = tmp_path / "bad.mediapkg"
        bad.write_text("this is not a zip file")
        result = validate_mediapkg(bad)
        assert not result.valid

    def test_missing_manifest(self, tmp_path):
        pkg = tmp_path / "no_manifest.mediapkg"
        with zipfile.ZipFile(pkg, "w") as zf:
            zf.writestr("somefile.txt", "hello")
        result = validate_mediapkg(pkg)
        assert not result.valid
        assert any("manifest.json" in e for e in result.errors)


# ─────────────────────────────────────────────
# Manifest errors
# ─────────────────────────────────────────────


class TestManifestErrors:

    def test_missing_version(self, tmp_path):
        manifest = _make_minimal_manifest()
        del manifest["version"]
        pkg = _write_pkg(tmp_path, manifest,
                         {"v001/emotions.parquet": _make_emotions_df()})
        result = validate_mediapkg(pkg)
        assert not result.valid
        assert any("version" in e for e in result.errors)

    def test_missing_tracks(self, tmp_path):
        manifest = _make_minimal_manifest()
        del manifest["tracks"]
        pkg = _write_pkg(tmp_path, manifest,
                         {"v001/emotions.parquet": _make_emotions_df()})
        result = validate_mediapkg(pkg)
        assert not result.valid

    def test_missing_videos(self, tmp_path):
        manifest = _make_minimal_manifest()
        del manifest["videos"]
        pkg = _write_pkg(tmp_path, manifest,
                         {"v001/emotions.parquet": _make_emotions_df()})
        result = validate_mediapkg(pkg)
        assert not result.valid

    def test_empty_videos_array(self, tmp_path):
        manifest = _make_minimal_manifest()
        manifest["videos"] = []
        pkg = _write_pkg(tmp_path, manifest, {})
        result = validate_mediapkg(pkg)
        assert not result.valid

    def test_duplicate_video_ids(self, tmp_path):
        manifest = _make_minimal_manifest()
        manifest["videos"].append({
            "id": "v001",
            "src": "https://example.org/v2.mp4",
            "files": {"emotions": "v001_dup/emotions.parquet"},
        })
        pkg = _write_pkg(tmp_path, manifest,
                         {"v001/emotions.parquet": _make_emotions_df()})
        result = validate_mediapkg(pkg)
        assert not result.valid
        assert any("Duplicate" in e for e in result.errors)

    def test_file_missing_from_archive(self, tmp_path):
        manifest = _make_minimal_manifest()
        pkg = _write_pkg(tmp_path, manifest, {})
        result = validate_mediapkg(pkg)
        assert not result.valid
        assert any("not found in archive" in e for e in result.errors)

    def test_track_referenced_but_not_defined(self, tmp_path):
        manifest = _make_minimal_manifest()
        manifest["videos"][0]["files"]["undefined_track"] = "v001/undefined.parquet"
        df = _make_emotions_df()
        pkg = _write_pkg(tmp_path, manifest, {
            "v001/emotions.parquet": df,
            "v001/undefined.parquet": df,
        })
        result = validate_mediapkg(pkg)
        assert not result.valid

    def test_observation_series_without_dimensions(self, tmp_path):
        manifest = _make_minimal_manifest()
        manifest["tracks"]["emotions"]["dimensions"] = {}
        pkg = _write_pkg(tmp_path, manifest,
                         {"v001/emotions.parquet": _make_emotions_df()})
        result = validate_mediapkg(pkg)
        assert not result.valid
        assert any("dimension" in e for e in result.errors)

    def test_dimension_not_in_columns(self, tmp_path):
        manifest = _make_minimal_manifest()
        manifest["tracks"]["emotions"]["dimensions"]["fear"] = {
            "description": "Fear", "range": "[0,1]",
        }
        pkg = _write_pkg(tmp_path, manifest,
                         {"v001/emotions.parquet": _make_emotions_df()})
        result = validate_mediapkg(pkg)
        assert not result.valid

    def test_unknown_track_type(self, tmp_path):
        manifest = _make_minimal_manifest()
        manifest["tracks"]["emotions"]["type"] = "mava:UnknownType"
        pkg = _write_pkg(tmp_path, manifest,
                         {"v001/emotions.parquet": _make_emotions_df()})
        result = validate_mediapkg(pkg)
        assert not result.valid


# ─────────────────────────────────────────────
# Parquet data errors
# ─────────────────────────────────────────────


class TestParquetErrors:

    def test_missing_start_seconds_column(self, tmp_path):
        manifest = _make_minimal_manifest()
        bad_df = pd.DataFrame({"angry": [0.1, 0.2]})
        pkg = _write_pkg(tmp_path, manifest,
                         {"v001/emotions.parquet": bad_df})
        result = validate_mediapkg(pkg)
        assert not result.valid

    def test_missing_declared_column(self, tmp_path):
        manifest = _make_minimal_manifest()
        bad_df = pd.DataFrame({"start_seconds": [0.0, 0.5]})
        pkg = _write_pkg(tmp_path, manifest,
                         {"v001/emotions.parquet": bad_df})
        result = validate_mediapkg(pkg)
        assert not result.valid

    def test_negative_start_seconds(self, tmp_path):
        manifest = _make_minimal_manifest()
        bad_df = pd.DataFrame({
            "start_seconds": [-1.0, 0.0, 0.5],
            "angry": [0.1, 0.2, 0.3],
        })
        pkg = _write_pkg(tmp_path, manifest,
                         {"v001/emotions.parquet": bad_df})
        result = validate_mediapkg(pkg)
        assert not result.valid
        assert any("negative" in e for e in result.errors)

    def test_unordered_start_seconds(self, tmp_path):
        manifest = _make_minimal_manifest()
        bad_df = _make_emotions_df(ordered=False)
        pkg = _write_pkg(tmp_path, manifest,
                         {"v001/emotions.parquet": bad_df})
        result = validate_mediapkg(pkg)
        assert not result.valid
        assert any("ordered" in e for e in result.errors)

    def test_annotation_series_end_before_start(self, tmp_path):
        manifest = _make_minimal_manifest()
        manifest["tracks"]["shots"] = {
            "type": "mava:AnnotationSeries",
            "description": "Shots",
            "columns": ["start_seconds", "end_seconds", "annotations"],
        }
        manifest["videos"][0]["files"]["shots"] = "v001/shots.parquet"
        bad_df = pd.DataFrame({
            "start_seconds": [5.0, 10.0],
            "end_seconds": [3.0, 15.0],
            "annotations": ["a", "b"],
        })
        pkg = _write_pkg(tmp_path, manifest, {
            "v001/emotions.parquet": _make_emotions_df(),
            "v001/shots.parquet": bad_df,
        })
        result = validate_mediapkg(pkg)
        assert not result.valid
        assert any(
            "end_seconds" in e and "start_seconds" in e
            for e in result.errors
        )

    def test_annotation_series_missing_end_seconds(self, tmp_path):
        manifest = _make_minimal_manifest()
        manifest["tracks"]["shots"] = {
            "type": "mava:AnnotationSeries",
            "description": "Shots",
            "columns": ["start_seconds", "end_seconds", "annotations"],
        }
        manifest["videos"][0]["files"]["shots"] = "v001/shots.parquet"
        bad_df = pd.DataFrame({
            "start_seconds": [0.0],
            "annotations": ["a"],
        })
        pkg = _write_pkg(tmp_path, manifest, {
            "v001/emotions.parquet": _make_emotions_df(),
            "v001/shots.parquet": bad_df,
        })
        result = validate_mediapkg(pkg)
        assert not result.valid

    def test_non_numeric_dimension(self, tmp_path):
        manifest = _make_minimal_manifest()
        bad_df = pd.DataFrame({
            "start_seconds": [0.0, 0.5],
            "angry": ["high", "low"],
        })
        pkg = _write_pkg(tmp_path, manifest,
                         {"v001/emotions.parquet": bad_df})
        result = validate_mediapkg(pkg)
        assert not result.valid
        assert any("not numeric" in e for e in result.errors)


# ─────────────────────────────────────────────
# Strict mode
# ─────────────────────────────────────────────


class TestStrictMode:

    def test_missing_sampling_interval_warns_in_strict(self, tmp_path):
        manifest = _make_minimal_manifest()
        pkg = _write_pkg(tmp_path, manifest,
                         {"v001/emotions.parquet": _make_emotions_df()})
        result = validate_mediapkg(pkg, strict=True)
        assert any("sampling_interval" in w for w in result.warnings)

    def test_missing_sampling_interval_ok_in_normal(self, tmp_path):
        manifest = _make_minimal_manifest()
        pkg = _write_pkg(tmp_path, manifest,
                         {"v001/emotions.parquet": _make_emotions_df()})
        result = validate_mediapkg(pkg, strict=False)
        assert not any("sampling_interval" in w for w in result.warnings)
