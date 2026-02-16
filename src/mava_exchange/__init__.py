"""
mava-exchange — read and write .mediapkg archives.

Public API:

    from mava_exchange import (
        # Track definitions
        ObservationSeries,
        AnnotationSeries,
        DimensionSpec,

        # Reading and writing
        MediaPackageWriter,
        MediaPackageReader,
    )

Example — writing:

    from mava_exchange import (
        MediaPackageWriter, ObservationSeries, AnnotationSeries, DimensionSpec
    )

    emotions = ObservationSeries(
        name="emotions",
        description="Face emotion scores from DeepFace",
        sampling_interval=0.5,
        dimensions=[
            DimensionSpec("angry",   "Anger probability",  "[0,1]"),
            DimensionSpec("fear",    "Fear probability",   "[0,1]"),
            DimensionSpec("neutral", "Neutral expression", "[0,1]"),
        ]
    )
    transcript = AnnotationSeries(
        name="transcript",
        description="Whisper speech-to-text segments",
    )

    with MediaPackageWriter("corpus.mediapkg", description="My corpus") as w:
        w.add_video("video_001", "https://example.org/talk.mp4")
        w.add_track("video_001", emotions,   emotions_df)
        w.add_track("video_001", transcript, transcript_df)

Example — reading:

    from mava_exchange import MediaPackageReader

    with MediaPackageReader("corpus.mediapkg") as r:
        print(r.video_ids)
        df = r.read_track("video_001", "emotions")
"""

from .tracks import DimensionSpec, ObservationSeries, AnnotationSeries, Track
from .writer import MediaPackageWriter
from .reader import MediaPackageReader

__version__ = "0.1.0"

__all__ = [
    "AnnotationSeries",
    # Track definitions
    "DimensionSpec",
    "MediaPackageReader",
    # IO
    "MediaPackageWriter",
    "ObservationSeries",
    "Track",
]
