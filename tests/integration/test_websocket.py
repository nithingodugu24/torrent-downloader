from types import SimpleNamespace

from app.api.deps import get_broadcaster
from app.services.broadcaster import TorrentBroadcaster


def test_broadcaster_dependency_reads_connection_state() -> None:
    broadcaster = TorrentBroadcaster()
    connection = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(broadcaster=broadcaster))
    )

    assert get_broadcaster(connection) is broadcaster
