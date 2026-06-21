// MediaPkg Viewer - Using hyparquet
import { parquetRead } from "https://cdn.jsdelivr.net/npm/hyparquet@1.7.0/+esm"

let currentPackage = null

console.log("Viewer script loaded with hyparquet")

// ── Video sync ───────────────────────────────────────────────────────────────
// One time-bus per video id. A panel that loads a local video "drives" the bus
// (publishes currentTime); every open panel for that video subscribes and reacts
// — box overlay (RegionSeries), playhead line (ObservationSeries), active-segment
// highlight (AnnotationSeries). The package never embeds the video; it is loaded
// locally and lines up by absolute timestamp.
const videoBuses = {}

function getBus(videoId) {
  if (!videoBuses[videoId]) {
    videoBuses[videoId] = {
      subs: new Set(),
      buttons: new Set(),
      driverEl: null,
    }
  }
  return videoBuses[videoId]
}

function subscribeTime(videoId, fn) {
  const bus = getBus(videoId)
  bus.subs.add(fn)
  return () => bus.subs.delete(fn)
}

// Wire a <video> as the bus driver: publish currentTime each frame.
function driveVideo(videoEl, videoId, onTime) {
  const bus = getBus(videoId)
  bus.driverEl = videoEl
  bus.buttons.forEach((b) => (b.style.display = "none"))
  const tick = () => {
    const t = videoEl.currentTime
    if (onTime) onTime(t)
    bus.subs.forEach((fn) => fn(t))
    if (videoEl.requestVideoFrameCallback)
      videoEl.requestVideoFrameCallback(tick)
  }
  if (videoEl.requestVideoFrameCallback) {
    videoEl.requestVideoFrameCallback(tick)
  } else {
    videoEl.addEventListener("timeupdate", tick)
    videoEl.addEventListener("seeked", tick)
  }
}

// A "Load video" button that embeds a <video> into `host` and drives the bus.
// Auto-hides once any panel for this video has loaded one. Returns the <video>.
function makeVideoLoader(videoId, host, onTime) {
  const bus = getBus(videoId)
  const fileInput = document.createElement("input")
  fileInput.type = "file"
  fileInput.accept = "video/*"
  fileInput.style.display = "none"
  const button = document.createElement("button")
  button.className = "close-btn"
  button.style.background = "#1976d2"
  button.textContent = "🎬 Load video"
  const videoEl = document.createElement("video")
  videoEl.playsInline = true
  videoEl.controls = true
  videoEl.style.cssText =
    "max-width: 100%; display: none; margin-top: 10px; border: 1px solid #ddd;"

  bus.buttons.add(button)
  if (bus.driverEl) button.style.display = "none"

  button.addEventListener("click", () => fileInput.click())
  fileInput.addEventListener("change", () => {
    const file = fileInput.files && fileInput.files[0]
    if (!file) return
    videoEl.src = URL.createObjectURL(file)
    videoEl.style.display = "block"
    driveVideo(videoEl, videoId, onTime)
  })

  host.appendChild(button)
  host.appendChild(fileInput)
  host.appendChild(videoEl)
  return videoEl
}

