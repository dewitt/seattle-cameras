#!/usr/bin/env python3
"""
Generate index.html from data/cameras.json.

Only Type == "sdot" cameras get embedded: those are the ones SDOT serves off
its Wowza streaming server (streamlock.net) with a real live HLS feed. The
other type present in the API response, "wsdot" (state highway cameras,
e.g. SR-99), are static-refresh JPEGs only — confirmed by reading SDOT's own
site JS (camera.video.js): the "Video" button there is only wired up when
camera.Type === "sdot". wsdot cameras are left out of this tool for now.

Run scripts/fetch_cameras.py first to (re)generate data/cameras.json.
"""
import json

with open("data/cameras.json") as f:
    cams = json.load(f)

sdot = [c for c in cams if c["Type"] == "sdot"]
sdot.sort(key=lambda c: (c["Neighborhood"], c["Description"]))

for c in sdot:
    c["StreamName"] = c["ImageUrl"].replace(".jpg", ".stream")

data_json = json.dumps(sdot, separators=(",", ":"))
print(f"{len(sdot)} sdot cameras embedded")

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Seattle Traffic Cameras — Live Stream Monitor</title>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="Single-page Seattle SDOT live traffic camera directory and HLS video viewer.">
<script src="https://cdn.jsdelivr.net/npm/hls.js@1.5.17/dist/hls.min.js"></script>
<style>
  :root {
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
    --header-bg: rgba(15, 20, 29, 0.86);
  }

  [data-theme="light"] {
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
    --text-tertiary: #94a3b8;

    --accent: #0284c7;
    --accent-hover: #0369a1;
    --accent-subtle: rgba(2, 132, 199, 0.1);
    --accent-border: rgba(2, 132, 199, 0.25);

    --live: #059669;
    --live-subtle: rgba(5, 150, 105, 0.1);
    --live-border: rgba(5, 150, 105, 0.25);

    --offline: #e11d48;
    --offline-subtle: rgba(225, 29, 72, 0.1);
    --offline-border: rgba(225, 29, 72, 0.25);

    --favorite: #d97706;
    --favorite-subtle: rgba(217, 119, 6, 0.1);
    --favorite-border: rgba(217, 119, 6, 0.25);

    --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.06);
    --shadow-md: 0 4px 14px rgba(0, 0, 0, 0.08);
    --shadow-lg: 0 16px 36px rgba(0, 0, 0, 0.12);
    --shadow-focus: 0 0 0 3px rgba(2, 132, 199, 0.18);

    --header-bg: rgba(255, 255, 255, 0.9);
  }

  @media (prefers-color-scheme: light) {
    :root:not([data-theme="dark"]) {
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
      --text-tertiary: #94a3b8;

      --accent: #0284c7;
      --accent-hover: #0369a1;
      --accent-subtle: rgba(2, 132, 199, 0.1);
      --accent-border: rgba(2, 132, 199, 0.25);

      --live: #059669;
      --live-subtle: rgba(5, 150, 105, 0.1);
      --live-border: rgba(5, 150, 105, 0.25);

      --offline: #e11d48;
      --offline-subtle: rgba(225, 29, 72, 0.1);
      --offline-border: rgba(225, 29, 72, 0.25);

      --favorite: #d97706;
      --favorite-subtle: rgba(217, 119, 6, 0.1);
      --favorite-border: rgba(217, 119, 6, 0.25);

      --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.06);
      --shadow-md: 0 4px 14px rgba(0, 0, 0, 0.08);
      --shadow-lg: 0 16px 36px rgba(0, 0, 0, 0.12);
      --shadow-focus: 0 0 0 3px rgba(2, 132, 199, 0.18);

      --header-bg: rgba(255, 255, 255, 0.9);
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

  /* Sticky Top Navigation Bar */
  header {
    position: sticky;
    top: 0;
    z-index: 50;
    background: var(--header-bg);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border-subtle);
    padding: 10px 16px;
    transition: background-color 0.2s;
  }

  .nav-container {
    max-width: 1440px;
    margin: 0 auto;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: center;
    justify-content: space-between;
  }

  .brand-group {
    display: flex;
    align-items: center;
    gap: 10px;
    user-select: none;
  }

  .brand-icon {
    width: 26px;
    height: 26px;
    color: var(--accent);
    flex-shrink: 0;
  }

  .brand-title {
    font-size: 15px;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--text-primary);
    white-space: nowrap;
    display: flex;
    align-items: center;
    gap: 8px;
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
    padding: 2px 7px;
    background: var(--bg-surface-elevated);
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-subtle);
  }

  /* Header Control Group */
  .controls-group {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    flex: 1;
    justify-content: flex-end;
    min-width: 280px;
  }

  .search-wrapper {
    position: relative;
    flex: 1;
    min-width: 180px;
    max-width: 320px;
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
    transition: all 0.15s ease;
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

  /* Neighborhood Dropdown */
  .select-wrapper {
    position: relative;
    display: inline-flex;
    align-items: center;
  }

  #neighborhood-filter {
    appearance: none;
    -webkit-appearance: none;
    height: 34px;
    background: var(--bg-input);
    border: 1px solid var(--border-default);
    color: var(--text-primary);
    padding: 0 28px 0 10px;
    border-radius: var(--radius-md);
    font-size: 13px;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.15s ease;
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

  /* Segmented Quick Filter Chips & Toggles */
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
    padding: 0 10px;
    font-size: 12.5px;
    font-weight: 500;
    font-family: inherit;
    border-radius: var(--radius-md);
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-default);
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s ease;
    user-select: none;
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

  .tab-count {
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    opacity: 0.85;
  }

  /* Density View Toggle */
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

  /* Theme Toggle Button */
  #theme-toggle-btn {
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
  }

  #theme-toggle-btn:hover {
    color: var(--text-primary);
    background: var(--bg-surface-hover);
    border-color: var(--border-strong);
  }

  /* Active Filter Indicator Bar */
  .active-filters-bar {
    max-width: 1440px;
    margin: 8px auto 0;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
  }

  .filter-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 8px;
    font-size: 12px;
    font-weight: 500;
    border-radius: var(--radius-full);
    background: var(--accent-subtle);
    color: var(--accent);
    border: 1px solid var(--accent-border);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .filter-chip:hover {
    opacity: 0.85;
    transform: translateY(-1px);
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
  }

  .clear-all-link:hover {
    color: var(--text-primary);
  }

  /* Main Layout */
  main {
    max-width: 1440px;
    margin: 0 auto;
    padding: 16px;
  }

  /* Neighborhood Section Headings */
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

  /* Grid & Cards */
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
    transition: transform 0.18s cubic-bezier(0.16, 1, 0.3, 1),
                border-color 0.18s ease,
                box-shadow 0.18s ease;
    display: flex;
    flex-direction: column;
    position: relative;
  }

  .card:hover {
    transform: translateY(-2px);
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

  /* Play Hover Overlay */
  .thumb-hover-overlay {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.25);
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

  /* Card Badges */
  .badge-status {
    position: absolute;
    top: 6px;
    right: 6px;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    background: rgba(8, 12, 18, 0.78);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    color: var(--live);
    border: 1px solid var(--live-border);
    display: flex;
    align-items: center;
    gap: 4px;
    letter-spacing: 0.04em;
    user-select: none;
  }

  .badge-status.offline {
    color: var(--offline);
    border-color: var(--offline-border);
    background: rgba(18, 8, 10, 0.82);
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
    background: rgba(8, 12, 18, 0.75);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: rgba(255, 255, 255, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.15s ease;
    z-index: 2;
  }

  .fav-btn:hover {
    color: var(--favorite);
    background: rgba(8, 12, 18, 0.9);
    border-color: var(--favorite-border);
    transform: scale(1.1);
  }

  .fav-btn.active {
    color: var(--favorite);
    border-color: var(--favorite-border);
    background: rgba(25, 20, 10, 0.85);
  }

  .card-label {
    padding: 9px 10px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    background: var(--bg-surface);
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
    font-size: 11px;
    color: var(--text-tertiary);
    margin-top: 1px;
  }

  .card-id-tag {
    font-family: var(--font-mono);
    font-size: 10.5px;
    color: var(--text-tertiary);
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
    max-width: 380px;
    color: var(--text-secondary);
  }

  .reset-filters-btn {
    margin-top: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
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
    max-width: 1100px;
    max-height: 94vh;
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

  .modal-meta-row {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 3px;
    flex-wrap: wrap;
  }

  .modal-live-indicator {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    color: var(--live);
    font-weight: 600;
    font-size: 11.5px;
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

  /* Video Viewport Container */
  .video-viewport-wrapper {
    position: relative;
    width: 100%;
    background: #000000;
    display: flex;
    align-items: center;
    justify-content: center;
    aspect-ratio: 16 / 9;
    max-height: 72vh;
  }

  #modal-video {
    width: 100%;
    height: 100%;
    max-height: 72vh;
    object-fit: contain;
    background: #000000;
    display: block;
  }

  /* Suppress Chrome's native overlay play button scrim on hover */
  #modal-video::-webkit-media-controls-overlay-enclosure { display: none !important; }

  /* Player Buffering / Loading State */
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

  /* Stream Error / Timeout Overlay */
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
    max-width: 380px;
    line-height: 1.4;
  }

  .error-actions {
    display: flex;
    gap: 10px;
    margin-top: 4px;
  }

  .retry-stream-btn {
    padding: 7px 14px;
    font-size: 12.5px;
    font-weight: 600;
    border-radius: var(--radius-md);
    background: var(--accent);
    color: #ffffff;
    border: none;
    cursor: pointer;
  }

  /* Modal Footer Controls Bar */
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
    padding: 0 12px;
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

  /* Keyboard Legend Bar */
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

  /* Back to Top Floating Button */
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
    transform: translateY(-2px);
  }

  /* Mobile Responsive Tweaks */
  @media (max-width: 640px) {
    header { padding: 8px 12px; }
    .nav-container { gap: 8px; }
    .controls-group { min-width: 100%; justify-content: stretch; }
    .search-wrapper { max-width: 100%; }
    .select-wrapper { flex: 1; }
    #neighborhood-filter { width: 100%; }
    .modal-dialog { max-height: 98vh; }
    .modal-footer { justify-content: center; }
    .action-tools-group { width: 100%; justify-content: center; }
    .keyboard-legend { display: none; }
  }
</style>
</head>
<body>

<header>
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
        <select id="neighborhood-filter">
          <option value="">All neighborhoods</option>
        </select>
        <svg class="select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </div>

      <div class="quick-filters">
        <button id="fav-filter-btn" class="filter-tab-btn fav-tab" title="Toggle favorites filter">
          <span>★</span> Favorites <span id="fav-count-pill" class="tab-count"></span>
        </button>
        <button id="hide-offline-btn" class="filter-tab-btn" title="Toggle offline cameras">
          Hide offline
        </button>
      </div>

      <div class="density-group" title="Grid display density">
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

      <button id="theme-toggle-btn" title="Toggle theme (Light / Dark / Auto)">
        <svg id="theme-icon-moon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
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

<div id="modal">
  <div class="modal-dialog">
    <div class="modal-header">
      <div class="modal-header-info">
        <div class="modal-title-row">
          <div id="modal-title">Camera Feed</div>
          <span class="modal-live-indicator"><span class="live-dot"></span> LIVE</span>
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

    <div class="video-viewport-wrapper">
      <video id="modal-video" controls autoplay playsinline muted></video>

      <div id="player-spinner" class="player-spinner-overlay">
        <div class="spinner-ring"></div>
        <span>Connecting to live SDOT stream…</span>
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
          <a id="btn-error-direct" class="modal-btn" href="#" target="_blank">Open Direct Stream</a>
        </div>
      </div>
    </div>

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
        <a id="btn-open-direct" class="modal-btn primary-action" href="#" target="_blank" title="Open direct .m3u8 stream in VLC or new tab">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
            <polyline points="15 3 21 3 21 9"></polyline>
            <line x1="10" y1="14" x2="21" y2="3"></line>
          </svg>
          Direct Stream
        </a>
      </div>
    </div>

    <div class="keyboard-legend">
      Shortcuts: <kbd>←</kbd> <kbd>→</kbd> Navigate &nbsp;·&nbsp; <kbd>Space</kbd> Play/Pause &nbsp;·&nbsp; <kbd>F</kbd> Fullscreen &nbsp;·&nbsp; <kbd>P</kbd> PiP &nbsp;·&nbsp; <kbd>C</kbd> Copy Link &nbsp;·&nbsp; <kbd>Esc</kbd> Close
    </div>
  </div>
</div>

<button id="back-to-top" title="Back to top">
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="18 15 12 9 6 15"></polyline>
  </svg>
</button>

<script>
const CAMERAS = __DATA_JSON__;
const WOWZA_TEMPLATE = "https://61e0c5d388c2e.streamlock.net:443/live/{stream}/playlist.m3u8";
const THUMB_BASE = "https://www.seattle.gov/trafficcams/images/";
const FAVORITES_KEY = "sc-favorites";
const FILTERS_KEY = "sc-filters";
const SCROLL_KEY = "sc-scroll";
const DENSITY_KEY = "sc-density";
const THEME_KEY = "sc-theme";

let filtered = CAMERAS.slice();
let currentIndex = -1;
let hls = null;
let subInterval = null;
let streamTimeoutTimer = null;
let onlyFavorites = false;
let hideOffline = false;
let currentDensity = localStorage.getItem(DENSITY_KEY) || "normal";
let currentTheme = localStorage.getItem(THEME_KEY) || "auto";

const offlineIds = new Set();
const lastConfirmedAt = new Map();
const camById = new Map(CAMERAS.map(c => [c.Id, c]));

function applyTheme(theme) {
  currentTheme = theme;
  localStorage.setItem(THEME_KEY, theme);
  const moon = document.getElementById("theme-icon-moon");
  const sun = document.getElementById("theme-icon-sun");

  if (theme === "light") {
    document.documentElement.setAttribute("data-theme", "light");
    moon.style.display = "none";
    sun.style.display = "block";
  } else if (theme === "dark") {
    document.documentElement.setAttribute("data-theme", "dark");
    moon.style.display = "block";
    sun.style.display = "none";
  } else {
    document.documentElement.removeAttribute("data-theme");
    const isLight = window.matchMedia("(prefers-color-scheme: light)").matches;
    moon.style.display = isLight ? "none" : "block";
    sun.style.display = isLight ? "block" : "none";
  }
}

function toggleTheme() {
  if (currentTheme === "auto") {
    const isLight = window.matchMedia("(prefers-color-scheme: light)").matches;
    applyTheme(isLight ? "dark" : "light");
  } else if (currentTheme === "dark") {
    applyTheme("light");
  } else {
    applyTheme("dark");
  }
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

function updateModalSub(cam) {
  let meta = cam.Neighborhood + " · Camera " + cam.Id;
  const t = lastConfirmedAt.get(cam.Id);
  if (t) {
    meta += " · Confirmed live " + formatAgo(Date.now() - t);
  }
  document.getElementById("modal-sub").textContent = meta;

  const favBtnText = document.getElementById("modal-fav-text");
  const isFav = favorites.has(cam.Id);
  favBtnText.textContent = isFav ? "Favorited" : "Favorite";
  const modalFavBtn = document.getElementById("btn-modal-fav");
  modalFavBtn.classList.toggle("active-fav", isFav);
}

function loadFavorites() {
  try { return new Set(JSON.parse(localStorage.getItem(FAVORITES_KEY) || "[]")); }
  catch { return new Set(); }
}
const favorites = loadFavorites();

function saveFavorites() {
  localStorage.setItem(FAVORITES_KEY, JSON.stringify([...favorites]));
  updateFavBadge();
}

function toggleFavorite(id) {
  if (favorites.has(id)) {
    favorites.delete(id);
  } else {
    favorites.add(id);
  }
  saveFavorites();
  if (currentIndex >= 0 && filtered[currentIndex]) {
    updateModalSub(filtered[currentIndex]);
  }
  render();
}

function updateFavBadge() {
  const pill = document.getElementById("fav-count-pill");
  const count = favorites.size;
  pill.textContent = count > 0 ? "(" + count + ")" : "";
  const favBtn = document.getElementById("fav-filter-btn");
  favBtn.classList.toggle("active", onlyFavorites);
}

function saveFilterState() {
  const state = {
    q: document.getElementById("search").value,
    hood: document.getElementById("neighborhood-filter").value,
    hideOffline: hideOffline,
    onlyFavorites: onlyFavorites,
  };
  localStorage.setItem(FILTERS_KEY, JSON.stringify(state));

  // Sync with URL query parameters for shareability
  const params = new URLSearchParams(location.search);
  if (state.q) params.set("q", state.q); else params.delete("q");
  if (state.hood) params.set("hood", state.hood); else params.delete("hood");
  if (state.onlyFavorites) params.set("fav", "1"); else params.delete("fav");
  if (state.hideOffline) params.set("liveonly", "1"); else params.delete("liveonly");

  const newUrl = location.pathname + (params.toString() ? "?" + params.toString() : "");
  history.replaceState(null, "", newUrl);
}

function restoreFilterState() {
  const params = new URLSearchParams(location.search);
  let state;
  try { state = JSON.parse(localStorage.getItem(FILTERS_KEY) || "null"); }
  catch { state = null; }

  const q = params.get("q") || (state && state.q) || "";
  const hood = params.get("hood") || (state && state.hood) || "";
  const hasFav = params.has("fav") ? params.get("fav") === "1" : (state ? !!state.onlyFavorites : false);
  const hasHideOffline = params.has("liveonly") ? params.get("liveonly") === "1" : (state ? !!state.hideOffline : false);

  if (q) {
    document.getElementById("search").value = q;
    document.getElementById("search-box").classList.add("has-val");
  }
  if (hood) document.getElementById("neighborhood-filter").value = hood;
  onlyFavorites = hasFav;
  hideOffline = hasHideOffline;
  document.getElementById("hide-offline-btn").classList.toggle("active", hideOffline);
}

function streamUrl(cam) {
  return WOWZA_TEMPLATE.replace("{stream}", cam.StreamName);
}

function thumbUrl(cam) {
  return THUMB_BASE + cam.ImageUrl + "?t=" + Date.now();
}

function buildNeighborhoodOptions() {
  const sel = document.getElementById("neighborhood-filter");
  const hoods = [...new Set(CAMERAS.map(c => c.Neighborhood))].sort();
  for (const h of hoods) {
    const count = CAMERAS.filter(c => c.Neighborhood === h).length;
    const opt = document.createElement("option");
    opt.value = h;
    opt.textContent = `${h} (${count})`;
    sel.appendChild(opt);
  }
}

function setDensity(density) {
  currentDensity = density;
  localStorage.setItem(DENSITY_KEY, density);
  document.getElementById("btn-density-compact").classList.toggle("active", density === "compact");
  document.getElementById("btn-density-normal").classList.toggle("active", density === "normal");
  document.querySelectorAll(".grid").forEach(g => {
    g.classList.toggle("compact", density === "compact");
  });
}

function buildCard(cam) {
  const card = document.createElement("div");
  const isOffline = offlineIds.has(cam.Id);
  card.className = "card" + (isOffline ? " offline" : "");
  card.dataset.id = cam.Id;
  card.tabIndex = 0;
  const isFav = favorites.has(cam.Id);

  card.innerHTML = `
    <div class="thumb-wrap">
      <img loading="lazy" src="${thumbUrl(cam)}" alt="">
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
      <button class="fav-btn${isFav ? ' active' : ''}" title="${isFav ? 'Remove from favorites' : 'Add to favorites'}" aria-label="Favorite">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="${isFav ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2">
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
        </svg>
      </button>
      <span class="badge-status ${isOffline ? 'offline' : ''}">
        <span class="badge-dot"></span>${isOffline ? 'OFFLINE' : 'LIVE'}
      </span>
    </div>
    <div class="card-label">
      <div class="card-desc">${cam.Description}</div>
      <div class="card-meta-row">
        <span>${cam.Neighborhood}</span>
        <span class="card-id-tag">${cam.Id}</span>
      </div>
    </div>`;

  const img = card.querySelector("img");
  const placeholder = card.querySelector(".thumb-placeholder");

  img.addEventListener("load", () => {
    // 352x240 placeholder check: SDOT serves 352x240 for maintenance graphics
    if (img.naturalWidth === 352 && img.naturalHeight === 240) {
      img.style.display = "none";
      placeholder.style.display = "flex";
    } else {
      img.style.display = "block";
      placeholder.style.display = "none";
    }
  });

  img.addEventListener("error", () => {
    img.style.display = "none";
    placeholder.style.display = "flex";
    const retries = Number(img.dataset.retries || 0);
    if (retries < 2) {
      img.dataset.retries = retries + 1;
      setTimeout(() => {
        const retryImg = new Image();
        retryImg.onload = () => {
          if (retryImg.naturalWidth === 352 && retryImg.naturalHeight === 240) {
            img.style.display = "none";
            placeholder.style.display = "flex";
          } else {
            img.src = retryImg.src;
            img.style.display = "block";
            placeholder.style.display = "none";
          }
        };
        retryImg.src = thumbUrl(cam);
      }, 2500 * (retries + 1));
    }
  });

  card.querySelector(".fav-btn").addEventListener("click", (e) => {
    e.stopPropagation();
    toggleFavorite(cam.Id);
  });

  card.addEventListener("click", () => openModal(cam));
  card.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      openModal(cam);
    }
  });

  return card;
}

