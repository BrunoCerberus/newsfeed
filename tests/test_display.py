"""Tests for newsfeed.display — Rich terminal output."""

from io import StringIO

from rich.console import Console

import newsfeed.display as display_mod
from newsfeed.display import display_all, display_categories_list, display_category


def _capture_console():
    """Create a Console that writes to a StringIO buffer and return (console, buffer)."""
    buf = StringIO()
    return Console(file=buf, force_terminal=True, width=120), buf


class TestDisplayCategory:
    def test_empty_entries_returns_zero(self, monkeypatch):
        test_console, buf = _capture_console()
        monkeypatch.setattr(display_mod, "console", test_console)
        count = display_category("technology", [])
        assert count == 0

    def test_returns_entry_count(self, monkeypatch, sample_articles):
        test_console, buf = _capture_console()
        monkeypatch.setattr(display_mod, "console", test_console)
        articles = sample_articles(3)
        count = display_category("technology", articles)
        assert count == 3

    def test_output_contains_titles(self, monkeypatch, sample_articles):
        test_console, buf = _capture_console()
        monkeypatch.setattr(display_mod, "console", test_console)
        articles = sample_articles(2)
        display_category("world", articles)
        output = buf.getvalue()
        assert "Article 0" in output
        assert "Article 1" in output

    def test_output_contains_source_names(self, monkeypatch, sample_articles):
        test_console, buf = _capture_console()
        monkeypatch.setattr(display_mod, "console", test_console)
        articles = sample_articles(1)
        display_category("science", articles)
        output = buf.getvalue()
        assert "Source 0" in output

    def test_number_offset(self, monkeypatch, sample_articles):
        test_console, buf = _capture_console()
        monkeypatch.setattr(display_mod, "console", test_console)
        articles = sample_articles(2)
        display_category("technology", articles, number_offset=5)
        output = buf.getvalue()
        # First article should be numbered 6 (offset 5 + 1)
        assert "6" in output


class TestDisplayAll:
    def test_returns_flat_article_list(self, monkeypatch, sample_articles):
        test_console, buf = _capture_console()
        monkeypatch.setattr(display_mod, "console", test_console)
        data = {
            "technology": sample_articles(2),
            "world": sample_articles(3),
        }
        result = display_all(data)
        assert len(result) == 5

    def test_empty_categories(self, monkeypatch):
        test_console, buf = _capture_console()
        monkeypatch.setattr(display_mod, "console", test_console)
        result = display_all({})
        assert result == []


class TestDisplayCategoriesList:
    def test_output_contains_category_names(self, monkeypatch):
        test_console, buf = _capture_console()
        monkeypatch.setattr(display_mod, "console", test_console)
        display_categories_list(["technology", "world", "science"])
        output = buf.getvalue()
        assert "technology" in output
        assert "world" in output
        assert "science" in output

    def test_output_contains_aliases_hint(self, monkeypatch):
        test_console, buf = _capture_console()
        monkeypatch.setattr(display_mod, "console", test_console)
        display_categories_list(["technology"])
        output = buf.getvalue()
        assert "Aliases" in output
