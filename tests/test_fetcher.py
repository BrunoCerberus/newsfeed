"""Tests for newsfeed.fetcher — RSS feed fetching and parsing."""

from email.utils import format_datetime
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

import httpx

import newsfeed.cache as cache_mod
from newsfeed.fetcher import _fetch_and_parse, fetch_category

# Minimal RSS XML for testing
RSS_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    {items}
  </channel>
</rss>"""

RSS_ITEM = """<item>
  <title>{title}</title>
  <link>{link}</link>
  <description>{description}</description>
  <pubDate>{pubdate}</pubDate>
</item>"""

ATOM_ITEM_UPDATED = """<item>
  <title>{title}</title>
  <link>{link}</link>
  <description>{description}</description>
  <updated>{updated}</updated>
</item>"""


def _make_rss(*articles):
    """Build RSS XML from (title, link, desc, pubdate) tuples."""
    items = []
    for title, link, desc, pubdate in articles:
        items.append(RSS_ITEM.format(title=title, link=link, description=desc, pubdate=pubdate))
    return RSS_TEMPLATE.format(items="\n".join(items))


def _make_rss_with_updated(title, link, desc, updated):
    """Build RSS with <updated> instead of <pubDate>."""
    item = ATOM_ITEM_UPDATED.format(title=title, link=link, description=desc, updated=updated)
    return RSS_TEMPLATE.format(items=item)


def _mock_response(text, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.text = text
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


class TestFetchAndParse:
    def test_parses_rss_entries(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path)
        pubdate = format_datetime(datetime.now(timezone.utc))
        xml = _make_rss(("Title 1", "http://example.com/1", "Desc 1", pubdate))
        monkeypatch.setattr("newsfeed.fetcher.httpx.get", lambda *a, **kw: _mock_response(xml))

        result = _fetch_and_parse("TestSrc", "http://example.com/feed", use_cache=False)
        assert len(result) == 1
        assert result[0]["title"] == "Title 1"
        assert result[0]["link"] == "http://example.com/1"
        assert result[0]["source"] == "TestSrc"
        assert result[0]["published"] == pubdate

    def test_http_error_returns_empty(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path)
        monkeypatch.setattr(
            "newsfeed.fetcher.httpx.get",
            lambda *a, **kw: _mock_response("", status_code=500),
        )
        result = _fetch_and_parse("Src", "http://example.com/feed", use_cache=False)
        assert result == []

    def test_timeout_returns_empty(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path)

        def raise_timeout(*a, **kw):
            raise httpx.TimeoutException("timeout")

        monkeypatch.setattr("newsfeed.fetcher.httpx.get", raise_timeout)
        result = _fetch_and_parse("Src", "http://example.com/feed", use_cache=False)
        assert result == []

    def test_cache_hit_skips_http(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path)
        cached = [{"title": "Cached", "link": "http://cached.com", "description": "", "published": "", "source": "S"}]
        cache_mod.put("http://example.com/feed", cached)

        http_called = False

        def spy_get(*a, **kw):
            nonlocal http_called
            http_called = True
            return _mock_response("")

        monkeypatch.setattr("newsfeed.fetcher.httpx.get", spy_get)
        result = _fetch_and_parse("S", "http://example.com/feed", use_cache=True)
        assert result == cached
        assert not http_called

    def test_cache_write_on_success(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path)
        pubdate = format_datetime(datetime.now(timezone.utc))
        xml = _make_rss(("Title", "http://example.com/1", "Desc", pubdate))
        monkeypatch.setattr("newsfeed.fetcher.httpx.get", lambda *a, **kw: _mock_response(xml))

        _fetch_and_parse("Src", "http://example.com/feed", use_cache=True)
        # Verify cache was written
        cached = cache_mod.get("http://example.com/feed")
        assert cached is not None
        assert len(cached) == 1
        assert cached[0]["title"] == "Title"

    def test_falls_back_to_updated_field(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path)
        updated = format_datetime(datetime.now(timezone.utc))
        xml = _make_rss_with_updated("Title", "http://example.com/1", "Desc", updated)
        monkeypatch.setattr("newsfeed.fetcher.httpx.get", lambda *a, **kw: _mock_response(xml))

        result = _fetch_and_parse("Src", "http://example.com/feed", use_cache=False)
        assert len(result) == 1
        # published field should have the updated value
        assert result[0]["published"] == updated

    def test_sanitizes_description(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path)
        pubdate = format_datetime(datetime.now(timezone.utc))
        xml = _make_rss(("Title", "http://example.com/1", "<b>Bold</b> &amp; italic", pubdate))
        monkeypatch.setattr("newsfeed.fetcher.httpx.get", lambda *a, **kw: _mock_response(xml))

        result = _fetch_and_parse("Src", "http://example.com/feed", use_cache=False)
        assert result[0]["description"] == "Bold & italic"


class TestFetchCategory:
    def test_merges_multiple_sources(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path)
        now = datetime.now(timezone.utc)
        pubdate_a = format_datetime(now - timedelta(hours=1))
        pubdate_b = format_datetime(now)

        xml_a = _make_rss(("From A", "http://a.com/1", "A desc", pubdate_a))
        xml_b = _make_rss(("From B", "http://b.com/1", "B desc", pubdate_b))

        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            url = args[0]
            if "feed-a" in url:
                return _mock_response(xml_a)
            return _mock_response(xml_b)

        monkeypatch.setattr("newsfeed.fetcher.httpx.get", mock_get)

        sources = {
            "Source A": "http://example.com/feed-a.xml",
            "Source B": "http://example.com/feed-b.xml",
        }
        result = fetch_category(sources, use_cache=False, limit=5)
        assert len(result) == 2
        # Most recent first
        assert result[0]["title"] == "From B"

    def test_empty_sources_returns_empty(self):
        result = fetch_category({}, use_cache=False, limit=5)
        assert result == []

    def test_one_source_fails_others_succeed(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path)
        pubdate = format_datetime(datetime.now(timezone.utc))
        xml = _make_rss(("Good", "http://good.com/1", "Works", pubdate))

        def mock_get(*args, **kwargs):
            url = args[0]
            if "bad" in url:
                raise httpx.TimeoutException("timeout")
            return _mock_response(xml)

        monkeypatch.setattr("newsfeed.fetcher.httpx.get", mock_get)

        sources = {
            "Good Source": "http://example.com/good-feed.xml",
            "Bad Source": "http://example.com/bad-feed.xml",
        }
        result = fetch_category(sources, use_cache=False, limit=5)
        assert len(result) == 1
        assert result[0]["title"] == "Good"

    def test_sorted_by_timestamp_descending(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path)
        now = datetime.now(timezone.utc)
        old = format_datetime(now - timedelta(hours=5))
        recent = format_datetime(now - timedelta(minutes=10))

        xml = _make_rss(
            ("Old", "http://example.com/old", "Old article", old),
            ("Recent", "http://example.com/recent", "Recent article", recent),
        )
        monkeypatch.setattr("newsfeed.fetcher.httpx.get", lambda *a, **kw: _mock_response(xml))

        sources = {"Src": "http://example.com/feed.xml"}
        result = fetch_category(sources, use_cache=False, limit=10)
        assert result[0]["title"] == "Recent"
        assert result[1]["title"] == "Old"