function appendSection(main, heading, cams, isFavSection = false) {
  if (cams.length === 0) return;
  const section = document.createElement("div");
  section.className = "neighborhood-section";

  const row = document.createElement("div");
  row.className = "neighborhood-heading-row";

  const h = document.createElement("div");
  h.className = "neighborhood-title" + (isFavSection ? " fav-heading" : "");
  h.innerHTML = `${isFavSection ? '★ ' : ''}${heading} <span class="heading-count-badge">(${cams.length})</span>`;
  row.appendChild(h);

  const divider = document.createElement("div");
  divider.className = "heading-divider";
  row.appendChild(divider);

  section.appendChild(row);

  const grid = document.createElement("div");
  grid.className = "grid" + (currentDensity === "compact" ? " compact" : "");
  for (const cam of cams) {
    grid.appendChild(buildCard(cam));
  }
  section.appendChild(grid);
  main.appendChild(section);
}

function render() {
  const main = document.getElementById("main");
  main.innerHTML = "";

  let visible = filtered.slice();
  if (hideOffline) {
    visible = visible.filter(c => !offlineIds.has(c.Id));
  }
  if (onlyFavorites) {
    visible = visible.filter(c => favorites.has(c.Id));
  }

  if (visible.length === 0) {
    const isFavEmpty = onlyFavorites && favorites.size === 0;
    main.innerHTML = `
      <div class="empty-state">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          ${isFavEmpty ? '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>' : '<circle cx="12" cy="12" r="10"></circle><line x1="8" y1="12" x2="16" y2="12"></line>'}
        </svg>
        <div class="empty-title">${isFavEmpty ? 'No favorites saved yet' : 'No cameras found'}</div>
        <div class="empty-msg">${isFavEmpty ? 'Click the star icon on any traffic camera card to add it to your pinned favorites list.' : 'No active traffic cameras matched your current search filters or favorites selection.'}</div>
        <button class="reset-filters-btn" id="btn-reset-filters">${isFavEmpty ? 'Show All Cameras' : 'Reset All Filters'}</button>
      </div>`;
    document.getElementById("btn-reset-filters").addEventListener("click", () => {
      document.getElementById("search").value = "";
      document.getElementById("search-box").classList.remove("has-val");
      document.getElementById("neighborhood-filter").value = "";
      onlyFavorites = false;
      hideOffline = false;
      document.getElementById("hide-offline-btn").classList.remove("active");
      applyFilters();
    });
    document.getElementById("visible-count").textContent = `0 / ${CAMERAS.length} Cameras`;
    return;
  }

  const favCams = visible.filter(c => favorites.has(c.Id));
  if (favCams.length > 0 && !onlyFavorites) {
    appendSection(main, "Favorites", favCams, true);
  }

  const rest = onlyFavorites ? favCams : visible.filter(c => !favorites.has(c.Id));
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

  document.getElementById("visible-count").textContent = `${visible.length} of ${CAMERAS.length} Cameras`;
  updateFavBadge();
}

