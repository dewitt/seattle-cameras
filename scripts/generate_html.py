#!/usr/bin/env python3
"""
Generate index.html from data/cameras.json.

Only Type == "sdot" cameras get embedded: those are the ones SDOT serves off
its Wowza streaming server (streamlock.net) with a real live HLS feed. The
other type present in the API response, "wsdot" (state highway cameras,
e.g. SR-99), are static-refresh JPEGs only — confirmed by reading SDOT's own
site JS (camera.video.js): the "Video" button there is only wired up when
camera.Type === "sdot". wsdot cameras are left out of this tool for now.

Run scripts/fetch_cameras.py first to (re)generate data/cameras.json.
"""
import json

with open("data/cameras.json") as f:
    cams = json.load(f)

sdot = [c for c in cams if c["Type"] == "sdot"]
sdot.sort(key=lambda c: (c["Neighborhood"], c["Description"]))

for c in sdot:
    c["StreamName"] = c["ImageUrl"].replace(".jpg", ".stream")

data_json = json.dumps(sdot, separators=(",", ":"))
print(f"{len(sdot)} sdot cameras embedded")

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Seattle Traffic Cameras — Live</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/hls.js@1.5.17/dist/hls.min.js"></script>
<style>
  :root {
    --bg: #0b0d10;
    --panel: #14171c;
    --panel2: #1c2027;
    --border: #2a2f38;
    --text: #e6e9ee;
    --muted: #8b93a1;
    --accent: #4da3ff;
    --offline: #ff5d5d;
    --thumb-bg: #000000;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  }
  header {
    position: sticky; top: 0; z-index: 20;
    background: var(--panel);
    border-bottom: 1px solid var(--border);
    padding: 12px 16px;
    display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
  }
  header h1 { font-size: 16px; margin: 0; font-weight: 600; white-space: nowrap; }
  header .count { color: var(--muted); font-size: 13px; }
  #search {
    flex: 1; min-width: 160px; max-width: 320px;
    background: var(--panel2); border: 1px solid var(--border); color: var(--text);
    padding: 8px 10px; border-radius: 6px; font-size: 14px;
  }
  #neighborhood-filter {
    background: var(--panel2); border: 1px solid var(--border); color: var(--text);
    padding: 8px 10px; border-radius: 6px; font-size: 14px;
  }
  #hide-offline { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--muted); }
  main { padding: 16px; }
  .neighborhood-heading {
    font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--muted); margin: 24px 4px 10px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 12px;
  }
  .card {
    background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
    overflow: hidden; cursor: pointer; transition: border-color .15s, transform .15s;
  }
  .card:hover { border-color: var(--accent); transform: translateY(-1px); }
  .card.offline { opacity: 0.45; }
  .thumb-wrap { position: relative; width: 100%; aspect-ratio: 16/9; background: var(--thumb-bg); }
  .thumb-wrap img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .thumb-wrap img.thumb-broken { display: none; }
  .thumb-wrap .no-preview {
    display: none; position: absolute; inset: 0; align-items: center; justify-content: center;
    color: var(--muted); font-size: 12px; text-align: center; padding: 8px;
  }
  .thumb-wrap img.thumb-broken + .no-preview { display: flex; }
  .badge {
    position: absolute; top: 6px; right: 6px; font-size: 10px; padding: 2px 6px;
    border-radius: 4px; background: rgba(0,0,0,0.6); color: rgba(255,255,255,0.85);
  }
  .badge.offline { color: var(--offline); }
  .fav-btn {
    position: absolute; top: 6px; left: 6px; font-size: 14px; line-height: 1;
    padding: 3px 6px; border-radius: 4px; background: rgba(0,0,0,0.6);
    color: rgba(255,255,255,0.85); border: none; cursor: pointer;
  }
  .fav-btn.active, .fav-btn:hover { color: #ffd54a; }
  .card .label { padding: 8px 10px; font-size: 13px; line-height: 1.3; }
  .card .label .desc { font-weight: 500; }
  .card .label .hood { color: var(--muted); font-size: 11px; margin-top: 2px; }

  #modal {
    display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.92); z-index: 100;
    align-items: center; justify-content: center; flex-direction: column;
  }
  #modal.open { display: flex; }
  #modal video { max-width: 96vw; max-height: 82vh; background: #000; }
  #modal-title { color: var(--text); font-size: 15px; margin: 12px 0 4px; text-align: center; }
  #modal-sub { color: var(--muted); font-size: 12px; margin-bottom: 10px; text-align: center; }
  #modal-controls { display: flex; gap: 10px; margin-top: 6px; flex-wrap: wrap; justify-content: center; }
  #modal-controls button, #modal-controls a {
    background: var(--panel2); border: 1px solid var(--border); color: var(--text);
    padding: 8px 14px; border-radius: 6px; font-size: 13px; cursor: pointer; text-decoration: none;
  }
  #modal-controls button:hover, #modal-controls a:hover { border-color: var(--accent); }
  #modal-close {
    position: absolute; top: 16px; right: 20px; font-size: 22px; color: var(--muted);
    background: none; border: none; cursor: pointer;
  }
  #modal-close:hover { color: var(--text); }
  #modal-error { color: var(--offline); font-size: 13px; margin-top: 8px; display: none; }

  @media (prefers-color-scheme: light) {
    :root {
      --bg: #f5f6f8; --panel: #ffffff; --panel2: #eef0f3; --border: #dde1e6;
      --text: #1b1f24; --muted: #6b7280; --thumb-bg: #d8dce2;
    }
  }
