"""Tests for newsfeed.app — TUI app logic (no UI interactions)."""

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
        from newsfeed.globe import _generate_frames, NUM_FRAMES, GLOBE_HEIGHT
        frames = _generate_frames()
        assert len(frames) == NUM_FRAMES
        for frame in frames:
            assert len(frame) == GLOBE_HEIGHT
            for row in frame:
                assert isinstance(row, str)
                assert len(row) > 0

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
