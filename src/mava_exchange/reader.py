"""
MediaPackageReader — reads a .mediapkg archive.

Usage:

    from mava_exchange.reader import MediaPackageReader

    with MediaPackageReader("corpus.mediapkg") as reader:
        # Inspect the corpus
        print(reader.video_ids)
        print(reader.track_names)

        # Read a specific track into a DataFrame
        df = reader.read_track("video_001", "emotions")

        # Read all tracks for a video
        tracks = reader.read_video("video_001")
        # → {"emotions": df, "transcript": df, ...}
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from .tracks import AnnotationSeries, DimensionSpec, ObservationSeries, Track
from typing import Self


def _track_from_dict(name: str, d: dict) -> Track:
    """Reconstruct a Track object from a manifest dict entry."""
    track_type = d.get("type", "")
    if track_type == "mava:ObservationSeries":
        dims = [
            DimensionSpec(
                name=dim_name,
                description=dim_meta.get("description", ""),
                range=dim_meta.get("range", ""),
            )
            for dim_name, dim_meta in d.get("dimensions", {}).items()
        ]
        return ObservationSeries(
            name=name,
            description=d.get("description", ""),
            dimensions=dims,
            sampling_interval=d.get("sampling_interval_seconds"),
        )
    elif track_type == "mava:AnnotationSeries":
        return AnnotationSeries(
            name=name,
            description=d.get("description", ""),
        )
    else:
        raise ValueError(
            f"Unknown track type '{track_type}' for track '{name}'"
        )


class MediaPackageReader:
    """
    Reads a .mediapkg archive.

    Use as a context manager (recommended):

        with MediaPackageReader("corpus.mediapkg") as reader:
            df = reader.read_track("video_001", "emotions")

    Or open/close manually:

        reader = MediaPackageReader("corpus.mediapkg")
        reader.open()
        df = reader.read_track("video_001", "emotions")
        reader.close()
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._zf:       zipfile.ZipFile | None = None
        self._manifest: dict | None = None

    def open(self) -> MediaPackageReader:
        if not self.path.exists():
            raise FileNotFoundError(f"Package not found: {self.path}")
        if not zipfile.is_zipfile(self.path):
            raise ValueError(f"Not a valid ZIP archive: {self.path}")
        self._zf = zipfile.ZipFile(self.path, "r")
        self._manifest = json.loads(self._zf.read("manifest.json"))
        return self

    def close(self):
        if self._zf:
            self._zf.close()
            self._zf = None

    # ── Manifest accessors ───────────────────────────────────────────

    @property
    def manifest(self) -> dict:
        self._require_open()
        return self._manifest

    @property
    def version(self) -> str:
        return self.manifest["version"]

    @property
    def description(self) -> str:
        return self.manifest.get("description", "")

    @property
    def ontology(self) -> str:
        return self.manifest.get("ontology", "")

    @property
    def video_ids(self) -> list[str]:
        return [v["id"] for v in self.manifest["videos"]]

    @property
    def track_names(self) -> list[str]:
        return list(self.manifest["tracks"].keys())

    def video_meta(self, video_id: str) -> dict:
        """Return the manifest entry for a video (src, title, duration etc.)"""
        video = self._find_video(video_id)
        return {k: v for k, v in video.items() if k != "files"}

    def track_def(self, track_name: str) -> Track:
        """Return the Track object for a named track."""
        tracks = self.manifest["tracks"]
        if track_name not in tracks:
            raise KeyError(
                f"Track '{track_name}' not found. "
                f"Available: {', '.join(tracks.keys())}"
            )
        return _track_from_dict(track_name, tracks[track_name])

    def tracks_for_video(self, video_id: str) -> list[str]:
        """Return track names available for a specific video."""
        return list(self._find_video(video_id)["files"].keys())

    # ── Data reading ─────────────────────────────────────────────────

    def read_track(self, video_id: str, track_name: str) -> pd.DataFrame:
        """
        Read a single track for a video into a DataFrame.

        Columns will match the track definition's column list.
        """
        self._require_open()
        video = self._find_video(video_id)

        if track_name not in video["files"]:
            available = ", ".join(video["files"].keys())
            raise KeyError(
                f"Track '{track_name}' not available for video '{video_id}'. "
                f"Available: {available}"
            )

        path = video["files"][track_name]
        buf = io.BytesIO(self._zf.read(path))
        return pq.read_table(buf).to_pandas()

    def read_video(self, video_id: str) -> dict[str, pd.DataFrame]:
        """
        Read all tracks for a video.

        Returns a dict of track_name → DataFrame.
        """
        return {
            track_name: self.read_track(video_id, track_name)
            for track_name in self.tracks_for_video(video_id)
        }

    # ── File stats (without loading data) ───────────────────────────

    def file_stats(self) -> list[dict]:
        """
        Return size and row count for each Parquet file.
        Does not load row data — reads Parquet metadata only.
        """
        self._require_open()
        stats = []
        for info in self._zf.infolist():
            if info.filename == "manifest.json":
                continue
            buf = io.BytesIO(self._zf.read(info.filename))
            meta = pq.read_metadata(buf)
            stats.append({
                "path":           info.filename,
                "rows":           meta.num_rows,
                "size_bytes":     info.file_size,
                "compressed_bytes": info.compress_size,
            })
        return stats

    # ── Internal helpers ─────────────────────────────────────────────

    def _require_open(self):
        if self._zf is None:
            raise RuntimeError(
                "Reader is not open. Use 'with MediaPackageReader(...) as r:' "
                "or call reader.open() first."
            )

    def _find_video(self, video_id: str) -> dict:
        for video in self.manifest["videos"]:
            if video["id"] == video_id:
                return video
        raise KeyError(
            f"Video '{video_id}' not found. "
            f"Available: {', '.join(self.video_ids)}"
        )

    # ── Context manager ──────────────────────────────────────────────

    def __enter__(self) -> Self:
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
