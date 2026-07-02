"""
Tests for rdf.py — standalone export_manifest_as_rdf function.
"""

import pandas as pd
import pytest
import rdflib

from mava_exchange import (
    AnnotationSeries,
    DimensionSpec,
    MediaPackageReader,
    MediaPackageWriter,
    ObservationSeries,
)
from mava_exchange.rdf import export_manifest_as_rdf


def _manifest(pkg):
    with MediaPackageReader(pkg) as r:
        return r.manifest


def _relationship_pkg(pkg_path):
    """A package with a parent + derived_from/method edge, for relation tests."""
    shots = AnnotationSeries(name="shots", description="Shot segmentation")
    joanne = ObservationSeries(
        name="joanne", description="Presence score", sampling_interval=0.5,
        dimensions=[DimensionSpec("score", "Presence", "[0,1]")],
        parent="shots", derived_from=["shots"], method="cluster_to_scalar",
    )
    interval = pd.DataFrame(
        {"start_seconds": [0.0, 2.0], "end_seconds": [2.0, 4.0], "annotations": ["", ""]}
    )
    score = pd.DataFrame({"start_seconds": [0.0, 0.5], "score": [0.6, 0.4]})
    with MediaPackageWriter(pkg_path, description="Relations") as w:
        w.add_video("v1", "https://example.org/v1.mp4")
        w.add_track("v1", shots, interval)
        w.add_track("v1", joanne, score)
    return pkg_path


class TestRDFExport:

    def test_turtle_produces_string(self, single_video_pkg):
        ttl = export_manifest_as_rdf(_manifest(single_video_pkg), format="turtle")
        assert isinstance(ttl, str)
        assert len(ttl) > 100
        assert "@prefix mava:" in ttl

    def test_jsonld_produces_string(self, single_video_pkg):
        jsonld = export_manifest_as_rdf(_manifest(single_video_pkg), format="json-ld")
        assert isinstance(jsonld, str)
        assert len(jsonld) > 100
        assert "@id" in jsonld

    def test_turtle_contains_package(self, single_video_pkg):
        ttl = export_manifest_as_rdf(_manifest(single_video_pkg), format="turtle")
        assert "mava:MediaPackage" in ttl

    def test_turtle_contains_video(self, single_video_pkg):
        ttl = export_manifest_as_rdf(_manifest(single_video_pkg), format="turtle")
        assert "mava:Video" in ttl
        assert "v001" in ttl

    def test_turtle_contains_observation_series(self, single_video_pkg):
        ttl = export_manifest_as_rdf(_manifest(single_video_pkg), format="turtle")
        assert "mava:ObservationSeries" in ttl
        assert "emotions" in ttl or "emotion" in ttl

    def test_turtle_contains_annotation_series(self, single_video_pkg):
        ttl = export_manifest_as_rdf(_manifest(single_video_pkg), format="turtle")
        assert "mava:AnnotationSeries" in ttl
        assert "transcript" in ttl

    def test_turtle_contains_dimensions(self, single_video_pkg):
        ttl = export_manifest_as_rdf(_manifest(single_video_pkg), format="turtle")
        assert "mava:Dimension" in ttl
        assert "angry" in ttl
        assert "neutral" in ttl

    def test_turtle_parseable_by_rdflib(self, single_video_pkg):
        ttl = export_manifest_as_rdf(_manifest(single_video_pkg), format="turtle")
        g = rdflib.Graph()
        g.parse(data=ttl, format="turtle")
        assert len(g) > 10

    def test_unknown_format_raises(self, single_video_pkg):
        with pytest.raises(ValueError, match="Unknown format"):
            export_manifest_as_rdf(_manifest(single_video_pkg), format="xml")

    def test_custom_base_uri(self, single_video_pkg):
        ttl = export_manifest_as_rdf(
            _manifest(single_video_pkg),
            format="turtle",
            base_uri="http://myproject.org/",
        )
        assert "myproject.org" in ttl

    def test_turtle_contains_track_relationships(self, tmp_path):
        pkg = _relationship_pkg(tmp_path / "rel.mediapkg")
        ttl = export_manifest_as_rdf(_manifest(pkg), format="turtle")
        assert "mava:hasParent" in ttl
        assert "mava:derivedFrom" in ttl
        assert "mava:derivationMethod" in ttl

    def test_export_conforms_to_shacl(self, tmp_path):
        pyshacl = pytest.importorskip("pyshacl")
        pkg = _relationship_pkg(tmp_path / "rel.mediapkg")
        ttl = export_manifest_as_rdf(_manifest(pkg), format="turtle")
        data = rdflib.Graph().parse(data=ttl, format="turtle")
        shapes = rdflib.Graph().parse("spec/mava.shacl.ttl", format="turtle")
        conforms, _, text = pyshacl.validate(data, shacl_graph=shapes, inference="none")
        assert conforms, text

    def test_turtle_contains_region_series(self, tmp_path, region_track, region_df):
        pkg = tmp_path / "regions.mediapkg"
        with MediaPackageWriter(pkg, description="Regions") as w:
            w.add_video("v1", "https://example.org/v1.mp4")
            w.add_track("v1", region_track, region_df)
        ttl = export_manifest_as_rdf(_manifest(pkg), format="turtle")
        assert "mava:RegionSeries" in ttl
        assert "mava:coordinateSpace" in ttl
        assert "mava:Dimension" in ttl
        # geometry dimensions are emitted as Dimension nodes
        assert "det_score" in ttl
        g = rdflib.Graph()
        g.parse(data=ttl, format="turtle")
        assert len(g) > 10
