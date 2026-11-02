from pathlib import Path

import pytest
from app.utils.paths import safe_resolve_under_root
from fastapi import HTTPException


def test_safe_resolve_allows_relative_paths(tmp_path: Path) -> None:
    resolved = safe_resolve_under_root(tmp_path, "category/file.bin")

    assert resolved == tmp_path / "category" / "file.bin"


def test_safe_resolve_rejects_traversal(tmp_path: Path) -> None:
    with pytest.raises(HTTPException):
        safe_resolve_under_root(tmp_path, "../outside")


def test_safe_resolve_rejects_absolute_escape(tmp_path: Path) -> None:
    with pytest.raises(HTTPException):
        safe_resolve_under_root(tmp_path, str(tmp_path.parent / "outside"))
