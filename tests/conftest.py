"""Shared fixtures for newsfeed tests."""

from email.utils import format_datetime
from datetime import datetime, timezone, timedelta

import pytest


@pytest.fixture()
def sample_article():
    """A single article dict with all expected keys."""
    return {
        "title": "Test Article Title",
        "link": "https://example.com/article/1",
        "description": "This is a test article description.",
        "published": format_datetime(datetime.now(timezone.utc) - timedelta(hours=2)),
        "source": "Test Source",
    }


@pytest.fixture()
def sample_articles():
    """Factory fixture: returns a list of n articles with distinct links and staggered dates."""

    def _make(n: int = 5) -> list[dict]:
        now = datetime.now(timezone.utc)
        return [
            {
                "title": f"Article {i}",
                "link": f"https://example.com/article/{i}",
                "description": f"Description for article {i}.",
                "published": format_datetime(now - timedelta(hours=i)),
                "source": f"Source {i}",
            }
            for i in range(n)
        ]

    return _make


@pytest.fixture()
def sample_sources():
    """A small sources dict for testing fetcher."""
    return {
        "Test Source A": "http://example.com/feed-a.xml",
        "Test Source B": "http://example.com/feed-b.xml",
    }
