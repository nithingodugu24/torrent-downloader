from starlette.requests import HTTPConnection

from app.services.broadcaster import TorrentBroadcaster
from app.services.torrent_service import TorrentService


def get_torrent_service(connection: HTTPConnection) -> TorrentService:
    return connection.app.state.torrent_service


def get_broadcaster(connection: HTTPConnection) -> TorrentBroadcaster:
    return connection.app.state.broadcaster
