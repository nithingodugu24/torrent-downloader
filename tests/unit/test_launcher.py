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


def test_port_conflict_does_not_spawn_or_kill_process(monkeypatch):
    probe = Mock()
    probe.bind.side_effect = OSError("in use")
    socket = Mock()
    socket.__enter__ = Mock(return_value=probe)
    socket.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(launcher.socket, "socket", lambda: socket)
    spawn = Mock()
    monkeypatch.setattr(launcher.subprocess, "Popen", spawn)
    with pytest.raises(RuntimeError, match="Port 8000 is in use"):
        launcher.serve(Path("python"), 8000, False)
    spawn.assert_not_called()
