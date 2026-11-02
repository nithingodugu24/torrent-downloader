# Torrent Downloader

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

The owner uses Torrent Downloader personally on their local computer to manage authorized torrents, monitor transfers, and stream video to VLC. Personal local use was confirmed during initialization on 2026-11-02.

## Product Purpose

Provide a private local workspace for adding and managing torrent transfers, understanding their current state, and accessing downloaded files or preparing VLC playback while a video is downloading. Success means completing these tasks with clear status and actionable feedback.

## Operating Context

- Browser-based React and TypeScript frontend served with Vite; FastAPI backend with a libtorrent runtime.
- Default local development addresses: frontend `http://127.0.0.1:5173`, backend `http://127.0.0.1:8000`.
- Start the frontend with `npm run dev` from `frontend`; build it with `npm run build` there.
- Progress updates arrive through WebSocket messages. SQLite persists task state by default.
- VLC playback uses a prepared HTTP stream URL pasted into VLC's network-stream dialog. Playback and seeking may buffer while pieces download.

## Capabilities and Constraints

- Add tasks using magnet URIs or `.torrent` uploads.
- Search, filter, and sort transfers; inspect progress, size, speeds, peers, seeds, and ratio.
- Resume, pause, stop, recheck, and remove transfers.
- Inspect files and task events; download available files and prepare supported video streams.
- Configure category, priority, bandwidth caps, maximum connections, and sequential downloading per task.
- Preserve existing task data and backend behavior during interface work.
- Torrent data and browser downloads must stay within the configured storage root.
- The project is intended for legal, user-authorized torrents. It does not provide torrent search, DRM circumvention, or copyright bypass features.
- Local/private deployment is the established context; public hosting and multi-user authentication are not confirmed requirements.

## Brand Commitments

Preserve the existing product name, Torrent Downloader. The owner requested Impeccable for future interface design work. No additional binding visual direction was established during initialization.

## Evidence on Hand

- `README.md`: product capabilities, setup, deployment boundaries, VLC workflow, and configuration.
- `frontend/src/`: implemented dashboard, transfer controls, add-torrent dialog, detail drawer, and API integration.
- `backend/app/`: FastAPI routes, torrent service, storage constraints, and runtime engine.
- `tests/`: backend unit and integration checks.
- `output/ui/`: local previews captured during the preceding UI update; these are implementation snapshots, not independent design specifications.
- No customer testimonials, adoption metrics, performance benchmarks, or commercial claims were supplied. Do not fabricate them.

## Product Principles

- Keep personal local transfer management central to product decisions.
- Show real transfer state clearly and provide useful feedback when operations fail.
- Preserve the complete transfer and VLC workflows when simplifying the interface.
- Keep private local operation and configured storage boundaries intact.

## Open Decisions

No product-specific accessibility standard, public deployment requirement, or additional audience was confirmed. Basic keyboard access and responsive browser behavior remain implementation quality requirements.
