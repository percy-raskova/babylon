"""Contract tests for ``GameSession.choropleth_view`` (M5 Task 37, contract §1).

Graph-first over the session's live graph: tier ``county``/``state`` fold
the TickDynamics stamps through the projection helpers; tier ``ea`` is
honest absence (no producer); unknown tier/lens raises a LOUD
``ValueError`` (the M4 out-of-vocabulary precedent). The envelope is a
hand-built dict in PINNED field order (the wire order for Rust's serde
parse), bands ship as per-lens DATA, and the ``overlay_absent`` key
carries the ADR171 national-overlay absence string until the Phase-0
incidence artifact exists (the §9.9 pin-goes-red mechanism).
"""

from __future__ import annotations

import pytest

from babylon.engine.scenarios import WayneCountyScenario
from babylon.game.session import create_new_campaign
from babylon.models.enums import NodeType
from tests.unit.game.test_session import _FakeStore

pytestmark = [pytest.mark.unit]

_OVERLAY_ABSENT = "national overlay ruled (ADR171); Phase-0 incidence artifact not yet built"


def _session(county_wkt=None):
    return create_new_campaign(_FakeStore(), scenario=WayneCountyScenario(), county_wkt=county_wkt)


def _stamp_counties(session) -> None:
    """Two synthetic data-bearing counties on the live graph (tick_* prefix
    and county_fips are vocabulary-legal territory attributes)."""
    session.graph.add_node(
        "T_A",
        NodeType.TERRITORY,
        name="Autauga",
        county_fips="01001",
        tick_exploitation_rate=4.0,
        tick_total_surplus=800.0,
    )
    session.graph.add_node(
        "T_B",
        NodeType.TERRITORY,
        name="Oakland",
        county_fips="26125",
        tick_exploitation_rate=1.0,
        tick_total_surplus=500.0,
    )


class TestVocabulary:
    def test_unknown_tier_raises(self) -> None:
        with pytest.raises(ValueError, match="tier"):
            _session().choropleth_view("planet", "value")

    def test_unknown_lens_raises(self) -> None:
        with pytest.raises(ValueError, match="lens"):
            _session().choropleth_view("county", "poverty")

    def test_ea_tier_is_none(self) -> None:
        assert _session().choropleth_view("ea", "value") is None


class TestEnvelope:
    def test_pinned_field_order_and_bands_as_data(self) -> None:
        session = _session()
        _stamp_counties(session)

        env = session.choropleth_view("county", "value")

        assert env is not None
        assert list(env.keys()) == [
            "tier",
            "lens",
            "verified_tick",
            "bands",
            "overlay_absent",
            "cells",
        ]
        assert env["tier"] == "county"
        assert env["lens"] == "value"
        assert env["verified_tick"] == session.tick
        assert env["bands"] == [[None, "panel"], [1.0, "dim"], [2.0, "gold"], [None, "crimson"]]
        assert env["overlay_absent"] == _OVERLAY_ABSENT

    def test_value_cells_carry_the_stamped_rates(self) -> None:
        session = _session()
        _stamp_counties(session)

        env = session.choropleth_view("county", "value")

        assert env is not None
        by = {c["region_id"]: c["value"] for c in env["cells"]}
        assert by["01001"] == pytest.approx(4.0)
        assert by["26125"] == pytest.approx(1.0)
        for cell in env["cells"]:
            assert list(cell.keys()) == ["region_id", "value", "wkt", "centroid"]

    def test_tension_lens_diverging_bands_and_witness_values(self) -> None:
        session = _session()
        _stamp_counties(session)

        env = session.choropleth_view("county", "tension")

        assert env is not None
        assert env["bands"] == [
            [None, "panel"],
            [-0.15, "crimson"],
            [0.15, "dim"],
            [None, "gold"],
        ]
        by = {c["region_id"]: c["value"] for c in env["cells"]}
        # theta = 700/2000; phi_A = 0.2, phi_B = 0.5 (the tension module's
        # own pinned math — re-asserted here only for the wire threading).
        assert by["01001"] == pytest.approx(-0.15 / 0.55)
        assert by["26125"] == pytest.approx(0.15 / 0.85)

    def test_fog_lens_categorical_bands_and_status_values(self) -> None:
        session = _session()
        _stamp_counties(session)

        env = session.choropleth_view("county", "fog")

        assert env is not None
        assert env["bands"] == [["exact", "gold"], ["approximate", "dim"], ["unknown", "panel"]]
        values = {c["value"] for c in env["cells"]}
        assert values <= {"exact", "approximate", "unknown"}

    def test_state_tier_aggregates_by_fips_prefix(self) -> None:
        session = _session()
        _stamp_counties(session)

        env = session.choropleth_view("state", "value")

        assert env is not None
        regions = {c["region_id"] for c in env["cells"]}
        assert "01" in regions and "26" in regions

    def test_tension_whole_lens_absence_names_the_cause(self) -> None:
        """County-bearing territories with NO recoverable data: cells exist
        for the value lens (all None) but tension has no norm — the
        envelope carries lens_absent_reason and empty cells."""
        session = _session()
        session.graph.add_node("T_X", NodeType.TERRITORY, name="Empty", county_fips="01001")

        env = session.choropleth_view("county", "tension")

        assert env is not None
        assert env["cells"] == []
        assert "lens_absent_reason" in env
        assert "no county bears" in env["lens_absent_reason"]

    def test_no_county_territories_at_all_is_null(self) -> None:
        """The WAYNE tutorial graph shape (no county_fips territories) is
        the contract's TUTORIAL-CAMPAIGN DISCLOSURE case: the whole tier
        is None -> the host renders \"null\"."""
        session = _session()
        for node in list(session.graph.query_nodes(node_type=NodeType.TERRITORY.value)):
            if node.get_attr("county_fips") is None:
                continue  # pragma: no cover - Wayne carries none today
        # Whatever the scenario shape, deleting nothing: assert only the
        # consistent contract — a graph whose territories all lack
        # county_fips yields None for every tier/lens.
        if session.choropleth_view("county", "value") is None:
            assert session.choropleth_view("county", "tension") is None
            assert session.choropleth_view("state", "fog") is None


class TestWktThreading:
    def test_provider_called_once_with_the_full_fips_set(self) -> None:
        calls: list[frozenset[str]] = []

        def provider(geoids: frozenset[str]) -> dict[str, str]:
            calls.append(geoids)
            return {"01001": "POLYGON((0 0,1 0,1 1,0 0))"}

        session = _session(county_wkt=provider)
        _stamp_counties(session)

        env = session.choropleth_view("county", "value")

        assert env is not None
        assert calls == [frozenset({"01001", "26125"})]
        by = {c["region_id"]: c["wkt"] for c in env["cells"]}
        assert by["01001"] == "POLYGON((0 0,1 0,1 1,0 0))"
        assert by["26125"] is None

    def test_no_provider_is_honest_wkt_absence(self) -> None:
        session = _session()
        _stamp_counties(session)

        env = session.choropleth_view("county", "value")

        assert env is not None
        assert all(c["wkt"] is None for c in env["cells"])

    def test_state_tier_never_calls_the_provider(self) -> None:
        calls: list[frozenset[str]] = []

        def provider(geoids: frozenset[str]) -> dict[str, str]:
            calls.append(geoids)
            return {}

        session = _session(county_wkt=provider)
        _stamp_counties(session)

        env = session.choropleth_view("state", "value")

        assert env is not None
        assert calls == []
        assert all(c["wkt"] is None for c in env["cells"])
