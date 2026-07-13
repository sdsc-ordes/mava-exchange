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

### 1.5 Spatial detections — `RegionSeries`

A `RegionSeries` stores bounding boxes in **long format**: one row per
detection, so several rows can share the same `start_seconds`. The geometry
columns (`x`, `y`, `w`, `h`) and `det_score` are declared as dimensions, just
like an `ObservationSeries`; `cluster_id` (machine cluster) and a nullable
`label` (human identity) are added automatically.

```python
from mava_exchange import RegionSeries, DimensionSpec

faces = RegionSeries(
    name="face_regions",
    description="Per-frame face bounding boxes, normalized to [0,1] of the frame.",
    sampling_interval=0.5,
    dimensions=[
        DimensionSpec("x",         "Box left edge (normalized)", "[0,1]"),
        DimensionSpec("y",         "Box top edge (normalized)",  "[0,1]"),
        DimensionSpec("w",         "Box width (normalized)",     "[0,1]"),
        DimensionSpec("h",         "Box height (normalized)",    "[0,1]"),
        DimensionSpec("det_score", "Detection confidence",       "[0,1]"),
    ],
)

# One row per detection. cluster_id is an integer; label may be None.
faces_df = pd.DataFrame({
    "start_seconds": [0.0,  0.0,  0.5],   # two detections at t=0.0
    "x":          [0.10, 0.60, 0.11],
    "y":          [0.20, 0.18, 0.21],
    "w":          [0.15, 0.14, 0.15],
    "h":          [0.30, 0.28, 0.30],
    "det_score":  [0.95, 0.88, 0.93],
    "cluster_id": pd.array([0, 1, 0], dtype="Int64"),
    "label":      ["Alice", None, "Alice"],
})

with MediaPackageWriter("faces.mediapkg") as writer:
    writer.add_video("video_001", "https://example.org/videos/talk.mp4",
                     width=3840, height=2160, fps=25.0)
    writer.add_track("video_001", faces, faces_df)
```

Geometry is always **normalized** to `[0,1]` of the frame (top-left origin), so
`x`/`y`/`w`/`h` must lie in `[0,1]`; absolute pixels are recoverable from the
video's `width`/`height`. `label` is nullable and need not be unique — several
clusters may share one label.

### 1.6 Declaring relationships between tracks

Every track type accepts two independent, optional edges:

- **`parent`** — containment: the track this one lives _under_ (a single track
  name; the parent graph must be acyclic).
- **`derived_from`** + **`method`** — provenance: the source tracks this one is
  _computed from_ (a list), and how (`method` is required when `derived_from` is
  set, e.g. `"argmax"`, `"cluster_to_scalar"`, `"aggregate_scalar"`).

A track may have both at once — e.g. an aggregation that _lives under_
`aggregations` yet is _computed from_ several sources:

```python
shots = AnnotationSeries(name="shots", description="Shot segmentation")

# Contained in `shots`, and derived (argmax) from the five shot-size scores:
shot_sizes = AnnotationSeries(
    name="shot_sizes",
    description="Dominant shot size per shot",
    parent="shots",
    derived_from=["extreme_close_up", "close_up", "medium", "full", "long"],
    method="argmax",
)

# A per-person presence score, derived from the face detections:
person_alice = ObservationSeries(
    name="person_alice",
    description="Alice presence score",
    sampling_interval=0.5,
    dimensions=[DimensionSpec("presence", "Presence score", "[0,1]")],
    parent="person_identification",
    derived_from=["face_regions"],
    method="cluster_to_scalar",
)
```

These edges are written into `manifest.json` (and exported to RDF as
`mava:hasParent` / `mava:derivedFrom` / `mava:derivationMethod`). The validator
checks that every referenced track exists, that `method` is present whenever
`derived_from` is, and that the `parent` graph is acyclic.

---

## 2. Reading a `.mediapkg`

Use `MediaPackageReader` to read a package. Use it as a context manager to
ensure the file is closed properly. To run the examples below you can use the
`corpus.mediapkg` under `examples/output` from the `mava-exchange` repository.

