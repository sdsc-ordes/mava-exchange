# Add a new track type

Use this skill when adding a new track type class to mava-exchange. It encodes
the complete safe workflow so all guards are satisfied before the work is done.

## Inputs

The user must supply:

- **Track type name** (e.g., `ScoreSeries`, `KeyframeSeries`)
- **Description** of what it models
- **Data shape**: what columns does a conforming DataFrame have?
- **Relationship to existing types**: is it closest to `ObservationSeries`
  (dense numeric), `AnnotationSeries` (sparse string intervals), or
  `AnnotationListSeries` (sparse multi-label intervals)?

If any of these are unclear, ask before proceeding.

## Steps

### 1. Read the spec and ontology

Before writing any code, read:

- `spec/SPEC.md` — specifically the section on track types (search for "Track
  Types" and "ObservationSeries")
- `spec/mava.ttl` — look at how existing track types are modelled (search for
  `mava:ObservationSeries`)
- `src/mava_exchange/tracks.py` — read the full file to understand the dataclass
  conventions

**Flag**: if the new track type requires a new ontology term in `spec/mava.ttl`,
stop and note this explicitly. Ontology changes are human-owned — propose the
addition but do not make it without approval.

### 2. Add the class to `tracks.py`

Follow the exact conventions of the existing dataclasses:

- Use `@dataclass`
- Set `type: Literal["mava:YourType"]` as a field with `init=False`
- Implement `columns` as a `@property` returning the list of required column
  names
- Implement `to_dict()` returning the manifest-compatible dict
- Add a docstring with an example `DataFrame`

The `type` literal must match an entry in `KNOWN_TRACK_TYPES` in `validate.py`.
If it doesn't, also add it there.

### 3. Export from `__init__.py`

Add the new class to:

- The import block in `src/mava_exchange/__init__.py`
- The `__all__` list

### 4. Update the validator if needed

If the new type has unique data constraints (e.g., new required columns, value
constraints), add a `_check_<type>` function in `validate.py` and call it from
`_validate_parquet`.

Only add a check if it enforces something the spec requires. Do not add
defensive checks for things that "might be nice."

### 5. Add a hypothesis strategy and roundtrip tests

In `tests/test_roundtrip.py`:

1. Add a `@st.composite` strategy `<type_name>_with_data(draw)` following the
   pattern of the existing strategies (see `observation_series_with_data`,
   `annotation_series_with_data`).

2. Add two property tests:
   - `test_<type_name>_roundtrip_clean` — write → `validate_mediapkg` → no
     errors
   - `test_<type_name>_roundtrip_fidelity` — write → read → DataFrame matches

Use
`@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])`.

### 6. Run the guard layers

```bash
just test       # must pass with ≥85% coverage
just lint       # must pass clean
just typecheck  # must pass clean
```

Do not declare the task done until all three pass.

### 7. Checklist before finishing

- [ ] New class follows the `@dataclass` conventions in `tracks.py`
- [ ] `type` literal is in `KNOWN_TRACK_TYPES` in `validate.py`
- [ ] Exported from `__init__.py` and in `__all__`
- [ ] Hypothesis strategy generates valid DataFrames (no manual construction)
- [ ] Both roundtrip property tests pass
- [ ] `just test` passes with coverage gate
- [ ] `just lint` and `just typecheck` pass clean
- [ ] If a new ontology term is needed: flagged for human review, not added
      silently