function renderFilterIndicator() {
  const el = document.getElementById("filter-indicator");
  el.innerHTML = "";
  const hood = document.getElementById("neighborhood-filter").value;
  const q = document.getElementById("search").value.trim();
  let hasFilters = false;

  if (hood) {
    hasFilters = true;
    const chip = document.createElement("button");
    chip.className = "filter-chip";
    chip.innerHTML = `<span>${hood}</span> <span class="filter-chip-remove">✕</span>`;
    chip.title = "Clear neighborhood filter";
    chip.addEventListener("click", () => {
      document.getElementById("neighborhood-filter").value = "";
      applyFilters();
    });
    el.appendChild(chip);
  }

  if (q) {
    hasFilters = true;
    const chip = document.createElement("button");
    chip.className = "filter-chip";
    chip.innerHTML = `<span>“${q}”</span> <span class="filter-chip-remove">✕</span>`;
    chip.title = "Clear search";
    chip.addEventListener("click", () => {
      document.getElementById("search").value = "";
      document.getElementById("search-box").classList.remove("has-val");
      applyFilters();
    });
    el.appendChild(chip);
  }

  if (onlyFavorites) {
    hasFilters = true;
    const chip = document.createElement("button");
    chip.className = "filter-chip";
    chip.innerHTML = `<span>★ Favorites Only</span> <span class="filter-chip-remove">✕</span>`;
    chip.title = "Show all cameras";
    chip.addEventListener("click", () => {
      onlyFavorites = false;
      applyFilters();
    });
    el.appendChild(chip);
  }

  if (hideOffline) {
    hasFilters = true;
    const chip = document.createElement("button");
    chip.className = "filter-chip";
    chip.innerHTML = `<span>Hide Offline</span> <span class="filter-chip-remove">✕</span>`;
    chip.title = "Show offline cameras";
    chip.addEventListener("click", () => {
      hideOffline = false;
      document.getElementById("hide-offline-btn").classList.remove("active");
      applyFilters();
    });
    el.appendChild(chip);
  }

  if (hasFilters) {
    const clearBtn = document.createElement("button");
    clearBtn.className = "clear-all-link";
    clearBtn.textContent = "Clear all";
    clearBtn.addEventListener("click", () => {
      document.getElementById("search").value = "";
      document.getElementById("search-box").classList.remove("has-val");
      document.getElementById("neighborhood-filter").value = "";
      onlyFavorites = false;
      hideOffline = false;
      document.getElementById("hide-offline-btn").classList.remove("active");
      applyFilters();
    });
    el.appendChild(clearBtn);
  }
}

