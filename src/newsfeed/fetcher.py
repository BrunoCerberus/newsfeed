"""Parallel RSS feed fetching and parsing."""

from concurrent.futures import ThreadPoolExecutor, as_completed

import feedparser
import httpx

from newsfeed import cache
from newsfeed.utils import sanitize_html


def _fetch_and_parse(source_name: str, url: str, use_cache: bool) -> list[dict]:
    """Fetch a single RSS feed and return parsed entries."""
    if use_cache:
        cached = cache.get(url)
        if cached is not None:
            return cached

    try:
        resp = httpx.get(url, timeout=10, follow_redirects=True, headers={
            "User-Agent": "newsfeed/0.1 (terminal RSS reader)",
        })
        resp.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException):
        return []

    feed = feedparser.parse(resp.text)
    entries = []
    for entry in feed.entries:
        entries.append({
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "description": sanitize_html(
                entry.get("summary") or entry.get("description", "")
            ),
            "published": entry.get("published", ""),
            "source": source_name,
        })

    if use_cache:
        cache.put(url, entries)

    return entries


def fetch_category(
    sources: dict[str, str],
    use_cache: bool = True,
    limit: int = 5,
) -> list[dict]:
    """Fetch all feeds for a category in parallel, return merged + sorted entries."""
    all_entries: list[dict] = []

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(_fetch_and_parse, name, url, use_cache): name
            for name, url in sources.items()
        }
        for future in as_completed(futures):
            entries = future.result()
            all_entries.extend(entries[:limit])

    # Sort by published date descending (most recent first)
    all_entries.sort(key=lambda e: e.get("published", ""), reverse=True)
    return all_entries
