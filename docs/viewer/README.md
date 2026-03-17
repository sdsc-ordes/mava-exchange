# MediaPkg Viewer

A simple web-based viewer for `.mediapkg` video annotation packages.

## Features

- 📦 Drag & drop `.mediapkg` files
- 📊 Visualize ObservationSeries as line charts
- 📝 Display AnnotationSeries as timeline segments
- 🏷️ Show AnnotationListSeries with multi-label tags
- 🌐 Works entirely in the browser (no server needed)

## Usage

### Local

Just open `index.html` in a web browser. No build step or installation required.

### Online

Visit: https://sdsc-ordes.github.io/mava-exchange/viewer/

## How it works

1. Drop a `.mediapkg` file into the viewer
2. The viewer unzips it using JSZip
3. Reads the `manifest.json` to understand the structure
4. Parses Parquet files using parquet-wasm
5. Renders visualizations using Chart.js

All processing happens client-side. No data is uploaded to any server.

## Technologies

- [JSZip](https://stuk.github.io/jszip/) - Unzip .mediapkg files
- [hyparquet](https://github.com/hyparam/hyparquet) - Read Parquet in browser
- [Chart.js](https://www.chartjs.org/) - Render time-series charts
- Vanilla JavaScript - No framework dependencies

## Example

Try it with the [example corpus](../examples/output/corpus.mediapkg)

## Limitations

- No video playback (just shows annotations)
- No editing capabilities (read-only)
- Large packages (>100MB) may be slow to load
- Designed for exploration, not production use
