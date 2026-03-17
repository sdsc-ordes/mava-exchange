// MediaPkg Viewer - Main logic
let currentPackage = null

console.log("Viewer script loaded")

// Wait for DOM to be ready
document.addEventListener("DOMContentLoaded", function () {
  console.log("DOM ready, setting up event listeners")

  const dropZone = document.getElementById("dropZone")
  const fileInput = document.getElementById("fileInput")

  if (!dropZone || !fileInput) {
    console.error("Elements not found!")
    return
  }

  console.log("Elements found:", { dropZone, fileInput })

  // Click to browse
  dropZone.addEventListener("click", function () {
    console.log("Drop zone clicked")
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
    console.log("File dropped")
    const file = e.dataTransfer.files[0]
    if (file) {
      console.log("Processing file:", file.name)
      loadPackage(file)
    }
  })

  // File input change
  fileInput.addEventListener("change", function (e) {
    console.log("File selected via input")
    const file = e.target.files[0]
    if (file) {
      console.log("Processing file:", file.name)
      loadPackage(file)
    }
  })

  console.log("All event listeners attached")
})

// Load and parse .mediapkg file
async function loadPackage(file) {
  try {
    console.log("Loading package:", file.name)

    // Read ZIP file
    const arrayBuffer = await file.arrayBuffer()
    console.log("File loaded, size:", arrayBuffer.byteLength)

    const zip = await JSZip.loadAsync(arrayBuffer)
    console.log("ZIP loaded, files:", Object.keys(zip.files))

    // Read manifest
    const manifestFile = zip.file("manifest.json")
    if (!manifestFile) {
      throw new Error("manifest.json not found in package")
    }
    const manifestText = await manifestFile.async("text")
    const manifest = JSON.parse(manifestText)
    console.log("Manifest loaded:", manifest)

    // Store package data
    currentPackage = { manifest, zip, name: file.name }

    // Display package info
    displayPackageInfo(manifest)
    displayVideoList(manifest, zip)
  } catch (error) {
    showError("Failed to load package: " + error.message)
    console.error("Load error:", error)
  }
}

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

async function visualizeTrack(videoId, trackName, trackPath, trackDef) {
  console.log("Visualizing track:", trackName)

  const chart = document.getElementById("chart")
  chart.innerHTML =
    '<p style="text-align: center; padding: 20px;">Loading data...</p>'

  document.getElementById("vizTitle").textContent = trackName
  document.getElementById("vizSubtitle").textContent =
    trackDef.type.split(":")[1] + " • " + videoId
  document.getElementById("visualization").classList.add("visible")
  document
    .getElementById("visualization")
    .scrollIntoView({ behavior: "smooth" })

  try {
    // 1. Get the binary file from the ZIP
    const fileData = currentPackage.zip.file(trackPath)
    if (!fileData) throw new Error(`File ${trackPath} not found in package`)

    const arrayBuffer = await fileData.async("arrayBuffer")
    const uint8Array = new Uint8Array(arrayBuffer)

    // 2. Import hyparquet dynamically
    // This bypasses the "parquet is not defined" error entirely
    const { parquetRead } = await import(
      "https://cdn.jsdelivr.net/npm/hyparquet@1.25.1/+esm"
    )

    // 3. Read the data
    // We use rowFormat: 'object' to get easy-to-use JSON objects
    await parquetRead({
      file: uint8Array,
      rowFormat: "object",
      onComplete: (data) => {
        renderDataTable(data)
      },
    })
  } catch (error) {
    chart.innerHTML = `<div class="error">Error loading Parquet: ${error.message}</div>`
    console.error("Parquet error:", error)
  }
}

// Keep your renderDataTable function as it was
function renderDataTable(rows) {
  const chart = document.getElementById("chart")
  if (!rows || rows.length === 0) {
    chart.innerHTML = "<p>No data found in this track.</p>"
    return
  }

  const columns = Object.keys(rows[0])
  let html =
    '<div style="overflow-x: auto; border: 1px solid #ddd; border-radius: 4px;">'
  html +=
    '<table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">'

  // Header
  html +=
    '<thead style="background: #f8f9fa; border-bottom: 2px solid #ddd;"><tr>'
  columns.forEach(
    (col) =>
      (html += `<th style="padding: 10px; font-weight: 600;">${col}</th>`),
  )
  html += "</tr></thead><tbody>"

  // Body
  rows.forEach((row, i) => {
    html += `<tr style="background: ${i % 2 === 0 ? "#fff" : "#fafafa"}; border-bottom: 1px solid #eee;">`
    columns.forEach((col) => {
      let val = row[col]
      if (typeof val === "object" && val !== null) val = JSON.stringify(val)
      html += `<td style="padding: 8px 10px;">${val ?? ""}</td>`
    })
    html += "</tr>"
  })

  html += "</tbody></table></div>"
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

window.closeVisualization = closeVisualization

console.log("Functions defined, waiting for DOM...")
