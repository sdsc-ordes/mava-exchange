# mava-exchange v0.2 extensions — planning overview

This folder captures the analysis and plan for the next round of format
extensions, derived from exploring the `silent_child` example corpus (both the
processed Advene/EAF export **and** the raw platform DB in `raw_data/`).

## Goal

Extend the `.mediapkg` format with three related capabilities, all observed in
real data:

1. **Track hierarchy** — parent/child relationships between tracks.
2. **Clustering** — grouping detections into identities (e.g. faces → people).
3. **Bounding boxes** — a spatial track type (proposed `RegionSeries`).

## Files in this folder

| File                     | Purpose                                                                                  |
| ------------------------ | ---------------------------------------------------------------------------------------- |
| `00-overview.md`         | This file — context and reading order.                                                   |
| `01-data-analysis.md`    | **Preserved** findings from exploring `silent_child` (TSV/EAF export + raw platform DB). |
| `02-roadmap.md`          | The mental model, feature mapping, corrected conclusions, build order, and design facts. |
| `03-spike-next-steps.md` | Concrete steps to run the **step-0 design spike** in a fresh chat.                       |

Read in order: `01` (what the data is) → `02` (what we're building and why) →
`03` (what to do next).

## Status / key decisions already taken

- **Bounding boxes:** model as a NEW spatial track type `RegionSeries` (long
  format, one row per detection). NOT `ObservationListSeries`. Confirmed with
  the user.
- **Build philosophy:** de-risk first via a paper design spike on the _real_
  `face_clustering` data, THEN implement bottom-up (lowest surface → highest).
- **`ObservationListSeries`:** deferred (no compelling case; `Dominant Color(s)`
  is better as a 3-dimension `ObservationSeries`).
- **Version:** these are additive but break old readers → target a `0.1 → 0.2`
  bump (requires `SPEC.md`, `mava.ttl`, `mava.shacl.ttl`, and a `CHANGELOG.md`
  migration note).

## Human-core constraint (from `CLAUDE.md`)

Every one of these features touches **human-owned** files that must NOT be
changed without explicit instruction: `tracks.py`, `__init__.py`,
`spec/SPEC.md`, `spec/mava.ttl`, `spec/mava.shacl.ttl`. The spike is **paper
only** — it touches none of these.
