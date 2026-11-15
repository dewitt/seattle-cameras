#!/usr/bin/env python3
"""
Generate index.html from data/cameras.json.

Embeds both SDOT live HLS video cameras and WSDOT refreshing highway still
cameras, along with coordinates and the SDOT Wowza stream template.

Run scripts/fetch_cameras.py first to refresh data/cameras.json.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

FALLBACK_WOWZA = "https://61e0c5d388c2e.streamlock.net:443/live/{stream}/playlist.m3u8"
FALLBACK_SDOT_BASE = "https://www.seattle.gov/trafficcams/images/"
FALLBACK_WSDOT_BASE = "https://images.wsdot.wa.gov/nw/"


def load_camera_payload(path: Path) -> tuple[dict, list[dict]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        config = {
            "generatedAt": "",
            "wowzaTemplate": FALLBACK_WOWZA,
            "sdotImageBase": FALLBACK_SDOT_BASE,
            "wsdotImageBase": FALLBACK_WSDOT_BASE,
        }
        cams = raw
    else:
        config = {
            "generatedAt": raw.get("generatedAt", ""),
            "wowzaTemplate": raw.get("wowzaTemplate") or FALLBACK_WOWZA,
            "sdotImageBase": raw.get("sdotImageBase") or FALLBACK_SDOT_BASE,
            "wsdotImageBase": raw.get("wsdotImageBase") or FALLBACK_WSDOT_BASE,
        }
        cams = raw.get("cameras", [])
    return config, cams


def prepare_cameras(raw_cams: list[dict]) -> list[dict]:
    prepared: list[dict] = []
    for item in raw_cams:
        cam = dict(item)
        cam_type = (cam.get("Type") or "").strip().lower()
        cam["Type"] = cam_type
        image_url = (cam.get("ImageUrl") or "").strip()
        if image_url and not re.search(r"\.(?:jpe?g|png|gif)$", image_url, re.I):
            image_url += ".jpg"
        cam["ImageUrl"] = image_url
        if cam_type == "sdot" and image_url:
            cam["StreamName"] = re.sub(r"\.jpe?g$", ".stream", image_url, flags=re.I)
        prepared.append(cam)

    prepared.sort(
        key=lambda c: (
            c.get("Neighborhood") == "Regional Highways",
            c.get("Neighborhood", ""),
            c.get("Description", ""),
            c.get("Id", ""),
        )
    )
    return prepared


def safe_json(obj: object) -> str:
    return json.dumps(obj, separators=(",", ":")).replace("</", "<\\/")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Seattle Traffic Cameras — Live Stream Monitor</title>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="Single-page Seattle SDOT live traffic camera and WSDOT highway camera viewer with Grid, Interactive Map, and Multi-Cam Wall modes.">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css" integrity="sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H" crossorigin="anonymous">
<script defer src="https://cdn.jsdelivr.net/npm/hls.js@1.7.4/dist/hls.min.js" integrity="sha384-p9vgU/7IYJWd3I4STrtqxqR/2cAQlhIX7D/HrTnIMEjjcUox165b7se7sxmm3zDg" crossorigin="anonymous"></script>
<script defer src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js" integrity="sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH" crossorigin="anonymous"></script>
<style>
  :root {
    color-scheme: dark;
    --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    --font-mono: ui-monospace, "SF Mono", "Cascadia Code", Menlo, Monaco, Consolas, monospace;

    --bg-page: #080b11;
    --bg-surface: #0f141d;
    --bg-surface-elevated: #151b27;
    --bg-surface-hover: #1c2433;
    --bg-input: #121824;
    --bg-thumb: #05080e;

    --border-subtle: rgba(255, 255, 255, 0.07);
    --border-default: rgba(255, 255, 255, 0.12);
    --border-strong: rgba(255, 255, 255, 0.22);
    --border-focus: #38bdf8;

    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --text-tertiary: #64748b;

    --accent: #38bdf8;
    --accent-hover: #0ea5e9;
    --accent-subtle: rgba(56, 189, 248, 0.12);
    --accent-border: rgba(56, 189, 248, 0.32);

    --live: #10b981;
    --live-subtle: rgba(16, 185, 129, 0.14);
    --live-border: rgba(16, 185, 129, 0.35);

    --still: #38bdf8;
    --still-subtle: rgba(56, 189, 248, 0.14);
    --still-border: rgba(56, 189, 248, 0.35);

    --offline: #f43f5e;
    --offline-subtle: rgba(244, 63, 94, 0.14);
    --offline-border: rgba(244, 63, 94, 0.35);

    --favorite: #fbbf24;
    --favorite-subtle: rgba(251, 191, 36, 0.14);
    --favorite-border: rgba(251, 191, 36, 0.35);

    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.35);
    --shadow-md: 0 4px 14px rgba(0, 0, 0, 0.45);
    --shadow-lg: 0 16px 36px rgba(0, 0, 0, 0.6);
    --shadow-focus: 0 0 0 3px rgba(56, 189, 248, 0.22);

    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;
    --radius-full: 9999px;

    --grid-min: 240px;
    --header-bg: rgba(15, 20, 29, 0.88);
    --header-h: 64px;
  }

  [data-theme="light"] {
    color-scheme: light;
    --bg-page: #f8fafc;
    --bg-surface: #ffffff;
    --bg-surface-elevated: #f1f5f9;
    --bg-surface-hover: #e2e8f0;
    --bg-input: #ffffff;
    --bg-thumb: #e2e8f0;

    --border-subtle: rgba(0, 0, 0, 0.06);
    --border-default: rgba(0, 0, 0, 0.12);
    --border-strong: rgba(0, 0, 0, 0.22);
    --border-focus: #0284c7;

    --text-primary: #0f172a;
    --text-secondary: #475569;
    --text-tertiary: #64748b;

    --accent: #0284c7;
    --accent-hover: #0369a1;
    --accent-subtle: rgba(2, 132, 199, 0.1);
    --accent-border: rgba(2, 132, 199, 0.28);

    --live: #059669;
    --live-subtle: rgba(5, 150, 105, 0.1);
    --live-border: rgba(5, 150, 105, 0.28);

    --still: #0284c7;
    --still-subtle: rgba(2, 132, 199, 0.1);
    --still-border: rgba(2, 132, 199, 0.28);

    --offline: #e11d48;
    --offline-subtle: rgba(225, 29, 72, 0.1);
    --offline-border: rgba(225, 29, 72, 0.28);

    --favorite: #d97706;
    --favorite-subtle: rgba(217, 119, 6, 0.1);
    --favorite-border: rgba(217, 119, 6, 0.28);

    --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.06);
    --shadow-md: 0 4px 14px rgba(0, 0, 0, 0.08);
    --shadow-lg: 0 16px 36px rgba(0, 0, 0, 0.12);
    --shadow-focus: 0 0 0 3px rgba(2, 132, 199, 0.18);

    --header-bg: rgba(255, 255, 255, 0.92);
  }

  @media (prefers-color-scheme: light) {
    :root:not([data-theme="dark"]) {
      color-scheme: light;
      --bg-page: #f8fafc;
      --bg-surface: #ffffff;
      --bg-surface-elevated: #f1f5f9;
      --bg-surface-hover: #e2e8f0;
      --bg-input: #ffffff;
      --bg-thumb: #e2e8f0;

      --border-subtle: rgba(0, 0, 0, 0.06);
      --border-default: rgba(0, 0, 0, 0.12);
      --border-strong: rgba(0, 0, 0, 0.22);
      --border-focus: #0284c7;

      --text-primary: #0f172a;
      --text-secondary: #475569;
      --text-tertiary: #64748b;

      --accent: #0284c7;
      --accent-hover: #0369a1;
      --accent-subtle: rgba(2, 132, 199, 0.1);
      --accent-border: rgba(2, 132, 199, 0.28);

      --live: #059669;
      --live-subtle: rgba(5, 150, 105, 0.1);
      --live-border: rgba(5, 150, 105, 0.28);

      --still: #0284c7;
      --still-subtle: rgba(2, 132, 199, 0.1);
      --still-border: rgba(2, 132, 199, 0.28);

      --offline: #e11d48;
      --offline-subtle: rgba(225, 29, 72, 0.1);
      --offline-border: rgba(225, 29, 72, 0.28);

      --favorite: #d97706;
      --favorite-subtle: rgba(217, 119, 6, 0.1);
      --favorite-border: rgba(217, 119, 6, 0.28);

      --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.06);
      --shadow-md: 0 4px 14px rgba(0, 0, 0, 0.08);
      --shadow-lg: 0 16px 36px rgba(0, 0, 0, 0.12);
      --shadow-focus: 0 0 0 3px rgba(2, 132, 199, 0.18);

      --header-bg: rgba(255, 255, 255, 0.92);
    }
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg-page);
    color: var(--text-primary);
    font-family: var(--font-sans);
    min-height: 100vh;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  header {
    position: sticky;
    top: 0;
    z-index: 600;
    background: var(--header-bg);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border-subtle);
    padding: 10px 16px;
    transition: background-color 0.2s;
  }

  .nav-container {
    max-width: 1560px;
    margin: 0 auto;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    justify-content: space-between;
  }

  .brand-group {
    display: flex;
    align-items: center;
    gap: 8px;
    user-select: none;
  }

  .brand-icon {
    width: 24px;
    height: 24px;
    color: var(--accent);
    flex-shrink: 0;
  }

  .brand-title {
    font-size: 14.5px;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--text-primary);
    white-space: nowrap;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .live-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 2px 7px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-radius: var(--radius-full);
    background: var(--live-subtle);
    color: var(--live);
    border: 1px solid var(--live-border);
  }

  .live-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
    box-shadow: 0 0 8px currentColor;
    animation: pulse-dot 2s infinite ease-in-out;
  }

  @keyframes pulse-dot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.45; transform: scale(0.85); }
  }

  .stats-count {
    font-size: 12px;
    color: var(--text-secondary);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    padding: 2px 8px;
    background: var(--bg-surface-elevated);
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-subtle);
  }

  .controls-group {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    flex: 1;
    justify-content: flex-end;
    min-width: 280px;
  }

  /* View Mode Switcher */
  .segmented-group {
    display: flex;
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    padding: 2px;
    gap: 2px;
  }

  .seg-btn {
    height: 28px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 0 8px;
    font-size: 12px;
    font-weight: 500;
    font-family: inherit;
    background: transparent;
    border: none;
    color: var(--text-secondary);
    border-radius: calc(var(--radius-md) - 2px);
    cursor: pointer;
    transition: all 0.15s ease;
    white-space: nowrap;
  }

  .seg-btn:hover {
    color: var(--text-primary);
  }

  .seg-btn.active {
    background: var(--bg-surface-hover);
    color: var(--text-primary);
    box-shadow: var(--shadow-sm);
  }

  .seg-btn svg {
    width: 13px;
    height: 13px;
    flex-shrink: 0;
  }

  .search-wrapper {
    position: relative;
    flex: 1;
    min-width: 140px;
    max-width: 205px;
    display: flex;
    align-items: center;
  }

  .search-icon {
    position: absolute;
    left: 10px;
    width: 15px;
    height: 15px;
    color: var(--text-tertiary);
    pointer-events: none;
  }

  #search {
    width: 100%;
    height: 34px;
    background: var(--bg-input);
    border: 1px solid var(--border-default);
    color: var(--text-primary);
    padding: 0 32px 0 30px;
    border-radius: var(--radius-md);
    font-size: 13.5px;
    font-family: inherit;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }

  #search:focus {
    outline: none;
    border-color: var(--border-focus);
    box-shadow: var(--shadow-focus);
  }

  #search::placeholder {
    color: var(--text-tertiary);
    font-size: 13px;
  }

  .search-shortcut-badge {
    position: absolute;
    right: 8px;
    padding: 1px 5px;
    font-size: 11px;
    font-family: var(--font-mono);
    color: var(--text-tertiary);
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: 4px;
    pointer-events: none;
    line-height: 1.3;
  }

  .search-clear-btn {
    position: absolute;
    right: 6px;
    width: 22px;
    height: 22px;
    display: none;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-tertiary);
    border-radius: 50%;
    cursor: pointer;
    font-size: 12px;
  }

  .search-clear-btn:hover {
    color: var(--text-primary);
    background: var(--bg-surface-hover);
  }

  .search-wrapper.has-val .search-shortcut-badge { display: none; }
  .search-wrapper.has-val .search-clear-btn { display: flex; }

  .select-wrapper {
    position: relative;
    display: inline-flex;
    align-items: center;
  }

  #neighborhood-filter {
    appearance: none;
    -webkit-appearance: none;
    height: 34px;
    max-width: 185px;
    background: var(--bg-input);
    border: 1px solid var(--border-default);
    color: var(--text-primary);
    padding: 0 24px 0 9px;
    border-radius: var(--radius-md);
    font-size: 12.5px;
    font-family: inherit;
    cursor: pointer;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }

  #neighborhood-filter:focus {
    outline: none;
    border-color: var(--border-focus);
    box-shadow: var(--shadow-focus);
  }

  .select-chevron {
    position: absolute;
    right: 8px;
    width: 14px;
    height: 14px;
    color: var(--text-tertiary);
    pointer-events: none;
  }

  .quick-filters {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .filter-tab-btn {
    height: 34px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 0 8px;
    font-size: 12px;
    font-weight: 500;
    font-family: inherit;
    border-radius: var(--radius-md);
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-default);
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s ease;
    user-select: none;
    white-space: nowrap;
  }

  .filter-tab-btn:hover {
    color: var(--text-primary);
    background: var(--bg-surface-hover);
  }

  .filter-tab-btn.active {
    background: var(--accent-subtle);
    border-color: var(--accent-border);
    color: var(--accent);
  }

  .filter-tab-btn.fav-tab.active {
    background: var(--favorite-subtle);
    border-color: var(--favorite-border);
    color: var(--favorite);
  }

  .filter-tab-btn.video-tab.active {
    background: var(--live-subtle);
    border-color: var(--live-border);
    color: var(--live);
  }

  .tab-count {
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    opacity: 0.85;
  }

  .density-group {
    display: flex;
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    padding: 2px;
  }

  .density-btn {
    width: 30px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-tertiary);
    border-radius: calc(var(--radius-md) - 2px);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .density-btn:hover {
    color: var(--text-primary);
  }

  .density-btn.active {
    background: var(--bg-surface-hover);
    color: var(--text-primary);
    box-shadow: var(--shadow-sm);
  }

  .icon-btn {
    width: 34px;
    height: 34px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s ease;
    flex-shrink: 0;
  }

  .icon-btn:hover {
    color: var(--text-primary);
    background: var(--bg-surface-hover);
    border-color: var(--border-strong);
  }

  .icon-btn.spinning svg {
    animation: spin 0.55s ease;
  }

  .active-filters-bar {
    max-width: 1480px;
    margin: 8px auto 0;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
  }

  .active-filters-bar:empty {
    display: none;
  }

  .filter-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 9px;
    font-size: 12px;
    font-weight: 500;
    font-family: inherit;
    border-radius: var(--radius-full);
    background: var(--accent-subtle);
    color: var(--accent);
    border: 1px solid var(--accent-border);
    cursor: pointer;
    transition: opacity 0.15s ease;
  }

  .filter-chip:hover {
    opacity: 0.85;
  }

  .filter-chip-remove {
    font-size: 11px;
    line-height: 1;
    font-weight: bold;
  }

  .clear-all-link {
    font-size: 12px;
    color: var(--text-tertiary);
    background: none;
    border: none;
    cursor: pointer;
    text-decoration: underline;
    padding: 2px 6px;
    font-family: inherit;
  }

  .clear-all-link:hover {
    color: var(--text-primary);
  }

  /* Grid View */
  main {
    max-width: 1480px;
    margin: 0 auto;
    padding: 16px;
  }

  .neighborhood-section {
    margin-bottom: 28px;
  }

  .neighborhood-heading-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 20px 0 12px;
    padding-bottom: 4px;
  }

  .neighborhood-section:first-child .neighborhood-heading-row {
    margin-top: 4px;
  }

  .neighborhood-title {
    font-size: 13.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    gap: 8px;
    white-space: nowrap;
  }

  .neighborhood-title.fav-heading {
    color: var(--favorite);
  }

  .neighborhood-title.corridor-heading {
    color: var(--accent);
  }

  .heading-count-badge {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-tertiary);
    font-variant-numeric: tabular-nums;
  }

  .heading-divider {
    flex: 1;
    height: 1px;
    background: var(--border-subtle);
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(var(--grid-min), 1fr));
    gap: 14px;
  }

  .grid.compact {
    --grid-min: 190px;
    gap: 10px;
  }

  .card {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    overflow: hidden;
    cursor: pointer;
    transition: border-color 0.18s ease, box-shadow 0.18s ease, opacity 0.18s ease;
    display: flex;
    flex-direction: column;
    position: relative;
  }

  .card:hover {
    border-color: var(--accent-border);
    box-shadow: var(--shadow-md), 0 0 20px rgba(56, 189, 248, 0.12);
  }

  .card:focus-visible {
    outline: none;
    border-color: var(--border-focus);
    box-shadow: var(--shadow-focus);
  }

  .card.offline {
    opacity: 0.65;
  }

  .card.offline:hover {
    opacity: 0.95;
    border-color: var(--offline-border);
  }

  .thumb-wrap {
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 9;
    background: var(--bg-thumb);
    overflow: hidden;
  }

  .thumb-wrap img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    transition: transform 0.3s ease;
  }

  .card:hover .thumb-wrap img {
    transform: scale(1.03);
  }

  .thumb-placeholder {
    display: none;
    position: absolute;
    inset: 0;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
    color: var(--text-tertiary);
    font-size: 11px;
    text-align: center;
    padding: 12px;
    background: var(--bg-surface-elevated);
  }

  .thumb-placeholder-icon {
    width: 22px;
    height: 22px;
    opacity: 0.6;
  }

  .thumb-hover-overlay {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.22);
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.18s ease;
  }

  .card:hover .thumb-hover-overlay {
    opacity: 1;
  }

  .play-indicator-circle {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: rgba(15, 20, 29, 0.85);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    border: 1px solid rgba(255, 255, 255, 0.35);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #ffffff;
    transform: scale(0.85);
    transition: transform 0.18s ease;
  }

  .card:hover .play-indicator-circle {
    transform: scale(1);
  }

  .badge-status {
    position: absolute;
    top: 6px;
    right: 6px;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    background: rgba(8, 12, 18, 0.8);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.45);
    display: flex;
    align-items: center;
    gap: 4px;
    letter-spacing: 0.04em;
    user-select: none;
  }

  .badge-status.still {
    color: #7dd3fc;
    border-color: rgba(56, 189, 248, 0.45);
    background: rgba(8, 15, 24, 0.82);
  }

  .badge-status.offline {
    color: #fb7185;
    border-color: rgba(244, 63, 94, 0.45);
    background: rgba(18, 8, 10, 0.84);
  }

  .badge-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: currentColor;
  }

  .fav-btn {
    position: absolute;
    top: 6px;
    left: 6px;
    width: 26px;
    height: 26px;
    border-radius: var(--radius-sm);
    background: rgba(8, 12, 18, 0.78);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    border: 1px solid rgba(255, 255, 255, 0.14);
    color: rgba(255, 255, 255, 0.75);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.15s ease;
    z-index: 2;
  }

  .fav-btn:hover {
    color: var(--favorite);
    background: rgba(8, 12, 18, 0.92);
    border-color: var(--favorite-border);
    transform: scale(1.08);
  }

  .fav-btn.active {
    color: var(--favorite);
    border-color: var(--favorite-border);
    background: rgba(25, 20, 10, 0.88);
  }

  .card-label {
    padding: 9px 10px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    background: var(--bg-surface);
    flex: 1;
  }

  .card-desc {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1.35;
    word-break: break-word;
  }

  .card-meta-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    font-size: 11px;
    color: var(--text-tertiary);
    margin-top: auto;
    padding-top: 2px;
  }

  .card-id-tag {
    font-family: var(--font-mono);
    font-size: 10.5px;
    color: var(--text-tertiary);
    flex-shrink: 0;
  }

  /* Empty Results State */
  .empty-state {
    padding: 60px 20px;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    color: var(--text-secondary);
  }

  .empty-icon {
    width: 48px;
    height: 48px;
    color: var(--text-tertiary);
    opacity: 0.7;
  }

  .empty-title {
    font-size: 17px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .empty-msg {
    font-size: 13.5px;
    max-width: 400px;
    color: var(--text-secondary);
  }

  .reset-filters-btn {
    margin-top: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    font-family: inherit;
    border-radius: var(--radius-md);
    background: var(--accent);
    color: #ffffff;
    border: none;
    cursor: pointer;
    transition: opacity 0.15s;
  }

  .reset-filters-btn:hover {
    opacity: 0.9;
  }

  /* Interactive Map View */
  #map-view {
    display: none;
    position: relative;
    width: 100%;
    height: calc(100vh - var(--header-h, 64px));
    min-height: 500px;
    background: var(--bg-page);
  }

  #map-view.active {
    display: block;
  }

  #map-canvas {
    width: 100%;
    height: 100%;
    background: var(--bg-page);
  }

  #map-canvas.dark-tiles .leaflet-tile-pane {
    filter: invert(100%) hue-rotate(180deg) brightness(92%) contrast(90%) saturate(80%);
  }

  .leaflet-container {
    font-family: var(--font-sans);
  }

  .leaflet-bar {
    border: 1px solid var(--border-default) !important;
    box-shadow: var(--shadow-md) !important;
    border-radius: var(--radius-md) !important;
    overflow: hidden;
  }

  .leaflet-bar a {
    background-color: var(--bg-surface) !important;
    color: var(--text-primary) !important;
    border-bottom-color: var(--border-subtle) !important;
  }

  .leaflet-bar a:hover,
  .leaflet-bar a:focus {
    background-color: var(--bg-surface-hover) !important;
    color: var(--accent) !important;
  }

  .leaflet-control-attribution {
    background: var(--header-bg) !important;
    color: var(--text-tertiary) !important;
    font-size: 10.5px !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    border-top-left-radius: var(--radius-sm);
  }

  .leaflet-control-attribution a {
    color: var(--text-secondary) !important;
  }

  .map-overlay-bar {
    position: absolute;
    top: 12px;
    right: 12px;
    z-index: 500;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    background: var(--header-bg);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md);
    font-size: 12px;
    color: var(--text-secondary);
  }

  .map-legend-item {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    white-space: nowrap;
  }

  .legend-swatch {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    border: 1.5px solid #ffffff;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
  }

  .legend-swatch.live { background: #10b981; }
  .legend-swatch.still { background: #38bdf8; }
  .legend-swatch.fav { background: #fbbf24; }
  .legend-swatch.offline { background: #f43f5e; }

  .map-fit-btn {
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 500;
    font-family: inherit;
    border-radius: var(--radius-sm);
    background: var(--accent-subtle);
    border: 1px solid var(--accent-border);
    color: var(--accent);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .map-fit-btn:hover {
    background: var(--accent);
    color: #ffffff;
  }

  .cam-pin-wrap {
    background: transparent !important;
    border: none !important;
  }

  .cam-pin {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 2px solid #ffffff;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.55);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 700;
    color: #080b11;
    transition: transform 0.12s ease;
  }

  .cam-pin:hover {
    transform: scale(1.22);
  }

  .cam-pin.multi {
    width: 20px;
    height: 20px;
  }

  .cam-pin.live { background: #10b981; }
  .cam-pin.still { background: #38bdf8; }
  .cam-pin.fav { background: #fbbf24; color: #080b11; }
  .cam-pin.offline { background: #f43f5e; color: #ffffff; }

  .leaflet-tooltip.cam-map-tooltip {
    background: var(--bg-surface);
    color: var(--text-primary);
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-md);
    padding: 6px;
    box-shadow: var(--shadow-lg);
    font-family: var(--font-sans);
  }

  .leaflet-tooltip.cam-map-tooltip::before {
    border-top-color: var(--border-strong);
  }

  .map-tip-body {
    width: 212px;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .map-tip-img {
    width: 212px;
    height: 119px;
    object-fit: cover;
    border-radius: var(--radius-sm);
    background: var(--bg-thumb);
    display: block;
  }

  .map-tip-title {
    font-size: 12px;
    font-weight: 600;
    line-height: 1.3;
    white-space: normal;
  }

  .map-tip-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 11px;
    color: var(--text-secondary);
  }

  .map-tip-pill {
    font-size: 10px;
    font-weight: 700;
    padding: 1px 5px;
    border-radius: 4px;
  }

  .map-tip-pill.live { background: var(--live-subtle); color: var(--live); }
  .map-tip-pill.still { background: var(--still-subtle); color: var(--still); }
  .map-tip-pill.offline { background: var(--offline-subtle); color: var(--offline); }

  /* Multi-Cam Wall View */
  #wall-view {
    display: none;
    max-width: 1480px;
    margin: 0 auto;
    padding: 16px;
  }

  #wall-view.active {
    display: block;
  }

  .wall-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 14px;
    padding: 10px 14px;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
  }

  .wall-title-group {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
  }

  .wall-heading {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .wall-presets {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
  }

  .wall-preset-btn {
    padding: 3px 9px;
    font-size: 11.5px;
    font-weight: 500;
    font-family: inherit;
    border-radius: var(--radius-full);
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-default);
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .wall-preset-btn:hover {
    color: var(--text-primary);
    border-color: var(--accent-border);
  }

  .wall-controls {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .wall-page-info {
    font-size: 12px;
    color: var(--text-secondary);
    font-variant-numeric: tabular-nums;
  }

  .wall-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
  }

  .wall-grid.cols-3 {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .wall-tile {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .wall-tile-header {
    padding: 8px 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    background: var(--bg-surface-elevated);
    border-bottom: 1px solid var(--border-subtle);
  }

  .wall-tile-title {
    font-size: 12.5px;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
    flex: 1;
  }

  .wall-tile-actions {
    display: flex;
    align-items: center;
    gap: 5px;
    flex-shrink: 0;
  }

  .wall-tile-badge {
    font-size: 10px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: var(--radius-sm);
  }

  .wall-tile-badge.live { background: var(--live-subtle); color: var(--live); border: 1px solid var(--live-border); }
  .wall-tile-badge.still { background: var(--still-subtle); color: var(--still); border: 1px solid var(--still-border); }
  .wall-tile-badge.offline { background: var(--offline-subtle); color: var(--offline); border: 1px solid var(--offline-border); }

  .wall-mini-btn {
    padding: 3px 7px;
    font-size: 11.5px;
    font-weight: 500;
    font-family: inherit;
    border-radius: var(--radius-sm);
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .wall-mini-btn:hover {
    color: var(--text-primary);
    border-color: var(--border-strong);
  }

  .wall-mini-btn.fav-on {
    color: var(--favorite);
    border-color: var(--favorite-border);
    background: var(--favorite-subtle);
  }

  .wall-media-wrap {
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 9;
    background: #000000;
    cursor: pointer;
  }

  .wall-media-wrap video,
  .wall-media-wrap img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
    background: #000000;
  }

  .wall-tile-status {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.55);
    color: #e2e8f0;
    font-size: 12px;
    pointer-events: none;
  }

  /* Fullscreen Live Video Player Modal */
  #modal {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(4, 7, 12, 0.92);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    z-index: 1000;
    align-items: center;
    justify-content: center;
    padding: 16px;
    opacity: 0;
    transition: opacity 0.2s ease;
  }

  #modal.open {
    display: flex;
    opacity: 1;
  }

  .modal-dialog {
    width: 100%;
    max-width: 1120px;
    max-height: 95vh;
    display: flex;
    flex-direction: column;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-lg);
    overflow: hidden;
    animation: modalScale 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  }

  @keyframes modalScale {
    from { transform: scale(0.96); opacity: 0; }
    to { transform: scale(1); opacity: 1; }
  }

  .modal-header {
    padding: 12px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    border-bottom: 1px solid var(--border-subtle);
    background: var(--bg-surface-elevated);
  }

  .modal-header-info {
    flex: 1;
    min-width: 0;
  }

  .modal-title-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  #modal-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .modal-live-indicator {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.04em;
    padding: 2px 7px;
    border-radius: var(--radius-full);
    color: var(--live);
    background: var(--live-subtle);
    border: 1px solid var(--live-border);
  }

  .modal-live-indicator.connecting {
    color: var(--text-secondary);
    background: var(--bg-surface);
    border-color: var(--border-default);
  }

  .modal-live-indicator.still {
    color: var(--still);
    background: var(--still-subtle);
    border-color: var(--still-border);
  }

  .modal-live-indicator.offline {
    color: var(--offline);
    background: var(--offline-subtle);
    border-color: var(--offline-border);
  }

  .modal-live-indicator.offline .live-dot,
  .modal-live-indicator.connecting .live-dot {
    animation: none;
    box-shadow: none;
  }

  .modal-meta-row {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 3px;
    flex-wrap: wrap;
  }

  #modal-sub {
    color: var(--text-secondary);
    font-variant-numeric: tabular-nums;
  }

  .modal-close-btn {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-md);
    background: transparent;
    border: 1px solid transparent;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s ease;
    flex-shrink: 0;
  }

  .modal-close-btn:hover {
    color: var(--text-primary);
    background: var(--bg-surface-hover);
    border-color: var(--border-default);
  }

  .modal-close-btn:focus-visible {
    outline: none;
    border-color: var(--border-focus);
    box-shadow: var(--shadow-focus);
  }

  .video-viewport-wrapper {
    position: relative;
    width: 100%;
    background: #000000;
    display: flex;
    align-items: center;
    justify-content: center;
    aspect-ratio: 16 / 9;
    max-height: min(66vh, calc(95vh - 220px));
  }

  .video-viewport-wrapper:fullscreen,
  .video-viewport-wrapper:-webkit-full-screen {
    max-height: 100vh;
    width: 100vw;
    height: 100vh;
  }

  .video-viewport-wrapper:fullscreen #modal-video,
  .video-viewport-wrapper:fullscreen #modal-still,
  .video-viewport-wrapper:-webkit-full-screen #modal-video,
  .video-viewport-wrapper:-webkit-full-screen #modal-still {
    max-height: 100vh;
  }

  #modal-video,
  #modal-still {
    width: 100%;
    height: 100%;
    max-height: min(66vh, calc(95vh - 220px));
    object-fit: contain;
    background: #000000;
    display: block;
  }

  #modal-still {
    display: none;
  }

  #modal-video::-webkit-media-controls-overlay-enclosure { display: none !important; }

  .player-spinner-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    background: rgba(0, 0, 0, 0.65);
    color: #ffffff;
    font-size: 13px;
    pointer-events: none;
    transition: opacity 0.2s;
  }

  .spinner-ring {
    width: 34px;
    height: 34px;
    border: 3px solid rgba(255, 255, 255, 0.2);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  #modal-error {
    position: absolute;
    inset: 0;
    display: none;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    background: rgba(10, 4, 6, 0.88);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    color: #ffffff;
    padding: 24px;
    text-align: center;
    z-index: 5;
  }

  .error-icon {
    width: 36px;
    height: 36px;
    color: var(--offline);
  }

  .error-text {
    font-size: 14px;
    font-weight: 500;
    color: #fecdd3;
    max-width: 400px;
    line-height: 1.4;
  }

  .error-actions {
    display: flex;
    gap: 10px;
    margin-top: 4px;
    flex-wrap: wrap;
    justify-content: center;
  }

  .retry-stream-btn {
    padding: 7px 14px;
    font-size: 12.5px;
    font-weight: 600;
    font-family: inherit;
    border-radius: var(--radius-md);
    background: var(--accent);
    color: #ffffff;
    border: none;
    cursor: pointer;
  }

  /* Nearby Corridor Hop Strip */
  .modal-nearby-bar {
    display: none;
    padding: 8px 16px;
    background: var(--bg-surface);
    border-top: 1px solid var(--border-subtle);
    align-items: center;
    gap: 6px;
    overflow-x: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--border-strong) transparent;
  }

  .modal-nearby-bar.visible {
    display: flex;
  }

  .nearby-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-tertiary);
    white-space: nowrap;
    margin-right: 2px;
  }

  .nearby-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 9px;
    font-size: 11.5px;
    font-family: inherit;
    border-radius: var(--radius-full);
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-default);
    color: var(--text-secondary);
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.15s ease;
  }

  .nearby-pill:hover {
    color: var(--text-primary);
    border-color: var(--accent-border);
    background: var(--bg-surface-hover);
  }

  .nearby-pill-dist {
    font-weight: 600;
    color: var(--accent);
  }

  .nearby-pill.same-spot .nearby-pill-dist {
    color: var(--live);
  }

  .modal-footer {
    padding: 10px 16px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    background: var(--bg-surface-elevated);
    border-top: 1px solid var(--border-subtle);
  }

  .nav-step-group {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .action-tools-group {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }

  .modal-btn {
    height: 34px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 0 11px;
    font-size: 12.5px;
    font-weight: 500;
    font-family: inherit;
    border-radius: var(--radius-md);
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    color: var(--text-primary);
    cursor: pointer;
    text-decoration: none;
    transition: all 0.15s ease;
    user-select: none;
  }

  .modal-btn:hover {
    background: var(--bg-surface-hover);
    border-color: var(--border-strong);
  }

  .modal-btn:focus-visible {
    outline: none;
    border-color: var(--border-focus);
    box-shadow: var(--shadow-focus);
  }

  .modal-btn svg {
    width: 14px;
    height: 14px;
    flex-shrink: 0;
    color: var(--text-secondary);
  }

  .modal-btn:hover svg {
    color: var(--text-primary);
  }

  .modal-btn.primary-action {
    background: var(--accent-subtle);
    border-color: var(--accent-border);
    color: var(--accent);
  }

  .modal-btn.primary-action:hover {
    background: var(--accent);
    color: #ffffff;
  }

  .modal-btn.primary-action:hover svg {
    color: #ffffff;
  }

  .modal-btn.active-fav {
    background: var(--favorite-subtle);
    border-color: var(--favorite-border);
    color: var(--favorite);
  }

  .modal-btn.active-fav svg {
    color: var(--favorite);
    fill: currentColor;
  }

  .keyboard-legend {
    padding: 6px 16px 8px;
    font-size: 11px;
    color: var(--text-tertiary);
    text-align: center;
    background: var(--bg-surface-elevated);
    border-top: 1px solid var(--border-subtle);
    user-select: none;
  }

  .keyboard-legend kbd {
    display: inline-block;
    padding: 1px 4px;
    font-family: var(--font-mono);
    font-size: 10px;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: 3px;
    color: var(--text-secondary);
  }

  #back-to-top {
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 38px;
    height: 38px;
    border-radius: 50%;
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-default);
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: var(--shadow-md);
    opacity: 0;
    pointer-events: none;
    transform: translateY(10px);
    transition: all 0.2s ease;
    z-index: 40;
  }

  #back-to-top.visible {
    opacity: 1;
    pointer-events: auto;
    transform: translateY(0);
  }

  #back-to-top:hover {
    color: var(--text-primary);
    background: var(--bg-surface-hover);
    border-color: var(--accent-border);
  }

  @media (max-width: 900px) {
    .wall-grid.cols-3 {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 640px) {
    header { padding: 8px 12px; }
    .nav-container { gap: 8px; }
    .controls-group { min-width: 100%; justify-content: stretch; }
    .search-wrapper { max-width: 100%; }
    .select-wrapper { flex: 1; }
    #neighborhood-filter { width: 100%; max-width: 100%; }
    .wall-grid,
    .wall-grid.cols-3 { grid-template-columns: 1fr; }
    .modal-dialog { max-height: 98vh; }
    .modal-footer { justify-content: center; }
    .action-tools-group { width: 100%; justify-content: center; }
    .keyboard-legend { display: none; }
    .map-overlay-bar { left: 10px; right: 10px; top: auto; bottom: 16px; }
  }
</style>
</head>
<body>

<header id="app-header">
  <div class="nav-container">
    <div class="brand-group">
      <svg class="brand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
        <circle cx="12" cy="13" r="4"/>
      </svg>
      <div class="brand-title">
        Seattle Traffic Cameras
        <span class="live-pill"><span class="live-dot"></span>Live</span>
      </div>
      <span class="stats-count" id="visible-count">...</span>
    </div>

    <div class="controls-group">
      <div class="segmented-group" role="tablist" aria-label="View mode">
        <button id="btn-view-grid" class="seg-btn active" title="Grid view (G)">
          <svg viewBox="0 0 16 16" fill="currentColor"><rect x="1.5" y="1.5" width="5.5" height="5.5" rx="1.2"/><rect x="9" y="1.5" width="5.5" height="5.5" rx="1.2"/><rect x="1.5" y="9" width="5.5" height="5.5" rx="1.2"/><rect x="9" y="9" width="5.5" height="5.5" rx="1.2"/></svg>
          Grid
        </button>
        <button id="btn-view-map" class="seg-btn" title="Interactive map view (M)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"></polygon><line x1="8" y1="2" x2="8" y2="18"></line><line x1="16" y1="6" x2="16" y2="22"></line></svg>
          Map
        </button>
        <button id="btn-view-wall" class="seg-btn" title="Live multi-cam wall (W)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="9" height="8" rx="1.5"></rect><rect x="13" y="3" width="9" height="8" rx="1.5"></rect><rect x="2" y="13" width="9" height="8" rx="1.5"></rect><rect x="13" y="13" width="9" height="8" rx="1.5"></rect></svg>
          Wall
        </button>
      </div>

      <div class="search-wrapper" id="search-box">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8"></circle>
          <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
        </svg>
        <input id="search" type="text" placeholder="Search street, area, ID…" autocomplete="off" spellcheck="false">
        <kbd class="search-shortcut-badge">/</kbd>
        <button id="search-clear" class="search-clear-btn" title="Clear search">✕</button>
      </div>

      <div class="select-wrapper">
        <select id="neighborhood-filter" aria-label="Corridor or neighborhood filter">
          <option value="">All locations</option>
        </select>
        <svg class="select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </div>

      <div class="quick-filters">
        <button id="fav-filter-btn" class="filter-tab-btn fav-tab" title="Toggle favorites filter">
          <span>★</span> Favorites <span id="fav-count-pill" class="tab-count"></span>
        </button>
        <button id="video-only-btn" class="filter-tab-btn video-tab" title="Show live HLS video cameras only">
          Video only
        </button>
        <button id="hide-offline-btn" class="filter-tab-btn" title="Hide offline cameras">
          Hide offline
        </button>
      </div>

      <div id="density-group" class="density-group" title="Grid display density">
        <button id="btn-density-compact" class="density-btn" title="Compact grid">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
            <rect x="1" y="1" width="3.5" height="3.5" rx="1"/>
            <rect x="6.25" y="1" width="3.5" height="3.5" rx="1"/>
            <rect x="11.5" y="1" width="3.5" height="3.5" rx="1"/>
            <rect x="1" y="6.25" width="3.5" height="3.5" rx="1"/>
            <rect x="6.25" y="6.25" width="3.5" height="3.5" rx="1"/>
            <rect x="11.5" y="6.25" width="3.5" height="3.5" rx="1"/>
            <rect x="1" y="11.5" width="3.5" height="3.5" rx="1"/>
            <rect x="6.25" y="11.5" width="3.5" height="3.5" rx="1"/>
            <rect x="11.5" y="11.5" width="3.5" height="3.5" rx="1"/>
          </svg>
        </button>
        <button id="btn-density-normal" class="density-btn active" title="Standard grid">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
            <rect x="1.5" y="1.5" width="5.5" height="5.5" rx="1.5"/>
            <rect x="9" y="1.5" width="5.5" height="5.5" rx="1.5"/>
            <rect x="1.5" y="9" width="5.5" height="5.5" rx="1.5"/>
            <rect x="9" y="9" width="5.5" height="5.5" rx="1.5"/>
          </svg>
        </button>
      </div>

      <button id="refresh-thumbs-btn" class="icon-btn" title="Refresh snapshots (R)">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="23 4 23 10 17 10"></polyline>
          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
        </svg>
      </button>

      <button id="theme-toggle-btn" class="icon-btn" title="Theme: Auto">
        <svg id="theme-icon-auto" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
          <line x1="8" y1="21" x2="16" y2="21"></line>
          <line x1="12" y1="17" x2="12" y2="21"></line>
        </svg>
        <svg id="theme-icon-moon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:none;">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
        </svg>
        <svg id="theme-icon-sun" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:none;">
          <circle cx="12" cy="12" r="5"></circle>
          <line x1="12" y1="1" x2="12" y2="3"></line>
          <line x1="12" y1="21" x2="12" y2="23"></line>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
          <line x1="1" y1="12" x2="3" y2="12"></line>
          <line x1="21" y1="12" x2="23" y2="12"></line>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
        </svg>
      </button>
    </div>
  </div>

  <div id="filter-indicator" class="active-filters-bar"></div>
</header>

<main id="main"></main>

<section id="map-view" aria-label="Interactive camera map">
  <div id="map-canvas"></div>
  <div class="map-overlay-bar" id="map-overlay-bar">
    <span class="map-legend-item"><span class="legend-swatch live"></span>Live Video</span>
    <span class="map-legend-item"><span class="legend-swatch still"></span>Highway Still</span>
    <span class="map-legend-item"><span class="legend-swatch fav"></span>Favorite</span>
    <span class="map-legend-item"><span class="legend-swatch offline"></span>Offline</span>
    <button id="btn-map-fit" class="map-fit-btn">Fit to results</button>
  </div>
</section>

<section id="wall-view" aria-label="Multi-camera live wall">
  <div class="wall-toolbar">
    <div class="wall-title-group">
      <span class="wall-heading" id="wall-heading">Live Multi-Cam Wall</span>
      <div class="wall-presets" id="wall-presets">
        <button class="wall-preset-btn" data-corridor="corridor:ship-canal">Ship Canal Bridges</button>
        <button class="wall-preset-btn" data-corridor="corridor:mercer-denny">Mercer &amp; Denny</button>
        <button class="wall-preset-btn" data-corridor="corridor:west-seattle">West Seattle Bridges</button>
        <button class="wall-preset-btn" data-corridor="corridor:i5">I-5 Corridor</button>
        <button class="wall-preset-btn" data-corridor="corridor:sr520">SR-520</button>
      </div>
    </div>
    <div class="wall-controls">
      <div class="segmented-group" title="Tiles per page (capped at 6 for HTTP/1.1 connection limit)">
        <button id="btn-wall-4" class="seg-btn active">2×2</button>
        <button id="btn-wall-6" class="seg-btn">3×2</button>
      </div>
      <button id="btn-wall-prev" class="wall-mini-btn">← Prev</button>
      <span id="wall-page-info" class="wall-page-info">...</span>
      <button id="btn-wall-next" class="wall-mini-btn">Next →</button>
    </div>
  </div>
  <div id="wall-grid" class="wall-grid"></div>
</section>

<div id="modal">
  <div class="modal-dialog">
    <div class="modal-header">
      <div class="modal-header-info">
        <div class="modal-title-row">
          <div id="modal-title">Camera Feed</div>
          <span id="modal-live-pill" class="modal-live-indicator connecting"><span class="live-dot"></span> <span id="modal-live-label">CONNECTING…</span></span>
        </div>
        <div class="modal-meta-row">
          <span id="modal-sub">...</span>
        </div>
      </div>
      <button id="modal-close" class="modal-close-btn" title="Close (Esc)">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>

    <div class="video-viewport-wrapper" id="video-viewport">
      <video id="modal-video" controls autoplay playsinline muted></video>
      <img id="modal-still" alt="">

      <div id="player-spinner" class="player-spinner-overlay">
        <div class="spinner-ring"></div>
        <span id="player-spinner-text">Connecting to live SDOT stream…</span>
      </div>

      <div id="modal-error">
        <svg class="error-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        <div class="error-text" id="modal-error-msg">Feed is currently unreachable or slow to respond.</div>
        <div class="error-actions">
          <button id="btn-retry-stream" class="retry-stream-btn">↻ Retry Stream</button>
          <a id="btn-error-direct" class="modal-btn" href="#" target="_blank" rel="noopener">Open Direct Stream</a>
        </div>
      </div>
    </div>

    <div id="modal-nearby" class="modal-nearby-bar"></div>

    <div class="modal-footer">
      <div class="nav-step-group">
        <button id="btn-prev" class="modal-btn" title="Previous camera (←)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
          Prev
        </button>
        <button id="btn-next" class="modal-btn" title="Next camera (→)">
          Next
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </button>
      </div>

      <div class="action-tools-group">
        <button id="btn-modal-fav" class="modal-btn" title="Toggle Favorite">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
          </svg>
          <span id="modal-fav-text">Favorite</span>
        </button>
        <button id="btn-show-on-map" class="modal-btn" title="Show on Map (M)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
            <circle cx="12" cy="10" r="3"></circle>
          </svg>
          Map
        </button>
        <button id="btn-fullscreen" class="modal-btn" title="Fullscreen (F)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path>
          </svg>
          Fullscreen
        </button>
        <button id="btn-pip" class="modal-btn" title="Picture in Picture (P)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
            <rect x="12" y="9" width="8" height="6" rx="1" ry="1"></rect>
          </svg>
          PiP
        </button>
        <button id="btn-copy-link" class="modal-btn" title="Copy shareable camera link (C)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
          </svg>
          <span>Copy link</span>
        </button>
        <a id="btn-open-direct" class="modal-btn primary-action" href="#" target="_blank" rel="noopener" title="Open direct stream or image">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
            <polyline points="15 3 21 3 21 9"></polyline>
            <line x1="10" y1="14" x2="21" y2="3"></line>
          </svg>
          <span id="open-direct-text">Direct Stream</span>
        </a>
      </div>
    </div>

    <div class="keyboard-legend">
      Shortcuts: <kbd>←</kbd> <kbd>→</kbd> Navigate &nbsp;·&nbsp; <kbd>Space</kbd> Play/Pause &nbsp;·&nbsp; <kbd>F</kbd> Fullscreen &nbsp;·&nbsp; <kbd>P</kbd> PiP &nbsp;·&nbsp; <kbd>M</kbd> Map &nbsp;·&nbsp; <kbd>C</kbd> Copy Link &nbsp;·&nbsp; <kbd>Esc</kbd> Close
    </div>
  </div>
</div>

<button id="back-to-top" title="Back to top">
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="18 15 12 9 6 15"></polyline>
  </svg>
</button>

<script>
const CONFIG = __CONFIG_JSON__;
const CAMERAS = __DATA_JSON__;

const FAVORITES_KEY = "sc-favorites";
const FILTERS_KEY = "sc-filters";
const SCROLL_KEY = "sc-scroll";
const DENSITY_KEY = "sc-density";
const THEME_KEY = "sc-theme";
const VIEW_KEY = "sc-view";
const WALL_SIZE_KEY = "sc-wall-size";
const STILL_REFRESH_MS = 15000;

const SHIP_CANAL_BRIDGES = [
  [47.6598, -122.3762], // Ballard Bridge
  [47.6475, -122.3498], // Fremont Bridge
  [47.6531, -122.3227], // I-5 Ship Canal Bridge
  [47.6530, -122.3200], // University Bridge
  [47.6473, -122.3046], // Montlake Bridge
];

function escHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function hasCoords(cam) {
  return typeof cam.Lat === "number" && typeof cam.Lng === "number";
}

function distanceMeters(lat1, lng1, lat2, lng2) {
  if ([lat1, lng1, lat2, lng2].some(v => typeof v !== "number")) return Infinity;
  const R = 6371000;
  const toRad = d => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function bearingCompass(lat1, lng1, lat2, lng2) {
  const toRad = d => (d * Math.PI) / 180;
  const y = Math.sin(toRad(lng2 - lng1)) * Math.cos(toRad(lat2));
  const x =
    Math.cos(toRad(lat1)) * Math.sin(toRad(lat2)) -
    Math.sin(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.cos(toRad(lng2 - lng1));
  const deg = ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
  const dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  return dirs[Math.round(deg / 45) % 8];
}

function formatDistance(meters) {
  if (meters < 1000) return Math.round(meters) + "m";
  return (meters / 1000).toFixed(1) + "km";
}

function isNearAnyBridge(cam, points, radiusMeters) {
  if (!hasCoords(cam)) return false;
  return points.some(([lat, lng]) => distanceMeters(cam.Lat, cam.Lng, lat, lng) <= radiusMeters);
}

const CORRIDORS = [
  {
    id: "corridor:i5",
    label: "I-5 Corridor",
    dirLabel: "North → South",
    match: c => /\bI-5\b/.test(c.Description),
    sort: (a, b) => (b.Lat ?? -999) - (a.Lat ?? -999),
  },
  {
    id: "corridor:i90",
    label: "I-90 Bridge & Corridor",
    dirLabel: "West → East",
    match: c => /\bI-?90\b/.test(c.Description),
    sort: (a, b) => (a.Lng ?? 999) - (b.Lng ?? 999),
  },
  {
    id: "corridor:sr520",
    label: "SR-520 Bridge & Corridor",
    dirLabel: "West → East",
    match: c => /\b(?:SR-?520|520)\b/.test(c.Description),
    sort: (a, b) => (a.Lng ?? 999) - (b.Lng ?? 999),
  },
  {
    id: "corridor:sr99",
    label: "SR-99 & Aurora Ave",
    dirLabel: "North → South",
    match: c => /\b(?:SR-?99|Aurora)\b/i.test(c.Description),
    sort: (a, b) => (b.Lat ?? -999) - (a.Lat ?? -999),
  },
  {
    id: "corridor:i405",
    label: "I-405 Corridor",
    dirLabel: "North → South",
    match: c => /\bI-?405\b/.test(c.Description),
    sort: (a, b) => (b.Lat ?? -999) - (a.Lat ?? -999),
  },
  {
    id: "corridor:ship-canal",
    label: "Ship Canal Bridges",
    dirLabel: "West → East",
    match: c => isNearAnyBridge(c, SHIP_CANAL_BRIDGES, 600),
    sort: (a, b) => (a.Lng ?? 999) - (b.Lng ?? 999),
  },
  {
    id: "corridor:west-seattle",
    label: "West Seattle & Duwamish Bridges",
    dirLabel: "West → East",
    match: c => /(?:W Seattle Bridge|Spokane|1st Ave S Bridge|Lower Bridge|Harbor Island|Delridge Way Exit|Fauntleroy Way SW & SW Alaska)/i.test(c.Description),
    sort: (a, b) => (a.Lng ?? 999) - (b.Lng ?? 999),
  },
  {
    id: "corridor:mercer-denny",
    label: "Mercer St & Denny Way",
    dirLabel: "West → East",
    match: c => /\b(?:Mercer St|Denny Way)\b/i.test(c.Description),
    sort: (a, b) => (a.Lng ?? 999) - (b.Lng ?? 999),
  },
];
const corridorById = new Map(CORRIDORS.map(co => [co.id, co]));

let thumbEpoch = Date.now();
let visibleList = CAMERAS.slice();
let currentCam = null;
let modalSessionId = 0;
let hls = null;
let subInterval = null;
let streamTimeoutTimer = null;
let stillRefreshTimer = null;
let lastFocusedEl = null;

let onlyFavorites = false;
let videoOnly = false;
let hideOffline = false;
let currentDensity = localStorage.getItem(DENSITY_KEY) === "compact" ? "compact" : "normal";
let currentTheme = ["auto", "light", "dark"].includes(localStorage.getItem(THEME_KEY))
  ? localStorage.getItem(THEME_KEY)
  : "auto";
let currentView = ["grid", "map", "wall"].includes(localStorage.getItem(VIEW_KEY))
  ? localStorage.getItem(VIEW_KEY)
  : "grid";
let wallSize = Number(localStorage.getItem(WALL_SIZE_KEY)) === 6 ? 6 : 4;
let wallPage = 0;
let wallCleanups = [];

let mapInstance = null;
let mapTileLayer = null;
let mapMarkersLayer = null;
let mapHasFitOnce = false;
let skipNextAutoFit = false;

const offlineIds = new Set();
const lastConfirmedAt = new Map();
const camById = new Map(CAMERAS.map(c => [c.Id, c]));
const cardElById = new Map();
const markerByGroupKey = new Map();

function loadFavorites() {
  try { return new Set(JSON.parse(localStorage.getItem(FAVORITES_KEY) || "[]")); }
  catch { return new Set(); }
}
const favorites = loadFavorites();

function isEffectiveLightTheme() {
  if (currentTheme === "light") return true;
  if (currentTheme === "dark") return false;
  return window.matchMedia("(prefers-color-scheme: light)").matches;
}

function updateThemeIcons() {
  const autoIcon = document.getElementById("theme-icon-auto");
  const moonIcon = document.getElementById("theme-icon-moon");
  const sunIcon = document.getElementById("theme-icon-sun");
  const btn = document.getElementById("theme-toggle-btn");

  autoIcon.style.display = currentTheme === "auto" ? "block" : "none";
  sunIcon.style.display = currentTheme === "light" ? "block" : "none";
  moonIcon.style.display = currentTheme === "dark" ? "block" : "none";

  const labels = {
    auto: "Theme: Auto (click for Light)",
    light: "Theme: Light (click for Dark)",
    dark: "Theme: Dark (click for Auto)",
  };
  btn.title = labels[currentTheme] || labels.auto;
}

function applyTheme(theme) {
  currentTheme = ["auto", "light", "dark"].includes(theme) ? theme : "auto";
  localStorage.setItem(THEME_KEY, currentTheme);
  if (currentTheme === "auto") {
    document.documentElement.removeAttribute("data-theme");
  } else {
    document.documentElement.setAttribute("data-theme", currentTheme);
  }
  updateThemeIcons();
  updateMapTiles();
}

function toggleTheme() {
  const order = ["auto", "light", "dark"];
  const next = order[(order.indexOf(currentTheme) + 1) % order.length];
  applyTheme(next);
}

function streamUrl(cam) {
  return CONFIG.wowzaTemplate.replace("{stream}", cam.StreamName || "");
}

function thumbUrl(cam, epoch = thumbEpoch) {
  if (!cam || !cam.ImageUrl) return "";
  const encoded = encodeURI(cam.ImageUrl);
  const suffix = epoch ? "?t=" + epoch : "";
  if (cam.Type === "wsdot") return CONFIG.wsdotImageBase + encoded + suffix;
  if (cam.Type === "port") return "https://images.wsdot.wa.gov/portofseattle/" + encoded + suffix;
  return CONFIG.sdotImageBase + encoded + suffix;
}

function formatAgo(ms) {
  const secs = Math.round(ms / 1000);
  if (secs < 4) return "just now";
  if (secs < 60) return secs + "s ago";
  const mins = Math.round(secs / 60);
  if (mins < 60) return mins + "m ago";
  const hrs = Math.round(mins / 60);
  return hrs + "h ago";
}

function updateModalStatus(cam, state) {
  const pill = document.getElementById("modal-live-pill");
  const label = document.getElementById("modal-live-label");
  pill.classList.remove("connecting", "still", "offline");
  if (state === "offline") {
    pill.classList.add("offline");
    label.textContent = "OFFLINE";
  } else if (state === "still") {
    pill.classList.add("still");
    label.textContent = "STILL · 15S";
  } else if (state === "connecting") {
    pill.classList.add("connecting");
    label.textContent = "CONNECTING…";
  } else {
    label.textContent = "LIVE";
  }
}

function updateModalSub(cam) {
  if (!cam) return;
  let meta = cam.Neighborhood + " · Camera " + cam.Id;
  const t = lastConfirmedAt.get(cam.Id);
  if (t) {
    meta += cam.Type === "sdot"
      ? " · Confirmed live " + formatAgo(Date.now() - t)
      : " · Refreshed " + formatAgo(Date.now() - t);
  }
  document.getElementById("modal-sub").textContent = meta;

  const isFav = favorites.has(cam.Id);
  document.getElementById("modal-fav-text").textContent = isFav ? "Favorited" : "Favorite";
  document.getElementById("btn-modal-fav").classList.toggle("active-fav", isFav);
}

function saveFavorites() {
  localStorage.setItem(FAVORITES_KEY, JSON.stringify([...favorites]));
  updateFavBadge();
}

function updateFavBadge() {
  const pill = document.getElementById("fav-count-pill");
  const count = favorites.size;
  pill.textContent = count > 0 ? "(" + count + ")" : "";
  document.getElementById("fav-filter-btn").classList.toggle("active", onlyFavorites);
}

function updateCardState(id) {
  const card = cardElById.get(id);
  const cam = camById.get(id);
  if (!card || !cam) return;

  const isOffline = offlineIds.has(id);
  const isFav = favorites.has(id);
  card.classList.toggle("offline", isOffline);

  const badge = card.querySelector(".badge-status");
  if (badge) {
    badge.className = "badge-status" + (isOffline ? " offline" : cam.Type !== "sdot" ? " still" : "");
    badge.innerHTML = '<span class="badge-dot"></span>' + (isOffline ? "OFFLINE" : cam.Type === "sdot" ? "LIVE" : "STILL");
  }

  const favBtn = card.querySelector(".fav-btn");
  if (favBtn) {
    favBtn.classList.toggle("active", isFav);
    favBtn.title = isFav ? "Remove from favorites" : "Add to favorites";
    const poly = favBtn.querySelector("polygon");
    if (poly) poly.setAttribute("fill", isFav ? "currentColor" : "none");
  }
}

function markCameraOffline(id, isOffline) {
  const changed = isOffline ? !offlineIds.has(id) : offlineIds.has(id);
  if (isOffline) offlineIds.add(id);
  else offlineIds.delete(id);

  if (changed) {
    updateCardState(id);
    const cam = camById.get(id);
    if (cam && hasCoords(cam) && mapInstance) {
      updateMapMarkerGroup(cam);
    }
    if (hideOffline && changed) {
      applyFilters();
    }
  }
}

function toggleFavorite(id) {
  if (favorites.has(id)) favorites.delete(id);
  else favorites.add(id);
  saveFavorites();
  updateCardState(id);
  if (currentCam && currentCam.Id === id) {
    updateModalSub(currentCam);
  }
  applyFilters();
}

function syncHeaderHeight() {
  const header = document.getElementById("app-header");
  if (header) {
    document.documentElement.style.setProperty("--header-h", header.offsetHeight + "px");
  }
}

function saveFilterState() {
  const state = {
    q: document.getElementById("search").value,
    hood: document.getElementById("neighborhood-filter").value,
    hideOffline,
    onlyFavorites,
    videoOnly,
  };
  localStorage.setItem(FILTERS_KEY, JSON.stringify(state));

  const params = new URLSearchParams(location.search);
  if (state.q) params.set("q", state.q); else params.delete("q");
  if (state.hood) params.set("hood", state.hood); else params.delete("hood");
  if (state.onlyFavorites) params.set("fav", "1"); else params.delete("fav");
  if (state.videoOnly) params.set("video", "1"); else params.delete("video");
  if (state.hideOffline) params.set("liveonly", "1"); else params.delete("liveonly");
  if (currentView !== "grid") params.set("view", currentView); else params.delete("view");

  const newUrl = location.pathname + (params.toString() ? "?" + params.toString() : "");
  history.replaceState(null, "", newUrl);
}

function restoreFilterState() {
  const params = new URLSearchParams(location.search);
  let state;
  try { state = JSON.parse(localStorage.getItem(FILTERS_KEY) || "null"); }
  catch { state = null; }

  const q = params.has("q") ? (params.get("q") || "") : ((state && state.q) || "");
  const hood = params.has("hood") ? (params.get("hood") || "") : ((state && state.hood) || "");
  onlyFavorites = params.has("fav") ? params.get("fav") === "1" : (state ? !!state.onlyFavorites : false);
  videoOnly = params.has("video") ? params.get("video") === "1" : (state ? !!state.videoOnly : false);
  hideOffline = params.has("liveonly") ? params.get("liveonly") === "1" : (state ? !!state.hideOffline : false);

  if (params.has("view")) {
    const pv = params.get("view");
    if (["grid", "map", "wall"].includes(pv)) currentView = pv;
  }

  const searchEl = document.getElementById("search");
  searchEl.value = q;
  document.getElementById("search-box").classList.toggle("has-val", q.length > 0);

  const hoodEl = document.getElementById("neighborhood-filter");
  hoodEl.value = hood;
  if (hoodEl.value !== hood) hoodEl.value = "";

  document.getElementById("video-only-btn").classList.toggle("active", videoOnly);
  document.getElementById("hide-offline-btn").classList.toggle("active", hideOffline);
  updateFavBadge();
}

function buildLocationOptions() {
  const sel = document.getElementById("neighborhood-filter");

  const corrGroup = document.createElement("optgroup");
  corrGroup.label = "Corridors & Bridges";
  for (const corr of CORRIDORS) {
    const count = CAMERAS.filter(corr.match).length;
    if (count === 0) continue;
    const opt = document.createElement("option");
    opt.value = corr.id;
    opt.textContent = `${corr.label} (${count})`;
    corrGroup.appendChild(opt);
  }
  sel.appendChild(corrGroup);

  const seattleHoods = [...new Set(CAMERAS.map(c => c.Neighborhood))]
    .filter(h => h && h !== "Regional Highways")
    .sort();
  const hoodGroup = document.createElement("optgroup");
  hoodGroup.label = "Seattle Neighborhoods";
  for (const h of seattleHoods) {
    const count = CAMERAS.filter(c => c.Neighborhood === h).length;
    const opt = document.createElement("option");
    opt.value = h;
    opt.textContent = `${h} (${count})`;
    hoodGroup.appendChild(opt);
  }
  sel.appendChild(hoodGroup);

  const regionalCount = CAMERAS.filter(c => c.Neighborhood === "Regional Highways").length;
  if (regionalCount > 0) {
    const regGroup = document.createElement("optgroup");
    regGroup.label = "Regional";
    const opt = document.createElement("option");
    opt.value = "Regional Highways";
    opt.textContent = `Regional Highways (${regionalCount})`;
    regGroup.appendChild(opt);
    sel.appendChild(regGroup);
  }

  sel.options[0].textContent = `All locations (${CAMERAS.length})`;
}

function setDensity(density) {
  currentDensity = density === "compact" ? "compact" : "normal";
  localStorage.setItem(DENSITY_KEY, currentDensity);
  document.getElementById("btn-density-compact").classList.toggle("active", currentDensity === "compact");
  document.getElementById("btn-density-normal").classList.toggle("active", currentDensity === "normal");
  document.querySelectorAll(".grid").forEach(g => {
    g.classList.toggle("compact", currentDensity === "compact");
  });
}

function getOrCreateCard(cam) {
  let card = cardElById.get(cam.Id);
  if (card) {
    updateCardState(cam.Id);
    if (card.dataset.epoch !== String(thumbEpoch)) {
      const img = card.querySelector("img");
      card.dataset.epoch = String(thumbEpoch);
      card._retryGen = (card._retryGen || 0) + 1;
      clearTimeout(card._retryTimer);
      img.src = thumbUrl(cam, thumbEpoch);
    }
    return card;
  }

  card = document.createElement("div");
  const isOffline = offlineIds.has(cam.Id);
  const isFav = favorites.has(cam.Id);
  const badgeClass = isOffline ? " offline" : cam.Type !== "sdot" ? " still" : "";
  const badgeLabel = isOffline ? "OFFLINE" : cam.Type === "sdot" ? "LIVE" : "STILL";

  card.className = "card" + (isOffline ? " offline" : "");
  card.dataset.id = cam.Id;
  card.dataset.epoch = String(thumbEpoch);
  card.tabIndex = 0;

  card.innerHTML = `
    <div class="thumb-wrap">
      <img loading="lazy" src="${escHtml(thumbUrl(cam, thumbEpoch))}" alt="${escHtml(cam.Description)}">
      <div class="thumb-placeholder">
        <svg class="thumb-placeholder-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
          <line x1="1" y1="1" x2="23" y2="23"/>
        </svg>
        <span>Preview unavailable</span>
      </div>
      <div class="thumb-hover-overlay">
        <div class="play-indicator-circle">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <polygon points="6 3 20 12 6 21 6 3"></polygon>
          </svg>
        </div>
      </div>
      <button class="fav-btn${isFav ? " active" : ""}" title="${isFav ? "Remove from favorites" : "Add to favorites"}" aria-label="Favorite">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="${isFav ? "currentColor" : "none"}" stroke="currentColor" stroke-width="2">
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
        </svg>
      </button>
      <span class="badge-status${badgeClass}">
        <span class="badge-dot"></span>${badgeLabel}
      </span>
    </div>
    <div class="card-label">
      <div class="card-desc">${escHtml(cam.Description)}</div>
      <div class="card-meta-row">
        <span>${escHtml(cam.Neighborhood)}</span>
        <span class="card-id-tag">${escHtml(cam.Id)}</span>
      </div>
    </div>`;

  const img = card.querySelector("img");
  const placeholder = card.querySelector(".thumb-placeholder");

  function showThumb() {
    img.style.display = "block";
    placeholder.style.display = "none";
  }

  function hideThumb() {
    img.style.display = "none";
    placeholder.style.display = "flex";
  }

  function scheduleThumbRetry(attempt, gen) {
    if (attempt > 2 || gen !== (card._retryGen || 0)) return;
    clearTimeout(card._retryTimer);
    card._retryTimer = setTimeout(() => {
      if (gen !== (card._retryGen || 0)) return;
      const retryImg = new Image();
      retryImg.onload = () => {
        if (gen !== (card._retryGen || 0)) return;
        if (cam.Type === "sdot" && retryImg.naturalWidth === 352 && retryImg.naturalHeight === 240) {
          hideThumb();
        } else {
          img.src = retryImg.src;
          showThumb();
        }
      };
      retryImg.onerror = () => {
        if (gen !== (card._retryGen || 0)) return;
        scheduleThumbRetry(attempt + 1, gen);
      };
      retryImg.src = thumbUrl(cam, Date.now());
    }, 2500 * attempt);
  }

  img.addEventListener("load", () => {
    if (cam.Type === "sdot" && img.naturalWidth === 352 && img.naturalHeight === 240) {
      hideThumb();
    } else {
      showThumb();
    }
  });

  img.addEventListener("error", () => {
    hideThumb();
    card._retryGen = (card._retryGen || 0) + 1;
    scheduleThumbRetry(1, card._retryGen);
  });

  card.querySelector(".fav-btn").addEventListener("click", e => {
    e.stopPropagation();
    toggleFavorite(cam.Id);
  });

  card.addEventListener("click", () => openModal(cam));
  card.addEventListener("keydown", e => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      openModal(cam);
    }
  });

  cardElById.set(cam.Id, card);
  return card;
}

function refreshThumbnails() {
  thumbEpoch = Date.now();
  const btn = document.getElementById("refresh-thumbs-btn");
  btn.classList.remove("spinning");
  void btn.offsetWidth;
  btn.classList.add("spinning");

  for (const [id, card] of cardElById.entries()) {
    const cam = camById.get(id);
    if (!cam || !card.isConnected) continue;
    const img = card.querySelector("img");
    clearTimeout(card._retryTimer);
    card._retryGen = (card._retryGen || 0) + 1;
    card.dataset.epoch = String(thumbEpoch);
    img.src = thumbUrl(cam, thumbEpoch);
  }
  if (currentView === "map" && mapInstance) {
    renderMapMarkers(false);
  }
}

function appendSection(main, heading, cams, { isFavSection = false, isCorridor = false } = {}) {
  if (cams.length === 0) return;
  const section = document.createElement("div");
  section.className = "neighborhood-section";

  const row = document.createElement("div");
  row.className = "neighborhood-heading-row";

  const h = document.createElement("div");
  h.className = "neighborhood-title" + (isFavSection ? " fav-heading" : isCorridor ? " corridor-heading" : "");
  const titleText = document.createTextNode((isFavSection ? "★ " : "") + heading + " ");
  h.appendChild(titleText);
  const countBadge = document.createElement("span");
  countBadge.className = "heading-count-badge";
  countBadge.textContent = `(${cams.length})`;
  h.appendChild(countBadge);
  row.appendChild(h);

  const divider = document.createElement("div");
  divider.className = "heading-divider";
  row.appendChild(divider);

  section.appendChild(row);

  const grid = document.createElement("div");
  grid.className = "grid" + (currentDensity === "compact" ? " compact" : "");
  for (const cam of cams) {
    grid.appendChild(getOrCreateCard(cam));
  }
  section.appendChild(grid);
  main.appendChild(section);
}

function resetAllFilters() {
  document.getElementById("search").value = "";
  document.getElementById("search-box").classList.remove("has-val");
  document.getElementById("neighborhood-filter").value = "";
  onlyFavorites = false;
  videoOnly = false;
  hideOffline = false;
  document.getElementById("video-only-btn").classList.remove("active");
  document.getElementById("hide-offline-btn").classList.remove("active");
  applyFilters();
}

function renderGrid() {
  const main = document.getElementById("main");
  main.innerHTML = "";

  if (visibleList.length === 0) {
    const isFavEmpty = onlyFavorites && favorites.size === 0;
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.innerHTML = `
      <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        ${isFavEmpty
          ? '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>'
          : '<circle cx="12" cy="12" r="10"></circle><line x1="8" y1="12" x2="16" y2="12"></line>'}
      </svg>
      <div class="empty-title"></div>
      <div class="empty-msg"></div>
      <button class="reset-filters-btn" id="btn-reset-filters"></button>`;
    empty.querySelector(".empty-title").textContent = isFavEmpty ? "No favorites saved yet" : "No cameras found";
    empty.querySelector(".empty-msg").textContent = isFavEmpty
      ? "Click the star icon on any camera card to add it to your pinned favorites list."
      : "No traffic cameras matched your current search or filter settings.";
    empty.querySelector("#btn-reset-filters").textContent = isFavEmpty ? "Show All Cameras" : "Reset All Filters";
    empty.querySelector("#btn-reset-filters").addEventListener("click", resetAllFilters);
    main.appendChild(empty);
    return;
  }

  const hood = document.getElementById("neighborhood-filter").value;
  const activeCorridor = corridorById.get(hood);

  if (activeCorridor) {
    appendSection(main, `${activeCorridor.label} (${activeCorridor.dirLabel})`, visibleList, { isCorridor: true });
    return;
  }

  const favCams = !onlyFavorites ? visibleList.filter(c => favorites.has(c.Id)) : [];
  if (favCams.length > 0) {
    appendSection(main, "Favorites", favCams, { isFavSection: true });
  }

  const rest = onlyFavorites ? visibleList : visibleList.filter(c => !favorites.has(c.Id));
  let lastHood = null;
  let bucket = [];
  for (const cam of rest) {
    if (cam.Neighborhood !== lastHood) {
      if (bucket.length > 0) appendSection(main, lastHood, bucket);
      lastHood = cam.Neighborhood;
      bucket = [];
    }
    bucket.push(cam);
  }
  if (bucket.length > 0) {
    appendSection(main, lastHood, bucket);
  }
}

function makeFilterChip(label, title, onClick) {
  const chip = document.createElement("button");
  chip.className = "filter-chip";
  chip.title = title;

  const textSpan = document.createElement("span");
  textSpan.textContent = label;
  chip.appendChild(textSpan);

  const removeSpan = document.createElement("span");
  removeSpan.className = "filter-chip-remove";
  removeSpan.textContent = "✕";
  chip.appendChild(removeSpan);

  chip.addEventListener("click", onClick);
  return chip;
}

function renderFilterIndicator() {
  const el = document.getElementById("filter-indicator");
  el.innerHTML = "";
  const hood = document.getElementById("neighborhood-filter").value;
  const q = document.getElementById("search").value.trim();
  let hasFilters = false;

  if (hood) {
    hasFilters = true;
    const corr = corridorById.get(hood);
    el.appendChild(makeFilterChip(corr ? corr.label : hood, "Clear location filter", () => {
      document.getElementById("neighborhood-filter").value = "";
      applyFilters();
    }));
  }

  if (q) {
    hasFilters = true;
    el.appendChild(makeFilterChip(`Search: ${q}`, "Clear search", () => {
      document.getElementById("search").value = "";
      document.getElementById("search-box").classList.remove("has-val");
      applyFilters();
    }));
  }

  if (onlyFavorites) {
    hasFilters = true;
    el.appendChild(makeFilterChip("★ Favorites Only", "Show all cameras", () => {
      onlyFavorites = false;
      applyFilters();
    }));
  }

  if (videoOnly) {
    hasFilters = true;
    el.appendChild(makeFilterChip("Video Only", "Include highway still cameras", () => {
      videoOnly = false;
      document.getElementById("video-only-btn").classList.remove("active");
      applyFilters();
    }));
  }

  if (hideOffline) {
    hasFilters = true;
    el.appendChild(makeFilterChip("Hide Offline", "Show offline cameras", () => {
      hideOffline = false;
      document.getElementById("hide-offline-btn").classList.remove("active");
      applyFilters();
    }));
  }

  if (hasFilters) {
    const clearBtn = document.createElement("button");
    clearBtn.className = "clear-all-link";
    clearBtn.textContent = "Clear all";
    clearBtn.addEventListener("click", resetAllFilters);
    el.appendChild(clearBtn);
  }
  syncHeaderHeight();
}

function applyFilters({ render = true } = {}) {
  const q = document.getElementById("search").value.trim().toLowerCase();
  const hood = document.getElementById("neighborhood-filter").value;
  const activeCorridor = corridorById.get(hood);

  let matches = CAMERAS.filter(c => {
    if (activeCorridor) {
      if (!activeCorridor.match(c)) return false;
    } else if (hood && c.Neighborhood !== hood) {
      return false;
    }
    if (q) {
      const hit =
        c.Description.toLowerCase().includes(q) ||
        c.Neighborhood.toLowerCase().includes(q) ||
        c.Id.toLowerCase().includes(q);
      if (!hit) return false;
    }
    if (videoOnly && c.Type !== "sdot") return false;
    if (hideOffline && offlineIds.has(c.Id)) return false;
    if (onlyFavorites && !favorites.has(c.Id)) return false;
    return true;
  });

  if (activeCorridor) {
    matches.sort(activeCorridor.sort);
    visibleList = matches;
  } else if (!onlyFavorites) {
    const favs = matches.filter(c => favorites.has(c.Id));
    const rest = matches.filter(c => !favorites.has(c.Id));
    visibleList = favs.concat(rest);
  } else {
    visibleList = matches;
  }

  document.getElementById("visible-count").textContent = `${visibleList.length} of ${CAMERAS.length}`;
  updateFavBadge();
  saveFilterState();
  renderFilterIndicator();

  wallPage = 0;
  if (!render) return;

  if (currentView === "grid") {
    renderGrid();
  } else if (currentView === "map") {
    renderMapMarkers(!skipNextAutoFit);
    skipNextAutoFit = false;
  } else if (currentView === "wall") {
    if (!document.getElementById("modal").classList.contains("open")) {
      renderWall();
    }
  }
}

/* ---------------- Interactive Map View ---------------- */

function updateMapTiles() {
  if (!mapInstance || typeof L === "undefined") return;
  const isLight = isEffectiveLightTheme();
  document.getElementById("map-canvas").classList.toggle("dark-tiles", !isLight);
  if (!mapTileLayer) {
    mapTileLayer = L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
      {
        maxNativeZoom: 18,
        maxZoom: 19,
        attribution: "Tiles &copy; Esri &mdash; Source: Esri, TomTom, Garmin, FAO, NOAA, USGS, &copy; OpenStreetMap contributors",
      }
    ).addTo(mapInstance);
  }
}

function getGroupPinInfo(group) {
  const anyFav = group.some(c => favorites.has(c.Id));
  const allOffline = group.every(c => offlineIds.has(c.Id));
  const anyLive = group.some(c => c.Type === "sdot" && !offlineIds.has(c.Id));
  let cls = "still";
  if (allOffline) cls = "offline";
  else if (anyFav) cls = "fav";
  else if (anyLive) cls = "live";
  const count = group.length;
  const size = count > 1 ? 20 : 14;
  return { cls, count, size };
}

function buildMarkerIcon(group) {
  const { cls, count, size } = getGroupPinInfo(group);
  const label = count > 1 ? String(count) : "";
  return L.divIcon({
    className: "cam-pin-wrap",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    html: `<div class="cam-pin ${cls}${count > 1 ? " multi" : ""}">${label}</div>`,
  });
}

function buildMapTooltipHtml(group) {
  const primary = group[0];
  const isOffline = offlineIds.has(primary.Id);
  const pillCls = isOffline ? "offline" : primary.Type === "sdot" ? "live" : "still";
  const pillText = isOffline ? "OFFLINE" : primary.Type === "sdot" ? "LIVE" : "STILL";
  const extra = group.length > 1 ? `<span>+${group.length - 1} more at spot</span>` : `<span>${escHtml(primary.Neighborhood)}</span>`;
  return `
    <div class="map-tip-body">
      <img class="map-tip-img" src="${escHtml(thumbUrl(primary, thumbEpoch))}" alt="">
      <div class="map-tip-title">${escHtml(primary.Description)}</div>
      <div class="map-tip-meta">
        ${extra}
        <span class="map-tip-pill ${pillCls}">${pillText}</span>
      </div>
    </div>`;
}

function groupKeyFor(cam) {
  return `${cam.Lat.toFixed(5)},${cam.Lng.toFixed(5)}`;
}

function updateMapMarkerGroup(cam) {
  if (!hasCoords(cam)) return;
  const entry = markerByGroupKey.get(groupKeyFor(cam));
  if (!entry) return;
  entry.marker.setIcon(buildMarkerIcon(entry.group));
  entry.marker.setTooltipContent(() => buildMapTooltipHtml(entry.group));
}

function ensureMapInitialized() {
  const canvas = document.getElementById("map-canvas");
  if (typeof L === "undefined") {
    document.getElementById("map-overlay-bar").style.display = "none";
    canvas.innerHTML = `
      <div class="empty-state">
        <div class="empty-title">Map library could not be loaded</div>
        <div class="empty-msg">Leaflet failed to load from the CDN. Check network access or switch back to Grid view.</div>
        <button class="reset-filters-btn" id="btn-map-fallback-grid">Back to Grid</button>
      </div>`;
    const fb = document.getElementById("btn-map-fallback-grid");
    if (fb) fb.addEventListener("click", () => setView("grid"));
    return false;
  }

  document.getElementById("map-overlay-bar").style.display = "flex";
  if (!mapInstance) {
    mapInstance = L.map(canvas, {
      center: [47.6062, -122.3321],
      zoom: 12,
      preferCanvas: true,
    });
    updateMapTiles();
    mapMarkersLayer = L.layerGroup().addTo(mapInstance);
  }
  return true;
}

function renderMapMarkers(fitBounds) {
  if (!ensureMapInitialized()) return;
  mapMarkersLayer.clearLayers();
  markerByGroupKey.clear();

  const groups = new Map();
  for (const cam of visibleList) {
    if (!hasCoords(cam)) continue;
    const key = groupKeyFor(cam);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(cam);
  }

  const coords = [];
  for (const [key, group] of groups.entries()) {
    const primary = group[0];
    coords.push([primary.Lat, primary.Lng]);
    const marker = L.marker([primary.Lat, primary.Lng], {
      icon: buildMarkerIcon(group),
      title: primary.Description,
    });
    marker.bindTooltip(() => buildMapTooltipHtml(group), {
      direction: "top",
      offset: [0, -10],
      opacity: 0.98,
      className: "cam-map-tooltip",
    });
    marker.on("click", () => openModal(primary));
    marker.addTo(mapMarkersLayer);
    markerByGroupKey.set(key, { marker, group });
  }

  if ((fitBounds || !mapHasFitOnce) && coords.length > 0) {
    if (coords.length === 1) {
      mapInstance.setView(coords[0], 15);
    } else {
      mapInstance.fitBounds(coords, { padding: [36, 36], maxZoom: 15 });
    }
    mapHasFitOnce = true;
  }
}

/* ---------------- Multi-Cam Wall View ---------------- */

function teardownWall() {
  for (const fn of wallCleanups) {
    try { fn(); } catch {}
  }
  wallCleanups = [];
}

function hasAnyFilterActive() {
  return Boolean(
    document.getElementById("search").value.trim() ||
    document.getElementById("neighborhood-filter").value ||
    onlyFavorites ||
    videoOnly ||
    hideOffline
  );
}

function getWallCandidates() {
  if (!hasAnyFilterActive()) {
    if (favorites.size > 0) {
      return {
        label: `★ Favorites Wall (${favorites.size})`,
        showPresets: false,
        cams: CAMERAS.filter(c => favorites.has(c.Id)),
      };
    }
    const defaultSeattle = CAMERAS.filter(c => c.Type === "sdot" && !offlineIds.has(c.Id));
    return {
      label: "Live Wall — star cameras or pick a corridor",
      showPresets: true,
      cams: defaultSeattle,
    };
  }
  return {
    label: `Filtered Wall (${visibleList.length})`,
    showPresets: false,
    cams: visibleList,
  };
}

function attachWallHls(video, statusEl, badgeEl, cam) {
  let tileHls = null;
  let timerId = null;
  let hasPlayed = false;
  let destroyed = false;
  const url = streamUrl(cam);

  const setTileOffline = () => {
    if (destroyed) return;
    statusEl.textContent = "Stream unavailable";
    statusEl.style.display = "flex";
    badgeEl.className = "wall-tile-badge offline";
    badgeEl.textContent = "OFFLINE";
    markCameraOffline(cam.Id, true);
  };

  timerId = setTimeout(() => {
    if (!hasPlayed) setTileOffline();
  }, 12000);

  video.onplaying = () => {
    if (destroyed) return;
    hasPlayed = true;
    clearTimeout(timerId);
    statusEl.style.display = "none";
    badgeEl.className = "wall-tile-badge live";
    badgeEl.textContent = "LIVE";
    lastConfirmedAt.set(cam.Id, Date.now());
    markCameraOffline(cam.Id, false);
  };

  if (video.canPlayType("application/vnd.apple.mpegurl")) {
    video.src = url;
    video.onerror = setTileOffline;
    video.play().catch(() => {});
  } else if (typeof Hls !== "undefined" && Hls.isSupported()) {
    tileHls = new Hls({ capLevelToPlayerSize: true, startLevel: -1 });
    tileHls.loadSource(url);
    tileHls.attachMedia(video);
    video.play().catch(() => {});

    let retries = 0;
    tileHls.on(Hls.Events.ERROR, (event, data) => {
      if (destroyed || !data.fatal) return;
      if (retries < 2 && data.type === Hls.ErrorTypes.NETWORK_ERROR) {
        retries++;
        tileHls.startLoad();
        return;
      }
      if (retries < 2 && data.type === Hls.ErrorTypes.MEDIA_ERROR) {
        retries++;
        tileHls.recoverMediaError();
        return;
      }
      setTileOffline();
    });
  } else {
    statusEl.textContent = "HLS unsupported in this browser";
  }

  return () => {
    destroyed = true;
    clearTimeout(timerId);
    video.onplaying = null;
    video.onerror = null;
    video.pause();
    video.removeAttribute("src");
    video.load();
    if (tileHls) {
      tileHls.destroy();
      tileHls = null;
    }
  };
}

function attachWallStill(imgEl, statusEl, badgeEl, cam) {
  let destroyed = false;
  let timerId = null;

  const refresh = () => {
    if (destroyed) return;
    const loader = new Image();
    loader.onload = () => {
      if (destroyed) return;
      imgEl.src = loader.src;
      statusEl.style.display = "none";
      badgeEl.className = "wall-tile-badge still";
      badgeEl.textContent = "STILL";
      lastConfirmedAt.set(cam.Id, Date.now());
      markCameraOffline(cam.Id, false);
    };
    loader.onerror = () => {
      if (destroyed) return;
      statusEl.textContent = "Image unavailable";
      statusEl.style.display = "flex";
      badgeEl.className = "wall-tile-badge offline";
      badgeEl.textContent = "OFFLINE";
    };
    loader.src = thumbUrl(cam, Date.now());
  };

  refresh();
  timerId = setInterval(refresh, STILL_REFRESH_MS);

  return () => {
    destroyed = true;
    clearInterval(timerId);
  };
}

function renderWall() {
  teardownWall();
  const grid = document.getElementById("wall-grid");
  grid.innerHTML = "";
  grid.classList.toggle("cols-3", wallSize === 6);

  document.getElementById("btn-wall-4").classList.toggle("active", wallSize === 4);
  document.getElementById("btn-wall-6").classList.toggle("active", wallSize === 6);

  const { label, showPresets, cams } = getWallCandidates();
  document.getElementById("wall-heading").textContent = label;
  document.getElementById("wall-presets").style.display = showPresets ? "flex" : "none";

  const totalPages = Math.max(1, Math.ceil(cams.length / wallSize));
  if (wallPage >= totalPages) wallPage = 0;

  const start = wallPage * wallSize;
  const pageCams = cams.slice(start, start + wallSize);

  const prevBtn = document.getElementById("btn-wall-prev");
  const nextBtn = document.getElementById("btn-wall-next");
  prevBtn.disabled = cams.length <= wallSize;
  nextBtn.disabled = cams.length <= wallSize;
  document.getElementById("wall-page-info").textContent =
    cams.length === 0 ? "0 cameras" : `${start + 1}–${start + pageCams.length} of ${cams.length}`;

  if (pageCams.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.innerHTML = `
      <div class="empty-title">No cameras match this wall filter</div>
      <div class="empty-msg">Clear filters or pick a corridor preset to view live cameras.</div>
      <button class="reset-filters-btn" id="btn-wall-reset">Reset Filters</button>`;
    empty.querySelector("#btn-wall-reset").addEventListener("click", resetAllFilters);
    grid.appendChild(empty);
    return;
  }

  for (const cam of pageCams) {
    const tile = document.createElement("div");
    tile.className = "wall-tile";
    const isFav = favorites.has(cam.Id);
    const isOffline = offlineIds.has(cam.Id);
    const badgeCls = isOffline ? "offline" : cam.Type === "sdot" ? "live" : "still";
    const badgeTxt = isOffline ? "OFFLINE" : cam.Type === "sdot" ? "LIVE" : "STILL";

    tile.innerHTML = `
      <div class="wall-tile-header">
        <div class="wall-tile-title" title="${escHtml(cam.Description)}">${escHtml(cam.Description)}</div>
        <div class="wall-tile-actions">
          <span class="wall-tile-badge ${badgeCls}">${badgeTxt}</span>
          <button class="wall-mini-btn wall-fav-btn${isFav ? " fav-on" : ""}" title="Toggle favorite">★</button>
          <button class="wall-mini-btn wall-expand-btn" title="Open full player">Expand</button>
        </div>
      </div>
      <div class="wall-media-wrap">
        ${cam.Type === "sdot"
          ? '<video muted autoplay playsinline></video>'
          : `<img src="${escHtml(thumbUrl(cam, thumbEpoch))}" alt="${escHtml(cam.Description)}">`}
        <div class="wall-tile-status">${cam.Type === "sdot" ? "Connecting…" : "Refreshing…"}</div>
      </div>`;

    tile.querySelector(".wall-fav-btn").addEventListener("click", () => toggleFavorite(cam.Id));
    tile.querySelector(".wall-expand-btn").addEventListener("click", () => openModal(cam));
    tile.querySelector(".wall-media-wrap").addEventListener("click", () => openModal(cam));

    grid.appendChild(tile);

    const statusEl = tile.querySelector(".wall-tile-status");
    const badgeEl = tile.querySelector(".wall-tile-badge");
    if (cam.Type === "sdot") {
      wallCleanups.push(attachWallHls(tile.querySelector("video"), statusEl, badgeEl, cam));
    } else {
      wallCleanups.push(attachWallStill(tile.querySelector("img"), statusEl, badgeEl, cam));
    }
  }
}

function setView(view, { skipFit = false } = {}) {
  const next = ["grid", "map", "wall"].includes(view) ? view : "grid";
  if (currentView === "wall" && next !== "wall") {
    teardownWall();
  }
  currentView = next;
  localStorage.setItem(VIEW_KEY, currentView);

  document.getElementById("btn-view-grid").classList.toggle("active", currentView === "grid");
  document.getElementById("btn-view-map").classList.toggle("active", currentView === "map");
  document.getElementById("btn-view-wall").classList.toggle("active", currentView === "wall");

  document.getElementById("main").style.display = currentView === "grid" ? "block" : "none";
  document.getElementById("density-group").style.display = currentView === "grid" ? "flex" : "none";
  document.getElementById("map-view").classList.toggle("active", currentView === "map");
  document.getElementById("wall-view").classList.toggle("active", currentView === "wall");

  if (currentView !== "grid") {
    document.getElementById("back-to-top").classList.remove("visible");
  } else {
    document.getElementById("back-to-top").classList.toggle("visible", window.scrollY > 350);
  }

  saveFilterState();
  syncHeaderHeight();

  if (currentView === "grid") {
    renderGrid();
  } else if (currentView === "map") {
    if (skipFit) mapHasFitOnce = true;
    renderMapMarkers(!skipFit);
    if (mapInstance) {
      setTimeout(() => mapInstance.invalidateSize(), 30);
    }
  } else if (currentView === "wall") {
    if (!document.getElementById("modal").classList.contains("open")) {
      renderWall();
    }
  }
}

/* ---------------- Player Modal ---------------- */

function renderNearbyBar(cam) {
  const bar = document.getElementById("modal-nearby");
  bar.innerHTML = "";
  if (!hasCoords(cam)) {
    bar.classList.remove("visible");
    return;
  }

  const candidates = [];
  for (const other of CAMERAS) {
    if (other.Id === cam.Id || !hasCoords(other)) continue;
    if (videoOnly && other.Type !== "sdot") continue;
    if (hideOffline && offlineIds.has(other.Id)) continue;
    const dist = distanceMeters(cam.Lat, cam.Lng, other.Lat, other.Lng);
    if (dist <= 3000) {
      candidates.push({ cam: other, dist });
    }
  }

  candidates.sort((a, b) => a.dist - b.dist);
  const sameSpot = candidates.filter(x => x.dist < 35);
  const nearby = candidates.filter(x => x.dist >= 35).slice(0, 5);
  const shown = sameSpot.concat(nearby);

  if (shown.length === 0) {
    bar.classList.remove("visible");
    return;
  }

  const label = document.createElement("span");
  label.className = "nearby-label";
  label.textContent = "Nearby:";
  bar.appendChild(label);

  for (const item of shown) {
    const pill = document.createElement("button");
    const isSame = item.dist < 35;
    pill.className = "nearby-pill" + (isSame ? " same-spot" : "");

    const distSpan = document.createElement("span");
    distSpan.className = "nearby-pill-dist";
    if (isSame) {
      distSpan.textContent = "Same spot";
    } else {
      const dir = bearingCompass(cam.Lat, cam.Lng, item.cam.Lat, item.cam.Lng);
      distSpan.textContent = `${formatDistance(item.dist)} ${dir}`;
    }
    pill.appendChild(distSpan);

    const nameSpan = document.createElement("span");
    nameSpan.textContent = item.cam.Description;
    pill.appendChild(nameSpan);

    pill.addEventListener("click", () => openModal(item.cam));
    bar.appendChild(pill);
  }
  bar.classList.add("visible");
}

function showModalError(msg, cam, sessionId) {
  if (sessionId !== modalSessionId) return;
  document.getElementById("player-spinner").style.display = "none";
  document.getElementById("modal-error-msg").textContent = msg;
  const directUrl = cam.Type === "sdot" ? streamUrl(cam) : thumbUrl(cam, Date.now());
  const errDirect = document.getElementById("btn-error-direct");
  errDirect.href = directUrl;
  errDirect.textContent = cam.Type === "sdot" ? "Open Direct Stream" : "Open Image";
  document.getElementById("btn-retry-stream").textContent = cam.Type === "sdot" ? "↻ Retry Stream" : "↻ Retry Image";
  updateModalStatus(cam, "offline");
  document.getElementById("modal-error").style.display = "flex";
}

function clearModalTimers() {
  if (subInterval) { clearInterval(subInterval); subInterval = null; }
  if (streamTimeoutTimer) { clearTimeout(streamTimeoutTimer); streamTimeoutTimer = null; }
  if (stillRefreshTimer) { clearInterval(stillRefreshTimer); stillRefreshTimer = null; }
}

function teardownModalMedia() {
  clearModalTimers();
  const video = document.getElementById("modal-video");
  video.onplaying = null;
  video.onerror = null;
  video.pause();
  video.removeAttribute("src");
  video.load();
  if (hls) {
    hls.destroy();
    hls = null;
  }
  const still = document.getElementById("modal-still");
  still.onload = null;
  still.onerror = null;
  still.removeAttribute("src");
}

function openModal(cam) {
  if (!cam) return;
  const modal = document.getElementById("modal");
  const wasOpen = modal.classList.contains("open");
  if (!wasOpen) {
    lastFocusedEl = document.activeElement;
  }

  if (currentView === "wall") {
    teardownWall();
  }

  teardownModalMedia();
  currentCam = cam;
  modalSessionId += 1;
  const sessionId = modalSessionId;

  const video = document.getElementById("modal-video");
  const still = document.getElementById("modal-still");
  const errEl = document.getElementById("modal-error");
  const spinner = document.getElementById("player-spinner");
  const spinnerText = document.getElementById("player-spinner-text");

  errEl.style.display = "none";
  spinner.style.display = "flex";
  document.getElementById("modal-title").textContent = cam.Description;
  updateModalSub(cam);
  renderNearbyBar(cam);

  const pipBtn = document.getElementById("btn-pip");
  pipBtn.style.display = (document.pictureInPictureEnabled && cam.Type === "sdot") ? "inline-flex" : "none";
  document.getElementById("btn-show-on-map").style.display = hasCoords(cam) ? "inline-flex" : "none";

  const params = new URLSearchParams(location.search);
  params.set("cam", cam.Id);
  history.replaceState(null, "", location.pathname + "?" + params.toString());

  subInterval = setInterval(() => updateModalSub(cam), 10000);

  if (cam.Type === "sdot") {
    still.style.display = "none";
    video.style.display = "block";
    spinnerText.textContent = "Connecting to live SDOT stream…";
    updateModalStatus(cam, "connecting");
    const directBtn = document.getElementById("btn-open-direct");
    directBtn.href = streamUrl(cam);
    document.getElementById("open-direct-text").textContent = "Direct Stream";

    let hasPlayed = false;
    streamTimeoutTimer = setTimeout(() => {
      if (sessionId !== modalSessionId || hasPlayed) return;
      markCameraOffline(cam.Id, true);
      showModalError("Live feed connection timed out. Camera may be temporarily offline.", cam, sessionId);
    }, 12000);

    video.onplaying = () => {
      if (sessionId !== modalSessionId) return;
      hasPlayed = true;
      clearTimeout(streamTimeoutTimer);
      spinner.style.display = "none";
      errEl.style.display = "none";
      markCameraOffline(cam.Id, false);
      lastConfirmedAt.set(cam.Id, Date.now());
      updateModalStatus(cam, "live");
      updateModalSub(cam);
    };

    const url = streamUrl(cam);

    // Always check native HLS before hls.js to avoid Safari MSE stalling at 0:00.
    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.onerror = () => {
        if (sessionId !== modalSessionId || hasPlayed) return;
        clearTimeout(streamTimeoutTimer);
        markCameraOffline(cam.Id, true);
        showModalError("Live stream is not responding (camera may be offline).", cam, sessionId);
      };
      video.src = url;
      video.play().catch(() => {});
    } else if (typeof Hls !== "undefined" && Hls.isSupported()) {
      hls = new Hls({ capLevelToPlayerSize: false, startLevel: -1 });
      hls.loadSource(url);
      hls.attachMedia(video);
      video.play().catch(() => {});

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        if (sessionId !== modalSessionId) return;
        if (hls && hls.levels && hls.levels.length > 1) {
          hls.currentLevel = hls.levels.length - 1;
        }
        video.play().catch(() => {});
      });

      let hlsRetries = 0;
      hls.on(Hls.Events.ERROR, (event, data) => {
        if (sessionId !== modalSessionId || !data.fatal) return;
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
        clearTimeout(streamTimeoutTimer);
        markCameraOffline(cam.Id, true);
        showModalError("Live stream is not responding (camera may be offline).", cam, sessionId);
      });
    } else {
      clearTimeout(streamTimeoutTimer);
      showModalError("This browser cannot play HLS streams directly.", cam, sessionId);
    }
  } else {
    video.style.display = "none";
    still.style.display = "block";
    spinnerText.textContent = "Loading highway camera snapshot…";
    updateModalStatus(cam, "still");

    const imgHref = thumbUrl(cam, thumbEpoch);
    const directBtn = document.getElementById("btn-open-direct");
    directBtn.href = imgHref;
    document.getElementById("open-direct-text").textContent = "Open Image";

    const loadStillFrame = isInitial => {
      if (sessionId !== modalSessionId) return;
      const freshUrl = thumbUrl(cam, Date.now());
      const preloader = new Image();
      preloader.onload = () => {
        if (sessionId !== modalSessionId) return;
        still.src = preloader.src;
        directBtn.href = preloader.src;
        spinner.style.display = "none";
        errEl.style.display = "none";
        markCameraOffline(cam.Id, false);
        lastConfirmedAt.set(cam.Id, Date.now());
        updateModalStatus(cam, "still");
        updateModalSub(cam);
      };
      preloader.onerror = () => {
        if (sessionId !== modalSessionId) return;
        if (isInitial) {
          markCameraOffline(cam.Id, true);
          showModalError("Camera image could not be loaded right now.", cam, sessionId);
        }
      };
      preloader.src = freshUrl;
    };

    loadStillFrame(true);
    stillRefreshTimer = setInterval(() => loadStillFrame(false), STILL_REFRESH_MS);
  }

  modal.classList.add("open");
  if (!wasOpen) {
    document.getElementById("modal-close").focus({ preventScroll: true });
  }
}

function closeModal() {
  const modal = document.getElementById("modal");
  if (!modal.classList.contains("open")) return;
  modal.classList.remove("open");

  const video = document.getElementById("modal-video");
  const keepPip = currentCam && currentCam.Type === "sdot" && document.pictureInPictureElement === video;

  if (keepPip) {
    clearModalTimers();
  } else {
    modalSessionId += 1;
    teardownModalMedia();
    currentCam = null;
  }

  const params = new URLSearchParams(location.search);
  params.delete("cam");
  const newUrl = location.pathname + (params.toString() ? "?" + params.toString() : "");
  history.replaceState(null, "", newUrl);

  if (lastFocusedEl && lastFocusedEl.isConnected && typeof lastFocusedEl.focus === "function") {
    lastFocusedEl.focus({ preventScroll: true });
  }
  lastFocusedEl = null;

  if (currentView === "wall" && !keepPip) {
    renderWall();
  }
}

function step(delta) {
  if (visibleList.length === 0) return;
  const idx = currentCam ? visibleList.findIndex(c => c.Id === currentCam.Id) : -1;
  const nextIdx = idx === -1 ? 0 : (idx + delta + visibleList.length) % visibleList.length;
  openModal(visibleList[nextIdx]);
}

function init() {
  const searchInput = document.getElementById("search");
  searchInput.addEventListener("input", () => {
    document.getElementById("search-box").classList.toggle("has-val", searchInput.value.length > 0);
    applyFilters();
  });

  document.getElementById("search-clear").addEventListener("click", () => {
    searchInput.value = "";
    document.getElementById("search-box").classList.remove("has-val");
    searchInput.focus();
    applyFilters();
  });

  document.getElementById("neighborhood-filter").addEventListener("change", applyFilters);

  document.getElementById("fav-filter-btn").addEventListener("click", () => {
    onlyFavorites = !onlyFavorites;
    applyFilters();
  });

  document.getElementById("video-only-btn").addEventListener("click", () => {
    videoOnly = !videoOnly;
    document.getElementById("video-only-btn").classList.toggle("active", videoOnly);
    applyFilters();
  });

  document.getElementById("hide-offline-btn").addEventListener("click", () => {
    hideOffline = !hideOffline;
    document.getElementById("hide-offline-btn").classList.toggle("active", hideOffline);
    applyFilters();
  });

  document.getElementById("btn-density-compact").addEventListener("click", () => setDensity("compact"));
  document.getElementById("btn-density-normal").addEventListener("click", () => setDensity("normal"));
  document.getElementById("refresh-thumbs-btn").addEventListener("click", refreshThumbnails);
  document.getElementById("theme-toggle-btn").addEventListener("click", toggleTheme);

  document.getElementById("btn-view-grid").addEventListener("click", () => setView("grid"));
  document.getElementById("btn-view-map").addEventListener("click", () => setView("map"));
  document.getElementById("btn-view-wall").addEventListener("click", () => setView("wall"));

  document.getElementById("btn-map-fit").addEventListener("click", () => {
    mapHasFitOnce = false;
    renderMapMarkers(true);
  });

  document.getElementById("btn-wall-4").addEventListener("click", () => {
    wallSize = 4;
    wallPage = 0;
    localStorage.setItem(WALL_SIZE_KEY, "4");
    renderWall();
  });

  document.getElementById("btn-wall-6").addEventListener("click", () => {
    wallSize = 6;
    wallPage = 0;
    localStorage.setItem(WALL_SIZE_KEY, "6");
    renderWall();
  });

  document.getElementById("btn-wall-prev").addEventListener("click", () => {
    const total = Math.max(1, Math.ceil(getWallCandidates().cams.length / wallSize));
    wallPage = (wallPage - 1 + total) % total;
    renderWall();
  });

  document.getElementById("btn-wall-next").addEventListener("click", () => {
    const total = Math.max(1, Math.ceil(getWallCandidates().cams.length / wallSize));
    wallPage = (wallPage + 1) % total;
    renderWall();
  });

  document.querySelectorAll(".wall-preset-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.getElementById("neighborhood-filter").value = btn.dataset.corridor;
      applyFilters();
    });
  });

  document.getElementById("modal-close").addEventListener("click", closeModal);
  document.getElementById("btn-prev").addEventListener("click", () => step(-1));
  document.getElementById("btn-next").addEventListener("click", () => step(1));
  document.getElementById("btn-retry-stream").addEventListener("click", () => {
    if (currentCam) openModal(currentCam);
  });

  document.getElementById("btn-modal-fav").addEventListener("click", () => {
    if (currentCam) toggleFavorite(currentCam.Id);
  });

  document.getElementById("btn-show-on-map").addEventListener("click", () => {
    if (!currentCam || !hasCoords(currentCam)) return;
    const target = currentCam;
    skipNextAutoFit = true;
    closeModal();
    setView("map", { skipFit: true });
    if (mapInstance) {
      setTimeout(() => {
        mapInstance.invalidateSize();
        mapInstance.setView([target.Lat, target.Lng], 15, { animate: false });
        skipNextAutoFit = false;
      }, 40);
    } else {
      skipNextAutoFit = false;
    }
  });

  document.getElementById("btn-fullscreen").addEventListener("click", () => {
    const viewport = document.getElementById("video-viewport");
    const video = document.getElementById("modal-video");
    if (!document.fullscreenElement && !document.webkitFullscreenElement) {
      if (viewport.requestFullscreen) viewport.requestFullscreen();
      else if (viewport.webkitRequestFullscreen) viewport.webkitRequestFullscreen();
      else if (currentCam && currentCam.Type === "sdot" && video.webkitEnterFullscreen) video.webkitEnterFullscreen();
    } else {
      if (document.exitFullscreen) document.exitFullscreen();
      else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
    }
  });

  if (!document.pictureInPictureEnabled) {
    document.getElementById("btn-pip").style.display = "none";
  }

  document.getElementById("btn-pip").addEventListener("click", async () => {
    try {
      if (document.pictureInPictureElement) {
        await document.exitPictureInPicture();
      } else {
        await document.getElementById("modal-video").requestPictureInPicture();
      }
    } catch {}
  });

  document.getElementById("modal-video").addEventListener("leavepictureinpicture", () => {
    const modal = document.getElementById("modal");
    if (!modal.classList.contains("open")) {
      modalSessionId += 1;
      teardownModalMedia();
      currentCam = null;
      if (currentView === "wall") {
        renderWall();
      }
    }
  });

  document.getElementById("btn-copy-link").addEventListener("click", async () => {
    if (!currentCam) return;
    const deepLink = new URL(location.href);
    deepLink.searchParams.set("cam", currentCam.Id);
    const link = deepLink.toString();
    const btnSpan = document.querySelector("#btn-copy-link span");

    let copied = false;
    try {
      await Promise.race([
        navigator.clipboard.writeText(link),
        new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), 2000)),
      ]);
      copied = true;
    } catch {
      const ta = document.createElement("textarea");
      ta.value = link;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { copied = document.execCommand("copy"); } catch {}
      document.body.removeChild(ta);
    }

    const original = btnSpan.textContent;
    btnSpan.textContent = copied ? "Copied!" : "Failed";
    setTimeout(() => { btnSpan.textContent = original; }, 1600);
  });

  document.getElementById("modal").addEventListener("click", e => {
    if (e.target.id === "modal") closeModal();
  });

  document.addEventListener("keydown", e => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;

    const modalOpen = document.getElementById("modal").classList.contains("open");
    if (modalOpen) {
      if (e.key === "Escape") { closeModal(); return; }
      if (e.key === "ArrowRight") { step(1); return; }
      if (e.key === "ArrowLeft") { step(-1); return; }
      if (e.key === " ") {
        const activeTag = document.activeElement ? document.activeElement.tagName : "";
        if (["BUTTON", "A", "INPUT", "SELECT"].includes(activeTag)) return;
        e.preventDefault();
        if (currentCam && currentCam.Type === "sdot") {
          const video = document.getElementById("modal-video");
          if (video.paused) video.play().catch(() => {});
          else video.pause();
        }
        return;
      }
      if (e.key === "f" || e.key === "F") {
        e.preventDefault();
        document.getElementById("btn-fullscreen").click();
        return;
      }
      if (e.key === "p" || e.key === "P") {
        if (currentCam && currentCam.Type === "sdot" && document.pictureInPictureEnabled) {
          e.preventDefault();
          document.getElementById("btn-pip").click();
        }
        return;
      }
      if (e.key === "m" || e.key === "M") {
        if (currentCam && hasCoords(currentCam)) {
          e.preventDefault();
          document.getElementById("btn-show-on-map").click();
        }
        return;
      }
      if (e.key === "c" || e.key === "C") {
        e.preventDefault();
        document.getElementById("btn-copy-link").click();
      }
      return;
    }

    const tag = document.activeElement ? document.activeElement.tagName : "";
    if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;

    if (e.key === "/") {
      e.preventDefault();
      document.getElementById("search").focus();
    } else if (e.key === "g" || e.key === "G") {
      e.preventDefault();
      setView("grid");
    } else if (e.key === "m" || e.key === "M") {
      e.preventDefault();
      setView("map");
    } else if (e.key === "w" || e.key === "W") {
      e.preventDefault();
      setView("wall");
    } else if (e.key === "r" || e.key === "R") {
      e.preventDefault();
      refreshThumbnails();
    }
  });

  const backToTopBtn = document.getElementById("back-to-top");
  window.addEventListener("scroll", () => {
    if (currentView === "grid") {
      backToTopBtn.classList.toggle("visible", window.scrollY > 350);
    }
    clearTimeout(window._scrollSaveTimer);
    window._scrollSaveTimer = setTimeout(() => {
      localStorage.setItem(SCROLL_KEY, String(window.scrollY));
    }, 200);
  }, { passive: true });

  backToTopBtn.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", () => {
    if (currentTheme === "auto") {
      updateThemeIcons();
      updateMapTiles();
    }
  });

  window.addEventListener("resize", syncHeaderHeight);

  applyTheme(currentTheme);
  buildLocationOptions();
  restoreFilterState();
  setDensity(currentDensity);
  applyFilters({ render: false });
  setView(currentView, { skipFit: false });

  const deepLinkId = new URL(location.href).searchParams.get("cam");
  const deepLinkCam = deepLinkId && camById.get(deepLinkId);
  if (deepLinkCam) {
    openModal(deepLinkCam);
  } else if (currentView === "grid") {
    const savedScroll = Number(localStorage.getItem(SCROLL_KEY) || 0);
    if (savedScroll > 0) window.scrollTo(0, savedScroll);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
</script>
</body>
</html>
"""


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    data_path = repo_root / "data" / "cameras.json"
    out_path = repo_root / "index.html"

    config, raw_cams = load_camera_payload(data_path)
    cameras = prepare_cameras(raw_cams)

    sdot_count = sum(1 for c in cameras if c.get("Type") == "sdot")
    wsdot_count = sum(1 for c in cameras if c.get("Type") == "wsdot")
    print(f"{len(cameras)} cameras embedded ({sdot_count} sdot, {wsdot_count} wsdot)")

    html = HTML_TEMPLATE.replace("__CONFIG_JSON__", safe_json(config)).replace(
        "__DATA_JSON__", safe_json(cameras)
    )
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {out_path} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
