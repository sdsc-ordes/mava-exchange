# Examples

A real-data example corpus for the `.mediapkg` format, plus the pipeline that
produces it.

Everything under `examples/` is **generated** — nothing here is hand-authored.
The flow below is meant as a support for the development process.

## Quickstart

Create a `.mediapkg` based on the example input:

```bash
just example               # input -> corpus.mediapkg
```

To fully (re)generate example inputs, follow the instructions below.

## How the create example inputs

## Step 1: fetch raw data from the TIBAVA demo instance

Two videos are currently imported: `Silent Child` and `Tagesschau`. Two of
TIBAVA's export modes produce the two halves of each `examples/input/<src>/`
folder:

<table>
<tr>
<td width="50%"><strong>Export project → <em>Include video</em></strong> produces <code>raw/</code> — the timeline tree, typed plugin results, result blobs, and the source video.</td>
<td width="50%"><strong>Individual CSVs → <em>Use seconds</em></strong> produces the per-track tsv files (one per timeline node), which the extractor gets from <code>raw/</code> and slices into <code>examples/input</code>.</td>
</tr>
<tr>
<td><img src="img/tibava_project_export.png" width="360" alt="TIBAVA Export project dialog with Include video checked"></td>
<td><img src="img/tibava_tsv_export.png" width="360" alt="TIBAVA Individual CSVs dialog with Use seconds checked"></td>
</tr>
</table>

## Step 2: cut and extract the data

To re-create local example `input/` files to help with the development process:

```bash
just examples::regenerate   # whole import: extract -> cut-clips -> example
```

Or the stages individually:

```bash
just examples::extract     # examples/raw   -> examples/input/
just examples::cut-clips   # examples/raw   -> examples/videos/   (needs ffmpeg)
just example               # input -> corpus.mediapkg
```

To reset the examples directory (no output, no raw data):

```bash
just examples::clean
```

```

```
