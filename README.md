<p align="center">
  <img src="./docs/assets/mava_logo.svg" alt="project logo" width="250">
</p>

<h1 align="center">
  mava-exchange
</h1>
<p align="center">
</p>

![Current Release](https://img.shields.io/badge/release-v0.1.0-orange)
[![Pipeline Status](https://github.com/sdsc-ordes/mava-exchange/actions/workflows/normal.yaml/badge.svg)](https://github.com/sdsc-ordes/mava-exchange/actions/workflows/normal.yaml)
[![License](https://img.shields.io/badge/License-Apache2.0-blue.svg)](http://www.apache.org/licenses/LICENSE-2.0.html)

**Authors:**

- [Stefan Milosavljevic](mailto:stefan.milosavljevic@sdsc.ethz.ch)
- [Sabine Maennel](mailto:sabine.maennel@sdsc.ethz.ch)

# mava-exchange

A Python library and standard package format for exchanging video annotation
data between research tools.

## Documentation

📚 **[Full Documentation](https://sdsc-ordes.github.io/mava-exchange/)** -
Complete user guide and API reference

Quick links:

- **[Getting Started](https://sdsc-ordes.github.io/mava-exchange/tutorial/getting-started.html)** -
  Installation and tutorial
- **[Format Specification](https://sdsc-ordes.github.io/mava-exchange/specification.html)** -
  Technical specification
- **[Interactive Viewer](https://sdsc-ordes.github.io/mava-exchange/viewer-app.html)** -
  Try it in your browser
- **[API Reference](https://sdsc-ordes.github.io/mava-exchange/reference-guide/index.html)** -
  Python class documentation

## Project Context

This work is part of the MAVA Project, which aims to improve interoperability
and data exchange among three research tools — VideoScope, TIB-AV-A, and VIAN.
By standardising data formats and developing tools to import, export, and
validate annotation packages, the project enhances data sharing and analysis
capabilities across linguistic, media studies, and audiovisual research.

This infrastructure will enable shared research workflows and ensure adherence
to FAIR principles, improving the accessibility and reusability of research
data.

## The Challenge

Video analysis via AI is computationally expensive and produces large datasets —
continuous observations such as emotion scores, scene analysis, and audio
features accumulate quickly across a corpus. It is therefore desirable to share
these results among video processing tools without recomputing them.

What is needed is a common data exchange format and tools to write, read, and
validate packages in that format. Packages should be:

- Interoperable and self-describing
- Efficient to write and compact in file size

## mava-exchange

`mava-exchange` addresses this with a standard package format for video
annotation corpora called `.mediapkg`. The library has two goals:

**Format definition** — `mava-exchange` defines the `.mediapkg` standard: a ZIP
archive containing annotation data as Parquet files alongside a manifest that
maps columns to the MAVA ontology via JSON-LD.

**Tooling** — `mava-exchange` provides a Python library and CLI tools to write,
read, inspect, and validate `.mediapkg` packages.

## Design Choices

- **ZIP + Parquet** — the `.mediapkg` is a ZIP archive containing one Parquet
  file per annotation track. Parquet offers compact storage, efficient reads,
  and columnar access. ZIP provides a universal container that any tool can open
  for inspection.

- **JSON-LD manifest** — each package contains a `manifest.json` with a JSON-LD
  `@context` that maps Parquet column names to terms in the MAVA ontology. This
  is the semantic layer — it describes what each column means without being part
  of the data itself.

- **MAVA ontology** — the ontology defines a shared vocabulary for annotation
  tracks, time coordinates, and observation dimensions. SHACL shapes are
  included for formal validation.

- **Python** — the library is implemented in Python, as all participating tools
  use Python. Support for other languages may be added in future releases.

## Inspiration

This format is inspired by GeoJSON and GeoParquet. GeoParquet embeds spatial
metadata inside Parquet files to describe geometry columns. `mava-exchange`
applies the same principle to temporal data: where GeoParquet uses spatial
coordinates, `mava-exchange` uses time coordinates on a video timeline. Where
GeoParquet metadata is purely operational, `mava-exchange` adds a semantic layer
via JSON-LD to link columns to a shared ontology.

## Using the library

Install from PyPI:

```bash
pip install mava-exchange
```

Write, read, and validate `.mediapkg` packages:

```python
from mava_exchange import (
    MediaPackageWriter, MediaPackageReader,
    ObservationSeries, AnnotationSeries, DimensionSpec,
)

# Define what your tracks mean
emotions = ObservationSeries(
    name="emotions",
    description="Face emotion scores from DeepFace",
    sampling_interval=0.5,
    dimensions=[
        DimensionSpec("angry",   "Anger probability",  "[0,1]"),
        DimensionSpec("neutral", "Neutral expression", "[0,1]"),
    ]
)

# Write a package
with MediaPackageWriter("corpus.mediapkg") as writer:
    writer.add_video("video_001", "https://example.org/talk.mp4")
    writer.add_track("video_001", emotions, emotions_df)

# Read it back
with MediaPackageReader("corpus.mediapkg") as reader:
    df = reader.read_track("video_001", "emotions")
```

Two CLI tools are also available after installation:

```bash
mediapkg-inspect  corpus.mediapkg
mediapkg-validate corpus.mediapkg
```

👉
**[See the full tutorial](https://sdsc-ordes.github.io/mava-exchange/tutorial/getting-started.html)**
for a complete walkthrough.

## Development

Clone the repository and install in editable mode with development dependencies:

```bash
git clone https://github.com/sdsc-ordes/mava-exchange.git
cd mava-exchange
uv sync --group dev
```

The project uses [just](https://github.com/casey/just) as a task runner:

```bash
just test      # run the test suite
just lint      # run ruff
just format    # format with ruff and treefmt
just build     # build the package
```

To run the example that converts real TSV annotation files into a `.mediapkg`
corpus:

```bash
just example           # create example corpus from TSV files
just inspect           # inspect the resulting corpus.mediapkg
just inspect-turtle    # view manifest as Turtle RDF
just validate          # validate the package
```

## Further Reading

- [Format Specification](https://sdsc-ordes.github.io/mava-exchange/specification.html) -
  Complete technical specification
- [MAVA Ontology](https://sdsc-ordes.github.io/mava-exchange/mava-ontology.html) -
  Semantic vocabulary (interactive)
- [User Guide](https://sdsc-ordes.github.io/mava-exchange/reference-guide/writer.html) -
  Writing and reading packages
- [CLI Tools](https://sdsc-ordes.github.io/mava-exchange/reference-guide/cli.html) -
  Command-line reference
- [Examples](examples/) - Complete example code

For development:

- [Contribution Guidelines](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## License

[Apache-2.0](LICENSE.md)

## Acknowledgements

This work was funded by the Swiss Data Science Center (SDSC) through its
National Call for Projects as an Infrastructure project.

We gratefully acknowledge the contributions of the SDSC experts and our
partners.

**SDSC Experts**:

- Dr. Stefan Milosavljevic, ORCID ID
  [0000-0002-9135-1353](https://orcid.org/0000-0002-9135-1353)
- Sabine Maennel, ORCID ID
  [0009-0001-3022-8239](https://orcid.org/0009-0001-3022-8239)
- Robin Franken, ORCID ID
  [0009-0008-0143-9118](https://orcid.org/0009-0008-0143-9118)
- Dr. Oksana Riba Grognuz, ORCID ID
  [0000-0002-2961-2655](https://orcid.org/0000-0002-2961-2655)

**Partner Institutions**

- Dr. Teodora Vuković, ORCID ID
  [0000-0002-5780-5665](https://orcid.org/0000-0002-5780-5665)
- Dr. Jeremy Zehr, ORCID ID
  [0000-0002-6046-8647](https://orcid.org/0000-0002-6046-8647)
- Prof. Dr. Josephine Diecke, ORCID ID
  [0000-0002-9342-0631](https://orcid.org/0000-0002-9342-0631)
- Dr. Simon Spiegel, ORCID ID
  [0000-0003-2141-5566](https://orcid.org/0000-0003-2141-5566)
- Prof. Dr. Ralph Ewerth, ORCID ID
  [0000-0003-0918-6297](https://orcid.org/0000-0003-0918-6297)
- Dr. Eric Müller-Budack, ORCID ID
  [0000-0002-6802-1241](https://orcid.org/0000-0002-6802-1241)
- Dr. Cristina Grisot, ORCID ID
  [0000-0003-0684-4442](https://orcid.org/0000-0003-0684-4442)

## How to Cite

If you use this software, please cite it as follows:

👉 See the [CITATION.cff](./CITATION.cff) file for the full list of software
authors and citation formats.

When referring to the project more broadly (including partner contributions),
please acknowledge the funding statement and collaborators listed in the
[Acknowledgements](#acknowledgements) section:

> "This work was funded by the Swiss Data Science Center (SDSC) through its
> National Call for Projects as an Infrastructure project."

## Copyright

Copyright © 2025-2026 Swiss Data Science Center
(SDSC),[www.datascience.ch](http://www.datascience.ch/), ROR:
[ror.org/02hdt9m26](https://ror.org/02hdt9m26). All rights reserved. The SDSC is
a Swiss National Research Infrastructure, jointly established and legally
represented by the École Polytechnique Fédérale de Lausanne (EPFL) and the
Eidgenössische Technische Hochschule Zürich (ETH Zürich) as a société simple.
This copyright encompasses all materials, software, documentation, and other
content created and developed by the SDSC.
