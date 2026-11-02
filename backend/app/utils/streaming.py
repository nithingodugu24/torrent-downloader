from fastapi import HTTPException

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".ts", ".mpeg", ".mpg"}


def byte_range(value: str | None, size: int) -> tuple[int, int]:
    """Parse a single HTTP byte range, including suffix and open-ended ranges."""
    if not value and size > 0:
        return 0, size - 1
    try:
        unit, interval = (value or "").split("=", 1)
        first, last = interval.split("-", 1)
        if unit.lower() != "bytes" or "," in interval or size <= 0:
            raise ValueError
        if not first:
            suffix = int(last)
            if suffix <= 0:
                raise ValueError
            return max(0, size - suffix), size - 1
        start = int(first)
        end = min(int(last), size - 1) if last else size - 1
        if start < 0 or start >= size or end < start:
            raise ValueError
        return start, end
    except ValueError as exc:
        raise HTTPException(
            416, "Requested range is not satisfiable.",
            headers={"Content-Range": f"bytes */{size}", "Accept-Ranges": "bytes"},
        ) from exc
