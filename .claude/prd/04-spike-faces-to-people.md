# Step-0 design spike — faces → people, + full silent_child mapping

**Status:** paper design draft. No code, no Parquet, no manifest written to
disk. No human-core file touched (`tracks.py`, `__init__.py`, `spec/SPEC.md`,
`spec/mava.ttl`, `spec/mava.shacl.ttl`). This document maps the real
`silent_child` data into a _draft_ `.mediapkg`, to lock the v0.2 design before
implementation.

Read `00-overview.md` → `01-data-analysis.md` → `02-roadmap.md` → `03` first.

**Decisions folded in from review (2026-06):**

- Drop `detection_id` from `RegionSeries` — not needed.
- Keep video `width`/`height` (+`fps`) in the manifest — needed to denormalize.
- **No identity sidecar / `ClusterTable`.** Thumbnails are generated on the fly
  by the importing tool. Identity lives as **columns on the timed tracks**.
- Labels are human-provided and incomplete; clusters may later be **merged** by
  giving them the same label. So `label` is nullable and many-clusters-to-one-
  label is expected.
- `derived_from` relationships between tracks: confirmed.

> Data location note: the raw corpus now lives at `data/silent_child/` (the path
> is gitignored), not `examples/input/silent_child/` as `01`/`03` state.

---

## 1. The data, re-confirmed

`face_clustering` run `af17483c…` emits a fan of typed results
(`plugin_run_results.yml`):

| result type        | what it is                                  | in scope?              |
| ------------------ | ------------------------------------------- | ---------------------- |
| `TYPE_BBOXES`      | 1,783 face boxes (one per detection)        | **yes → RegionSeries** |
| `FACE`             | 1,783 face records (`id`, `ref_id`)         | importer join only     |
| `CLUSTER`          | 83 clusters, each a list of `embedding_ids` | importer join only     |
| `TYPE_KPSS`        | facial keypoints                            | deferred               |
| `IMAGE_EMBEDDINGS` | embedding vectors                           | importer join only     |
| `IMAGES`           | face crops                                  | deferred (gen on fly)  |

Frame context (`video.yml`): `width: 3840`, `height: 2160`, `fps: 25.0`,
`duration: 1203.46`, `name: The Silent Child`.

Box fields (`1afa5e41…/bboxes_data.yml`): `x, y, w, h` normalized `[0,1]`
(top-left + size), `det_score`, `time` (0.5 s grid), `delta_time: 0.5`,
`ref_id`. Verified `bbox.ref_id == face.id`; counts **1,783 / 1,783 / 83**. The
shared **208 shot segments** are referenced by _every_ interval tier (confirmed:
all ANNOTATION timelines carry the same 208 `timeline_segment_ids`).

---

## 2. Decision A — `RegionSeries` (the new spatial track type)

**Long format: one row per detection**, many rows share a `start_seconds`.

### Manifest entry

```json
"face_regions": {
  "type": "mava:RegionSeries",
  "description": "Per-frame face bounding boxes from the face_clustering run, sampled every 0.5s. Coordinates normalized to [0,1] of the frame, top-left origin.",
  "sampling_interval_seconds": 0.5,
  "coordinate_space": "normalized",
  "parent": null,
  "columns": ["start_seconds", "x", "y", "w", "h", "det_score", "cluster_id", "label"],
  "dimensions": {
    "x":         {"description": "Box left edge, normalized",  "range": "[0,1]"},
    "y":         {"description": "Box top edge, normalized",   "range": "[0,1]"},
    "w":         {"description": "Box width, normalized",      "range": "[0,1]"},
    "h":         {"description": "Box height, normalized",     "range": "[0,1]"},
    "det_score": {"description": "Detection confidence",       "range": "[0,1]"}
  }
}
```

### Parquet rows (real values from `1afa5e41…/bboxes_data.yml`)

| start_seconds | x      | y      | w      | h      | det_score | cluster_id | label  |
| ------------- | ------ | ------ | ------ | ------ | --------- | ---------- | ------ |
| 65.5          | 0.4557 | 0.1019 | 0.1966 | 0.4037 | 0.8237    | 7          | Joanne |
| 66.0          | 0.5141 | 0.2361 | 0.2073 | 0.4486 | 0.7944    | 7          | Joanne |
| 66.5          | …      | …      | …      | 0.4727 | 0.8125    | 19         | null   |

