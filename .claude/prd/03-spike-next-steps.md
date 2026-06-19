# Step-0 design spike — instructions for a fresh chat

**Do this in a NEW chat.** Paste the "Kickoff prompt" below. Everything needed
is in this `.claude/prd/` folder — no prior chat context required.

## Goal

Produce a **paper design spike**: map ONE real `face_clustering` run from the
`silent_child` raw data end-to-end into a _draft_ `.mediapkg`, to lock three
coupled decisions before any implementation:

1. `RegionSeries` column layout (the bounding boxes).
2. **Where identity lives** — `cluster_id` column on detections vs a separate
   cluster/identity track (likely both; spike decides the split).
3. **How the two relationship kinds are declared** in the manifest — containment
   (`parent`) vs derivation (`derived_from` + method).

## Hard constraints

- **Paper only.** Do NOT modify any human-core file:
  `src/mava_exchange/tracks.py`, `src/mava_exchange/__init__.py`,
  `spec/SPEC.md`, `spec/mava.ttl`, `spec/mava.shacl.ttl`.
- Output goes to `.claude/prd/04-spike-faces-to-people.md` (a new markdown
  draft). No code, no Parquet, no manifest written to disk yet.
- This is a design artifact for the user to react to — end by asking for
  feedback, per the user's working style (analyze → plan → wait for confirmation
  before building).

## Steps

1. **Read context** (in order): `.claude/prd/00-overview.md`,
   `01-data-analysis.md`, `02-roadmap.md`. Then the current public types:
   `src/mava_exchange/tracks.py` and the format spec `spec/SPEC.md` §5–6.
2. **Re-confirm the raw data** (don't trust memory — re-read):
   - `examples/input/silent_child/raw_data/video.yml` (frame size, fps).
   - `bboxes_data.yml` in `raw_data/data/1afa5e418af4474485b7ae9b1d6b19bc/` (box
     fields).
   - `cluster_data.yml` and `faces_data.yml` (unzip the CLUSTER blob
     `1434b446…zip` and FACE blob `7288027b…zip`).
   - `raw_data/plugin_run_results.yml` — note the `face_clustering` run emits
     `TYPE_BBOXES`, `FACE`, `CLUSTER`, `TYPE_KPSS`, `IMAGE_EMBEDDINGS`,
     `IMAGES`.
3. **Draft the worked example** in `04-spike-faces-to-people.md`:
   - A `RegionSeries` manifest track entry (proposed `type`, columns,
     description, normalization note).
   - A sketch of the `RegionSeries` Parquet rows for a few real boxes
     (`start_seconds, x, y, w, h, det_score, cluster_id, label`).
   - The **cluster/identity** representation (one row per the 83 people) and how
     a detection row references it (`cluster_id`).
   - One **derived** ObservationSeries (a `cluster_to_scalar` presence track,
     e.g. "Joanne") showing a `derived_from` + method edge back to its cluster.
   - One **containment** example (Shots ⊃ Shot Sizes ⊃ Close-Up) showing the
     `parent` edge — to prove ONE hierarchy mechanism covers both spatial
     (faces→people) and interval (shots) cases.
   - The proposed **new ontology terms** needed (spatial: box geometry +
     det_score; relations: `hasParent` / `derivedFrom` + method). List them; do
     NOT edit `mava.ttl`.
   - Open questions / risks surfaced by trying to write it down.
4. **Stop and ask** the user to react before proposing implementation (which
   becomes step 1 of `02-roadmap.md`).

## Deliverable

`.claude/prd/04-spike-faces-to-people.md` — a self-contained design draft that
either confirms the `RegionSeries` + clustering + hierarchy design or surfaces a
problem to resolve before coding.

---

## Kickoff prompt (paste into the fresh chat)

> Read `.claude/prd/00-overview.md`, `01-data-analysis.md`, `02-roadmap.md`, and
> `03-spike-next-steps.md`. Then do the step-0 design spike exactly as described
> in `03`: map one real `face_clustering` run from the silent_child raw data
> into a draft `.mediapkg` design, written to
> `.claude/prd/04-spike-faces-to-people.md`. Paper only — do not touch any
> human-core file. Re-read the raw data to confirm details rather than relying
> on the notes. End by asking me for feedback before any implementation.
