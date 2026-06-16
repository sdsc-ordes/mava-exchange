"""
Example: convert TSV annotation files to a .mediapkg archive.

This script is an example of how to use the mava_exchange library.
It is not part of the library itself — it lives in examples/.

Expects the following layout:
    examples/
      video_001/
        Angry.tsv  Disgust.tsv  Fear.tsv  Happy.tsv
        Sad.tsv  Surprise.tsv  Neutral.tsv
        Shots.tsv  Face Emotions.tsv  Whisper Transcript.tsv
        scene_tags.tsv
      video_002/
        Shots.tsv  RMS Volume.tsv  Dominant Color(s).tsv
      output/
        corpus.mediapkg   ← written here

Run:
    uv run examples/tsv_to_mediapkg.py
"""

import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from mava_exchange import (
    MediaPackageWriter,
    ObservationSeries,
    AnnotationSeries,
    AnnotationListSeries,
    DimensionSpec,
)


# ─────────────────────────────────────────────
# Track definitions
# ─────────────────────────────────────────────

EMOTIONS_TRACK = ObservationSeries(
    name="emotions",
    description="Per-frame probability scores from face analysis model, sampled every 0.5s.",
    sampling_interval=0.5,
    dimensions=[
        DimensionSpec("angry",    "Anger probability",    "[0,1]"),
        DimensionSpec("disgust",  "Disgust probability",  "[0,1]"),
        DimensionSpec("fear",     "Fear probability",     "[0,1]"),
        DimensionSpec("happy",    "Happiness probability","[0,1]"),
        DimensionSpec("sad",      "Sadness probability",  "[0,1]"),
        DimensionSpec("surprise", "Surprise probability", "[0,1]"),
        DimensionSpec("neutral",  "Neutral expression",   "[0,1]"),
    ]
)
SHOTS_TRACK = AnnotationSeries(
    name="shots",
    description="Shot boundary intervals detected by scene detection model.",
)
FACE_EMOTIONS_TRACK = AnnotationSeries(
    name="face_emotions",
    description="Dominant face emotion label per detected interval.",
)
TRANSCRIPT_TRACK = AnnotationSeries(
    name="transcript",
    description="Speech-to-text segments from Whisper transcription model.",
)
SCENE_TAGS_TRACK = AnnotationListSeries(
    name="scene_tags",
    description="Scene classification tags from Places3 model (indoor/outdoor + natural/man-made).",
)
RMS_VOLUME_TRACK = ObservationSeries(
    name="rms_volume",
    description="RMS audio volume sampled at ~0.064s intervals.",
    sampling_interval=0.064,
    dimensions=[
        DimensionSpec("rms", "Root mean square audio volume", ">=0"),
    ]
)
DOMINANT_COLOR_TRACK = ObservationSeries(
    name="dominant_color",
    description="Dominant RGB color sampled every 0.5s. Each channel is a float in [0,1].",
    sampling_interval=0.5,
    dimensions=[
        DimensionSpec("r", "Red channel of dominant color",   "[0,1]"),
        DimensionSpec("g", "Green channel of dominant color", "[0,1]"),
        DimensionSpec("b", "Blue channel of dominant color",  "[0,1]"),
    ]
)


# ─────────────────────────────────────────────
# TSV loaders
# ─────────────────────────────────────────────

# Fixed creation timestamp so regenerating the example produces a
# byte-identical corpus.mediapkg (no spurious git diffs).
FIXED_CREATED = datetime(2025, 1, 1, tzinfo=timezone.utc)

EMOTION_NAMES = ["Angry", "Disgust", "Fear", "Happy", "Sad", "Surprise", "Neutral"]


def load_emotions(data_dir: Path) -> pd.DataFrame:
    dfs = []
    for name in EMOTION_NAMES:
        df = pd.read_csv(data_dir / f"{name}.tsv", sep="\t")
        df = df.rename(columns={
            "start in seconds":  "start_seconds",
            "start hh:mm:ss.ms": "_drop",
            "annotations":       name.lower(),
        })
        dfs.append(df.set_index("start_seconds")[[name.lower()]])
    return pd.concat(dfs, axis=1).reset_index()


