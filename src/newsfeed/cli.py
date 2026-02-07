"""CLI entry point — Click commands, flags, watch mode, open-in-browser."""

import time
import webbrowser

import click
from rich.console import Console

from newsfeed import config as cfg
from newsfeed.display import console, display_all, display_categories_list, display_category
from newsfeed.feeds import CATEGORIES, get_all_categories, resolve_category
from newsfeed.fetcher import fetch_category

user_config = cfg.load()


@click.command()
@click.argument("category", required=False, default=None)
@click.option("--limit", "-l", default=None, type=int, help="Articles per source.")
@click.option("--no-desc", is_flag=True, help="Headlines only, hide descriptions.")
@click.option("--no-cache", is_flag=True, help="Force fresh fetch, skip cache.")
@click.option("--watch", "-w", is_flag=True, help="Auto-refresh periodically.")
@click.option("--interval", "-i", default=None, type=int, help="Watch refresh interval in seconds.")
@click.option("--list-categories", is_flag=True, help="Show available categories.")
@click.option("--open", "open_num", default=None, type=int, help="Open Nth article in browser.")
def main(
    category: str | None,
    limit: int | None,
    no_desc: bool,
    no_cache: bool,
    watch: bool,
    interval: int | None,
    list_categories: bool,
    open_num: int | None,
) -> None:
    """Read categorized news from RSS feeds in your terminal."""
    if list_categories:
        display_categories_list(get_all_categories())
        return

    limit = limit or user_config["limit"]
    show_desc = (not no_desc) and user_config["show_desc"]
    use_cache = not no_cache
    watch_interval = interval or user_config["watch_interval"]

    # Determine which categories to show
    if category:
        resolved = resolve_category(category)
        if resolved is None:
            console.print(f"[red]Unknown category: {category}[/red]")
            console.print("[dim]Use --list-categories to see available options.[/dim]")
            raise SystemExit(1)
        target_categories = [resolved]
    else:
        target_categories = get_all_categories()

    def run_once() -> list[dict]:
        console.clear()
        console.print(
            "[bold]📰 newsfeed[/bold] [dim]— terminal news reader[/dim]\n"
        )

        if len(target_categories) == 1:
            cat = target_categories[0]
            entries = fetch_category(CATEGORIES[cat], use_cache=use_cache, limit=limit)
            display_category(cat, entries, show_desc)
            return entries
        else:
            data: dict[str, list[dict]] = {}
            for cat in target_categories:
                entries = fetch_category(CATEGORIES[cat], use_cache=use_cache, limit=limit)
                if entries:
                    data[cat] = entries
            return display_all(data, show_desc)

    if open_num is not None:
        articles = run_once()
        if 1 <= open_num <= len(articles):
            url = articles[open_num - 1].get("link", "")
            if url:
                console.print(f"\n[dim]Opening article #{open_num} in browser…[/dim]")
                webbrowser.open(url)
            else:
                console.print(f"[red]Article #{open_num} has no URL.[/red]")
        else:
            console.print(f"[red]Invalid article number: {open_num} (1-{len(articles)})[/red]")
        return

    if watch:
        try:
            while True:
                run_once()
                console.print(
                    f"\n[dim]Refreshing in {watch_interval}s… (Ctrl+C to quit)[/dim]"
                )
                time.sleep(watch_interval)
        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye![/dim]")
    else:
        run_once()
