# Working in this repo

seattle-cameras is a personal tool that builds one self-contained
`index.html` showing Seattle SDOT live HLS traffic cameras and Puget Sound
WSDOT highway cameras across Grid, interactive Map, and Multi-Cam Wall
views. There is no server and no framework. Two Python scripts fetch the
camera list and embed it in the page. Both `CLAUDE.md` and `GEMINI.md` are
symlinks to this file.

`README.md` describes the page features, the SDOT APIs, and the stream URLs,
and is the reference for those. This file covers how to change the code
without breaking it.

The project is for one person's use. When simplicity and edge-case handling
pull in different directions, keep it simple.

## Environment

The dev shell comes from a Nix flake loaded by direnv, and provides
`python3` and `curl`. Add new tooling to `flake.nix` instead of assuming it
is installed globally.

```sh
nix develop --command python3 scripts/generate_html.py
nix develop --command python3 scripts/fetch_cameras.py
```

Nix ignores untracked files, so `git add` a new file before the flake will
see it.

## Where the code lives

`index.html` is generated. The source is the HTML template string inside
`scripts/generate_html.py`, which reads `data/cameras.json` and embeds the
config and camera list as JSON. Edit the template and rebuild with
`python3 scripts/generate_html.py`. Editing `index.html` directly is only
useful for a throwaway experiment, since the next rebuild overwrites it.

`data/cameras.json` and `index.html` are both committed so that a fresh
clone works without running anything.

`scripts/fetch_cameras.py` queries 16 SDOT endpoints (`WowsaUrl`,
`GetAllNeighborhoods`, `Data?zoomId=16&type=2`, and 13 neighborhood queries)
using `max_workers=4`, then probes Wowza `playlist.m3u8` endpoints for
`StreamActive` and `images.wsdot.wa.gov/nw/` snapshots for `ImageActive`
using `max_workers=8` to pre-populate initial offline and snapshot-fallback
state. It intentionally avoids bulk-probing `www.seattle.gov` thumbnails so
SDOT's origin server is never flooded. Avoid running it in a loop or during
routine UI tests.

## Conventions

Keep the page a single `index.html` with no bundler, npm, or separate CSS
and JS files. External dependencies load from jsDelivr with Subresource
Integrity hashes and `defer` initialization wired on `DOMContentLoaded`:

- `hls.js@1.7.4` (`hls.min.js`), which Chrome and Firefox need because they
  lack native HLS playback.
- `leaflet@1.9.4` (`leaflet.css` and `leaflet.js`) for the interactive map.

Anything added beyond those needs a reason written down in the commit. There
is no CI, and GitHub Actions or linting should only be added if asked for.

## Testing a change

There is no automated test suite committed in the repo. Rebuild the page,
open it with `open index.html`, and test search and filtering (including
corridor presets), Grid thumbnails, Map pins and hover previews, Wall live
tiles, and the modal player (`Prev`, `Next`, `Map`, `Fullscreen`, `PiP`,
`Esc`, and the direct stream or image link).

Check that live HLS video moves (`currentTime > 0`) rather than trusting
that the player opened. The Safari failure described below leaves native
controls sitting at 0:00, which looks like a player that is still loading.

`screencapture` followed by reading the PNG works for visual checks. Clicks
sent through AppleScript or System Events do not: synthetic clicks, including
raw `CGEventCreateMouseEvent` calls through JXA, register at the
accessibility focus level without firing the page's DOM click listeners in
Safari. To test click-driven behavior automatically, use Chrome CDP or a
browser automation extension inside the page.

When testing Grid thumbnails from headless Chrome against `file://`,
`www.seattle.gov` CloudFront rules block requests whose `User-Agent`
contains `HeadlessChrome` (`403` / `net::ERR_BLOCKED_BY_ORB`), so pass a
standard Chrome `--user-agent` flag in CDP launches. Also remember that a
couple of inactive cameras (such as `CMR-0006` and `CMR-0008`) currently
`302`-redirect to `http://www.seattle.gov/x9045.xml` (`text/html`), causing
their thumbnail `<img>` to fail with `ERR_BLOCKED_BY_ORB` and show the
placeholder even when the page is healthy.

