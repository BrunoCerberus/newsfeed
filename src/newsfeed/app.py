"""Textual TUI app — live-streaming news feed with rotating globe and ticker."""

import subprocess
import time
import webbrowser
from datetime import datetime

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Static, TabbedContent, TabPane
from textual import work
from textual.worker import get_current_worker

from newsfeed.feeds import (
    CATEGORIES,
    CATEGORY_COLORS,
    CATEGORY_ICONS,
    get_all_categories,
)
from newsfeed.fetcher import fetch_category
from newsfeed.globe import Globe
from newsfeed.theme import NEWSFEED_THEME
from newsfeed.ticker import Ticker
from newsfeed.utils import published_ts, time_ago


class AppHeader(Static):
    """Branded header bar with app name and live clock."""

    clock: reactive[str] = reactive("")

    def on_mount(self) -> None:
        self.clock = datetime.now().strftime("%H:%M:%S")
        self.set_interval(1, self._tick)

    def _tick(self) -> None:
        self.clock = datetime.now().strftime("%H:%M:%S")

    def watch_clock(self) -> None:
        self.refresh()

    def render(self) -> str:
        width = self.size.width
        left = "\u25c6 NEWSFEED"
        center = "Live Terminal News Reader"
        right = self.clock
        # Calculate spacing
        gap = width - len(left) - len(center) - len(right)
        if gap < 2:
            return f"{left}  {right}"
        left_gap = (gap // 2)
        right_gap = gap - left_gap
        return f"{left}{' ' * left_gap}{center}{' ' * right_gap}{right}"


class StatsPanel(Static):
    """Article count display with category color dots."""

    article_count: reactive[int] = reactive(0)
    category_counts: reactive[dict] = reactive({})

    def render(self) -> str:
        lines = [f"[bold]{self.article_count}[/bold]", "[dim]total articles[/dim]", ""]
        counts = self.category_counts
        if counts:
            for cat, count in counts.items():
                color = CATEGORY_COLORS.get(cat, "white")
                icon = CATEGORY_ICONS.get(cat, "")
                name = cat.capitalize()
                lines.append(f"[{color}]{icon} {name}: {count}[/{color}]")
        return "\n".join(lines)


class StatusBar(Static):
    """Bottom status bar with article count and last refresh time."""

    article_count: reactive[int] = reactive(0)
    last_refresh: reactive[str] = reactive("\u2014")

    def render(self) -> str:
        return (
            f" {self.article_count} articles"
            f" | Last: {self.last_refresh}"
            f" | r:Refresh | q:Quit | enter:Open"
        )


class NewsfeedApp(App):
    """Live TUI news reader with globe, ticker, and category tabs."""

    TITLE = "newsfeed"
    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("enter", "open_article", "Open"),
    ]

    def __init__(
        self,
        refresh_interval: int = 300,
        limit: int = 5,
        use_cache: bool = True,
    ) -> None:
        super().__init__()
        self.refresh_interval = refresh_interval
        self.limit = limit
        self.use_cache = use_cache
        self.all_categories = get_all_categories()
        self.articles: dict[str, list[dict]] = {cat: [] for cat in self.all_categories}
        self.seen_links: set[str] = set()
        self._initial_load = True
        self.register_theme(NEWSFEED_THEME)
        self.theme = "newsfeed-dark"

    def compose(self) -> ComposeResult:
        yield AppHeader(id="app-header")
        yield Ticker(id="ticker")
        with Horizontal(id="main-content"):
            with Vertical(id="sidebar"):
                yield Globe(id="globe")
                yield StatsPanel(id="stats")
            with Vertical(id="news-panel"):
                with TabbedContent():
                    # "All" tab first
                    with TabPane("All", id="tab-all"):
                        yield DataTable(id="table-all", cursor_type="row")
                    # Category tabs with icons
                    for cat in self.all_categories:
                        icon = CATEGORY_ICONS.get(cat, "")
                        color = CATEGORY_COLORS.get(cat, "white")
                        label = f"{icon} [{color}]{cat.capitalize()}[/{color}]"
                        with TabPane(label, id=f"tab-{cat}"):
                            yield DataTable(id=f"table-{cat}", cursor_type="row")
        yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        # Set up columns on every table
        table_ids = ["table-all"] + [f"table-{cat}" for cat in self.all_categories]
        for tid in table_ids:
            table = self.query_one(f"#{tid}", DataTable)
            table.add_columns("Title", "Source", "Time")

        # Start continuous polling
        self._stream_feeds()
        # Refresh "time ago" column every 30s
        self.set_interval(30, self._refresh_time_column)

    def on_resize(self) -> None:
        """Hide sidebar on narrow terminals."""
        sidebar = self.query_one("#sidebar")
        if self.size.width < 90:
            sidebar.display = False
        else:
            sidebar.display = True

    @work(thread=True, exclusive=True, group="poll")
    def _stream_feeds(self) -> None:
        """Continuously poll categories in round-robin, push new articles to UI."""
        worker = get_current_worker()
        while not worker.is_cancelled:
            for cat in self.all_categories:
                if worker.is_cancelled:
                    return
                try:
                    entries = fetch_category(
                        CATEGORIES[cat], use_cache=self.use_cache, limit=self.limit
                    )
                except Exception:
                    continue
                fresh = [
                    e for e in entries
                    if e.get("link") and e["link"] not in self.seen_links
                ]
                if fresh:
                    for e in fresh:
                        self.seen_links.add(e["link"])
                    self.call_from_thread(self._ingest, cat, fresh)

            if self._initial_load:
                self._initial_load = False

            self.call_from_thread(self._mark_cycle_done)

            for _ in range(self.refresh_interval):
                if worker.is_cancelled:
                    return
                time.sleep(1)

    def _ingest(self, category: str, fresh: list[dict]) -> None:
        """Add new articles, rebuild tables, update ticker, flash animation."""
        self.articles[category].extend(fresh)
        self.articles[category].sort(
            key=lambda e: published_ts(e.get("published")), reverse=True
        )

        # Rebuild category table
        self._rebuild_table(f"table-{category}", self.articles[category], category)

        # Rebuild "All" table
        self._rebuild_all_table()

        # Update counts
        total = sum(len(v) for v in self.articles.values())
        status = self.query_one("#status-bar", StatusBar)
        status.article_count = total
        status.last_refresh = datetime.now().strftime("%H:%M:%S")

        # Update stats panel
        stats = self.query_one("#stats", StatsPanel)
        stats.article_count = total
        stats.category_counts = {
            cat: len(entries) for cat, entries in self.articles.items() if entries
        }

        # Update ticker with latest headlines from all categories
        all_headlines: list[tuple[str, dict]] = []
        for cat in self.all_categories:
            for entry in self.articles[cat]:
                all_headlines.append((cat, entry))
        all_headlines.sort(
            key=lambda pair: published_ts(pair[1].get("published")), reverse=True
        )
        ticker = self.query_one("#ticker", Ticker)
        ticker.update_headlines(all_headlines[:30])

        # Flash animation on the affected table
        if not self._initial_load:
            try:
                table = self.query_one(f"#table-{category}", DataTable)
                table.styles.animate(
                    "tint", "rgba(88,166,255,0.3)", duration=0.0, final_value="rgba(88,166,255,0)"
                )
                table.styles.animate(
                    "tint", "rgba(88,166,255,0)", duration=0.8
                )
            except Exception:
                pass

            # Audible notification
            subprocess.Popen(
                ["afplay", "/System/Library/Sounds/Glass.aiff"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    def _refresh_time_column(self) -> None:
        """Update the Time column on all tables so relative times stay accurate."""
        time_lookup: dict[str, str] = {}
        for cat in self.all_categories:
            for entry in self.articles[cat]:
                link = entry.get("link", "")
                if link:
                    time_lookup[link] = time_ago(entry.get("published"))

        table_ids = ["table-all"] + [f"table-{cat}" for cat in self.all_categories]
        for tid in table_ids:
            table = self.query_one(f"#{tid}", DataTable)
            col_keys = list(table.columns.keys())
            if len(col_keys) < 3:
                continue
            time_col_key = col_keys[2]
            for row_key in table.rows:
                link = str(row_key.value)
                ago = time_lookup.get(link, "")
                table.update_cell(row_key, time_col_key, ago)

    def _mark_cycle_done(self) -> None:
        status = self.query_one("#status-bar", StatusBar)
        status.last_refresh = datetime.now().strftime("%H:%M:%S")

    def _rebuild_table(
        self, table_id: str, entries: list[dict], category: str
    ) -> None:
        table = self.query_one(f"#{table_id}", DataTable)
        table.clear()
        color = CATEGORY_COLORS.get(category, "white")
        for entry in entries:
            link = entry.get("link", "")
            title = Text(entry.get("title", ""), style=f"bold {color}")
            source = entry.get("source", "")
            ago = time_ago(entry.get("published"))
            table.add_row(title, source, ago, key=link)

    def _rebuild_all_table(self) -> None:
        all_entries: list[tuple[str, dict]] = []
        for cat in self.all_categories:
            for entry in self.articles[cat]:
                all_entries.append((cat, entry))
        all_entries.sort(
            key=lambda pair: published_ts(pair[1].get("published")), reverse=True
        )

        table = self.query_one("#table-all", DataTable)
        table.clear()
        for cat, entry in all_entries:
            link = entry.get("link", "")
            color = CATEGORY_COLORS.get(cat, "white")
            title = Text(entry.get("title", ""), style=f"bold {color}")
            source = entry.get("source", "")
            ago = time_ago(entry.get("published"))
            table.add_row(title, source, ago, key=link)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Open the selected article in the browser."""
        link = str(event.row_key.value)
        if link:
            webbrowser.open(link)

    def action_refresh(self) -> None:
        """Force an immediate refresh (restarts the streaming loop)."""
        self._stream_feeds()

    def action_open_article(self) -> None:
        """Open the currently highlighted article."""
        try:
            tabbed = self.query_one(TabbedContent)
            active_pane = tabbed.active_pane
            if active_pane is None:
                return
            table = active_pane.query_one(DataTable)
            if table.cursor_row is not None and table.row_count > 0:
                row_key, _ = table.coordinate_to_cell_key(
                    table.cursor_coordinate
                )
                link = str(row_key.value)
                if link:
                    webbrowser.open(link)
        except Exception:
            pass


def run_live(
    refresh_interval: int = 300,
    limit: int = 5,
    use_cache: bool = True,
) -> None:
    """Entry point called from cli.py when --live is used."""
    app = NewsfeedApp(
        refresh_interval=refresh_interval,
        limit=limit,
        use_cache=use_cache,
    )
    app.run()
