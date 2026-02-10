"""Rotating ASCII globe widget — pre-computed spherical Earth projection."""

from __future__ import annotations

import math

from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

# Simplified continent bounding boxes as (min_lat, max_lat, min_lon, max_lon)
# Rough approximations covering major landmasses
_CONTINENTS: list[tuple[float, float, float, float]] = [
    # North America
    (25, 70, -130, -60),
    # Central America
    (10, 25, -120, -75),
    # South America
    (-55, 10, -80, -35),
    # Europe
    (36, 70, -10, 40),
    # Africa
    (-35, 37, -17, 51),
    # Middle East
    (12, 42, 25, 60),
    # Russia / Northern Asia
    (50, 75, 40, 180),
    # South/Southeast Asia
    (5, 50, 60, 140),
    # India
    (8, 35, 68, 90),
    # Australia
    (-40, -12, 113, 155),
    # Japan/Korea
    (30, 46, 125, 146),
    # UK/Ireland
    (50, 60, -11, 2),
    # Scandinavia
    (55, 71, 5, 30),
    # Indonesia
    (-8, 5, 95, 140),
    # Greenland
    (60, 84, -73, -12),
]

# Characters and colors for rendering
_OCEAN_CHARS = ". ~.`"
_LAND_CHARS = ".:+*#"
_ICE_CHAR = "*"

_OCEAN_STYLES = ["#1a3a5c", "#1e4068", "#224674", "#1a3a5c", "#163050"]
_LAND_STYLES = ["#2d5a1e", "#337722", "#3d8b2a", "#478f30", "#52a338"]
_ICE_STYLE = "#c8d6e5"

NUM_FRAMES = 60
GLOBE_WIDTH = 24
GLOBE_HEIGHT = 13


def _is_land(lat: float, lon: float) -> bool:
    """Check if a lat/lon coordinate is over land (using bounding boxes)."""
    for min_lat, max_lat, min_lon, max_lon in _CONTINENTS:
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return True
    return False


def _is_ice(lat: float) -> bool:
    """Check if latitude is in polar ice cap region."""
    return abs(lat) > 72


def _generate_frames() -> list[list[str]]:
    """Pre-compute all globe frames as lists of Rich-markup strings (one per row)."""
    frames: list[list[str]] = []
    cx = GLOBE_WIDTH / 2
    cy = GLOBE_HEIGHT / 2
    # Radius in each dimension (slightly less than half to leave margin)
    rx = cx - 1.0
    ry = cy - 0.5

    for f in range(NUM_FRAMES):
        lon_offset = (f / NUM_FRAMES) * 360.0
        rows: list[str] = []
        for y in range(GLOBE_HEIGHT):
            line_parts: list[str] = []
            for x in range(GLOBE_WIDTH):
                # Normalize to -1..1
                nx = (x - cx) / rx
                ny = (y - cy) / ry
                r2 = nx * nx + ny * ny
                if r2 > 1.0:
                    line_parts.append(" ")
                    continue
                # Spherical projection: map (nx, ny) -> (lat, lon)
                nz = math.sqrt(1.0 - r2)
                lat = math.degrees(math.asin(ny))
                lon = math.degrees(math.atan2(nx, nz)) + lon_offset
                # Normalize longitude to -180..180
                lon = ((lon + 180) % 360) - 180

                if _is_ice(lat):
                    line_parts.append(f"[{_ICE_STYLE}]{_ICE_CHAR}[/]")
                elif _is_land(lat, lon):
                    idx = int((nz * 4) % len(_LAND_CHARS))
                    ch = _LAND_CHARS[idx]
                    style = _LAND_STYLES[idx]
                    line_parts.append(f"[{style}]{ch}[/]")
                else:
                    # Use a pseudo-random ocean pattern based on position
                    idx = (x * 7 + y * 3 + f) % len(_OCEAN_CHARS)
                    ch = _OCEAN_CHARS[idx]
                    style = _OCEAN_STYLES[idx % len(_OCEAN_STYLES)]
                    line_parts.append(f"[{style}]{ch}[/]")
            rows.append("".join(line_parts))
        frames.append(rows)
    return frames


class Globe(Widget):
    """A rotating ASCII globe widget."""

    DEFAULT_CSS = """
    Globe {
        width: 26;
        height: 13;
    }
    """

    frame_index: reactive[int] = reactive(0)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._frames = _generate_frames()
        self._timer = None

    def on_mount(self) -> None:
        self._timer = self.set_interval(0.15, self._advance_frame)

    def _advance_frame(self) -> None:
        self.frame_index = (self.frame_index + 1) % NUM_FRAMES

    def watch_frame_index(self) -> None:
        self.refresh()

    def render(self) -> Text:
        frame = self._frames[self.frame_index]
        return Text.from_markup("\n".join(frame))

    def pause(self) -> None:
        if self._timer is not None:
            self._timer.stop()

    def resume(self) -> None:
        if self._timer is not None:
            self._timer.resume()
