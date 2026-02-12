"""Rotating globe widget — half-block 3D-lit spherical Earth projection."""

from __future__ import annotations

import math

from rich.style import Style
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

# Continent bounding boxes as (min_lat, max_lat, min_lon, max_lon)
_CONTINENTS: list[tuple[float, float, float, float]] = [
    # North America
    (30, 50, -128, -60),
    (50, 70, -140, -55),
    (60, 72, -168, -140),
    # Central America
    (10, 30, -115, -80),
    # South America
    (-55, -10, -75, -40),
    (-10, 10, -80, -45),
    # Europe
    (36, 60, -10, 30),
    (55, 71, 5, 40),
    (50, 59, -11, 2),
    # Africa
    (-35, 0, 10, 42),
    (0, 37, -17, 40),
    (0, 12, 25, 51),
    # Middle East
    (15, 40, 35, 60),
    # Russia / Northern Asia
    (50, 72, 30, 180),
    # Central / South Asia
    (25, 50, 60, 100),
    # India
    (8, 30, 68, 88),
    # Southeast Asia
    (10, 25, 95, 110),
    (0, 8, 100, 120),
    # China / Mongolia
    (20, 50, 100, 135),
    # Japan
    (31, 45, 129, 146),
    # Korea
    (34, 43, 125, 130),
    # Australia
    (-38, -12, 113, 153),
    # New Zealand
    (-47, -34, 166, 178),
    # Indonesia
    (-8, 0, 105, 140),
    # Greenland
    (60, 83, -55, -15),
    # Iceland
    (63, 66, -24, -13),
    # Madagascar
    (-25, -12, 43, 50),
    # Philippines
    (5, 19, 117, 127),
]

NUM_FRAMES = 60
GLOBE_WIDTH = 24
GLOBE_HEIGHT = 13
_PIXEL_H = GLOBE_HEIGHT * 2  # effective vertical pixels with half-blocks

# Light direction (normalized) — upper-right illumination
_LIGHT_RAW = (0.55, -0.45, 0.7)
_LIGHT_LEN = math.sqrt(sum(c * c for c in _LIGHT_RAW))
_LIGHT_DIR = tuple(c / _LIGHT_LEN for c in _LIGHT_RAW)

# Base colors (RGB 0–255)
_OCEAN_DEEP = (8, 25, 65)
_OCEAN_MID = (15, 50, 105)
_LAND_DARK = (22, 70, 18)
_LAND_BRIGHT = (50, 135, 42)
_DESERT_COLOR = (135, 125, 70)
_ICE_COLOR = (185, 210, 235)
_ATMO_COLOR = (50, 100, 200)

_AMBIENT = 0.10
_DIFFUSE = 0.90


def _is_land(lat: float, lon: float) -> bool:
    """Check if a lat/lon coordinate is over land (using bounding boxes)."""
    for min_lat, max_lat, min_lon, max_lon in _CONTINENTS:
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return True
    return False


def _is_ice(lat: float) -> bool:
    """Check if latitude is in polar ice cap region."""
    return abs(lat) > 72


def _is_desert(lat: float, lon: float) -> bool:
    """Check if coordinates fall in a major desert belt."""
    alat = abs(lat)
    if not (15 < alat < 35):
        return False
    # Sahara / Arabia
    if lat > 0 and -17 < lon < 60:
        return True
    # Australian outback
    if lat < 0 and 120 < lon < 150:
        return True
    return False


def _clamp(v: float) -> int:
    return max(0, min(255, int(v)))


