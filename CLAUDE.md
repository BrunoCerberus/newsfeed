# CLAUDE.md — newsfeed

## What this project is

A Python CLI tool that reads RSS news feeds and displays them in the terminal with Rich panels. Installed globally via `uv tool install -e .` as both `newsfeed` and `news` commands.

## Tech stack

- **Python 3.14** with `uv` for package management
- **click** for CLI parsing (not typer — lighter, no transitive deps)
- **httpx** for HTTP requests (not requests — modern API, built-in timeout/redirects)
- **feedparser** for RSS/Atom parsing
- **rich** for terminal panels, tables, and color output

## Architecture

```
src/newsfeed/
├── cli.py        # Entry point. Click command with all flags. Wires fetcher → display
├── feeds.py      # Pure data: CATEGORIES dict (category → {source_name → url}), ALIASES, CATEGORY_COLORS
├── fetcher.py    # ThreadPoolExecutor fetches all sources in parallel, feedparser parses XML
├── display.py    # Rich Console, Panel, Table. One panel per category, color-coded
├── cache.py      # JSON files in ~/.cache/newsfeed/, keyed by SHA256(url)[:16], TTL via mtime
├── config.py     # Reads ~/.config/newsfeed/config.toml with tomllib, merges with DEFAULTS
└── utils.py      # time_ago() (RFC 2822 → "3h ago"), sanitize_html(), truncate()
```

## Key patterns

- **Data flows one way**: `cli.py` calls `fetcher.fetch_category()` which returns `list[dict]`, then passes to `display.display_category()` or `display.display_all()`
- **Each article is a plain dict** with keys: `title`, `link`, `description`, `published`, `source`
- **Cache is per-URL**: each RSS feed URL gets its own JSON file. Cache checks happen inside `fetcher._fetch_and_parse()`
- **Categories are defined in `feeds.CATEGORIES`** — to add a source, just add an entry there. No other file needs changes
- **Aliases in `feeds.ALIASES`** map short names (tech, biz, sci, sport, ent) to full category names
- **Colors in `feeds.CATEGORY_COLORS`** map each category to a Rich color string

## Common tasks

### Add a new RSS source
Edit `feeds.py` → add to the relevant category dict in `CATEGORIES`. That's it.

### Add a new category
1. Add the category dict to `CATEGORIES` in `feeds.py`
2. Add a color to `CATEGORY_COLORS`
3. Optionally add an alias to `ALIASES`

### Change cache TTL
`cache.py:DEFAULT_TTL` (currently 600 seconds / 10 minutes).

### Change default article limit
`config.py:DEFAULTS["limit"]` (currently 5).

## Running

```bash
uv run newsfeed              # Development
newsfeed                     # After global install with uv tool install -e .
```

## File locations

- Cache: `~/.cache/newsfeed/*.json`
- Config: `~/.config/newsfeed/config.toml` (optional, created by user)
