"""Tests for newsfeed.cache — JSON file cache with TTL."""

import json

import newsfeed.cache as cache_mod
from newsfeed.cache import _cache_path, get, put


class TestCachePath:
    def test_same_url_same_path(self):
        assert _cache_path("http://example.com") == _cache_path("http://example.com")

    def test_different_urls_different_paths(self):
        assert _cache_path("http://a.com") != _cache_path("http://b.com")

    def test_path_is_under_cache_dir(self):
        path = _cache_path("http://example.com")
        assert str(path).startswith(str(cache_mod.CACHE_DIR))

    def test_path_ends_with_json(self):
        path = _cache_path("http://example.com")
        assert path.suffix == ".json"


class TestPutAndGet:
    def test_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path)
        entries = [{"title": "Test", "link": "http://example.com/1"}]
        put("http://example.com/feed", entries)
        result = get("http://example.com/feed")
        assert result == entries

    def test_get_missing_file_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path)
        assert get("http://nonexistent.com/feed") is None

    def test_get_expired_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path)
        entries = [{"title": "Old"}]
        put("http://example.com/feed", entries)

        # Advance time past the TTL
        import time
        real_time = time.time()
        monkeypatch.setattr("newsfeed.cache.time.time", lambda: real_time + 700)
        assert get("http://example.com/feed", ttl=600) is None

    def test_get_corrupt_json_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path)
        # Write invalid JSON to the cache path
        url = "http://example.com/corrupt"
        path = _cache_path(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{invalid json!!!")
        assert get(url) is None

    def test_multiple_urls_independent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path)
        entries_a = [{"title": "A"}]
        entries_b = [{"title": "B"}]
        put("http://a.com/feed", entries_a)
        put("http://b.com/feed", entries_b)
        assert get("http://a.com/feed") == entries_a
        assert get("http://b.com/feed") == entries_b

    def test_put_creates_cache_dir(self, tmp_path, monkeypatch):
        nested = tmp_path / "deep" / "nested"
        monkeypatch.setattr(cache_mod, "CACHE_DIR", nested)
        put("http://example.com/feed", [{"title": "Test"}])
        assert nested.exists()

    def test_get_within_ttl_returns_data(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path)
        entries = [{"title": "Fresh"}]
        put("http://example.com/feed", entries)
        # Don't advance time — should still be fresh
        assert get("http://example.com/feed", ttl=600) == entries
