"""Contract tests for the county tension lens producer (ADR170).

The Director-ruled ``county_extraction`` opposition, computed at PROJECTION
time from the graph's own TickDynamics stamps: per data-bearing county the
wage share ``phi = 1/(1+e)`` (``e`` = ``tick_exploitation_rate``), the
national norm ``theta = sum(v)/sum(v+s)`` (a RATIO OF SUMS, never a mean of
shares), and the witness ``w = (phi - theta)/(phi + theta)`` — algebraically
identical to the proposal's ``(b-a)/(a+b)`` with ``a = theta*(v+s)``,
``b = v``. The extensive ``v`` is recovered as ``s/e`` from the co-present
``tick_total_surplus`` stamp; a county missing either stamp — or carrying the
stamp block's own ``0.0`` no-hydration fallback — is HONESTLY ABSENT
(``w=None``), never a fabricated zero (Constitution III.11).
"""

from __future__ import annotations

import math

import pytest

from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


def _graph_with(counties: list[dict[str, object]]) -> BabylonGraph:
    """A graph of territory nodes, one per entry; ``fips=None`` omits the
    attribute entirely (an abstract territory with no county identity)."""
    g = BabylonGraph()
    for i, spec in enumerate(counties):
        attrs: dict[str, object] = {"name": f"County {i}"}
        if spec.get("fips") is not None:
            attrs["county_fips"] = spec["fips"]
        for key in ("tick_exploitation_rate", "tick_total_surplus"):
            if key in spec:
                attrs[key] = spec[key]
        g.add_node(f"T{i}", NodeType.TERRITORY, **attrs)
    return g


