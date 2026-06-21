"""Roundtrip tests for the v0.2 additions.

Covers the new read paths directly (write -> read), without depending on
validate_mediapkg — the validator gains RegionSeries support in the formal v0.2
spec step. These guard:

  - RegionSeries (long-format spatial detections, nullable label, int cluster_id)
  - hierarchy / provenance edges (parent, derived_from, method) on any track
  - video frame metadata (width / height / fps)
  - backward compatibility: relation fields are omitted when unset
"""
from __future__ import annotations

import pandas as pd

from mava_exchange import (
    AnnotationSeries,
    DimensionSpec,
    MediaPackageReader,
    MediaPackageWriter,
    ObservationSeries,
    RegionSeries,
)


def _write(pkg_path, video_kwargs, *tracks_and_dfs):
    with MediaPackageWriter(pkg_path) as w:
        w.add_video("v1", "https://example.org/v1.mp4", **video_kwargs)
        for track, df in tracks_and_dfs:
            w.add_track("v1", track, df)
    return pkg_path


def test_region_series_roundtrip(tmp_path, region_track, region_df):
    pkg = _write(tmp_path / "r.mediapkg", {}, (region_track, region_df))
    with MediaPackageReader(pkg) as r:
        track = r.track_def("face_regions")
        assert isinstance(track, RegionSeries)
        assert track.coordinate_space == "normalized"
        assert track.sampling_interval == 0.5
        assert track.columns == [
            "start_seconds", "x", "y", "w", "h", "det_score", "cluster_id", "label",
        ]
        df = r.read_track("v1", "face_regions")

    assert list(df.columns) == region_track.columns
    assert len(df) == len(region_df)
    # long format: two detections share start_seconds == 0.0
    assert (df["start_seconds"] == 0.0).sum() == 2
    # integer cluster ids preserved
    assert df["cluster_id"].tolist() == [0, 1, 0, 1, 2]
    # nullable label: known cluster, unknown name -> null
    assert df["label"].isna().sum() == 1
    assert df.loc[0, "label"] == "Alice"


def test_relationship_fields_roundtrip(tmp_path):
    shots = AnnotationSeries(name="shots", description="Shot segmentation")
    shot_sizes = AnnotationSeries(
        name="shot_sizes", description="Dominant shot size per shot",
        parent="shots", derived_from=["close_up", "long_shot"], method="argmax",
    )
    interval = pd.DataFrame({
        "start_seconds": [0.0, 2.0],
        "end_seconds": [2.0, 4.0],
        "annotations": ["", ""],
    })
    sizes = pd.DataFrame({
        "start_seconds": [0.0, 2.0],
        "end_seconds": [2.0, 4.0],
        "annotations": ["Close-Up", "Long Shot"],
    })
    pkg = _write(tmp_path / "h.mediapkg", {}, (shots, interval), (shot_sizes, sizes))

    with MediaPackageReader(pkg) as r:
        parent = r.track_def("shots")
        child = r.track_def("shot_sizes")

    assert parent.parent is None
    assert parent.derived_from is None
    assert parent.method is None
    assert child.parent == "shots"
    assert child.derived_from == ["close_up", "long_shot"]
    assert child.method == "argmax"


def test_derived_from_on_observation_series(tmp_path):
    presence = ObservationSeries(
        name="joanne", description="Presence score", sampling_interval=0.5,
        dimensions=[DimensionSpec("score", "Presence", "[0,1]")],
        parent="person_identification", derived_from=["face_regions"],
        method="cluster_to_scalar",
    )
    df = pd.DataFrame({"start_seconds": [0.0, 0.5], "score": [0.6, 0.4]})
    pkg = _write(tmp_path / "d.mediapkg", {}, (presence, df))

    with MediaPackageReader(pkg) as r:
        t = r.track_def("joanne")
    assert t.parent == "person_identification"
    assert t.derived_from == ["face_regions"]
    assert t.method == "cluster_to_scalar"


def test_video_frame_metadata_roundtrip(tmp_path, region_track, region_df):
    pkg = _write(
        tmp_path / "v.mediapkg",
        {"width": 3840, "height": 2160, "fps": 25.0, "duration_seconds": 1203.46},
        (region_track, region_df),
    )
    with MediaPackageReader(pkg) as r:
        meta = r.video_meta("v1")
    assert meta["width"] == 3840
    assert meta["height"] == 2160
    assert meta["fps"] == 25.0
    assert meta["duration_seconds"] == 1203.46


def test_relations_omitted_when_unset(tmp_path, emotions_track, emotions_df):
    """Backward compatibility: a track with no edges emits no relation keys."""
    pkg = _write(tmp_path / "e.mediapkg", {}, (emotions_track, emotions_df))
    with MediaPackageReader(pkg) as r:
        entry = r.manifest["tracks"]["emotions"]
    assert "parent" not in entry
    assert "derived_from" not in entry
    assert "method" not in entry
