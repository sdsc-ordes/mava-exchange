"""
Tests for the `tool_specific_data_model` field.

The field exists so that an importer can map a MAVA series back to the
tool-internal data model it came from. That only works if the value survives
every hop: manifest, reader, and RDF export. Each hop has its own test here,
because the field has silently lost data at two of them before.
"""

import contextlib
import io
import json
import zipfile

import pandas as pd
import pytest
import rdflib

from mava_exchange import (
    AnnotationListSeries,
    AnnotationSeries,
    DimensionSpec,
    MediaPackageReader,
    MediaPackageWriter,
    ObservationSeries,
    RegionSeries,
)
from mava_exchange.rdf import export_manifest_as_rdf
from mava_exchange.validate import validate_mediapkg

MAVA_TSDM = rdflib.URIRef("http://example.org/mava/ontology#toolSpecificDataModel")

TSDM = {"tibava": "RGB_HIST"}


# ─────────────────────────────────────────────
# Track definitions covering all four series types
# ─────────────────────────────────────────────

def _observation(**kw):
    return ObservationSeries(
        name="obs", description="Observation",
        dimensions=[DimensionSpec("score", "Score", "[0,1]")],
        sampling_interval=0.5, **kw,
    )


def _annotation(**kw):
    return AnnotationSeries(name="ann", description="Annotation", **kw)


def _annotation_list(**kw):
    return AnnotationListSeries(name="lst", description="Annotation list", **kw)


def _region(**kw):
    return RegionSeries(
        name="reg", description="Region",
        dimensions=[DimensionSpec("det_score", "Detection", "[0,1]")],
        sampling_interval=0.5, **kw,
    )


ALL_TRACKS = [_observation, _annotation, _annotation_list, _region]


def _df_for(track):
    """A minimal DataFrame matching the track's declared columns."""
    cols = track.columns
    if "annotations" in cols and "end_seconds" in cols:
        data = {"start_seconds": [0.0], "end_seconds": [1.0]}
        data["annotations"] = [["a", "b"]] if isinstance(track, AnnotationListSeries) else ["a"]
        return pd.DataFrame(data)
    if isinstance(track, RegionSeries):
        return pd.DataFrame({
            "start_seconds": [0.0], "x": [0.1], "y": [0.1], "w": [0.2], "h": [0.2],
            "det_score": [0.9], "cluster_id": [0], "label": ["face"],
        })
    return pd.DataFrame({"start_seconds": [0.0, 0.5], "score": [0.1, 0.2]})


def _write_pkg(pkg_path, track):
    with MediaPackageWriter(pkg_path, description="tsdm") as w:
        w.add_video("v001", "https://example.org/v.mp4")
        w.add_track("v001", track, _df_for(track))
    return pkg_path


# ─────────────────────────────────────────────
# to_dict
# ─────────────────────────────────────────────

class TestToDict:

    @pytest.mark.parametrize("factory", ALL_TRACKS)
    def test_omitted_when_unset(self, factory):
        assert "tool_specific_data_model" not in factory().to_dict()

    @pytest.mark.parametrize("factory", ALL_TRACKS)
    def test_present_when_set(self, factory):
        d = factory(tool_specific_data_model=TSDM).to_dict()
        assert d["tool_specific_data_model"] == TSDM

    def test_to_dict_copies_the_dict(self):
        """to_dict must not hand out a reference to the track's own dict."""
        source = {"tibava": "SCALAR"}
        d = _observation(tool_specific_data_model=source).to_dict()
        d["tool_specific_data_model"]["tibava"] = "MUTATED"
        assert source == {"tibava": "SCALAR"}


# ─────────────────────────────────────────────
# Round-trip: writer → reader
# ─────────────────────────────────────────────

class TestRoundTrip:

    @pytest.mark.parametrize("factory", ALL_TRACKS)
    def test_survives_write_then_read(self, tmp_path, factory):
        track = factory(tool_specific_data_model=TSDM)
        pkg = _write_pkg(tmp_path / "t.mediapkg", track)
        with MediaPackageReader(pkg) as r:
            assert r.track_def(track.name).tool_specific_data_model == TSDM

    @pytest.mark.parametrize("factory", ALL_TRACKS)
    def test_absent_stays_none(self, tmp_path, factory):
        track = factory()
        pkg = _write_pkg(tmp_path / "t.mediapkg", track)
        with MediaPackageReader(pkg) as r:
            assert r.track_def(track.name).tool_specific_data_model is None

    def test_several_models_from_one_tool(self, tmp_path):
        """The scenario SPEC.md names: two of a tool's models, one series."""
        several = {"tibava": ["emotion-data", "colour-data"]}
        track = _observation(tool_specific_data_model=several)
        pkg = _write_pkg(tmp_path / "t.mediapkg", track)
        with MediaPackageReader(pkg) as r:
            assert r.track_def("obs").tool_specific_data_model == several

    def test_multiple_tools_on_one_series(self, tmp_path):
        both = {"tibava": "SCALAR", "autoannotator": "video_brightness"}
        track = _observation(tool_specific_data_model=both)
        pkg = _write_pkg(tmp_path / "t.mediapkg", track)
        with MediaPackageReader(pkg) as r:
            assert r.track_def("obs").tool_specific_data_model == both


