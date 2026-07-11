"""Phi-week distribution tests (T058 / T074 / FR-034 / FR-035 / SC-010)."""

from __future__ import annotations

import math
from uuid import uuid4

import pytest

from babylon.domain.economics.boundary_flow_register import (
    BoundaryEdgeKind,
    BoundaryFlowRegister,
    NodeKind,
)
from babylon.engine.systems.phi_distribution import distribute_phi_week_to_counties


@pytest.mark.cross_scale
class TestDistributePhiWeekToCounties:
    def test_single_county_receives_full_weekly_share(self) -> None:
        register = BoundaryFlowRegister()
        sid = uuid4()
        transfers = distribute_phi_week_to_counties(
            session_id=sid,
            tick=0,
            external_node_id="canada",
            phi_year_inflow=100_000_000.0,
            county_exposure={"26163": 1.0},
            register=register,
        )
        weekly = 100_000_000.0 / 52.0
        assert math.isclose(transfers["26163"], weekly, abs_tol=1e-6)

    def test_two_county_split_sums_to_weekly(self) -> None:
        register = BoundaryFlowRegister()
        sid = uuid4()
        transfers = distribute_phi_week_to_counties(
            session_id=sid,
            tick=0,
            external_node_id="canada",
            phi_year_inflow=100_000_000.0,
            county_exposure={"26163": 0.6, "26125": 0.4},
            register=register,
        )
        weekly = 100_000_000.0 / 52.0
        assert math.isclose(sum(transfers.values()), weekly, abs_tol=1e-6)
        # 60/40 weighting respected.
        assert math.isclose(transfers["26163"], weekly * 0.6, abs_tol=1e-6)
        assert math.isclose(transfers["26125"], weekly * 0.4, abs_tol=1e-6)

    def test_drain_edges_recorded_for_each_county(self) -> None:
        register = BoundaryFlowRegister()
        sid = uuid4()
        distribute_phi_week_to_counties(
            session_id=sid,
            tick=0,
            external_node_id="china",
            phi_year_inflow=52_000.0,
            county_exposure={"26163": 0.5, "26125": 0.5},
            register=register,
        )
        rows = register.flush()
        assert len(rows) == 2
        for row in rows:
            assert row.flow_type is BoundaryEdgeKind.DRAIN_EDGE
            assert row.source_node_id == "china"
            assert row.source_kind is NodeKind.EXTERNAL
            assert row.dest_kind is NodeKind.COUNTY
            assert row.magnitude == 500.0

    def test_rejects_negative_phi(self) -> None:
        register = BoundaryFlowRegister()
        with pytest.raises(ValueError, match="non-negative"):
            distribute_phi_week_to_counties(
                session_id=uuid4(),
                tick=0,
                external_node_id="canada",
                phi_year_inflow=-1.0,
                county_exposure={"26163": 1.0},
                register=register,
            )

    def test_rejects_non_unit_exposure_weights(self) -> None:
        """FR-031 + Constitution III.1: weights must be normalized at the call site."""
        register = BoundaryFlowRegister()
        with pytest.raises(ValueError, match="weights must sum to 1.0"):
            distribute_phi_week_to_counties(
                session_id=uuid4(),
                tick=0,
                external_node_id="canada",
                phi_year_inflow=1000.0,
                county_exposure={"26163": 0.5, "26125": 0.3},  # sum 0.8
                register=register,
            )

    def test_annual_aggregate_matches_phi_year(self) -> None:
        """FR-035: 52 weeks of distribution sum to phi_year exactly within ε."""
        register = BoundaryFlowRegister()
        sid = uuid4()
        phi_year = 100_000.0
        county_exposure = {"26163": 0.6, "26125": 0.4}
        weekly_totals = []
        for week in range(52):
            transfers = distribute_phi_week_to_counties(
                session_id=sid,
                tick=week,
                external_node_id="canada",
                phi_year_inflow=phi_year,
                county_exposure=county_exposure,
                register=register,
            )
            weekly_totals.append(sum(transfers.values()))
        annual = sum(weekly_totals)
        assert math.isclose(annual, phi_year, abs_tol=1e-6), (
            f"FR-035 violated: sum of 52 weekly slices = {annual}, expected {phi_year}"
        )

    def test_empty_county_exposure_returns_empty(self) -> None:
        register = BoundaryFlowRegister()
        out = distribute_phi_week_to_counties(
            session_id=uuid4(),
            tick=0,
            external_node_id="canada",
            phi_year_inflow=1000.0,
            county_exposure={},
            register=register,
        )
        assert out == {}
        assert register.flush() == []
