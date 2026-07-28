"""Contract tests for the M5 tier/lens helpers (contract §1, graph-first).

The value lens and the state-tier variants share the tension module's
extensive-recovery fold (``v = s/e`` from the co-present TickDynamics
stamps): the value lens emits the exploitation rate ``e`` (inf-is-present
at ``v == 0``, the ledger lens's own convention), the state tier groups
counties by ``county_fips[:2]`` and aggregates RATIO-OF-SUMS — never a
mean of county rates (the intensive-aggregation law).
"""

from __future__ import annotations

import pytest

from babylon.models.enums import NodeType
from babylon.projection.fog.ledger import IntelLedger
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


def _graph(counties: list[dict[str, object]]) -> BabylonGraph:
    g = BabylonGraph()
    for i, spec in enumerate(counties):
        attrs: dict[str, object] = {"name": f"T{i}"}
        if spec.get("fips") is not None:
            attrs["county_fips"] = spec["fips"]
        for key in ("tick_exploitation_rate", "tick_total_surplus"):
            if key in spec:
                attrs[key] = spec[key]
        g.add_node(f"T{i}", NodeType.TERRITORY, **attrs)
    return g


class TestCountyValueCells:
    def test_single_territory_county_emits_its_rate_directly(self) -> None:
        """A lone territory's ``e`` is honest even when ``s`` is absent
        (no recovery needed for a group of one)."""
        from babylon.projection.topology.map_lenses import county_value_cells

        cells = county_value_cells(_graph([{"fips": "01001", "tick_exploitation_rate": 2.5}]))

        assert cells is not None
        assert cells[0].region_id == "01001"
        assert cells[0].value == pytest.approx(2.5)

    def test_infinity_is_present_not_absent(self) -> None:
        from babylon.projection.topology.map_lenses import county_value_cells

        cells = county_value_cells(
            _graph([{"fips": "01001", "tick_exploitation_rate": float("inf")}])
        )

        assert cells is not None
        assert cells[0].value == float("inf")

    def test_missing_rate_is_none_cell(self) -> None:
        from babylon.projection.topology.map_lenses import county_value_cells

        cells = county_value_cells(
            _graph(
                [
                    {"fips": "01001"},
                    {"fips": "02002", "tick_exploitation_rate": 1.0},
                ]
            )
        )

        assert cells is not None
        by = {c.region_id: c.value for c in cells}
        assert by["01001"] is None
        assert by["02002"] == pytest.approx(1.0)

    def test_multi_territory_county_is_ratio_of_sums_never_mean_of_rates(self) -> None:
        """(e=4, s=800 -> v=200) + (e=1, s=500 -> v=500): e = 1300/700,
        NOT mean(4, 1) = 2.5."""
        from babylon.projection.topology.map_lenses import county_value_cells

        cells = county_value_cells(
            _graph(
                [
                    {"fips": "01001", "tick_exploitation_rate": 4.0, "tick_total_surplus": 800.0},
                    {"fips": "01001", "tick_exploitation_rate": 1.0, "tick_total_surplus": 500.0},
                ]
            )
        )

        assert cells is not None
        assert cells[0].value == pytest.approx(1300.0 / 700.0)

    def test_no_county_territories_is_none(self) -> None:
        from babylon.projection.topology.map_lenses import county_value_cells

        assert county_value_cells(BabylonGraph()) is None


class TestStateTierCells:
    def _two_state_graph(self) -> BabylonGraph:
        # Michigan: two counties; Alabama: one.
        return _graph(
            [
                {"fips": "26163", "tick_exploitation_rate": 4.0, "tick_total_surplus": 800.0},
                {"fips": "26125", "tick_exploitation_rate": 1.0, "tick_total_surplus": 500.0},
                {"fips": "01001", "tick_exploitation_rate": 2.0, "tick_total_surplus": 600.0},
            ]
        )

    def test_state_value_is_ratio_of_sums_over_the_state(self) -> None:
        """MI: v=200+500, s=800+500 -> e=1300/700; AL: e=2."""
        from babylon.projection.topology.map_lenses import state_value_cells

        cells = state_value_cells(self._two_state_graph())

        assert cells is not None
        by = {c.region_id: c.value for c in cells}
        assert by["26"] == pytest.approx(1300.0 / 700.0)
        assert by["01"] == pytest.approx(2.0)

    def test_state_tension_uses_the_national_theta(self) -> None:
        """theta = (200+500+300)/(1000+1000+900) = 1000/2900; MI phi =
        700/2000; w = (phi-theta)/(phi+theta)."""
        from babylon.projection.topology.map_lenses import state_tension_cells

        cells = state_tension_cells(self._two_state_graph())

        assert cells is not None
        theta = 1000.0 / 2900.0
        phi_mi = 700.0 / 2000.0
        by = {c.region_id: c.w for c in cells}
        assert by["26"] == pytest.approx((phi_mi - theta) / (phi_mi + theta))

    def test_state_fog_is_most_informed_wins(self) -> None:
        """One county in reach lights its whole state exact; a state with
        no reach and no intel is unknown."""
        from babylon.projection.topology.map_lenses import state_fog_status

        g = self._two_state_graph()
        g.add_node("ORG1", NodeType.ORGANIZATION, name="Org")
        g.add_edge("ORG1", "T0", "presence")  # T0 = 26163

        status = state_fog_status(
            g, "ORG1", IntelLedger(), 10, radius=1, staleness_ticks=5, unknown_ticks=20
        )

        assert status["26"] == "exact"
        assert status["01"] == "unknown"

    def test_state_tension_none_when_no_data(self) -> None:
        from babylon.projection.topology.map_lenses import state_tension_cells

        assert state_tension_cells(_graph([{"fips": "26163"}])) is None
