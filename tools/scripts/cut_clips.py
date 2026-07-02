"""
Cut the short demo video clips (examples/videos/<src>.mp4) from the raw source
videos (gitignored, under data/<src>/raw_data/).

This is a one-off maintainer step, NOT part of the library. It needs `ffmpeg`
and the raw data. For every video folder under examples/input/<src>/ that
records a `source_window` in its video.yml, it cuts [start, end] from the raw
source and rebases the clip's timeline to 0 — so the clip lines up with the
0-based `start_seconds` in the extracted TSV rows (and hence the viewer).

Sources whose raw video is absent are skipped with a message; the committed
clips for those stay as they are.

Note: the output is re-encoded, so it is NOT byte-identical to a previously
committed clip (unlike corpus.mediapkg, which is byte-reproducible). The clips
are binary demo assets, not a reproducibility oracle.

Run:
    just cut-clips          # or: uv run tools/scripts/cut_clips.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
INPUT_ROOT = REPO / "examples" / "input"
VIDEOS_OUT = REPO / "examples" / "videos"


def raw_source(name: str) -> Path | None:
    """Locate the raw source video for a source under data/<name>/raw_data/."""
    raw = DATA / name / "raw_data"
    vy = raw / "video.yml"
    if vy.exists():
        v = yaml.safe_load(vy.read_text())
        exact = raw / f"{v['file']}{v.get('ext', '.mp4')}"
        if exact.exists():
            return exact
    # Fall back to the single source video at the raw_data root: the platform
    # sometimes stores it under a slightly different name (e.g. a double dot
    # before the extension) than video.yml's file/ext fields imply.
    mp4s = sorted(p for p in raw.glob("*.mp4")) if raw.is_dir() else []
    return mp4s[0] if len(mp4s) == 1 else None


def cut(start: float, end: float, raw: Path, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    # -ss before -i: fast seek that also rebases the output timestamps to 0, so
    # the clip's timeline matches the 0-based TSV rows. Re-encode for a clean,
    # keyframe-independent cut.
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start}",
        "-i", str(raw),
        "-t", f"{end - start}",
        # Cap width at 1280 (keep aspect, even height) so a 4K source doesn't
        # produce a huge demo clip; already-smaller videos are left as-is.
        "-vf", "scale='min(1280,iw)':-2",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(out),
    ]
    # Args are fully controlled (ffmpeg + repo-local paths), not user input.
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # noqa: S603


def main() -> None:
    for vdir in sorted(p for p in INPUT_ROOT.iterdir() if p.is_dir()):
        name = vdir.name
        v = yaml.safe_load((vdir / "video.yml").read_text())
        win = v.get("source_window")
        if not win:
            print(f"  skip {name}: no source_window in video.yml")
            continue
        raw = raw_source(name)
        if raw is None:
            print(f"  skip {name}: raw source video not found under data/{name}/raw_data/")
            continue
        out = VIDEOS_OUT / v.get("src", f"{name}.mp4")
        print(f"  {name}: cut [{win['start']}, {win['end']}]s -> {out.relative_to(REPO)}")
        cut(float(win["start"]), float(win["end"]), raw, out)
    print("Done.")


if __name__ == "__main__":
    main()
