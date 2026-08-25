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

- Search by street, neighborhood, or camera ID (press `/` to focus search)
- Filter by neighborhood dropdown or toggle favorites only and live only
- Shareable URL parameters (`?q=...`, `?hood=...`, `?cam=...`, `?fav=1`)
- Click any thumbnail to open the fullscreen live player at highest bitrate
- Navigate between cameras via Prev/Next buttons or `←` / `→` arrow keys
- Full keyboard control (`Space` play/pause, `F` fullscreen, `P` PiP,
  `C` copy link, `Esc` close)
- Display density switch (standard grid or compact grid)
- Automatic dark/light theme support with manual toggle override
- Thumbnails that fail to load or show maintenance graphics display a clean
  fallback placeholder and can be filtered via Hide offline
- Direct stream link gives you the raw `.m3u8` URL for VLC, `ffplay`, etc.

Thumbnails load once on page open, not on a polling interval — hitting SDOT's
servers with continuous refresh requests for 380 images felt like bad
citizenship for a personal tool. Reload the page for fresher snapshots.

## How it works

SDOT's Travelers site (an ASP.NET app) is a thin wrapper around two data
sources:

1. **Camera list & metadata** —
   `web.seattle.gov/Travelers/api/Map/GetCamerasByNeighborhood?neighborhood=<name>`
   returns cameras for one of 13 fixed neighborhoods (there's no list
   everything endpoint). Each entry has an `Id`, `Description`, `ImageUrl`,
   and `Type` (`sdot` or `wsdot`).
2. **Live video** — all `sdot`-type cameras are served off a single shared
   Wowza streaming server. The stream URL template comes from
   `web.seattle.gov/Travelers/api/Map/WowsaUrl`:
   `https://61e0c5d388c2e.streamlock.net:443/live/{stream}/playlist.m3u8`,
   where `{stream}` is the camera's `ImageUrl` with `.jpg` swapped for
   `.stream` (e.g. `QAnne_N_Roy_NS.jpg` → `QAnne_N_Roy_NS.stream`). No
   per-camera lookup needed — this pattern is entirely mechanical and was
   reverse-engineered from SDOT's own `camera.video.js`.
3. **Thumbnails** — static JPEGs at
   `www.seattle.gov/trafficcams/images/<ImageUrl>`.

`wsdot`-type cameras (state highway cams, e.g. SR-99) are static-refresh
JPEGs only — SDOT's own site only wires up video for `sdot` cameras — so
they are fetched into `data/cameras.json` but excluded from the generated
page. Extending this to show wsdot cameras as auto-refreshing stills (not
video) would be a reasonable future addition.

The Wowza CORS headers (`Access-Control-Allow-Origin: *`) mean all of this
works from a `file://` page with no proxy needed.

## Regenerating

```sh
python3 scripts/fetch_cameras.py    # refresh data/cameras.json from SDOT's API
python3 scripts/generate_html.py    # rebuild index.html from data/cameras.json
```

Run both whenever you want to pick up new/removed/renamed cameras. There is
no CI or scheduled job for this — it is a manual, occasional refresh.

## Known limitations / notes

- **Stalled stream watchdog**: A 12-second watchdog timer detects hung Wowza
  TLS connections or offline feeds and surfaces retry and direct stream links.
- **Maintenance placeholders**: Standard 352x240 maintenance placeholders
  served by SDOT are automatically caught and flagged with fallback badges.
- **wsdot cameras are not shown**: Only live SDOT HLS video feeds are
  currently embedded.

See `AGENTS.md` for the debugging history behind these and other gotchas
worth knowing before touching this code.
