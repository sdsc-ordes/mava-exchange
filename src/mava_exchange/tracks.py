"""
Track definitions for annotation data.

A track describes one Parquet file in a .mediapkg archive.

Three types:

- **ObservationSeries** - Dense time-series (emotion scores, audio volume)
- **AnnotationSeries** - Sparse intervals with single labels (transcripts, shots)
- **AnnotationListSeries** - Sparse intervals with multiple labels (scene tags)

Example::

    from mava_exchange import ObservationSeries, DimensionSpec

    emotions = ObservationSeries(
        name="emotions",
        description="Face emotion scores",
        sampling_interval=0.5,
        dimensions=[
            DimensionSpec("happy", "Happiness", "[0,1]"),
            DimensionSpec("sad", "Sadness", "[0,1]")
        ]
    )
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class DimensionSpec:
    """
    Describes one measured quantity (column) within an ObservationSeries.

    The name must match the column name in the Parquet file exactly.

    Example::

        DimensionSpec("angry", "Anger probability", "[0,1]")
        DimensionSpec("rms", "Audio RMS volume", ">=0")
    """
    name: str
    """Column name in Parquet file."""

    description: str = ""
    """Human-readable description of what this measures."""

    range: str = ""
    """Value range specification (e.g., "[0,1]", ">=0", "categorical")."""

    def to_dict(self) -> dict:
        """Converts to dictionary for manifest.json."""
        d = {"description": self.description}
        if self.range:
            d["range"] = self.range
        return d


@dataclass
class ObservationSeries:
    """
    Dense time-series of numeric observations sampled at regular intervals.

    Use for emotion scores, audio volume, confidence values, or any
    regularly-sampled numeric measurements.

    Each row in the Parquet file needs: start_seconds + one column per dimension.

    Example::

        emotions = ObservationSeries(
            name="emotions",
            description="Face emotion scores from DeepFace",
            sampling_interval=0.5,
            dimensions=[
                DimensionSpec("angry", "Anger probability", "[0,1]"),
                DimensionSpec("fear", "Fear probability", "[0,1]"),
                DimensionSpec("neutral", "Neutral expression", "[0,1]")
            ]
        )

        df = pd.DataFrame({
            "start_seconds": [0.0, 0.5, 1.0],
            "angry": [0.2, 0.1, 0.3],
            "fear": [0.1, 0.2, 0.1],
            "neutral": [0.7, 0.7, 0.6]
        })
    """
    name: str
    """Track name (must be unique within package)."""

    description: str
    """Human-readable description of what this track contains."""

    dimensions: list[DimensionSpec]
    """Measured quantities (columns in Parquet)."""

    sampling_interval: float | None = None
    """Seconds between samples for regularly-sampled data."""

    type: Literal["mava:ObservationSeries"] = field(
        default="mava:ObservationSeries", init=False
    )

    @property
    def columns(self) -> list[str]:
        """Returns column names."""
        return ["start_seconds"] + [d.name for d in self.dimensions]

    def to_dict(self) -> dict[str, Any]:
        """Converts to dictionary for manifest.json."""
        d: dict[str, Any] = {
            "type":        self.type,
            "description": self.description,
            "columns":     self.columns,
            "dimensions":  {dim.name: dim.to_dict() for dim in self.dimensions},
        }
        if self.sampling_interval is not None:
            d["sampling_interval_seconds"] = self.sampling_interval
        return d


@dataclass
class AnnotationSeries:
    """
    Sparse interval annotations with single-label values.

    Use for shot boundaries, transcripts, scene labels, or any annotation
    where each time segment has one string value.

    Each row in the Parquet file needs: start_seconds, end_seconds, annotations.

    Example::

        transcript = AnnotationSeries(
            name="transcript",
            description="Speech-to-text from Whisper"
        )

        df = pd.DataFrame({
            "start_seconds": [0.0, 5.2, 12.1],
            "end_seconds": [5.0, 12.0, 18.5],
            "annotations": ["Hello", "Welcome", "Let's begin"]
        })
    """
    name: str
    """Track name (must be unique within package)."""

    description: str
    """Human-readable description of what this track contains."""

    type: Literal["mava:AnnotationSeries"] = field(
        default="mava:AnnotationSeries", init=False
    )

    @property
    def columns(self) -> list[str]:
        """Returns column names."""
        return ["start_seconds", "end_seconds", "annotations"]

    def to_dict(self) -> dict:
        """Converts to dictionary for manifest.json."""
        return {
            "type":        self.type,
            "description": self.description,
            "columns":     self.columns,
        }


@dataclass
class AnnotationListSeries:
    """
    Sparse interval annotations with multiple labels per segment.

    Use for multi-label scene tags, keywords, or any annotation where
    multiple values apply simultaneously to a time segment.

    Each row in the Parquet file needs: start_seconds, end_seconds, annotations (as Python lists).

    Example::

        scene_tags = AnnotationListSeries(
            name="scene_tags",
            description="Scene classification (indoor/outdoor + natural/man-made)"
        )

        df = pd.DataFrame({
            "start_seconds": [0.0, 45.2, 78.5],
            "end_seconds": [45.2, 78.5, 120.0],
            "annotations": [
                ["outdoor", "natural"],
                ["indoor"],
                ["outdoor", "man-made"]
            ]
        })
    """
    name: str
    """Track name (must be unique within package)."""

    description: str
    """Human-readable description of what this track contains."""

    type: Literal["mava:AnnotationListSeries"] = field(
        default="mava:AnnotationListSeries", init=False
    )

    @property
    def columns(self) -> list[str]:
        """Returns column names."""
        return ["start_seconds", "end_seconds", "annotations"]

    def to_dict(self) -> dict:
        """Converts to dictionary for manifest.json."""
        return {
            "type":        self.type,
            "description": self.description,
            "columns":     self.columns,
        }


# Type alias for any kind of track
Track = ObservationSeries | AnnotationSeries | AnnotationListSeries