### Locked

- `start_seconds` = raw `time` (first column). `delta_time` (0.5) → track-level
  `sampling_interval_seconds`, not a column.
- Geometry: **normalized `[0,1]`, `xywh`, top-left** — matches raw
  byte-for-byte.
- `det_score`, `x, y, w, h` are numeric dimensions (`DOUBLE`).
- **`detection_id` dropped.**

### Alternatives considered

| fork              | chosen             | rejected        | why                                                  |
| ----------------- | ------------------ | --------------- | ---------------------------------------------------- |
| coordinate format | `xywh` top-left    | `xyxy` corners  | raw is `xywh`; zero-conversion import                |
| normalization     | normalized `[0,1]` | absolute pixels | raw is normalized; pixels recoverable via frame size |
| detection id      | dropped            | keep for joins  | KPSS/crops deferred; reinstate later if needed       |

---

## 3. Decision B — identity as columns (no sidecar)

Identity lives entirely on the timed `RegionSeries` rows, in two nullable
columns:

- **`cluster_id`** — the machine cluster a detection belongs to
  (`face_clustering` produced 83). Stable, present for every detection.
- **`label`** — the _human_ identity, e.g. `"Joanne"`. **Nullable.** Only ~5 of
  the 83 clusters were named in this corpus
  (`Joanne, Libby, Susanne, Paul, Paul's mother`, plus `Libby's brother/sister`
  as separate presence tracks).

**No `ClusterTable` sidecar.** Representative thumbnails are generated **on the
fly by the importing tool** from the boxes + the source video, so there is
nothing to persist. This keeps everything in timed Parquet tracks (your call).

### The label model (important nuance)

Clustering is unsupervised; labels are applied afterward by a human and are
incomplete. Consequences the format must tolerate:

- A label can be **missing** (`null`) even when `cluster_id` is set.
- **Many clusters → one label** is expected: cluster 6 and cluster 45 may both
  be `"Libby"` if the clusterer split her. Merging = assigning the same `label`
  (or, later, the same `cluster_id`); the format does not forbid it.
- Therefore: do **not** assume `cluster_id`↔`label` is 1:1, and do **not**
  validate label uniqueness or completeness.

