"""
Tests for track definitions (tracks.py).

Checks that ObservationSeries and AnnotationSeries produce the correct
manifest dicts and column lists.
"""

import pytest

from mava_exchange import (
    AnnotationListSeries,
    AnnotationSeries,
    DimensionSpec,
    ObservationSeries,
    RegionSeries,
)


def _obs_tdm(tool_data_model=None):
    return ObservationSeries(
        name="emotions",
        description="Test",
        dimensions=[DimensionSpec("angry", "Anger", "[0,1]")],
        tool_data_model=tool_data_model,
)
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

    def test_to_dict_tool_data_model_omitted_when_unset(self):
        track = ObservationSeries(
            name="emotions",
            description="Test",
            dimensions=[DimensionSpec("angry", "Anger", "[0,1]")]
        )
        assert "tool_data_model" not in track.to_dict()

    def test_to_dict_tool_data_model_present_when_set(self):
        track = _obs_tdm({"tibava": { "model" : "EmotionDataModel"}})
        assert track.to_dict()["tool_data_model"] == {"tibava": { "model" : "EmotionDataModel"}}

    def test_tool_data_model_output_is_independent_copy(self):
        track = _obs_tdm({"tibava": {"model": "emotions"}})
        track.to_dict()["tool_data_model"]["tibava"]["model"] = "changed"
        assert track.tool_data_model == {"tibava": {"model": "emotions"}}

    def test_tool_data_model_input_is_independent_copy(self):
        source = {"tibava": {"model": "emotions"}}
        track = _obs_tdm(source)
        source["tibava"]["model"] = "changed"
        assert track.to_dict()["tool_data_model"] == {"tibava": {"model": "emotions"}}

    def test_tool_data_model_empty_dict_is_omitted(self):
        assert "tool_data_model" not in _obs_tdm({}).to_dict()

    def test_tool_data_model_drops_empty_name_with_warning(self, caplog):
        track = _obs_tdm({"    ": {"model": "x"}, "tibava": {"model": "emotions"}})
        assert track.to_dict()["tool_data_model"] == {"tibava": {"model": "emotions"}}
        assert "empty tool name" in caplog.text

    def test_tool_data_model_only_empty_names_is_omitted(self):
        assert "tool_data_model" not in _obs_tdm({"": {"model": "x"}}).to_dict()

    @pytest.mark.parametrize("bad_value", [
        ["tibava"],                 # not a mapping
        {"tibava": {"emotions"}},   # value is a set
        {"tibava": "emotions"},     # value is a string
        {"tibava": ["emotions"]},   # value is a list
        {42: {"model": "x"}},       # non-string key
    ])
    def test_tool_data_model_rejects_invalid_structure(self, bad_value):
        with pytest.raises(TypeError):
            _obs_tdm(bad_value)


    def test_tool_data_model_supported_on_obs_series(self):
        obs_track = _obs_tdm({"tibava": { "model" : "EmotionDataModel"}})
        assert obs_track.to_dict()["tool_data_model"] == {"tibava": { "model" : "EmotionDataModel"}}

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

    def test_tool_data_model_supported_on_anno_series(self):
        anno_track = AnnotationSeries(
            name="transcript",
            description="Speech-to-text from Whisper",
            tool_data_model={"tibava": { "model" : "EmotionDataModel"}}
        )
        assert anno_track.to_dict()["tool_data_model"] == {"tibava": { "model" : "EmotionDataModel"}}

    def test_tool_data_model_supported_on_anno_list_series(self):
        anno_track = AnnotationListSeries(
            name="scene_tags",
            description="Scene classification (indoor/outdoor + natural/man-made)",
            tool_data_model={"tibava": { "model" : "EmotionDataModel"}}
        )
        assert anno_track.to_dict()["tool_data_model"] == {"tibava": { "model" : "EmotionDataModel"}}

class TestRegionSeries:

    def test_tool_data_model_supported_on_region_series(self):
        region_track = RegionSeries(
                name="face_regions",
                description="Per-frame face bounding boxes",
                sampling_interval=0.5,
                dimensions=[
                    DimensionSpec("x", "Box left edge (normalized)", "[0,1]"),
                    DimensionSpec("y", "Box top edge (normalized)", "[0,1]"),
                    DimensionSpec("w", "Box width (normalized)", "[0,1]"),
                    DimensionSpec("h", "Box height (normalized)", "[0,1]"),
                    DimensionSpec("det_score", "Detection confidence", "[0,1]"),
                ],
                tool_data_model={"tibava": { "model" : "EmotionDataModel"}}
            )
        assert region_track.to_dict()["tool_data_model"] == {"tibava": { "model" : "EmotionDataModel"}}


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
