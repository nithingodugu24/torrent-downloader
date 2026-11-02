# Torrent Downloader

A local torrent manager with a browser dashboard. Add magnet links or `.torrent` files, follow live transfer progress, and stream supported videos to VLC while they download.

Use torrents you own or have permission to download. The app runs locally and includes internal search across Bitsearch, UIndex, LimeTorrents, The Pirate Bay, and TorrentDownload.

## Quick start on Windows

### Install these once

- [64-bit Python 3.11](https://www.python.org/downloads/) (recommended). During installation, enable **Add python.exe to PATH**.
- [Node.js 20 or newer](https://nodejs.org/), including npm.
- [VLC](https://www.videolan.org/vlc/) only if you want video playback.

### Start the app

1. Download or clone this project and extract it into a normal folder.
2. Double-click **`start.bat`**.
3. Wait for the first-time setup to finish. The launcher downloads Python requirements (including libtorrent), installs frontend dependencies, and builds the dashboard.
4. Your browser opens automatically. The default address is **[http://127.0.0.1:8000](http://127.0.0.1:8000)**; if that port is busy, the launcher picks another available port and prints the correct address.

**No `.env` file, database setup, manual pip/npm commands, or environment activation is needed.** The launcher manages a private `.venv` automatically and uses local defaults.

Keep the launcher window open while using the app. Press **Ctrl+C** there to stop it and allow transfer state to save. Start it again with the same `start.bat`; unchanged dependencies and UI builds are reused. Internet is needed for first-time installation and downloading torrents, but unchanged setup does not reinstall packages.

If PowerShell is your starting point:

```powershell
.\start.bat
```

No manual port changes are needed. If another service is using port 8000, the launcher chooses a free port automatically and remembers it. Starting the launcher again reopens the running app; after stopping it, the next launch tries the remembered port first.

## Linux and macOS

Install Python 3.11 or newer and Node.js 20 or newer, then run from the project folder:

```bash
python3 start.py
```

The launcher follows the same automatic setup process. On systems where Python's venv support is packaged separately, install it first (for example, `sudo apt install python3-venv` on Debian/Ubuntu). Libtorrent must have a compatible binary wheel for your Python and operating system; 64-bit Python 3.11 is the recommended starting point.

## Using the dashboard

- **Add a transfer:** choose **Add torrent**, paste a magnet link or select a `.torrent` file, then submit. Open **Transfer options** only if you need a category, destination, priority, or sequential downloading.
- **Search torrents:** open **Find torrents** in the sidebar, enter keywords, choose a source or **All sources**, and select **Find torrents**. Results are sorted by estimated availability, with plain-language labels such as **Well shared**, **May be slow**, and **May not finish**. **Download** adds a transfer using its magnet link. Expand **Source counts** for raw seed/peer numbers. Availability comes from site-reported counts and cannot guarantee speed or completion. Results appear as each source responds, while slower sources continue searching. Source progress, outages, and blocks appear beside the results. You can use **Stop search** to keep the results already loaded, or start another search without waiting. Search terms are sent to the selected sites.
- **Find transfers:** use the sidebar filters, search box, status selector, and sort controls.
- **Manage a transfer:** pause/resume it from the row. The more-actions menu contains stop, recheck, and remove.
- **Estimate download time:** transfers show time remaining from their actual download speed. Search results show signal bars for estimated availability; optionally enter your internet speed in Mbps for a rough time estimate before starting. Missing metadata, paused transfers, and stalled downloads show their state instead of a countdown.
- **Inspect it:** select its name to open **Overview**, **Files**, and **Activity**. Transfer settings are available under Overview.
- **Download a file:** use its download link in Files when available.

### Watch in VLC while downloading

1. Open a transfer's **Overview** and choose **Stream in VLC**.
2. Wait for the initial video buffer, then copy the stream URL.
3. In VLC, press **Ctrl+N**, paste the URL, and select **Play**.
4. For a torrent with multiple videos, choose **Stream** beside the desired video in **Files**.

Video options appear after metadata arrives. Streaming enables sequential downloading and resumes paused transfers. Playback and seeking can buffer when pieces or seeds are unavailable. Keep the app and torrent running; if a stream times out, prepare it again. Localhost URLs work on the same computer as the app.

## Useful launcher options

```powershell
# Install/build without opening or starting the app
.\start.bat --setup-only

# Start without opening a browser
.\start.bat --no-browser

# Prefer a particular port (automatically falls back if busy)
.\start.bat --port 8001

# Rebuild the dashboard
.\start.bat --rebuild
```

The same options work with `python start.py` or `python3 start.py`. Re-running the launcher while its app is already running reopens the existing app. To use rebuilt code, stop the running app and restart it.

## Your files and settings

| Folder | Contents | Keep it? |
| --- | --- | --- |
| `downloads/` | Downloaded and partially downloaded files | Yes |
| `state/` | Task database and resume information | Yes |
| `torrent-files/` | Uploaded torrent sources needed to restore tasks | Yes |
| `.venv/` | Automatically installed Python packages | Recreated by the launcher if missing |
| `.runtime/` | Setup/build fingerprints | Recreated automatically |
| `frontend/dist/` | Built dashboard served by the app | Rebuilt automatically if missing |
| `frontend/node_modules/` | Frontend build dependencies | Reinstalled when the UI needs a build |

The existing database filename is retained for compatibility with older installations. Renaming the app does not create a new database or discard transfers.

### Optional configuration

Defaults are enough for local use. Advanced users may copy `.env.example` to `.env` and change storage paths, bandwidth limits, connection limits, or database settings. Existing environment variables take precedence over `.env` values. No file is copied or overwritten automatically.

The app binds to `127.0.0.1`. Public hosting and authentication are outside the default setup.

## Docker alternative

With Docker and Compose installed:

```bash
docker compose up --build
```

Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)**. The image builds the dashboard and runs it together with the API. Python and Node do not need to be installed on the host, and no `.env` file is required. Downloads, state, and torrent sources persist in the mounted folders.

Stop with **Ctrl+C**, or use `docker compose down` after running in detached mode. Add advanced environment overrides to the `app` service's `environment` section when needed.

## Troubleshooting

| Problem | What to do |
| --- | --- |
| Python was not found | Install 64-bit Python 3.11 with the PATH option, then reopen the launcher. |
| Node/npm was not found | Install Node.js 20 or newer, then reopen the terminal or launcher. |
| Installation failed | Read the first error in the launcher window. Check internet access, proxy/firewall settings, and available disk space, then retry. |
| No matching libtorrent distribution | Use 64-bit Python 3.11. Binary support varies by platform; the launcher avoids compiling libtorrent from source. |
| Port 8000 is in use | No action needed: the launcher selects an available port, remembers it, and opens the correct address. Other processes are left running. |
| Browser did not open | Visit the address printed in the launcher window. |
| Setup needs repairing | Stop the app, delete `.venv` and `.runtime`, then run the launcher again. Keep `downloads`, `state`, and `torrent-files`. |
| No download progress | Check the transfer status, available seeds, internet connection, and any bandwidth limits. |
| VLC buffers or cannot open a link | Prepare the stream again, check seeds/speed, and keep the app running on the same computer. |

## Development

The regular launcher serves a production UI build from FastAPI. For frontend hot reload, run the backend and Vite separately:

```powershell
# First install normal app requirements/build
.\start.bat --setup-only

# Terminal 1: backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# Terminal 2: frontend (http://127.0.0.1:5173)
cd frontend
npm run dev
```

Install optional development tools and run checks from the project root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check backend tests start.py
npm --prefix frontend run build
```

`backend/` contains FastAPI and the torrent engine; `frontend/src/` contains the React UI; `tests/` contains service, API, streaming, and launcher checks. `.agents`, `.codex`, and `.impeccable` contain the configured development/design tooling, not app data. Test caches, old logs, build metadata, and cache archives are generated files and do not belong in source control.
