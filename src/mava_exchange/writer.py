"""
Writer for creating .mediapkg archives.

This module provides the MediaPackageWriter class for building .mediapkg files
incrementally by adding videos and their annotation tracks.
"""
from __future__ import annotations

from typing import Self

import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .tracks import Track

MAVA        = "http://example.org/mava/ontology#"
FORMAT_VERSION = "0.2"

JSONLD_CONTEXT = {
    "@context": {
        "xsd":  "http://www.w3.org/2001/XMLSchema#",
        "mava": MAVA,
        "start_seconds": {"@id": "mava:atTime",       "@type": "xsd:decimal"},
        "end_seconds":   {"@id": "mava:endTime",      "@type": "xsd:decimal"},
        "annotations":   {"@id": "mava:stringValue",  "@type": "xsd:string"},
        "numericValue":  {"@id": "mava:numericValue",  "@type": "xsd:decimal"},
        # RegionSeries geometry / score (mapped to dedicated ontology terms)
        "x":          {"@id": "mava:x",              "@type": "xsd:decimal"},
        "y":          {"@id": "mava:y",              "@type": "xsd:decimal"},
        "w":          {"@id": "mava:width",          "@type": "xsd:decimal"},
        "h":          {"@id": "mava:height",         "@type": "xsd:decimal"},
        "det_score":  {"@id": "mava:detectionScore", "@type": "xsd:decimal"},
        # RegionSeries identity columns
        "cluster_id": {"@id": "mava:clusterId",      "@type": "xsd:integer"},
        "label":      {"@id": "mava:identityLabel",  "@type": "xsd:string"},
    }
}


