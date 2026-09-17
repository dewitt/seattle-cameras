# Agent Instructions — seattle-cameras

This file is read by AI coding agents (Claude Code, etc.) at the start of a
session in this directory. `CLAUDE.md` is a symlink to this file.

## What this project is

A single-file, dependency-free HTML tool (`index.html`) that shows every
live Seattle SDOT traffic camera as a searchable grid with a fullscreen live
HLS video viewer. No server, no framework, no build tool beyond two small
Python scripts that fetch data and bake it into the page. Read `README.md`
for the full architecture (how the camera list API and the Wowza streaming
server work, URL templates, etc.) — that's the primary reference, not
duplicated here.

This is a personal-use tool, not a product. Optimize for "keeps working and
stays simple" over "handles every edge case."

## Source of truth: `index.html` is generated

`index.html` is built by `scripts/generate_html.py`, which reads
`data/cameras.json` and inlines an HTML template string with the camera
data embedded as JSON. **Don't hand-edit `index.html` for anything but a
quick local experiment** — the real source is the template string inside
`generate_html.py`. Edit there, then:

```sh
python3 scripts/generate_html.py
```

Both `data/cameras.json` and `index.html` are committed to git (not
gitignored) so a fresh clone is immediately usable without running
anything. Re-run `scripts/fetch_cameras.py` only when you actually want to
refresh the camera list from SDOT (new/removed/renamed cameras) — it's a
live network call to a city government API, not something to run
speculatively or in a loop.

## How to test a change

There's no test suite — this is a static HTML/JS page. To verify a change:

```sh
open index.html
```

Then manually exercise the golden path: search/filter, click a thumbnail,
confirm the fullscreen player actually shows moving video (not just a
native `<video controls>` widget stuck at 0:00 — see the Safari gotcha
below, that exact failure mode is easy to reintroduce), test Prev/Next,
Fullscreen, Escape-to-close, and the "Open direct .m3u8" link.

If you're working from a Claude Code session with screen recording /
Accessibility permissions available, `screencapture` + reading the
resulting PNG is a reliable way to verify visually. Driving actual clicks
into the page via AppleScript/System Events on macOS is *not* reliable —
synthetic clicks (including raw `CGEventCreateMouseEvent` via JXA) were
found to register at the accessibility-focus level without firing the
page's real DOM `click` listeners in Safari. If you need to confirm
click-driven behavior programmatically rather than asking the user to
click, prefer a browser automation extension with real page-content access
(e.g. Chrome + an automation extension) over blind AppleScript coordinate
clicks.

## Known gotchas (hard-won, don't rediscover these)

1. **Safari + hls.js ordering bug.** Safari reports MediaSource Extensions
   support, so `Hls.isSupported()` returns `true` there too — naively
   checking that first routes Safari through hls.js, whose MSE path
   doesn't play nicely with WebKit and leaves the `<video>` stuck at 0:00
   with a tiny native-controls widget and no frame. Fix: always check
   `video.canPlayType("application/vnd.apple.mpegurl")` **first** and use
   `video.src = url` directly when true; only fall back to `Hls.isSupported()`
   for browsers without native HLS (Chrome, Firefox). This is already
   correct in the current template — preserve the ordering if you touch
   `openModal()`.

2. **System Python's SSL cert bundle is empty on this Mac.** The
   python.org-installer Python (`/Library/Frameworks/Python.framework`)
   ships without a populated CA bundle, so `urllib`/`requests` HTTPS calls
   fail with `CERTIFICATE_VERIFY_FAILED` even against perfectly valid
   certs. `curl` uses the system trust store and works fine. That's why
   `fetch_cameras.py` shells out to `curl` via `subprocess` instead of
   using `urllib.request` directly — keep doing that for any new network
   code here, or run `Install Certificates.command` first if you really
   want to use `urllib`/`requests`.

3. **The SDOT camera-list API has no "list everything" endpoint.** Cameras
   are only enumerable per-neighborhood (13 fixed names, from
   `api/Map/GetAllNeighborhoods`). `fetch_cameras.py` queries all 13 and
   dedupes by `Id` since boundary cameras appear in more than one.

4. **All `sdot` cameras share one Wowza host.** Don't be tempted to look up
   a per-camera stream host — `api/Map/WowsaUrl` returns one template
   (`https://61e0c5d388c2e.streamlock.net:443/live/{stream}/playlist.m3u8`)
   used for every camera; only `{stream}` (== `ImageUrl` with `.jpg` →
   `.stream`) varies.

5. **`wsdot`-type cameras have no live video**, only static refreshing
   JPEGs (confirmed via SDOT's own `camera.video.js` — the Video button is
   only wired for `Type === "sdot"`). They're fetched and stored in
   `data/cameras.json` for completeness but filtered out in
   `generate_html.py`. If someone asks for state-highway cameras too,
   that's a real gap, not a bug — see README's "Known limitations."

6. **A camera reachable-but-erroring vs. genuinely hung look identical from
   the UI**, but are diagnosable from the shell: a real 404/error from the
   Wowza server (`curl -s -o /dev/null -w '%{http_code}'`) returns fast; a
   server-side hang (has happened — the whole Wowza box went briefly
   unresponsive at the TLS layer during initial development) times out on
   `curl` even for cameras that work fine moments later. Don't assume a
   single failed request means a camera is permanently offline — retry
   before concluding that.

## Conventions

- Keep it a single `index.html` — no bundlers, no npm, no separate CSS/JS
  files. The one external dependency (`hls.js`, loaded from jsdelivr CDN)
  is deliberate and fine; anything beyond that should have a clear reason.
- `flake.nix` + `.envrc` (`use flake`) provide the dev shell (`python3`,
  `curl`). Add any new tooling there rather than assuming it's installed
  globally. Nix flakes only see git-tracked files, so `git add` a new file
  before `nix develop` will notice it.
- No CI. This is a personal tool in a private repo; don't add GitHub
  Actions, linting, etc. unless explicitly asked.
- Commit `data/cameras.json` and `index.html` as real build outputs, not
  gitignored artifacts — the whole point is that a fresh clone works with
  zero setup.
