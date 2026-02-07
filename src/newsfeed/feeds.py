"""RSS feed registry — maps categories to feed URLs."""

CATEGORIES: dict[str, dict[str, str]] = {
    "world": {
        "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "NPR News": "https://feeds.npr.org/1001/rss.xml",
        "NYT World": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    },
    "technology": {
        "BBC Tech": "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
        "TechCrunch": "https://techcrunch.com/feed/",
        "NYT Tech": "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        "Hacker News": "https://hnrss.org/frontpage",
        "The Verge": "https://www.theverge.com/rss/index.xml",
    },
    "business": {
        "BBC Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "NYT Business": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
        "NPR Economy": "https://feeds.npr.org/1006/rss.xml",
    },
    "science": {
        "BBC Science": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "NYT Science": "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
        "NASA": "https://www.nasa.gov/feed/",
        "Ars Technica Science": "https://feeds.arstechnica.com/arstechnica/science",
    },
    "sports": {
        "BBC Sport": "https://feeds.bbci.co.uk/sport/rss.xml",
        "ESPN": "https://www.espn.com/espn/rss/news",
        "NYT Sports": "https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml",
    },
    "entertainment": {
        "BBC Entertainment": "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
        "NYT Arts": "https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml",
    },
}

# Short aliases for CLI convenience
ALIASES: dict[str, str] = {
    "tech": "technology",
    "biz": "business",
    "sci": "science",
    "sport": "sports",
    "ent": "entertainment",
}

CATEGORY_COLORS: dict[str, str] = {
    "world": "bright_red",
    "technology": "bright_cyan",
    "business": "bright_green",
    "science": "bright_magenta",
    "sports": "bright_yellow",
    "entertainment": "bright_blue",
}


def resolve_category(name: str) -> str | None:
    """Resolve a category name or alias to a canonical category name."""
    name = name.lower().strip()
    if name in CATEGORIES:
        return name
    return ALIASES.get(name)


def get_all_categories() -> list[str]:
    """Return all category names."""
    return list(CATEGORIES.keys())
