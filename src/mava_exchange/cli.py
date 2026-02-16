"""
CLI entry points for inspecting and validating .mediapkg files.

Installed as:
    mediapkg-inspect  → inspect_cmd
    mediapkg-validate → validate_cmd

Usage:
    mediapkg-inspect  corpus.mediapkg
    mediapkg-inspect  corpus.mediapkg --track emotions
    mediapkg-inspect  corpus.mediapkg --track emotions --video video_001 --head 10
    mediapkg-validate corpus.mediapkg
    mediapkg-validate corpus.mediapkg --strict
"""

import argparse
import sys
from pathlib import Path

from .reader import MediaPackageReader
from .validate import validate_mediapkg


# ─────────────────────────────────────────────
# inspect
# ─────────────────────────────────────────────

def _print_summary(reader: MediaPackageReader):
    m = reader.manifest
    print(f"Version:     {reader.version}")
    print(f"Created:     {m.get('created', '—')}")
    print(f"Ontology:    {reader.ontology}")
    print(f"Description: {reader.description or '—'}")
    print(f"Videos:      {len(reader.video_ids)}")

    print("\nTracks:")
    for name, track_dict in m["tracks"].items():
        dims = track_dict.get("dimensions", {})
        dim_str = f"  [{', '.join(dims.keys())}]" if dims else ""
        interval = track_dict.get("sampling_interval_seconds")
        interval_str = f"  @{interval}s" if interval else ""
        print(f"  {name:<22} {track_dict['type']}{interval_str}{dim_str}")

    print("\nVideos:")
    for video in m["videos"]:
        print(f"  {video['id']}")
        print(f"    src:    {video['src']}")
        print(f"    tracks: {', '.join(video['files'].keys())}")

    print("\nFiles:")
    print(f"  {'Path':<45} {'Rows':>6}  {'Raw':>10}  {'Compressed':>10}  {'Saved':>6}")
    print(f"  {'-'*45} {'-'*6}  {'-'*10}  {'-'*10}  {'-'*6}")

    total_raw = total_comp = 0
    for s in reader.file_stats():
        ratio = (1 - s["compressed_bytes"] / max(s["size_bytes"], 1)) * 100
        total_raw  += s["size_bytes"]
        total_comp += s["compressed_bytes"]
        print(
            f"  {s['path']:<45} {s['rows']:>6}  "
            f"{s['size_bytes']/1024:>8.1f}KB  "
            f"{s['compressed_bytes']/1024:>8.1f}KB  "
            f"{ratio:>5.0f}%"
        )

    total_ratio = (1 - total_comp / max(total_raw, 1)) * 100
    print(
        f"\n  {'TOTAL':<45} {'':>6}  "
        f"{total_raw/1024:>8.1f}KB  "
        f"{total_comp/1024:>8.1f}KB  "
        f"{total_ratio:>5.0f}%"
    )


def _print_track(reader: MediaPackageReader, video_id: str,
                 track_name: str, n_head: int):
    track = reader.track_def(track_name)
    df = reader.read_track(video_id, track_name)

    print(f"\nTrack:   {track_name}  ({track.type})")
    print(f"Video:   {video_id}")
    print(f"Desc:    {track.description}")
    print(f"Rows:    {len(df)}")

    print("\nColumns:")
    for col in df.columns:
        print(f"  {col:<22} {df[col].dtype}")

    print(f"\nFirst {n_head} rows:")
    print(df.head(n_head).to_string(index=False))

    if hasattr(track, "dimensions") and track.dimensions:
        print("\nDimensions:")
        for dim in track.dimensions:
            range_str = f"  {dim.range}" if dim.range else ""
            print(f"  {dim.name:<20} {dim.description}{range_str}")


def inspect_cmd():
    parser = argparse.ArgumentParser(
        prog="mediapkg-inspect",
        description="Inspect a .mediapkg archive.",
    )
    parser.add_argument("package", type=Path)
    parser.add_argument("--track",  type=str, default=None,
                        help="Show detail for a specific track.")
    parser.add_argument("--video",  type=str, default=None,
                        help="Video ID to use with --track (default: first video).")
    parser.add_argument("--head",   type=int, default=5,
                        help="Number of rows to show (default: 5).")
    args = parser.parse_args()

    print(f"\n{'═' * 60}")
    print(f"  {args.package}")
    print('═' * 60 + "\n")

    with MediaPackageReader(args.package) as reader:
        if args.track:
            video_id = args.video or reader.video_ids[0]
            _print_track(reader, video_id, args.track, args.head)
        else:
            _print_summary(reader)

    print()


# ─────────────────────────────────────────────
# validate
# ─────────────────────────────────────────────

def validate_cmd():
    parser = argparse.ArgumentParser(
        prog="mediapkg-validate",
        description="Validate a .mediapkg archive against the MAVA spec.",
    )
    parser.add_argument("package", type=Path)
    parser.add_argument("--strict", action="store_true",
                        help="Warn about recommended but optional fields.")
    args = parser.parse_args()

    result = validate_mediapkg(args.package, strict=args.strict)
    print(result.summary())
    sys.exit(0 if result.valid else 1)
