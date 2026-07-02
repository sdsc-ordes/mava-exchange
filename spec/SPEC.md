# MediaPkg Format Specification

**Version:** 0.2 (Draft) **Repository:**
https://github.com/smaennel/mava-exchange **Ontology:**
http://example.org/mava/ontology# **License:** Apache 2.0

## Status

This is an early draft specification. It is being developed in the context of
the TIBAV-A and videoscope use cases at ETH Zurich / Swiss Data Science Center.
Feedback welcome via GitHub issues.

The key words MUST, MUST NOT, REQUIRED, SHOULD, SHOULD NOT, RECOMMENDED, MAY,
and OPTIONAL in this document are to be interpreted as described in
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## 1. Introduction

MediaPkg (`.mediapkg`) is a lightweight, compressed interchange format for
time-based annotations on video files. It is designed for efficient exchange
between video annotation and processing tools without the overhead of full RDF
serialisation.

A `.mediapkg` file is a ZIP archive containing:

- A `manifest.json` describing the corpus, its videos, annotation tracks, and
  the semantic meaning of all columns
- One or more Parquet files — one per annotation track per video — containing
  the actual annotation data

The format is backed by the MAVA ontology, which provides a shared vocabulary
for annotation tools in linguistics and multimodal analysis.

---

## 2. Motivation

Tools in the video annotation space produce a variety of outputs — emotion
scores, shot boundaries, transcripts, scene labels, and others. These outputs
are currently exchanged as plain TSV or CSV files with no shared vocabulary,
making interoperability between tools difficult.

A previous approach exported all data to RDF/Turtle. While semantically rich,
this proved too slow for large videos — serialisation of a single video's
annotations could take ten minutes or more.

MediaPkg addresses this by separating two concerns:

- **Data transport** — handled by Parquet inside ZIP, which is fast, compressed,
  and columnar
- **Semantic meaning** — handled by the MAVA ontology and a JSON-LD `@context`
  in the manifest

This mirrors the approach taken by GeoParquet in the geospatial domain:
efficient binary data with attached semantic metadata.

---

## 3. Relation to Existing Standards

### GeoParquet

