"""Tests for newsfeed.utils — time formatting, HTML sanitization, text truncation."""

from email.utils import format_datetime
from datetime import datetime, timezone, timedelta

from newsfeed.utils import time_ago, published_ts, sanitize_html, truncate


# ── time_ago ──────────────────────────────────────────────────────────────────


class TestTimeAgo:
    def test_none_returns_empty(self):
        assert time_ago(None) == ""

    def test_empty_string_returns_empty(self):
        assert time_ago("") == ""

    def test_bad_format_returns_empty(self):
        assert time_ago("not a date") == ""

    def test_just_now(self, monkeypatch):
        now = datetime.now(timezone.utc)
        published = format_datetime(now)
        monkeypatch.setattr("newsfeed.utils.time.time", lambda: now.timestamp() + 30)
        assert time_ago(published) == "just now"

    def test_minutes_ago(self, monkeypatch):
        now = datetime.now(timezone.utc)
        published = format_datetime(now)
        monkeypatch.setattr("newsfeed.utils.time.time", lambda: now.timestamp() + 300)
        assert time_ago(published) == "5m ago"

    def test_hours_ago(self, monkeypatch):
        now = datetime.now(timezone.utc)
        published = format_datetime(now)
        monkeypatch.setattr("newsfeed.utils.time.time", lambda: now.timestamp() + 7200)
        assert time_ago(published) == "2h ago"

    def test_days_ago(self, monkeypatch):
        now = datetime.now(timezone.utc)
        published = format_datetime(now)
        monkeypatch.setattr("newsfeed.utils.time.time", lambda: now.timestamp() + 172800)
        assert time_ago(published) == "2d ago"

    def test_one_minute_boundary(self, monkeypatch):
        now = datetime.now(timezone.utc)
        published = format_datetime(now)
        monkeypatch.setattr("newsfeed.utils.time.time", lambda: now.timestamp() + 60)
        assert time_ago(published) == "1m ago"

    def test_one_hour_boundary(self, monkeypatch):
        now = datetime.now(timezone.utc)
        published = format_datetime(now)
        monkeypatch.setattr("newsfeed.utils.time.time", lambda: now.timestamp() + 3600)
        assert time_ago(published) == "1h ago"

    def test_one_day_boundary(self, monkeypatch):
        now = datetime.now(timezone.utc)
        published = format_datetime(now)
        monkeypatch.setattr("newsfeed.utils.time.time", lambda: now.timestamp() + 86400)
        assert time_ago(published) == "1d ago"


# ── published_ts ──────────────────────────────────────────────────────────────


class TestPublishedTs:
    def test_none_returns_zero(self):
        assert published_ts(None) == 0.0

    def test_empty_returns_zero(self):
        assert published_ts("") == 0.0

    def test_bad_format_returns_zero(self):
        assert published_ts("not a date") == 0.0

    def test_valid_date_returns_timestamp(self):
        dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        published = format_datetime(dt)
        assert published_ts(published) == dt.timestamp()


# ── sanitize_html ─────────────────────────────────────────────────────────────


class TestSanitizeHtml:
    def test_none_returns_empty(self):
        assert sanitize_html(None) == ""

    def test_empty_returns_empty(self):
        assert sanitize_html("") == ""

    def test_plain_text_passthrough(self):
        assert sanitize_html("Hello world") == "Hello world"

    def test_strips_html_tags(self):
        assert sanitize_html("<b>Bold</b> and <i>italic</i>") == "Bold and italic"

    def test_decodes_entities(self):
        assert sanitize_html("Tom &amp; Jerry") == "Tom & Jerry"

    def test_collapses_whitespace(self):
        assert sanitize_html("too   much\n\nspace") == "too much space"

    def test_combined(self):
        result = sanitize_html("<p>Hello &amp; <b>world</b></p>  \n  ")
        assert result == "Hello & world"


# ── truncate ──────────────────────────────────────────────────────────────────


class TestTruncate:
    def test_short_text_unchanged(self):
        assert truncate("Hello", max_len=200) == "Hello"

    def test_exact_length_unchanged(self):
        text = "a" * 200
        assert truncate(text, max_len=200) == text

    def test_long_text_truncated_with_ellipsis(self):
        text = "word " * 50  # 250 chars
        result = truncate(text, max_len=30)
        assert result.endswith("…")
        assert len(result) <= 30

    def test_custom_max_len(self):
        text = "The quick brown fox jumps over the lazy dog"
        result = truncate(text, max_len=20)
        assert result.endswith("…")
        assert len(result) <= 20

    def test_truncates_at_word_boundary(self):
        text = "one two three four five six"
        result = truncate(text, max_len=15)
        # Should not break mid-word
        assert result.endswith("…")
        # The part before the ellipsis should be complete words
        words_part = result[:-1]  # remove the ellipsis
        assert not words_part.endswith(" ")  # rsplit removes trailing partial
