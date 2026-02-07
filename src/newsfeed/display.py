"""Rich terminal display — color-coded panels and tables."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from newsfeed.feeds import CATEGORY_COLORS
from newsfeed.utils import time_ago, truncate

console = Console()


def display_category(
    category: str,
    entries: list[dict],
    show_desc: bool = True,
    number_offset: int = 0,
) -> int:
    """Display a single category as a Rich panel. Returns count of articles shown."""
    if not entries:
        return 0

    color = CATEGORY_COLORS.get(category, "white")

    table = Table(
        show_header=False,
        box=None,
        padding=(0, 1),
        expand=True,
    )
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Article", ratio=1)
    table.add_column("Source", style="dim", width=18, justify="right")
    table.add_column("Time", style="dim", width=8, justify="right")

    for i, entry in enumerate(entries):
        num = str(number_offset + i + 1)
        title = Text(entry["title"], style=f"bold {color}")

        if show_desc and entry.get("description"):
            desc = truncate(entry["description"], 120)
            title.append(f"\n{desc}", style="dim")

        source = entry.get("source", "")
        ago = time_ago(entry.get("published"))

        table.add_row(num, title, source, ago)

    panel = Panel(
        table,
        title=f"[bold {color}]{category.upper()}[/bold {color}]",
        border_style=color,
        padding=(0, 1),
    )
    console.print(panel)
    return len(entries)


def display_all(
    categories_data: dict[str, list[dict]],
    show_desc: bool = True,
) -> list[dict]:
    """Display all categories. Returns flat list of all articles for --open indexing."""
    all_articles: list[dict] = []
    offset = 0
    for category, entries in categories_data.items():
        count = display_category(category, entries, show_desc, number_offset=offset)
        all_articles.extend(entries)
        offset += count
    return all_articles


def display_categories_list(categories: list[str]) -> None:
    """Show available categories with their colors."""
    console.print("\n[bold]Available categories:[/bold]\n")
    for cat in categories:
        color = CATEGORY_COLORS.get(cat, "white")
        console.print(f"  [{color}]●[/{color}] {cat}")
    console.print()
    console.print("[dim]Aliases: tech, biz, sci, sport, ent[/dim]\n")
