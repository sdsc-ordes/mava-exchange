# Writing Packages

Create `.mediapkg` archives with `MediaPackageWriter`.

## Basic Pattern

```python
from mava_exchange import MediaPackageWriter, ObservationSeries, DimensionSpec

# Define a track
emotions = ObservationSeries(
    name="emotions",
    description="Face emotion scores",
    sampling_interval=0.5,
    dimensions=[
        DimensionSpec("happy", "Happiness", "[0,1]"),
        DimensionSpec("sad", "Sadness", "[0,1]"),
    ]
)

# Prepare data
import pandas as pd
df = pd.DataFrame({
    "start_seconds": [0.0, 0.5, 1.0],
    "happy": [0.8, 0.7, 0.9],
    "sad": [0.2, 0.3, 0.1],
})

# Write package
with MediaPackageWriter("output.mediapkg") as w:
    w.add_video("v001", "video.mp4")
    w.add_track("v001", emotions, df)
```

## Common Tasks

### Single video with multiple tracks

```python
with MediaPackageWriter("analysis.mediapkg") as w:
    w.add_video("v001", "video.mp4")

    # Add different track types
    w.add_track("v001", emotions_track, emotions_df)
    w.add_track("v001", transcript_track, transcript_df)
    w.add_track("v001", scene_tags_track, tags_df)
```

### Multi-video corpus

```python
with MediaPackageWriter("corpus.mediapkg", description="My dataset") as w:
    # First video
    w.add_video("v001", "https://example.org/video1.mp4")
    w.add_track("v001", emotions_track, emotions_df_1)
    w.add_track("v001", transcript_track, transcript_df_1)

    # Second video
    w.add_video("v002", "https://example.org/video2.mp4")
    w.add_track("v002", emotions_track, emotions_df_2)
    w.add_track("v002", transcript_track, transcript_df_2)
```

### Add video metadata

```python
with MediaPackageWriter("output.mediapkg") as w:
    w.add_video(
        video_id="v001",
        src="video.mp4",
        title="Opening Keynote",
        duration_seconds=3600.5
    )
    w.add_track("v001", emotions_track, df)
```

### Reusing track definitions across videos

```python
# Define track once
emotions = ObservationSeries(
    name="emotions",
    description="Face emotions",
    sampling_interval=0.5,
    dimensions=[DimensionSpec("happy", "Happiness", "[0,1]")]
)

with MediaPackageWriter("corpus.mediapkg") as w:
    # Use same track definition for multiple videos
    w.add_video("v001", "video1.mp4")
    w.add_track("v001", emotions, emotions_df_1)

    w.add_video("v002", "video2.mp4")
    w.add_track("v002", emotions, emotions_df_2)  # Same track definition
```

## What Gets Written

When you call `write()` (or exit the context manager), a ZIP file is created
with:

```
output.mediapkg
├── manifest.json          # Package metadata and track definitions
└── v001/
    ├── emotions.parquet   # Track data as Parquet files
    └── transcript.parquet
```

The manifest contains:

- Package version and description
- Video metadata (src, title, duration)
- Track definitions (type, columns, dimensions)
- File paths mapping videos to their tracks

## Class Reference

```{eval-rst}
.. currentmodule:: mava_exchange

.. autoclass:: MediaPackageWriter
   :members:
   :exclude-members: __weakref__
```
