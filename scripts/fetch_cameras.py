#!/usr/bin/env python3
"""
Fetch Seattle and regional traffic camera data from SDOT's Travelers API and
write it to data/cameras.json.

Uses `curl` as a subprocess rather than urllib/requests so HTTPS always uses the
system trust store across macOS Python builds and Nix shells.

Combines four SDOT endpoints:
- api/Map/WowsaUrl for the live Wowza HLS playlist template
- api/Map/GetAllNeighborhoods for the canonical Seattle neighborhood list
- api/Map/GetCamerasByNeighborhood?neighborhood=... for neighborhood labels
- api/Map/Data?zoomId=16&type=2 for all SDOT + WSDOT cameras and coordinates
"""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import json
import math
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

FALLBACK_NEIGHBORHOODS = [
    "Ballard",
    "Central",
    "Delridge",
    "Downtown",
    "East",
    "Greater Duwamish",
    "Lake Union",
    "Magnolia/Queen Anne",
    "North",
    "Northeast",
    "Northwest",
    "Southeast",
    "Southwest",
]
FALLBACK_WOWZA_TEMPLATE = (
    "https://61e0c5d388c2e.streamlock.net:443/live/{stream}/playlist.m3u8"
)
SDOT_IMAGE_BASE = "https://www.seattle.gov/trafficcams/images/"
WSDOT_IMAGE_BASE = "https://images.wsdot.wa.gov/nw/"
API_ROOT = "https://web.seattle.gov/Travelers/api/Map/"
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif")
COS_SEATTLE_LAT = math.cos(math.radians(47.6))


def curl_json(url: str) -> object:
    """Fetch a JSON endpoint via curl, unwrapping SDOT's double-encoded strings."""
    raw = subprocess.run(
        ["curl", "-fsS", "--max-time", "15", url],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    data = json.loads(raw)
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data
    return data


def fetch_wowza_template() -> str:
    """Fetch the Wowza stream template, falling back if malformed."""
    try:
        tpl = curl_json(API_ROOT + "WowsaUrl")
        if isinstance(tpl, str) and tpl.startswith("https://") and "{stream}" in tpl:
            return tpl
    except (subprocess.SubprocessError, ValueError) as exc:
        print(f"warning: WowsaUrl fetch failed ({exc}); using fallback", file=sys.stderr)
    return FALLBACK_WOWZA_TEMPLATE


def fetch_neighborhood_names() -> list[str]:
    """Fetch the list of SDOT neighborhoods, falling back to the fixed 13."""
    try:
        items = curl_json(API_ROOT + "GetAllNeighborhoods")
        if isinstance(items, list):
            names = sorted(
                item["DisplayName"]
                for item in items
                if isinstance(item, dict) and item.get("DisplayName")
            )
            if names:
                return names
    except (subprocess.SubprocessError, ValueError) as exc:
        print(
            f"warning: GetAllNeighborhoods failed ({exc}); using fallback",
            file=sys.stderr,
        )
    return list(FALLBACK_NEIGHBORHOODS)


def fetch_neighborhood(name: str) -> list[dict]:
    """Fetch the camera list for one Seattle neighborhood."""
    url = (
        API_ROOT
        + "GetCamerasByNeighborhood?"
        + urllib.parse.urlencode({"neighborhood": name})
    )
    data = curl_json(url)
    return data if isinstance(data, list) else []


def normalize_image_url(url: str | None) -> str:
    """Normalize ImageUrl and append .jpg when SDOT omits the file extension."""
    cleaned = (url or "").strip()
    if cleaned and not cleaned.lower().endswith(IMAGE_EXTS):
        cleaned += ".jpg"
    return cleaned


def nearest_neighborhood(
    lat: float,
    lng: float,
    reference_cams: list[dict],
) -> str:
    """Return the neighborhood of the closest camera with known coordinates."""
    nearest = min(
        reference_cams,
        key=lambda c: (c["Lat"] - lat) ** 2
        + ((c["Lng"] - lng) * COS_SEATTLE_LAT) ** 2,
    )
    return nearest["Neighborhood"]


def probe_sdot_stream(wowza_template: str, image_url: str) -> bool:
    """Return False only when Wowza explicitly returns 404 for an SDOT stream."""
    if not image_url:
        return True
    stream_name = re.sub(r"\.jpe?g$", ".stream", image_url, flags=re.I)
    url = wowza_template.replace("{stream}", urllib.parse.quote(stream_name))
    try:
        res = subprocess.run(
            ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "6", url],
            capture_output=True,
            text=True,
        )
        return res.stdout.strip() != "404"
    except subprocess.SubprocessError:
        return True


