// MediaPkg Viewer - Using hyparquet
import { parquetRead } from "https://cdn.jsdelivr.net/npm/hyparquet@1.7.0/+esm"

let currentPackage = null

console.log("Viewer script loaded with hyparquet")

// Wait for DOM to be ready
document.addEventListener("DOMContentLoaded", function () {
  console.log("DOM ready, setting up event listeners")

  const dropZone = document.getElementById("dropZone")
  const fileInput = document.getElementById("fileInput")

  if (!dropZone || !fileInput) {
    console.error("Elements not found!")
    return
  }

  // Click to browse
  dropZone.addEventListener("click", function () {
    fileInput.click()
  })

  // Drag & drop
  dropZone.addEventListener("dragover", function (e) {
    e.preventDefault()
    e.stopPropagation()
    dropZone.classList.add("dragover")
  })

  dropZone.addEventListener("dragleave", function (e) {
    e.preventDefault()
    e.stopPropagation()
    dropZone.classList.remove("dragover")
  })

  dropZone.addEventListener("drop", function (e) {
    e.preventDefault()
    e.stopPropagation()
    dropZone.classList.remove("dragover")
    const file = e.dataTransfer.files[0]
    if (file) {
      loadPackage(file)
    }
  })

  // File input change
  fileInput.addEventListener("change", function (e) {
    const file = e.target.files[0]
    if (file) {
      loadPackage(file)
    }
  })

  console.log("All event listeners attached")
})

/**
 * Load and parse a .mediapkg file
 * @param {File} file - The .mediapkg file from file input or drag-drop
 */
async function loadPackage(file) {
  try {
    console.log("Loading package:", file.name)

    const arrayBuffer = await file.arrayBuffer()
    const zip = await JSZip.loadAsync(arrayBuffer)

    const manifestFile = zip.file("manifest.json")
    if (!manifestFile) {
      throw new Error("manifest.json not found in package")
    }
    const manifestText = await manifestFile.async("text")
    const manifest = JSON.parse(manifestText)

    currentPackage = { manifest, zip, name: file.name }

    displayPackageInfo(manifest)
    displayVideoList(manifest, zip)
  } catch (error) {
    showError("Failed to load package: " + error.message)
    console.error("Load error:", error)
  }
}

/**
 * Display package information
 * @param {object} manifest - Manifest object from the package as jsonld
 */
function displayPackageInfo(manifest) {
  document.getElementById("infoVersion").textContent = manifest.version
  document.getElementById("infoCreated").textContent = manifest.created || "—"
  document.getElementById("infoDescription").textContent =
    manifest.description || "—"
  document.getElementById("infoVideos").textContent = manifest.videos.length
  document.getElementById("infoTracks").textContent = Object.keys(
    manifest.tracks,
  ).length

  document.getElementById("packageInfo").classList.add("visible")
}

/**
 * Display the list of videos and tracks from the package
 * @param {object} manifest - Manifest object from the package as jsonld
 */
function displayVideoList(manifest) {
  const videoList = document.getElementById("videoList")
  videoList.innerHTML = "<h2>Videos & Tracks</h2>"

  for (const video of manifest.videos) {
    const videoCard = document.createElement("div")
    videoCard.className = "video-card"

    const header = document.createElement("div")
    header.className = "video-header"
    header.innerHTML =
      '<span class="video-icon">📹</span><span class="video-title">' +
      video.id +
      "</span>"
    videoCard.appendChild(header)

    const trackList = document.createElement("div")
    trackList.className = "track-list"

    for (const [trackName, trackPath] of Object.entries(video.files)) {
      const trackDef = manifest.tracks[trackName]
      const trackItem = document.createElement("div")
      trackItem.className = "track-item"

      const typeClass =
        trackDef.type === "mava:ObservationSeries"
          ? "observation"
          : trackDef.type === "mava:AnnotationListSeries"
            ? "list"
            : "annotation"

      const icon =
        trackDef.type === "mava:ObservationSeries"
          ? "📊"
          : trackDef.type === "mava:AnnotationListSeries"
            ? "🏷️"
            : "📝"

      trackItem.innerHTML =
        "<span>" +
        icon +
        '</span><span style="flex: 1;">' +
        trackName +
        '</span><span class="track-type ' +
        typeClass +
        '">' +
        trackDef.type.split(":")[1] +
        "</span>"

      trackItem.onclick = function () {
        visualizeTrack(video.id, trackName, trackPath, trackDef)
      }
      trackList.appendChild(trackItem)
    }

    videoCard.appendChild(trackList)
    videoList.appendChild(videoCard)
  }
}

