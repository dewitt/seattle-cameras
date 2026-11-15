# Seattle Traffic Cameras

`index.html` is a single-file viewer for Seattle traffic cameras and Puget
Sound highway cameras. It reads camera metadata embedded at build time and
runs directly from a `file://` URL with no local server. Two Python scripts,
`scripts/fetch_cameras.py` and `scripts/generate_html.py`, fetch the camera
index from SDOT into `data/cameras.json` and regenerate `index.html`.

SDOT's own [Travelers site](https://web.seattle.gov/travelers/) displays the
same cameras as unsearchable map pins that open one at a time. This page adds
instant search, geographic corridor sorting, an interactive overview map, a
multi-camera live wall, and both live SDOT HLS streams and refreshing WSDOT
highway snapshots.

## Using the page

Open <https://seattle.unto.net/> or open `index.html`
locally in a browser, for example with `open index.html`. The page needs
network access for camera snapshots, live HLS video, Esri map tiles, and two
libraries loaded from jsDelivr (`hls.js` and Leaflet).

All views share the header controls:

- Search matches a camera's street description, neighborhood, and ID.
- The location menu selects all cameras, 8 highway and bridge corridors
  sorted geographically (`I-5`, `I-90`, `SR-520`, `SR-99`, `I-405`, Ship Canal
  Bridges, West Seattle & Duwamish Bridges, and Mercer St & Denny Way), the
  13 Seattle neighborhoods, or Regional Highways.
- `Favorites`, `Video only`, and `Hide offline` narrow the active view. Each
  active filter appears as a removable chip below the header.
- The `Refresh snapshots` button reloads still thumbnails across the page
  on demand with a fresh timestamp query parameter.
- The theme button cycles through Auto, Light, and Dark modes, following the
  operating system setting in Auto mode.

### Grid

- Cameras are grouped by neighborhood, or listed in a single corridor
  section sorted North-to-South or West-to-East when a corridor is selected.
  Saved favorites appear in a dedicated top section unless a corridor filter
  is active.
- The star button on a thumbnail pins or unpins a favorite.
- The density switch toggles between compact and standard card sizes.
- An SDOT camera with an active HLS stream whose thumbnail fails or matches
  SDOT's `352x240` maintenance graphic shows a preview placeholder while
  remaining playable for live video. A camera is marked `OFFLINE` when both
  its stream and snapshot fail, or when a `wsdot` or snapshot-only camera
  fails to load an image.

### Map

- Switch to Map view (`M`) to inspect geocoded cameras on a Leaflet map over
  Esri `World_Street_Map` tiles, with an inverted dark filter in dark mode.
- Co-located cameras at the same coordinates merge into a numbered
  intersection pin colored by status (green for live video, blue for WSDOT
  highway still, gold for favorite, red when all cameras at that spot are
  offline).
- Hovering a pin shows the primary camera's thumbnail, description, area, and
  status; clicking opens the player modal, where adjacent co-located cameras
  appear in the nearby strip.
- Clicking `Fit to results` zooms the map to match the currently filtered
  cameras.

### Wall

- Switch to Wall view (`W`) to monitor 4 (`2x2`) or 6 (`3x2`) cameras
  simultaneously, paged through the active filter or one of the bridge and
  highway presets.
- SDOT cameras with active streams play live HLS video in each tile while
  `wsdot` cameras and snapshot-only SDOT cameras refresh snapshots every 15
  seconds. Failed HLS tiles fall back to 15-second snapshots in place before
  marking a camera offline.
- The default Seattle preset skips cameras flagged as snapshot-only at build
  time. Opening the full player modal pauses the Wall streams until the
  modal closes so the modal player has full connection headroom to the Wowza
  host.

### Player

Clicking any camera opens the player modal. Active SDOT (`sdot`) cameras play
live H.264 video over HLS at the highest bitrate stream, starting muted so
browsers allow autoplay. If an SDOT stream returns `404` or fails to load,
the player switches automatically to a 15-second `STILL · 15S` snapshot
stream and marks the camera offline only if the snapshot fails too. WSDOT
(`wsdot`) cameras display a still snapshot that refreshes automatically every
15 seconds.

Below the video frame, cameras within 3 km appear as clickable pills labeled
`Same spot` (within 35 m) or with distance and compass direction. Footer
controls provide previous and next stepping, `Favorite`, `Map` (jumps to that
camera's coordinates), `Fullscreen`, `PiP` (remains open if you close the
modal and cleans up when exited), `Copy link`, and the raw `.m3u8` or image
URL.

