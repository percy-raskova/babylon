"""M5 Task 40 smoke (contract §5): fixture-fed tri-county choropleth,
end-to-end through the REAL seam.

One test drives the whole lane the unit tiers pin piecewise: a real
``GameSession`` over the WAYNE scenario with three stamped Detroit-area
counties (values landing in three different bands) and a synthetic WKT
provider → the real ``RustClientHost.choropleth_json`` passthrough → the
Rust client's serde parse → the scanline fill → a headless transcript
frame. Colors cannot cross the text transcript (the Rust frame-content
tests pin those); what this smoke certifies is the SEAM — graph stamps
in, filled labeled polygons out, never a blank interior (the
certified-blank-golden class).
"""

from __future__ import annotations

import json

import pytest

from babylon.engine.scenarios import WayneCountyScenario
from babylon.game.session import create_new_campaign
from babylon.models.enums import NodeType
from babylon.tui.campaign_menu import InMemoryCampaignCatalog
from babylon.tui.host import RustClientHost
from tests.unit.game.test_session import _FakeStore
from tests.unit.tui.test_rust_client_ffi import _FakeHost, babylon_tui

pytestmark = pytest.mark.unit

#: The three Detroit-area counties (the detroit_tri_county reading the
#: contract §5 ruled), stamped so each lands in a DIFFERENT value band:
#: 0.5 → dim, 1.5 → gold, 2.5 → crimson.
_STAMPS = (
    ("T_WAYNE_CO", "Wayne", "26163", 2.5, 500.0),
    ("T_OAKLAND_CO", "Oakland", "26125", 1.5, 300.0),
    ("T_MACOMB_CO", "Macomb", "26099", 0.5, 100.0),
)

_WKT = {
    "26163": "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))",
    "26125": "POLYGON((12 0, 22 0, 22 10, 12 10, 12 0))",
    "26099": "POLYGON((24 0, 34 0, 34 10, 24 10, 24 0))",
}


def _tri_county_session():
    session = create_new_campaign(
        _FakeStore(),
        scenario=WayneCountyScenario(),
        county_wkt=lambda geoids: {g: _WKT[g] for g in geoids if g in _WKT},
    )
    for node_id, name, fips, e, s in _STAMPS:
        session.graph.add_node(
            node_id,
            NodeType.TERRITORY,
            name=name,
            county_fips=fips,
            tick_exploitation_rate=e,
            tick_total_surplus=s,
        )
    return session


class _TriCountyHost(_FakeHost):
    """The FFI fake for everything EXCEPT the maps surface, which threads
    the REAL ``RustClientHost.choropleth_json`` over a real session."""

    def __init__(self) -> None:
        self._host = RustClientHost(
            InMemoryCampaignCatalog(), defines_hash="dh1", engine_version="ev1"
        )
        self._host.session = _tri_county_session()

    def choropleth_json(self, args_json: str) -> str:
        return self._host.choropleth_json(args_json)


def test_tri_county_fixture_renders_filled_labeled_polygons() -> None:
    config = json.dumps(
        {
            "campaign_id": "c1",
            "campaign_name": "Wayne County",
            "render_tier": "glyph",
            "tutorial_enabled": False,
            "narrator_enabled": False,
            "headless": True,
            "script": [{"key": "enter"}, {"key": "2"}, {"key": "q"}, {"key": "q"}],
        }
    )

    transcript = json.loads(babylon_tui.run(_TriCountyHost(), config))

    assert "choropleth_json" in transcript["host_calls"], (
        "entering the map pane must fetch the envelope through the seam"
    )
    map_frame = transcript["frames"][2]
    assert "map — county/value" in map_frame, f"map pane title missing:\n{map_frame}"
    assert any(block in map_frame for block in "▀▄█"), (
        "no HalfBlock fill cells — the tri-county polygons did not render "
        "(solid interiors blit as '█', edges as '▀'/'▄'):\n" + map_frame
    )
    for fips in ("26163", "26125", "26099"):
        assert fips in map_frame, f"county label {fips} missing:\n{map_frame}"
    assert "no county map" not in map_frame, (
        "the honest-absence line rendered over a county-bearing graph"
    )