function applyFilters() {
  const q = document.getElementById("search").value.trim().toLowerCase();
  const hood = document.getElementById("neighborhood-filter").value;

  filtered = CAMERAS.filter(c => {
    if (hood && c.Neighborhood !== hood) return false;
    if (q && !(c.Description.toLowerCase().includes(q) || c.Neighborhood.toLowerCase().includes(q) || c.Id.toLowerCase().includes(q))) return false;
    return true;
  });

  saveFilterState();
  renderFilterIndicator();
  render();
}

function showModalError(msg, cam) {
  const errEl = document.getElementById("modal-error");
  const msgEl = document.getElementById("modal-error-msg");
  const spinner = document.getElementById("player-spinner");
  spinner.style.display = "none";
  msgEl.textContent = msg;
  document.getElementById("btn-error-direct").href = streamUrl(cam);
  errEl.style.display = "flex";
}

function openModal(cam) {
  currentIndex = filtered.indexOf(cam);
  const modal = document.getElementById("modal");
  const video = document.getElementById("modal-video");
  const errEl = document.getElementById("modal-error");
  const spinner = document.getElementById("player-spinner");

  errEl.style.display = "none";
  spinner.style.display = "flex";
  document.getElementById("modal-title").textContent = cam.Description;
  updateModalSub(cam);
  document.getElementById("btn-open-direct").href = streamUrl(cam);

  const params = new URLSearchParams(location.search);
  params.set("cam", cam.Id);
  history.replaceState(null, "", location.pathname + "?" + params.toString());

  if (hls) { hls.destroy(); hls = null; }
  if (subInterval) clearInterval(subInterval);
  if (streamTimeoutTimer) clearTimeout(streamTimeoutTimer);

  subInterval = setInterval(() => updateModalSub(cam), 10000);

  // 12-second stream watchdog timer
  streamTimeoutTimer = setTimeout(() => {
    if (video.paused && video.currentTime === 0) {
      showModalError("Live feed connection timed out. Camera may be temporarily offline.", cam);
      offlineIds.add(cam.Id);
    }
  }, 12000);

  video.onplaying = () => {
    if (streamTimeoutTimer) clearTimeout(streamTimeoutTimer);
    spinner.style.display = "none";
    errEl.style.display = "none";
    lastConfirmedAt.set(cam.Id, Date.now());
    updateModalSub(cam);
  };

  const url = streamUrl(cam);

  // Safari Native HLS Support Check (Always check first to avoid hls.js MSE stall bug on Safari)
  if (video.canPlayType("application/vnd.apple.mpegurl")) {
    video.src = url;
    video.play().catch(() => {});
  } else if (Hls.isSupported()) {
    hls = new Hls({ capLevelToPlayerSize: false, startLevel: -1 });
    hls.loadSource(url);
    hls.attachMedia(video);
    video.play().catch(() => {});

    hls.on(Hls.Events.MANIFEST_PARSED, () => {
      if (hls.levels && hls.levels.length > 1) {
        hls.currentLevel = hls.levels.length - 1;
      }
      video.play().catch(() => {});
    });

    let hlsRetries = 0;
    hls.on(Hls.Events.ERROR, (event, data) => {
      if (!data.fatal) return;
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
      offlineIds.add(cam.Id);
      showModalError("Live stream is not responding (camera may be offline).", cam);
    });
  } else {
    showModalError("This browser cannot play HLS streams directly.", cam);
  }

  modal.classList.add("open");
}

