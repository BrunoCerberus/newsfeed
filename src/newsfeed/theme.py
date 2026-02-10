"""Custom 'deep space newsroom' dark theme for the TUI."""

from textual.theme import Theme

NEWSFEED_THEME = Theme(
    name="newsfeed-dark",
    primary="#58a6ff",
    secondary="#f78166",
    accent="#bc8cff",
    background="#0d1117",
    surface="#161b22",
    panel="#21262d",
    warning="#d29922",
    error="#f85149",
    success="#3fb950",
    dark=True,
    variables={
        "footer-background": "#161b22",
        "footer-key-foreground": "#58a6ff",
        "footer-description-foreground": "#8b949e",
        "scrollbar-background": "#161b22",
        "scrollbar-color": "#30363d",
        "scrollbar-color-hover": "#484f58",
        "scrollbar-color-active": "#58a6ff",
        "input-cursor-foreground": "#58a6ff",
    },
)
