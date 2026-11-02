import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.config import Settings
from app.torrent_engine.base import EngineTorrentOptions
from app.torrent_engine.libtorrent_engine import LibtorrentEngine


@pytest.mark.anyio
async def test_stream_waits_for_verified_piece_and_uses_file_offset(tmp_path: Path):
    """A sparse/preallocated file must not be served just because it exists."""
    (tmp_path / "video.mkv").write_bytes(b"abcdefgh")
    available = asyncio.Event()
    requested = []
    storage = SimpleNamespace(
        file_size=lambda index: 8, file_offset=lambda index: 3,
        file_path=lambda index: "video.mkv",
    )
    info = SimpleNamespace(files=lambda: storage, piece_length=lambda: 4)
    handle = SimpleNamespace(
        torrent_file=lambda: info,
        status=lambda: SimpleNamespace(save_path=str(tmp_path), paused=False),
        have_piece=lambda piece: available.is_set(),
        file_priority=lambda *args: 4,
        set_piece_deadline=lambda piece, deadline: requested.append(piece),
        reset_piece_deadline=lambda piece: None,
        is_valid=lambda: True,
        has_metadata=lambda: True,
    )
    engine = object.__new__(LibtorrentEngine)
    engine._handles = {"test": handle}
    pending = asyncio.create_task(engine.read_stream_chunk("test", 0, 0, 8))
    await asyncio.sleep(0.01)
    assert not pending.done()
    assert requested[0] == 0
    available.set()
    # File starts at torrent byte 3: first chunk ends at the piece boundary.
    assert await pending == b"a"
    assert await engine.read_stream_chunk("test", 0, 1, 7) == b"bcde"
    assert await engine.read_stream_chunk("test", 0, 5, 3) == b"fgh"


@pytest.fixture()
def anyio_backend():
    return "asyncio"


def test_auto_managed_queue_is_not_a_user_pause():
    engine = object.__new__(LibtorrentEngine)
    engine._lt = SimpleNamespace(torrent_flags=SimpleNamespace(auto_managed=32))
    assert engine._map_state(SimpleNamespace(paused=True, flags=32), None) == "queued"
    assert engine._map_state(SimpleNamespace(paused=True, flags=0), None) == "paused"


@pytest.mark.anyio
async def test_real_libtorrent_reads_local_video(tmp_path: Path):
    lt = pytest.importorskip("libtorrent")
    data = bytes(range(256)) * 300
    video = tmp_path / "movie.mkv"
    video.write_bytes(data)
    storage = lt.file_storage()
    storage.add_file("movie.mkv", len(data))
    creator = lt.create_torrent(storage, 16384)
    lt.set_piece_hashes(creator, str(tmp_path))
    torrent = tmp_path / "movie.torrent"
    torrent.write_bytes(lt.bencode(creator.generate()))
    engine = LibtorrentEngine(Settings())
    try:
        await engine.add_torrent_file(
            "local", torrent, tmp_path, EngineTorrentOptions(is_sequential=True)
        )
        async with asyncio.timeout(10):
            while not engine._handles["local"].have_piece(0):  # noqa: ASYNC110
                await asyncio.sleep(0.05)
        result = await engine.read_stream_chunk("local", 0, 123, 20000)
        assert result == data[123:16384]
        tail = await engine.read_stream_chunk("local", 0, len(data) - 50, 50)
        assert tail == data[-50:]
    finally:
        await engine.remove("local")
        await engine.close()