function closeModal() {
  document.getElementById("modal").classList.remove("open");
  const video = document.getElementById("modal-video");
  video.pause();
  video.removeAttribute("src");
  video.load();
  video.onplaying = null;
  if (hls) { hls.destroy(); hls = null; }
  if (subInterval) { clearInterval(subInterval); subInterval = null; }
  if (streamTimeoutTimer) { clearTimeout(streamTimeoutTimer); streamTimeoutTimer = null; }

  const params = new URLSearchParams(location.search);
  params.delete("cam");
  const newUrl = location.pathname + (params.toString() ? "?" + params.toString() : "");
  history.replaceState(null, "", newUrl);
}

function step(delta) {
  if (currentIndex === -1 || filtered.length === 0) return;
  let idx = (currentIndex + delta + filtered.length) % filtered.length;
  openModal(filtered[idx]);
}

// Event Listeners
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

document.getElementById("hide-offline-btn").addEventListener("click", () => {
  hideOffline = !hideOffline;
  document.getElementById("hide-offline-btn").classList.toggle("active", hideOffline);
  applyFilters();
});

document.getElementById("btn-density-compact").addEventListener("click", () => setDensity("compact"));
document.getElementById("btn-density-normal").addEventListener("click", () => setDensity("normal"));
document.getElementById("theme-toggle-btn").addEventListener("click", toggleTheme);