</style>
</head>
<body>

<header>
  <h1>Seattle Traffic Cameras</h1>
  <span class="count" id="visible-count"></span>
  <input id="search" type="text" placeholder="Search street or neighborhood…">
  <select id="neighborhood-filter"><option value="">All neighborhoods</option></select>
  <label id="hide-offline"><input type="checkbox" id="hide-offline-check"> Hide offline</label>
</header>

<main id="main"></main>

<div id="modal">
  <button id="modal-close" title="Close (Esc)">✕</button>
  <video id="modal-video" controls autoplay playsinline></video>
  <div id="modal-title"></div>
  <div id="modal-sub"></div>
  <div id="modal-error"></div>
  <div id="modal-controls">
    <button id="btn-prev">← Prev</button>
    <button id="btn-fullscreen">Fullscreen</button>
    <button id="btn-copy-link">Copy link</button>
    <button id="btn-next">Next →</button>
    <a id="btn-open-direct" href="#" target="_blank">Open direct .m3u8</a>
  </div>
</div>

<script>
const CAMERAS = __DATA_JSON__;
const WOWZA_TEMPLATE = "https://61e0c5d388c2e.streamlock.net:443/live/{stream}/playlist.m3u8";
const THUMB_BASE = "https://www.seattle.gov/trafficcams/images/";
const FAVORITES_KEY = "sc-favorites";
const FILTERS_KEY = "sc-filters";
const SCROLL_KEY = "sc-scroll";

let filtered = CAMERAS.slice();
let currentIndex = -1;
let hls = null;
const offlineIds = new Set();
const camById = new Map(CAMERAS.map(c => [c.Id, c]));

function loadFavorites() {
  try { return new Set(JSON.parse(localStorage.getItem(FAVORITES_KEY) || "[]")); }
  catch { return new Set(); }
}
const favorites = loadFavorites();
function saveFavorites() {
  localStorage.setItem(FAVORITES_KEY, JSON.stringify([...favorites]));
}
function toggleFavorite(id) {
  if (favorites.has(id)) favorites.delete(id); else favorites.add(id);
  saveFavorites();
  render();
}

