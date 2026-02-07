"""Tests for newsfeed.app — TUI app logic (no UI interactions)."""

from newsfeed.app import NewsfeedApp, StatusBar


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
