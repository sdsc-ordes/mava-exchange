# Examples

A worked, real-data example corpus for the `.mediapkg` format, plus the pipeline
that produces it. Two source videos are included:

- **`tagesschau`** — a rich **hierarchy** example: `Shots ⊃ Shot Sizes ⊃ …`,
  audio under the transcript, `Face Emotions ⊃ 7 emotions`, a named anchor, and
  a human-edited second segmentation. Derivations: `argmax` /
  `cluster_to_scalar` / `manual`. No bounding boxes (this export has none).
- **`silent_child`** — the **spatial** example: real face bounding boxes as a
  `RegionSeries` (`face_regions`), with a resolved `cluster_id` per detection,
  plus a little hierarchy context (per-person presence derived from the
  regions).

## Layout

```
examples/
  input/<src>/            # declarative INPUT (committed, human-readable)
    video.yml             #   id, src, title, width/height/fps, duration, source_window
    tracks.yml            #   per-track metadata: type, parent, derived_from, method, dimensions
    <track>.tsv           #   one slim TSV per track (rows only), filename == track name
  output/
    corpus.mediapkg       # the built package (both videos)
  videos/<src>.mp4        # short demo clips, timeline rebased to 0
  scripts/build_mediapkg.py
```

An RDF view of the manifest (Turtle / JSON-LD) isn't committed — render it on
demand with `just unpack examples/output/corpus.mediapkg tmp/pkg turtle` (or
`json-ld`; `tmp/` is a gitignored scratch dir), or
`mediapkg-inspect examples/output/corpus.mediapkg --format turtle`.

## How the examples are derived

Everything under `examples/` is **generated** — nothing here is hand-authored,
and the derive scripts are a **temporary guide**, to be retired once
applications export `.mediapkg` directly via `mava-exchange`. The raw data and
the two upstream stages that produce `input/` and `videos/`
(`extract_segment.py`, `cut_clips.py`) live with the raw data — see
[`data/README.md`](../data/README.md).

This README owns the last stage: the committed `input/` → the corpus.

```mermaid
flowchart LR
    input["examples/input/ (committed)"]
    corpus["examples/output/corpus.mediapkg"]
    input -->|"scripts/build_mediapkg.py · just example"| corpus
```

[`scripts/build_mediapkg.py`](scripts/build_mediapkg.py) expects one folder per
video under `input/<src>/`, each holding:

- `video.yml` — `id`, `src`, `title`, `width`/`height`/`fps`, `duration`;
- `tracks.yml` — per-track `type`, `parent`, `derived_from`, `method`,
  `dimensions`;
- one `<track>.tsv` per track (filename == track name, `start_seconds` first).

It is fully **generic**: it auto-discovers every `input/<src>/` folder and every
track declared in `tracks.yml`, so a new video or track is added by dropping
files under `input/` — no code change. The creation timestamp is fixed, so the
corpus is byte-reproducible.

## Regenerate everything

```bash
just examples::regenerate   # whole import: extract -> cut-clips -> example
```

Or the stages individually:

```bash
just examples::extract     # raw   -> examples/input/    (needs data/)
just examples::cut-clips   # raw   -> examples/videos/   (needs data/ + ffmpeg)
just example               # input -> corpus.mediapkg
```

Every stage overwrites in place, so re-running is the normal, safe retry; only
`just example` works without the gitignored `data/` (`just examples::clean`
wipes the outputs first for a from-scratch rebuild). The corpus is
byte-reproducible, but clips are re-encoded — regenerating them yields a new,
functionally identical binary (commit intentionally).