// Chart.js plugin: draw a vertical playhead line at state.t (in seconds).
function playheadPlugin(state) {
  return {
    id: "playhead",
    afterDatasetsDraw(c) {
      if (state.t == null) return
      const x = c.scales.x.getPixelForValue(state.t)
      if (x == null || Number.isNaN(x)) return
      const ctx = c.ctx
      ctx.save()
      ctx.strokeStyle = "#e53935"
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.moveTo(x, c.chartArea.top)
      ctx.lineTo(x, c.chartArea.bottom)
      ctx.stroke()
      ctx.restore()
    },
  }
}

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

    // Build a containment tree (parent -> children), scoped to the tracks that
    // are actually present in this video. Roots are tracks with no parent (or a
    // parent that lives in another video).
    const names = Object.keys(video.files)
    const inVideo = new Set(names)
    const childrenOf = {}
    const roots = []
    for (const name of names) {
      const parent = manifest.tracks[name] ? manifest.tracks[name].parent : null
      if (parent && inVideo.has(parent)) {
        ;(childrenOf[parent] = childrenOf[parent] || []).push(name)
      } else {
        roots.push(name)
      }
    }

    const renderTrack = (trackName, depth) => {
      const trackDef = manifest.tracks[trackName]
      const trackPath = video.files[trackName]
      trackList.appendChild(
        makeTrackItem(video.id, trackName, trackPath, trackDef, depth),
      )
      for (const child of childrenOf[trackName] || []) {
        renderTrack(child, depth + 1)
      }
    }
    for (const root of roots) renderTrack(root, 0)

    videoCard.appendChild(trackList)
    videoList.appendChild(videoCard)
  }
}

const TYPE_META = {
  "mava:ObservationSeries": { cls: "observation", icon: "📊" },
  "mava:AnnotationSeries": { cls: "annotation", icon: "📝" },
  "mava:AnnotationListSeries": { cls: "list", icon: "🏷️" },
  "mava:RegionSeries": { cls: "region", icon: "🟦" },
}

/**
 * Build one clickable track row, indented by its depth in the hierarchy.
 * @param {string} videoId - Video identifier
 * @param {string} trackName - Track name
 * @param {string} trackPath - Path to the Parquet file in the ZIP
 * @param {object} trackDef - Track definition from the manifest
 * @param {number} depth - Nesting depth (0 = root)
 * @returns {HTMLElement} the track row
 */
function makeTrackItem(videoId, trackName, trackPath, trackDef, depth) {
  const item = document.createElement("div")
  item.className = "track-item"
  if (depth > 0) item.style.marginLeft = depth * 18 + "px"

  const meta = TYPE_META[trackDef.type] || TYPE_META["mava:AnnotationSeries"]
  const branch =
    depth > 0 ? '<span style="color: #ccc; margin-right: 4px;">└</span>' : ""

  // Derivation edge: small chip showing the method, sources in the tooltip.
  let derived = ""
  if (trackDef.derived_from && trackDef.derived_from.length) {
    derived =
      '<span title="derived from: ' +
      trackDef.derived_from.join(", ") +
      '" style="font-size: 10px; color: #00897b; margin-left: 6px;">⟵ ' +
      escapeHtml(trackDef.method || "derived") +
      "</span>"
  }

  item.innerHTML =
    branch +
    "<span>" +
    meta.icon +
    '</span><span style="flex: 1;">' +
    escapeHtml(trackName) +
    derived +
    '</span><span class="track-type ' +
    meta.cls +
    '">' +
    trackDef.type.split(":")[1] +
    "</span>"

  item.onclick = function () {
    visualizeTrack(videoId, trackName, trackPath, trackDef)
  }
  return item
}

/**
 * Build a closable visualization panel (header + own chart area).
 * @param {string} key - Unique key (videoId/trackName) for de-duplication
 * @param {string} title - Track name
 * @param {string} subtitle - Type / video / rows / hierarchy summary
 * @returns {{panel: HTMLElement, chart: HTMLElement}} the panel and its chart area
 */
