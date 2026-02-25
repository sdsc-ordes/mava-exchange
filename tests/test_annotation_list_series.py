"""
Tests for AnnotationListSeries track type.

Tests the new multi-label annotation format with Parquet LIST columns.
"""

import pytest
import pandas as pd
import numpy as np

from mava_exchange import (
    AnnotationListSeries,
    MediaPackageWriter,
    MediaPackageReader,
)
from mava_exchange.validate import validate_mediapkg


class TestAnnotationListSeriesDefinition:
    """Tests for AnnotationListSeries track definition."""

    def test_type_is_correct(self, scene_tags_track):
        assert scene_tags_track.type == "mava:AnnotationListSeries"

    def test_columns_are_standard(self, scene_tags_track):
        assert scene_tags_track.columns == ["start_seconds", "end_seconds", "annotations"]

    def test_to_dict_structure(self, scene_tags_track):
        d = scene_tags_track.to_dict()
        assert d["type"] == "mava:AnnotationListSeries"
        assert d["description"] == "Scene classification tags from Places3"
        assert d["columns"] == ["start_seconds", "end_seconds", "annotations"]
        assert "dimensions" not in d  # List series don't have dimensions


class TestAnnotationListSeriesWriteRead:
    """Test writing and reading AnnotationListSeries."""

    def test_write_and_read_back(self, tmp_path, scene_tags_track, scene_tags_df):
        """Write list annotations and read them back as lists."""
        pkg = tmp_path / "test.mediapkg"

        with MediaPackageWriter(pkg, description="Test") as w:
            w.add_video("v001", "https://example.org/v.mp4")
            w.add_track("v001", scene_tags_track, scene_tags_df)

        with MediaPackageReader(pkg) as r:
            df = r.read_track("v001", "scene_tags")

        # Check data is preserved
        assert len(df) == 3
        assert list(df["start_seconds"]) == [0.0, 45.2, 78.5]

        # Check annotations are lists (PyArrow returns numpy arrays)
        assert isinstance(df.loc[0, "annotations"], np.ndarray) or isinstance(df.loc[0, "annotations"], list)
        assert list(df.loc[0, "annotations"]) == ["outdoor", "natural"]
        assert list(df.loc[1, "annotations"]) == ["indoor"]
        assert list(df.loc[2, "annotations"]) == ["outdoor", "man-made"]

    def test_track_def_roundtrip(self, tmp_path, scene_tags_track, scene_tags_df):
        """Track definition survives write/read cycle."""
        pkg = tmp_path / "test.mediapkg"

        with MediaPackageWriter(pkg, description="Test") as w:
            w.add_video("v001", "https://example.org/v.mp4")
            w.add_track("v001", scene_tags_track, scene_tags_df)

        with MediaPackageReader(pkg) as r:
            track = r.track_def("scene_tags")

        assert isinstance(track, AnnotationListSeries)
        assert track.name == "scene_tags"
        assert track.type == "mava:AnnotationListSeries"
        assert track.description == "Scene classification tags from Places3"

    def test_empty_lists_allowed(self, tmp_path, scene_tags_track):
        """Empty lists in annotations column are valid."""
        df = pd.DataFrame({
            "start_seconds": [0.0, 10.0],
            "end_seconds": [10.0, 20.0],
            "annotations": [["outdoor"], []],  # Second row has empty list
        })

        pkg = tmp_path / "test.mediapkg"

        with MediaPackageWriter(pkg, description="Test") as w:
            w.add_video("v001", "https://example.org/v.mp4")
            w.add_track("v001", scene_tags_track, df)

        with MediaPackageReader(pkg) as r:
            result = r.read_track("v001", "scene_tags")

        # Empty lists come back as empty arrays
        assert len(result.loc[1, "annotations"]) == 0

    def test_single_item_lists(self, tmp_path, scene_tags_track):
        """Single-item lists work correctly."""
        df = pd.DataFrame({
            "start_seconds": [0.0],
            "end_seconds": [10.0],
            "annotations": [["indoor"]],  # List with one item
        })

        pkg = tmp_path / "test.mediapkg"

        with MediaPackageWriter(pkg, description="Test") as w:
            w.add_video("v001", "https://example.org/v.mp4")
            w.add_track("v001", scene_tags_track, df)

        with MediaPackageReader(pkg) as r:
            result = r.read_track("v001", "scene_tags")

        assert list(result.loc[0, "annotations"]) == ["indoor"]
        assert isinstance(result.loc[0, "annotations"], (list, np.ndarray))

    def test_many_labels_per_segment(self, tmp_path, scene_tags_track):
        """Segments can have many labels."""
        df = pd.DataFrame({
            "start_seconds": [0.0],
            "end_seconds": [10.0],
            "annotations": [["outdoor", "natural", "forest", "sunny", "daytime"]],
        })

        pkg = tmp_path / "test.mediapkg"

        with MediaPackageWriter(pkg, description="Test") as w:
            w.add_video("v001", "https://example.org/v.mp4")
            w.add_track("v001", scene_tags_track, df)

        with MediaPackageReader(pkg) as r:
            result = r.read_track("v001", "scene_tags")

        assert len(result.loc[0, "annotations"]) == 5
        assert "forest" in result.loc[0, "annotations"]


class TestAnnotationListSeriesValidation:
    """Test validation catches common errors."""

    def test_missing_start_column(self, tmp_path, scene_tags_track):
        """Missing start_seconds column fails validation."""
        df = pd.DataFrame({
            "end_seconds": [10.0],
            "annotations": [["outdoor"]],
        })

        pkg = tmp_path / "test.mediapkg"

        # Writer should reject missing columns
        with pytest.raises(ValueError, match="missing columns"):
            with MediaPackageWriter(pkg, description="Test") as w:
                w.add_video("v001", "https://example.org/v.mp4")
                w.add_track("v001", scene_tags_track, df)

    def test_string_instead_of_list_fails(self, tmp_path, scene_tags_track):
        """Validation catches strings instead of lists."""
        df = pd.DataFrame({
            "start_seconds": [0.0],
            "end_seconds": [10.0],
            "annotations": ["outdoor,natural"],  # String, not list!
        })

        pkg = tmp_path / "test.mediapkg"

        with MediaPackageWriter(pkg, description="Test") as w:
            w.add_video("v001", "https://example.org/v.mp4")
            w.add_track("v001", scene_tags_track, df)

        result = validate_mediapkg(pkg)

        assert not result.valid
        assert any("must contain lists" in err.lower() for err in result.errors)


class TestAnnotationListSeriesIntegration:
    """Integration tests with multiple track types."""

    def test_mixed_track_types_in_package(self, tmp_path, emotions_track,
                                          scene_tags_track, emotions_df, scene_tags_df):
        """Package can contain both ObservationSeries and AnnotationListSeries."""
        pkg = tmp_path / "test.mediapkg"

        with MediaPackageWriter(pkg, description="Mixed tracks") as w:
            w.add_video("v001", "https://example.org/v.mp4")
            w.add_track("v001", emotions_track, emotions_df)
            w.add_track("v001", scene_tags_track, scene_tags_df)

        with MediaPackageReader(pkg) as r:
            assert set(r.track_names) == {"emotions", "scene_tags"}

            # Can read both track types
            emotions = r.read_track("v001", "emotions")
            tags = r.read_track("v001", "scene_tags")

            assert "angry" in emotions.columns

            assert isinstance(tags.loc[0, "annotations"], (list, np.ndarray))
            assert list(tags.loc[0, "annotations"]) == ["outdoor", "natural"]
