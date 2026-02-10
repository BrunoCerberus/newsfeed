# AGENTS.md — newsfeed

## Project overview

`newsfeed` is a terminal news reader CLI built in Python. It fetches RSS feeds from ~20 major news sources across 6 categories and renders them as color-coded Rich panels. Runs as a global command via `uv tool install`.

## Module responsibilities

### `cli.py` — Orchestrator
The only module that imports from all others. Defines the Click command with all CLI flags and arguments. Handles watch mode (loop + sleep), open-in-browser (`webbrowser.open`), and category resolution. Loads user config at module level. The `--live` flag early-returns into `app.run_live()` before any existing logic runs (lazy import for zero cost when not used).

### `app.py` — Textual TUI (live mode)
Full-screen interactive app launched by `--live`. Layout: `AppHeader` (branded title + live clock), `Ticker` (scrolling headlines), `Horizontal` sidebar (`Globe` + `StatsPanel`) beside `TabbedContent` with one `DataTable` per category tab plus an "All" tab. Tab labels include category emoji icons. Background polling via `@work(thread=True, exclusive=True)` calls `fetcher.fetch_category()` in an OS thread and pushes updates to the UI via `call_from_thread()`. Deduplicates articles by link. New articles trigger a blue tint flash animation on the affected table and update the ticker. Sidebar hides responsively when terminal width < 90 columns. Key bindings: `q` quit, `r` force refresh, `Enter` open article in browser. Uses external `app.tcss` stylesheet and custom theme from `theme.py`.

### `app.tcss` — TUI stylesheet
External Textual CSS for the TUI layout. Styles all widgets: screen, header, ticker, globe, sidebar, tabs (with 200ms hover/active transitions), DataTable (alternating row colors, cursor highlight), StatusBar, and Footer. Category color classes use `ansi_bright_*` names.

### `globe.py` — Rotating ASCII globe
Custom Textual `Widget` that renders a rotating Earth. Pre-computes 60 frames (~14ms) using spherical projection with continent bounding boxes. Ocean = blue chars, Land = green chars, Ice caps = white. Frame index cycles via `set_interval(0.15s)`. 24x13 character grid. `pause()`/`resume()` methods for visibility control.

### `ticker.py` — Scrolling news ticker
Horizontal scrolling headline bar widget. Concatenates latest headlines with `+++` separators, doubled for seamless looping. `set_interval(0.12s)` shifts offset by 1 char. Headlines colored by category via `CATEGORY_COLORS`. `update_headlines(articles)` called by app after each fetch cycle.

### `theme.py` — Custom dark theme
Registers a Textual `Theme` named `newsfeed-dark`. Background: `#0d1117` (dark navy), Surface: `#161b22`, Panel: `#21262d`. Primary: `#58a6ff` (bright blue), Secondary: `#f78166` (warm orange), Accent: `#bc8cff` (purple). Also sets footer, scrollbar, and input cursor color variables.

### `feeds.py` — Data registry
Pure data, no I/O. Four dicts:
- `CATEGORIES`: `{category_name: {source_name: rss_url}}` — the single source of truth for what gets fetched
- `ALIASES`: short names → full category names (e.g., `tech` → `technology`)
- `CATEGORY_COLORS`: category → Rich color string for display
- `CATEGORY_ICONS`: category → emoji for TUI tab labels (e.g., `world` → 🌍)

Two helper functions: `resolve_category()` and `get_all_categories()`.

### `fetcher.py` — Network layer
`fetch_category(sources, use_cache, limit)` is the main entry point. Uses `ThreadPoolExecutor(max_workers=8)` to fetch all sources in a category concurrently. Each feed goes through:
1. Cache check (if enabled)
2. `httpx.get()` with 10s timeout and redirect following
3. `feedparser.parse()` on the response text
4. Entries normalized to dicts with: `title`, `link`, `description`, `published`, `source`
5. Cache write (if enabled)

Returns merged entries sorted by `published` date descending. Silent failure: HTTP errors return empty list.

### `display.py` — Presentation layer
Owns the `rich.Console` instance. Two display functions:
- `display_category()` — one Rich Panel containing a Table. Articles are numbered (with offset for global numbering across categories). Shows title (bold + category color), optional description (dim), source name, and relative time.
- `display_all()` — iterates categories, calls `display_category()` with running offset, returns flat article list for `--open` indexing.

### `cache.py` — Persistence layer
File-based JSON cache in `~/.cache/newsfeed/`. Cache key = `SHA256(url)[:16]`. TTL checked via file mtime (default 600s). Three functions: `get()`, `put()`, `_cache_path()`.

### `config.py` — Configuration
Reads `~/.config/newsfeed/config.toml` using stdlib `tomllib`. Merges with `DEFAULTS` dict. Config is optional — sensible defaults built in.

### `utils.py` — Pure functions
- `time_ago(published_str)` — parses RFC 2822 date strings, returns "3h ago" style relative time
- `sanitize_html(text)` — `html.unescape()` + regex strip tags + collapse whitespace
- `truncate(text, max_len)` — word-boundary truncation with ellipsis

## Data flow

### Standard mode
```
User runs CLI
    → cli.py parses args via Click
    → cli.py resolves category (feeds.resolve_category)
    → cli.py calls fetcher.fetch_category(sources_dict)
        → fetcher spawns ThreadPoolExecutor
        → each thread: cache.get() → httpx.get() → feedparser.parse() → cache.put()
        → returns sorted list[dict]
    → cli.py passes entries to display.display_category() or display.display_all()
        → display builds Rich Panel + Table
        → prints to console
```

### Live TUI mode (`--live`)
```
User runs CLI with --live
    → cli.py early-returns into app.run_live()
    → NewsfeedApp registers custom theme, composes layout:
        AppHeader (clock ticks every 1s)
        Ticker (scrolls every 0.12s)
        Horizontal: Sidebar (Globe rotates every 0.15s, StatsPanel) + TabbedContent + DataTables
        StatusBar + Footer
    → on_mount() triggers _stream_feeds() + sets 30s time-column refresh timer
    → _stream_feeds() runs in @work(thread=True)
        → round-robin fetches each category via fetcher.fetch_category()
        → deduplicates by link
        → call_from_thread(_ingest)
            → rebuilds DataTables + StatusBar + StatsPanel
            → updates Ticker headlines
            → triggers flash animation on affected table
            → plays notification sound (after initial load)
    → sleeps refresh_interval, then repeats cycle
```

## Design constraints

- **No API keys** — only public RSS feeds. Adding a source that requires authentication would need changes to `fetcher._fetch_and_parse()`
- **No async** — uses `ThreadPoolExecutor` for parallelism. Simpler than asyncio for I/O-bound RSS fetching with ~20 feeds
- **Articles are plain dicts** — no dataclass or model. Keys: `title`, `link`, `description`, `published`, `source`
- **One console instance** — shared via `display.console`, imported by `cli.py`
- **Cache is append-only** — no eviction. Old files expire by TTL and get overwritten on next fetch

## Extending

To add a new feature, the typical pattern is:
1. Add any new data/config to `feeds.py` or `config.py`
2. Add processing logic to `fetcher.py` if it involves data
3. Add display logic to `display.py` if it involves output
4. Wire it together in `cli.py` with a new Click option
5. For TUI-specific features, extend `app.py` (new widgets, key bindings, or worker methods)
