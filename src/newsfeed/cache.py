"""JSON file cache with TTL support."""

import hashlib
import json
import time
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "newsfeed"
DEFAULT_TTL = 600  # 10 minutes


def _cache_path(url: str) -> Path:
    """Generate a cache file path for a given URL."""
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{key}.json"


def get(url: str, ttl: int = DEFAULT_TTL) -> list[dict] | None:
    """Return cached entries for a URL if fresh, else None."""
    path = _cache_path(url)
    if not path.exists():
        return None
    if time.time() - path.stat().st_mtime > ttl:
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def put(url: str, entries: list[dict]) -> None:
    """Write entries to cache for a URL."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(url)
    path.write_text(json.dumps(entries, ensure_ascii=False))