MediaPkg is directly inspired by [GeoParquet](https://geoparquet.org/).
GeoParquet embeds metadata inside Parquet files under a `geo` key to describe
geometry columns. MediaPkg uses the same mechanism (a `mj` key in the Parquet
metadata) and extends it with a JSON-LD context for full ontology linkage.

| Concept           | GeoParquet                               | MediaPkg                            |
| ----------------- | ---------------------------------------- | ----------------------------------- |
| Container         | `.parquet` file                          | `.mediapkg` ZIP archive             |
| Metadata location | Embedded in Parquet `key_value_metadata` | `manifest.json` in ZIP              |
| Semantic layer    | None (operational only)                  | JSON-LD `@context` → MAVA ontology  |
| Coordinate system | WGS84 (spatial)                          | Seconds from video start (temporal) |
| Multi-file corpus | Not addressed                            | Multiple videos in one archive      |

### ELAN / EAF

[ELAN](https://archive.mpi.nl/tla/elan) (EUDICO Linguistic Annotator) is the
dominant annotation tool in linguistics and multimodal research. It stores
annotations in the EAF format (ELAN Annotation Format) — an XML file organised
around **tiers**: named layers that group time-aligned annotations. Tiers can be
hierarchically connected and linked to linguistic types.

EAF is the primary export format of several tools in the MAVA project context,
including TIB-AV-A. MediaPkg is not a replacement for EAF — it serves a
different purpose:

| Concept             | EAF                                        | MediaPkg                               |
| ------------------- | ------------------------------------------ | -------------------------------------- |
| Primary use         | Human annotation and transcription         | Machine-generated analysis output      |
| Data model          | Tiers with typed, hierarchical annotations | Flat observation and annotation series |
| Numeric time-series | Not supported                              | First-class (ObservationSeries)        |
| File format         | XML                                        | Parquet inside ZIP                     |
| Corpus packaging    | One file per recording                     | Multiple videos in one archive         |
| Performance         | Slow to parse at scale                     | Columnar, fast reads                   |

A future integration goal is to allow tools to import EAF annotations into
`.mediapkg` as `AnnotationSeries` tracks, enabling combined analysis of human
annotations and AI-generated observation data in a single package.

### CLARIN / CMDI

[CLARIN](https://www.clarin.eu) (Common Language Resources and Technology
Infrastructure) is the European research infrastructure for language resources.
Its metadata standard is
[CMDI](https://www.clarin.eu/content/cmdi-component-metadata-infrastructure)
(Component Metadata Infrastructure) — a flexible, component-based XML metadata
framework standardised in ISO 24622.

CMDI operates at a different level than MediaPkg: it describes **resources**
(corpora, recordings, tools) rather than the annotation data inside them. A CMDI
record for a video corpus would describe who created it, what language is
spoken, what tools were used, and where the data can be found — but not the
content of the annotations themselves.

The two are complementary:

| Concept     | CMDI                                 | MediaPkg                      |
| ----------- | ------------------------------------ | ----------------------------- |
| Describes   | The resource (corpus-level metadata) | The annotation data           |
| Format      | XML                                  | JSON-LD + Parquet             |
| Audience    | Archive infrastructure, discovery    | Analysis tools, data exchange |
| Granularity | Corpus and recording level           | Track and row level           |

For CLARIN-compliant archiving, a `.mediapkg` corpus would be described by a
CMDI metadata record that references the package as a resource. The MAVA
ontology provides the semantic vocabulary that bridges the two levels.

### Frictionless Data

[Frictionless Data](https://frictionlessdata.io/) is a framework for describing,
validating, and packaging tabular data. It supports Parquet files through a
generic `datapackage.json` metadata file that declares table schemas with column
types, constraints, and human-readable descriptions.

**The fundamental difference is architectural**: Frictionless is built around
**domain-agnostic tooling** that works with any tabular data — its value lies in
generic validation and packaging infrastructure that users adapt to their domain
by writing schemas. MediaPkg is built around a **domain-specific ontology**
(MAVA) that defines the semantics of video annotations — tooling is written to
support this ontology, not the other way around.

| Concept           | Frictionless Data                          | MediaPkg                                                                 |
| ----------------- | ------------------------------------------ | ------------------------------------------------------------------------ |
| Domain            | Generic tabular data                       | Video annotations (time-series + intervals)                              |
| Semantic layer    | None (operational metadata only)           | JSON-LD `@context` → MAVA ontology                                       |
| Schema            | Table Schema (columns, types, constraints) | Track types (ObservationSeries, AnnotationSeries) with ontology mappings |
| Multi-file corpus | Flat collection of unrelated tables        | Hierarchical structure (videos → tracks)                                 |
| Use case          | Data validation and publishing             | Tool interoperability with semantic precision                            |

### W3C Web Annotation

The W3C Web Annotation model is general-purpose but verbose and does not have
first-class support for dense numeric time-series (e.g. scores sampled every
0.5s). MediaPkg reuses the MAVA ontology's annotation vocabulary but does not
require full Web Annotation compliance.

### WebVTT

WebVTT is well-suited for subtitles but is a plain text format with no support
for structured or numeric properties. It cannot represent multi-dimensional
observation scores or structured interval annotations.

---

## 4. File Format

### Extension and MIME type

- File extension: `.mediapkg`
- MIME type: `application/vnd.mava.mediapkg+zip` (provisional)

### Structure

A `.mediapkg` file MUST be a valid ZIP archive (as defined by
[PKWARE ZIP](https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT)) using
DEFLATE compression.

It MUST contain a `manifest.json` at the root of the archive.

It MUST contain at least one Parquet file referenced by the manifest.

```
corpus.mediapkg
  manifest.json
  video_001/
    emotions.parquet
    transcript.parquet
    shots.parquet
    face_emotions.parquet
  video_002/
    emotions.parquet
    transcript.parquet
    ...
```

Each video's files MUST be contained in a folder named by the video's `id` as
declared in the manifest.

---

## 5. manifest.json

The `manifest.json` file is the entry point to a `.mediapkg` archive. It MUST be
valid JSON and MUST be located at the root of the ZIP archive.

### Top-level fields

| Field         | Type         | Required | Description                                               |
| ------------- | ------------ | -------- | --------------------------------------------------------- |
| `version`     | string       | MUST     | Format version. Currently `"0.2"`.                        |
| `created`     | string       | MUST     | ISO 8601 datetime of package creation.                    |
| `ontology`    | string (URI) | MUST     | URI of the MAVA ontology.                                 |
| `context`     | object       | MUST     | JSON-LD `@context` mapping column names to ontology URIs. |
| `tracks`      | object       | MUST     | Track definitions describing each Parquet file type.      |
| `videos`      | array        | MUST     | One entry per video. Must contain at least one entry.     |
| `description` | string       | OPTIONAL | Human-readable description of the corpus.                 |

### Example

```json
{
  "version": "0.2",
  "created": "2025-08-12T10:00:00+00:00",
  "description": "Emotion and transcript annotations for talk recordings",
  "ontology": "http://example.org/mava/ontology#",
  "context": {
    "@context": {
      "xsd": "http://www.w3.org/2001/XMLSchema#",
      "mava": "http://example.org/mava/ontology#",
      "start_seconds": { "@id": "mava:atTime", "@type": "xsd:decimal" },
      "end_seconds": { "@id": "mava:endTime", "@type": "xsd:decimal" },
      "annotations": { "@id": "mava:stringValue", "@type": "xsd:string" }
    }
  },
  "tracks": {},
  "videos": []
}
```

### The `context` field

The `context` field MUST contain a JSON-LD `@context` object that maps every
column name used in any Parquet file in the archive to a term in the MAVA
ontology. This is the single authoritative semantic mapping for the whole corpus
— it is not duplicated per file.

A consumer that wishes to reconstruct RDF triples from the Parquet data MUST use
this context.

### The `tracks` field

The `tracks` field is an object where each key is a track name and each value
describes one type of annotation file. Track names MUST be lowercase strings
with no spaces (use underscores).

Each track entry MUST contain:

| Field                       | Type             | Required                                    | Description                                                                                                            |
| --------------------------- | ---------------- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `type`                      | string           | MUST                                        | One of `"mava:ObservationSeries"`, `"mava:AnnotationSeries"`, `"mava:AnnotationListSeries"`, or `"mava:RegionSeries"`. |
| `description`               | string           | MUST                                        | Human-readable description of the track.                                                                               |
| `columns`                   | array of strings | MUST                                        | Ordered list of column names in the Parquet file.                                                                      |
| `dimensions`                | object           | MUST for `ObservationSeries`/`RegionSeries` | Maps each value column name to its description and value range.                                                        |
| `sampling_interval_seconds` | number           | OPTIONAL                                    | For `ObservationSeries` / `RegionSeries`: the sampling interval in seconds.                                            |
| `coordinate_space`          | string           | OPTIONAL                                    | For `RegionSeries`: `"normalized"` (geometry in `[0,1]` of the frame) or `"pixel"`. Defaults to `"normalized"`.        |
| `parent`                    | string           | OPTIONAL                                    | Containment parent: the name of the track this one lives under. At most one; the parent graph MUST be acyclic.         |
| `derived_from`              | array of strings | OPTIONAL                                    | Provenance: names of the tracks this track is computed from (1..n).                                                    |
| `method`                    | string           | MUST when `derived_from` present            | How the track was derived, e.g. `"argmax"`, `"cluster_to_scalar"`, `"aggregate_scalar"`.                               |

**Track relationships.** `parent` and `derived_from` are two distinct edges and
MUST NOT be conflated. `parent` is single-valued containment (where a track
lives in the tree); `derived_from` is multi-valued provenance (what a track was
computed from). A track MAY have both at once — e.g. a join that lives under an
"aggregations" container (`parent`) yet is computed from several source tracks
(`derived_from`). Every name referenced by `parent` or `derived_from` MUST be a
track defined in `tracks`, and the `parent` graph MUST be acyclic.

#### Track example — ObservationSeries

```json
"emotions": {
  "type": "mava:ObservationSeries",
  "description": "Per-frame probability scores from face analysis, sampled every 0.5s.",
  "sampling_interval_seconds": 0.5,
  "columns": ["start_seconds", "angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"],
  "dimensions": {
    "angry":    {"description": "Anger probability score",    "range": "[0,1]"},
    "disgust":  {"description": "Disgust probability score",  "range": "[0,1]"},
    "fear":     {"description": "Fear probability score",     "range": "[0,1]"},
    "happy":    {"description": "Happiness probability score","range": "[0,1]"},
    "sad":      {"description": "Sadness probability score",  "range": "[0,1]"},
    "surprise": {"description": "Surprise probability score", "range": "[0,1]"},
    "neutral":  {"description": "Neutral expression score",   "range": "[0,1]"}
  }
}
```

#### Track example — AnnotationSeries

```json
"transcript": {
  "type": "mava:AnnotationSeries",
  "description": "Speech-to-text segments from Whisper transcription model.",
  "columns": ["start_seconds", "end_seconds", "annotations"]
}
```

#### Track example - AnnotationListSeries

```json
"scene_tags": {
  "type": "mava:AnnotationListSeries",
  "description": "Scene classification tags from Places3 model (indoor/outdoor + natural/man-made)",
  "columns": ["start_seconds", "end_seconds", "annotations"]
}
```

### The `videos` field

The `videos` field MUST be an array with at least one entry. Each entry
describes one video in the corpus.

| Field              | Type         | Required | Description                                                                         |
| ------------------ | ------------ | -------- | ----------------------------------------------------------------------------------- |
| `id`               | string       | MUST     | Unique identifier for this video. Used as the folder name inside the ZIP.           |
| `src`              | string (URI) | MUST     | URI or filename of the original video file.                                         |
| `files`            | object       | MUST     | Maps track name → path of the Parquet file inside the ZIP.                          |
| `title`            | string       | OPTIONAL | Human-readable title.                                                               |
| `duration_seconds` | number       | OPTIONAL | Total duration of the video in seconds.                                             |
| `width`            | integer      | OPTIONAL | Frame width in pixels. Recoverable absolute geometry for normalized `RegionSeries`. |
| `height`           | integer      | OPTIONAL | Frame height in pixels.                                                             |
| `fps`              | number       | OPTIONAL | Frame rate in frames per second.                                                    |

#### Video entry example

```json
{
  "id": "video_001",
  "src": "https://example.org/videos/talk.mp4",
  "title": "Example Talk",
  "duration_seconds": 3600.0,
  "files": {
    "emotions": "video_001/emotions.parquet",
    "transcript": "video_001/transcript.parquet",
    "shots": "video_001/shots.parquet",
    "face_emotions": "video_001/face_emotions.parquet"
  }
}
```

---

## 6. Track Types

MediaPkg defines four track types. The core distinction in the MAVA ontology is
between dense time-series data (`ObservationSeries`) and sparse interval
annotations (`AnnotationSeries`, `AnnotationListSeries`); `RegionSeries` (added
in 0.2) extends the model to spatial detections such as bounding boxes.

### 6.1 ObservationSeries

An `ObservationSeries` is a dense, regularly sampled time-series of numeric
values. Each row is a `mava:ObservationPoint`.

**Required columns:**

| Column          | Maps to       | Parquet type | Description                                                                |
| --------------- | ------------- | ------------ | -------------------------------------------------------------------------- |
| `start_seconds` | `mava:atTime` | `DOUBLE`     | Time of the observation in seconds from video start. MUST be non-negative. |

**Dimension columns:** One column per declared dimension. Column names MUST
match the keys in the track's `dimensions` object in the manifest. Values MUST
be numeric (`xsd:decimal`).

**Examples of ObservationSeries tracks:** emotion scores, explosion detection
scores, interior/exterior classification scores, any dense ML model output.

### 6.2 AnnotationSeries

An `AnnotationSeries` is a sparse set of interval annotations. Each row is a
`mava:AnnotationSegment` with a start time, end time, and a string value.

**Required columns:**

| Column          | Maps to            | Parquet type | Description                                                           |
| --------------- | ------------------ | ------------ | --------------------------------------------------------------------- |
| `start_seconds` | `mava:startTime`   | `DOUBLE`     | Start of the interval in seconds. MUST be non-negative.               |
| `end_seconds`   | `mava:endTime`     | `DOUBLE`     | End of the interval in seconds. MUST be greater than `start_seconds`. |
| `annotations`   | `mava:stringValue` | `STRING`     | The annotation value for this segment.                                |

### 6.3 AnnotationListSeries

An `AnnotationListSeries` is a sparse set of interval annotations where each
segment has multiple simultaneous values. Each row is a
mava:AnnotationListSegment with a start time, end time, and a list of strings.

**Required columns:**

| Column          | Maps to          | Parquet type   | Description                                                           |
| --------------- | ---------------- | -------------- | --------------------------------------------------------------------- |
| `start_seconds` | `mava:startTime` | `DOUBLE`       | Start of the interval in seconds. MUST be non-negative.               |
| `end_seconds`   | `mava:endTime`   | `DOUBLE`       | End of the interval in seconds. MUST be greater than `start_seconds`. |
| `annotations`   | `mava:listValue` | `LIST<STRING>` | A list of string annotations for this segment.                        |

**Note on duration:** Duration is not stored as a column — it is derivable as
`end_seconds - start_seconds`. This avoids redundancy and potential
inconsistency.

**Note on timecodes:** Human-readable timecode strings (e.g. `HH:MM:SS.ms`) are
not stored in the interchange format. They are derivable from seconds and add no
information. Tools that need to display timecodes MUST compute them from
`start_seconds` / `end_seconds`.

**Examples of AnnotationSeries tracks:** shot boundaries, speech-to-text
transcripts, face emotion labels, scene labels.

### 6.4 RegionSeries

A `RegionSeries` is a series of spatial detections over time, in **long
format**: one row per detection, so many rows MAY share the same
`start_seconds`. Each row is a `mava:RegionDetection` — a bounding box with a
detection score and an identity. It was added in 0.2 for face/object detections.

**Required columns:**

| Column          | Maps to               | Parquet type | Description                                                               |
| --------------- | --------------------- | ------------ | ------------------------------------------------------------------------- |
| `start_seconds` | `mava:atTime`         | `DOUBLE`     | Time of the detection in seconds from video start. MUST be non-negative.  |
| `x`             | `mava:x`              | `DOUBLE`     | Box left edge. In `[0,1]` when `coordinate_space` is `"normalized"`.      |
| `y`             | `mava:y`              | `DOUBLE`     | Box top edge (top-left origin). In `[0,1]` when normalized.               |
| `w`             | `mava:width`          | `DOUBLE`     | Box width. In `[0,1]` when normalized.                                    |
| `h`             | `mava:height`         | `DOUBLE`     | Box height. In `[0,1]` when normalized.                                   |
| `det_score`     | `mava:detectionScore` | `DOUBLE`     | Detection confidence. MUST be in `[0,1]`.                                 |
| `cluster_id`    | `mava:clusterId`      | `INT64`      | Machine cluster the detection belongs to. MUST be present.                |
| `label`         | `mava:identityLabel`  | `STRING`     | Human identity label. Nullable; not unique and not 1:1 with `cluster_id`. |

`x`, `y`, `w`, `h`, and `det_score` are **dimension columns** declared in the
track's `dimensions` object, exactly as for `ObservationSeries`. `cluster_id`
and `label` are **fixed columns** present in every `RegionSeries`.

**Coordinate space.** The optional `coordinate_space` field on the track is
`"normalized"` (default — geometry in `[0,1]` of the frame) or `"pixel"`
(absolute pixels). When the space is `"normalized"`, `x`, `y`, `w`, `h` MUST lie
in `[0,1]`. Absolute pixel geometry is recoverable from normalized values via
the video's `width` / `height`.

**Identity model.** Identity lives on the timed rows, not in a sidecar.
`cluster_id` is the unsupervised machine cluster (stable, always present).
`label` is a human-applied name that MAY be missing, and several clusters MAY
share one label (e.g. a person split across clusters). Consumers MUST NOT assume
`cluster_id` ↔ `label` is one-to-one, and MUST NOT require label completeness
or uniqueness.

#### Track example — RegionSeries

```json
"face_regions": {
  "type": "mava:RegionSeries",
  "description": "Per-frame face bounding boxes, sampled every 0.5s. Coordinates normalized to [0,1] of the frame, top-left origin.",
  "sampling_interval_seconds": 0.5,
  "coordinate_space": "normalized",
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

**Examples of RegionSeries tracks:** face bounding boxes, object detections, any
localized per-frame spatial annotation.

---

## 7. Parquet Files

### Encoding

Each Parquet file in a `.mediapkg` archive MUST conform to the
[Apache Parquet format specification](https://parquet.apache.org/docs/file-format/).

Column names MUST match the `columns` array declared for the track in the
manifest exactly, in the declared order.

### Column types

There are two kinds of columns:

**Fixed columns** have the same name in every track that uses them:
`start_seconds`, `end_seconds`, `annotations`, and (for `RegionSeries`)
`cluster_id` and `label`. Their Parquet type is always the same.

**Dimension columns** have variable names — whatever was declared in the track's
`dimensions` object in the manifest. Their Parquet type is always `DOUBLE`
regardless of the name.

| Column               | Parquet type                       | Notes                                            |
| -------------------- | ---------------------------------- | ------------------------------------------------ |
| `start_seconds`      | `DOUBLE`                           | Fixed name, always present                       |
| `end_seconds`        | `DOUBLE`                           | Fixed name, AnnotationSeries only                |
| Dimension columns    | `DOUBLE`                           | Variable names, ObservationSeries / RegionSeries |
| `annotations`        | `BYTE_ARRAY` (UTF-8 string)        | Fixed name, AnnotationSeries only                |
| `annotations` (list) | `LIST<BYTE_ARRAY>` (UTF-8 strings) | Fixed name, AnnotationListSeries only            |
| `cluster_id`         | `INT64`                            | Fixed name, RegionSeries only                    |
| `label`              | `BYTE_ARRAY` (UTF-8 string)        | Fixed name, RegionSeries only; nullable          |

#### Example — ObservationSeries (emotions track)

The dimension columns are `angry`, `fear`, `happy`, `sad`, `neutral` — the names
declared in the track's `dimensions` object. All are `DOUBLE`.

```
emotions.parquet
┌───────────────┬─────────┬─────────┬─────────┬─────────┬─────────┐
│ start_seconds │  angry  │  fear   │  happy  │   sad   │ neutral │
│    DOUBLE     │ DOUBLE  │ DOUBLE  │ DOUBLE  │ DOUBLE  │ DOUBLE  │
├───────────────┼─────────┼─────────┼─────────┼─────────┼─────────┤
│     0.000     │  0.021  │  0.014  │  0.743  │  0.011  │  0.211  │
│     0.500     │  0.034  │  0.009  │  0.698  │  0.028  │  0.231  │
│     1.000     │  0.018  │  0.022  │  0.712  │  0.015  │  0.233  │
└───────────────┴─────────┴─────────┴─────────┴─────────┴─────────┘
```

A different tool producing explosion scores would have different dimension
column names but the same structure:

```
explosion.parquet
┌───────────────┬───────────┐
│ start_seconds │ explosion │
│    DOUBLE     │  DOUBLE   │
├───────────────┼───────────┤
│     0.000     │   0.003   │
│     0.100     │   0.011   │
│     0.200     │   0.842   │
└───────────────┴───────────┘
```

#### Example — AnnotationSeries (transcript track)

No dimension columns. Fixed columns `start_seconds`, `end_seconds`,
`annotations` only.

```
transcript.parquet
┌───────────────┬─────────────┬──────────────────────────────────┐
│ start_seconds │ end_seconds │           annotations            │
│    DOUBLE     │   DOUBLE    │           BYTE_ARRAY             │
├───────────────┼─────────────┼──────────────────────────────────┤
│     0.000     │    12.300   │ "Welcome to the conference."     │
│    12.500     │    29.800   │ "Today we discuss annotation."   │
│    30.100     │    45.000   │ "Thank you for joining us."      │
└───────────────┴─────────────┴──────────────────────────────────┘
```

#### Example — AnnotationListSeries (scene_tags track)

Similar to the AnnotationSeries, just that the annotations are lists of variable
length such as tags.

```
scene_tags.parquet
┌───────────────┬─────────────┬───────────────────────────┐
│ start_seconds │ end_seconds │       annotations         │
│    DOUBLE     │   DOUBLE    │     LIST<STRING>          │
├───────────────┼─────────────┼───────────────────────────┤
│     0.000     │    45.200   │ ["outdoor", "natural"]    │
│    45.200     │    78.500   │ ["indoor"]                │
│    78.500     │   120.000   │ ["outdoor", "man-made"]   │
└───────────────┴─────────────┴───────────────────────────┘

```

#### Example — RegionSeries (face_regions track)

Long format: one row per detection, so several rows share a `start_seconds`.
Dimension columns `x`, `y`, `w`, `h`, `det_score` plus the fixed `cluster_id`
and `label`. `label` is nullable (cluster known, name not yet assigned).

```
face_regions.parquet
┌───────────────┬────────┬────────┬────────┬────────┬───────────┬────────────┬────────┐
│ start_seconds │   x    │   y    │   w    │   h    │ det_score │ cluster_id │ label  │
│    DOUBLE     │ DOUBLE │ DOUBLE │ DOUBLE │ DOUBLE │  DOUBLE   │   INT64    │ STRING │
├───────────────┼────────┼────────┼────────┼────────┼───────────┼────────────┼────────┤
│    65.500     │ 0.4557 │ 0.1019 │ 0.1966 │ 0.4037 │  0.8237   │     7      │ Joanne │
│    66.000     │ 0.5141 │ 0.2361 │ 0.2073 │ 0.4486 │  0.7944   │     7      │ Joanne │
│    66.000     │ 0.1204 │ 0.3017 │ 0.1500 │ 0.4727 │  0.8125   │    19      │  null  │
└───────────────┴────────┴────────┴────────┴────────┴───────────┴────────────┴────────┘
```

### Compression

Parquet files SHOULD use Snappy or ZSTD compression for row groups. The ZIP
archive provides additional compression on top.

### Row ordering

Rows in an `ObservationSeries` file MUST be ordered by `start_seconds`
ascending.

Rows in an `AnnotationSeries` file SHOULD be ordered by `start_seconds`
ascending.

Rows in a `RegionSeries` file MUST be ordered by `start_seconds` non-strictly
ascending — equal values are expected, since the long format puts multiple
detections at the same time on consecutive rows.

---

## 8. Ontology and Semantic Layer

### MAVA Ontology

All semantic terms used in MediaPkg are defined in the MAVA ontology at
`http://example.org/mava/ontology#`. The ontology is provided in Turtle (`.ttl`)
format in the `spec/` directory of this repository.

The ontology defines:

- `mava:VideoCorpus` — a collection of videos
- `mava:Video` — a single video resource
- `mava:MediaPackage` — a `.mediapkg` archive
- `mava:ObservationSeries` / `mava:ObservationPoint` — dense time-series
  analysis
- `mava:AnnotationSeries` / `mava:AnnotationSegment` /
  `mava:AnnotationListSegment` — sparse interval annotations
- `mava:RegionSeries` / `mava:RegionDetection` — spatial detections (bounding
  boxes), long format
- `mava:Dimension` — a single measured quantity within an ObservationSeries or
  RegionSeries
- Time properties: `mava:atTime`, `mava:startTime`, `mava:endTime`
- Value properties: `mava:numericValue`, `mava:stringValue`, `mava:listValue`
- Region geometry / identity: `mava:x`, `mava:y`, `mava:width`, `mava:height`,
  `mava:detectionScore`, `mava:coordinateSpace`, `mava:clusterId`,
  `mava:identityLabel`
- Track relationships: `mava:hasParent` (containment), `mava:derivedFrom` +
  `mava:derivationMethod` (provenance)

### JSON-LD Context

The `context` field in the manifest is a JSON-LD `@context` that maps Parquet
column names to MAVA ontology term URIs. A consumer that reads a `.mediapkg`
file and wishes to export RDF MUST use this context to expand column names to
full URIs before serialising.

### Reused Vocabularies

| Prefix     | Namespace                           | Used for                  |
| ---------- | ----------------------------------- | ------------------------- |
| `mava:`    | `http://example.org/mava/ontology#` | All domain-specific terms |
| `xsd:`     | `http://www.w3.org/2001/XMLSchema#` | Datatype declarations     |
| `dcterms:` | `http://purl.org/dc/terms/`         | Ontology metadata         |

---

## 9. Validation

### Manifest validation

A `manifest.json` MUST be valid JSON. Implementations SHOULD validate it against
the JSON Schema provided at `spec/manifest.schema.json` in this repository.

### Ontology validation (SHACL)

SHACL shapes for validating RDF data exported from a `.mediapkg` are included in
`spec/mava.ttl`. The shapes enforce:

- Every `ObservationPoint` has exactly one `mava:atTime` value (non-negative)
  and belongs to an `ObservationSeries`
- Every `AnnotationSegment` has exactly one `mava:startTime` and one
  `mava:endTime` (both non-negative) and belongs to an `AnnotationSeries`
- Every `ObservationSeries` has a description and at least one declared
  dimension
- Every `RegionDetection` has exactly one `mava:atTime` (non-negative), belongs
  to a `RegionSeries`, and carries box geometry, a cluster id, and (optionally)
  a label
- Every `Dimension` has exactly one name matching a Parquet column

### Package validation

Implementations SHOULD verify that:

- Every file referenced in `manifest.videos[*].files` exists in the ZIP archive
- Column names in each Parquet file match the `columns` array for that track in
  the manifest
- `end_seconds > start_seconds` for all rows in `AnnotationSeries` files
- `start_seconds >= 0` for all rows
- For `RegionSeries`: `cluster_id` and `label` columns are declared; geometry
  and `det_score` columns are numeric; `det_score` is in `[0,1]`; and when
  `coordinate_space` is `"normalized"`, `x` / `y` / `w` / `h` are in `[0,1]`
- For track relationships: every `parent` and `derived_from` names an existing
  track, `method` is present whenever `derived_from` is, and the `parent` graph
  is acyclic

---

## 10. Corpus Packages

A single `.mediapkg` file MAY contain annotations for more than one video. This
is the primary mechanism for distributing a corpus.

### Combining packages

Two or more single-video `.mediapkg` files MAY be combined into a corpus
package. When combining:

- The `videos` arrays from all input packages MUST be merged
- Each video `id` MUST be unique within the combined manifest — implementors
  MUST check for conflicts before combining
- The `context` and `tracks` from the first package are used as the basis;
  implementations SHOULD warn if input packages have conflicting contexts or
  track definitions
- All Parquet files from input packages are included unchanged, preserving their
  folder structure

### Splitting packages

A corpus package MAY be split into individual video packages by extracting each
video's folder and writing a manifest containing only that video's entry.

---

## 11. Design Decisions

### Why ZIP and not a single Parquet file?

A single Parquet file cannot contain a corpus-level manifest or multiple videos
with heterogeneous track schemas. ZIP is universally supported, allows
incremental reading, and provides an additional compression layer on top of
Parquet's own compression.

### Why Parquet and not Arrow IPC?

Parquet provides better compression (important for transfer) and broader
ecosystem support. Arrow IPC is faster to write but produces larger files. For
an interchange format where transfer efficiency matters, Parquet is the better
choice. Individual tools may use Arrow IPC internally.

### Why not RDF/Turtle directly?

Serialising a single video's annotations as RDF took approximately ten minutes
in practice. Parquet serialisation of the same data takes under a second. RDF
export remains possible as a derived output — a tool can read a `.mediapkg` and
export Turtle using the JSON-LD context — but it is not the primary interchange
mechanism.

### Why `end_seconds` instead of `duration_seconds`?

End time is more directly useful for querying: "find all annotations overlapping
timestamp X" requires `start_seconds <= X AND end_seconds >= X`. With duration
you would need to compute `start + duration` in every query. Duration is
trivially derivable as `end - start`.

### Why no timecode columns?

Timecode strings (`HH:MM:SS.ms`) are derivable from seconds and add no
information. Including them in every row would increase file size and introduce
potential inconsistencies. Tools that need to display timecodes compute them at
render time.

### Why are dimension names not ontology properties?

The MAVA ontology does not define properties for specific score types (e.g.
`mava:angryScore`). Instead, `mava:Dimension` allows any measured quantity to be
declared per series in the manifest. This means the ontology does not need to
change when new ML models with new output types are introduced — only the
manifest's `dimensions` object needs updating.

### Why JSON-LD for the context and not plain URI mappings?

JSON-LD is a W3C standard for embedding linked data semantics in JSON. It is
machine-actionable: a JSON-LD processor can expand column names to full URIs and
convert rows to RDF triples without any custom code. Plain URI mappings would
require a custom parser. Both approaches store the same information, but JSON-LD
is more interoperable.

---

_MediaPkg v0.2 Draft — ETH Zurich / Swiss Data Science Center_
