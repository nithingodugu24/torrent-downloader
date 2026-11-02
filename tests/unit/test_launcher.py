import json
import socket
from pathlib import Path
from unittest.mock import Mock

import pytest

import start as launcher


@pytest.fixture()
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    monkeypatch.setattr(launcher, "FRONTEND", tmp_path / "frontend")
    monkeypatch.setattr(launcher, "RUNTIME", tmp_path / ".runtime")
    monkeypatch.setattr(launcher, "VENV", tmp_path / ".venv")
    launcher.RUNTIME.mkdir()
    return tmp_path


def frontend_sources(root):
    frontend = root / "frontend"
    (frontend / "src").mkdir(parents=True)
    for name in (
        "package.json",
        "package-lock.json",
        "index.html",
        "vite.config.ts",
        "tsconfig.json",
        "tsconfig.node.json",
        "src/App.tsx",
    ):
        (frontend / name).write_text("test", encoding="utf-8")
    return frontend


def test_build_reused_until_source_changes(workspace, monkeypatch):
    frontend = frontend_sources(workspace)
    calls = []

    def build(command, cwd):
        calls.append(command)
        (frontend / "dist").mkdir(exist_ok=True)
        (frontend / "dist/index.html").write_text("built")

    monkeypatch.setattr(launcher, "run", build)
    monkeypatch.setattr(launcher.shutil, "which", lambda command: command)
    monkeypatch.setattr(launcher.subprocess, "check_output", lambda *args, **kwargs: "v20.0.0")
    launcher.prepare_frontend()
    assert [command[1] for command in calls] == ["ci", "run"]
    launcher.prepare_frontend()
    assert len(calls) == 2
    (frontend / "src/App.tsx").write_text("changed")
    launcher.prepare_frontend()
    assert len(calls) == 4
    launcher.prepare_frontend(rebuild=True)
    assert len(calls) == 6


def test_failed_build_is_not_cached(workspace, monkeypatch):
    frontend_sources(workspace)
    monkeypatch.setattr(launcher.shutil, "which", lambda command: command)
    monkeypatch.setattr(launcher.subprocess, "check_output", lambda *args, **kwargs: "v20.0.0")
    monkeypatch.setattr(launcher, "run", Mock(side_effect=RuntimeError("install failed")))
    with pytest.raises(RuntimeError, match="install failed"):
        launcher.prepare_frontend()
    assert not (launcher.RUNTIME / "frontend.sha256").exists()


def test_missing_node_has_actionable_message(workspace, monkeypatch):
    frontend_sources(workspace)
    monkeypatch.setattr(launcher.shutil, "which", lambda command: None)
    with pytest.raises(RuntimeError, match="Install Node.js 20"):
        launcher.prepare_frontend()


def test_running_app_reopened_without_install(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    monkeypatch.setattr(launcher, "RUNTIME", tmp_path / ".runtime")
    monkeypatch.setattr(launcher.sys, "argv", ["start.py"])
    monkeypatch.setattr(launcher, "is_our_app", lambda url: True)
    prepare = Mock()
    browser = Mock()
    monkeypatch.setattr(launcher, "prepare_python", prepare)
    monkeypatch.setattr(launcher.webbrowser, "open", browser)
    assert launcher.main() == 0
    prepare.assert_not_called()
    browser.assert_called_once_with("http://127.0.0.1:8000")


def test_setup_only_does_not_start_server(workspace, monkeypatch):
    monkeypatch.setattr(launcher.sys, "argv", ["start.py", "--setup-only"])
    monkeypatch.setattr(launcher, "prepare_python", lambda: Path("python"))
    monkeypatch.setattr(launcher, "prepare_frontend", lambda rebuild: None)
    serve = Mock()
    monkeypatch.setattr(launcher, "serve", serve)
    assert launcher.main() == 0
    serve.assert_not_called()


def test_busy_port_is_skipped_with_real_socket():
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        preferred = occupied.getsockname()[1]
        chosen = launcher.available_port(preferred)
        assert chosen != preferred
        with socket.socket() as check:
            check.bind(("127.0.0.1", chosen))


def test_fallback_port_is_used_for_server_browser_and_next_launch(workspace, monkeypatch):
    monkeypatch.setattr(launcher, "available_port", lambda preferred: 8001)
    monkeypatch.setattr(launcher, "is_our_app", lambda url: url.endswith(":8001"))
    process = Mock(returncode=0)
    process.poll.side_effect = [None, 0]
    spawn = Mock(return_value=process)
    browser = Mock()
    monkeypatch.setattr(launcher.subprocess, "Popen", spawn)
    monkeypatch.setattr(launcher.webbrowser, "open", browser)
    launcher.serve(Path("python"), 8000, True)
    assert spawn.call_args.args[0][-1] == "8001"
    browser.assert_called_once_with("http://127.0.0.1:8001")
    assert launcher.saved_port() == 8001
    process.terminate.assert_not_called()
    process.kill.assert_not_called()


def test_running_app_on_remembered_port_reopens_without_install(workspace, monkeypatch):
    (launcher.RUNTIME / "server.json").write_text(json.dumps({"port": 8001}))
    monkeypatch.setattr(launcher.sys, "argv", ["start.py"])
    monkeypatch.setattr(launcher, "is_our_app", lambda url: url.endswith(":8001"))
    prepare = Mock()
    browser = Mock()
    monkeypatch.setattr(launcher, "prepare_python", prepare)
    monkeypatch.setattr(launcher.webbrowser, "open", browser)
    assert launcher.main() == 0
    prepare.assert_not_called()
    browser.assert_called_once_with("http://127.0.0.1:8001")


@pytest.mark.parametrize("contents", ["bad json", "[]", '{"port": 70000}', '{"port": true}'])
def test_invalid_saved_port_is_ignored(workspace, contents):
    (launcher.RUNTIME / "server.json").write_text(contents)
    assert launcher.saved_port() is None


def test_restart_prefers_previous_port(workspace, monkeypatch):
    (launcher.RUNTIME / "server.json").write_text(json.dumps({"port": 8001}))
    monkeypatch.setattr(launcher.sys, "argv", ["start.py", "--no-browser"])
    monkeypatch.setattr(launcher, "is_our_app", lambda url: False)
    monkeypatch.setattr(launcher, "prepare_python", lambda: Path("python"))
    monkeypatch.setattr(launcher, "prepare_frontend", lambda rebuild: None)
    serve = Mock()
    monkeypatch.setattr(launcher, "serve", serve)
    assert launcher.main() == 0
    serve.assert_called_once_with(Path("python"), 8001, False)
