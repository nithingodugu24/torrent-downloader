"""Install requirements and run Torrent Downloader without manual environment setup."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
RUNTIME = ROOT / ".runtime"
VENV = ROOT / ".venv"


def run(command: list[str], cwd: Path = ROOT) -> None:
    subprocess.run(command, cwd=cwd, check=True)  # noqa: S603 -- fixed launcher commands


def fingerprint(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def prepare_python() -> Path:
    python = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        print("\n[1/3] Creating the app's private Python environment...", flush=True)
        venv.EnvBuilder(with_pip=True).create(VENV)
    stamp = RUNTIME / "python.sha256"
    expected = fingerprint([ROOT / "requirements.txt"])
    ready = (
        subprocess.run(  # noqa: S603 -- app-local Python and fixed import probe
            [
                str(python),
                "-c",
                "import fastapi, uvicorn, sqlalchemy, aiosqlite, asyncpg, multipart, libtorrent",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )
    if not stamp.is_file() or stamp.read_text() != expected or not ready:
        print("\n[1/3] Downloading Python requirements...", flush=True)
        run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--only-binary=libtorrent",
                "-r",
                str(ROOT / "requirements.txt"),
            ]
        )
        stamp.write_text(expected)
    else:
        print("[1/3] Python requirements are ready.", flush=True)
    return python


def prepare_frontend(rebuild: bool = False) -> None:
    sources = [p for p in (FRONTEND / "src").rglob("*") if p.is_file()]
    sources += [
        FRONTEND / name
        for name in (
            "package.json",
            "package-lock.json",
            "index.html",
            "vite.config.ts",
            "tsconfig.json",
            "tsconfig.node.json",
        )
    ]
    expected = fingerprint(sources)
    stamp = RUNTIME / "frontend.sha256"
    if (
        not rebuild
        and (FRONTEND / "dist/index.html").is_file()
        and stamp.is_file()
        and stamp.read_text() == expected
    ):
        print("[2/3] Interface is ready.", flush=True)
        return
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    node = shutil.which("node")
    if not npm or not node:
        raise RuntimeError(
            "Install Node.js 20 or newer from https://nodejs.org/ and reopen this window."
        )
    version = subprocess.check_output(  # noqa: S603 -- resolved Node executable
        [node, "--version"], text=True
    ).strip()
    if int(version.lstrip("v").split(".")[0]) < 20:
        raise RuntimeError("Node.js 20 or newer is required. Install it from https://nodejs.org/.")
    print("\n[2/3] Installing interface requirements and building...", flush=True)
    run([npm, "ci", "--no-audit", "--no-fund"], cwd=FRONTEND)
    run([npm, "run", "build"], cwd=FRONTEND)
    stamp.write_text(expected)


def is_our_app(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/api/health", timeout=1) as response:  # noqa: S310 -- localhost HTTP only
            return json.load(response).get("app") == "torrent-downloader"
    except (OSError, ValueError):
        return False


def serve(python: Path, port: int, open_browser: bool) -> None:
    url = f"http://127.0.0.1:{port}"
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError(
                f"Port {port} is in use. Close that server or use --port {port + 1}."
            ) from exc
    print(f"\n[3/3] Starting Torrent Downloader at {url}", flush=True)
    print("Keep this window open. Press Ctrl+C to stop the app.\n", flush=True)
    process = subprocess.Popen(  # noqa: S603 -- app-local Python and validated port
        [
            str(python),
            "-m",
            "uvicorn",
            "app.main:app",
            "--app-dir",
            "backend",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=ROOT,
    )
    try:
        deadline = time.monotonic() + 60
        while process.poll() is None and time.monotonic() < deadline:
            if is_our_app(url):
                if open_browser:
                    webbrowser.open(url)
                process.wait()
                if process.returncode:
                    raise RuntimeError(f"The server exited with code {process.returncode}.")
                return
            time.sleep(0.25)
        raise RuntimeError("The server did not become ready. Read its error above and try again.")
    finally:
        if process.poll() is None:
            # Ctrl+C reaches uvicorn too; allow time to save resume data first.
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup-only", action="store_true", help="Install/build without starting")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser")
    parser.add_argument("--rebuild", action="store_true", help="Force an interface rebuild")
    parser.add_argument("--port", type=int, default=8000, help="Local app port (default: 8000)")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    os.chdir(ROOT)
    print("Torrent Downloader", flush=True)
    try:
        if not args.setup_only and is_our_app(f"http://127.0.0.1:{args.port}"):
            print(f"Already running at http://127.0.0.1:{args.port}")
            if not args.no_browser:
                webbrowser.open(f"http://127.0.0.1:{args.port}")
            return 0
        if sys.version_info < (3, 11):  # noqa: UP036 -- explain unsupported launcher runtimes
            raise RuntimeError("Install 64-bit Python 3.11 or newer, then run this launcher again.")
        RUNTIME.mkdir(exist_ok=True)
        python = prepare_python()
        prepare_frontend(args.rebuild)
        if args.setup_only:
            print("\nSetup complete. Run start.bat (Windows) or python3 start.py to open the app.")
        else:
            serve(python, args.port, not args.no_browser)
        return 0
    except KeyboardInterrupt:
        print("\nTorrent Downloader stopped.")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"\nSetup/start failed: {exc}", file=sys.stderr)
        print(
            "Check internet access for install errors. See README.md for troubleshooting.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
