# `data/` — illustrative raw exports (not version controlled)

This directory holds the **raw video-annotation exports** the example corpus was
derived from. In order to provide provenance and reproduciblity, we explain here
how the example data has been derived. The scripts that were used are part of
this repo, in [`data/scripts/`](scripts/).

The actual data is gitignored. It is described here where the examples came from
and how the import can be repeated. The maintainer scripts under `data/scripts/`
are the tracked exception — everything else under `data/` is not version
controlled.

## Where it comes from — the TIBAVA demo instance

The example data is exported, for now, from a project in the
[**TIBAVA** demo instance](https://service.tib.eu/tibava). Two videos are
currently imported: `Silent Child` and `Tageschau`

of TIBAVA's export modes produce the two halves of each `data/<src>/` folder:

<table>
<tr>
<td width="50%"><strong>Export project → <em>Include video</em></strong> produces <code>raw_data/</code> — the timeline tree, typed plugin results, result blobs, and the source video.</td>
<td width="50%"><strong>Individual CSVs → <em>Use seconds</em></strong> produces the per-track <code>tsv/</code> files (one per timeline node), which the extractor slices into <code>examples/input</code>.</td>
</tr>
<tr>
<td><img src="tibava_project_export.png" width="360" alt="TIBAVA Export project dialog with Include video checked"></td>
<td><img src="tibava_tsv_export.png" width="360" alt="TIBAVA Individual CSVs dialog with Use seconds checked"></td>
</tr>
</table>

## Temporary by design

This raw data, and the scripts that turn it into `.mediapkg`
(`data/scripts/extract_segment.py`, `examples/scripts/build_mediapkg.py`,
`data/scripts/cut_clips.py`), are a **transitional guide**. The end state is
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
