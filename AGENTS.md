# Working in this repo

seattle-cameras is a personal tool that builds one self-contained
`index.html` showing every live SDOT traffic camera in Seattle as a
searchable grid, with a player for each camera's live HLS stream. There is no
server and no framework. Two Python scripts fetch the camera list and embed
it in the page. `CLAUDE.md` is a symlink to this file.

`README.md` describes the page's features, the SDOT APIs, and the Wowza
stream URLs, and is the reference for those. This file covers how to change
the code without breaking it.

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
camera data as JSON. Edit the template and rebuild with
`python3 scripts/generate_html.py`. Editing `index.html` directly is only
useful for a throwaway experiment, since the next rebuild overwrites it.

`data/cameras.json` and `index.html` are both committed so that a fresh
clone works without running anything.

`scripts/fetch_cameras.py` makes 13 requests to a city government API.
Run it when you want SDOT's current camera list, and not as part of
routine testing or in a loop.

## Conventions

Keep the page a single `index.html` with no bundler, npm, or separate CSS
and JS files. The one external dependency is `hls.js` from jsDelivr, which
Chrome and Firefox need because they lack native HLS playback. Anything
added beyond that needs a reason written down in the commit.

There is no CI, and GitHub Actions or linting should only be added if asked
for.

## Testing a change

There is no test suite. Rebuild the page, open it with `open index.html`,
and go through search and filtering, open a camera, check the video is
actually moving, then try previous and next, fullscreen, Escape to close,
and the direct `.m3u8` link.

Check that the video moves rather than trusting that the player opened.
The Safari failure described below leaves a native controls widget sitting
at 0:00, which looks like a player that is still loading.

`screencapture` followed by reading the PNG works for visual checks. Clicks
sent through AppleScript or System Events do not: synthetic clicks,
including raw `CGEventCreateMouseEvent` calls through JXA, registered at
the accessibility focus level without firing the page's DOM `click`
listeners in Safari. To test click-driven behavior without asking DeWitt,
use a browser automation extension that works inside the page.

The Chrome automation extension has two limitations of its own, both seen
in August 2026:

- Clicks at pixel coordinates taken from an earlier screenshot sometimes
  land in the wrong place, because the screenshot resolution changed
  between captures (1402x840, then 1120x672, in the same tab). Click by
  element reference from the find tool instead.
- Its Chrome returned a truthy `canPlayType` for
  `application/vnd.apple.mpegurl`, so the page took the native HLS branch,
  and playback then failed with `DEMUXER_ERROR_COULD_NOT_PARSE`. Video
  playback results from that browser say nothing about a normal Chrome or
  Safari, so confirm playback in a regular browser.

When you report that something works, say whether you saw it happen or are
inferring it, and give the command or check that showed it.

## Things that will break if you change them

Each of these came from a bug that took a while to track down.

Check `video.canPlayType("application/vnd.apple.mpegurl")` before
`Hls.isSupported()` in `openModal()`. Safari supports Media Source
Extensions, so `Hls.isSupported()` is true there as well, and routing Safari
through hls.js leaves the video stuck at 0:00 with no frame. When
`canPlayType` is truthy the page sets `video.src` directly, and hls.js is
used only in browsers without native HLS.

Keep `muted` on the `<video>` element and keep the `video.play()` call that
runs immediately after `hls.attachMedia()`. The hls.js branch used to call
`play()` only from the `MANIFEST_PARSED` callback, which can run after the
click's user activation has lapsed, and Chrome then blocks unmuted autoplay
without an error. The paused video showed Chrome's large play button and a
dark overlay whenever the pointer moved over it.

Keep `fetch_cameras.py` making HTTPS requests through `curl`. The
python.org installer's Python in `/Library/Frameworks/Python.framework`
ships without a populated CA bundle, so `urllib` and `requests` fail with
`CERTIFICATE_VERIFY_FAILED` against valid certificates, while `curl` uses
the system trust store. Use `curl` for any new network code too, or run
`Install Certificates.command` before switching to `urllib`.

The camera list API has no endpoint that returns everything. Cameras are
listed per neighborhood, for the 13 names returned by
`api/Map/GetAllNeighborhoods`, so `fetch_cameras.py` queries all 13 and
dedupes by `Id` because cameras on a boundary appear in more than one.

Every `sdot` camera streams from the same Wowza host. `api/Map/WowsaUrl`
returns a single template, and only `{stream}` changes, being `ImageUrl`
with `.jpg` replaced by `.stream`. There is no per-camera host to look up.

Cameras of type `wsdot` have no live video. SDOT's `camera.video.js` wires
its video button only when `Type === "sdot"`, and `wsdot` cameras are served
as still images. They are stored in `data/cameras.json` and filtered out in
`generate_html.py`. Adding them would be new work, and the README lists it
as a known gap.

Keep thumbnail failures out of the offline status. Thumbnails come from
`www.seattle.gov` and video from the Wowza host, and one can fail while the
other works. A camera is marked offline only when its stream fails to start
within the 12 second watchdog.

A camera whose stream returns an error and one whose server has hung look
the same in the page. From the shell they differ: an error from Wowza comes
back quickly from `curl -s -o /dev/null -w '%{http_code}'`, while a hang
times out. During initial development the whole Wowza server stopped
answering at the TLS layer for a while, and cameras that timed out worked a
few minutes later. Retry before concluding a camera is offline.

## Decisions already made

Please ask before revisiting these.

The native `<video controls>` bar stays. Moving the pointer over a playing
video still draws the browser's translucent overlay behind the controls
until they hide. Both Safari and Chrome draw it so their controls stay
readable over any video, and neither lets a page restyle it. Removing it
would mean replacing the native controls with custom play, pause, and mute
buttons, and in August 2026 DeWitt decided that the overlay was not
bothersome enough to justify that.

## Writing style

Documentation and commit messages should read like a person wrote them. A
few habits to avoid:

- Defining things by contrast, such as saying something is a gap, not a
  bug.
- Sentence fragments standing in for emphasis.
- Short portentous declarations used as topic sentences or headings.
- Em-dashes used for dramatic effect rather than to join clauses.
- Starting a paragraph or list item with a bolded slogan.

Explain the thing instead. Saying that thumbnails come from
`www.seattle.gov` and video from the Wowza host, so one can fail while the
other works, is better than a slogan like a broken thumbnail is not a dead
camera. Direct imperatives are fine in this file where they are genuinely
instructions, but follow them with a plain reason.

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
