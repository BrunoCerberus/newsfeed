"""Tests for newsfeed.app — TUI app logic (no UI interactions)."""

from unittest.mock import patch, MagicMock

import pytest

from newsfeed.app import NewsfeedApp, StatusBar, AppHeader, StatsPanel


class TestStatusBar:
    def test_render_default(self):
        bar = StatusBar()
        output = bar.render()
        assert "0 articles" in output
        assert "Last:" in output

    def test_render_with_values(self):
        bar = StatusBar()
        bar.article_count = 42
        bar.last_refresh = "14:30:00"
        output = bar.render()
        assert "42 articles" in output
        assert "14:30:00" in output

    def test_render_contains_keybindings(self):
        bar = StatusBar()
        output = bar.render()
        assert "r:Refresh" in output
        assert "q:Quit" in output
        assert "enter:Open" in output


class TestStatsPanel:
    def test_render_default(self):
        panel = StatsPanel()
        output = panel.render()
        assert "0" in output
        assert "total articles" in output

    def test_render_with_counts(self):
        panel = StatsPanel()
        panel.article_count = 42
        panel.category_counts = {"world": 10, "technology": 15}
        output = panel.render()
        assert "42" in output
        assert "World" in output
        assert "Technology" in output


class TestNewsfeedAppInit:
    def test_default_attributes(self):
        app = NewsfeedApp()
        assert app.refresh_interval == 300
        assert app.limit == 5
        assert app.use_cache is True
        assert len(app.all_categories) == 6
        assert all(cat in app.articles for cat in app.all_categories)
        assert all(len(entries) == 0 for entries in app.articles.values())
        assert len(app.seen_links) == 0

    def test_custom_attributes(self):
        app = NewsfeedApp(refresh_interval=60, limit=10, use_cache=False)
        assert app.refresh_interval == 60
        assert app.limit == 10
        assert app.use_cache is False

    def test_articles_dict_has_all_categories(self):
        app = NewsfeedApp()
        from newsfeed.feeds import get_all_categories
        for cat in get_all_categories():
            assert cat in app.articles
            assert isinstance(app.articles[cat], list)

    def test_theme_registered(self):
        app = NewsfeedApp()
        assert app.theme == "newsfeed-dark"


class TestGlobe:
    def test_frame_generation(self):
        from newsfeed.globe import _generate_frames, NUM_FRAMES, GLOBE_WIDTH, _PIXEL_H
        frames = _generate_frames()
        assert len(frames) == NUM_FRAMES
        for frame in frames:
            assert len(frame) == _PIXEL_H
            for row in frame:
                assert len(row) == GLOBE_WIDTH
                for pixel in row:
                    assert pixel is None or (isinstance(pixel, tuple) and len(pixel) == 3)

    def test_is_land(self):
        from newsfeed.globe import _is_land
        # London should be land
        assert _is_land(51.5, -0.1) is True
        # Middle of Pacific should be ocean
        assert _is_land(0, -160) is False

    def test_is_ice(self):
        from newsfeed.globe import _is_ice
        assert _is_ice(80) is True
        assert _is_ice(-80) is True
        assert _is_ice(45) is False


class TestTicker:
    def test_update_headlines(self):
        from newsfeed.ticker import Ticker
        ticker = Ticker()
        articles = [
            ("world", {"title": "Test headline 1"}),
            ("technology", {"title": "Test headline 2"}),
        ]
        ticker.update_headlines(articles)
        assert "Test headline 1" in ticker._plain_text
        assert "Test headline 2" in ticker._plain_text
        assert "+++" in ticker._plain_text

    def test_update_headlines_empty(self):
        from newsfeed.ticker import Ticker
        ticker = Ticker()
        ticker.update_headlines([])
        assert ticker._plain_text == ""

    def test_text_doubled_for_looping(self):
        from newsfeed.ticker import Ticker
        ticker = Ticker()
        articles = [("world", {"title": "Hello"})]
        ticker.update_headlines(articles)
        # Text should appear twice for seamless looping
        count = ticker._plain_text.count("Hello")
        assert count == 2


# ---------------------------------------------------------------------------
# Async Textual tests using App.run_test()
# ---------------------------------------------------------------------------

SAMPLE_ARTICLES = [
    {
        "title": "Breaking news story",
        "link": "https://example.com/1",
        "description": "Desc 1",
        "published": "Mon, 10 Feb 2025 12:00:00 GMT",
        "source": "TestSource",
    },
    {
        "title": "Second story",
        "link": "https://example.com/2",
        "description": "Desc 2",
        "published": "Mon, 10 Feb 2025 11:00:00 GMT",
        "source": "TestSource2",
    },
]


def _make_app() -> NewsfeedApp:
    """Create an app instance with _stream_feeds patched to no-op."""
    app = NewsfeedApp(refresh_interval=300, limit=5, use_cache=True)
    app._stream_feeds = MagicMock()  # type: ignore[method-assign]
    return app