def _lerp_color(
    c1: tuple[int, ...], c2: tuple[int, ...], t: float
) -> tuple[int, ...]:
    return tuple(_clamp(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _generate_frames() -> list[list[list[tuple[int, ...] | None]]]:
    """Pre-compute frames as [frame][y][x] = (r,g,b) or None."""
    cx = GLOBE_WIDTH / 2
    cy = _PIXEL_H / 2
    rx = cx - 1.5
    ry = cy - 1.0

    frames: list[list[list[tuple[int, ...] | None]]] = []
    for f in range(NUM_FRAMES):
        lon_offset = (f / NUM_FRAMES) * 360.0
        grid: list[list[tuple[int, ...] | None]] = []
        for y in range(_PIXEL_H):
            row: list[tuple[int, ...] | None] = []
            for x in range(GLOBE_WIDTH):
                nx = (x - cx) / rx
                ny = (y - cy) / ry
                r2 = nx * nx + ny * ny

                if r2 > 1.0:
                    # Atmosphere glow just outside the sphere
                    if r2 < 1.25:
                        t = 1.0 - (r2 - 1.0) / 0.25
                        a = t * t * 0.12
                        row.append(tuple(_clamp(c * a) for c in _ATMO_COLOR))
                    else:
                        row.append(None)
                    continue

                nz = math.sqrt(1.0 - r2)

                # Fix orientation: negate ny so north is up
                lat = math.degrees(math.asin(-ny))
                lon = math.degrees(math.atan2(nx, nz)) + lon_offset
                lon = ((lon + 180) % 360) - 180

                # Diffuse lighting
                normal = (nx, -ny, nz)
                dot = sum(normal[i] * _LIGHT_DIR[i] for i in range(3))
                brightness = _AMBIENT + _DIFFUSE * max(0.0, dot)

                # Fresnel atmosphere rim
                fresnel = (1.0 - nz) ** 3

                # Base color
                if _is_ice(lat):
                    base = _ICE_COLOR
                elif _is_land(lat, lon):
                    if _is_desert(lat, lon):
                        base = _lerp_color(_LAND_DARK, _DESERT_COLOR, 0.6)
                    else:
                        alt = nz * 0.5 + 0.5
                        base = _lerp_color(_LAND_DARK, _LAND_BRIGHT, alt * 0.7)
                else:
                    depth = nz * 0.3 + 0.2
                    base = _lerp_color(_OCEAN_DEEP, _OCEAN_MID, depth)

                # Apply brightness
                lit = tuple(_clamp(c * brightness) for c in base)
                # Apply atmosphere rim
                final = _lerp_color(lit, _ATMO_COLOR, fresnel * 0.3)

                row.append(final)
            grid.append(row)
        frames.append(grid)
    return frames


# Style cache to avoid creating duplicate Style objects
_style_cache: dict[tuple[tuple[int, ...] | None, tuple[int, ...] | None], Style] = {}


def _get_style(
    fg: tuple[int, ...] | None, bg: tuple[int, ...] | None
) -> Style:
    key = (fg, bg)
    cached = _style_cache.get(key)
    if cached is not None:
        return cached
    fg_s = f"rgb({fg[0]},{fg[1]},{fg[2]})" if fg else None
    bg_s = f"rgb({bg[0]},{bg[1]},{bg[2]})" if bg else None
    style = Style(color=fg_s, bgcolor=bg_s)
    _style_cache[key] = style
    return style


def _frame_to_text(grid: list[list[tuple[int, ...] | None]]) -> Text:
    """Convert a pixel grid to Rich Text using half-block characters."""
    text = Text()
    for cy in range(GLOBE_HEIGHT):
        if cy > 0:
            text.append("\n")
        top_row = grid[cy * 2]
        bot_row = grid[cy * 2 + 1]
        for x in range(GLOBE_WIDTH):
            top = top_row[x]
            bot = bot_row[x]
            if top is None and bot is None:
                text.append(" ")
            elif top is not None and bot is not None:
                text.append("▀", _get_style(fg=top, bg=bot))
            elif top is not None:
                text.append("▀", _get_style(fg=top, bg=None))
            else:
                text.append("▄", _get_style(fg=bot, bg=None))
    return text


class Globe(Widget):
    """A rotating 3D-lit globe widget with half-block rendering."""

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
        self._rendered = [_frame_to_text(g) for g in self._frames]
        self._timer = None

    def on_mount(self) -> None:
        self._timer = self.set_interval(0.15, self._advance_frame)

    def _advance_frame(self) -> None:
        self.frame_index = (self.frame_index + 1) % NUM_FRAMES

    def watch_frame_index(self) -> None:
        self.refresh()

    def render(self) -> Text:
        return self._rendered[self.frame_index]

    def pause(self) -> None:
        if self._timer is not None:
            self._timer.stop()

    def resume(self) -> None:
        if self._timer is not None:
            self._timer.resume()
