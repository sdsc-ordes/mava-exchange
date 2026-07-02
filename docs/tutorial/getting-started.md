# Getting Started

This tutorial walks through the core workflows for the `mava-exchange` library:
writing a `.mediapkg` file from DataFrames, reading one back, validating it, and
inspecting it from the command line.

## Installation

```bash
pip install mava-exchange
# or with uv:
uv add mava-exchange
```

## Concepts

A `.mediapkg` file is a ZIP archive containing annotation data for one or more
videos. Each video has one or more **tracks** — Parquet files containing the
actual data.

There are four kinds of tracks:

- **ObservationSeries** — a dense time-series of numeric values sampled at
  regular intervals. Each row is one point in time with one or more numeric
  dimensions. Use this for ML model outputs like emotion scores, audio volume,
  or any score sampled at a fixed rate.

- **AnnotationSeries** — sparse interval annotations. Each row covers a time
  span (`start_seconds` → `end_seconds`) with a string value. Use this for
  transcripts, shot boundaries, or any labeled segment.

- **AnnotationListSeries** — sparse interval annotations with multiple labels
  per segment. Each row covers a time span with a list of string values. Use
  this for multi-label classifications, keyword tags, or any annotation where
  multiple values apply simultaneously.

- **RegionSeries** — spatial detections in long format (one row per detection,
  so many rows may share a `start_seconds`). Each row is a bounding box (`x`,
  `y`, `w`, `h`) with a detection score and an identity (`cluster_id` + optional
  `label`). Use this for face or object boxes. (Added in format 0.2.)

---

## 1. Writing a `.mediapkg`

### 1.1 Define your tracks

First describe what your data means using `ObservationSeries` or
`AnnotationSeries`. This is the semantic layer — it tells consumers what each
column measures.

```python
from mava_exchange import ObservationSeries, AnnotationSeries, AnnotationListSeries, DimensionSpec

# A time-series track: one numeric value per dimension per timestep
emotion_track = ObservationSeries(
    name="emotions",
    description="Face emotion probability scores from DeepFace model",
    sampling_interval=0.5,   # seconds between samples
    dimensions=[
        DimensionSpec("angry",   "Anger probability",    "[0,1]"),
        DimensionSpec("happy",   "Happiness probability","[0,1]"),
        DimensionSpec("neutral", "Neutral expression",   "[0,1]"),
    ]
)

# An interval annotation track: start, end, and a string label per row
transcript_track = AnnotationSeries(
    name="transcript",
    description="Speech-to-text segments from Whisper",
)

# A multi-label annotation track: start, end, and a list of labels per row
scene_tags_track = AnnotationListSeries(
    name="scene_tags",
    description="Scene classification tags from Places3 model",
)
```

You can define any dimensions you need — the library is not tied to emotion
scores. For example, a different tool might declare:

```python
explosion_track = ObservationSeries(
    name="explosion_detection",
    description="Explosion probability from audio model, sampled every 0.1s",
    sampling_interval=0.1,
    dimensions=[
        DimensionSpec("explosion", "Explosion probability", "[0,1]"),
    ]
)
```

### 1.2 Prepare your DataFrames

Each track expects a DataFrame with the columns declared in its definition.

For an **ObservationSeries**, the required columns are `start_seconds` plus one
column per dimension:

```python
import pandas as pd
import numpy as np

n = 100
emotions_df = pd.DataFrame({
    "start_seconds": np.arange(n) * 0.5,
    "angry":         np.random.uniform(0, 0.3, n),
    "happy":         np.random.uniform(0, 0.8, n),
    "neutral":       np.random.uniform(0, 0.5, n),
})
```

For an **AnnotationSeries**, the required columns are `start_seconds`,
`end_seconds`, and `annotations`:

```python
transcript_df = pd.DataFrame({
    "start_seconds": [0.0,  12.5, 30.1],
    "end_seconds":   [12.3, 29.8, 45.0],
    "annotations":   [
        "Welcome to the conference.",
        "Today we discuss video annotation.",
        "Thank you for joining us.",
    ],
})
```

