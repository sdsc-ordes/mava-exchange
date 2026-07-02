# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-06-22

Format version `0.1` → `0.2`. **Additive** — all `0.1` packages remain valid
`0.2` packages. The only backward-incompatibility is in the other direction: a
strict `0.1` reader rejects the new `mava:RegionSeries` track type and the new
manifest fields below. Readers that ignore unknown track types and fields are
unaffected.

### Added

- `RegionSeries` track type for spatial detections (bounding boxes), in long
  format — one row per detection. Geometry is `x` / `y` / `w` / `h` plus a
  `det_score`, with an optional `coordinate_space` (`"normalized"` default, or
  `"pixel"`).
- Per-row identity on `RegionSeries`: `cluster_id` (machine cluster, integer)
  and a nullable `label` (human identity; not unique, not 1:1 with cluster).
- Track hierarchy and provenance on every track type: `parent` (containment,
  acyclic), `derived_from` (sources) and `method` (derivation method, required
  when `derived_from` is present).
- Optional video frame metadata: `width`, `height`, `fps`.
- Ontology (`mava.ttl`): `mava:RegionSeries`, `mava:RegionDetection`, geometry
  and identity properties (`mava:x`, `mava:y`, `mava:width`, `mava:height`,
  `mava:detectionScore`, `mava:coordinateSpace`, `mava:clusterId`,
  `mava:identityLabel`), and relationship properties (`mava:hasParent`,
  `mava:derivedFrom`, `mava:derivationMethod`). SHACL shapes for the new class
  and properties.
- Validator (`validate_mediapkg`): accepts version `"0.2"` and `RegionSeries`;
  checks region geometry/score ranges and the `parent` / `derived_from` /
  `method` relationship rules.

### Changed

- Ontology: `mava:atTime` domain widened to include `mava:RegionDetection`;
  `mava:hasAnalysis` range widened to include `mava:RegionSeries`.

## [0.1.1] - 2026-04-15

### Added

- Relax Python version requirement to >=3.12

## [0.1.0] - 2026-03-23

### Added

- Initial public release
- `MediaPackageWriter` for creating `.mediapkg` archives
- `MediaPackageReader` for reading and inspecting packages
- Three track types: `ObservationSeries`, `AnnotationSeries`,
  `AnnotationListSeries`
- CLI tools: `mediapkg-validate` and `mediapkg-inspect`
- Package validation against MAVA specification
- Comprehensive Sphinx documentation with Furo theme
- Interactive web viewer for `.mediapkg` files
- PyLODE-generated ontology documentation
- GitHub Actions workflow for automatic documentation deployment

[Unreleased]: https://github.com/sdsc-ordes/mava-exchange/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/sdsc-ordes/mava-exchange/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/sdsc-ordes/mava-exchange/releases/tag/v0.1.0
