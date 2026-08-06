# Seattle Traffic Cameras

A single self-contained `index.html` that shows every live Seattle SDOT
traffic camera feed, grouped by neighborhood, with a fullscreen live-video
viewer — no server, no build step, no dependencies beyond a browser with
internet access. Built because the [official SDOT Travelers
site](https://web.seattle.gov/travelers/) makes this needlessly clunky (map
pins, one camera at a time, no search).

## Using it

Open `index.html` directly in a browser (double-click it, or `open
index.html`). That's it — everything is embedded, including the camera list.

- Search by street or neighborhood, or filter by neighborhood via the dropdown
- Click any thumbnail to open a fullscreen live player at the highest
  available bitrate
- Prev/Next buttons or ← → arrow keys to flip between cameras without
  closing the viewer
- Thumbnails that fail to load are automatically marked **OFFLINE** and can
  be hidden via the toggle
- "Open direct .m3u8" gives you the raw stream URL for VLC, `ffplay`, etc.

Thumbnails load once on page open, not on a polling interval — hitting SDOT's
servers with continuous refresh requests for 380 images felt like bad
citizenship for a personal tool. Reload the page for fresher snapshots.

## How it works

SDOT's Travelers site (an ASP.NET app) is a thin wrapper around two data
sources:

1. **Camera list & metadata** — `web.seattle.gov/Travelers/api/Map/GetCamerasByNeighborhood?neighborhood=<name>`
   returns cameras for one of 13 fixed neighborhoods (there's no
   "list everything" endpoint). Each entry has an `Id`, `Description`,
   `ImageUrl`, and `Type` (`sdot` or `wsdot`).
2. **Live video** — all `sdot`-type cameras are served off a single shared
   Wowza streaming server. The stream URL template comes from
   `web.seattle.gov/Travelers/api/Map/WowsaUrl`:
   `https://61e0c5d388c2e.streamlock.net:443/live/{stream}/playlist.m3u8`,
   where `{stream}` is the camera's `ImageUrl` with `.jpg` swapped for
   `.stream` (e.g. `QAnne_N_Roy_NS.jpg` → `QAnne_N_Roy_NS.stream`). No
   per-camera lookup needed — this pattern is entirely mechanical and was
   reverse-engineered from SDOT's own `camera.video.js`.
3. **Thumbnails** — static JPEGs at `www.seattle.gov/trafficcams/images/<ImageUrl>`.

`wsdot`-type cameras (state highway cams, e.g. SR-99) are static-refresh
JPEGs only — SDOT's own site only wires up a "Video" button for `sdot`
cameras — so they're fetched into `data/cameras.json` but excluded from the
generated page. Extending this to show wsdot cameras as auto-refreshing
stills (not video) would be a reasonable future addition.

The Wowza CORS headers (`Access-Control-Allow-Origin: *`) mean all of this
works from a `file://` page with no proxy needed.

## Regenerating

```sh
python3 scripts/fetch_cameras.py    # refresh data/cameras.json from SDOT's API
python3 scripts/generate_html.py    # rebuild index.html from data/cameras.json
```

Run both whenever you want to pick up new/removed/renamed cameras. There's
no CI or scheduled job for this — it's a manual, occasional refresh.

## Known limitations / things worth revisiting

- **"CAMERA UNDER MAINTENANCE" placeholders read as LIVE.** A handful of
  cameras serve a static maintenance-notice graphic instead of failing to
  load, so the thumbnail `onerror` offline-detection doesn't catch them —
  the image *does* load successfully, it's just not real footage. Clicking
  through will show the video player spin/fail because the underlying
  Wowza stream for that camera is genuinely down. No fix currently; would
  need either a known-placeholder-filename list or an image hash/dimension
  check.
- **Hung (not failed) streams look identical to "still loading."** If
  SDOT's Wowza server is timing out at the TLS layer (has happened — see
  git history) rather than cleanly erroring, `hls.js`'s error handler never
  fires and the player just spins forever. Worth adding an explicit
  timeout that surfaces "feed not responding" after ~10s.
- **wsdot cameras aren't shown at all** (see above).

See `AGENTS.md` for the debugging history behind these and other gotchas
worth knowing before touching this code.