function saveFilterState() {
  const state = {
    q: document.getElementById("search").value,
    hood: document.getElementById("neighborhood-filter").value,
    hideOffline: document.getElementById("hide-offline-check").checked,
  };
  localStorage.setItem(FILTERS_KEY, JSON.stringify(state));
}
function restoreFilterState() {
  let state;
  try { state = JSON.parse(localStorage.getItem(FILTERS_KEY) || "null"); }
  catch { state = null; }
  if (!state) return;
  if (state.q) document.getElementById("search").value = state.q;
  if (state.hood) document.getElementById("neighborhood-filter").value = state.hood;
  document.getElementById("hide-offline-check").checked = !!state.hideOffline;
}

function streamUrl(cam) {
  return WOWZA_TEMPLATE.replace("{stream}", cam.StreamName);
}
function thumbUrl(cam) {
  return THUMB_BASE + cam.ImageUrl + "?t=" + Date.now();
}

function buildNeighborhoodOptions() {
  const sel = document.getElementById("neighborhood-filter");
  const hoods = [...new Set(CAMERAS.map(c => c.Neighborhood))].sort();
  for (const h of hoods) {
    const opt = document.createElement("option");
    opt.value = h; opt.textContent = h;
    sel.appendChild(opt);
  }
}

function buildCard(cam) {
  const card = document.createElement("div");
  card.className = "card" + (offlineIds.has(cam.Id) ? " offline" : "");
  card.dataset.id = cam.Id;
  const isFav = favorites.has(cam.Id);
  card.innerHTML = `
    <div class="thumb-wrap">
      <img loading="lazy" src="${thumbUrl(cam)}" alt="">
      <span class="no-preview">No preview</span>
      <button class="fav-btn${isFav ? ' active' : ''}" title="${isFav ? 'Remove from favorites' : 'Add to favorites'}">${isFav ? '★' : '☆'}</button>
      <span class="badge ${offlineIds.has(cam.Id) ? 'offline' : ''}">${offlineIds.has(cam.Id) ? 'OFFLINE' : 'LIVE'}</span>
    </div>
    <div class="label">
      <div class="desc">${cam.Description}</div>
      <div class="hood">${cam.Id}</div>
    </div>`;
  const img = card.querySelector("img");
  img.addEventListener("load", () => {
    // SDOT sometimes serves a valid 200 OK image that's actually a static
    // "Camera Under Maintenance" placeholder graphic (always 352x240) —
    // that never fires an error event, but it's not a real preview frame.
    // Real thumbnails are always full camera resolution. This says nothing
    // about the live stream itself, which may work fine — see below.
    if (img.naturalWidth === 352 && img.naturalHeight === 240) {
      img.classList.add("thumb-broken");
    }
  });
  img.addEventListener("error", () => {
    const retries = Number(img.dataset.retries || 0);
    // A single failed thumbnail fetch is often a transient blip — retry
    // with backoff before giving up on the preview image.
    if (retries < 2) {
      img.dataset.retries = retries + 1;
      setTimeout(() => { img.src = thumbUrl(cam); }, 2000 * (retries + 1));
      return;
    }
    // The thumbnail service (seattle.gov) and the video stream (Wowza)
    // are separate hosts — a dead thumbnail does NOT mean the camera's
    // live feed is down, so only hide the broken preview image. Offline
    // status is determined solely by actually trying to play the stream
    // (see the HLS error handling in openModal).
    img.classList.add("thumb-broken");
  });
  card.querySelector(".fav-btn").addEventListener("click", (e) => {
    e.stopPropagation();
    toggleFavorite(cam.Id);
  });
  card.addEventListener("click", () => openModal(cam));
  return card;
}

function appendSection(main, heading, cams) {
  if (cams.length === 0) return;
  const h = document.createElement("div");
  h.className = "neighborhood-heading";
  h.textContent = heading;
  main.appendChild(h);
  const grid = document.createElement("div");
  grid.className = "grid";
  for (const cam of cams) grid.appendChild(buildCard(cam));
  main.appendChild(grid);
}

