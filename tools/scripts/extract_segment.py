"""
Build example INPUT from short segments of real platform exports.

This is a one-off data-preparation script, NOT part of the library. It reads the
raw platform data (gitignored, under `data/<source>/`) and emits small, committed
example inputs under `examples/input/<source>/`.

Two complementary real examples are produced:

  - `tagesschau`  — a rich HIERARCHY example (Shots ⊃ Shot Sizes ⊃ …, audio under
    the transcript, Face Emotions ⊃ 7 emotions, a named anchor, a human-edited
    second segmentation). Derivations: argmax / cluster_to_scalar / manual.
    No bounding boxes (this export has none).
  - `silent_child` — the SPATIAL example: real face bounding boxes
    (`RegionSeries`) with a resolved `cluster_id` per detection, plus a little
    hierarchy context (person presence derived from the regions).

The track tree is built faithfully from each export's `timelines.yml`
(`parent` ← `parent_id`, type ← node type). A small per-source overlay adds the
`derived_from` / `method` edges that the raw dumps don't record explicitly.

Each track's row data is written to `<track-slug>.tsv`, so the downstream
transform can wire track → file 1:1 by name.

It does NOT produce a `.mediapkg` — that transform is the next step.

Run:
    just extract-examples          # or: uv run tools/scripts/extract_segment.py
"""

from __future__ import annotations

import csv
import io
import itertools
import re
import zipfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
OUT_ROOT = REPO / "examples" / "input"

# Dense single-value tracks: a nicer dimension/column name than the default.
DIM_NAME = {
    "rms_volume": "rms",
    "shot_density": "density",
    "video_brightness": "brightness",
}
DIM_RANGE = {"rms": ">=0"}
DEFAULT_DIM = "score"

# Minimum component count for an annotation value to be treated as a vector.
VECTOR_MIN = 2
# Component count that maps to named RGB dimensions.
RGB_COMPONENTS = 3

# ─────────────────────────────────────────────
# Per-source configuration
# ─────────────────────────────────────────────

SOURCES = {
    "tagesschau": {
        "window": (0.0, 90.0),
        "title": "Tagesschau (segment)",
        "include": None,  # all timeline nodes that have a TSV
        # slug -> (sources, method)
        "derivations": {
            "shot_sizes": (
                [
                    "extreme_close_up",
                    "close_up",
                    "medium_shot",
                    "full_shot",
                    "long_shot",
                ],
                "argmax",
            ),
            "face_emotions": (
                ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"],
                "argmax",
            ),
            "shots_modified": (["shots"], "manual"),
        },
        "regions": None,
    },
    "silent_child": {
        "window": (85.0, 105.2),
        "title": "The Silent Child (segment)",
        # Only Joanne and Paul actually appear in this window; the other named
        # people (Libby, Susanne, Paul's mother) stay near zero, so they're left out.
        "include": ["Shots", "Person Identification", "Joanne", "Paul"],
        # Each named person is a cluster_to_scalar presence series. The source
        # cluster isn't recorded in the export, so derived_from points at the
        # face_regions track (the spatial layer the identities come from).
        "derivations": {
            person: (["face_regions"], "cluster_to_scalar")
            for person in ("joanne", "paul")
        },
        "regions": {
            "bboxes_yml": "data/1afa5e418af4474485b7ae9b1d6b19bc/bboxes_data.yml",
            "cluster_zip": "data/1434b446fc1e4bffb938dc61d6be8507.zip",
            "track": "face_regions",
        },
    },
}


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────


def slug(name: str) -> str:
    s = name.lower().replace("(s)", "s")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def numbers(val: str | None) -> list[str]:
    return re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", val or "")


def read_tsv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return list(reader.fieldnames or []), list(reader)


def write_tsv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    # An empty trailing column (e.g. a blank `label` / `annotations`) leaves the
    # line ending in a tab; strip per-line trailing whitespace so the output is
    # already clean and the trailing-whitespace pre-commit hook is a no-op.
    cleaned = "".join(line.rstrip() + "\n" for line in buf.getvalue().splitlines())
    path.write_text(cleaned)


def unzip_yaml(zip_path: Path, member: str) -> dict:
    with zipfile.ZipFile(zip_path) as zf:
        return yaml.safe_load(zf.read(member))


# ─────────────────────────────────────────────
# Track building
# ─────────────────────────────────────────────


