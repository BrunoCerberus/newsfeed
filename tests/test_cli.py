"""Tests for newsfeed.cli — Click CLI entry point."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from newsfeed.cli import main


@pytest.fixture()
def runner():
    return CliRunner()


class TestListCategories:
    def test_exit_zero(self, runner):
        result = runner.invoke(main, ["--list-categories"])
        assert result.exit_code == 0

    def test_output_contains_categories(self, runner):
        result = runner.invoke(main, ["--list-categories"])
        assert "technology" in result.output
        assert "world" in result.output
        assert "science" in result.output


class TestLiveMode:
    def test_calls_run_live(self, runner):
        with patch("newsfeed.app.run_live") as mock_run_live:
            result = runner.invoke(main, ["--live"])
            mock_run_live.assert_called_once()


class TestDefaultMode:
    def test_no_args_fetches_all_categories(self, runner):
        with patch("newsfeed.cli.fetch_category") as mock_fetch:
            with patch("newsfeed.cli.display_all") as mock_display:
                mock_fetch.return_value = [{"title": "T", "link": "http://x.com", "description": "", "published": "", "source": "S"}]
                mock_display.return_value = []
                result = runner.invoke(main, [])
                assert mock_fetch.call_count == 6  # all 6 categories

    def test_single_category(self, runner):
        with patch("newsfeed.cli.fetch_category") as mock_fetch:
            with patch("newsfeed.cli.display_category") as mock_display:
                mock_fetch.return_value = [{"title": "T", "link": "http://x.com"}]
                mock_display.return_value = 1
                result = runner.invoke(main, ["technology"])
                assert result.exit_code == 0
                mock_fetch.assert_called_once()

    def test_alias_resolves(self, runner):
        with patch("newsfeed.cli.fetch_category") as mock_fetch:
            with patch("newsfeed.cli.display_category") as mock_display:
                mock_fetch.return_value = []
                mock_display.return_value = 0
                result = runner.invoke(main, ["tech"])
                assert result.exit_code == 0


class TestInvalidCategory:
    def test_unknown_category_exits_1(self, runner):
        result = runner.invoke(main, ["nonexistent"])
        assert result.exit_code == 1
        assert "Unknown category" in result.output


class TestLimitOption:
    def test_limit_passed_to_fetcher(self, runner):
        with patch("newsfeed.cli.fetch_category") as mock_fetch:
            with patch("newsfeed.cli.display_category"):
                mock_fetch.return_value = []
                runner.invoke(main, ["technology", "--limit", "10"])
                call_kwargs = mock_fetch.call_args
                assert call_kwargs.kwargs.get("limit") == 10 or call_kwargs[1].get("limit") == 10


class TestNoCacheOption:
    def test_no_cache_passed_to_fetcher(self, runner):
        with patch("newsfeed.cli.fetch_category") as mock_fetch:
            with patch("newsfeed.cli.display_category"):
                mock_fetch.return_value = []
                runner.invoke(main, ["technology", "--no-cache"])
                call_kwargs = mock_fetch.call_args
                assert call_kwargs.kwargs.get("use_cache") is False or call_kwargs[1].get("use_cache") is False


class TestOpenOption:
    def test_open_valid_article(self, runner):
        articles = [
            {"title": "Art 1", "link": "http://example.com/1", "description": "", "published": "", "source": "S"},
        ]
        with patch("newsfeed.cli.fetch_category", return_value=articles):
            with patch("newsfeed.cli.display_category", return_value=1):
                with patch("newsfeed.cli.webbrowser.open") as mock_open:
                    result = runner.invoke(main, ["technology", "--open", "1"])
                    mock_open.assert_called_once_with("http://example.com/1")

    def test_open_out_of_range(self, runner):
        articles = [
            {"title": "Art 1", "link": "http://example.com/1", "description": "", "published": "", "source": "S"},
        ]
        with patch("newsfeed.cli.fetch_category", return_value=articles):
            with patch("newsfeed.cli.display_category", return_value=1):
                result = runner.invoke(main, ["technology", "--open", "999"])
                assert "Invalid article number" in result.output

    def test_open_article_with_no_url(self, runner):
        articles = [
            {"title": "No Link", "link": "", "description": "", "published": "", "source": "S"},
        ]
        with patch("newsfeed.cli.fetch_category", return_value=articles):
            with patch("newsfeed.cli.display_category", return_value=1):
                result = runner.invoke(main, ["technology", "--open", "1"])
                assert "has no URL" in result.output


class TestWatchMode:
    def test_watch_exits_on_keyboard_interrupt(self, runner):
        call_count = 0

        def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            raise KeyboardInterrupt()

        with patch("newsfeed.cli.fetch_category", return_value=[]):
            with patch("newsfeed.cli.display_all", return_value=[]):
                with patch("newsfeed.cli.time.sleep", side_effect=mock_sleep):
                    result = runner.invoke(main, ["--watch"])
                    assert "Goodbye" in result.output
