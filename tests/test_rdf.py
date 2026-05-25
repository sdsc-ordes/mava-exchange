"""
Tests for rdf.py — standalone export_manifest_as_rdf function.
"""

import pytest
import rdflib

from mava_exchange import MediaPackageReader
from mava_exchange.rdf import export_manifest_as_rdf


def _manifest(pkg):
    with MediaPackageReader(pkg) as r:
        return r.manifest


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