def dense_dims(annotation_value: str) -> dict[str, dict]:
    """Decide ObservationSeries dimensions from a sample annotation value."""
    nums = numbers(annotation_value)
    if len(nums) >= VECTOR_MIN:  # vector (e.g. dominant color "[r g b]")
        names = (
            ["r", "g", "b"]
            if len(nums) == RGB_COMPONENTS
            else [f"c{i}" for i in range(len(nums))]
        )
        return {n: {"description": f"Component {n}", "range": "[0,1]"} for n in names}
    return {}  # scalar — caller fills the single dim


def detect_interval(rows: list[dict]) -> float | None:
    """Median gap between consecutive samples — the real sampling interval."""
    ts = sorted(float(r["start in seconds"]) for r in rows)
    diffs = sorted(round(b - a, 4) for a, b in itertools.pairwise(ts) if b > a)
    return diffs[len(diffs) // 2] if diffs else None


def slice_rows(
    rows: list[dict], window: tuple[float, float], *, interval: bool
) -> list[dict]:
    w0, w1 = window
    out = []
    for r in rows:
        start = float(r["start in seconds"])
        if interval:
            if w0 <= start < w1:
                out.append(r)
        elif w0 <= start <= w1:
            out.append(r)
    return out


def build_from_timelines(cfg: dict, raw: Path, tsv: Path, out: Path) -> dict[str, dict]:
    timelines = yaml.safe_load((raw / "timelines.yml").read_text())
    timelines = (
        timelines
        if isinstance(timelines, list)
        else timelines.get("timelines", timelines)
    )
    by_id = {t["id"]: t for t in timelines}
    include = cfg["include"]
    window = cfg["window"]
    tracks: dict[str, dict] = {}

    for node in timelines:
        name = node["name"]
        if include is not None and name not in include:
            continue
        src_tsv = tsv / f"{name}.tsv"
        if not src_tsv.exists():
            print(f"  skip {name!r}: no TSV (e.g. numpy-only result)")
            continue

        node_slug = slug(name)
        parent_id = node.get("parent_id")
        parent = slug(by_id[parent_id]["name"]) if parent_id in by_id else None
        ntype = node.get("type")
        interval = ntype in ("ANNOTATION", "TRANSCRIPT")

        _fields, rows = read_tsv(src_tsv)
        kept = slice_rows(rows, window, interval=interval)
        # Rebase to 0 (so a clip cut at the window start lines up) and keep only
        # the columns the build step uses (drop absolute hh:mm:ss timecodes).
        off = window[0]
        if interval:
            out_fields = ["start in seconds", "duration in seconds", "annotations"]
            out_rows = [
                {
                    "start in seconds": f"{float(r['start in seconds']) - off:g}",
                    "duration in seconds": r.get("duration in seconds", ""),
                    "annotations": r.get("annotations", "") or "",
                }
                for r in kept
            ]
        else:
            out_fields = ["start in seconds", "annotations"]
            out_rows = [
                {
                    "start in seconds": f"{float(r['start in seconds']) - off:g}",
                    "annotations": r.get("annotations", "") or "",
                }
                for r in kept
            ]
        write_tsv(out / f"{node_slug}.tsv", out_fields, out_rows)

        entry: dict = {"description": name, "parent": parent}
        if interval:
            entry = {"type": "mava:AnnotationSeries", **entry}
        else:
            dims = dense_dims(rows[0]["annotations"] if rows else "")
            if not dims:
                dim = DIM_NAME.get(node_slug, DEFAULT_DIM)
                dims = {
                    dim: {"description": name, "range": DIM_RANGE.get(dim, "[0,1]")}
                }
            entry = {
                "type": "mava:ObservationSeries",
                **entry,
                "sampling_interval_seconds": detect_interval(kept),
                "dimensions": dims,
            }
        # put type first for readability
        tracks[node_slug] = {"type": entry.pop("type"), **entry}
        print(
            f"  {node_slug}: {tracks[node_slug]['type']}"
            f" ({len(kept)} rows, parent={parent}, "
            f"si={tracks[node_slug].get('sampling_interval_seconds')})"
        )
    return tracks


def build_regions(cfg: dict, raw: Path, out: Path) -> dict:
    """silent_child only: real bboxes with cluster_id resolved via the cluster blob."""
    rc = cfg["regions"]
    window = cfg["window"]
    bboxes = yaml.safe_load((raw / rc["bboxes_yml"]).read_text())["bboxes"]
    clusters = unzip_yaml(raw / rc["cluster_zip"], "cluster_data.yml")["cluster"]
    face_to_cluster: dict[str, int] = {}
    for idx, cl in enumerate(clusters):
        for fid in cl.get("embedding_ref_ids", []):
            face_to_cluster[fid] = idx

    w0, w1 = window
    rows = []
    for b in bboxes:
        t = float(b["time"])
        if not (w0 <= t <= w1):
            continue
        rows.append(
            {
                "start in seconds": f"{t - w0:g}",  # rebased to 0 (clip start)
                "x": f"{b['x']:.6f}",
                "y": f"{b['y']:.6f}",
                "w": f"{b['w']:.6f}",
                "h": f"{b['h']:.6f}",
                "det_score": f"{b['det_score']:.4f}",
                "cluster_id": face_to_cluster[b["ref_id"]],
                "label": "",  # labels are not in the export (clusters are unnamed)
            }
        )
    rows.sort(key=lambda r: (float(r["start in seconds"]), r["cluster_id"]))
    cols = ["start in seconds", "x", "y", "w", "h", "det_score", "cluster_id", "label"]
    write_tsv(out / f"{rc['track']}.tsv", cols, rows)
    print(
        f"  {rc['track']}: RegionSeries ({len(rows)} boxes, "
        f"{len({r['cluster_id'] for r in rows})} clusters)"
    )
    return {
        "type": "mava:RegionSeries",
        "description": "Per-frame face bounding boxes, normalized to [0,1] of the "
        "frame, top-left origin. One row per detection.",
        "parent": None,
        "coordinate_space": "normalized",
        "sampling_interval_seconds": 0.5,
        "dimensions": {
            "x": {"description": "Box left edge (normalized)", "range": "[0,1]"},
            "y": {"description": "Box top edge (normalized)", "range": "[0,1]"},
            "w": {"description": "Box width (normalized)", "range": "[0,1]"},
            "h": {"description": "Box height (normalized)", "range": "[0,1]"},
            "det_score": {"description": "Detection confidence", "range": "[0,1]"},
        },
    }


def apply_derivations(tracks: dict, derivations: dict) -> None:
    for node_slug, (sources, method) in derivations.items():
        if node_slug not in tracks:
            print(f"  WARN derivation target {node_slug!r} not in tracks")
            continue
        tracks[node_slug]["derived_from"] = list(sources)
        tracks[node_slug]["method"] = method


def write_video_yml(cfg: dict, name: str, raw: Path, out: Path) -> None:
    v = yaml.safe_load((raw / "video.yml").read_text())
    start, end = cfg["window"]
    meta = {
        "id": name,
        "src": f"{name}.mp4",
        "title": cfg["title"],
        "width": int(v["width"]),
        "height": int(v["height"]),
        "fps": float(v["fps"]),
        # Times are rebased to 0, so this clip is `end - start` long. The source
        # window records where it was cut from (for the ffmpeg command).
        "duration_seconds": round(end - start, 3),
        "source_window": {"start": start, "end": end},
    }
    (out / "video.yml").write_text(
        yaml.dump(meta, sort_keys=False, default_flow_style=False)
    )


def write_tracks_yml(name: str, cfg: dict, tracks: dict, out: Path) -> None:
    header = (
        f"# Track metadata for {name} — segment "
        f"{cfg['window'][0]}-{cfg['window'][1]}s.\n"
        "# Built from the export's timelines.yml (parent <- parent_id, type <- node\n"
        "# type) plus a derivation overlay. Relationships are track-level metadata,\n"
        "# NOT columns in the TSV row data. Each track's rows live in <track>.tsv.\n\n"
    )
    body = yaml.dump(
        tracks, sort_keys=False, default_flow_style=False, allow_unicode=True
    )
    (out / "tracks.yml").write_text(header + body)


def extract(name: str, cfg: dict) -> None:
    raw = DATA / name / "raw_data"
    tsv = DATA / name / "tsv"
    out = OUT_ROOT / name
    out.mkdir(parents=True, exist_ok=True)
    # Clean previously-generated files so dropped tracks don't linger.
    for stale in [*out.glob("*.tsv"), *out.glob("*.yml")]:
        stale.unlink()
    print(f"\n=== {name}  (window {cfg['window'][0]}-{cfg['window'][1]}s) → {out} ===")
    write_video_yml(cfg, name, raw, out)
    tracks = build_from_timelines(cfg, raw, tsv, out)
    if cfg["regions"]:
        tracks[cfg["regions"]["track"]] = build_regions(cfg, raw, out)
    apply_derivations(tracks, cfg["derivations"])
    write_tracks_yml(name, cfg, tracks, out)
    print(f"  tracks.yml: {len(tracks)} tracks")


def main() -> None:
    for name, cfg in SOURCES.items():
        extract(name, cfg)
    print("\nDone.")


if __name__ == "__main__":
    main()
