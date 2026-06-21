"""
mava-exchange — Read and write .mediapkg video annotation packages.

Quick example::

    from mava_exchange import (
        MediaPackageWriter,
        MediaPackageReader,
        ObservationSeries,
        DimensionSpec,
    )

    # Define a track
    emotions = ObservationSeries(
        name="emotions",
        description="Face emotions",
        sampling_interval=0.5,
        dimensions=[
            DimensionSpec("happy", "Happiness", "[0,1]"),
            DimensionSpec("sad", "Sadness", "[0,1]"),
        ]
    )

    # Write package
    with MediaPackageWriter("output.mediapkg") as w:
        w.add_video("v001", "video.mp4")
        w.add_track("v001", emotions, emotions_df)

    # Read package
    with MediaPackageReader("output.mediapkg") as r:
        df = r.read_track("v001", "emotions")
        print(df.head())
"""
from .rdf import export_manifest_as_rdf
from .reader import MediaPackageReader, file_stats
from .tracks import (
    AnnotationListSeries,
    AnnotationSeries,
    DimensionSpec,
    ObservationSeries,
    RegionSeries,
    Track,
)
from .writer import MediaPackageWriter

__version__ = "0.1.0"

__all__ = [
    "AnnotationListSeries",
    "AnnotationSeries",
    "DimensionSpec",
    "MediaPackageReader",
    "MediaPackageWriter",
    "ObservationSeries",
    "RegionSeries",
    "Track",
    "export_manifest_as_rdf",
    "file_stats",
]
