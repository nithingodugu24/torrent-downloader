from pathlib import Path

from fastapi import HTTPException, status


def safe_resolve_under_root(root: Path, requested: str | None = None) -> Path:
    root_resolved = root.resolve()
    candidate = root_resolved if not requested else Path(requested)
    if not candidate.is_absolute():
        candidate = root_resolved / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path must stay inside the configured storage root.",
        ) from exc
    return resolved


def safe_torrent_filename(task_id: str) -> str:
    return f"{task_id}.torrent"


def display_path(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return path.name
