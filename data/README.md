# `data/` — illustrative raw exports (not version controlled)

This directory holds the **raw video-annotation exports** the example corpus is
derived from. Everything here except this README and the two screenshots below
is **gitignored** and must not be committed. Consumers of the examples don't
need it — everything they need is already under [`examples/`](../examples/).

It exists only to **show what the real data looks like**, so the `.mediapkg`
format (and the writer/reader/validator) can be developed and checked for
idempotent round-tripping against genuine platform output.

## Where it comes from — the TIBAVA demo instance

The example data is exported, for now, from a project in the **TIBAVA** demo
instance (the video-annotation platform this format serves). Two of TIBAVA's
export modes produce the two halves of each `data/<src>/` folder:

**Export project → _Include video_** produces `raw_data/` (the timeline tree,
typed plugin results, result blobs, and the source video):

![TIBAVA "Export project" dialog with Include video checked](tibava_project_export.png)

**Individual CSVs → _Use seconds_** produces the per-track `tsv/` files (one per
timeline node), which the extractor slices into `examples/input`:

![TIBAVA "Individual CSVs" dialog with Use seconds checked](tibava_tsv_export.png)

## Temporary by design

This raw data, and the scripts that turn it into `.mediapkg`
(`tools/scripts/extract_segment.py`, `examples/scripts/build_mediapkg.py`,
`tools/scripts/cut_clips.py`), are a **transitional guide**. The end state is
that the applications export `.mediapkg` **directly, via the `mava-exchange`
Python package** — at which point this manual raw→mediapkg path is retired. The
scripts stay in the repo only as a reference for that integration.

It is also not committed because it is **media / biometric data**: third-party
copyrighted video plus face crops, embeddings, and clustering of identifiable
people. LFS would not change that — publishing is publishing.

## Expected layout

The tooling expects one folder per source, matching the two exports above:

```
data/<src>/
  raw_data/                    # from "Export project" (Include video)
    <hash>.mp4                 #   the source video (cut_clips.py reads this)
    video.yml                  #   width, height, fps, duration, file (=<hash>), ext
    timelines.yml              #   the track tree (parent_id, node type) -> hierarchy
    plugin_runs.yml            #   plugin run metadata (derivation methods)
    plugin_run_results.yml     #   typed results (SCALAR, SHOTS, CLUSTER, TYPE_BBOXES, …)
    data/                      #   result blobs (zips) referenced by data_id
  tsv/                         # from "Individual CSVs" (Use seconds)
    <Track Name>.tsv           #   per-track rows, one file per timeline node
```

- **`extract_segment.py`** reads `raw_data/timelines.yml` for the tree and
  `tsv/<Track Name>.tsv` for each track's rows. For `silent_child` it also reads
  the face-box and cluster blobs under `raw_data/data/` to build the
  `RegionSeries`. The per-source window / included tracks / derivation overlay
  live in that script's `SOURCES` table.
- **`cut_clips.py`** reads `raw_data/video.yml` to locate `<hash>.mp4` and cuts
  the demo clip using the `source_window` recorded in
  `examples/input/<src>/video.yml`.

> Not every source arrives complete. A source needs `tsv/` (per-track rows) to
> feed the extractor, box blobs to get a `RegionSeries`, and
> `raw_data/<hash>.mp4` to cut a clip. Missing pieces are skipped, not
> fabricated.

## Obtaining it (maintainers)

Export the source project from the TIBAVA demo instance using the two modes
shown above and place the result under `data/<src>/` in the layout above. See
[`examples/README.md`](../examples/README.md) for how it flows into the corpus.