For an **AnnotationListSeries**, the required columns are start_seconds,
end_seconds, and annotations — but annotations contains lists of strings:

```
scene_tags_df = pd.DataFrame({
    "start_seconds": [0.0, 45.2, 78.5],
    "end_seconds":   [45.2, 78.5, 120.0],
    "annotations":   [
        ["outdoor", "natural"],
        ["indoor"],
        ["outdoor", "man-made"],
    ],
})
```

### 1.3 Write the package

Use `MediaPackageWriter` as a context manager. Call `add_video()` first, then
`add_track()` for each track. The file is written when the `with` block exits.

```python
from mava_exchange import MediaPackageWriter

with MediaPackageWriter("corpus.mediapkg", description="My annotation corpus") as writer:
    writer.add_video(
        video_id="video_001",
        src="https://example.org/videos/talk.mp4",
    )
    writer.add_track("video_001", emotion_track,   emotions_df)
    writer.add_track("video_001", transcript_track, transcript_df)
```

### 1.4 Multiple videos

Add as many videos as you need before the `with` block exits. Videos can have
different track sets — a track name shared across videos must have an identical
definition:

```python
rms_track = ObservationSeries(
    name="rms_volume",
    description="RMS audio volume",
    sampling_interval=0.064,
    dimensions=[DimensionSpec("rms", "Root mean square audio volume", ">=0")]
)

rms_df = pd.DataFrame({
    "start_seconds": np.arange(200) * 0.064,
    "rms":           np.abs(np.random.normal(0.1, 0.02, 200)),
})

with MediaPackageWriter("corpus.mediapkg", description="Two-video corpus") as writer:
    # video_001: emotions + transcript
    writer.add_video("video_001", "https://example.org/videos/talk_001.mp4")
    writer.add_track("video_001", emotion_track,    emotions_df)
    writer.add_track("video_001", transcript_track, transcript_df)

    # video_002: rms volume + transcript (different track set)
    writer.add_video("video_002", "https://example.org/videos/talk_002.mp4")
    writer.add_track("video_002", rms_track,        rms_df)
    writer.add_track("video_002", transcript_track, transcript_df)
```

---

## 2. Reading a `.mediapkg`

Use `MediaPackageReader` to read a package. Use it as a context manager to
ensure the file is closed properly.

```python
from mava_exchange import MediaPackageReader

with MediaPackageReader("corpus.mediapkg") as reader:

    # What's in this package?
    print(reader.video_ids)       # ["video_001", "video_002"]
    print(reader.track_names)     # ["emotions", "transcript", "rms_volume", "scene_tags"]

    # Which tracks does a specific video have?
    print(reader.tracks_for_video("video_001"))  # ["emotions", "transcript"]
    print(reader.tracks_for_video("video_002"))  # ["rms_volume", "transcript"]

    # Read a track into a DataFrame
    df = reader.read_track("video_001", "emotions")
    print(df.head())
    #    start_seconds     angry     happy   neutral
    # 0            0.0  0.12451  0.64231  0.23318
    # 1            0.5  0.08734  0.71204  0.20062

    # Read all tracks for a video at once
    tracks = reader.read_video("video_001")
    # tracks == {"emotions": df, "transcript": df}

    # Get track definition (reconstructed as a typed object)
    track = reader.track_def("emotions")
    print(track.sampling_interval)        # 0.5
    print([d.name for d in track.dimensions])  # ["angry", "happy", "neutral"]

    # Get video metadata
    meta = reader.video_meta("video_001")
    print(meta["src"])  # "https://example.org/videos/talk_001.mp4"
```

### Quick file stats without loading data

```python
with MediaPackageReader("corpus.mediapkg") as reader:
    for stat in reader.file_stats():
        ratio = (1 - stat["compressed_bytes"] / stat["size_bytes"]) * 100
        print(f"{stat['path']:<40} {stat['rows']:>6} rows  {ratio:.0f}% compressed")
```