# ─────────────────────────────────────────────
# RDF export
#
# Regression guard: the exporter once iterated the dict, which yields keys,
# so every track exported the bare tool name and the model was lost.
# ─────────────────────────────────────────────

class TestRDFExport:

    def _graph(self, pkg):
        with MediaPackageReader(pkg) as r:
            manifest = r.manifest
        g = rdflib.Graph()
        g.parse(data=export_manifest_as_rdf(manifest, format="turtle"), format="turtle")
        return g

    @pytest.mark.parametrize("factory", ALL_TRACKS)
    def test_exports_one_json_literal_per_track(self, tmp_path, factory):
        pkg = _write_pkg(tmp_path / "t.mediapkg", factory(tool_specific_data_model=TSDM))
        values = list(self._graph(pkg).objects(predicate=MAVA_TSDM))
        assert len(values) == 1
        assert json.loads(str(values[0])) == TSDM

    def test_literal_is_typed_rdf_json(self, tmp_path):
        pkg = _write_pkg(tmp_path / "t.mediapkg", _observation(tool_specific_data_model=TSDM))
        literal = next(self._graph(pkg).objects(predicate=MAVA_TSDM))
        assert literal.datatype == rdflib.RDF.JSON

    def test_model_value_is_not_dropped(self, tmp_path):
        """The bug this file exists for: keys survived, values did not."""
        pkg = _write_pkg(tmp_path / "t.mediapkg", _observation(tool_specific_data_model=TSDM))
        ttl = export_manifest_as_rdf(_manifest_of(pkg), format="turtle")
        assert "RGB_HIST" in ttl

    def test_omitted_when_unset(self, tmp_path):
        pkg = _write_pkg(tmp_path / "t.mediapkg", _observation())
        assert list(self._graph(pkg).objects(predicate=MAVA_TSDM)) == []

    def test_export_is_byte_stable(self, tmp_path):
        """Key order must not vary between runs — the corpus is committed."""
        unordered = {"zebra": "Z", "alpha": "A", "middle": "M"}
        pkg = _write_pkg(tmp_path / "t.mediapkg", _observation(tool_specific_data_model=unordered))
        manifest = _manifest_of(pkg)
        first = export_manifest_as_rdf(manifest, format="turtle")
        second = export_manifest_as_rdf(manifest, format="turtle")
        assert first == second


def _manifest_of(pkg):
    with MediaPackageReader(pkg) as r:
        return r.manifest


# ─────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────

class TestValidation:

    def _validate_with(self, tmp_path, value):
        """Write a valid package, rewrite the field, then validate it."""
        pkg = _write_pkg(tmp_path / "t.mediapkg", _observation(tool_specific_data_model=TSDM))
        patched = tmp_path / "patched.mediapkg"
        with zipfile.ZipFile(pkg) as zin, zipfile.ZipFile(patched, "w") as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "manifest.json":
                    manifest = json.loads(data)
                    manifest["tracks"]["obs"]["tool_specific_data_model"] = value
                    data = json.dumps(manifest, indent=2).encode()
                zout.writestr(item, data)
        with contextlib.redirect_stdout(io.StringIO()):
            result = validate_mediapkg(patched)
        return [e for e in result.errors if "tool_specific" in e]

    def test_one_model_per_tool_accepted(self, tmp_path):
        assert self._validate_with(tmp_path, {"tibava": "SCALAR"}) == []

    def test_several_models_from_one_tool_accepted(self, tmp_path):
        """SPEC.md: the field exists for several of a tool's models mapping
        to one series, so a single tool's entry may name more than one."""
        value = {"tibava": ["emotion-data", "colour-data"]}
        assert self._validate_with(tmp_path, value) == []

    def test_several_tools_accepted(self, tmp_path):
        """A package picks up a key per tool as it is re-exported."""
        value = {"tibava": "SCALAR", "autoannotator": ["brightness", "waveform"]}
        assert self._validate_with(tmp_path, value) == []

    @pytest.mark.parametrize("value", [["SCALAR"], "SCALAR", 3])
    def test_non_object_rejected(self, tmp_path, value):
        """The pre-migration form carried no tool name; it must not pass."""
        assert self._validate_with(tmp_path, value)

    @pytest.mark.parametrize("model", [3, {"nested": "object"}, ["ok", 3], []])
    def test_malformed_model_rejected(self, tmp_path, model):
        assert self._validate_with(tmp_path, {"tibava": model})

    def test_empty_tool_name_rejected(self, tmp_path):
        assert self._validate_with(tmp_path, {"": "SCALAR"})
