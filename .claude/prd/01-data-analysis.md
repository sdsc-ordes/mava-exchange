# Data analysis — silent_child example corpus

Source explored: `examples/input/silent_child/`. Two representations of the same
video ("The Silent Child"):

- **Processed export** — `tsv/` (40 files), `The Slient Child.eaf`, `.csv`. An
  Advene/ELAN-family export.
- **Raw platform DB** — `raw_data/`. A TIB-AV-Analytics–style store: the
  authoritative source the export was generated from.

> **Key lesson:** the processed export had STRIPPED the spatial layer and
> FLATTENED the hierarchy. Conclusions must be drawn from `raw_data/`, not the
> EAF. (An early read of only the EAF wrongly concluded "no bounding boxes,
> hierarchy only implicit" — the raw data corrected this.)

---

## A. Processed export (`tsv/`, `.eaf`)

### Two physical schemas

- **Dense** (3 cols: `start in seconds`, `start hh:mm:ss.ms`, `annotations`) —
  one scalar sampled every **0.5s**. → maps to `ObservationSeries`.
- **Interval** (5 cols: start, `duration`, `annotations` as a JSON list) —
  sparse segments. → maps to `AnnotationSeries` / `AnnotationListSeries`.

### Decisive fact: one shared segmentation

Every interval tier (`Shots`, `Aggregations`, `Concepts`,
`Person Identification`, `Audio Analysis`, `Shot Sizes`, `Shot Captioning`)
shares the **identical** start+duration boundaries (verified by md5 on the
start/duration columns). The whole corpus is organised around **shot
boundaries**; the dense 0.5s scores are the raw layer beneath them.

### Annotation value convention

Interval annotation values use a `Category::Value` namespace, e.g.
`"Shot Size::Full Shot"`, `"Emotion::Fear"`, `"Blib::a man in a suit..."`.
Values are wrapped in JSON arrays (`["Shot Size::Full Shot"]`).

### EAF tier structure

40 tiers, all `LINGUISTIC_TYPE_REF="default-lt"`, `TIME_ALIGNABLE="true"`,
`GRAPHIC_REFERENCES="false"`, and **no `PARENT_REF`** → the EAF export is
**structurally flat** and has **no spatial references**. The hierarchy that
exists in the source is lost in this export.

---

## B. Raw platform DB (`raw_data/`) — the authoritative source

### Top-level structure

```
raw_data/
  video.yml              # video metadata: 3840x2160, 25 fps, duration 1203.46s
  meta.yml               # version 1.0
  plugin_runs.yml        # the analyses that were run (the pipeline)
  plugin_run_results.yml # typed outputs of each run (DAG of results)
  timelines.yml          # UI tiers, WITH explicit parent_id tree
  data/                  # hashed .zip blobs + extracted folders (yaml/numpy)
```

`video.yml` essentials: `width: 3840`, `height: 2160`, `fps: 25.0`,
`duration: 1203.46`, `name: The Slient Child`.

### Provenance model

`video → plugin_runs (analyses) → plugin_run_results (typed outputs) → data blobs`.
The analyses form a **derivation DAG**, not a flat list.

**Plugin run types observed:**
`thumbnail, shotdetection, audio_freq, audio_rms, whisper, color_analysis, clip (x3), face_clustering, shot_density, shot_type_classification, deepface_emotion, blip_vqa, cluster_to_scalar (x7), aggregate_scalar (x5)`.

**Result types observed:**
`SHOTS, IMAGES (x2), HIST, RGB_HIST, SCALAR (x29), CLUSTER, FACE, TYPE_BBOXES, TYPE_KPSS, IMAGE_EMBEDDINGS`.

### The three target features, all explicit in the raw data

#### 1. Track hierarchy — explicit `parent_id` tree

`timelines.yml` entries carry `parent_id` and a `type` (`ANNOTATION` |
`PLUGIN_RESULT`). Real multi-level tree:

```
Shots                       (parent_id: null,  type: ANNOTATION)
├─ Shot Density             (PLUGIN_RESULT)   dense
├─ Dominant Color(s)        (PLUGIN_RESULT)   dense vector ([r g b])
└─ Shot Sizes               (ANNOTATION)      interval label
   ├─ Extreme Close-Up      (PLUGIN_RESULT) ┐
   ├─ Close-Up              (PLUGIN_RESULT) │ dense 0.5s scores;
   ├─ Medium Shot           (PLUGIN_RESULT) │ Shot Sizes = argmax over these
   ├─ Full Shot             (PLUGIN_RESULT) │
   └─ Long Shot             (PLUGIN_RESULT) ┘
Audio Analysis              (parent_id: null) → RMS Volume, Audio Spectrogram
Person Identification       → per-person presence scalars + Face Emotions
Concepts                    → Bicycle Ride, Night, Car
Aggregations                → Shot <= MS, Joanne & Libby, ... (derived joins)
```

`type: PLUGIN_RESULT` ≈ `ObservationSeries`; `type: ANNOTATION` ≈
`AnnotationSeries`. The hierarchy maps ~1:1 onto existing track types arranged
in a tree.

#### 2. Clustering — 83 clusters over 1,783 faces

- `face_clustering` run groups face **embeddings** into **83 clusters** (=
  person identities). `cluster_data.yml`: each cluster is a list of
  `embedding_ids`.
- `cluster_to_scalar` (7 runs) projects individual clusters → per-person
  presence ObservationSeries (the `Joanne`, `Libby`, `Paul`… timelines).
- `aggregate_scalar` (5 runs) → joint series (`Joanne & Libby`, `Shot <= MS`).

#### 3. Bounding boxes — 1,783 normalized boxes

`data/<hash>/bboxes_data.yml`, one entry per detection:

| field                | example                   | meaning                              |
| -------------------- | ------------------------- | ------------------------------------ |
| `x, y, w, h`         | `0.456,0.102,0.197,0.404` | **normalized [0,1]** top-left + size |
| `det_score`          | `0.824`                   | detection confidence                 |
| `time`, `delta_time` | `65.5`, `0.5`             | timestamp on 0.5s grid               |
| `id`                 | hash                      | unique detection id                  |
| `ref_id`             | hash                      | → `face.id` (identity chain)         |

Counts: **1,783 bboxes, 1,783 faces, 83 clusters.**

### The identity chain (resolves a box to a person)

```
bbox ──ref_id──▶ face ──(embedding)──▶ cluster (person)
1783             1783                   83
```

Verified: first bbox `ref_id` (`df985e73…`) == first face `id` (`df985e73…`).
Clusters reference `embedding_ids`; embeddings correspond to faces. The same
`face_clustering` run also emits `TYPE_KPSS` (facial keypoints),
`IMAGE_EMBEDDINGS`, and face-crop `IMAGES`.

---

## C. Implications for the format (design facts)

1. **Boxes are normalized [0,1]** → need a frame `width`/`height` (in
   `video.yml`: `3840×2160`) to denormalize, OR a documented "coords are
   normalized" rule.
2. **Identity is a per-row attribute, not a separate track** → each detection
   row should carry a `cluster_id`/`person_id`; the cluster→presence
   ObservationSeries is a _derived_ track, not the primary store.
3. **Two distinct relationship kinds:**
   - **Containment** — `timelines.parent_id` (Shots ⊃ Shot Sizes ⊃ Close-Up).
   - **Derivation / provenance** — the plugin DAG (`Shot Sizes` = argmax of
     shot-size scalars; `Joanne` presence = `cluster_to_scalar(cluster)`). The
     hierarchy feature must distinguish these — they are not the same edge.
4. **Pure segmentation track** — `Shots` carries intervals with _empty_
   annotation values; it is the anchor everything aligns to. Current
   `AnnotationSeries` assumes a value column; segmentation may deserve
   first-class treatment.
5. **`ObservationListSeries` not needed** — `Dominant Color(s)` (an `[r g b]`
   vector per frame) is better modeled as a 3-dimension `ObservationSeries`.

## How to re-explore (commands used)

```bash
cd examples/input/silent_child
# schemas of every tsv
for f in tsv/*.tsv; do echo "== $f =="; head -n 2 "$f"; done
# confirm shared shot boundaries
for f in Shots "Shot Sizes" "Face Emotions"; do awk -F'\t' 'NR>1{print $2"|"$4}' "tsv/$f.tsv" | md5; done
# raw DB
cat raw_data/video.yml raw_data/plugin_runs.yml raw_data/plugin_run_results.yml
head -n 40 raw_data/data/1afa5e418af4474485b7ae9b1d6b19bc/bboxes_data.yml   # bboxes
unzip -l raw_data/data/1434b446fc1e4bffb938dc61d6be8507.zip                # CLUSTER
unzip -l raw_data/data/7288027bb92d4b75b16f09fd30b54d23.zip                # FACE
grep -nE '^\s+(name|parent_id|type):' raw_data/timelines.yml | head -40    # hierarchy
```

> Note: `raw_data/data/` contains macOS-duplicated folders (`… 2`, `… 3`) —
> ignore the numbered copies.
