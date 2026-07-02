"""Export .mediapkg manifest as RDF (Turtle or JSON-LD)."""
from __future__ import annotations

import json

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF, XSD


def _value_key(x: object) -> str:
    """Stable sort key for a JSON-LD property value."""
    if isinstance(x, dict):
        return x.get("@id") or x.get("@value") or json.dumps(x, sort_keys=True)
    return str(x)


def _sort_node(node: dict) -> dict:
    """Sort a node's list-valued properties in place, recursing into objects."""
    for k, v in node.items():
        if isinstance(v, list):
            node[k] = sorted(
                (_sort_node(x) if isinstance(x, dict) else x for x in v),
                key=_value_key,
            )
    return node


def _canonical_jsonld(data: str) -> str:
    """Deterministically order rdflib's JSON-LD so regeneration is byte-stable.

    rdflib emits nodes (and their value lists) in an unstable order; sort the
    node list by @id, sort every value list, and sort keys on dump.
    """
    obj = json.loads(data)
    if isinstance(obj, list):
        obj = sorted((_sort_node(n) for n in obj), key=lambda n: n.get("@id", ""))
    elif isinstance(obj, dict) and isinstance(obj.get("@graph"), list):
        obj["@graph"] = sorted(
            (_sort_node(n) for n in obj["@graph"]), key=lambda n: n.get("@id", "")
        )
    elif isinstance(obj, dict):
        _sort_node(obj)
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"


def _add_dimensions(g, series_uri, track_name, track_def, MAVA, EX) -> None:  # noqa: PLR0913
    """Emit mava:Dimension nodes for an Observation- or RegionSeries."""
    for dim_name, dim_meta in track_def.get("dimensions", {}).items():
        dim_uri = EX[f"dim_{track_name}_{dim_name}"]
        g.add((series_uri, MAVA.hasDimension, dim_uri))
        g.add((dim_uri, RDF.type, MAVA.Dimension))
        g.add((dim_uri, MAVA.dimensionName, Literal(dim_name)))
        if "description" in dim_meta:
            g.add((dim_uri, MAVA.dimensionDescription, Literal(dim_meta["description"])))
        if "range" in dim_meta:
            g.add((dim_uri, MAVA.valueRange, Literal(dim_meta["range"])))


def export_manifest_as_rdf(  # noqa: PLR0912
    manifest: dict,
    format: str = "turtle",
    base_uri: str = "http://example.org/data/",
) -> str:
    """
    Export a manifest dict as RDF.

    Exports package structure only, not row data.

    Parameters
    ----------
    manifest : dict
        Parsed manifest.json dictionary from a .mediapkg archive.
    format : str
        "turtle" or "json-ld"
    base_uri : str
        Base URI for generated identifiers

    Returns
    -------
    str
        RDF serialization
    """
    MAVA = Namespace(manifest.get("ontology", "http://example.org/mava/ontology#"))
    EX = Namespace(base_uri)

    g = Graph()
    g.bind("mava", MAVA)
    g.bind("dcterms", DCTERMS)
    g.bind("xsd", XSD)
    g.bind("ex", EX)

    pkg_uri = EX["package"]
    g.add((pkg_uri, RDF.type, MAVA.MediaPackage))
    description = manifest.get("description", "")
    if description:
        g.add((pkg_uri, DCTERMS.description, Literal(description)))
    if "created" in manifest:
        g.add((pkg_uri, DCTERMS.created,
               Literal(manifest["created"], datatype=XSD.dateTime)))

    for video in manifest["videos"]:
        video_uri = EX[f"video_{video['id']}"]
        g.add((pkg_uri, MAVA.hasVideo, video_uri))
        g.add((video_uri, RDF.type, MAVA.Video))

        if "src" in video:
            # Absolute URI -> use as-is; a bare filename -> resolve against the
            # stable example base. Passing a relative ref to URIRef would let the
            # serializer resolve it against the cwd, leaking a local file:// path.
            src = video["src"]
            src_uri = URIRef(src) if "://" in src else EX[src]
            g.add((video_uri, DCTERMS.source, src_uri))

        for track_name in video.get("files", {}).keys():
            series_uri = EX[f"series_{track_name}"]
            g.add((video_uri, MAVA.hasAnalysis, series_uri))

    for track_name, track_def in manifest["tracks"].items():
        series_uri = EX[f"series_{track_name}"]
        track_type = track_def.get("type")

        if track_type == "mava:ObservationSeries":
            g.add((series_uri, RDF.type, MAVA.ObservationSeries))

            if "sampling_interval_seconds" in track_def:
                g.add((series_uri, MAVA.samplingInterval,
                       Literal(track_def["sampling_interval_seconds"], datatype=XSD.decimal)))

            _add_dimensions(g, series_uri, track_name, track_def, MAVA, EX)

        elif track_type == "mava:RegionSeries":
            g.add((series_uri, RDF.type, MAVA.RegionSeries))

            if "sampling_interval_seconds" in track_def:
                g.add((series_uri, MAVA.samplingInterval,
                       Literal(track_def["sampling_interval_seconds"], datatype=XSD.decimal)))
            if "coordinate_space" in track_def:
                g.add((series_uri, MAVA.coordinateSpace,
                       Literal(track_def["coordinate_space"])))

            _add_dimensions(g, series_uri, track_name, track_def, MAVA, EX)

        elif track_type == "mava:AnnotationSeries":
            g.add((series_uri, RDF.type, MAVA.AnnotationSeries))

        elif track_type == "mava:AnnotationListSeries":
            g.add((series_uri, RDF.type, MAVA.AnnotationListSeries))

        if "description" in track_def:
            g.add((series_uri, MAVA.seriesDescription,
                   Literal(track_def["description"])))

    if format == "turtle":
        # Collapse rdflib's trailing blank lines to a single newline so the
        # output matches the pre-commit end-of-file hook (no regenerate churn).
        return g.serialize(format="turtle").rstrip() + "\n"
    elif format == "json-ld":
        return _canonical_jsonld(g.serialize(format="json-ld"))
    else:
        raise ValueError(f"Unknown format '{format}'. Use 'turtle' or 'json-ld'.")