function makePanel(key, title, subtitle) {
  const panel = document.createElement("div")
  panel.className = "viz-panel"
  panel.dataset.key = key

  const header = document.createElement("div")
  header.className = "viz-header"

  const titles = document.createElement("div")
  const titleEl = document.createElement("div")
  titleEl.className = "viz-title"
  titleEl.textContent = title
  const subEl = document.createElement("div")
  subEl.className = "viz-subtitle"
  subEl.textContent = subtitle
  titles.appendChild(titleEl)
  titles.appendChild(subEl)

  const closeBtn = document.createElement("button")
  closeBtn.className = "close-btn"
  closeBtn.textContent = "Close"
  closeBtn.addEventListener("click", () => {
    if (typeof panel._cleanup === "function") panel._cleanup()
    // If this panel was driving the video bus, release it so other panels can.
    const vid = panel.dataset.key.split("/")[0]
    const bus = videoBuses[vid]
    if (bus && bus.driverEl && panel.contains(bus.driverEl)) {
      bus.driverEl = null
      bus.buttons.forEach((b) => (b.style.display = ""))
    }
    const container = panel.parentElement
    panel.remove()
    if (container && container.children.length === 0) {
      container.classList.remove("visible")
    }
  })

  header.appendChild(titles)
  header.appendChild(closeBtn)

  const chart = document.createElement("div")
  chart.className = "chart"

  panel.appendChild(header)
  panel.appendChild(chart)
  return { panel, chart }
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

    // Open a panel for this track. Panels stack below each other; opening the
    // same track again just scrolls to its existing panel instead of duplicating.
    const key = videoId + "/" + trackName
    const viz = document.getElementById("visualization")
    const existing = Array.from(viz.children).find(
      (el) => el.dataset.key === key,
    )
    if (existing) {
      existing.scrollIntoView({ behavior: "smooth" })
      return
    }

    let subtitle =
      trackDef.type.split(":")[1] +
      " • " +
      videoId +
      " • " +
      dataObjects.length +
      " rows"
    if (trackDef.parent) subtitle += " • ↳ under " + trackDef.parent
    if (trackDef.derived_from && trackDef.derived_from.length) {
      subtitle +=
        " • " +
        (trackDef.method || "derived") +
        "(" +
        trackDef.derived_from.join(", ") +
        ")"
    }

    const { panel, chart } = makePanel(key, trackName, subtitle)
    viz.appendChild(panel)
    viz.classList.add("visible")
    panel.scrollIntoView({ behavior: "smooth" })

    // Render based on track type into this panel's own chart area.
    if (trackDef.type === "mava:ObservationSeries") {
      renderObservationSeries(chart, dataObjects, trackDef, videoId)
    } else if (trackDef.type === "mava:AnnotationListSeries") {
      renderAnnotationListSeries(chart, dataObjects, trackDef, videoId)
    } else if (trackDef.type === "mava:RegionSeries") {
      renderRegionSeries(chart, dataObjects, trackDef, videoId)
    } else {
      renderAnnotationSeries(chart, dataObjects, trackDef, videoId)
    }
  } catch (error) {
    showError("Failed to load track: " + error.message)
    console.error("Visualization error:", error)
  }
}

/**
 * Render an ObservationSeries as a line chart into the given container.
 * @param {HTMLElement} chart - Panel chart area to render into
 * @param {Array<object>} data - Data rows as array of objects
 * @param {object} trackDef - Track definition from manifest
 * @param {string} videoId - Video identifier (for playhead sync)
 */
function renderObservationSeries(chart, data, trackDef, videoId) {
  chart.innerHTML = ""
  const wrap = document.createElement("div")
  wrap.style.padding = "20px"
  const desc = document.createElement("p")
  desc.style.cssText = "margin-bottom: 15px; color: #666;"
  desc.textContent = trackDef.description || ""
  const controls = document.createElement("div")
  controls.style.marginBottom = "10px"
  const ctx = document.createElement("canvas")
  wrap.appendChild(desc)
  wrap.appendChild(controls)
  wrap.appendChild(ctx)
  chart.appendChild(wrap)

  // Generate line chart
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

  const playhead = { t: null }
  const chartObj = new Chart(ctx, {
    type: "line",
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: false,
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
          // Always span at least [0, 1] so low-valued score tracks read on a
          // consistent scale; tracks that exceed 1 (e.g. RMS) still expand.
          suggestedMin: 0,
          suggestedMax: 1,
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
    plugins: [playheadPlugin(playhead)],
  })

  // Move a red playhead line in step with the loaded video; offer to load one.
  const unsub = subscribeTime(videoId, (t) => {
    playhead.t = t
    chartObj.draw()
  })
  makeVideoLoader(videoId, controls, null)

  const panel = chart.parentElement
  if (panel) {
    panel._cleanup = () => {
      unsub()
      chartObj.destroy()
    }
  }
}

