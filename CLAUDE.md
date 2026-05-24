# mava-exchange — AI Contributor Guide

`mava-exchange` is a Python library for reading and writing `.mediapkg` files:
ZIP-based containers for structured video annotations. It is part of the MAVA
project (SDSC national infrastructure).

## Human core — do not modify without explicit instruction

These files encode deliberate design decisions. Changing them has downstream
consequences (breaking changes to the format, ontology, or public API). Always
flag before touching.

| File                            | Why it's human-owned                                                                                                                                                 |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `spec/SPEC.md`                  | Formal RFC 2119 format specification — versioned deliberately                                                                                                        |
| `spec/mava.ttl`                 | RDF ontology — adding/renaming terms is a breaking change for consumers                                                                                              |
| `spec/mava.shacl.ttl`           | SHACL constraint shapes for RDF exports — must stay in sync with the ontology                                                                                        |
| `src/mava_exchange/tracks.py`   | Public type hierarchy (`ObservationSeries`, `AnnotationSeries`, `AnnotationListSeries`, `DimensionSpec`) — changing signatures or semantics is a breaking API change |
| `src/mava_exchange/__init__.py` | Public exports — only add here, never remove without a deprecation cycle                                                                                             |

## AI-delegatable surface

These files are safe to regenerate, refactor, or extend — the test suite and
guard layers will catch regressions.

- `src/mava_exchange/writer.py` — MediaPackageWriter implementation
- `src/mava_exchange/reader.py` — MediaPackageReader implementation
- `src/mava_exchange/cli.py` — CLI entry points (`mediapkg-inspect`,
  `mediapkg-validate`)
- `src/mava_exchange/validate.py` — validation logic (but: `validate_mediapkg`
  is the correctness oracle — don't weaken its checks)
- `tests/` — extend freely; never delete existing tests without justification
- `docs/` — prose, examples, tutorials

## Development commands

```bash
just test          # run pytest (with coverage gate)
just lint          # ruff check
just typecheck     # mypy strict
just audit         # pip-audit vulnerability scan
just format        # treefmt (ruff + prettier + typos + yamllint)
just build         # uv build
just build-docs    # sphinx + pylode
```

All commands assume `uv` is available. In the Nix dev shell:
`just develop just <target>`.

## Adding a new track type

Use `/project:add-track-type` — it encodes the complete safe workflow:

1. Check the ontology (`spec/mava.ttl`) for existing patterns
2. Add the class to `tracks.py` following the dataclass conventions
3. Export from `__init__.py`
4. Add a hypothesis strategy + roundtrip test in `tests/test_roundtrip.py`
5. Run `just test` — must pass before done
6. Flag if a new ontology term is needed

## Checking spec compliance

Use `/project:check-spec-compliance` on any PR touching `writer.py`,
`reader.py`, or `validate.py`.

## Correctness oracle

`validate_mediapkg(path)` (in `validate.py`) is the ground truth for what a
valid `.mediapkg` looks like. The roundtrip property tests in
`tests/test_roundtrip.py` use it as the oracle. If you change the validator, run
the full test suite — any regression in the property tests means a format
contract was broken.

## Conventions

- Python 3.12+, type hints required on all public functions
- Dataclasses for data-holding types (no attrs, no pydantic)
- No external HTTP calls, no global state
- Parquet column names must match the `DimensionSpec.name` values exactly
- `start_seconds` is always the first column in every track DataFrame
- `end_seconds` is required in AnnotationSeries and AnnotationListSeries but
  absent in ObservationSeries
- Test fixtures live in `tests/conftest.py` — add shared fixtures there, not
  inline

## Format version

The current format version is `0.1`. Bumping it requires a change to `SPEC.md`,
`mava.ttl`, and a migration note in `CHANGELOG.md`.