/**
 * Visualize a track from the package
 * @param {string} videoId - Video identifier
 * @param {string} trackName - Name of the track
 * @param {string} trackPath - Path to Parquet file in ZIP
 * @param {object} trackDef - Track definition from manifest
 */
async function visualizeTrack(videoId, trackName, trackPath, trackDef) {
  try {
    console.log("Visualizing track:", trackName)

    // Read Parquet file from ZIP
    const parquetFile = currentPackage.zip.file(trackPath)
    if (!parquetFile) {
      throw new Error("Track file not found: " + trackPath)
    }

    const parquetData = await parquetFile.async("arraybuffer")
    console.log("Parquet data loaded, size:", parquetData.byteLength)

    // Parse with hyparquet - collect schema and rows
    let schema = null
    const rows = []

    await parquetRead({
      file: parquetData,
      onComplete: (data, schemaDef) => {
        console.log("Parquet parsed, rows:", data.length)
        if (!schema && schemaDef) {
          schema = schemaDef
          console.log("Schema:", schema)
        }
        rows.push(...data)
      },
    })

    console.log("Total rows:", rows.length)
    if (rows.length > 0) {
      console.log("First row (raw):", rows[0])
    }

    // Convert arrays to objects using schema
    let dataObjects = rows
    if (rows.length > 0 && Array.isArray(rows[0])) {
      // hyparquet returns arrays - convert to objects
      const columnNames =
        trackDef.columns || Object.keys(trackDef.dimensions || {})
      console.log("Converting arrays to objects using columns:", columnNames)

      dataObjects = rows.map((row) => {
        const obj = {}
        columnNames.forEach((colName, i) => {
          obj[colName] = row[i]
        })
        return obj
      })

      console.log("First row (converted):", dataObjects[0])
    }

    // Show visualization
    document.getElementById("vizTitle").textContent = trackName
    document.getElementById("vizSubtitle").textContent =
      trackDef.type.split(":")[1] +
      " • " +
      videoId +
      " • " +
      dataObjects.length +
      " rows"
    document.getElementById("visualization").classList.add("visible")
    document
      .getElementById("visualization")
      .scrollIntoView({ behavior: "smooth" })

    // Render based on track type
    if (trackDef.type === "mava:ObservationSeries") {
      renderObservationSeries(dataObjects, trackDef)
    } else if (trackDef.type === "mava:AnnotationListSeries") {
      renderAnnotationListSeries(dataObjects, trackDef)
    } else {
      renderAnnotationSeries(dataObjects, trackDef)
    }
  } catch (error) {
    showError("Failed to load track: " + error.message)
    console.error("Visualization error:", error)
  }
}

/**
 * Visualize a track from the package
 * @param {Array<object>} data - Data rows as array of objects
 * @param {object} trackDef - Track definition from manifest
 */
