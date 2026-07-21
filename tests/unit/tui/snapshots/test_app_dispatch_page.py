"""WO-45 full-app golden: ten kinds' statblocks live on one page.

Every fence defers to the app's default kind-dispatch provider (no baked
bodies), so this golden certifies the whole composition — plus the
unknown-kind absence refusal — in a single render.
"""

from __future__ import annotations

from pathlib import Path


def test_all_kinds_page_renders_through_the_dispatch(snap_compare) -> None:  # type: ignore[no-untyped-def]
    assert snap_compare(Path(__file__).parent / "app_dispatch_app.py", terminal_size=(132, 130))