def load_interval(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t")
    df = df.rename(columns={
        "start in seconds":     "start_seconds",
        "start hh:mm:ss.ms":    "_drop1",
        "duration in seconds":  "_duration",
        "duration hh:mm:ss.ms": "_drop2",
        "annotations":          "annotations",
    })
    df["end_seconds"] = df["start_seconds"] + df["_duration"]
    return df[["start_seconds", "end_seconds", "annotations"]]


def load_scene_tags(data_dir: Path) -> pd.DataFrame:
    """Load scene tags and convert comma-separated values to lists."""
    df = pd.read_csv(data_dir / "scene_tags.tsv", sep="\t", comment="#")
    df["start_seconds"] = pd.to_numeric(df["start_seconds"])
    df["end_seconds"] = pd.to_numeric(df["end_seconds"])
    df["annotations"] = df["tags"].str.split(",")
    return df[["start_seconds", "end_seconds", "annotations"]]


def load_rms_volume(data_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(data_dir / "RMS Volume.tsv", sep="\t")
    df = df.rename(columns={
        "start in seconds":  "start_seconds",
        "start hh:mm:ss.ms": "_drop",
        "annotations":       "rms",
    })
    df["rms"] = pd.to_numeric(df["rms"], errors="coerce")
    return df[["start_seconds", "rms"]].dropna()


def _parse_rgb(val: str) -> tuple[float, float, float]:
    nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", str(val))
    rgb_vector_length = 3
    if len(nums) >= rgb_vector_length:
        return float(nums[0]), float(nums[1]), float(nums[2])
    return float("nan"), float("nan"), float("nan")


def load_dominant_color(data_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(data_dir / "Dominant Color(s).tsv", sep="\t")
    df = df.rename(columns={
        "start in seconds":  "start_seconds",
        "start hh:mm:ss.ms": "_drop",
        "annotations":       "_raw",
    })
    rgb = df["_raw"].apply(_parse_rgb)
    df["r"] = rgb.apply(lambda x: x[0])
    df["g"] = rgb.apply(lambda x: x[1])
    df["b"] = rgb.apply(lambda x: x[2])
    return df[["start_seconds", "r", "g", "b"]]


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    examples_dir = Path(__file__).parent.parent
    input_dir  = examples_dir / "input"
    dir_001  = input_dir / "video_001"
    dir_002  = input_dir / "video_002"
    out_path = examples_dir / "output" / "corpus.mediapkg"
    out_path.parent.mkdir(exist_ok=True)

    print("Loading video_001...")
    emotions_df      = load_emotions(dir_001)
    shots_001_df     = load_interval(dir_001 / "Shots.tsv")
    face_emotions_df = load_interval(dir_001 / "Face Emotions.tsv")
    transcript_df    = load_interval(dir_001 / "Whisper Transcript.tsv")
    scene_tags_df    = load_scene_tags(dir_001)

    print("Loading video_002...")
    shots_002_df = load_interval(dir_002 / "Shots.tsv")
    rms_df       = load_rms_volume(dir_002)
    color_df     = load_dominant_color(dir_002)

    print(f"Writing {out_path}...")
    with MediaPackageWriter(
        out_path,
        description="Example corpus: two videos with different annotation tracks",
        created=FIXED_CREATED,
    ) as writer:
        writer.add_video("video_001", "https://example.org/videos/talk_001.mp4")
        writer.add_track("video_001", EMOTIONS_TRACK,      emotions_df)
        writer.add_track("video_001", SHOTS_TRACK,         shots_001_df)
        writer.add_track("video_001", FACE_EMOTIONS_TRACK, face_emotions_df)
        writer.add_track("video_001", TRANSCRIPT_TRACK,    transcript_df)
        writer.add_track("video_001", SCENE_TAGS_TRACK,    scene_tags_df)

        writer.add_video("video_002", "https://example.org/videos/talk_002.mp4")
        writer.add_track("video_002", SHOTS_TRACK,          shots_002_df)
        writer.add_track("video_002", RMS_VOLUME_TRACK,     rms_df)
        writer.add_track("video_002", DOMINANT_COLOR_TRACK, color_df)

    print("Done.")


if __name__ == "__main__":
    main()
