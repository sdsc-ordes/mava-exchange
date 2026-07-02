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
    inspect/
      corpus.mediapkg.ttl     # RDF (Turtle) export of the manifest
      corpus.mediapkg.jsonld  # RDF (JSON-LD) export of the manifest
  videos/<src>.mp4        # short demo clips, timeline rebased to 0
  scripts/build_mediapkg.py
```

## How the examples are derived

Everything under `examples/` is **generated** — nothing here is hand-authored.
The raw data comes from the **TIBAVA demo instance** (see
[`data/README.md`](../data/README.md)); the derive scripts below are a
**temporary guide**, to be retired once the applications export `.mediapkg`
directly via the `mava-exchange` package.

The chain runs in two stages, with the committed `input/` in the middle:

```
data/<src>/  ──(1) extract──▶  examples/input/<src>/  ──(2) build──▶  examples/output/corpus.mediapkg
 (raw, gitignored)                (committed)                             (committed)
        │
        └────────────(3) cut────▶  examples/videos/<src>.mp4  (committed)
```

### (1) Raw → `examples/input/` — `just examples::extract`

[`tools/scripts/extract_segment.py`](../tools/scripts/extract_segment.py) reads
the raw platform exports under `data/<src>/` (gitignored — see
[`data/README.md`](../data/README.md)) and writes the declarative input:

- the **track tree** comes straight from the export's `timelines.yml`
  (`parent ← parent_id`, `type ← node type`); a small per-source overlay adds
  the `derived_from` / `method` edges the raw dumps don't record;
- each track's rows are sliced to a time **window**, **rebased to 0** (so a clip
  cut at the window start lines up), stripped of absolute `hh:mm:ss` timecodes,
  and written to `<track>.tsv`;
- `silent_child` additionally resolves real face boxes into a `RegionSeries`
  (`bbox.ref_id → face → cluster → cluster_id`);
- `video.yml` records `source_window` (where the clip was cut from) alongside
  `width` / `height` / `fps` / `duration`.

The per-source window, included tracks, and derivation overlay live in the
`SOURCES` table at the top of that script.

> Maintainer-only: this step needs the raw data and is not required to _use_ the
> examples.

### (2) `examples/input/` → `corpus.mediapkg` — `just example`

[`scripts/build_mediapkg.py`](scripts/build_mediapkg.py) is generic and
data-driven: it auto-discovers every folder under `input/`, reads `video.yml` +
`tracks.yml`, builds each track from its declared `type`/`dimensions`, loads the
matching `<track>.tsv`, and writes `output/corpus.mediapkg`. There is no
per-video or per-track code — add a video by adding an `input/<src>/` folder.

The creation timestamp is fixed, so regenerating the corpus is
byte-reproducible.

### (3) Raw video → `examples/videos/<src>.mp4` — `just examples::cut-clips`

[`tools/scripts/cut_clips.py`](../tools/scripts/cut_clips.py) cuts each short
demo clip from the raw source video using the `source_window` recorded in
`input/<src>/video.yml`, rebasing the clip's timeline to 0 so it matches the
0-based TSV rows (and the viewer). It needs `ffmpeg` and the raw source video
under `data/<src>/raw_data/`; sources whose raw video is absent are skipped.

> Unlike the corpus, clips are **not** byte-reproducible (they are re-encoded).
> They are binary demo assets, not a reproducibility oracle.

## Regenerate everything

One command does the whole import — input, clips, corpus, and inspect RDF:

```bash
just examples::regenerate   # extract -> cut-clips -> example -> snapshots
```

Or run the stages individually:

```bash
just examples::extract     # (1) raw  -> examples/input/     (needs data/)
just examples::cut-clips   # (3) raw  -> examples/videos/     (needs data/ + ffmpeg)
just example               # (2) input -> corpus.mediapkg
just examples::snapshots   # refresh output/inspect/*.ttl,*.jsonld from the corpus
```

Only `example` runs without the raw data — `examples::extract` and
`examples::cut-clips` are maintainer steps that need the gitignored `data/`.

### Clean rebuild

Every stage overwrites in place (the extractor even prunes stale per-source
files), so re-running `just examples::regenerate` is the normal, safe "retry" —
no clean needed.

For a from-scratch rebuild you can also wipe the generated outputs first:

```bash
just examples::clean        # remove corpus, inspect RDF, and clips
just examples::regenerate   # rebuild them all from data/
```

This is safe as long as `data/` holds the raw sources for every example (it
does: both `silent_child` and `tagesschau`). The corpus and inspect RDF are
byte-reproducible; the **clips are re-encoded**, so regenerating them produces a
new (functionally identical) binary — commit that intentionally.
