"""Tests for newsfeed.feeds — category registry, aliases, resolution."""

from newsfeed.feeds import (
    ALIASES,
    CATEGORIES,
    CATEGORY_COLORS,
    get_all_categories,
    resolve_category,
)

EXPECTED_CATEGORIES = {"world", "technology", "business", "science", "sports", "entertainment"}


class TestCategoriesRegistry:
    def test_all_six_categories_exist(self):
        assert set(CATEGORIES.keys()) == EXPECTED_CATEGORIES

    def test_each_category_has_sources(self):
        for cat, sources in CATEGORIES.items():
            assert len(sources) > 0, f"{cat} has no sources"

    def test_sources_are_dicts_with_string_values(self):
        for cat, sources in CATEGORIES.items():
            for name, url in sources.items():
                assert isinstance(name, str)
                assert isinstance(url, str)
                assert url.startswith("http"), f"{cat}/{name} URL doesn't start with http"


class TestCategoryColors:
    def test_every_category_has_a_color(self):
        for cat in CATEGORIES:
            assert cat in CATEGORY_COLORS, f"{cat} missing from CATEGORY_COLORS"

    def test_colors_are_strings(self):
        for cat, color in CATEGORY_COLORS.items():
            assert isinstance(color, str)
            assert len(color) > 0


class TestAliases:
    def test_all_aliases_map_to_valid_categories(self):
        for alias, target in ALIASES.items():
            assert target in CATEGORIES, f"Alias '{alias}' maps to unknown category '{target}'"

    def test_expected_aliases_exist(self):
        assert "tech" in ALIASES
        assert "biz" in ALIASES
        assert "sci" in ALIASES
        assert "sport" in ALIASES
        assert "ent" in ALIASES


class TestResolveCategory:
    def test_exact_match(self):
        assert resolve_category("technology") == "technology"

    def test_alias(self):
        assert resolve_category("tech") == "technology"

    def test_case_insensitive(self):
        assert resolve_category("WORLD") == "world"
        assert resolve_category("Technology") == "technology"

    def test_whitespace_stripped(self):
        assert resolve_category("  science  ") == "science"

    def test_unknown_returns_none(self):
        assert resolve_category("nonexistent") is None

    def test_empty_returns_none(self):
        assert resolve_category("") is None


class TestGetAllCategories:
    def test_returns_six_items(self):
        result = get_all_categories()
        assert len(result) == 6

    def test_matches_categories_keys(self):
        result = get_all_categories()
        assert set(result) == EXPECTED_CATEGORIES

    def test_returns_list(self):
        assert isinstance(get_all_categories(), list)
