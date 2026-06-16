# Check spec compliance

Use this skill on any PR that touches `writer.py`, `reader.py`, or
`validate.py`. It cross-checks the implementation against the formal MAVA
specification and reports gaps.

## When to use

- Before merging any PR that modifies the write/read/validate path
- After an AI-assisted contribution to the format implementation
- When reviewing whether a proposed change is spec-conformant

## Steps

### 1. Identify changed files

List the files changed in the current diff that are in scope:

- `src/mava_exchange/writer.py`
- `src/mava_exchange/reader.py`
- `src/mava_exchange/validate.py`

If none of these are changed, this skill is not needed.

### 2. Read the spec

Read `spec/SPEC.md` in full. Note every **MUST**, **MUST NOT**, **SHOULD**, and
**SHOULD NOT** clause.

Group them by area:

- Archive structure (ZIP, manifest location)
- Manifest fields (version, created, ontology, context, tracks, videos)
- Track definitions (type, columns, dimensions)
- Parquet data constraints (column names, types, ordering, nullability)
- Versioning rules

### 3. Cross-check each changed file

For each changed file, go through the spec clauses and check whether the
implementation satisfies them. Report as a table:

| Spec clause (paraphrased)             | Location in spec | Status | Notes                                |
| ------------------------------------- | ---------------- | ------ | ------------------------------------ |
| Manifest MUST contain `version` field | §3.1             | ✓ Pass | checked in `_check_top_level_fields` |
| `start_seconds` MUST be non-negative  | §4.2             | ✓ Pass | checked in `_check_start_seconds`    |
| ...                                   |                  |        |                                      |

Use these statuses:

- **✓ Pass** — implementation satisfies the clause
- **✗ Fail** — implementation violates or ignores the clause
- **⚠ Partial** — implementation partially satisfies the clause
- **? Unclear** — spec is ambiguous; note the ambiguity

### 4. Check the roundtrip property tests

Verify that `tests/test_roundtrip.py` has coverage for the changed behaviour:

- Is there a hypothesis strategy that generates inputs exercising the changed
  code path?
- Does the `validate_mediapkg` oracle catch the type of error that the changed
  code path could introduce?

If not, note what strategy or test is missing.

### 5. Report

Output a concise report structured as:

```
## Spec compliance report

**Files reviewed**: writer.py, validate.py
**Spec version**: 0.1 (spec/SPEC.md)

### MUST clauses: N checked, M passed, K failed

[table from step 3]

### SHOULD clauses: N checked, M passed, K warnings

[table]

### Missing test coverage

[list of gaps, if any]

### Recommendation

APPROVE / REQUEST CHANGES / NEEDS DISCUSSION
```

Do not propose fixes in this report — that is a separate task. The goal is a
clear, structured audit that a human reviewer can act on.
