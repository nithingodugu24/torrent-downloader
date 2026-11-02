import pytest
from app.schemas.torrent import MagnetCreate, TorrentPatch
from pydantic import ValidationError


def test_magnet_create_rejects_non_magnet_uri() -> None:
    with pytest.raises(ValidationError):
        MagnetCreate(magnet_uri="https://example.test/file.torrent")


def test_magnet_create_accepts_magnet_uri() -> None:
    payload = MagnetCreate(
        magnet_uri="magnet:?xt=urn:btih:0123456789012345678901234567890123456789"
    )

    assert payload.magnet_uri.startswith("magnet:?")


def test_patch_rejects_invalid_priority() -> None:
    with pytest.raises(ValidationError):
        TorrentPatch(priority=99)