```python
from mava_exchange import MediaPackageReader

with MediaPackageReader("corpus.mediapkg") as reader:

    # What's in this package?
    print(reader.video_ids)       # ['silent_child', 'tagesschau']
    print(reader.track_names)     # ['shots', 'person_identification', ... ]

    # Which tracks does a specific video have?
    print(reader.tracks_for_video("silent_child")) # ['shots', 'person_identification', ... ]
    print(reader.tracks_for_video("tagesschau"))   # ['shots', 'shot_density', ...]

    # Read a track into a DataFrame
    df = reader.read_track("tagesschau", "dominant_colors")
    print(df.head())
    # start_seconds         r         g         b
    # 0            0.0  0.070001  0.121187  0.178580
    # 1            0.5  0.069677  0.118246  0.171448
    # 2            1.0  0.070119  0.118845  0.172824
    # 3            1.5  0.070927  0.120733  0.176737
    # 4            2.0  0.071317  0.123408  0.183246

    # Read all tracks for a video at once
    tracks = reader.read_video("tagesschau")
    # tracks == {"emotions": df, "transcript": df}

    # Get track definition (reconstructed as a typed object)
    track = reader.track_def("dominant_colors")
    print(track.sampling_interval)        # 0.5
    print([d.name for d in track.dimensions])  # ['r', 'g', 'b']

    # Get video metadata
    meta = reader.video_meta("tagesschau")
    print(meta["src"])  # "tagesschau.mp4"
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
Created:     2025-01-01T00:00:00+00:00
Ontology:    http://example.org/mava/ontology#
Description: Example corpus: real segments (tagesschau hierarchy, silent_child face regions).
Videos:      2

Tracks:
  shots                  mava:AnnotationSeries
  person_identification  mava:AnnotationSeries
  joanne                 mava:ObservationSeries  @0.5s  [score]
  paul                   mava:ObservationSeries  @0.5s  [score]
  face_regions           mava:RegionSeries  @0.5s  [x, y, w, h, det_score]
  shot_density           mava:ObservationSeries  @0.1s  [density]
  dominant_colors        mava:ObservationSeries  @0.5s  [r, g, b]
  shot_sizes             mava:AnnotationSeries
  close_up               mava:ObservationSeries  @0.2s  [score]
  medium_shot            mava:ObservationSeries  @0.2s  [score]
  long_shot              mava:ObservationSeries  @0.2s  [score]
  whisper_transcript     mava:AnnotationSeries
  rms_volume             mava:ObservationSeries  @0.064s  [rms]
  face_emotions          mava:AnnotationSeries
  happy                  mava:ObservationSeries  @0.5s  [score]
  sad                    mava:ObservationSeries  @0.5s  [score]
  neutral                mava:ObservationSeries  @0.5s  [score]
  anchor_daubner         mava:ObservationSeries  @0.5s  [score]
  shots_modified         mava:AnnotationSeries

Videos:
  silent_child
    src:    silent_child.mp4
    tracks: shots, person_identification, joanne, paul, face_regions
  tagesschau
    src:    tagesschau.mp4
    tracks: shots, shot_density, dominant_colors, shot_sizes, close_up, medium_shot, long_shot, whisper_transcript, rms_volume, face_emotions, happy, sad, neutral, anchor_daubner, shots_modified

Files:
  Path                                            Rows         Raw  Compressed   Saved
  --------------------------------------------- ------  ----------  ----------  ------
  silent_child/shots.parquet                         6       2.4KB       1.2KB     51%
  silent_child/person_identification.parquet         6       2.4KB       1.2KB     51%
  silent_child/joanne.parquet                       41       2.3KB       1.4KB     40%
  silent_child/paul.parquet                         41       2.3KB       1.4KB     40%
  silent_child/face_regions.parquet                 46       6.8KB       3.4KB     50%
  tagesschau/shots.parquet                          11       2.4KB       1.2KB     49%
  tagesschau/shot_density.parquet                  901      15.6KB      11.6KB     25%
  tagesschau/dominant_colors.parquet               181       8.2KB       5.6KB     32%
  tagesschau/shot_sizes.parquet                     10       2.6KB       1.3KB     50%
  tagesschau/close_up.parquet                      451       7.8KB       5.1KB     34%
  tagesschau/medium_shot.parquet                   451       8.0KB       5.4KB     33%
  tagesschau/long_shot.parquet                     451       6.6KB       4.3KB     35%
  tagesschau/whisper_transcript.parquet             18       4.0KB       2.2KB     45%
  tagesschau/rms_volume.parquet                   1407      22.3KB      15.3KB     31%
  tagesschau/face_emotions.parquet                   9       2.5KB       1.3KB     50%
  tagesschau/happy.parquet                         155       3.7KB       2.3KB     37%
  tagesschau/sad.parquet                           155       3.8KB       2.5KB     36%
  tagesschau/neutral.parquet                       155       3.8KB       2.5KB     36%
  tagesschau/anchor_daubner.parquet                155       3.9KB       2.5KB     36%
  tagesschau/shots_modified.parquet                 11       2.4KB       1.2KB     49%

  TOTAL                                                    114.0KB      72.8KB     36%
```

**Drill into a specific track:**

```bash
mediapkg-inspect corpus.mediapkg --track face_emotions --video tagesschau --head 3
```

```
════════════════════════════════════════════════════════════
  corpus.mediapkg
════════════════════════════════════════════════════════════


Track:   dominant_colors  (mava:ObservationSeries)
Video:   tagesschau
Desc:    Dominant Color(s)
Rows:    181

Columns:
  start_seconds          float64
  r                      float64
  g                      float64
  b                      float64

First 3 rows:
 start_seconds        r        g        b
           0.0 0.070001 0.121187 0.178580
           0.5 0.069677 0.118246 0.171448
           1.0 0.070119 0.118845 0.172824

Dimensions:
  r                    Component r  [0,1]
  g                    Component g  [0,1]
  b                    Component b  [0,1]
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
