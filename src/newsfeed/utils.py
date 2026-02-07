"""Utility functions — time formatting, HTML sanitization, text truncation."""

import html
import re
import time
from email.utils import parsedate_to_datetime


def time_ago(published: str | None) -> str:
    """Convert a published date string to a human-readable 'time ago' format."""
    if not published:
        return ""
    try:
        dt = parsedate_to_datetime(published)
        diff = time.time() - dt.timestamp()
    except Exception:
        return ""

    if diff < 60:
        return "just now"
    elif diff < 3600:
        mins = int(diff / 60)
        return f"{mins}m ago"
    elif diff < 86400:
        hours = int(diff / 3600)
        return f"{hours}h ago"
    else:
        days = int(diff / 86400)
        return f"{days}d ago"


def sanitize_html(text: str | None) -> str:
    """Strip HTML tags and decode entities from text."""
    if not text:
        return ""
    # Decode HTML entities
    text = html.unescape(text)
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def truncate(text: str, max_len: int = 200) -> str:
    """Truncate text to max_len characters, adding ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rsplit(" ", 1)[0] + "…"
