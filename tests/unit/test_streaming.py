import pytest
from app.utils.streaming import byte_range
from fastapi import HTTPException


@pytest.mark.parametrize(
    ("header", "expected"),
    [(None, (0, 99)), ("bytes=20-39", (20, 39)), ("bytes=80-", (80, 99)),
     ("bytes=-10", (90, 99)), ("bytes=90-200", (90, 99)), ("bytes=-200", (0, 99))],
)
def test_video_ranges(header, expected):
    assert byte_range(header, 100) == expected


@pytest.mark.parametrize(
    "header", ["bytes=100-", "bytes=30-20", "bytes=-0", "bytes=0-1,4-5", "bad", "items=0-1"]
)
def test_invalid_video_ranges(header):
    with pytest.raises(HTTPException) as error:
        byte_range(header, 100)
    assert error.value.status_code == 416
    assert error.value.headers["Content-Range"] == "bytes */100"