class MediaPackageWriter:
    """
    Write a .mediapkg archive incrementally.

    Use as a context manager (recommended) or call .write() manually.

    Example
    -------
    ::

        with MediaPackageWriter("out.mediapkg") as w:
            w.add_video("v1", "https://example.org/v1.mp4")
            w.add_track("v1", my_track, my_df)

    Multiple videos can be added before writing:

    ::

        writer = MediaPackageWriter("corpus.mediapkg")
        for video_id, src, tracks_and_dfs in my_videos:
            writer.add_video(video_id, src)
            for track, df in tracks_and_dfs:
                writer.add_track(video_id, track, df)
        writer.write()
    """

    def __init__(
        self,
        path:        str | Path,
        description: str = "",
        created:     datetime | None = None,
    ):
        """
        Initialize writer.

        Parameters
        ----------
        path : str or Path
            Output path for .mediapkg file
        description : str, optional
            Human-readable description of the corpus
        created : datetime, optional
            Creation timestamp recorded in the manifest. When omitted, the
            current UTC time is used at write time. Pass a fixed value to
            produce a byte-reproducible archive — it also fixes the ZIP entry
            timestamps.
        Examples
        ________
            >>> with MediaPackageWriter("output.mediapkg") as w:
                    # ... add videos and tracks
                    # ... and write them at the end of the block ...
        """
        self.path        = Path(path)
        self.description = description
        self.created     = created
        self._videos: dict[str, dict] = {}     # video_id → {src, title, duration}
        self._tracks: dict[str, Track] = {}    # track_name → Track
        self._data:   dict[str, dict[str, pd.DataFrame]] = {} # video_id → {track_name → DataFrame}

    def add_video(  # noqa: PLR0913
        self,
        video_id:         str,
        src:              str,
        title:            str | None = None,
        duration_seconds: float | None = None,
        width:            int | None = None,
        height:           int | None = None,
        fps:              float | None = None,
    ) -> "MediaPackageWriter":
        """
        Register a video. Must be called before add_track for this video.

        Parameters
        ----------
        video_id : str
            Unique identifier for this video
        src : str
            URI or path to the video file
        title : str, optional
            Human-readable title
        duration_seconds : float, optional
            Video duration in seconds

        Returns
        -------
        MediaPackageWriter
            Self for method chaining

        Raises
        ------
        ValueError
            If video_id already exists

        Examples
        ________
            >>> with MediaPackageWriter("output.mediapkg", "A sample media corpus") as w:
                    w.add_video("video_001", "https://example.org/video.mp4")
        """
        if video_id in self._videos:
            raise ValueError(f"Video '{video_id}' already added")
        self._videos[video_id] = {
            "id":  video_id,
            "src": src,
            **({"title": title} if title else {}),
            **({"width": width} if width is not None else {}),
            **({"height": height} if height is not None else {}),
            **({"fps": fps} if fps is not None else {}),
            **({"duration_seconds": duration_seconds} if duration_seconds else {}),
        }
        self._data[video_id] = {}
        return self

    def add_track(
        self,
        video_id: str,
        track:    Track,
        df:       pd.DataFrame,
    ) -> "MediaPackageWriter":
        """
        Add a DataFrame as a track for a video.

        The DataFrame must contain the columns declared by the track.
        If the same track name is used across multiple videos, the track
        definition must be identical (checked automatically).

        Parameters
        ----------
        video_id : str
            Video identifier (must be added first with add_video)
        track : Track
            Track definition (ObservationSeries, AnnotationSeries, or AnnotationListSeries)
        df : pd.DataFrame
            Data with columns matching track.columns

        Returns
        -------
        MediaPackageWriter
            Self for method chaining

        Raises
        ------
        ValueError
            If video_id not found, track definition conflicts, or columns missing

        Examples
        ________
            >>> with MediaPackageWriter("output.mediapkg") as w:
                    w.add_track("video_001", emotions, emotions_df)
        """
        if video_id not in self._videos:
            raise ValueError(
                f"Unknown video '{video_id}'. Call add_video() first."
            )

        # If this track name was already registered by another video,
        # check that the definition is consistent
        if track.name in self._tracks:
            existing = self._tracks[track.name]
            if existing.to_dict() != track.to_dict():
                raise ValueError(
                    f"Track '{track.name}' was already added with a different "
                    f"definition. Track definitions must be consistent across videos."
                )
        else:
            self._tracks[track.name] = track

        # Basic column check before accepting the data
        missing = set(track.columns) - set(df.columns)
        if missing:
            raise ValueError(
                f"DataFrame for track '{track.name}' is missing columns: "
                f"{', '.join(sorted(missing))}"
            )

        self._data[video_id][track.name] = df[track.columns]
        return self

    def _build_manifest(
        self,
        files_map: dict[str, dict[str, str]],
        created:   datetime,
    ) -> dict:
        return {
            "version":     FORMAT_VERSION,
            "created":     created.isoformat(),
            "description": self.description,
            "ontology":    MAVA,
            "context":     JSONLD_CONTEXT,
            "tracks":      {
                name: track.to_dict()
                for name, track in self._tracks.items()
            },
            "videos":      [
                {
                    **video_meta,
                    "files": files_map[video_id],
                }
                for video_id, video_meta in self._videos.items()
            ],
        }

    def write(self):
        """
        Write the .mediapkg archive to disk.

        Raises
        ------
        ValueError
            If no videos have been added

        Examples
        ________
            >>> with MediaPackageWriter("output.mediapkg") as w:
                    # ... add videos and tracks ...
                    w.write()
        """
        if not self._videos:
            raise ValueError("No videos added — nothing to write.")

        created = self.created or datetime.now(timezone.utc)
        # ZIP date_time supports only years >= 1980; created is always later.
        zip_date_time = created.timetuple()[:6]

        def _writestr(zf: zipfile.ZipFile, name: str, data: bytes | str) -> None:
            # Use an explicit ZipInfo so the entry timestamp is deterministic
            # (driven by `created`) rather than the wall clock at write time.
            info = zipfile.ZipInfo(name, date_time=zip_date_time)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, data)

        files_map: dict[str, dict[str, str]] = {}

        with zipfile.ZipFile(
            self.path, "w", compression=zipfile.ZIP_DEFLATED
        ) as zf:

            for video_id, tracks in self._data.items():
                files_map[video_id] = {}
                for track_name, df in tracks.items():
                    entry = f"{video_id}/{track_name}.parquet"
                    _writestr(zf, entry, _df_to_parquet_bytes(df))
                    files_map[video_id][track_name] = entry

            manifest = self._build_manifest(files_map, created)
            _writestr(zf, "manifest.json", json.dumps(manifest, indent=2))

    # Context manager support
    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.write()
        return False


def _df_to_parquet_bytes(df: pd.DataFrame) -> bytes:
    table = pa.Table.from_pandas(df, preserve_index=False)
    buf = io.BytesIO()
    pq.write_table(table, buf)
    return buf.getvalue()
