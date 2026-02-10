"""Tests for newsfeed.ticker — scrolling headline widget."""

from unittest.mock import MagicMock

import pytest
from rich.text import Text

from newsfeed.ticker import Ticker


class TestTickerRender:
    def test_render_empty_returns_empty_text(self):
        ticker = Ticker()
        result = ticker.render()
        assert isinstance(result, Text)
        assert result.plain == ""


@pytest.mark.asyncio
class TestTickerRenderAsync:
    async def test_render_with_headlines(self):
        from textual.app import App, ComposeResult

        class TickerApp(App):
            def compose(self) -> ComposeResult:
                yield Ticker(id="ticker")

        app = TickerApp()
        async with app.run_test(size=(80, 3)) as pilot:
            ticker = app.query_one("#ticker", Ticker)
            articles = [
                ("world", {"title": "Story A"}),
                ("technology", {"title": "Story B"}),
            ]
            ticker.update_headlines(articles)
            result = ticker.render()
            assert isinstance(result, Text)
            assert len(result.plain) > 0

    async def test_render_wraps_around(self):
        from textual.app import App, ComposeResult

        class TickerApp(App):
            def compose(self) -> ComposeResult:
                yield Ticker(id="ticker")

        app = TickerApp()
        async with app.run_test(size=(80, 3)) as pilot:
            ticker = app.query_one("#ticker", Ticker)
            articles = [("world", {"title": "Hi"})]
            ticker.update_headlines(articles)
            # Set offset near end to test wrap-around
            ticker.offset = len(ticker._plain_text) - 2
            result = ticker.render()
            assert isinstance(result, Text)
            assert len(result.plain) > 0


class TestTickerScroll:
    def test_scroll_increments_offset(self):
        ticker = Ticker()
        articles = [("world", {"title": "Test headline"})]
        ticker.update_headlines(articles)
        assert ticker.offset == 0
        ticker._scroll()
        assert ticker.offset == 1

    def test_scroll_wraps_around(self):
        ticker = Ticker()
        articles = [("world", {"title": "A"})]
        ticker.update_headlines(articles)
        plain_len = len(ticker._plain_text)
        ticker.offset = plain_len - 1
        ticker._scroll()
        assert ticker.offset == 0

    def test_scroll_noop_when_empty(self):
        ticker = Ticker()
        ticker._scroll()
        assert ticker.offset == 0


class TestTickerPauseResume:
    def test_pause_stops_timer(self):
        ticker = Ticker()
        mock_timer = MagicMock()
        ticker._timer = mock_timer
        ticker.pause()
        mock_timer.stop.assert_called_once()

    def test_resume_resumes_timer(self):
        ticker = Ticker()
        mock_timer = MagicMock()
        ticker._timer = mock_timer
        ticker.resume()
        mock_timer.resume.assert_called_once()

    def test_pause_noop_when_no_timer(self):
        ticker = Ticker()
        ticker._timer = None
        ticker.pause()  # should not raise

    def test_resume_noop_when_no_timer(self):
        ticker = Ticker()
        ticker._timer = None
        ticker.resume()  # should not raise


@pytest.mark.asyncio
class TestTickerAsync:
    async def test_on_mount_sets_timer(self):
        """Mounting the ticker in a real app should set the interval timer."""
        from textual.app import App, ComposeResult

        class TickerApp(App):
            def compose(self) -> ComposeResult:
                yield Ticker(id="ticker")

        app = TickerApp()
        async with app.run_test(size=(80, 3)) as pilot:
            ticker = app.query_one("#ticker", Ticker)
            assert ticker._timer is not None

    async def test_scroll_advances_after_mount(self):
        from textual.app import App, ComposeResult

        class TickerApp(App):
            def compose(self) -> ComposeResult:
                yield Ticker(id="ticker")

        app = TickerApp()
        async with app.run_test(size=(80, 3)) as pilot:
            ticker = app.query_one("#ticker", Ticker)
            articles = [("world", {"title": "Headline text for scrolling"})]
            ticker.update_headlines(articles)
            # Wait for a few scroll ticks
            await pilot.pause(0.5)
            assert ticker.offset > 0