class TestCountyTensionCells:
    """Contract of ``county_tension_cells(graph)``."""

    def test_two_county_pinned_math(self) -> None:
        """e=4 -> phi=0.2, s=800 -> v=200; e=1 -> phi=0.5, s=500 -> v=500.
        theta = (200+500)/(1000+1000) = 0.35;
        w_A = (0.2-0.35)/(0.2+0.35), w_B = (0.5-0.35)/(0.5+0.35)."""
        from babylon.projection.topology.tension import county_tension_cells

        cells = county_tension_cells(
            _graph_with(
                [
                    {"fips": "01001", "tick_exploitation_rate": 4.0, "tick_total_surplus": 800.0},
                    {"fips": "02002", "tick_exploitation_rate": 1.0, "tick_total_surplus": 500.0},
                ]
            )
        )

        assert cells is not None
        by_fips = {c.region_id: c.w for c in cells}
        assert by_fips["01001"] == pytest.approx(-0.15 / 0.55)
        assert by_fips["02002"] == pytest.approx(0.15 / 0.85)

    def test_signs_source_negative_recipient_positive(self) -> None:
        """The witness sign is the political content: the higher-exploitation
        county (thin wage share) reads NEGATIVE (Phi-source, crimson); the
        wage-heavy county reads POSITIVE (Phi-recipient, gold)."""
        from babylon.projection.topology.tension import county_tension_cells

        cells = county_tension_cells(
            _graph_with(
                [
                    {"fips": "01001", "tick_exploitation_rate": 4.0, "tick_total_surplus": 800.0},
                    {"fips": "02002", "tick_exploitation_rate": 1.0, "tick_total_surplus": 500.0},
                ]
            )
        )

        assert cells is not None
        by_fips = {c.region_id: c.w for c in cells}
        assert by_fips["01001"] is not None and by_fips["01001"] < 0
        assert by_fips["02002"] is not None and by_fips["02002"] > 0

    def test_single_data_bearing_county_is_the_norm_itself(self) -> None:
        """With one county, theta == phi, so w == 0 exactly — the map of
        deviation renders equilibrium as zero (Mao: unevenness is the
        figure, not the ground)."""
        from babylon.projection.topology.tension import county_tension_cells

        cells = county_tension_cells(
            _graph_with(
                [{"fips": "01001", "tick_exploitation_rate": 2.0, "tick_total_surplus": 100.0}]
            )
        )

        assert cells is not None
        assert cells[0].w == pytest.approx(0.0)

    def test_zero_fallback_stamps_are_absence_not_zero_tension(self) -> None:
        """The stamp block writes ``0.0`` for both attrs when the county's
        TensorRegistry was never hydrated — that poisoned fallback must
        surface as w=None, never as a computed cell."""
        from babylon.projection.topology.tension import county_tension_cells

        cells = county_tension_cells(
            _graph_with(
                [
                    {"fips": "01001", "tick_exploitation_rate": 0.0, "tick_total_surplus": 0.0},
                    {"fips": "02002", "tick_exploitation_rate": 1.0, "tick_total_surplus": 500.0},
                ]
            )
        )

        assert cells is not None
        by_fips = {c.region_id: c.w for c in cells}
        assert by_fips["01001"] is None

    def test_missing_either_stamp_is_absence(self) -> None:
        from babylon.projection.topology.tension import county_tension_cells

        cells = county_tension_cells(
            _graph_with(
                [
                    {"fips": "01001", "tick_exploitation_rate": 2.0},
                    {"fips": "02002", "tick_total_surplus": 500.0},
                    {"fips": "03003", "tick_exploitation_rate": 1.0, "tick_total_surplus": 400.0},
                ]
            )
        )

        assert cells is not None
        by_fips = {c.region_id: c.w for c in cells}
        assert by_fips["01001"] is None
        assert by_fips["02002"] is None
        assert by_fips["03003"] is not None

    def test_no_data_bearing_county_returns_none(self) -> None:
        """Zero data-bearing counties -> no theta exists -> the WHOLE lens is
        honestly absent (None), the envelope's lens_absent_reason case."""
        from babylon.projection.topology.tension import county_tension_cells

        cells = county_tension_cells(
            _graph_with(
                [
                    {"fips": "01001"},
                    {"fips": "02002", "tick_exploitation_rate": 0.0, "tick_total_surplus": 0.0},
                ]
            )
        )

        assert cells is None

    def test_graph_without_county_territories_returns_none(self) -> None:
        from babylon.projection.topology.tension import county_tension_cells

        assert county_tension_cells(_graph_with([{"fips": None}])) is None
        assert county_tension_cells(BabylonGraph()) is None

    def test_infinite_exploitation_rate_is_the_bled_dry_limit(self) -> None:
        """e=inf means v=0 (all new value is surplus): phi=0, w=-1 exactly —
        a PRESENT value (the value lens's own inf-is-present convention),
        never absence."""
        from babylon.projection.topology.tension import county_tension_cells

        cells = county_tension_cells(
            _graph_with(
                [
                    {
                        "fips": "01001",
                        "tick_exploitation_rate": float("inf"),
                        "tick_total_surplus": 800.0,
                    },
                    {"fips": "02002", "tick_exploitation_rate": 1.0, "tick_total_surplus": 500.0},
                ]
            )
        )

        assert cells is not None
        by_fips = {c.region_id: c.w for c in cells}
        assert by_fips["01001"] == pytest.approx(-1.0)

    def test_multi_territory_county_sums_extensives_before_the_share(self) -> None:
        """Two territories in one county: v and s SUM (extensive) before phi
        is taken — never a mean of the two territories' shares (the
        intensive-aggregation law)."""
        from babylon.projection.topology.tension import county_tension_cells

        # Split county 01001: (e=4, s=400) + (e=4, s=400) == one (e=4, s=800).
        split = county_tension_cells(
            _graph_with(
                [
                    {"fips": "01001", "tick_exploitation_rate": 4.0, "tick_total_surplus": 400.0},
                    {"fips": "01001", "tick_exploitation_rate": 4.0, "tick_total_surplus": 400.0},
                    {"fips": "02002", "tick_exploitation_rate": 1.0, "tick_total_surplus": 500.0},
                ]
            )
        )
        merged = county_tension_cells(
            _graph_with(
                [
                    {"fips": "01001", "tick_exploitation_rate": 4.0, "tick_total_surplus": 800.0},
                    {"fips": "02002", "tick_exploitation_rate": 1.0, "tick_total_surplus": 500.0},
                ]
            )
        )

        assert split is not None and merged is not None
        assert split == merged

    def test_cells_sorted_by_fips_and_bounded(self) -> None:
        from babylon.projection.topology.tension import county_tension_cells

        cells = county_tension_cells(
            _graph_with(
                [
                    {"fips": "55555", "tick_exploitation_rate": 9.0, "tick_total_surplus": 900.0},
                    {"fips": "01001", "tick_exploitation_rate": 0.5, "tick_total_surplus": 100.0},
                    {"fips": "26163", "tick_exploitation_rate": 2.0, "tick_total_surplus": 600.0},
                ]
            )
        )

        assert cells is not None
        assert [c.region_id for c in cells] == ["01001", "26163", "55555"]
        for cell in cells:
            if cell.w is not None:
                assert -1.0 <= cell.w <= 1.0
                assert math.isfinite(cell.w)

    def test_deterministic_across_repeated_calls(self) -> None:
        from babylon.projection.topology.tension import county_tension_cells

        g = _graph_with(
            [
                {"fips": "01001", "tick_exploitation_rate": 4.0, "tick_total_surplus": 800.0},
                {"fips": "02002", "tick_exploitation_rate": 1.0, "tick_total_surplus": 500.0},
            ]
        )

        assert county_tension_cells(g) == county_tension_cells(g)
