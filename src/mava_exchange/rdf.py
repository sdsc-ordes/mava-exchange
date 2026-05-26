"""Export .mediapkg manifest as RDF (Turtle or JSON-LD)."""
from __future__ import annotations

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF, XSD


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
            g.add((video_uri, DCTERMS.source, URIRef(video["src"])))

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

    if format == "turtle":
        return g.serialize(format="turtle")
    elif format == "json-ld":
        return g.serialize(format="json-ld", indent=2)
    else:
        raise ValueError(f"Unknown format '{format}'. Use 'turtle' or 'json-ld'.")
