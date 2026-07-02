# Viewer for mediapkg files

## How to Use

- Download mediapkg example
  [`corpus.mediapkg`](https://github.com/sdsc-ordes/mava-exchange/blob/main/examples/output/corpus.mediapkg)
  or use your own mediapkg
- You can use the emmbedded viewer or open the viewer in full page mode
  <a href="viewer-app.html" target="_blank">here</a>.
- Drag and drop a `.mediapkg` file into the viewer
- Browse videos and tracks
- Click any track to visualize it

<iframe src="viewer-app.html"
        style="width: 100%; height: 80vh; border: none;">
</iframe>

## Features

- 📦 Drag & drop `.mediapkg` files
- 📊 View ObservationSeries as line charts
- 📝 View AnnotationSeries as timelines
- 🏷️ View AnnotationListSeries with multi-label tags
- 🎯 View RegionSeries bounding boxes over the video, with the track hierarchy
- 🔍 Inspect package metadata and structure

## Technologies

- [JSZip](https://stuk.github.io/jszip/) - Unzip .mediapkg files
- [hyparquet](https://github.com/hyparam/hyparquet) - Read Parquet in browser
- [Chart.js](https://www.chartjs.org/) - Render time-series charts
- Vanilla JavaScript - No framework dependencies
