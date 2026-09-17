# Seattle Traffic Cameras

`index.html` is a self-contained page that shows every live SDOT traffic
camera in Seattle as a searchable grid grouped by neighborhood, with a
player for each camera's live HLS stream. The camera list is embedded in the
page, so it runs from a `file://` URL without a server. Two Python scripts
fetch the camera list from SDOT and regenerate the page.

SDOT's own [Travelers site](https://web.seattle.gov/travelers/) shows the
same cameras as map pins that open one at a time, with no search.

## Using the page

Open `index.html` in a browser, for example with `open index.html`. The page
needs network access for thumbnails, video, and `hls.js`, which loads from
the jsDelivr CDN.

### Grid

- Search matches a camera's street description, neighborhood, and id.
- The neighborhood dropdown, the Favorites button, and the Hide offline
  button narrow the grid. Each active filter shows as a chip in the header,
  and clicking a chip clears that filter.
- The star on a thumbnail adds the camera to favorites.
- The density switch toggles between the standard and compact grid.
- The theme button overrides the operating system's light or dark setting.
  The page follows the operating system until the button is first used.

Thumbnails load once when the page opens and are not refreshed on a timer,
because 380 images polled continuously is a lot of traffic to send to a
city server for a personal tool. Reload the page to get newer snapshots.

A thumbnail that fails to load, or that SDOT replaces with its 352x240
maintenance graphic, is shown as a placeholder. This affects only the
thumbnail. A camera is marked offline when its video stream fails to start.

### Player

Clicking a thumbnail opens the player at the stream's highest bitrate. The
player has buttons for previous and next camera, fullscreen,
picture-in-picture, copying a link, and opening the raw `.m3u8` URL, which
plays in VLC or `ffplay`. The subtitle shows how long ago the stream was
last seen playing.

If a stream has not started after 12 seconds, the player shows an error
with a retry button and the direct stream link.

Video starts muted, because browsers allow muted video to autoplay without
a click. Nothing is lost, since the stream playlists declare only an H.264
video codec (`avc1`) and no audio track.

### Keyboard

| Key       | Action                                   |
|-----------|------------------------------------------|
| `/`       | Focus the search box                     |
| `←` `→`   | Previous or next camera in the player    |
| `Space`   | Play or pause                            |
| `F`       | Fullscreen                               |
| `P`       | Picture-in-picture                       |
| `C`       | Copy a link to the current camera        |
| `Esc`     | Close the player                         |

### URL parameters and saved state

| Parameter    | Effect                                    |
|--------------|-------------------------------------------|
| `cam=<id>`   | Opens the player for that camera          |
| `q=<text>`   | Sets the search text                      |
| `hood=<name>`| Filters to one neighborhood               |
| `fav=1`      | Shows favorites only                      |
| `liveonly=1` | Hides offline cameras                     |

The page keeps these parameters in sync with the current view, so the
address bar can be copied to share it. Search text, filters, favorites,
grid density, theme, and scroll position are also saved in `localStorage`
and restored on the next visit. A parameter in the URL takes precedence over
the saved value.

## Data sources

SDOT's Travelers site is an ASP.NET application backed by three sources.

The camera list comes from
`web.seattle.gov/Travelers/api/Map/GetCamerasByNeighborhood?neighborhood=<name>`.
The API has no endpoint that returns every camera, only one per
neighborhood, for 13 fixed neighborhood names. Each entry has an `Id`,
`Description`, `ImageUrl`, and `Type`, which is either `sdot` or `wsdot`.

Live video for every `sdot` camera is served by one Wowza streaming server.
`web.seattle.gov/Travelers/api/Map/WowsaUrl` returns the URL template

```
https://61e0c5d388c2e.streamlock.net:443/live/{stream}/playlist.m3u8
```

where `{stream}` is the camera's `ImageUrl` with `.jpg` replaced by
`.stream`, so `QAnne_N_Roy_NS.jpg` becomes `QAnne_N_Roy_NS.stream`. The
mapping was worked out from SDOT's `camera.video.js`, and no per-camera
lookup is involved. The server sends `Access-Control-Allow-Origin: *`, which
is what lets a `file://` page play the streams without a proxy.

Thumbnails are static JPEGs at
`www.seattle.gov/trafficcams/images/<ImageUrl>`.

Cameras of type `wsdot` are state highway cameras such as SR-99. SDOT's site
serves them only as still images and wires its video button only to `sdot`
cameras, so `fetch_cameras.py` stores them in `data/cameras.json` and
`generate_html.py` leaves them out of the page. Showing them as refreshing
stills would be a reasonable addition.

## Regenerating the page

```sh
python3 scripts/fetch_cameras.py    # refresh data/cameras.json from SDOT
python3 scripts/generate_html.py    # rebuild index.html from the JSON
```

Run both to pick up cameras SDOT has added, removed, or renamed. Nothing
runs them on a schedule. `index.html` and `data/cameras.json` are committed
so that a fresh clone works without running either script.

`flake.nix` defines a dev shell with `python3` and `curl`, which you can
enter with `nix develop`. Running `direnv allow` once loads it automatically
when you `cd` into the directory. Any other `python3` and `curl` work too.

`AGENTS.md` records the debugging history behind the code and the
behaviors that are easy to break.
