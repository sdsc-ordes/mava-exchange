"""
Tests for MediaPackageReader (reader.py).

Checks that the reader correctly reconstructs manifest metadata,
track definitions, and DataFrames from a written .mediapkg.
"""

import pytest
import rdflib
import pandas as pd

from mava_exchange import MediaPackageReader, ObservationSeries, AnnotationSeries


class TestReaderManifest:

    def test_version(self, single_video_pkg):
        with MediaPackageReader(single_video_pkg) as r:
            assert r.version == "0.1"

    def test_description(self, single_video_pkg):
        with MediaPackageReader(single_video_pkg) as r:
            assert r.description == "Single video test"

    def test_video_ids(self, single_video_pkg):
        with MediaPackageReader(single_video_pkg) as r:
            assert r.video_ids == ["v001"]

    def test_track_names(self, single_video_pkg):
        with MediaPackageReader(single_video_pkg) as r:
            assert set(r.track_names) == {"emotions", "transcript"}

    def test_corpus_video_ids(self, corpus_pkg):
        with MediaPackageReader(corpus_pkg) as r:
            assert set(r.video_ids) == {"v001", "v002"}

    def test_tracks_for_video(self, corpus_pkg):
        with MediaPackageReader(corpus_pkg) as r:
            assert set(r.tracks_for_video("v001")) == {"emotions", "transcript"}
            assert set(r.tracks_for_video("v002")) == {"rms_volume", "transcript"}

    def test_video_meta_contains_src(self, single_video_pkg):
        with MediaPackageReader(single_video_pkg) as r:
            meta = r.video_meta("v001")
        assert meta["src"] == "https://example.org/v001.mp4"

    def test_video_meta_excludes_files(self, single_video_pkg):
        """files is internal — not part of the video metadata."""
        with MediaPackageReader(single_video_pkg) as r:
            meta = r.video_meta("v001")
        assert "files" not in meta


class TestReaderTrackDefs:

    def test_observation_series_reconstructed(self, single_video_pkg):
        with MediaPackageReader(single_video_pkg) as r:
            track = r.track_def("emotions")
        assert isinstance(track, ObservationSeries)
        assert track.name == "emotions"
        assert track.sampling_interval == 0.5

    def test_observation_series_dimensions(self, single_video_pkg):
        with MediaPackageReader(single_video_pkg) as r:
            track = r.track_def("emotions")
        dim_names = [d.name for d in track.dimensions]
        assert "angry" in dim_names
        assert "neutral" in dim_names

    def test_annotation_series_reconstructed(self, single_video_pkg):
        with MediaPackageReader(single_video_pkg) as r:
            track = r.track_def("transcript")
        assert isinstance(track, AnnotationSeries)
        assert track.name == "transcript"

    def test_unknown_track_raises(self, single_video_pkg):
        with MediaPackageReader(single_video_pkg) as r:
            with pytest.raises(KeyError, match="nonexistent"):
                r.track_def("nonexistent")


class TestReaderData:

    def test_read_track_returns_dataframe(self, single_video_pkg):
        with MediaPackageReader(single_video_pkg) as r:
            df = r.read_track("v001", "emotions")
        assert isinstance(df, pd.DataFrame)

    def test_read_track_has_correct_columns(self, single_video_pkg):
        with MediaPackageReader(single_video_pkg) as r:
            df = r.read_track("v001", "emotions")
        assert "start_seconds" in df.columns
        assert "angry" in df.columns
        assert "neutral" in df.columns

    def test_read_track_row_count(self, single_video_pkg, emotions_df):
        with MediaPackageReader(single_video_pkg) as r:
            df = r.read_track("v001", "emotions")
        assert len(df) == len(emotions_df)

    def test_read_track_values_roundtrip(self, single_video_pkg, emotions_df):
        """Values written must equal values read back."""
        with MediaPackageReader(single_video_pkg) as r:
            df = r.read_track("v001", "emotions")
        pd.testing.assert_series_equal(
            df["start_seconds"].reset_index(drop=True),
            emotions_df["start_seconds"].reset_index(drop=True),
            check_names=False,
        )

    def test_read_annotation_series(self, single_video_pkg, transcript_df):
        with MediaPackageReader(single_video_pkg) as r:
            df = r.read_track("v001", "transcript")
        assert "start_seconds" in df.columns
        assert "end_seconds" in df.columns
        assert "annotations" in df.columns
        assert len(df) == len(transcript_df)

    def test_read_video_returns_all_tracks(self, single_video_pkg):
        with MediaPackageReader(single_video_pkg) as r:
            tracks = r.read_video("v001")
        assert set(tracks.keys()) == {"emotions", "transcript"}
        assert all(isinstance(df, pd.DataFrame) for df in tracks.values())

    def test_read_unknown_video_raises(self, single_video_pkg):
        with MediaPackageReader(single_video_pkg) as r:
            with pytest.raises(KeyError, match="nonexistent"):
                r.read_track("nonexistent", "emotions")

    def test_read_unknown_track_raises(self, single_video_pkg):
        with MediaPackageReader(single_video_pkg) as r:
            with pytest.raises(KeyError, match="nonexistent"):
                r.read_track("v001", "nonexistent")

    def test_file_stats_row_counts(self, single_video_pkg, emotions_df,
                                   transcript_df):
        with MediaPackageReader(single_video_pkg) as r:
            stats = r.file_stats()
        rows_by_path = {s["path"]: s["rows"] for s in stats}
        assert rows_by_path["v001/emotions.parquet"]   == len(emotions_df)
        assert rows_by_path["v001/transcript.parquet"] == len(transcript_df)


