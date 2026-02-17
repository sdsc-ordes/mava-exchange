"""
Tests for track definitions (tracks.py).

Checks that ObservationSeries and AnnotationSeries produce the correct
manifest dicts and column lists.
"""

from mava_exchange import ObservationSeries, AnnotationSeries, DimensionSpec


class TestObservationSeries:

    def test_columns_include_start_seconds(self):
        track = ObservationSeries(
            name="emotions",
            description="Test",
            dimensions=[DimensionSpec("angry", "Anger", "[0,1]")]
        )
        assert track.columns[0] == "start_seconds"

    def test_columns_include_all_dimensions(self):
        track = ObservationSeries(
            name="emotions",
            description="Test",
            dimensions=[
                DimensionSpec("angry",   "Anger",   "[0,1]"),
                DimensionSpec("neutral", "Neutral", "[0,1]"),
            ]
        )
        assert track.columns == ["start_seconds", "angry", "neutral"]

    def test_to_dict_type(self):
        track = ObservationSeries(
            name="emotions",
            description="Test",
            dimensions=[DimensionSpec("angry", "Anger", "[0,1]")]
        )
        assert track.to_dict()["type"] == "mava:ObservationSeries"

    def test_to_dict_sampling_interval_optional(self):
        track = ObservationSeries(
            name="emotions",
            description="Test",
            dimensions=[DimensionSpec("angry", "Anger", "[0,1]")]
        )
        assert "sampling_interval_seconds" not in track.to_dict()

    def test_to_dict_sampling_interval_present_when_set(self):
        track = ObservationSeries(
            name="emotions",
            description="Test",
            sampling_interval=0.5,
            dimensions=[DimensionSpec("angry", "Anger", "[0,1]")]
        )
        assert track.to_dict()["sampling_interval_seconds"] == 0.5

    def test_to_dict_dimensions(self):
        track = ObservationSeries(
            name="emotions",
            description="Test",
            dimensions=[
                DimensionSpec("angry", "Anger probability", "[0,1]"),
            ]
        )
        dims = track.to_dict()["dimensions"]
        assert "angry" in dims
        assert dims["angry"]["description"] == "Anger probability"
        assert dims["angry"]["range"] == "[0,1]"

    def test_type_field_not_settable(self):
        """type is always mava:ObservationSeries regardless of what you pass."""
        track = ObservationSeries(
            name="x", description="x",
            dimensions=[DimensionSpec("v", "v")]
        )
        assert track.type == "mava:ObservationSeries"


class TestAnnotationSeries:

    def test_columns_fixed(self):
        track = AnnotationSeries(name="transcript", description="Test")
        assert track.columns == ["start_seconds", "end_seconds", "annotations"]

    def test_to_dict_type(self):
        track = AnnotationSeries(name="transcript", description="Test")
        assert track.to_dict()["type"] == "mava:AnnotationSeries"

    def test_to_dict_no_dimensions(self):
        track = AnnotationSeries(name="transcript", description="Test")
        assert "dimensions" not in track.to_dict()


class TestDimensionSpec:

    def test_to_dict_includes_description(self):
        dim = DimensionSpec("angry", "Anger score", "[0,1]")
        d = dim.to_dict()
        assert d["description"] == "Anger score"
        assert d["range"] == "[0,1]"

    def test_to_dict_omits_empty_range(self):
        dim = DimensionSpec("angry", "Anger score")
        d = dim.to_dict()
        assert "range" not in d