The Chrome automation extension has two limitations of its own, both seen in
August 2026:

- Clicks at pixel coordinates taken from an earlier screenshot sometimes
  land in the wrong place, because the screenshot resolution changed between
  captures (1402x840, then 1120x672, in the same tab). Click by element
  reference from the find tool instead.
- Its Chrome returned a truthy `canPlayType` for
  `application/vnd.apple.mpegurl`, so the page took the native HLS branch,
  and playback then failed with `DEMUXER_ERROR_COULD_NOT_PARSE`. Confirm
  playback in a regular browser or standard Chrome CDP.

When you report that something works, say whether you saw it happen or are
inferring it, and give the command or check that showed it.

## Things that will break if you change them

Each of these came from a bug or empirical constraint discovered here.

Use `shouldUseNativeHls(video)` instead of checking
`video.canPlayType("application/vnd.apple.mpegurl")` directly in
`openModal()` and `attachWallHls()`. Safari supports Media Source Extensions
so `Hls.isSupported()` is true there as well, and routing Safari through
`hls.js` leaves video stuck at `0:00` with no frame. However, Chrome 157+
also returns `maybe` for `application/vnd.apple.mpegurl` while throwing
`PipelineStatus::DEMUXER_ERROR_COULD_NOT_PARSE` on SDOT streams under native
`<video>` playback, so non-WebKit browsers must stay on `hls.js` unless `Hls`
is unavailable.

Keep `muted` on both modal and Wall `<video>` elements and keep the
`video.play()` call immediately after `hls.attachMedia()`. Calling `play()`
only inside `MANIFEST_PARSED` can execute after user activation lapses,
causing browsers to block playback silently.

Keep `fetch_cameras.py` making HTTPS requests through `curl`. The
python.org installer's Python in `/Library/Frameworks/Python.framework`
ships without a populated CA bundle, so `urllib` and `requests` fail with
`CERTIFICATE_VERIFY_FAILED` against valid certificates, while `curl` uses
the system trust store.

SDOT's `web.seattle.gov/Travelers/api/*` endpoints omit
`Access-Control-Allow-Origin` headers, so browser `fetch()` from `file://`
fails with CORS errors. Data collection must happen at build time in
`fetch_cameras.py`.

Query both `GetCamerasByNeighborhood` (all 13 names from
`GetAllNeighborhoods`) and `api/Map/Data?zoomId=16&type=2`. The neighborhood
endpoints omit `Lat`/`Lng`, omit 5 `sdot` cameras (`CMR-0139`, `CMR-0143`,
`CMR-0275`, `CMR-0363`, `CMR-0421`), and omit regional `wsdot` highway
cameras, while `Map/Data` omits canonical neighborhood names. Several
`wsdot` entries omit `.jpg` in `ImageUrl`, so both `fetch_cameras.py` and
`generate_html.py` normalize extensionless filenames with `.jpg`.

Scope SDOT's `352x240` maintenance-graphic thumbnail check strictly to
`cam.Type === "sdot"`. Genuine WSDOT highway images often measure around
`335x209` to `352x240` and would falsely hide if checked unconditionally.

Keep thumbnail URLs cacheable on initial load and respect the separation
between `www.seattle.gov` images and Wowza streams. Never append
`?t=Date.now()` to initial grid image URLs: `www.seattle.gov` sits behind
CloudFront (`cache-control: public, max-age=300`), and unique query strings
bypass the CDN and overload SDOT's F5 BigIP origin with hundreds of
simultaneous origin requests. Initial load uses bare URLs (`thumbEpoch = 0`),
manual refresh uses a 60-second bucket for `sdot` (`freshStillEpoch`), and
failed grid images retry at most once after `3500ms`.

Keep HLS stream fallback layered ahead of offline state. Many SDOT cameras
return `404` on Wowza while still serving fresh JPEGs, and some working
streams redirect their JPEG to `x9045.xml` or serve a `352x240` maintenance
card. When an `sdot` stream returns `404`, exhausts `NETWORK_ERROR` retries
(staggered at `1000 * hlsRetries` ms), or hits the 12-second startup timeout,
fall back automatically to `STILL · 15S` snapshot playback (`startModalStill`
or `attachWallStill`) before marking the camera offline. Mark an active-stream
camera offline only after both video and snapshot fail, and mark snapshot-only
(`StreamActive === false`) or `wsdot` cameras offline immediately if their
image fails to load.

