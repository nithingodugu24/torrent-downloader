---
version: 1
slug: "frontend-src-app-tsx"
primary_target: "frontend/src/App.tsx"
related_targets: ["frontend/src/styles/redesign.css","frontend/src/components/TorrentSearch.tsx"]
---

# Torrent Downloader UI

Mode: Operate.

## Direction contract

THESIS: Adopt the user-supplied torrent-downloader-redesigned.zip interface while preserving the current working app.

OWN-WORLD: Slate sidebar, royal-blue actions, cool pale background, white panels, restrained borders, system UI type, compact tables and softly rounded controls from the supplied redesign.css.

STORY: The owner can inspect transfers, add torrents, prepare VLC playback, and find downloads across five progressively loaded sources with understandable availability labels.

FIRST VIEWPORT: Preserve the supplied fixed sidebar, topbar, Transfer center heading, four summary panels and transfer queue. Keep Find torrents in the sidebar and apply the same control and surface styling to its dedicated view.

FORM: User-pinned source UI; no direction round is needed. seed: none (unavailable). Reference lives in .runtime/redesign-reference/; screenshot in .impeccable/review/reference-desktop.jpg.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

Constraints: Preserve live data and backend behavior. Never replace current backend, API, launcher, tests or progressive-search logic with older archive files. Keep source estimates qualified and controls keyboard accessible.
