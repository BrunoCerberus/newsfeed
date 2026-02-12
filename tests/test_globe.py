"""Tests for newsfeed.globe — rotating ASCII globe widget."""

from unittest.mock import MagicMock

import pytest
from rich.text import Text

from newsfeed.globe import Globe, NUM_FRAMES


class TestGlobeUnit:
    def test_init_generates_frames(self):
        globe = Globe()
        assert len(globe._frames) == NUM_FRAMES

    def test_advance_frame_increments(self):
        globe = Globe()
        assert globe.frame_index == 0
        globe._advance_frame()
        assert globe.frame_index == 1

    def test_advance_frame_wraps(self):
        globe = Globe()
        globe.frame_index = NUM_FRAMES - 1
        globe._advance_frame()
        assert globe.frame_index == 0

    def test_render_returns_text(self):
        globe = Globe()
        result = globe.render()
        assert isinstance(result, Text)
        assert len(result.plain) > 0

    def test_render_different_frames(self):
        globe = Globe()
        text0 = globe.render()
        globe.frame_index = 30
        text30 = globe.render()
        # Rotation changes colors/styles even though the sphere shape is the same
        assert text0._spans != text30._spans


class TestGlobePauseResume:
    def test_pause_stops_timer(self):
        globe = Globe()
        mock_timer = MagicMock()
        globe._timer = mock_timer
        globe.pause()
        mock_timer.stop.assert_called_once()

    def test_resume_resumes_timer(self):
        globe = Globe()
        mock_timer = MagicMock()
        globe._timer = mock_timer
        globe.resume()
        mock_timer.resume.assert_called_once()

    def test_pause_noop_when_no_timer(self):
        globe = Globe()
        globe._timer = None
        globe.pause()  # should not raise

    def test_resume_noop_when_no_timer(self):
        globe = Globe()
        globe._timer = None
        globe.resume()  # should not raise


@pytest.mark.asyncio
class TestGlobeAsync:
    async def test_on_mount_sets_timer(self):
        from textual.app import App, ComposeResult

        class GlobeApp(App):
            def compose(self) -> ComposeResult:
                yield Globe(id="globe")

        app = GlobeApp()
        async with app.run_test(size=(30, 15)) as pilot:
            globe = app.query_one("#globe", Globe)
            assert globe._timer is not None

    async def test_frame_advances_after_mount(self):
        from textual.app import App, ComposeResult

        class GlobeApp(App):
            def compose(self) -> ComposeResult:
                yield Globe(id="globe")

        app = GlobeApp()
        async with app.run_test(size=(30, 15)) as pilot:
            globe = app.query_one("#globe", Globe)
            # Wait for some animation frames
            await pilot.pause(0.5)
            assert globe.frame_index > 0
