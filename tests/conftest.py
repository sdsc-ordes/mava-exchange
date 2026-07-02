"""
Shared fixtures for mava_exchange tests.

All fixtures use synthetic data — no real TSV files needed.
"""

import numpy as np
import pandas as pd
import pytest

from mava_exchange import (
    AnnotationSeries,
    AnnotationListSeries,
    DimensionSpec,
    MediaPackageWriter,
    ObservationSeries,
    RegionSeries,
)


# ─────────────────────────────────────────────
# Track definitions
# ─────────────────────────────────────────────


@pytest.fixture
def emotions_track():
    return ObservationSeries(
        name="emotions",
        description="Face emotion scores",
        sampling_interval=0.5,
        dimensions=[
            DimensionSpec("angry", "Anger probability", "[0,1]"),
            DimensionSpec("neutral", "Neutral expression", "[0,1]"),
        ],
    )


@pytest.fixture
def transcript_track():
    return AnnotationSeries(
        name="transcript",
        description="Whisper speech-to-text segments",
    )


@pytest.fixture
def scene_tags_track():
    return AnnotationListSeries(
        name="scene_tags",
        description="Scene classification tags from Places3",
    )


@pytest.fixture
def rms_track():
    return ObservationSeries(
        name="rms_volume",
        description="RMS audio volume",
        sampling_interval=0.064,
        dimensions=[
            DimensionSpec("rms", "Root mean square volume", ">=0"),
        ],
    )


@pytest.fixture
def region_track():
    return RegionSeries(
        name="face_regions",
        description="Per-frame face bounding boxes",
        sampling_interval=0.5,
        coordinate_space="normalized",
        dimensions=[
            DimensionSpec("x", "Box left edge (normalized)", "[0,1]"),
            DimensionSpec("y", "Box top edge (normalized)", "[0,1]"),
            DimensionSpec("w", "Box width (normalized)", "[0,1]"),
            DimensionSpec("h", "Box height (normalized)", "[0,1]"),
            DimensionSpec("det_score", "Detection confidence", "[0,1]"),
        ],
    )


# ─────────────────────────────────────────────
# DataFrames
# ─────────────────────────────────────────────


@pytest.fixture
def emotions_df():
    """Synthetic emotion scores: 10 rows at 0.5s intervals."""
    n = 10
    t = np.arange(n) * 0.5
    rng = np.random.default_rng(42)
    scores = rng.dirichlet(np.ones(2), size=n)  # rows sum to 1
    return pd.DataFrame({
        "start_seconds": t,
        "angry": scores[:, 0],
        "neutral": scores[:, 1],
    })


@pytest.fixture
def transcript_df():
    """Synthetic transcript: 3 non-overlapping segments."""
    return pd.DataFrame({
        "start_seconds": [0.0, 5.2, 11.8],
        "end_seconds": [5.0, 11.5, 20.0],
        "annotations": ["Hello world", "This is a test", "Goodbye"],
    })


@pytest.fixture
def scene_tags_df():
    """Synthetic scene tags: 3 segments with multi-label annotations."""
    return pd.DataFrame({
        "start_seconds": [0.0, 45.2, 78.5],
        "end_seconds": [45.2, 78.5, 120.0],
        "annotations": [
            ["outdoor", "natural"],
            ["indoor"],
            ["outdoor", "man-made"],
        ],
    })


@pytest.fixture
def rms_df():
    """Synthetic RMS volume: 20 rows at 0.064s intervals."""
    n = 20
    rng = np.random.default_rng(99)
    return pd.DataFrame({
        "start_seconds": np.arange(n) * 0.064,
        "rms": np.abs(rng.normal(0.1, 0.05, n)),
    })


@pytest.fixture
def region_df():
    """Synthetic face boxes: long format (multiple detections per timestamp),
    with one detection whose label is null (cluster known, name unknown)."""
    return pd.DataFrame({
        "start_seconds": [0.0, 0.0, 0.5, 0.5, 1.0],
        "x":  [0.10, 0.60, 0.11, 0.61, 0.40],
        "y":  [0.20, 0.18, 0.21, 0.19, 0.50],
        "w":  [0.15, 0.14, 0.15, 0.14, 0.12],
        "h":  [0.30, 0.28, 0.30, 0.28, 0.20],
        "det_score": [0.95, 0.88, 0.93, 0.85, 0.70],
        "cluster_id": pd.array([0, 1, 0, 1, 2], dtype="Int64"),
        "label": ["Alice", "Bob", "Alice", "Bob", None],
    })


# ─────────────────────────────────────────────
# Package fixtures
# ─────────────────────────────────────────────


@pytest.fixture
def single_video_pkg(tmp_path, emotions_track, transcript_track,
                     emotions_df, transcript_df):
    """A .mediapkg with one video and two tracks."""
    pkg_path = tmp_path / "single.mediapkg"
    with MediaPackageWriter(pkg_path, description="Single video test") as w:
        w.add_video("v001", "https://example.org/v001.mp4")
        w.add_track("v001", emotions_track, emotions_df)
        w.add_track("v001", transcript_track, transcript_df)
    return pkg_path


@pytest.fixture
def corpus_pkg(tmp_path, emotions_track, transcript_track, rms_track,
               emotions_df, transcript_df, rms_df):
    """A .mediapkg corpus with two videos and different track sets."""
    pkg_path = tmp_path / "corpus.mediapkg"
    with MediaPackageWriter(pkg_path, description="Corpus test") as w:
        w.add_video("v001", "https://example.org/v001.mp4")
        w.add_track("v001", emotions_track, emotions_df)
        w.add_track("v001", transcript_track, transcript_df)

        w.add_video("v002", "https://example.org/v002.mp4")
        w.add_track("v002", rms_track, rms_df)
        w.add_track("v002", transcript_track, transcript_df)
    return pkg_path
