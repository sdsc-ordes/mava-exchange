"""Reader for loading .mediapkg archives."""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import pyarrow.parquet as pq
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, DCTERMS, XSD

from .tracks import AnnotationSeries, DimensionSpec, ObservationSeries, Track, AnnotationListSeries

if TYPE_CHECKING:
    from typing import Self


def _track_from_dict(name: str, d: dict) -> Track:
    """Reconstruct Track object from manifest dict."""
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
    elif track_type == "mava:AnnotationListSeries":
        return AnnotationListSeries(
            name=name,
            description=d.get("description", ""),
        )
    else:
        raise ValueError(f"Unknown track type '{track_type}' for track '{name}'")


class MediaPackageReader:
    """
    Read .mediapkg archive files.

    Use as a context manager or call open()/close() manually.

    Example::

        with MediaPackageReader("corpus.mediapkg") as r:
            print(r.video_ids)
            print(r.track_names)
            df = r.read_track("v001", "emotions")
    """

    def __init__(self, path: str | Path):
        """
        Initialize reader.

        Parameters
        ----------
        path : str or Path
            Path to .mediapkg file
        """
        self.path = Path(path)
        self._zf: zipfile.ZipFile | None = None
        self._manifest: dict | None = None

    def open(self) -> Self:
        """Open the package for reading."""
        if not self.path.exists():
            raise FileNotFoundError(f"Package not found: {self.path}")
        if not zipfile.is_zipfile(self.path):
            raise ValueError(f"Not a valid ZIP archive: {self.path}")
        self._zf = zipfile.ZipFile(self.path, "r")
        self._manifest = json.loads(self._zf.read("manifest.json"))
        return self

    def close(self):
        """Close the package file."""
        if self._zf:
            self._zf.close()
            self._zf = None

    @property
    def manifest(self) -> dict:
        """The parsed manifest.json dictionary."""
        self._require_open()
        assert self._manifest is not None
        return self._manifest

    @property
    def version(self) -> str:
        """Format version from manifest."""
        return self.manifest["version"]

    @property
    def description(self) -> str:
        """Package description."""
        return self.manifest.get("description", "")

    @property
    def ontology(self) -> str:
        """Ontology URI."""
        return self.manifest.get("ontology", "")

    @property
    def video_ids(self) -> list[str]:
        """List of video IDs in the package."""
        return [v["id"] for v in self.manifest["videos"]]

    @property
    def track_names(self) -> list[str]:
        """List of all track names across all videos."""
        return list(self.manifest["tracks"].keys())

    def video_meta(self, video_id: str) -> dict:
        """
        Get video metadata.

        Returns src, title, duration etc. (excludes file paths).
        """
        video = self._find_video(video_id)
        return {k: v for k, v in video.items() if k != "files"}

    def track_def(self, track_name: str) -> Track:
        """
        Get track definition object.

        Returns
        -------
        Track
            ObservationSeries, AnnotationSeries, or AnnotationListSeries
        """
        tracks = self.manifest["tracks"]
        if track_name not in tracks:
            raise KeyError(
                f"Track '{track_name}' not found. "
                f"Available: {', '.join(tracks.keys())}"
            )
        return _track_from_dict(track_name, tracks[track_name])

    def tracks_for_video(self, video_id: str) -> list[str]:
        """List track names available for a video."""
        return list(self._find_video(video_id)["files"].keys())

    def read_track(self, video_id: str, track_name: str) -> pd.DataFrame:
        """
        Read a track's data into a DataFrame.

        Parameters
        ----------
        video_id : str
            Video identifier
        track_name : str
            Track name

        Returns
        -------
        pd.DataFrame
            Track data with columns matching the track definition
        """
        self._require_open()
        assert self._zf is not None
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

        Returns
        -------
        dict[str, pd.DataFrame]
            Mapping of track_name → DataFrame
        """
        return {
            track_name: self.read_track(video_id, track_name)
            for track_name in self.tracks_for_video(video_id)
        }

    def file_stats(self) -> list[dict]:
        """
        Get size and row count for each Parquet file.

        Reads metadata only, does not load data.

        Returns
        -------
        list[dict]
            List of {path, rows, size_bytes, compressed_bytes}
        """
        self._require_open()
        assert self._zf is not None
        stats = []
        for info in self._zf.infolist():
            if info.filename == "manifest.json":
                continue
            buf = io.BytesIO(self._zf.read(info.filename))
            meta = pq.read_metadata(buf)
            stats.append({
                "path": info.filename,
                "rows": meta.num_rows,
                "size_bytes": info.file_size,
                "compressed_bytes": info.compress_size,
            })
        return stats

    def export_manifest_as_rdf(  # noqa: PLR0912
        self, format: str = "turtle", base_uri: str = "http://example.org/data/"
    ) -> str:
        """
        Export manifest as RDF.

        Exports package structure only, not row data.

        Parameters
        ----------
        format : str
            "turtle" or "json-ld"
        base_uri : str
            Base URI for generated identifiers

        Returns
        -------
        str
            RDF serialization
        """
        self._require_open()

        # Namespaces
        MAVA = Namespace(self.manifest.get("ontology", "http://example.org/mava/ontology#"))
        EX = Namespace(base_uri)

        g = Graph()
        g.bind("mava", MAVA)
        g.bind("dcterms", DCTERMS)
        g.bind("xsd", XSD)
        g.bind("ex", EX)

        # Package
        pkg_uri = EX["package"]
        g.add((pkg_uri, RDF.type, MAVA.MediaPackage))
        if self.description:
            g.add((pkg_uri, DCTERMS.description, Literal(self.description)))
        if "created" in self.manifest:
            g.add((pkg_uri, DCTERMS.created,
                   Literal(self.manifest["created"], datatype=XSD.dateTime)))

        # Videos
        for video in self.manifest["videos"]:
            video_uri = EX[f"video_{video['id']}"]
            g.add((pkg_uri, MAVA.hasVideo, video_uri))
            g.add((video_uri, RDF.type, MAVA.Video))

            if "src" in video:
                g.add((video_uri, DCTERMS.source, URIRef(video["src"])))

            for track_name in video.get("files", {}).keys():
                series_uri = EX[f"series_{track_name}"]
                g.add((video_uri, MAVA.hasAnalysis, series_uri))

        # Tracks
        for track_name, track_def in self.manifest["tracks"].items():
            series_uri = EX[f"series_{track_name}"]
            track_type = track_def.get("type")

            if track_type == "mava:ObservationSeries":
                g.add((series_uri, RDF.type, MAVA.ObservationSeries))

                if "sampling_interval_seconds" in track_def:
                    g.add((series_uri, MAVA.samplingInterval,
                           Literal(track_def["sampling_interval_seconds"], datatype=XSD.decimal)))

                for dim_name, dim_meta in track_def.get("dimensions", {}).items():
                    dim_uri = EX[f"dim_{track_name}_{dim_name}"]
                    g.add((series_uri, MAVA.hasDimension, dim_uri))
                    g.add((dim_uri, RDF.type, MAVA.Dimension))
                    g.add((dim_uri, MAVA.dimensionName, Literal(dim_name)))

                    if "description" in dim_meta:
                        g.add((dim_uri, MAVA.dimensionDescription,
                               Literal(dim_meta["description"])))
                    if "range" in dim_meta:
                        g.add((dim_uri, MAVA.valueRange, Literal(dim_meta["range"])))

            elif track_type == "mava:AnnotationSeries":
                g.add((series_uri, RDF.type, MAVA.AnnotationSeries))

            elif track_type == "mava:AnnotationListSeries":
                g.add((series_uri, RDF.type, MAVA.AnnotationListSeries))

            if "description" in track_def:
                g.add((series_uri, MAVA.seriesDescription,
                       Literal(track_def["description"])))

        # Serialize
        if format == "turtle":
            return g.serialize(format="turtle")
        elif format == "json-ld":
            return g.serialize(format="json-ld", indent=2)
        else:
            raise ValueError(f"Unknown format '{format}'. Use 'turtle' or 'json-ld'.")

    def _require_open(self):
        """Check that package is open."""
        if self._zf is None:
            raise RuntimeError(
                "Reader is not open. Use 'with MediaPackageReader(...) as r:' "
                "or call reader.open() first."
            )

    def _find_video(self, video_id: str) -> dict:
        """Find video in manifest by ID."""
        for video in self.manifest["videos"]:
            if video["id"] == video_id:
                return video
        raise KeyError(
            f"Video '{video_id}' not found. "
            f"Available: {', '.join(self.video_ids)}"
        )

    def __enter__(self) -> Self:
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
