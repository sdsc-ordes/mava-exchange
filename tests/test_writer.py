"""
Tests for MediaPackageWriter (writer.py).

Checks that the writer produces valid ZIP archives with correct
manifest structure and Parquet files.
"""

import json
import zipfile

import pytest
import pandas as pd

from mava_exchange import (
    MediaPackageWriter,
    ObservationSeries,
    DimensionSpec,
)


class TestWriterBasic:

    def test_writes_zip_file(self, single_video_pkg):
        assert single_video_pkg.exists()
        assert zipfile.is_zipfile(single_video_pkg)

    def test_manifest_present(self, single_video_pkg):
        with zipfile.ZipFile(single_video_pkg) as zf:
            assert "manifest.json" in zf.namelist()

    def test_manifest_version(self, single_video_pkg):
        with zipfile.ZipFile(single_video_pkg) as zf:
            manifest = json.loads(zf.read("manifest.json"))
        assert manifest["version"] == "0.2"

    def test_manifest_has_context(self, single_video_pkg):
        with zipfile.ZipFile(single_video_pkg) as zf:
            manifest = json.loads(zf.read("manifest.json"))
        assert "@context" in manifest["context"]

    def test_parquet_files_present(self, single_video_pkg):
        with zipfile.ZipFile(single_video_pkg) as zf:
            names = zf.namelist()
        assert "v001/emotions.parquet" in names
        assert "v001/transcript.parquet" in names

    def test_manifest_lists_videos(self, single_video_pkg):
        with zipfile.ZipFile(single_video_pkg) as zf:
            manifest = json.loads(zf.read("manifest.json"))
        assert len(manifest["videos"]) == 1
        assert manifest["videos"][0]["id"] == "v001"

    def test_manifest_tracks_defined(self, single_video_pkg):
        with zipfile.ZipFile(single_video_pkg) as zf:
            manifest = json.loads(zf.read("manifest.json"))
        assert "emotions" in manifest["tracks"]
        assert "transcript" in manifest["tracks"]

    def test_description_in_manifest(self, single_video_pkg):
        with zipfile.ZipFile(single_video_pkg) as zf:
            manifest = json.loads(zf.read("manifest.json"))
        assert manifest["description"] == "Single video test"


class TestWriterCorpus:

    def test_two_videos_in_manifest(self, corpus_pkg):
        with zipfile.ZipFile(corpus_pkg) as zf:
            manifest = json.loads(zf.read("manifest.json"))
        assert len(manifest["videos"]) == 2

    def test_video_ids_correct(self, corpus_pkg):
        with zipfile.ZipFile(corpus_pkg) as zf:
            manifest = json.loads(zf.read("manifest.json"))
        ids = [v["id"] for v in manifest["videos"]]
        assert "v001" in ids
        assert "v002" in ids

    def test_different_tracks_per_video(self, corpus_pkg):
        with zipfile.ZipFile(corpus_pkg) as zf:
            manifest = json.loads(zf.read("manifest.json"))
        v001_tracks = set(
            next(v for v in manifest["videos"] if v["id"] == "v001")["files"]
        )
        v002_tracks = set(
            next(v for v in manifest["videos"] if v["id"] == "v002")["files"]
        )
        assert "emotions" in v001_tracks
        assert "emotions" not in v002_tracks
        assert "rms_volume" in v002_tracks
        assert "rms_volume" not in v001_tracks

    def test_shared_track_defined_once(self, corpus_pkg):
        """transcript is used by both videos but defined once in tracks."""
        with zipfile.ZipFile(corpus_pkg) as zf:
            manifest = json.loads(zf.read("manifest.json"))
        # Should appear once in tracks, not duplicated
        assert list(manifest["tracks"].keys()).count("transcript") == 1

    def test_all_parquet_files_present(self, corpus_pkg):
        with zipfile.ZipFile(corpus_pkg) as zf:
            names = set(zf.namelist())
        assert "v001/emotions.parquet"   in names
        assert "v001/transcript.parquet" in names
        assert "v002/rms_volume.parquet" in names
        assert "v002/transcript.parquet" in names


class TestWriterValidation:

    def test_raises_on_unknown_video(self, tmp_path, emotions_track, emotions_df):
        writer = MediaPackageWriter(tmp_path / "x.mediapkg")
        with pytest.raises(ValueError, match="Unknown video"):
            writer.add_track("nonexistent", emotions_track, emotions_df)

    def test_raises_on_missing_columns(self, tmp_path, emotions_track):
        writer = MediaPackageWriter(tmp_path / "x.mediapkg")
        writer.add_video("v001", "https://example.org/v.mp4")
        bad_df = pd.DataFrame({"start_seconds": [0.0], "wrong_col": [1.0]})
        with pytest.raises(ValueError, match="missing columns"):
            writer.add_track("v001", emotions_track, bad_df)

    def test_raises_on_empty_package(self, tmp_path):
        writer = MediaPackageWriter(tmp_path / "x.mediapkg")
        with pytest.raises(ValueError, match="No videos added"):
            writer.write()

    def test_raises_on_duplicate_video(self, tmp_path):
        writer = MediaPackageWriter(tmp_path / "x.mediapkg")
        writer.add_video("v001", "https://example.org/v.mp4")
        with pytest.raises(ValueError, match="already added"):
            writer.add_video("v001", "https://example.org/v.mp4")

    def test_raises_on_inconsistent_track_definition(
        self, tmp_path, emotions_df, rms_df
    ):
        """Same track name with different definitions across videos must fail."""
        track_a = ObservationSeries(
            name="scores",
            description="Version A",
            dimensions=[DimensionSpec("x", "X")]
        )
        track_b = ObservationSeries(
            name="scores",
            description="Version B — different",
            dimensions=[DimensionSpec("x", "X")]
        )
        df = pd.DataFrame({"start_seconds": [0.0], "x": [0.5]})

        writer = MediaPackageWriter(tmp_path / "x.mediapkg")
        writer.add_video("v001", "https://example.org/v1.mp4")
        writer.add_track("v001", track_a, df)
        writer.add_video("v002", "https://example.org/v2.mp4")
        with pytest.raises(ValueError, match="different definition"):
            writer.add_track("v002", track_b, df)

    def test_context_manager_does_not_write_on_exception(self, tmp_path,
                                                          emotions_track,
                                                          emotions_df):
        pkg_path = tmp_path / "x.mediapkg"
        with pytest.raises(RuntimeError):
            with MediaPackageWriter(pkg_path) as w:
                w.add_video("v001", "https://example.org/v.mp4")
                w.add_track("v001", emotions_track, emotions_df)
                raise RuntimeError("something went wrong")
        assert not pkg_path.exists()