def probe_wsdot_image(wsdot_base: str, image_url: str) -> bool:
    """Return False only when WSDOT explicitly returns 404 for a snapshot."""
    if not image_url:
        return True
    url = wsdot_base + urllib.parse.quote(image_url, safe="/")
    try:
        res = subprocess.run(
            ["curl", "-sSI", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "6", url],
            capture_output=True,
            text=True,
        )
        return res.stdout.strip() != "404"
    except subprocess.SubprocessError:
        return True


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    out_path = repo_root / "data" / "cameras.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("fetching WowsaUrl and neighborhood list...", file=sys.stderr)
    wowza_template = fetch_wowza_template()
    neighborhoods = fetch_neighborhood_names()

    print(
        f"fetching {len(neighborhoods)} neighborhoods + Map/Data...",
        file=sys.stderr,
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        map_future = pool.submit(curl_json, API_ROOT + "Data?zoomId=16&type=2")
        hood_futures = {
            name: pool.submit(fetch_neighborhood, name) for name in neighborhoods
        }

    hood_cams: dict[str, dict] = {}
    for name in sorted(neighborhoods):
        for cam in hood_futures[name].result():
            cid = cam.get("Id")
            if cid:
                entry = dict(cam)
                entry["Neighborhood"] = name
                hood_cams[cid] = entry

    map_data = map_future.result()
    features = map_data.get("Features", []) if isinstance(map_data, dict) else []

    map_cams: dict[str, dict] = {}
    for feature in features:
        coord = feature.get("PointCoordinate")
        has_coord = (
            isinstance(coord, list)
            and len(coord) >= 2
            and isinstance(coord[0], (int, float))
            and isinstance(coord[1], (int, float))
        )
        lat = round(float(coord[0]), 6) if has_coord else None
        lng = round(float(coord[1]), 6) if has_coord else None
        for cam in feature.get("Cameras", []):
            cid = cam.get("Id")
            if cid:
                entry = dict(cam)
                entry["Lat"] = lat
                entry["Lng"] = lng
                map_cams[cid] = entry

    merged: dict[str, dict] = {}
    for cid in set(hood_cams) | set(map_cams):
        base = dict(hood_cams.get(cid, {}))
        if cid in map_cams:
            base.update(map_cams[cid])
        base["Id"] = cid
        base["Description"] = (base.get("Description") or "").strip()
        base["ImageUrl"] = normalize_image_url(base.get("ImageUrl"))
        base["Type"] = (base.get("Type") or "").strip().lower()
        base.setdefault("Lat", None)
        base.setdefault("Lng", None)
        if cid in hood_cams:
            base["Neighborhood"] = hood_cams[cid]["Neighborhood"]
        else:
            base["Neighborhood"] = None
        merged[cid] = base

    coord_refs = [
        c
        for c in merged.values()
        if c["Neighborhood"] and c["Lat"] is not None and c["Lng"] is not None
    ]
    for cam in merged.values():
        if cam["Neighborhood"]:
            continue
        if cam["Type"] == "sdot" and cam["Lat"] is not None and coord_refs:
            cam["Neighborhood"] = nearest_neighborhood(
                cam["Lat"], cam["Lng"], coord_refs
            )
        else:
            cam["Neighborhood"] = "Regional Highways"

    cams = sorted(
        merged.values(),
        key=lambda c: (
            c["Neighborhood"] == "Regional Highways",
            c["Neighborhood"],
            c["Description"],
            c["Id"],
        ),
    )

    if len(cams) < 100:
        sys.exit(
            f"error: expected >= 100 cameras from SDOT APIs, got {len(cams)}; "
            "leaving data/cameras.json unchanged"
        )

    by_type: dict[str, int] = {}
    for c in cams:
        by_type[c["Type"]] = by_type.get(c["Type"], 0) + 1
    print(f"{len(cams)} unique cameras — {by_type}", file=sys.stderr)

    print("probing SDOT HLS playlists and WSDOT snapshots...", file=sys.stderr)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        sdot_futs = {
            c["Id"]: pool.submit(probe_sdot_stream, wowza_template, c["ImageUrl"])
            for c in cams
            if c["Type"] == "sdot"
        }
        wsdot_futs = {
            c["Id"]: pool.submit(probe_wsdot_image, WSDOT_IMAGE_BASE, c["ImageUrl"])
            for c in cams
            if c["Type"] == "wsdot"
        }

    sdot_active = 0
    sdot_404 = 0
    wsdot_active = 0
    wsdot_404 = 0
    for c in cams:
        if c["Type"] == "sdot":
            ok = sdot_futs[c["Id"]].result()
            c["StreamActive"] = ok
            c["ImageActive"] = True
            if ok:
                sdot_active += 1
            else:
                sdot_404 += 1
        elif c["Type"] == "wsdot":
            ok = wsdot_futs[c["Id"]].result()
            c["StreamActive"] = False
            c["ImageActive"] = ok
            if ok:
                wsdot_active += 1
            else:
                wsdot_404 += 1
        else:
            c["StreamActive"] = False
            c["ImageActive"] = True
    print(
        f"health: sdot streams {sdot_active} active / {sdot_404} 404; "
        f"wsdot images {wsdot_active} active / {wsdot_404} 404",
        file=sys.stderr,
    )

    payload = {
        "generatedAt": dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "wowzaTemplate": wowza_template,
        "sdotImageBase": SDOT_IMAGE_BASE,
        "wsdotImageBase": WSDOT_IMAGE_BASE,
        "cameras": cams,
    }

    tmp_path = out_path.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    os.replace(tmp_path, out_path)
    print(f"wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
