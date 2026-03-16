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

function visualizeTrack(videoId, trackName, trackPath, trackDef) {
  console.log("Visualizing track:", trackName)

  document.getElementById("vizTitle").textContent = trackName
  document.getElementById("vizSubtitle").textContent =
    trackDef.type.split(":")[1] + " • " + videoId
  document.getElementById("visualization").classList.add("visible")
  document
    .getElementById("visualization")
    .scrollIntoView({ behavior: "smooth" })

  const chart = document.getElementById("chart")
  chart.innerHTML =
    '<div style="padding: 40px; text-align: center; background: #f5f5f5; border-radius: 8px;">' +
    "<h3>Track: " +
    trackName +
    "</h3>" +
    '<p style="margin-top: 10px; color: #666;">Type: ' +
    trackDef.type +
    "</p>" +
    '<p style="margin-top: 5px; color: #666;">Description: ' +
    trackDef.description +
    "</p>" +
    '<p style="margin-top: 20px; font-size: 14px;"><strong>Note:</strong> Parquet visualization coming soon.<br>' +
    "For now, this confirms the package loads correctly.</p></div>"
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
