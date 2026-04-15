# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/sdsc-ordes/mava-exchange/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sdsc-ordes/mava-exchange/releases/tag/v0.1.0