@pytest.mark.asyncio
class TestNewsfeedAppAsync:
    """Async tests that mount the full app via run_test()."""

    async def test_compose_creates_all_widgets(self):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            # Core layout widgets
            assert app.query_one("#app-header", AppHeader)
            assert app.query_one("#ticker")
            assert app.query_one("#globe")
            assert app.query_one("#stats", StatsPanel)
            assert app.query_one("#status-bar", StatusBar)
            app.query_one("Footer")

    async def test_all_tables_exist_with_columns(self):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            from textual.widgets import DataTable
            from newsfeed.feeds import get_all_categories

            # "All" table + one per category
            all_cats = get_all_categories()
            table_all = app.query_one("#table-all", DataTable)
            assert len(table_all.columns) == 3

            for cat in all_cats:
                table = app.query_one(f"#table-{cat}", DataTable)
                assert len(table.columns) == 3

    async def test_tab_panes_exist(self):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            from textual.widgets import TabPane
            from newsfeed.feeds import get_all_categories

            # All tab + 6 category tabs = 7
            panes = app.query(TabPane)
            assert len(panes) == 7

    async def test_on_resize_hides_sidebar_narrow(self):
        app = _make_app()
        async with app.run_test(size=(80, 40)) as pilot:
            sidebar = app.query_one("#sidebar")
            # Trigger the handler (the app is already 80 wide)
            app.on_resize()
            assert sidebar.display is False

    async def test_on_resize_shows_sidebar_wide(self):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            sidebar = app.query_one("#sidebar")
            app.on_resize()
            assert sidebar.display is True

    async def test_ingest_populates_tables(self):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            from textual.widgets import DataTable

            app._initial_load = True
            app._ingest("world", SAMPLE_ARTICLES)

            # Category table should have 2 rows
            table = app.query_one("#table-world", DataTable)
            assert table.row_count == 2

            # "All" table should also have 2 rows
            table_all = app.query_one("#table-all", DataTable)
            assert table_all.row_count == 2

    async def test_ingest_updates_status_bar(self):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            app._initial_load = True
            app._ingest("technology", SAMPLE_ARTICLES)

            status = app.query_one("#status-bar", StatusBar)
            assert status.article_count == 2

    async def test_ingest_updates_stats_panel(self):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            app._initial_load = True
            app._ingest("science", SAMPLE_ARTICLES)

            stats = app.query_one("#stats", StatsPanel)
            assert stats.article_count == 2
            assert "science" in stats.category_counts
            assert stats.category_counts["science"] == 2

    async def test_ingest_updates_ticker(self):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            from newsfeed.ticker import Ticker

            app._initial_load = True
            app._ingest("world", SAMPLE_ARTICLES)

            ticker = app.query_one("#ticker", Ticker)
            assert "Breaking news story" in ticker._plain_text

    async def test_ingest_flash_and_sound_on_non_initial(self):
        """After initial load, _ingest should trigger flash animation + sound."""
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            app._initial_load = False  # simulate post-initial
            with patch("newsfeed.app.subprocess.Popen") as mock_popen:
                app._ingest("world", SAMPLE_ARTICLES)
                mock_popen.assert_called_once()

    async def test_rebuild_table(self):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            from textual.widgets import DataTable

            app._rebuild_table("table-sports", SAMPLE_ARTICLES, "sports")
            table = app.query_one("#table-sports", DataTable)
            assert table.row_count == 2

    async def test_rebuild_all_table(self):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            from textual.widgets import DataTable

            app.articles["world"] = list(SAMPLE_ARTICLES)
            app._rebuild_all_table()
            table_all = app.query_one("#table-all", DataTable)
            assert table_all.row_count == 2

    async def test_mark_cycle_done(self):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            app._mark_cycle_done()
            status = app.query_one("#status-bar", StatusBar)
            # last_refresh should be updated to a time string (HH:MM:SS)
            assert ":" in status.last_refresh

    async def test_refresh_time_column(self):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            # Inject articles first
            app._initial_load = True
            app._ingest("world", SAMPLE_ARTICLES)

            # Now refresh time column — should not raise
            app._refresh_time_column()

    async def test_action_open_article(self):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            app._initial_load = True
            app._ingest("world", SAMPLE_ARTICLES)

            # Switch to world tab by clicking on it (or just use the all tab)
            with patch("newsfeed.app.webbrowser.open") as mock_open:
                app.action_open_article()
                # The All tab is active by default and has rows
                mock_open.assert_called_once()

    async def test_action_open_article_empty_table(self):
        """action_open_article should not crash on empty tables."""
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            # No articles — should just return without error
            app.action_open_article()

    async def test_on_data_table_row_selected(self):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            from textual.widgets import DataTable

            app._initial_load = True
            app._ingest("world", SAMPLE_ARTICLES)

            with patch("newsfeed.app.webbrowser.open") as mock_open:
                # Simulate row selection event
                table = app.query_one("#table-all", DataTable)
                table.action_select_cursor()
                await pilot.pause()
                mock_open.assert_called_once()

    async def test_action_refresh_restarts_stream(self):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            app._stream_feeds.reset_mock()
            app.action_refresh()
            app._stream_feeds.assert_called_once()


@pytest.mark.asyncio
class TestAppHeaderRender:
    async def test_wide_render_shows_center_text(self):
        app = _make_app()
        async with app.run_test(size=(120, 40)) as pilot:
            header = app.query_one("#app-header", AppHeader)
            output = header.render()
            assert "NEWSFEED" in output
            assert "Live Terminal News Reader" in output

    async def test_narrow_render_compact(self):
        app = _make_app()
        async with app.run_test(size=(30, 10)) as pilot:
            header = app.query_one("#app-header", AppHeader)
            output = header.render()
            assert "NEWSFEED" in output
            # Narrow should not have center text
            assert "Live Terminal News Reader" not in output
