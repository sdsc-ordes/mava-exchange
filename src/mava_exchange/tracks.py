"""
Track definitions for annotation data.

A track describes one Parquet file in a .mediapkg archive.

Four types:

- **ObservationSeries** - Dense time-series (emotion scores, audio volume)
- **AnnotationSeries** - Sparse intervals with single labels (transcripts, shots)
- **AnnotationListSeries** - Sparse intervals with multiple labels (scene tags)
- **RegionSeries** - Spatial detections / bounding boxes, long format (faces, objects)

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

import copy
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

logger = logging.getLogger(__name__)


# The relationship fields (parent/derived_from/method) are repeated per type
# rather than inherited from a base class: the shared *logic* lives in
# _relations() below; a base would force @dataclass(kw_only=True) and still need
# the Track union for type-narrowing, so it isn't worth it.
def _relations(track: Any) -> dict[str, Any]:
    """Optional hierarchy / provenance edges, emitted only when present."""
    d: dict[str, Any] = {}
    if track.parent is not None:
        d["parent"] = track.parent
    if track.derived_from:
        d["derived_from"] = list(track.derived_from)
    if track.method is not None:
        d["method"] = track.method
    return d

def _check_tool_data_model(value: Any) -> dict[str, dict[str, Any]] | None:
    """Validate a tool_data_model and return an independent copy.

    Names must be non-empty strings (empty ones are dropped with a warning);
    each value must be an object. Serialisation concerns live in the writer.
    """
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise TypeError(f"tool_data_model must be a mapping, got {type(value).__name__}")
    result = {}
    for name, entry in value.items():
        if not isinstance(name, str):
            raise TypeError(f"tool_data_model keys must be strings, got {type(name).__name__}")
        if not name.strip():
            logger.warning("Dropping tool_data_model entry with an empty tool name.")
            continue
        if not isinstance(entry, Mapping):
            raise TypeError(f"tool_data_model[{name!r}] must be an object, got {type(entry).__name__}")
        result[name] = copy.deepcopy(dict(entry))
    return result or None

def _tool_data_model(track: Any, d: dict[str, Any]) -> dict[str, Any]:
    """Add the optional tool-specific data model, when the track declares one.

    Shared by all four series types. Deep-copies the value so a caller
    changing the manifest cannot reach back into the track definition.
    """
    if track.tool_data_model:
        d["tool_data_model"] = copy.deepcopy(track.tool_data_model)
    return d

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

    parent: str | None = None
    """Containment parent track name (None if top-level)."""

    derived_from: list[str] | None = None
    """Source track names this track is derived from (provenance)."""

    method: str | None = None
    """Derivation method (e.g. 'argmax', 'cluster_to_scalar', 'aggregate_scalar')."""

    tool_data_model: dict[str, dict[str, Any]] | None = None
    """Tool-internal data model(s) this series was produced from, keyed by tool name."""

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
            **_relations(self),
            "columns":     self.columns,
            "dimensions":  {dim.name: dim.to_dict() for dim in self.dimensions},
        }
        if self.sampling_interval is not None:
            d["sampling_interval_seconds"] = self.sampling_interval
        d = _tool_data_model(self, d)
        return d

    def __post_init__(self) -> None:
            self.tool_data_model = _check_tool_data_model(self.tool_data_model)


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

    parent: str | None = None
    """Containment parent track name (None if top-level)."""

    derived_from: list[str] | None = None
    """Source track names this track is derived from (provenance)."""

    method: str | None = None
    """Derivation method (e.g. 'argmax', 'cluster_to_scalar', 'aggregate_scalar')."""

    tool_data_model: dict[str, dict[str, Any]] | None = None
    """Tool-internal data model(s) this series was produced from, keyed by tool name."""

    type: Literal["mava:AnnotationSeries"] = field(
        default="mava:AnnotationSeries", init=False
    )

    @property
    def columns(self) -> list[str]:
        """Returns column names."""
        return ["start_seconds", "end_seconds", "annotations"]

    def to_dict(self) -> dict:
        """Converts to dictionary for manifest.json."""
        d: dict[str, Any] = {
            "type":        self.type,
            "description": self.description,
            **_relations(self),
            "columns":     self.columns,
            }

        return _tool_data_model(self, d)

    def __post_init__(self) -> None:
            self.tool_data_model = _check_tool_data_model(self.tool_data_model)


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

    parent: str | None = None
    """Containment parent track name (None if top-level)."""

    derived_from: list[str] | None = None
    """Source track names this track is derived from (provenance)."""

    method: str | None = None
    """Derivation method (e.g. 'argmax', 'cluster_to_scalar', 'aggregate_scalar')."""

    tool_data_model: dict[str, dict[str, Any]] | None = None
    """Tool-internal data model(s) this series was produced from, keyed by tool name."""

    type: Literal["mava:AnnotationListSeries"] = field(
        default="mava:AnnotationListSeries", init=False
    )

    @property
    def columns(self) -> list[str]:
        """Returns column names."""
        return ["start_seconds", "end_seconds", "annotations"]

    def to_dict(self) -> dict:
        """Converts to dictionary for manifest.json."""
        d: dict[str, Any] = {
            "type":        self.type,
            "description": self.description,
            **_relations(self),
            "columns":     self.columns,
            }

        return _tool_data_model(self, d)

    def __post_init__(self) -> None:
            self.tool_data_model = _check_tool_data_model(self.tool_data_model)


@dataclass
class RegionSeries:
    """
    Spatial detections — one row per detection (long format).

    Use for bounding boxes (faces, objects). Geometry is normalized to [0,1] of
    the frame with a top-left origin (``x``, ``y``, ``w``, ``h``) plus a
    detection score; each row also carries an identity (``cluster_id``) and an
    optional human ``label``.

    Each row in the Parquet file needs: start_seconds + one column per dimension
    (x, y, w, h, det_score) + cluster_id + label.

    Example::

        faces = RegionSeries(
            name="face_regions",
            description="Per-frame face bounding boxes",
            sampling_interval=0.5,
            dimensions=[
                DimensionSpec("x", "Box left edge (normalized)", "[0,1]"),
                DimensionSpec("y", "Box top edge (normalized)", "[0,1]"),
                DimensionSpec("w", "Box width (normalized)", "[0,1]"),
                DimensionSpec("h", "Box height (normalized)", "[0,1]"),
                DimensionSpec("det_score", "Detection confidence", "[0,1]"),
            ],
        )
    """
    name: str
    """Track name (must be unique within package)."""

    description: str
    """Human-readable description of what this track contains."""

    dimensions: list[DimensionSpec]
    """Geometry + score columns (x, y, w, h, det_score)."""

    sampling_interval: float | None = None
    """Seconds between samples for regularly-sampled detections."""

    parent: str | None = None
    """Containment parent track name (None if top-level)."""

    derived_from: list[str] | None = None
    """Source track names this track is derived from (provenance)."""

    method: str | None = None
    """Derivation method (e.g. 'argmax', 'cluster_to_scalar', 'aggregate_scalar')."""

    tool_data_model: dict[str, dict[str, Any]] | None = None
    """Tool-internal data model(s) this series was produced from, keyed by tool name."""

    type: Literal["mava:RegionSeries"] = field(
        default="mava:RegionSeries", init=False
    )

    @property
    def columns(self) -> list[str]:
        """Returns column names."""
        return ["start_seconds"] + [d.name for d in self.dimensions] + ["cluster_id", "label"]

    def to_dict(self) -> dict[str, Any]:
        """Converts to dictionary for manifest.json."""
        d: dict[str, Any] = {
            "type":             self.type,
            "description":      self.description,
            **_relations(self),
            "columns":          self.columns,
            "dimensions":       {dim.name: dim.to_dict() for dim in self.dimensions},
        }
        if self.sampling_interval is not None:
            d["sampling_interval_seconds"] = self.sampling_interval
        return _tool_data_model(self, d)

    def __post_init__(self) -> None:
        self.tool_data_model = _check_tool_data_model(self.tool_data_model)


# Type alias for any kind of track
Track = ObservationSeries | AnnotationSeries | AnnotationListSeries | RegionSeries