function render() {
  const main = document.getElementById("main");
  main.innerHTML = "";
  const hideOffline = document.getElementById("hide-offline-check").checked;
  const visible = filtered.filter(c => !(hideOffline && offlineIds.has(c.Id)));

  appendSection(main, "★ Favorites", visible.filter(c => favorites.has(c.Id)));

  const rest = visible.filter(c => !favorites.has(c.Id));
  let lastHood = null;
  let bucket = [];
  for (const cam of rest) {
    if (cam.Neighborhood !== lastHood) {
      appendSection(main, lastHood, bucket);
      lastHood = cam.Neighborhood;
      bucket = [];
    }
    bucket.push(cam);
  }
  appendSection(main, lastHood, bucket);

  document.getElementById("visible-count").textContent = visible.length + " / " + CAMERAS.length + " cameras";
}

function applyFilters() {
  const q = document.getElementById("search").value.trim().toLowerCase();
  const hood = document.getElementById("neighborhood-filter").value;
  filtered = CAMERAS.filter(c => {
    if (hood && c.Neighborhood !== hood) return false;
    if (q && !(c.Description.toLowerCase().includes(q) || c.Neighborhood.toLowerCase().includes(q))) return false;
    return true;
  });
  saveFilterState();
  render();
}

function openModal(cam) {
  currentIndex = filtered.indexOf(cam);
  const modal = document.getElementById("modal");
  const video = document.getElementById("modal-video");
  const errEl = document.getElementById("modal-error");
  errEl.style.display = "none";
  document.getElementById("modal-title").textContent = cam.Description;
  document.getElementById("modal-sub").textContent = cam.Neighborhood + "  ·  " + cam.Id;
  document.getElementById("btn-open-direct").href = streamUrl(cam);

  const deepLink = new URL(location.href);
  deepLink.searchParams.set("cam", cam.Id);
  history.replaceState(null, "", deepLink);

  if (hls) { hls.destroy(); hls = null; }

  const url = streamUrl(cam);
  if (video.canPlayType("application/vnd.apple.mpegurl")) {
    // Prefer native HLS (Safari) — more reliable than hls.js's MSE path there,
    // and Safari also reports MediaSource support so Hls.isSupported() alone
    // would wrongly route Safari through hls.js and leave the video stuck at 0:00.
    video.src = url;
    video.play().catch(() => {});
  } else if (Hls.isSupported()) {
    hls = new Hls({ capLevelToPlayerSize: false, startLevel: -1 });
    hls.loadSource(url);
    hls.attachMedia(video);
    hls.on(Hls.Events.MANIFEST_PARSED, () => {
      // force the highest-bitrate variant available
      if (hls.levels && hls.levels.length > 1) {
        hls.currentLevel = hls.levels.length - 1;
      }
      video.play().catch(() => {});
    });
    let hlsRetries = 0;
    hls.on(Hls.Events.ERROR, (event, data) => {
      if (!data.fatal) return;
      // hls.js's own recommended recovery: a fatal network/media error is
      // often recoverable (brief blip, keyframe glitch) rather than proof
      // the camera is actually offline — try recovering before giving up.
      if (hlsRetries < 2 && data.type === Hls.ErrorTypes.NETWORK_ERROR) {
        hlsRetries++;
        hls.startLoad();
        return;
      }
      if (hlsRetries < 2 && data.type === Hls.ErrorTypes.MEDIA_ERROR) {
        hlsRetries++;
        hls.recoverMediaError();
        return;
      }
      offlineIds.add(cam.Id);
      errEl.textContent = "This feed isn't responding right now (camera may be offline).";
      errEl.style.display = "block";
    });
  } else {
    errEl.textContent = "This browser can't play HLS video.";
    errEl.style.display = "block";
  }

  modal.classList.add("open");
}

