"""Textual TUI app — live-streaming news feed with category tabs."""

import subprocess
import time
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
from newsfeed.utils import published_ts, time_ago


class StatusBar(Static):
    """Bottom status bar with article count and last refresh time."""

    article_count: reactive[int] = reactive(0)
    last_refresh: reactive[str] = reactive("—")

    def render(self) -> str:
        return (
            f" {self.article_count} articles"
            f" | Last: {self.last_refresh}"
        )


class NewsfeedApp(App):
    """Live TUI news reader with category tabs and continuous polling."""

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

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            # "All" tab first
            with TabPane("All", id="tab-all"):
                yield DataTable(id="table-all", cursor_type="row")
            # One tab per category
            for cat in self.all_categories:
                color = CATEGORY_COLORS.get(cat, "white")
                label = f"[{color}]{cat.capitalize()}[/{color}]"
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

        # Start the continuous polling loop
        self._stream_feeds()

    @work(thread=True, exclusive=True, group="poll")
    def _stream_feeds(self) -> None:
        """Continuously poll categories one at a time in a round-robin loop.

        Each category is fetched individually, and new articles are pushed
        to the UI immediately. After a full cycle through all categories,
        sleep for refresh_interval before starting the next cycle.
        """
        while True:
            for cat in self.all_categories:
                entries = fetch_category(
                    CATEGORIES[cat], use_cache=self.use_cache, limit=self.limit
                )
                fresh = [
                    e for e in entries
                    if e.get("link") and e["link"] not in self.seen_links
                ]
                if fresh:
                    for e in fresh:
                        self.seen_links.add(e["link"])
                    self.call_from_thread(self._ingest, cat, fresh)

            # Update the "last refresh" timestamp after a full cycle
            self.call_from_thread(self._mark_cycle_done)

            # Wait before next full cycle
            time.sleep(self.refresh_interval)

    def _ingest(self, category: str, fresh: list[dict]) -> None:
        """Add new articles and rebuild affected tables. Plays bell sound."""
        self.articles[category].extend(fresh)
        self.articles[category].sort(key=lambda e: published_ts(e.get("published")), reverse=True)

        # Rebuild this category's table
        self._rebuild_table(f"table-{category}", self.articles[category], category)

        # Rebuild "All" table
        self._rebuild_all_table()

        # Update count
        total = sum(len(v) for v in self.articles.values())
        status = self.query_one(StatusBar)
        status.article_count = total
        status.last_refresh = datetime.now().strftime("%H:%M:%S")

        # Audible notification for new articles
        subprocess.Popen(
            ["afplay", "/System/Library/Sounds/Pop.aiff"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _mark_cycle_done(self) -> None:
        status = self.query_one(StatusBar)
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
        all_entries.sort(key=lambda pair: published_ts(pair[1].get("published")), reverse=True)

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
