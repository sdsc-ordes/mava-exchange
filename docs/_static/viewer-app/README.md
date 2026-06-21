# MediaPkg Viewer

A simple web-based viewer for `.mediapkg` video annotation packages.

## Features

- 📦 Drag & drop `.mediapkg` files
- 📊 Visualize ObservationSeries as line charts
- 📝 Display AnnotationSeries as timeline segments
- 🏷️ Show AnnotationListSeries with multi-label tags
- 🟦 Render RegionSeries as bounding boxes per timestamp (colored by cluster)
- 🎬 Optionally load the source video locally to overlay boxes and sync a
  playhead across all open panels (the package never embeds the video)
- 🪟 Open multiple tracks at once as stacked, individually closable panels
- 🌐 Works entirely client-side (no data leaves the browser)

## Usage

### Local

Serve this folder over HTTP and open it — the module import is blocked from
`file://`, and the libraries load from a CDN (so you need internet):

```bash
just viewer          # → http://localhost:8000/
# or: python3 -m http.server -d docs/_static/viewer-app 8000
```

Then drop a `.mediapkg` (e.g. `examples/output/corpus.mediapkg`) into the page.

### Online

Visit: https://sdsc-ordes.github.io/mava-exchange/viewer/

## How it works

1. Drop a `.mediapkg` file into the viewer
2. The viewer unzips it using JSZip
3. Reads the `manifest.json` to understand the structure
4. Parses Parquet files using hyparquet
5. Renders visualizations using Chart.js (and a canvas for RegionSeries)

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