function closeModal() {
  document.getElementById("modal").classList.remove("open");
  const video = document.getElementById("modal-video");
  video.pause();
  video.removeAttribute("src");
  video.load();
  if (hls) { hls.destroy(); hls = null; }

  const deepLink = new URL(location.href);
  deepLink.searchParams.delete("cam");
  history.replaceState(null, "", deepLink);
}

function step(delta) {
  if (currentIndex === -1 || filtered.length === 0) return;
  let idx = (currentIndex + delta + filtered.length) % filtered.length;
  openModal(filtered[idx]);
}

document.getElementById("search").addEventListener("input", applyFilters);
document.getElementById("neighborhood-filter").addEventListener("change", applyFilters);
document.getElementById("hide-offline-check").addEventListener("change", () => { saveFilterState(); render(); });
document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("btn-prev").addEventListener("click", () => step(-1));
document.getElementById("btn-next").addEventListener("click", () => step(1));
document.getElementById("btn-fullscreen").addEventListener("click", () => {
  const video = document.getElementById("modal-video");
  if (video.requestFullscreen) video.requestFullscreen();
});
document.getElementById("btn-copy-link").addEventListener("click", async () => {
  const cam = filtered[currentIndex];
  if (!cam) return;
  const deepLink = new URL(location.href);
  deepLink.searchParams.set("cam", cam.Id);
  const link = deepLink.toString();
  const btn = document.getElementById("btn-copy-link");

  let copied = false;
  try {
    // The async Clipboard API can hang indefinitely waiting on a permission
    // prompt in some embedded/automated contexts instead of rejecting, so
    // race it against a timeout rather than trusting it to always settle.
    await Promise.race([
      navigator.clipboard.writeText(link),
      new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), 2000)),
    ]);
    copied = true;
  } catch {
    // Fall back to the old execCommand trick for browsers/contexts where
    // the async Clipboard API is unavailable, denied, or stalls.
    const ta = document.createElement("textarea");
    ta.value = link;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try { copied = document.execCommand("copy"); } catch {}
    document.body.removeChild(ta);
  }

  const original = btn.textContent;
  btn.textContent = copied ? "Copied!" : "Copy failed";
  setTimeout(() => { btn.textContent = original; }, 1500);
});
document.getElementById("modal").addEventListener("click", (e) => {
  if (e.target.id === "modal") closeModal();
});
document.addEventListener("keydown", (e) => {
  if (!document.getElementById("modal").classList.contains("open")) return;
  if (e.key === "Escape") closeModal();
  if (e.key === "ArrowRight") step(1);
  if (e.key === "ArrowLeft") step(-1);
});
document.addEventListener("keydown", (e) => {
  // "/" focuses search, like GitHub — but not while typing elsewhere or
  // while the modal (which has its own arrow/Escape handling) is open.
  if (e.key !== "/") return;
  if (document.getElementById("modal").classList.contains("open")) return;
  const tag = document.activeElement.tagName;
  if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
  e.preventDefault();
  document.getElementById("search").focus();
});
window.addEventListener("scroll", () => {
  clearTimeout(window._scrollSaveTimer);
  window._scrollSaveTimer = setTimeout(() => {
    localStorage.setItem(SCROLL_KEY, String(window.scrollY));
  }, 200);
}, { passive: true });

buildNeighborhoodOptions();
restoreFilterState();
applyFilters();

const deepLinkId = new URL(location.href).searchParams.get("cam");
const deepLinkCam = deepLinkId && camById.get(deepLinkId);
if (deepLinkCam) {
  openModal(deepLinkCam);
} else {
  const savedScroll = Number(localStorage.getItem(SCROLL_KEY) || 0);
  if (savedScroll > 0) window.scrollTo(0, savedScroll);
}
</script>
</body>
</html>
"""

html = html.replace("__DATA_JSON__", data_json)

out_path = "index.html"
with open(out_path, "w") as f:
    f.write(html)
print(f"wrote {out_path} ({len(html)} bytes)")
