# UWSLeech

UWSLeech is a local/private torrent management web app for legal, user-authorized torrents only. It provides a FastAPI backend, a React dashboard, WebSocket progress updates, SQLite persistence by default, and a libtorrent-backed runtime engine.

This project does not include torrent search, copyright bypass tooling, DRM circumvention, or any feature intended to help unauthorized downloading.

## Features

- Add legal torrents by magnet URI or `.torrent` upload.
- Start, pause, resume, stop, remove, and recheck tasks.
- Live status, progress, speeds, ratio, peers, seeds, files, and task logs.
- Per-task category, priority, bandwidth caps, max connections, and sequential mode.
- Stream video to VLC while downloading, with copyable URLs and HTTP seeking support.
- SQLite local database with PostgreSQL-ready async SQLAlchemy configuration.
- Safe storage-root enforcement for torrent files and browser downloads.
- Docker and docker-compose support for private/local deployment.

## Local Setup

Create an environment file:

```powershell
Copy-Item .env.example .env
```

Install backend dependencies:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Install libtorrent Python bindings for your platform. The package name differs across environments:

```powershell
pip install libtorrent
```

On Debian/Ubuntu-based systems:

```bash
sudo apt install python3-libtorrent
```

With Conda:

```bash
conda install -c conda-forge libtorrent
```

Run the backend:

```powershell
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Run the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173).

## Stream to VLC while downloading

Add a magnet or `.torrent`, then select **Stream in VLC** in its details. For torrents
with multiple videos, use **Stream** beside the file you want. Video options appear
after torrent metadata arrives. Streaming enables sequential downloading and resumes
paused torrents. Copy the displayed URL, press **Ctrl+N** in VLC, paste it, and play.

The server waits for verified downloaded pieces and prioritizes the requested video
position, including when VLC seeks to the end for container metadata. Startup and
seeking may buffer; playback needs enough available seeds and download speed to keep
up with the video bitrate. If a piece is unavailable for two minutes, reopen the URL
to retry. Keep the app server and torrent running. URLs use the configured API origin
or the dashboard's origin; localhost URLs work on the same computer as the server.

## Docker

Create `.env` from `.env.example`, then run:

```bash
docker compose up --build
```

The backend and frontend bind to `127.0.0.1` by default. Keep that behavior for private/local use unless you add authentication or a protected reverse proxy.

## Configuration

Important settings live in `.env.example`:

- `DATABASE_URL`: defaults to SQLite, can be changed to a PostgreSQL async URL.
- `STORAGE_ROOT`: all torrent data and browser downloads must stay under this root.
- `TORRENT_STATE_DIR`: resume-data storage.
- `TORRENT_FILE_DIR`: uploaded `.torrent` storage.
- `ALLOWED_HOSTS` and `CORS_ORIGINS`: browser/API deployment boundaries.
- `PUBLIC_RATE_LIMIT_PER_MINUTE`: optional in-memory limit for exposed HTTP endpoints.

## Development Checks

```powershell
py -3.11 -m compileall backend tests
pytest
ruff check backend tests
cd frontend
npm run build
```

Backend tests cover service and HTTP behavior with an in-process fake engine. A local
video streaming test also exercises real libtorrent when its bindings are installed.
Runtime requires real libtorrent bindings.

## Legal Demo Sources

For testing with real torrents, use only public-domain, open-source, or otherwise authorized content. Good candidates are official Linux distribution torrents or public-domain media distributed by its rights holder. Do not add unlicensed content.