document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("btn-prev").addEventListener("click", () => step(-1));
document.getElementById("btn-next").addEventListener("click", () => step(1));
document.getElementById("btn-retry-stream").addEventListener("click", () => {
  if (currentIndex >= 0 && filtered[currentIndex]) {
    openModal(filtered[currentIndex]);
  }
});

document.getElementById("btn-modal-fav").addEventListener("click", () => {
  if (currentIndex >= 0 && filtered[currentIndex]) {
    toggleFavorite(filtered[currentIndex].Id);
  }
});

document.getElementById("btn-fullscreen").addEventListener("click", () => {
  const video = document.getElementById("modal-video");
  if (!document.fullscreenElement) {
    if (video.requestFullscreen) video.requestFullscreen();
    else if (video.webkitRequestFullscreen) video.webkitRequestFullscreen();
  } else {
    if (document.exitFullscreen) document.exitFullscreen();
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

document.getElementById("btn-copy-link").addEventListener("click", async () => {
  const cam = filtered[currentIndex];
  if (!cam) return;
  const deepLink = new URL(location.href);
  deepLink.searchParams.set("cam", cam.Id);
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

document.getElementById("modal").addEventListener("click", (e) => {
  if (e.target.id === "modal") closeModal();
});

document.addEventListener("keydown", (e) => {
  const modalOpen = document.getElementById("modal").classList.contains("open");
  if (modalOpen) {
    if (e.key === "Escape") closeModal();
    if (e.key === "ArrowRight") step(1);
    if (e.key === "ArrowLeft") step(-1);
    if (e.key === " ") {
      e.preventDefault();
      const video = document.getElementById("modal-video");
      if (video.paused) video.play().catch(() => {});
      else video.pause();
    }
    if (e.key === "f" || e.key === "F") {
      e.preventDefault();
      document.getElementById("btn-fullscreen").click();
    }
    if (e.key === "p" || e.key === "P") {
      e.preventDefault();
      document.getElementById("btn-pip").click();
    }
    if (e.key === "c" || e.key === "C") {
      e.preventDefault();
      document.getElementById("btn-copy-link").click();
    }
    return;
  }

  if (e.key === "/") {
    const tag = document.activeElement.tagName;
    if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
    e.preventDefault();
    document.getElementById("search").focus();
  }
});

// Scroll to Top & Scroll Persistence
const backToTopBtn = document.getElementById("back-to-top");
window.addEventListener("scroll", () => {
  backToTopBtn.classList.toggle("visible", window.scrollY > 350);
  clearTimeout(window._scrollSaveTimer);
  window._scrollSaveTimer = setTimeout(() => {
    localStorage.setItem(SCROLL_KEY, String(window.scrollY));
  }, 200);
}, { passive: true });

backToTopBtn.addEventListener("click", () => {
  window.scrollTo({ top: 0, behavior: "smooth" });
});

// Initialize
applyTheme(currentTheme);
buildNeighborhoodOptions();
restoreFilterState();
setDensity(currentDensity);
applyFilters();

const deepLinkId = new URL(location.href).searchParams.get("cam");
const deepLinkCam = deepLinkId && camById.get(deepLinkId);
if (deepLinkCam) {
  openModal(deepLinkCam);
} else {
  const savedScroll = Number(localStorage.getItem(SCROLL_KEY) || 0);
  if (savedScroll > 0) window.scrollTo(0, savedScroll);
}
</script>
</body>
</html>
"""

html = html.replace("__DATA_JSON__", data_json)

out_path = "index.html"
with open(out_path, "w") as f:
    f.write(html)
print(f"wrote {out_path} ({len(html)} bytes)")