A named **presence** ObservationSeries (`person_libby`) is then a _derivation_
that selects all detections whose `label == "Libby"` (or whose `cluster_id` is
in Libby's set) and projects them to a per-time score — see §4.

### Importer note (out of format scope)

`bbox.ref_id → face.id → (embedding) → cluster → cluster_id`. The face→cluster
hop goes through the embedding id-space (cluster `embedding_ids` are not face
ids). The importer resolves this; the `.mediapkg` stores only the resolved
per-row `cluster_id`.

---

## 4. Decision C — the two relationship kinds (confirmed)

Two **separate, explicit** fields on a track entry — different edges, never
conflated.

### C.1 Containment — `parent` (a track name, or `null`)

Mirrors `timelines.parent_id`. `close_up.parent = "shot_sizes"`,
`shot_sizes.parent = "shots"`.

### C.2 Derivation — `derived_from` (list) + `method` (string)

The `method` is the `plugin_runs` type verbatim: `argmax`, `cluster_to_scalar`,
`aggregate_scalar`.

```json
"shot_sizes": {
  "type": "mava:AnnotationSeries",
  "parent": "shots",
  "derived_from": ["shotsize_extreme_close_up", "shotsize_close_up", "shotsize_medium", "shotsize_full", "shotsize_long"],
  "method": "argmax",
  "columns": ["start_seconds", "end_seconds", "annotations"]
}
```

`shot_sizes` is **both** contained in `shots` and derived (argmax) from the five
dense score series — two edges, one node, hence two fields.

### C.3 "Multiple parents" = the derivation edge, not containment

A track like **Libby & Happy** feels like it has _two parents_ (Libby and
Happy). It does — but that is the **derivation** relationship, which is a
**list** and is already multi-source. Containment stays a strict **tree** (one
parent), matching the raw single `parent_id`:

```json
"agg_libby_happy": {
  "type": "mava:ObservationSeries",
  "parent": "aggregations",                      // ← single containment parent (where it lives)
  "derived_from": ["person_libby", "emotion_happy"],  // ← many derivation sources (what it's computed from)
  "method": "aggregate_scalar",
  "sampling_interval_seconds": 0.5,
  "columns": ["start_seconds", "score"],
  "dimensions": { "score": {"description": "Joint Libby-and-Happy score", "range": "[0,1]"} }
}
```

So a node has **0–1 containment parents** and **0–N derivation sources**. This
is exactly why the two edges are separate fields: "lives under Aggregations" and
"computed from Libby + Happy" are both true at once, and a single `parent` field
could not express both.

```json
"person_joanne": {
  "type": "mava:ObservationSeries",
  "parent": "person_identification",
  "derived_from": ["face_regions"],
  "method": "cluster_to_scalar",
  "sampling_interval_seconds": 0.5,
  "columns": ["start_seconds", "presence"],
  "dimensions": { "presence": {"description": "Joanne presence score", "range": "[0,1]"} }
}
```

---

## 5. Full `silent_child` mapping — metadata + tracks

This is the whole timeline tree from the UI (your screenshot), mapped to
`.mediapkg`. **Mapping rule, derived from the raw model:**

- `type: ANNOTATION` (interval, on the shared 208 shot segments) →
  **`AnnotationSeries`** — columns `[start_seconds, end_seconds, annotations]`.
- `type: PLUGIN_RESULT` (dense 0.5 s) → **`ObservationSeries`** — columns
  `[start_seconds, <dims…>]`.
- `type: TRANSCRIPT` → **`AnnotationSeries`** (text).
- Spatial (not shown in this export) → **`RegionSeries`**.

Container nodes (Audio Analysis, Person Identification, Concepts, Aggregations)
are themselves `AnnotationSeries` aligned to the shot segmentation — no separate
"group" type is needed; the `parent` field carries the whole tree. Confirmed
against `Person Identification.tsv`: 208 interval rows, **empty** `annotations`
column — a pure shot-aligned container with no values of its own.

**What the "numbers" are.** The dense per-person tracks (`Joanne.tsv`,
`Libby.tsv`, …) carry a **presence/confidence score in ~[0,1] per 0.5 s**
(`cluster_to_scalar` of that identity's cluster), e.g. Joanne `47.0 → 0.606`.
The score begins at the person's first appearance. The _container_ track
(`Person Identification`) has no numbers — only the dense children do.

**Concepts are not spatial / not object identification.** `Bicycle Ride`,
`Night`, `Car` are `clip` zero-shot **concept scores** — frame-level semantic
similarity to a text prompt (`Bicylce Ride.tsv`: values hover near 0.5), with
**no bounding box**. They are `ObservationSeries`, not `RegionSeries`. The only
spatial layer in this corpus is **faces** (boxes → `RegionSeries`).
`RegionSeries` is the _general_ spatial type; if future data brings true object
detection (localized cars/bikes with boxes), those become `RegionSeries` too —
faces are simply its first instance here.

### 5.1 Manifest metadata (top level + video entry)

```json
{
  "version": "0.2",
  "created": "2026-06-20T00:00:00+00:00",
  "description": "The Silent Child — full annotation corpus (shots, audio, identities, emotions, concepts, aggregations, face regions).",
  "ontology": "http://example.org/mava/ontology#",
  "context": {
    "@context": {
      /* see §6 */
    }
  },
  "tracks": {
    /* see §5.2 */
  },
  "videos": [
    {
      "id": "silent_child",
      "src": "the_silent_child.mp4",
      "title": "The Silent Child",
      "width": 3840,
      "height": 2160,
      "fps": 25.0,
      "duration_seconds": 1203.46,
      "files": {
        "shots": "silent_child/shots.parquet",
        "shot_density": "silent_child/shot_density.parquet",
        "dominant_colors": "silent_child/dominant_colors.parquet",
        "shot_sizes": "silent_child/shot_sizes.parquet",
        "face_regions": "silent_child/face_regions.parquet"
        /* … one entry per track below … */
      }
    }
  ]
}
```

New (additive) video fields: `width`, `height`, `fps`.

### 5.2 Track inventory (all 40 timelines + the new spatial track)

`Obs` = `mava:ObservationSeries` (cols `start_seconds, <dims>`); `Ann` =
`mava:AnnotationSeries` (cols `start_seconds, end_seconds, annotations`); `Reg`
= `mava:RegionSeries`.

| UI name                | track name                  | type | parent                  | derived_from · method                                                                | dims / notes                                        |
| ---------------------- | --------------------------- | ---- | ----------------------- | ------------------------------------------------------------------------------------ | --------------------------------------------------- |
| Shots                  | `shots`                     | Ann  | —                       | —                                                                                    | shared 208-segment segmentation; empty labels       |
| Shot Density           | `shot_density`              | Obs  | `shots`                 | —                                                                                    | `density`                                           |
| Dominant Color(s)      | `dominant_colors`           | Obs  | `shots`                 | —                                                                                    | `r`, `g`, `b` (3-dim, not a list)                   |
| Shot Sizes             | `shot_sizes`                | Ann  | `shots`                 | [5 shotsize_*] · `argmax`                                                            | label per shot                                      |
| Extreme Close-Up       | `shotsize_extreme_close_up` | Obs  | `shot_sizes`            | —                                                                                    | `score`                                             |
| Close-Up               | `shotsize_close_up`         | Obs  | `shot_sizes`            | —                                                                                    | `score`                                             |
| Medium Shot            | `shotsize_medium`           | Obs  | `shot_sizes`            | —                                                                                    | `score`                                             |
| Full Shot              | `shotsize_full`             | Obs  | `shot_sizes`            | —                                                                                    | `score`                                             |
| Long Shot              | `shotsize_long`             | Obs  | `shot_sizes`            | —                                                                                    | `score`                                             |
| Audio Analysis         | `audio_analysis`            | Ann  | —                       | —                                                                                    | container (aligned to shots)                        |
| Audio Spectrogram      | `audio_spectrogram`         | Obs  | `audio_analysis`        | —                                                                                    | `freq_000…freq_NNN` — see Q2                        |
| RMS Volume             | `rms_volume`                | Obs  | `audio_analysis`        | —                                                                                    | `rms` (≥0)                                          |
| Whisper Transcript     | `whisper_transcript`        | Ann  | `audio_analysis`        | —                                                                                    | text (TRANSCRIPT)                                   |
| Person Identification  | `person_identification`     | Ann  | —                       | —                                                                                    | container                                           |
| Joanne                 | `person_joanne`             | Obs  | `person_identification` | [face_regions] · `cluster_to_scalar`                                                 | `presence`                                          |
| Libby                  | `person_libby`              | Obs  | `person_identification` | [face_regions] · `cluster_to_scalar`                                                 | `presence`                                          |
| Susanne                | `person_susanne`            | Obs  | `person_identification` | [face_regions] · `cluster_to_scalar`                                                 | `presence`                                          |
| Paul                   | `person_paul`               | Obs  | `person_identification` | [face_regions] · `cluster_to_scalar`                                                 | `presence`                                          |
| Paul's mother          | `person_pauls_mother`       | Obs  | `person_identification` | [face_regions] · `cluster_to_scalar`                                                 | `presence`                                          |
| Libby's brother        | `person_libbys_brother`     | Obs  | — (raw: top-level)      | [face_regions] · `cluster_to_scalar`                                                 | `presence`; could group under person_identification |
| Libby's sister         | `person_libbys_sister`      | Obs  | — (raw: top-level)      | [face_regions] · `cluster_to_scalar`                                                 | `presence`                                          |
| Face Emotions          | `face_emotions`             | Ann  | —                       | [7 emotion_*] · `argmax`                                                             | dominant emotion per segment                        |
| Angry                  | `emotion_angry`             | Obs  | `face_emotions`         | —                                                                                    | `score`                                             |
| Disgust                | `emotion_disgust`           | Obs  | `face_emotions`         | —                                                                                    | `score`                                             |
| Fear                   | `emotion_fear`              | Obs  | `face_emotions`         | —                                                                                    | `score`                                             |
| Happy                  | `emotion_happy`             | Obs  | `face_emotions`         | —                                                                                    | `score`                                             |
| Sad                    | `emotion_sad`               | Obs  | `face_emotions`         | —                                                                                    | `score`                                             |
| Surprise               | `emotion_surprise`          | Obs  | `face_emotions`         | —                                                                                    | `score`                                             |
| Neutral                | `emotion_neutral`           | Obs  | `face_emotions`         | —                                                                                    | `score`                                             |
| Concepts               | `concepts`                  | Ann  | —                       | —                                                                                    | container                                           |
| Bicylce Ride           | `concept_bicycle_ride`      | Obs  | `concepts`              | —                                                                                    | `score` (clip)                                      |
| Night                  | `concept_night`             | Obs  | `concepts`              | —                                                                                    | `score`                                             |
| Car                    | `concept_car`               | Obs  | `concepts`              | —                                                                                    | `score`                                             |
| Aggregations           | `aggregations`              | Ann  | —                       | —                                                                                    | container                                           |
| Shot <= MS             | `agg_shot_le_ms`            | Obs  | `aggregations`          | [shotsize_extreme_close_up, shotsize_close_up, shotsize_medium] · `aggregate_scalar` | `score`                                             |
| Joanne & Libby         | `agg_joanne_libby`          | Obs  | `aggregations`          | [person_joanne, person_libby] · `aggregate_scalar`                                   | `score`                                             |
| Libby & Happy          | `agg_libby_happy`           | Obs  | `aggregations`          | [person_libby, emotion_happy] · `aggregate_scalar`                                   | `score`                                             |
| Joanne & Sad           | `agg_joanne_sad`            | Obs  | `aggregations`          | [person_joanne, emotion_sad] · `aggregate_scalar`                                    | `score`                                             |
| Joanne & Bicycle       | `agg_joanne_bicycle`        | Obs  | `aggregations`          | [person_joanne, concept_bicycle_ride] · `aggregate_scalar`                           | `score`                                             |
| Shot Captioning        | `shot_captioning`           | Ann  | — (shares shots seg.)   | —                                                                                    | text caption per shot (blip_vqa)                    |
| _(not in this export)_ | `face_regions`              | Reg  | — (top level)           | — _(it is the **source** of the `person\__` presence tracks)\*                       | the new spatial track (§2)                          |

Counts: 8 `AnnotationSeries` (incl. 4 containers + transcript + captioning) · 30
`ObservationSeries` · 1 `RegionSeries`.

### 5.3 Representative track JSON

```json
"dominant_colors": {
  "type": "mava:ObservationSeries",
  "description": "Dominant frame color as an RGB triple, sampled every 0.5s.",
  "sampling_interval_seconds": 0.5,
  "parent": "shots",
  "columns": ["start_seconds", "r", "g", "b"],
  "dimensions": {
    "r": {"description": "Red channel",   "range": "[0,255]"},
    "g": {"description": "Green channel", "range": "[0,255]"},
    "b": {"description": "Blue channel",  "range": "[0,255]"}
  }
},
"face_emotions": {
  "type": "mava:AnnotationSeries",
  "description": "Dominant face emotion per shot segment (argmax of the seven emotion scores).",
  "derived_from": ["emotion_angry","emotion_disgust","emotion_fear","emotion_happy","emotion_sad","emotion_surprise","emotion_neutral"],
  "method": "argmax",
  "columns": ["start_seconds", "end_seconds", "annotations"]
},
"shots": {
  "type": "mava:AnnotationSeries",
  "description": "Shot segmentation — the shared interval boundaries every other interval tier aligns to. Annotation values are empty.",
  "columns": ["start_seconds", "end_seconds", "annotations"]
}
```

---

## 6. Proposed new ontology terms (list only — `mava.ttl` NOT edited)

Namespace `mava: http://example.org/mava/ontology#`.

**Spatial / regions**

| term                                         | kind             | notes                                             |
| -------------------------------------------- | ---------------- | ------------------------------------------------- |
| `mava:RegionSeries`                          | Class            | sibling of `ObservationSeries`                    |
| `mava:RegionDetection`                       | Class            | one detection row (sibling of `ObservationPoint`) |
| `mava:x`,`mava:y`,`mava:width`,`mava:height` | DatatypeProperty | normalized `xsd:decimal` box geometry             |
| `mava:detectionScore`                        | DatatypeProperty | `xsd:decimal`                                     |
| `mava:coordinateSpace`                       | DatatypeProperty | `"normalized"` \| `"pixel"` on the series         |

**Identity (columns, no entity class)**

| term                 | kind             | notes                                                  |
| -------------------- | ---------------- | ------------------------------------------------------ |
| `mava:clusterId`     | DatatypeProperty | machine cluster of a detection                         |
| `mava:identityLabel` | DatatypeProperty | nullable human label; not unique, not 1:1 with cluster |

**Relations**

| term                    | kind             | notes                                                   |
| ----------------------- | ---------------- | ------------------------------------------------------- |
| `mava:hasParent`        | ObjectProperty   | containment; acyclic                                    |
| `mava:derivedFrom`      | ObjectProperty   | provenance; 1..n sources                                |
| `mava:derivationMethod` | DatatypeProperty | `argmax` \| `cluster_to_scalar` \| `aggregate_scalar` … |

**Video frame (manifest video entry, not ontology):** `width`, `height`, `fps`.

Dropped vs the previous draft: `mava:ClusterTable`, `mava:Cluster`,
`representative_image` (thumbnails generated on the fly).

### JSON-LD `@context` additions

```json
"x": {"@id":"mava:x","@type":"xsd:decimal"},
"y": {"@id":"mava:y","@type":"xsd:decimal"},
"w": {"@id":"mava:width","@type":"xsd:decimal"},
"h": {"@id":"mava:height","@type":"xsd:decimal"},
"det_score": {"@id":"mava:detectionScore","@type":"xsd:decimal"},
"cluster_id": {"@id":"mava:clusterId","@type":"xsd:integer"},
"label": {"@id":"mava:identityLabel","@type":"xsd:string"}
```

---

## 7. Open questions / risks — **RESOLVED (2026-06)**

1. **Q1 — `RegionSeries.parent`. → `null` (top level).** `face_regions` is the
   **source**, not a child, of identity: the `person_*` presence tracks are
   `derived_from: [face_regions]`. It does not derive from any other track.
2. **Q2 — Audio Spectrogram. → `ObservationSeries`** with one dimension per
   frequency bin (`freq_000…freq_NNN`). Not deferred.
3. **Q3 — pure-segmentation `shots`. → accept empty annotation values.** No
   dedicated segmentation type for now.
4. **Q4 — container tracks. → emit** as (possibly empty) `AnnotationSeries`, so
   the manifest faithfully mirrors the tree.
5. **Q5 — `cluster_id` dtype. → integer.** Hash→int mapping is the importer's
   job.
6. **Q6 — validator surface for v0.2. → as proposed:** `parent` exists +
   acyclic; `derived_from` targets exist; normalized coords in `[0,1]`;
   `RegionSeries` long-format shape; **no** label uniqueness/completeness check
   (by design).

---

## 8. Recommendation & next step

The design holds on real data and now covers the whole corpus:

- **`RegionSeries`** (normalized `xywh`, long format) for boxes;
- **identity as `cluster_id` + nullable `label` columns** on the timed tracks
  (no sidecar; thumbnails on the fly; clusters mergeable by label);
- **two explicit relationship fields** (`parent`; `derived_from`+`method`) that
  reproduce the entire `silent_child` tree — containment (shots ⊃ shot_sizes ⊃
  close_up), argmax derivations (shot_sizes, face_emotions), `cluster_to_scalar`
  presence series, and `aggregate_scalar` joins — under one mechanism.

§7 is resolved. Implementation proceeds **feature by feature, bottom-up** per
`02-roadmap.md` (step 1 = track hierarchy), touching human-core files only with
explicit sign-off, batched into a single `0.1 → 0.2` version bump.

**Please review and give feedback before any implementation begins.**
