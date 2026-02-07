"""Optional user configuration from ~/.config/newsfeed/config.toml."""

import tomllib
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "newsfeed" / "config.toml"

DEFAULTS = {
    "limit": 5,
    "show_desc": True,
    "watch_interval": 300,
}


def load() -> dict:
    """Load user config, falling back to defaults for missing keys."""
    config = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            user_config = tomllib.loads(CONFIG_PATH.read_text())
            config.update(user_config)
        except Exception:
            pass
    return config