### Keyboard

| Key | Scope | Action |
|---|---|---|
| `/` | Page | Focus the search box |
| `G` | Page | Switch to Grid view |
| `M` | Page | Switch to Map view |
| `W` | Page | Switch to Wall view |
| `R` | Page | Refresh all visible snapshots |
| `←` `→` | Player | Previous or next camera in current list |
| `Space` | Player | Play or pause live video |
| `F` | Player | Toggle fullscreen |
| `P` | Player | Toggle Picture-in-Picture |
| `M` | Player | Jump to camera location on the map |
| `C` | Player | Copy direct link to current camera |
| `Esc` | Player | Close player modal |

### URL parameters and saved state

| Parameter | Effect |
|---|---|
| `cam=<id>` | Opens the player for that camera |
| `q=<text>` | Sets the search query |
| `hood=<name>` | Filters to a neighborhood or corridor (`corridor:sr520`) |
| `fav=1` | Shows favorites only |
| `video=1` | Shows live HLS SDOT cameras only |
| `liveonly=1` | Hides cameras marked offline |
| `view=<mode>` | Selects `grid`, `map`, or `wall` |

The page synchronizes filter parameters into the browser address bar and saves
search text, filters, favorites, grid density, theme, active view, wall tile
count, and grid scroll position in `localStorage`. URL parameters take
precedence over saved state on load.

## Data sources

SDOT's Travelers application exposes four ASP.NET JSON endpoints queried at
build time by `scripts/fetch_cameras.py`:

- `https://web.seattle.gov/Travelers/api/Map/Data?zoomId=16&type=2`
  returns all map clusters with `[Lat, Lng]` coordinates, 5 SDOT cameras
  omitted from the neighborhood lists, and regional WSDOT highway cameras.
- `https://web.seattle.gov/Travelers/api/Map/GetAllNeighborhoods`
  returns the 13 Seattle neighborhood names.
- `https://web.seattle.gov/Travelers/api/Map/GetCamerasByNeighborhood?neighborhood=<name>`
  supplies canonical neighborhood labels for city cameras. Unlisted SDOT
  cameras take the nearest neighborhood by coordinate, and highway cameras
  fall under `Regional Highways`.
- `https://web.seattle.gov/Travelers/api/Map/WowsaUrl` returns the Wowza HLS
  template:

```
https://61e0c5d388c2e.streamlock.net:443/live/{stream}/playlist.m3u8
```

For each `sdot` camera, `{stream}` is `ImageUrl` with `.jpg` replaced by
`.stream`. Live HLS playlists and `.ts` segments include
`Access-Control-Allow-Origin: *`, allowing direct playback from `file://`.

Still images resolve from two roots:

- SDOT snapshots load from
  `https://www.seattle.gov/trafficcams/images/<ImageUrl>`.
- WSDOT snapshots load from `https://images.wsdot.wa.gov/nw/<ImageUrl>`,
  with `.jpg` appended for entries that omit a file extension.

Map view loads raster tiles from Esri `World_Street_Map`:

```
https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}
```

## Regenerating the page

```sh
python3 scripts/fetch_cameras.py    # refresh data/cameras.json from SDOT
python3 scripts/generate_html.py    # rebuild index.html from the JSON
```

The current dataset embeds 656 unique cameras (395 `sdot` and 261 `wsdot`),
recording `StreamActive` from Wowza HLS manifest checks and `ImageActive`
from WSDOT snapshot checks (`www.seattle.gov` thumbnails are left unprobed at
build time and cached via CloudFront on initial load).
`data/cameras.json` and `index.html` are committed so a fresh clone works
immediately without running either script.

[The GitHub Pages workflow](.github/workflows/deploy-pages.yml) rebuilds and
deploys `index.html` to <https://seattle.unto.net/> on pushes
to `main`, manual dispatch, and once daily at `13:17` UTC (`17 13 * * *`). It
runs `scripts/fetch_cameras.py` first and falls back to the checked-in
`data/cameras.json` if SDOT's API is unreachable.

`flake.nix` provides a dev shell with `python3` and `curl`, entered with
`nix develop`. Running `direnv allow` loads it automatically on `cd`. Any
system `python3` and `curl` also work.

`AGENTS.md` records the debugging history and invariants behind the code.