---

## 3. Validating a `.mediapkg`

### From Python

```python
from mava_exchange.validate import validate_mediapkg

result = validate_mediapkg("corpus.mediapkg")

if result.valid:
    print("Package is valid.")
else:
    print(result.summary())
```

The validator checks:

- manifest structure and required fields
- every file referenced in the manifest exists in the archive
- every referenced track is defined
- `start_seconds` is non-null, non-negative, and ordered
- `end_seconds > start_seconds` for all `AnnotationSeries` rows
- dimension columns are numeric and non-null for `ObservationSeries`

Pass `strict=True` to also warn about recommended but optional fields:

```python
result = validate_mediapkg("corpus.mediapkg", strict=True)
print(result.summary())
```

### From the command line

```bash
mediapkg-validate corpus.mediapkg
mediapkg-validate corpus.mediapkg --strict
```

Exit code is `0` for valid and `1` for invalid — works in CI pipelines:

```bash
mediapkg-validate corpus.mediapkg || exit 1
```

---

## 4. Inspecting from the CLI

The `mediapkg-inspect` command gives a human-readable summary without writing
any code.

**Corpus overview:**

```bash
mediapkg-inspect corpus.mediapkg
```

```
════════════════════════════════════════════════════════════
  corpus.mediapkg
════════════════════════════════════════════════════════════

Version:     0.2
Created:     2025-08-12T10:00:00+00:00
Ontology:    http://example.org/mava/ontology#
Description: Two-video corpus
Videos:      2

Tracks:
  emotions               mava:ObservationSeries  @0.5s  [angry, happy, neutral]
  transcript             mava:AnnotationSeries
  rms_volume             mava:ObservationSeries  @0.064s  [rms]

Videos:
  video_001
    src:    https://example.org/videos/talk_001.mp4
    tracks: emotions, transcript
  video_002
    src:    https://example.org/videos/talk_002.mp4
    tracks: rms_volume, transcript

Files:
  Path                                          Rows     Raw   Compressed  Saved
  -------------------------------------------- ------  ------  ----------  -----
  video_001/emotions.parquet                      100   8.2KB      3.1KB    62%
  video_001/transcript.parquet                      3   2.1KB      1.4KB    33%
  video_002/rms_volume.parquet                    200   6.4KB      2.8KB    56%
  video_002/transcript.parquet                      3   2.1KB      1.4KB    33%
```

**Drill into a specific track:**

```bash
mediapkg-inspect corpus.mediapkg --track emotions --video video_001 --head 3
```

```
Track:   emotions  (mava:ObservationSeries)
Video:   video_001
Desc:    Face emotion probability scores from DeepFace model
Rows:    100

Columns:
  start_seconds          double[pyarrow]
  angry                  double[pyarrow]
  happy                  double[pyarrow]
  neutral                double[pyarrow]

First 3 rows:
  start_seconds     angry     happy   neutral
            0.0  0.12451  0.64231  0.23318
            0.5  0.08734  0.71204  0.20062
            1.0  0.21003  0.55891  0.23106

Dimensions:
  angry                Anger probability    [0,1]
  happy                Happiness probability  [0,1]
  neutral              Neutral expression   [0,1]
```

---

## 5. The `.mediapkg` format at a glance

A `.mediapkg` is a ZIP archive. You can always unzip it manually to inspect:

```bash
unzip -l corpus.mediapkg
# or
unzip corpus.mediapkg -d corpus_contents/
cat corpus_contents/manifest.json
```

The `manifest.json` is human-readable JSON containing all metadata, the JSON-LD
context mapping column names to the MAVA ontology, and the file inventory. See
`spec/SPEC.md` for the full format specification.

---

## Next steps

- See `examples/README.md` for the real-data example corpus and the pipeline
  that builds it (`examples/scripts/build_mediapkg.py`).
- See `spec/SPEC.md` for the full format specification.
- See `spec/mava.ttl` for the MAVA ontology and SHACL validation shapes.
