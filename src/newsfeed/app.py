"""Textual TUI app — live-streaming news feed with category tabs."""

import webbrowser
from datetime import datetime

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Header, Static, TabbedContent, TabPane
from textual import work

from newsfeed.feeds import CATEGORIES, CATEGORY_COLORS, get_all_categories
from newsfeed.fetcher import fetch_category
from newsfeed.utils import time_ago


class StatusBar(Static):
    """Bottom status bar with article count, last refresh, and countdown."""

    article_count: reactive[int] = reactive(0)
    last_refresh: reactive[str] = reactive("—")
    countdown: reactive[int] = reactive(0)

    def render(self) -> str:
        return (
            f" {self.article_count} articles"
            f" | Last: {self.last_refresh}"
            f" | Next in: {self.countdown}s"
        )


class NewsfeedApp(App):
    """Live TUI news reader with category tabs and background polling."""

    TITLE = "newsfeed — live mode"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("enter", "open_article", "Open"),
    ]

    CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    DataTable {
        height: 1fr;
    }
    """

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
        # category -> list of article dicts
        self.articles: dict[str, list[dict]] = {cat: [] for cat in self.all_categories}
        self.seen_links: set[str] = set()
        self._countdown = self.refresh_interval

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            # "All" tab first
            with TabPane("All", id="tab-all"):
                yield DataTable(id="table-all", cursor_type="row")
            # One tab per category
            for cat in self.all_categories:
                color = CATEGORY_COLORS.get(cat, "white")
                label = Text(cat.capitalize(), style=color)
                with TabPane(label, id=f"tab-{cat}"):
                    yield DataTable(id=f"table-{cat}", cursor_type="row")
        yield StatusBar()
        yield Footer()

    def on_mount(self) -> None:
        # Set up columns on every table
        table_ids = ["table-all"] + [f"table-{cat}" for cat in self.all_categories]
        for tid in table_ids:
            table = self.query_one(f"#{tid}", DataTable)
            table.add_columns("Title", "Source", "Time")

        # Initial fetch + timers
        self._poll_feeds()
        self.set_interval(self.refresh_interval, self._poll_feeds)
        self.set_interval(1, self._tick_countdown)

    def _tick_countdown(self) -> None:
        self._countdown = max(0, self._countdown - 1)
        self.query_one(StatusBar).countdown = self._countdown

    @work(thread=True, exclusive=True)
    def _poll_feeds(self) -> None:
        """Fetch all categories in a background thread."""
        new_articles: dict[str, list[dict]] = {}
        for cat in self.all_categories:
            entries = fetch_category(
                CATEGORIES[cat], use_cache=self.use_cache, limit=self.limit
            )
            fresh = [e for e in entries if e.get("link") and e["link"] not in self.seen_links]
            if fresh:
                new_articles[cat] = fresh
                for e in fresh:
                    self.seen_links.add(e["link"])

        if new_articles:
            self.call_from_thread(self._merge_and_rebuild, new_articles)
        else:
            self.call_from_thread(self._update_status_only)

    def _update_status_only(self) -> None:
        self._countdown = self.refresh_interval
        status = self.query_one(StatusBar)
        status.last_refresh = datetime.now().strftime("%H:%M:%S")
        status.countdown = self._countdown

    def _merge_and_rebuild(self, new_articles: dict[str, list[dict]]) -> None:
        # Merge new articles into stores
        for cat, entries in new_articles.items():
            self.articles[cat].extend(entries)
            # Sort by published date descending
            self.articles[cat].sort(
                key=lambda e: e.get("published", ""), reverse=True
            )

        # Rebuild per-category tables
        for cat in self.all_categories:
            self._rebuild_table(f"table-{cat}", self.articles[cat], cat)

        # Rebuild "All" table — merge all categories, sorted
        all_entries = []
        for cat in self.all_categories:
            for entry in self.articles[cat]:
                all_entries.append((cat, entry))
        all_entries.sort(key=lambda pair: pair[1].get("published", ""), reverse=True)
        self._rebuild_all_table(all_entries)

        # Update status
        total = sum(len(v) for v in self.articles.values())
        self._countdown = self.refresh_interval
        status = self.query_one(StatusBar)
        status.article_count = total
        status.last_refresh = datetime.now().strftime("%H:%M:%S")
        status.countdown = self._countdown

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

    def _rebuild_all_table(self, entries: list[tuple[str, dict]]) -> None:
        table = self.query_one("#table-all", DataTable)
        table.clear()
        for cat, entry in entries:
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
        """Force an immediate refresh."""
        self._poll_feeds()

    def action_open_article(self) -> None:
        """Open the currently highlighted article."""
        # Find the active DataTable in the currently visible tab
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
