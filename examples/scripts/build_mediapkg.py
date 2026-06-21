"""
Transform the declarative example INPUT into a `.mediapkg` archive.

Reads every video folder under `examples/input/<video>/`:

    <video>/
      video.yml        # id, src, title, width, height, fps, duration, segment
      tracks.yml       # per-track: type, parent, derived_from, method, dimensions
      <track>.tsv      # one TSV per track (filename == track name)

and writes `examples/output/corpus.mediapkg`.

This is the generic counterpart to `extract_segment.py`: extract builds the
input from raw platform data; this builds the package from the input. It is the
single, uniform path for every video (no per-video hardcoding).

Run:
    uv run examples/scripts/build_mediapkg.py
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from mava_exchange import (
    AnnotationListSeries,
    AnnotationSeries,
    DimensionSpec,
    MediaPackageWriter,
    ObservationSeries,
    RegionSeries,
)

INPUT_ROOT = Path(__file__).resolve().parents[1] / "input"
OUT_PATH = Path(__file__).resolve().parents[1] / "output" / "corpus.mediapkg"

# Fixed timestamp so regenerating the corpus is byte-reproducible.
FIXED_CREATED = datetime(2025, 1, 1, tzinfo=timezone.utc)

NUM_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


# ─────────────────────────────────────────────
# Track construction from tracks.yml metadata
# ─────────────────────────────────────────────


def _relations(meta: dict) -> dict:
    return {k: meta[k] for k in ("parent", "derived_from", "method") if k in meta}


def _dims(meta: dict) -> list[DimensionSpec]:
    return [
        DimensionSpec(
            name=n, description=dm.get("description", ""), range=dm.get("range", "")
        )
        for n, dm in meta.get("dimensions", {}).items()
    ]


def build_track(name: str, meta: dict):
    t = meta["type"]
    if t == "mava:ObservationSeries":
        return ObservationSeries(
            name=name,
            description=meta.get("description", ""),
            dimensions=_dims(meta),
            sampling_interval=meta.get("sampling_interval_seconds"),
            **_relations(meta),
        )
    if t == "mava:AnnotationSeries":
        return AnnotationSeries(
            name=name, description=meta.get("description", ""), **_relations(meta)
        )
    if t == "mava:AnnotationListSeries":
        return AnnotationListSeries(
            name=name, description=meta.get("description", ""), **_relations(meta)
        )
    if t == "mava:RegionSeries":
        return RegionSeries(
            name=name,
            description=meta.get("description", ""),
            dimensions=_dims(meta),
            sampling_interval=meta.get("sampling_interval_seconds"),
            coordinate_space=meta.get("coordinate_space", "normalized"),
            **_relations(meta),
        )
    raise ValueError(f"Unknown track type {t!r} for track {name!r}")


# ─────────────────────────────────────────────
# TSV → DataFrame loaders (one per track type)
# ─────────────────────────────────────────────


def _annotation_to_str(val: object) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    if s.startswith("["):
        try:
            arr = json.loads(s)
            if isinstance(arr, list):
                return ", ".join(str(x) for x in arr)
        except json.JSONDecodeError:
            pass
    return s


def _annotation_to_list(val: object) -> list[str]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []
    s = str(val).strip()
    if s.startswith("["):
        try:
            arr = json.loads(s)
            if isinstance(arr, list):
                return [str(x) for x in arr]
        except json.JSONDecodeError:
            pass
    return [s] if s else []


def load_track_df(track, tsv: Path) -> pd.DataFrame:
    raw = pd.read_csv(tsv, sep="\t", dtype=str)
    start = pd.to_numeric(raw["start in seconds"])

    if isinstance(track, ObservationSeries):
        out = pd.DataFrame({"start_seconds": start})
        dims = [d.name for d in track.dimensions]
        if len(dims) == 1:
            out[dims[0]] = pd.to_numeric(raw["annotations"], errors="coerce")
        else:  # vector packed into the annotations cell, e.g. "[r g b]"
            parsed = raw["annotations"].apply(
                lambda v: [float(x) for x in NUM_RE.findall(v or "")]
            )
            for i, dim in enumerate(dims):
                out[dim] = parsed.apply(
                    lambda xs, i=i: xs[i] if i < len(xs) else float("nan")
                )
        return out

    if isinstance(track, RegionSeries):
        out = pd.DataFrame({"start_seconds": start})
        for dim in (d.name for d in track.dimensions):
            out[dim] = pd.to_numeric(raw[dim], errors="coerce")
        out["cluster_id"] = pd.to_numeric(raw["cluster_id"], errors="coerce").astype(
            "Int64"
        )
        out["label"] = raw["label"].where(
            raw["label"].astype(str).str.len() > 0, other=None
        )
        return out

    # AnnotationSeries / AnnotationListSeries — interval rows
    end = start + pd.to_numeric(raw["duration in seconds"])
    annotations = raw.get("annotations", pd.Series([""] * len(raw)))
    conv = (
        _annotation_to_list
        if isinstance(track, AnnotationListSeries)
        else _annotation_to_str
    )
    return pd.DataFrame(
        {
            "start_seconds": start,
            "end_seconds": end,
            "annotations": annotations.apply(conv),
        }
    )


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    video_dirs = sorted(p for p in INPUT_ROOT.iterdir() if p.is_dir())

    with MediaPackageWriter(
        OUT_PATH,
        description="Example corpus: real segments (tagesschau hierarchy, "
        "silent_child face regions).",
        created=FIXED_CREATED,
    ) as writer:
        for vdir in video_dirs:
            video = yaml.safe_load((vdir / "video.yml").read_text())
            tracks_meta = yaml.safe_load((vdir / "tracks.yml").read_text())
            vid = video["id"]
            writer.add_video(
                vid,
                src=video["src"],
                title=video.get("title"),
                duration_seconds=video.get("duration_seconds"),
                width=video.get("width"),
                height=video.get("height"),
                fps=video.get("fps"),
            )
            print(f"{vid}: {len(tracks_meta)} tracks")
            for name, meta in tracks_meta.items():
                track = build_track(name, meta)
                df = load_track_df(track, vdir / f"{name}.tsv")
                writer.add_track(vid, track, df)
                print(
                    f"   {name:<22} {meta['type'].split(':')[-1]:<20} {len(df):>5} rows"
                )

    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
