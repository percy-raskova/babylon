"""Behavioral contract for the MapView lens selector (Task 4)."""

import pytest

from babylon.tui.shell.views.map_view import MapView


@pytest.mark.asyncio
async def test_lens_toggle_updates_selected_field(make_shell_harness):
    view = MapView(id="map")
    async with make_shell_harness(view):
        assert view.lens == "value"
        view.set_lens("tension")
        assert view.lens == "tension"


def test_lens_is_restricted_to_known_values():
    view = MapView(id="map")
    with pytest.raises(ValueError):
        view.set_lens("bogus")  # type: ignore[arg-type]
