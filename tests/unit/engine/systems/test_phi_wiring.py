"""Tests for ImperialRentSystem.step() Φ-distribution wiring (Spec 063 T024-T026 / US2).

Exercises the sub-stage 5b wiring (T079 closure): the engine system reads
external_nodes_phi + county_exposure_by_external from context and emits
DRAIN_EDGE rows via the existing ``distribute_phi_week_to_counties`` helper.

No DB or graph needed — the tested code path is a pure context+register
interaction.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from babylon.economics.boundary_flow_register import (
    BoundaryEdgeKind,
    BoundaryFlowRegister,
    NodeKind,
)
from babylon.engine.context import TickContext
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.topology.graph import BabylonGraph

pytestmark = [pytest.mark.unit]


def _make_context(
    *,
    session_id,
    tick: int,
    register: BoundaryFlowRegister,
    external_nodes_phi: dict[str, float],
    county_exposure_by_external: dict[str, dict[str, float]],
) -> TickContext:
    """Build a TickContext with all spec-063 phi wiring keys."""
    ctx = TickContext(tick=tick)
    ctx.persistent_data["session_id"] = session_id
    ctx.persistent_data["boundary_flow_register"] = register
    ctx.persistent_data["external_nodes_phi"] = external_nodes_phi
    ctx.persistent_data["county_exposure_by_external"] = county_exposure_by_external
    return ctx


def _drain_rows(register: BoundaryFlowRegister) -> list:
    return [r for r in register._buffer if r.flow_type == BoundaryEdgeKind.DRAIN_EDGE]  # noqa: SLF001


def test_fr_017_phi_wiring_emits_drain_edge_rows_per_external_county_pair() -> None:
    """FR-017/018: each (external source, county dest) gets one DRAIN_EDGE row."""
    register = BoundaryFlowRegister()
    session_id = uuid4()
    # Canada phi: $52M/year → $1M/week. Wayne:0.5, Oakland:0.3, Macomb:0.2.
    ctx = _make_context(
        session_id=session_id,
        tick=1,
        register=register,
        external_nodes_phi={"canada": 52_000_000.0},
        county_exposure_by_external={
            "canada": {"26163": 0.5, "26125": 0.3, "26099": 0.2},
        },
    )
    sys = ImperialRentSystem()

    sys._invoke_phi_distribution_if_wired(ctx)  # noqa: SLF001 — testing internal seam

    rows = _drain_rows(register)
    assert len(rows) == 3
    # All rows have correct kind discriminators
    for r in rows:
        assert r.source_kind == NodeKind.EXTERNAL
        assert r.source_node_id == "canada"
        assert r.dest_kind == NodeKind.COUNTY
        assert r.dest_node_id in {"26163", "26125", "26099"}
    # Weekly Φ totals to phi_year / 52
    weekly_total = sum(r.magnitude for r in rows)
    assert weekly_total == pytest.approx(52_000_000.0 / 52, rel=1e-9)


def test_fr_019_no_drain_edges_target_rest_of_usa() -> None:
    """FR-019: Φ MUST land at dest_kind=county, never at dest_node_id='rest_of_usa'."""
    register = BoundaryFlowRegister()
    ctx = _make_context(
        session_id=uuid4(),
        tick=0,
        register=register,
        external_nodes_phi={"china": 1_000_000.0},
        county_exposure_by_external={
            "china": {"26163": 1.0},
        },
    )
    ImperialRentSystem()._invoke_phi_distribution_if_wired(ctx)  # noqa: SLF001

    rows = _drain_rows(register)
    assert rows
    for r in rows:
        assert r.dest_node_id != "rest_of_usa"
        assert r.dest_kind == NodeKind.COUNTY


def test_fr_020_zero_phi_inflow_emits_no_drain_rows() -> None:
    """FR-020: external nodes with phi_year_inflow == 0 contribute zero rows; tick succeeds."""
    register = BoundaryFlowRegister()
    ctx = _make_context(
        session_id=uuid4(),
        tick=0,
        register=register,
        external_nodes_phi={"sub_saharan_africa": 0.0, "china": 100_000.0},
        county_exposure_by_external={
            "sub_saharan_africa": {"26163": 1.0},
            "china": {"26163": 1.0},
        },
    )
    ImperialRentSystem()._invoke_phi_distribution_if_wired(ctx)  # noqa: SLF001

    rows = _drain_rows(register)
    sources = {r.source_node_id for r in rows}
    assert "china" in sources  # non-zero inflow → rows emitted
    assert "sub_saharan_africa" not in sources  # zero inflow → no rows


def test_fr_021_annual_conservation_52_ticks_sum_equals_phi_year() -> None:
    """FR-021: 52 weekly distributions sum to phi_year_inflow within 52 × eps."""
    register = BoundaryFlowRegister()
    session_id = uuid4()
    external_nodes_phi = {"canada": 52_000.0}
    exposure = {"canada": {"26163": 0.4, "26125": 0.35, "26099": 0.25}}
    sys = ImperialRentSystem()
    for tick in range(52):
        ctx = _make_context(
            session_id=session_id,
            tick=tick,
            register=register,
            external_nodes_phi=external_nodes_phi,
            county_exposure_by_external=exposure,
        )
        sys._invoke_phi_distribution_if_wired(ctx)  # noqa: SLF001

    rows = _drain_rows(register)
    assert len(rows) == 52 * 3  # 52 ticks × 3 counties
    annual_total = sum(r.magnitude for r in rows)
    expected = 52_000.0
    assert abs(annual_total - expected) <= 52 * 1e-9 * expected


def test_wiring_silent_noop_when_context_missing_keys() -> None:
    """Back-compat: missing any of the 4 required context keys → no-op, no exception."""
    register = BoundaryFlowRegister()
    sys = ImperialRentSystem()
    # Empty context (no spec-063 keys) — must not raise
    empty_ctx = TickContext(tick=0)
    sys._invoke_phi_distribution_if_wired(empty_ctx)  # noqa: SLF001
    assert _drain_rows(register) == []

    # Partial context (register but missing exposure) — must not raise
    partial = TickContext(tick=0)
    partial.persistent_data["session_id"] = uuid4()
    partial.persistent_data["boundary_flow_register"] = register
    partial.persistent_data["external_nodes_phi"] = {"canada": 100.0}
    # missing county_exposure_by_external
    sys._invoke_phi_distribution_if_wired(partial)  # noqa: SLF001
    assert _drain_rows(register) == []


def test_step_calls_invoke_phi_distribution_seam(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Smoke: ImperialRentSystem.step() invokes _invoke_phi_distribution_if_wired exactly once.

    Verifies the seam is wired into the public step() method without
    requiring the full 5-phase economic circuit to execute (which has
    its own substantial fixture surface).
    """
    sys = ImperialRentSystem()
    seam_calls: list[TickContext] = []

    def fake_invoke(self, context, services=None):  # type: ignore[no-untyped-def]
        seam_calls.append(context)

    monkeypatch.setattr(ImperialRentSystem, "_invoke_phi_distribution_if_wired", fake_invoke)

    # Stub out the rest of step() so the test stays focused on the seam.
    def _noop_load_economy(_self, _graph, _services):  # type: ignore[no-untyped-def]
        return _StubEconomy()

    def _noop(*_a, **_kw):  # type: ignore[no-untyped-def]
        return None

    monkeypatch.setattr(ImperialRentSystem, "_load_economy", _noop_load_economy)
    for phase in (
        "_process_extraction_phase",
        "_process_tribute_phase",
        "_process_wages_phase",
        "_process_subsidy_phase",
        "_process_decision_phase",
        "_save_economy",
        "_invoke_vol2_circulation_if_wired",
    ):
        monkeypatch.setattr(ImperialRentSystem, phase, _noop)

    graph = BabylonGraph()
    ctx = TickContext(tick=5)

    class _DummyServices:
        class _DummyDefines:
            class _DummyEconomy:
                initial_rent_pool = 100.0

            economy = _DummyEconomy()

        defines = _DummyDefines()

    sys.step(graph, _DummyServices(), ctx)
    assert len(seam_calls) == 1
    assert seam_calls[0] is ctx


class _StubEconomy:
    """Minimal stub for the in-graph economy object."""

    imperial_rent_pool = 100.0
    current_super_wage_rate = 0.2
    current_repression_level = 0.0