Keep Wall view capped at 4 or 6 live tiles and tear down Wall streams while
`#modal` is open (also delay Wall resumption until Picture-in-Picture exits).
Always call `hls.destroy()` or `tileHls.destroy()` before resetting `<video>`
(`pause()`, `removeAttribute`, `load()`) so `hls.js` media source cleanup
cannot fire spurious error events. The shared Wowza host (`streamlock.net`)
speaks HTTP/1.1, where browsers enforce a 6-connection-per-origin limit;
opening extra streams saturates the socket pool and stalls modal playback.
Note that Wowza's Sectigo TLS certificate rotates periodically (current cert
expires January 2027), and `WowsaUrl` returns the active streaming hostname at
fetch time.

Map view uses Esri `World_Street_Map` raster tiles in `{z}/{y}/{x}`
order (row `y` before column `x`) with a CSS inversion filter for dark mode.
Two common alternatives fail from `file://`: `basemaps.cartocdn.com` returns
`API KEY REQUIRED` placeholder PNGs, and `tile.openstreetmap.org` rejects
requests missing an HTTP `Referer` header. Do not swap `{y}/{x}` to
`{x}/{y}` on the ArcGIS MapServer URL.

Escape dynamic values with `escHtml()` (or set `.textContent`) anywhere
HTML strings are built, including filter chips (`q=` URL parameter) and
Leaflet marker tooltips. Also keep `?cam=` deep linking independent of active
filters so shared camera URLs always open even when `localStorage` filters
exclude that camera, and detach PiP shutdown from closing the modal.

Never trigger `applyFilters()` or re-assign existing `<img>` `src` URLs
needlessly on every keystroke (`renderGrid()` preserves existing card DOM
nodes via `cardElById` unless `thumbEpoch` increments).

A camera whose stream returns an error and one whose server has hung look
the same in the page. From the shell they differ: an error from Wowza comes
back quickly from `curl -s -o /dev/null -w '%{http_code}'`, while a hang
times out. Retry before concluding a camera is offline.

## Decisions already made

Please ask before revisiting these.

The native `<video controls>` bar stays in `#modal-video`. Moving the pointer
over a playing video still draws the browser's translucent overlay behind
the controls until they hide. Both Safari and Chrome draw it so their controls
stay readable over any video, and neither lets a page restyle it. Removing
it would mean replacing native controls with custom play, pause, and mute
buttons, and in August 2026 DeWitt decided the overlay was acceptable.

## Writing style

Documentation and commit messages should read like a person wrote them.
Avoid these habits:

- Defining things by contrast, such as saying something is a gap or feature
  rather than a bug.
- Sentence fragments standing in for emphasis.
- Short portentous declarations used as topic sentences or headings.
- Em-dashes used for dramatic effect rather than to join clauses.
- Starting a paragraph or list item with a bolded slogan.

Explain the thing directly. Saying that thumbnails come from
`www.seattle.gov` and video from the Wowza host, so one can fail while the
other works, is clearer than a slogan. Direct imperatives are fine in this
file where they are instructions, followed by a plain reason.

### Technical documentation

`README.md` is reference material.

- Do not open with rhetorical questions, imaginary user scenarios, or a
  problem framing. State what the tool is, what it reads, and what it
  produces in the first paragraph.
- Organize sections by subsystem, such as the page, the data sources, and
  the build scripts.
- Document keys, URL parameters, and options in tables or lists instead of
  narrating them.
- State how things connect without defending why they were built that way.
- Use quotation marks only for verbatim quotes and exact UI labels in
  step-by-step instructions, never for emphasis or terminology.
- Wrap Markdown prose, lists, and tables at 78 columns, except for URLs and
  code that cannot be broken.

### Commit messages

- Do not prefix the subject with type words such as `feat:` or `fix:`.
- State what changed in the subject line. Use the body for the reason, any
  context that is not obvious from the diff, and what you measured or
  observed.
- End with the co-author trailer for the agent that made the change.
