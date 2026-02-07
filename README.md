# newsfeed

Terminal news reader that fetches RSS feeds from major news sources and displays them as color-coded Rich panels. No API keys, no browser — just news in your terminal.

## Install

Requires [uv](https://docs.astral.sh/uv/).

```bash
# Global install (available everywhere as `newsfeed` and `news`)
uv tool install -e ~/newsfeed

# Or run from the project directory
cd ~/newsfeed && uv run newsfeed
```

## Usage

```bash
newsfeed                          # All categories overview
newsfeed tech                     # Single category
newsfeed --limit 10               # More articles per source
newsfeed --no-desc                # Headlines only
newsfeed --watch                  # Auto-refresh every 5 min
newsfeed --watch --interval 120   # Custom refresh interval
newsfeed --no-cache               # Skip cache, fetch fresh
newsfeed --list-categories        # Show available categories
newsfeed --open 3                 # Open 3rd article in browser
newsfeed --live                   # Interactive TUI with live updates
newsfeed --live --interval 60     # TUI with 60s refresh cycle
newsfeed --live --no-cache        # TUI with fresh fetches only
```

Both `newsfeed` and `news` commands work (dual entry points).

### Category aliases

| Full name       | Alias   |
|-----------------|---------|
| technology      | `tech`  |
| business        | `biz`   |
| science         | `sci`   |
| sports          | `sport` |
| entertainment   | `ent`   |

## Sources

| Category        | Sources                                              |
|-----------------|------------------------------------------------------|
| **world**       | BBC World, NPR News, NYT World                      |
| **technology**  | BBC Tech, Ars Technica, TechCrunch, NYT Tech, Hacker News, The Verge |
| **business**    | BBC Business, NYT Business, NPR Economy              |
| **science**     | BBC Science, NYT Science, NASA, Ars Technica Science |
| **sports**      | BBC Sport, ESPN, NYT Sports                          |
| **entertainment** | BBC Entertainment, NYT Arts                        |

All sources are public RSS feeds — no API keys required.

## How it works

1. **Parallel fetching** — `ThreadPoolExecutor` fetches all feeds for a category concurrently (~1-2s total)
2. **Caching** — JSON files in `~/.cache/newsfeed/` with a 10-minute TTL. Repeated runs are instant (~0.1s)
3. **Silent failure** — If a feed is down, the rest still display. No crashes on network errors
4. **HTML sanitization** — RSS descriptions are stripped of HTML tags and decoded before display

## Configuration

Optional config file at `~/.config/newsfeed/config.toml`:

```toml
limit = 5              # Articles per source (default: 5)
show_desc = true       # Show descriptions (default: true)
watch_interval = 300   # Watch mode refresh in seconds (default: 300)
```

CLI flags override config file values.

## Project structure

```
src/newsfeed/
├── cli.py        # Click CLI — args, flags, watch mode, orchestration
├── app.py        # Textual TUI — live mode with category tabs and polling
├── feeds.py      # RSS feed registry (category → source name → URL)
├── fetcher.py    # Parallel HTTP fetch + feedparser parsing
├── display.py    # Rich panels, tables, color-coded categories
├── cache.py      # JSON file cache with TTL
├── config.py     # Optional TOML user config loader
└── utils.py      # time_ago(), HTML sanitize, truncate
```

## Dependencies

- [click](https://click.palletsprojects.com/) — CLI framework
- [feedparser](https://feedparser.readthedocs.io/) — RSS/Atom parsing
- [httpx](https://www.python-httpx.org/) — HTTP client with timeouts and redirects
- [rich](https://rich.readthedocs.io/) — Terminal formatting and panels
- [textual](https://textual.textualize.io/) — TUI framework for live mode