class TestReaderErrors:

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            with MediaPackageReader(tmp_path / "nonexistent.mediapkg"):
                pass

    def test_requires_open_before_access(self, single_video_pkg):
        r = MediaPackageReader(single_video_pkg)
        with pytest.raises(RuntimeError, match="not open"):
            _ = r.video_ids

    def test_context_manager_closes_on_exit(self, single_video_pkg):
        with MediaPackageReader(single_video_pkg) as r:
            pass
        with pytest.raises(RuntimeError, match="not open"):
            _ = r.video_ids


class TestReaderRDFExport:
    """Tests for export_manifest_as_rdf method."""

    def test_export_turtle_produces_string(self, single_video_pkg):
        """Turtle export returns a non-empty string."""
        with MediaPackageReader(single_video_pkg) as r:
            ttl = r.export_manifest_as_rdf(format="turtle")
        assert isinstance(ttl, str)
        assert len(ttl) > 100
        assert "@prefix mava:" in ttl

    def test_export_jsonld_produces_string(self, single_video_pkg):
        """JSON-LD export returns a non-empty string."""
        with MediaPackageReader(single_video_pkg) as r:
            jsonld = r.export_manifest_as_rdf(format="json-ld")
            print(jsonld)  # for debugging
        assert isinstance(jsonld, str)
        assert len(jsonld) > 100
        assert "@id" in jsonld

    def test_export_turtle_contains_package(self, single_video_pkg):
        """Turtle export contains MediaPackage triple."""
        with MediaPackageReader(single_video_pkg) as r:
            ttl = r.export_manifest_as_rdf(format="turtle")
        assert "mava:MediaPackage" in ttl

    def test_export_turtle_contains_video(self, single_video_pkg):
        """Turtle export contains Video triple."""
        with MediaPackageReader(single_video_pkg) as r:
            ttl = r.export_manifest_as_rdf(format="turtle")
        assert "mava:Video" in ttl
        assert "v001" in ttl

    def test_export_turtle_contains_observation_series(self, single_video_pkg):
        """Turtle export contains ObservationSeries for emotions track."""
        with MediaPackageReader(single_video_pkg) as r:
            ttl = r.export_manifest_as_rdf(format="turtle")
        assert "mava:ObservationSeries" in ttl
        assert "emotions" in ttl or "emotion" in ttl

    def test_export_turtle_contains_annotation_series(self, single_video_pkg):
        """Turtle export contains AnnotationSeries for transcript track."""
        with MediaPackageReader(single_video_pkg) as r:
            ttl = r.export_manifest_as_rdf(format="turtle")
        assert "mava:AnnotationSeries" in ttl
        assert "transcript" in ttl

    def test_export_turtle_contains_dimensions(self, single_video_pkg):
        """Turtle export contains Dimension triples."""
        with MediaPackageReader(single_video_pkg) as r:
            ttl = r.export_manifest_as_rdf(format="turtle")
        assert "mava:Dimension" in ttl
        assert "angry" in ttl
        assert "neutral" in ttl

    def test_export_turtle_parseable_by_rdflib(self, single_video_pkg):
        """Turtle export is valid and parseable."""
        with MediaPackageReader(single_video_pkg) as r:
            ttl = r.export_manifest_as_rdf(format="turtle")
        # Parse it to verify validity
        g = rdflib.Graph()
        g.parse(data=ttl, format="turtle")
        assert len(g) > 10  # should have multiple triples

    def test_export_unknown_format_raises(self, single_video_pkg):
        """Unknown format raises ValueError."""
        with MediaPackageReader(single_video_pkg) as r:
            with pytest.raises(ValueError, match="Unknown format"):
                r.export_manifest_as_rdf(format="xml")

    def test_export_custom_base_uri(self, single_video_pkg):
        """Custom base URI is used in output."""
        with MediaPackageReader(single_video_pkg) as r:
            ttl = r.export_manifest_as_rdf(
                format="turtle",
                base_uri="http://myproject.org/"
            )
        assert "myproject.org" in ttl
