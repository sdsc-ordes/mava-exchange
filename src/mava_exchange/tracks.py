"""
Track definitions — the building blocks for describing annotation data.

A Track describes the structure and meaning of one Parquet file
in a .mediapkg archive. There are two kinds:

  ObservationSeries — dense time-series of numeric values
                      sampled at regular intervals
                      e.g. emotion scores, RMS volume, dominant color

  AnnotationSeries  — sparse interval annotations
                      each row has a start, end, and a string value
                      e.g. shot boundaries, transcripts, labels
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class DimensionSpec:
    """
    Describes one measured quantity (column) within an ObservationSeries.

    The name must match the column name in the Parquet file exactly.
    """
    name:        str
    description: str = ""
    range:       str = ""   # e.g. "[0,1]", ">=0", "categorical"

    def to_dict(self) -> dict:
        d = {"description": self.description}
        if self.range:
            d["range"] = self.range
        return d


@dataclass
class ObservationSeries:
    """
    A dense time-series track of numeric observations.

    Maps to mava:ObservationSeries in the MAVA ontology.
    Each row in the Parquet file is a mava:ObservationPoint.

    Required Parquet columns:
      start_seconds  — time of observation (mava:atTime)
      <dim.name>...  — one column per declared dimension (mava:numericValue)

    Example:
        ObservationSeries(
            name="emotions",
            description="Face emotion scores from DeepFace model",
            sampling_interval=0.5,
            dimensions=[
                DimensionSpec("angry",   "Anger probability",    "[0,1]"),
                DimensionSpec("fear",    "Fear probability",     "[0,1]"),
                DimensionSpec("neutral", "Neutral expression",   "[0,1]"),
            ]
        )
    """
    name:               str
    description:        str
    dimensions:         list[DimensionSpec]
    sampling_interval:  float | None = None   # seconds between samples

    type: Literal["mava:ObservationSeries"] = field(
        default="mava:ObservationSeries", init=False
    )

    @property
    def columns(self) -> list[str]:
        return ["start_seconds"] + [d.name for d in self.dimensions]

    def to_dict(self) -> dict:
        d = {
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
    A sparse interval annotation track.

    Maps to mava:AnnotationSeries in the MAVA ontology.
    Each row in the Parquet file is a mava:AnnotationSegment.

    Required Parquet columns:
      start_seconds  — start of interval (mava:startTime)
      end_seconds    — end of interval   (mava:endTime)
      annotations    — string value      (mava:stringValue)

    Example:
        AnnotationSeries(
            name="transcript",
            description="Speech-to-text segments from Whisper",
        )
    """
    name:        str
    description: str

    type: Literal["mava:AnnotationSeries"] = field(
        default="mava:AnnotationSeries", init=False
    )

    @property
    def columns(self) -> list[str]:
        return ["start_seconds", "end_seconds", "annotations"]

    def to_dict(self) -> dict:
        return {
            "type":        self.type,
            "description": self.description,
            "columns":     self.columns,
        }


@dataclass
class AnnotationListSeries:
    """
    A sparse interval annotation track with list-valued annotations.

    Maps to mava:AnnotationListSeries in the MAVA ontology.
    Each row contains a list of strings in the annotations column.

    Required Parquet columns:
      start_seconds  — start of interval (mava:startTime)
      end_seconds    — end of interval   (mava:endTime)
      annotations    — list of strings   (Parquet LIST<STRING>)

    Use this for multi-label classifications, keyword tags, or any annotation
    where multiple values apply simultaneously to a time segment.

    Example:
        AnnotationListSeries(
            name="scene_tags",
            description="Scene classification tags (Places3: indoor/outdoor + natural/man-made)",
        )

        df = pd.DataFrame({
            "start_seconds": [0.0, 45.2, 78.5],
            "end_seconds":   [45.2, 78.5, 120.0],
            "annotations":   [
                ["outdoor", "natural"],
                ["indoor"],
                ["outdoor", "man-made"],
            ],
        })
    """
    name:        str
    description: str

    type: Literal["mava:AnnotationListSeries"] = field(
        default="mava:AnnotationListSeries", init=False
    )

    @property
    def columns(self) -> list[str]:
        return ["start_seconds", "end_seconds", "annotations"]

    def to_dict(self) -> dict:
        return {
            "type":        self.type,
            "description": self.description,
            "columns":     self.columns,
        }


# Type alias for any kind of track
Track = ObservationSeries | AnnotationSeries | AnnotationListSeries
