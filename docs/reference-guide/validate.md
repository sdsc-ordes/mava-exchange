# Validation

Check if `.mediapkg` files conform to the MAVA specification.

## Basic Usage

```python
from mava_exchange.validate import validate_mediapkg

result = validate_mediapkg("corpus.mediapkg")

if result.valid:
    print("✓ Package is valid")
else:
    print(result.summary())
```

## What Gets Validated

The validator checks:

### Package Structure

- ZIP archive is readable
- `manifest.json` exists at root
- All referenced Parquet files exist

### Manifest Contents

- Required fields present (version, created, ontology, tracks, videos)
- Track definitions are complete
- Video IDs are unique
- File paths match actual files in archive

### Parquet Data

- Columns match track definitions
- `start_seconds` is non-negative and sorted
- For annotations: `end_seconds > start_seconds`
- For observations: numeric dimensions with no nulls
- For list annotations: values are actually lists of strings

## Common Validation Tasks

### Check if package is valid

```python
from mava_exchange.validate import validate_mediapkg

result = validate_mediapkg("pkg.mediapkg")

if result.valid:
    print(f"✓ Package passed {result.checks} checks")
else:
    print(f"✗ Found {len(result.errors)} errors")
    for error in result.errors:
        print(error)
```

### Use strict mode

Strict mode warns about recommended but optional fields:

```python
result = validate_mediapkg("pkg.mediapkg", strict=True)

# Shows warnings for:
# - Missing track descriptions
# - Missing sampling_interval for ObservationSeries
# - Unexpected extra columns

print(result.summary())
```

### Command-line validation

```bash
# Basic validation
mediapkg-validate corpus.mediapkg

# Strict mode
mediapkg-validate corpus.mediapkg --strict

# Exit code: 0 if valid, 1 if invalid
mediapkg-validate corpus.mediapkg && echo "Valid!"
```

## Validation Output

### Valid package

```
═══════════════════════════════════════════════
  Validating: corpus.mediapkg
═══════════════════════════════════════════════

Manifest:
  Top-level fields...
  Tracks...
  Videos...

Parquet files:
  video_001/emotions.parquet...
  video_001/transcript.parquet...

✓ VALID  —  45 checks, 0 errors, 0 warnings
```

### Invalid package

```
═══════════════════════════════════════════════
  Validating: bad.mediapkg
═══════════════════════════════════════════════

Errors:
  ✗ video_001/emotions.parquet: start_seconds has negative values
  ✗ video_002/transcript.parquet: 3 row(s) where end_seconds <= start_seconds

✗ INVALID  —  42 checks, 2 errors, 0 warnings
```

## Common Errors

| Error                                   | Cause                              | Fix                                    |
| --------------------------------------- | ---------------------------------- | -------------------------------------- |
| `start_seconds has negative values`     | Time values < 0                    | Ensure all timestamps ≥ 0              |
| `rows not ordered by start_seconds`     | Data not sorted                    | Sort DataFrame before writing          |
| `end_seconds <= start_seconds`          | Invalid intervals                  | Check interval logic                   |
| `missing columns`                       | DataFrame missing required columns | Add all columns from track definition  |
| `annotations column must contain lists` | Used strings instead of lists      | Use AnnotationSeries for single labels |

## Function and Class References

For complete function and class documentation, see:

- [validate_mediapkg()](../generated/mava_exchange.validate.validate_mediapkg) -
  Validation function
- [ValidationResult](../generated/mava_exchange.validate.ValidationResult) -
  Result object