/**
 * Visualize a RegionSeries (spatial detections / bounding boxes).
 * Draws the normalized frame for one timestamp at a time, with a slider to
 * scrub through detections; boxes are colored by cluster_id.
 * @param {Array<object>} data - Detection rows (start_seconds, x, y, w, h, det_score, cluster_id, label)
 * @param {object} trackDef - Track definition from manifest
 * @param {string} videoId - Video identifier (used to look up the frame aspect)
 */
function renderRegionSeries(chart, data, trackDef, videoId) {
  // Frame aspect ratio from the manifest video entry (fallback 16:9).
  const video = (currentPackage?.manifest?.videos || []).find(
    (v) => v.id === videoId,
  )
  const frameW = video?.width || 16
  const frameH = video?.height || 9
  const pixelSpace = trackDef.coordinate_space === "pixel"

  // Unique, sorted timestamps.
  const times = [...new Set(data.map((r) => Number(r.start_seconds)))].sort(
    (a, b) => a - b,
  )

  const defaultW = 640
  const defaultH = Math.round(defaultW * (frameH / frameW))

  chart.innerHTML =
    '<div style="padding: 20px;">' +
    '<p style="margin-bottom: 12px; color: #666;">' +
    escapeHtml(trackDef.description || "") +
    "</p>" +
    '<div style="margin-bottom: 12px;">' +
    '<button class="region-load" style="font-size: 13px; padding: 6px 10px; cursor: pointer;">🎬 Load video to overlay…</button> ' +
    '<input type="file" class="region-file" accept="video/*" style="display: none;" />' +
    '<span class="region-hint" style="font-size: 12px; color: #888; margin-left: 8px;">boxes shown on a blank frame — load the source video to see them in place</span>' +
    "</div>" +
    '<div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">' +
    '<input type="range" class="region-slider" min="0" max="' +
    (times.length - 1) +
    '" value="0" style="flex: 1;" />' +
    '<span class="region-time" style="font-variant-numeric: tabular-nums; color: #333; min-width: 170px;"></span>' +
    "</div>" +
    '<div class="region-stage" style="position: relative; display: inline-block; max-width: 100%;">' +
    '<video class="region-video" playsinline controls style="display: none; max-width: 100%; border: 1px solid #ddd;"></video>' +
    '<canvas class="region-canvas" width="' +
    defaultW +
    '" height="' +
    defaultH +
    '" style="border: 1px solid #ddd; background: #fafafa; max-width: 100%; height: auto; display: block;"></canvas>' +
    "</div>" +
    '<div class="region-legend" style="margin-top: 12px; display: flex; flex-wrap: wrap; gap: 8px;"></div>' +
    "</div>"

  const canvas = chart.querySelector(".region-canvas")
  const ctx = canvas.getContext("2d")
  const slider = chart.querySelector(".region-slider")
  const timeLabel = chart.querySelector(".region-time")
  const legend = chart.querySelector(".region-legend")
  const videoEl = chart.querySelector(".region-video")
  const loadBtn = chart.querySelector(".region-load")
  const fileInput = chart.querySelector(".region-file")
  const hint = chart.querySelector(".region-hint")
  let hasVideo = false

  const clusterColor = (cid) => {
    if (cid === null || cid === undefined || cid === "")
      return "hsl(0, 0%, 55%)"
    const hue = (Number(cid) * 67) % 360
    return `hsl(${hue}, 70%, 45%)`
  }

  function draw(idx) {
    const t = times[idx]
    const boxes = data.filter((r) => Number(r.start_seconds) === t)
    const cw = canvas.width
    const ch = canvas.height

    ctx.clearRect(0, 0, cw, ch)
    const seen = new Map()

    boxes.forEach((b) => {
      // Normalized [0,1] (or pixel) coords, top-left origin -> canvas pixels.
      const px = (pixelSpace ? b.x / frameW : b.x) * cw
      const py = (pixelSpace ? b.y / frameH : b.y) * ch
      const pw = (pixelSpace ? b.w / frameW : b.w) * cw
      const ph = (pixelSpace ? b.h / frameH : b.h) * ch

      const color = clusterColor(b.cluster_id)
      ctx.lineWidth = 2
      ctx.strokeStyle = color
      ctx.fillStyle = color.replace("hsl", "hsla").replace(")", ", 0.12)")
      ctx.fillRect(px, py, pw, ph)
      ctx.strokeRect(px, py, pw, ph)

      const cid = b.cluster_id
      const hasCid = cid !== null && cid !== undefined && cid !== ""
      const tag = b.label || (hasCid ? "#" + cid : "?")
      const score =
        b.det_score != null ? " " + Number(b.det_score).toFixed(2) : ""
      ctx.fillStyle = color
      ctx.font = "14px sans-serif"
      ctx.fillText(tag + score, px + 2, Math.max(py - 4, 12))

      if (!seen.has(String(cid))) seen.set(String(cid), { color, tag })
    })

    timeLabel.textContent =
      "t = " + t.toFixed(2) + "s  •  " + boxes.length + " box(es)"

    legend.innerHTML = ""
    seen.forEach(({ color, tag }) => {
      const chip = document.createElement("span")
      chip.style.cssText =
        "display: inline-flex; align-items: center; gap: 4px; font-size: 12px; color: #333;"
      chip.innerHTML =
        '<span style="width: 12px; height: 12px; border-radius: 2px; display: inline-block; background: ' +
        color +
        ';"></span>'
      chip.appendChild(document.createTextNode(tag))
      legend.appendChild(chip)
    })
  }

  // Index of the timestamp closest to a given playback time.
  const nearestIdx = (tsec) => {
    let best = 0
    for (let i = 1; i < times.length; i++) {
      if (Math.abs(times[i] - tsec) < Math.abs(times[best] - tsec)) best = i
    }
    return best
  }

  slider.addEventListener("input", () => {
    const idx = Number(slider.value)
    draw(idx)
    if (hasVideo) videoEl.currentTime = times[idx]
  })

  // Optional: overlay the boxes on the real source video (loaded locally; the
  // package never embeds it). Times are absolute, so a full video lines up.
  loadBtn.addEventListener("click", () => fileInput.click())
  fileInput.addEventListener("change", () => {
    const file = fileInput.files && fileInput.files[0]
    if (!file) return
    videoEl.src = URL.createObjectURL(file)
    videoEl.style.display = "block"
    // Turn the canvas into a transparent overlay sitting on top of the video.
    Object.assign(canvas.style, {
      position: "absolute",
      left: "0",
      top: "0",
      width: "100%",
      height: "100%",
      background: "transparent",
      border: "none",
    })
    hint.textContent = "overlay synced to playback — play or scrub"
    loadBtn.style.display = "none"
    hasVideo = true

    videoEl.addEventListener("loadedmetadata", () => {
      // Match the overlay resolution to the frame for crisp, aligned boxes.
      canvas.width = videoEl.videoWidth || canvas.width
      canvas.height = videoEl.videoHeight || canvas.height
      videoEl.currentTime = times[0]
    })

    // Drive the bus: overlay boxes here, and publish time to any other open
    // panels for this video (charts get a playhead, annotations highlight).
    driveVideo(videoEl, videoId, (t) => {
      const idx = nearestIdx(t)
      slider.value = String(idx)
      draw(idx)
    })
  })

  // React to a video loaded by some other panel (e.g. an ObservationSeries):
  // move the slider/boxes along even without a video embedded in this panel.
  const unsub = subscribeTime(videoId, (t) => {
    if (hasVideo) return
    draw(nearestIdx(t))
    slider.value = String(nearestIdx(t))
  })
  const panel = chart.parentElement
  if (panel) panel._cleanup = unsub

  draw(0)
}

