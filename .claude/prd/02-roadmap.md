# Roadmap — v0.2 extensions

Builds on the findings in `01-data-analysis.md`. All three features are observed
in the raw `silent_child` platform data.

## The mental model the format already has

Existing types sit on two orthogonal axes:

|                                     | single value        | list of values         |
| ----------------------------------- | ------------------- | ---------------------- |
| **dense point** (`start_seconds`)   | `ObservationSeries` | _(empty — see below)_  |
| **sparse interval** (`start`+`end`) | `AnnotationSeries`  | `AnnotationListSeries` |

Bounding boxes are **not** the empty cell — they introduce a **new spatial
axis** the current format and ontology have no vocabulary for.

## Feature mapping

### 1. Track hierarchy (foundational)

- Observed as explicit `timelines.parent_id` tree + node `type`.
- **Model two relationship kinds** (do not conflate):
  - **Containment** — child track belongs under a parent track.
  - **Derivation / provenance** — track X is _derived from_ tracks Y… via a
    named method (e.g. `argmax`, `cluster_to_scalar`, `aggregate_scalar`).
- Additive at the manifest level: an optional `parent` field + a relation
  descriptor on each track. Needs new ontology terms (e.g. `mava:hasParent` /
  `mava:derivedFrom` + method) and validation (parent exists, no cycles,
  optional time-containment).

### 2. Clustering

- Clustering = group identity. In the data: 83 face clusters = person
  identities; downstream `cluster_to_scalar` produces presence
  ObservationSeries.
- **Identity lives as a column** (`cluster_id`/`person_id`) on the detection
  rows. Optionally a small **cluster/identity parent track** (one row per
  cluster: id, label, representative image ref). The presence ObservationSeries
  is a _derived_ child (a derivation edge — see hierarchy).
- Two flavors both real: spatial identity clustering (faces→people) and temporal
  aggregation (dense scores→per-shot label).

### 3. Bounding boxes → new `RegionSeries`

- Long format: **one row per detection**, multiple rows share a `start_seconds`.
- Proposed columns (subject to spike): `start_seconds`, `x`, `y`, `w`, `h`
  (normalized [0,1]), `det_score`, `cluster_id` (nullable), `label` (nullable).
- Needs new spatial ontology terms (none exist today) + new validation + a
  normalization convention (frame `width`/`height`, or "coords are [0,1]").
- Keypoints / embeddings / face-crop images are richer optional payloads — out
  of scope for the first cut.

### 4. `ObservationListSeries` — DEFERRED

The empty grid cell. No compelling case (`Dominant Color(s)` RGB vector → model
as 3-dimension `ObservationSeries`). Do not build speculatively.

## Build order (de-risk first, then simple → complex)

| #   | Step                                                                     | Risk                  | Notes                                                                                                             |
| --- | ------------------------------------------------------------------------ | --------------------- | ----------------------------------------------------------------------------------------------------------------- |
| 0   | **Design spike** on the real `face_clustering` run                       | attacks the real risk | paper only; see `03-spike-next-steps.md`. Locks RegionSeries columns + where identity lives + relationship kinds. |
| 1   | **Track hierarchy** (containment + derivation)                           | low                   | foundation; additive manifest + ontology + validation. No new data shapes.                                        |
| 2   | **Clustering — temporal aggregation** (`shot-size scores → Shot Sizes`)  | low                   | proves clustering/derivation on existing types; no spatial complexity.                                            |
| 3   | **`RegionSeries`** (face boxes)                                          | med                   | columns locked by the spike. New spatial ontology terms.                                                          |
| 4   | **Tracklets** = clustering applied to `RegionSeries` (faces → 83 people) | low                   | falls out of 1–3.                                                                                                 |

## Why this order

Hierarchy is the backbone; clustering is hierarchy (the derivation edge)
specialized; tracklets are clustering applied to `RegionSeries`. The spike
attacks the genuine risk up front — the **coupled design** of detections +
identity + relationship kinds — on real data, before any human-core file is
touched.

## Constraints / flags

- **Human-core files** (do NOT edit without explicit instruction):
  `src/mava_exchange/tracks.py`, `src/mava_exchange/__init__.py`,
  `spec/SPEC.md`, `spec/mava.ttl`, `spec/mava.shacl.ttl`. Every step 1–4 touches
  several of these → each needs explicit user sign-off.
- **Version bump 0.1 → 0.2** — additive but breaks old readers (unknown `type`).
  Per `CLAUDE.md`: requires `SPEC.md` + `mava.ttl` + `CHANGELOG.md` migration
  note. Batch all of v0.2 into one bump.
- **Correctness oracle** — `validate_mediapkg` in `validate.py`. Any new track
  type must extend it (don't weaken existing checks); roundtrip property tests
  in `tests/test_roundtrip.py` are the regression gate.
- **Conventions** — `start_seconds` first column; Parquet column names ==
  `DimensionSpec.name`; dataclasses only; Python 3.12+, type hints on public
  functions.
