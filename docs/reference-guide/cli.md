# Command Line Tools

Two CLI tools for working with `.mediapkg` files without writing code.

## mediapkg-inspect

Inspect package contents and display track data.

### Basic Usage

```bash
# Show package overview
mediapkg-inspect corpus.mediapkg
```

Output:

```
════════════════════════════════════════════════════════════
  corpus.mediapkg
════════════════════════════════════════════════════════════

Version:     0.1
Created:     2025-08-12T10:00:00+00:00
Ontology:    http://example.org/mava/ontology#
Description: My annotation corpus
Videos:      2

Tracks:
  emotions               mava:ObservationSeries  @0.5s  [angry, happy, neutral]
  transcript             mava:AnnotationSeries

Videos:
  video_001
    src:    https://example.org/video.mp4
    tracks: emotions, transcript

Files:
  Path                                          Rows     Raw   Compressed  Saved
  -------------------------------------------- ------  ------  ----------  -----
  video_001/emotions.parquet                      100   8.2KB      3.1KB    62%
  video_001/transcript.parquet                      3   2.1KB      1.4KB    33%
```

### Inspect a Specific Track

```bash
# Show track definition and first 5 rows (default)
mediapkg-inspect corpus.mediapkg --track emotions

# Show more rows
mediapkg-inspect corpus.mediapkg --track emotions --head 20

# Specify which video (for multi-video packages)
mediapkg-inspect corpus.mediapkg --track emotions --video video_001
```

Output:

```
Track:   emotions  (mava:ObservationSeries)
Video:   video_001
Desc:    Face emotion scores from DeepFace model
Rows:    100

Columns:
  start_seconds          float64
  angry                  float64
  happy                  float64
  neutral                float64

First 5 rows:
  start_seconds     angry     happy   neutral
            0.0  0.124510  0.642310  0.233180
            0.5  0.087340  0.712040  0.200620
            1.0  0.210030  0.558910  0.231060
            1.5  0.156780  0.623450  0.219770
            2.0  0.198230  0.589120  0.212650

Dimensions:
  angry                Anger probability    [0,1]
  happy                Happiness probability  [0,1]
  neutral              Neutral expression   [0,1]
```

### Export as RDF

```bash
# Export manifest as Turtle
mediapkg-inspect corpus.mediapkg --format turtle > manifest.ttl

# Export as JSON-LD
mediapkg-inspect corpus.mediapkg --format json-ld > manifest.jsonld
```

Requires the `rdf` extra:

```bash
pip install mava-exchange[rdf]
```

### Options

| Option         | Description                             | Default                |
| -------------- | --------------------------------------- | ---------------------- |
| `--track NAME` | Show specific track details             | None (shows overview)  |
| `--video ID`   | Video to use with --track               | First video in package |
| `--head N`     | Number of rows to display               | 5                      |
| `--format FMT` | Output format: summary, turtle, json-ld | summary                |

---

## mediapkg-validate

Validate package structure and data integrity.

### Basic Usage

```bash
mediapkg-validate corpus.mediapkg
```

### Valid Package Output

```
════════════════════════════════════════════════════════════
  Validating: corpus.mediapkg
════════════════════════════════════════════════════════════

Manifest:
  Top-level fields...
  Tracks...
  Videos...

Parquet files:
  video_001/emotions.parquet...
  video_001/transcript.parquet...

✓ VALID  —  45 checks, 0 errors, 0 warnings
```

Exit code: `0`

### Invalid Package Output

```
════════════════════════════════════════════════════════════
  Validating: corpus.mediapkg
════════════════════════════════════════════════════════════

Manifest:
  Top-level fields...
  Tracks...
  Videos...

Parquet files:
  video_001/emotions.parquet...

Errors:
  ✗ video_001/emotions.parquet: start_seconds has negative values
  ✗ video_001/transcript.parquet: 3 row(s) where end_seconds <= start_seconds

✗ INVALID  —  42 checks, 2 errors, 0 warnings
```

Exit code: `1`

### Strict Mode

Warns about recommended but optional fields:

```bash
mediapkg-validate corpus.mediapkg --strict
```

Additional warnings for:

- Missing track descriptions
- Missing `sampling_interval_seconds` for ObservationSeries
- Unexpected extra columns in Parquet files

### Use in CI/CD

```bash
# Fail build if invalid
mediapkg-validate corpus.mediapkg || exit 1

# GitHub Actions example
- name: Validate package
  run: mediapkg-validate output/corpus.mediapkg
```

### Options

| Option     | Description                         |
| ---------- | ----------------------------------- |
| `--strict` | Enable warnings for optional fields |

### Exit Codes

| Code | Meaning            |
| ---- | ------------------ |
| 0    | Package is valid   |
| 1    | Package has errors |

---

## Common Workflows

### Quick validation before sharing

```bash
mediapkg-validate corpus.mediapkg && echo "Ready to share!"
```

### Inspect then validate

```bash
# See what's in the package
mediapkg-inspect corpus.mediapkg

# Make sure it's valid
mediapkg-validate corpus.mediapkg --strict
```

### Check specific track data

```bash
# Overview
mediapkg-inspect corpus.mediapkg

# Drill into suspicious track
mediapkg-inspect corpus.mediapkg --track emotions --head 20
```

### Export metadata for archiving

```bash
# Create human-readable summary
mediapkg-inspect corpus.mediapkg > corpus_summary.txt

# Create machine-readable RDF
mediapkg-inspect corpus.mediapkg --format turtle > corpus_manifest.ttl
```