function renderAnnotationSeries(chart, data, trackDef, videoId) {
  const blank = (v) => v === null || v === undefined || String(v).trim() === ""
  const isEmpty = data.every((r) => blank(r.annotations))

  chart.innerHTML = ""
  const wrap = document.createElement("div")
  wrap.style.padding = "20px"

  const desc = document.createElement("p")
  desc.style.cssText = "margin-bottom: 12px; color: #666;"
  desc.textContent = trackDef.description || ""
  wrap.appendChild(desc)

  const controls = document.createElement("div")
  controls.style.marginBottom = "12px"
  wrap.appendChild(controls)

  // Segmentation / container tracks (e.g. shots, person_identification) carry no
  // labels of their own — explain that instead of showing blank rows.
  if (isEmpty) {
    const note = document.createElement("p")
    note.style.cssText =
      "margin: 0 0 15px; padding: 10px 12px; background: #eef2ff; " +
      "border-radius: 4px; color: #555; font-size: 13px;"
    note.textContent =
      "This track has no labels of its own — it segments the timeline " +
      "(a container / segmentation track). The " +
      data.length +
      " intervals below are its boundaries; child tracks hang off it in the " +
      "hierarchy."
    wrap.appendChild(note)
  }

  const segs = []
  data.forEach((row, i) => {
    const duration = (row.end_seconds - row.start_seconds).toFixed(1)
    const seg = document.createElement("div")
    seg.style.cssText =
      "background: #fff3e0; border-left: 4px solid #f57c00; padding: 12px; " +
      "margin: 8px 0; border-radius: 4px; transition: box-shadow 0.1s;"

    const tline = document.createElement("div")
    tline.style.cssText = "font-size: 12px; color: #666; margin-bottom: 4px;"
    tline.textContent =
      row.start_seconds.toFixed(1) +
      "s → " +
      row.end_seconds.toFixed(1) +
      "s (" +
      duration +
      "s)"

    const val = document.createElement("div")
    val.style.cssText = "font-size: 14px; color: #333;"
    if (blank(row.annotations)) {
      val.innerHTML =
        '<span style="color: #999;">Segment ' + (i + 1) + "</span>"
    } else {
      val.textContent = String(row.annotations)
    }

    seg.appendChild(tline)
    seg.appendChild(val)
    wrap.appendChild(seg)
    segs.push({ el: seg, start: row.start_seconds, end: row.end_seconds })
  })

  chart.appendChild(wrap)

  // Highlight the segment under the video playhead; offer to load a video.
  let active = null
  const unsub = subscribeTime(videoId, (t) => {
    const hit = segs.find((s) => t >= s.start && t < s.end)
    if (hit === active) return
    if (active) active.el.style.boxShadow = ""
    active = hit
    if (hit) hit.el.style.boxShadow = "0 0 0 3px #1976d2"
  })
  makeVideoLoader(videoId, controls, null)

  const panel = chart.parentElement
  if (panel) panel._cleanup = unsub
}

/**
 * Render an AnnotationListSeries (multi-label intervals) into the container.
 * @param {HTMLElement} chart - Panel chart area to render into
 * @param {Array<object>} data - Data rows as array of objects
 * @param {object} trackDef - Track definition from manifest
 * @param {string} videoId - Video identifier (unused; kept for a uniform render API)
 */
function renderAnnotationListSeries(chart, data, trackDef, videoId) {
  void videoId
  let html = '<div style="padding: 20px;">'
  html +=
    '<p style="margin-bottom: 15px; color: #666;">' +
    escapeHtml(trackDef.description || "") +
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
