# MAVA Exchange Documentation

A lightweight interchange format for video annotations.

## What is MediaPkg?

MediaPkg (`.mediapkg`) packages video annotation data in a portable format. It
uses:

- **Parquet** for efficient columnar storage
- **JSON-LD** for semantic metadata
- **ZIP** for compression and bundling

## Quick Example

```python
from mava_exchange import MediaPackageWriter, ObservationSeries, DimensionSpec

# Define a track
emotions = ObservationSeries(
    name="emotions",
    description="Face emotions",
    sampling_interval=0.5,
    dimensions=[DimensionSpec("happy", "Happiness", "[0,1]")]
)

# Write package
with MediaPackageWriter("output.mediapkg") as w:
    w.add_video("v001", "video.mp4")
    w.add_track("v001", emotions, df)
```

[See full tutorial →](tutorial/getting-started)

## Contents

```{toctree}
:maxdepth: 2
:caption: Getting Started

tutorial/getting-started
```

```{toctree}
:maxdepth: 1
:caption: Reference Guide

reference-guide/index
```

```{toctree}
:maxdepth: 1
:caption: Specification

specification
ontology
viewer
```
