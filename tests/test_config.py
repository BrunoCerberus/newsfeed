"""Tests for newsfeed.config — TOML config loading with defaults."""

import newsfeed.config as config_mod
from newsfeed.config import DEFAULTS, load


class TestLoad:
    def test_missing_config_returns_defaults(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_mod, "CONFIG_PATH", tmp_path / "nonexistent.toml")
        result = load()
        assert result == DEFAULTS

    def test_valid_partial_override(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.toml"
        config_file.write_text('limit = 10\n')
        monkeypatch.setattr(config_mod, "CONFIG_PATH", config_file)
        result = load()
        assert result["limit"] == 10
        assert result["show_desc"] == DEFAULTS["show_desc"]
        assert result["watch_interval"] == DEFAULTS["watch_interval"]

    def test_invalid_toml_returns_defaults(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.toml"
        config_file.write_text("this is not valid {{{{ toml !!!!")
        monkeypatch.setattr(config_mod, "CONFIG_PATH", config_file)
        result = load()
        assert result == DEFAULTS

    def test_full_override(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            'limit = 20\nshow_desc = false\nwatch_interval = 60\n'
        )
        monkeypatch.setattr(config_mod, "CONFIG_PATH", config_file)
        result = load()
        assert result["limit"] == 20
        assert result["show_desc"] is False
        assert result["watch_interval"] == 60

    def test_returns_fresh_dict_each_time(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_mod, "CONFIG_PATH", tmp_path / "nonexistent.toml")
        a = load()
        b = load()
        assert a == b
        assert a is not b  # distinct objects
