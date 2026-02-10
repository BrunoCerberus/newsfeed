"""Scrolling news ticker widget — horizontal headline bar."""

from __future__ import annotations

from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

from newsfeed.feeds import CATEGORY_COLORS

_SEPARATOR = "  +++  "
_SEPARATOR_STYLE = "dim #484f58"
_BULLET = " \u25cf "  # ●


class Ticker(Widget):
    """Horizontal scrolling news headline ticker."""

    DEFAULT_CSS = """
    Ticker {
        height: 1;
        width: 1fr;
    }
    """

    offset: reactive[int] = reactive(0)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._plain_text = ""
        self._styled_text = Text("")
        self._timer = None

    def on_mount(self) -> None:
        self._timer = self.set_interval(0.12, self._scroll)

    def _scroll(self) -> None:
        if len(self._plain_text) == 0:
            return
        self.offset = (self.offset + 1) % len(self._plain_text)

    def watch_offset(self) -> None:
        self.refresh()

    def update_headlines(self, articles: list[tuple[str, dict]]) -> None:
        """Rebuild the ticker text from (category, article) pairs."""
        if not articles:
            return
        text = Text("")
        plain = ""
        for i, (cat, article) in enumerate(articles[:30]):
            if i > 0:
                text.append(_SEPARATOR, style=_SEPARATOR_STYLE)
                plain += _SEPARATOR
            color = CATEGORY_COLORS.get(cat, "white")
            bullet_text = _BULLET
            title = article.get("title", "")
            text.append(bullet_text, style=f"bold {color}")
            text.append(title, style=color)
            plain += bullet_text + title

        # Double the text for seamless looping
        sep = Text(_SEPARATOR, style=_SEPARATOR_STYLE)
        self._styled_text = text + sep + text.copy()
        self._plain_text = plain + _SEPARATOR + plain
        self.offset = 0

    def render(self) -> Text:
        if len(self._plain_text) == 0:
            return Text("")

        width = self.size.width
        total_len = len(self._plain_text)

        start = self.offset % total_len
        styled = self._styled_text
        styled_len = len(styled.plain)
        if styled_len == 0:
            return Text("")

        # Crop the styled text to visible window
        visible = styled[start : start + width]
        # Wrap around for seamless looping
        if len(visible.plain) < width:
            remaining = width - len(visible.plain)
            visible = visible + styled[:remaining]

        return visible

    def pause(self) -> None:
        if self._timer is not None:
            self._timer.stop()

    def resume(self) -> None:
        if self._timer is not None:
            self._timer.resume()
