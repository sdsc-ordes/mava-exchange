# Reading Packages

Load and inspect `.mediapkg` files with `MediaPackageReader`.

## Basic Pattern

```python
from mava_exchange import MediaPackageReader

with MediaPackageReader("corpus.mediapkg") as r:
    # Inspect package
    print(r.video_ids)    # ['v001', 'v002']
    print(r.track_names)  # ['emotions', 'transcript']

    # Read data
    df = r.read_track("v001", "emotions")
```

## Common Tasks

### Inspect package contents

```python
with MediaPackageReader("corpus.mediapkg") as r:
    # Basic metadata
    print(r.version)      # "0.1"
    print(r.description)  # Package description

    # Available data
    print(r.video_ids)    # List all videos
    print(r.track_names)  # List all track types

    # Tracks for specific video
    tracks = r.tracks_for_video("v001")
    print(tracks)  # ['emotions', 'transcript', 'shots']
```

### Read specific tracks

```python
with MediaPackageReader("corpus.mediapkg") as r:
    # Read one track
    emotions_df = r.read_track("v001", "emotions")
    # Returns: DataFrame with columns ['start_seconds', 'happy', 'sad', ...]

    # Read all tracks for a video
    all_data = r.read_video("v001")
    # Returns: {'emotions': DataFrame, 'transcript': DataFrame, ...}
```

### Get track metadata

```python
with MediaPackageReader("corpus.mediapkg") as r:
    # Track definition
    track_def = r.track_def("emotions")
    print(track_def['type'])         # 'mava:ObservationSeries'
    print(track_def['dimensions'])   # {'happy': {...}, 'sad': {...}}

    # Video metadata
    video_meta = r.video_meta("v001")
    print(video_meta['src'])            # Video URL
    print(video_meta['duration_seconds'])  # 120.5
```

### Export as RDF

```python
from mava_exchange import MediaPackageReader

with MediaPackageReader("corpus.mediapkg") as r:
    # Export manifest as Turtle
    ttl = r.export_manifest_as_rdf(format="turtle")

    # Or as JSON-LD
    jsonld = r.export_manifest_as_rdf(format="json-ld")
```

## What You Get When Reading

| Method                             | Input                 | Output                          |
| ---------------------------------- | --------------------- | ------------------------------- |
| `read_track(video_id, track_name)` | Video ID + track name | DataFrame with track data       |
| `read_video(video_id)`             | Video ID              | Dict of {track_name: DataFrame} |
| `track_def(track_name)`            | Track name            | Dict with track definition      |
| `video_meta(video_id)`             | Video ID              | Dict with video metadata        |
| `tracks_for_video(video_id)`       | Video ID              | List of track names             |

## Class Reference

```{eval-rst}
.. currentmodule:: mava_exchange

.. autoclass:: MediaPackageReader
   :members:
   :exclude-members: __weakref__
```