function renderObservationSeries(data, trackDef) {
  const chart = document.getElementById("chart")

  let html = '<div style="padding: 20px;">'
  html +=
    '<p style="margin-bottom: 15px; color: #666;">' +
    trackDef.description +
    "</p>"

  // Add canvas for chart
  html += '<canvas id="chartCanvas"></canvas>'
  html += "</div>"

  chart.innerHTML = html

  // Generate line chart
  const ctx = document.getElementById("chartCanvas")
  const dimensions = Object.keys(trackDef.dimensions || {})

  // Create datasets - one line per dimension
  const datasets = dimensions.map((dimName, i) => {
    const hue = (i * 137.5) % 360 // Golden angle for color distribution
    return {
      label: dimName,
      data: data.map((row) => ({ x: row.start_seconds, y: row[dimName] })),
      borderColor: `hsl(${hue}, 70%, 50%)`,
      backgroundColor: `hsla(${hue}, 70%, 50%, 0.1)`,
      borderWidth: 2,
      pointRadius: 0, // Hide points for cleaner look
      tension: 0.1,
    }
  })

  new Chart(ctx, {
    type: "line",
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          position: "top",
        },
        tooltip: {
          mode: "index",
          intersect: false,
        },
      },
      scales: {
        x: {
          type: "linear",
          title: {
            display: true,
            text: "Time (seconds)",
          },
        },
        y: {
          title: {
            display: true,
            text: "Value",
          },
        },
      },
      interaction: {
        mode: "nearest",
        axis: "x",
        intersect: false,
      },
    },
  })
}

function renderAnnotationSeries(data, trackDef) {
  const chart = document.getElementById("chart")

  let html = '<div style="padding: 20px;">'
  html +=
    '<p style="margin-bottom: 15px; color: #666;">' +
    trackDef.description +
    "</p>"

  data.forEach((row) => {
    const duration = (row.end_seconds - row.start_seconds).toFixed(1)
    html +=
      '<div style="background: #fff3e0; border-left: 4px solid #f57c00; padding: 12px; margin: 8px 0; border-radius: 4px;">'
    html += '<div style="font-size: 12px; color: #666; margin-bottom: 4px;">'
    html +=
      row.start_seconds.toFixed(1) +
      "s → " +
      row.end_seconds.toFixed(1) +
      "s (" +
      duration +
      "s)"
    html += "</div>"
    html +=
      '<div style="font-size: 14px; color: #333;">' +
      escapeHtml(row.annotations) +
      "</div>"
    html += "</div>"
  })

  html += "</div>"
  chart.innerHTML = html
}

/**
 * Visualize a track from the package
 * @param {Array<object>} data - Data rows as array of objects
 * @param {object} trackDef - Track definition from manifest
 */
function renderAnnotationListSeries(data, trackDef) {
  const chart = document.getElementById("chart")

  let html = '<div style="padding: 20px;">'
  html +=
    '<p style="margin-bottom: 15px; color: #666;">' +
    trackDef.description +
    "</p>"

  data.forEach((row) => {
    const duration = (row.end_seconds - row.start_seconds).toFixed(1)
    html +=
      '<div style="background: #f3e5f5; border-left: 4px solid #7b1fa2; padding: 12px; margin: 8px 0; border-radius: 4px;">'
    html += '<div style="font-size: 12px; color: #666; margin-bottom: 8px;">'
    html +=
      row.start_seconds.toFixed(1) +
      "s → " +
      row.end_seconds.toFixed(1) +
      "s (" +
      duration +
      "s)"
    html += "</div>"
    html += "<div>"

    // Handle list values
    const tags = Array.isArray(row.annotations)
      ? row.annotations
      : [row.annotations]
    tags.forEach((tag) => {
      html +=
        '<span style="display: inline-block; background: #7b1fa2; color: white; padding: 4px 8px; border-radius: 3px; font-size: 12px; margin: 2px;">'
      html += escapeHtml(tag)
      html += "</span>"
    })

    html += "</div></div>"
  })

  html += "</div>"
  chart.innerHTML = html
}

function closeVisualization() {
  document.getElementById("visualization").classList.remove("visible")
}

function showError(message) {
  console.error("Error:", message)
  const errorDiv = document.createElement("div")
  errorDiv.className = "error"
  errorDiv.textContent = message
  document
    .querySelector(".container")
    .insertBefore(errorDiv, document.getElementById("dropZone").nextSibling)
  setTimeout(function () {
    errorDiv.remove()
  }, 5000)
}

function escapeHtml(text) {
  const div = document.createElement("div")
  div.textContent = text
  return div.innerHTML
}

window.closeVisualization = closeVisualization
