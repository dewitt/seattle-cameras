#!/usr/bin/env python3
"""
Fetch the full Seattle traffic camera list from SDOT's Travelers API and
write it to data/cameras.json.

Uses `curl` as a subprocess rather than urllib/requests: the system Python
on macOS (python.org installer) ships without a populated CA bundle, so
urllib's SSL verification fails with CERTIFICATE_VERIFY_FAILED even though
the actual cert chain is fine (verified independently via curl, which uses
the system trust store). Shelling out to curl sidesteps that entirely.

The API has no single "list everything" endpoint — cameras are only
enumerable per-neighborhood, so this queries all 13 SDOT neighborhoods and
dedupes by camera Id (a handful of cameras near neighborhood boundaries are
returned by more than one query).
"""
import json
import subprocess
import sys
import urllib.parse

NEIGHBORHOODS = [
    "Ballard", "Central", "Delridge", "Downtown", "East", "Greater Duwamish",
    "Lake Union", "Magnolia/Queen Anne", "North", "Northeast", "Northwest",
    "Southeast", "Southwest",
]

BASE = "https://web.seattle.gov/Travelers/api/Map/GetCamerasByNeighborhood"


def fetch_neighborhood(name: str) -> list[dict]:
    url = BASE + "?" + urllib.parse.urlencode({"neighborhood": name})
    raw = subprocess.run(
        ["curl", "-s", "--max-time", "15", url],
        capture_output=True, text=True, check=True,
    ).stdout
    # The API double-encodes: the HTTP body is a JSON string containing JSON.
    data = json.loads(raw)
    return json.loads(data) if isinstance(data, str) else data


def main() -> None:
    all_cams: dict[str, dict] = {}
    for name in NEIGHBORHOODS:
        print(f"fetching {name}...", file=sys.stderr)
        for cam in fetch_neighborhood(name):
            cam["Neighborhood"] = name
            all_cams[cam["Id"]] = cam  # dedupe by Id

    cams = list(all_cams.values())
    cams.sort(key=lambda c: (c["Neighborhood"], c["Description"]))

    by_type: dict[str, int] = {}
    for c in cams:
        by_type[c["Type"]] = by_type.get(c["Type"], 0) + 1
    print(f"{len(cams)} unique cameras — {by_type}", file=sys.stderr)

    out_path = "data/cameras.json"
    with open(out_path, "w") as f:
        json.dump(cams, f, indent=2)
    print(f"wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
