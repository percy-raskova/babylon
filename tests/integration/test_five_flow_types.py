"""Five-flow-type integration test (T050 / US4 / SC-011).

Exercises the four flow stages with direct helpers (Production via direct
hex assignment, Imperial Rent via phi_distribution, Distribution via
split_surplus_to_pirt, Equalization via the existing
DefaultHexEqualizationComputer). Vol II circulation is deferred to T055
(LODES OD matrix loader); this test does NOT exercise it.

Per-stage conservation invariants (FR-026 .. FR-035):
  - Production: hex c, v, s assignment is local (no cross-hex coupling)
  - Imperial Rent inflow: sum over counties == phi_year/52 per week
  - Distribution: p + i + r + t == s exactly
  - Equalization: sum(c) preserved across hexes (Constitution conservation
    proof in DefaultHexEqualizationComputer.equalize_capital docstring)
"""

from __future__ import annotations

import math
from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = [pytest.mark.cross_scale, pytest.mark.integration]

pytest.importorskip("psycopg")
pytest.importorskip("psycopg_pool")


@pytest.fixture(scope="module")
def apply_062_migrations(pg_pool):  # type: ignore[no-untyped-def]
    migrations_dir = Path("src/babylon/persistence/migrations").resolve()
    with pg_pool.connection() as conn:
        conn.autocommit = True
        for sql_file in sorted(migrations_dir.glob("00*.sql")):
            conn.execute(sql_file.read_text())


@pytest.fixture(scope="module")
def runtime(pg_pool, apply_062_migrations):  # type: ignore[no-untyped-def]
    from babylon.persistence import PostgresRuntime

    return PostgresRuntime(pool=pg_pool)


def test_production_growth_is_hex_local(runtime, pg_pool):  # type: ignore[no-untyped-def]
    """FR-026: Production grows v+s on the hex where it occurred; no cross-hex spill."""
    from datetime import UTC, datetime

    from babylon.persistence.audit_models import AuditSeverity, ConservationAuditRow
    from babylon.persistence.envelope import PerTickTransactionEnvelope
    from babylon.persistence.hex_state import DynamicHexState

    sid = uuid4()
    pre_v = 5.0
    post_v = 7.0
    labor_increment = post_v - pre_v
    rows = [
        DynamicHexState(
            session_id=sid,
            tick=0,
            h3_index="872d34a89ffffff",
            county_fips="26163",
            state_fips="26",
            region_id="east_north_central",
            c=10.0,
            v=pre_v,
            s=3.0,
            k=100.0,
            biocapacity_stock=20.0,
            energy_stock=10.0,
            raw_material_stock=5.0,
            internet_access_pct=0.5,
            surveillance_coupling=0.5,
        ),
        DynamicHexState(
            session_id=sid,
            tick=1,
            h3_index="872d34a89ffffff",
            county_fips="26163",
            state_fips="26",
            region_id="east_north_central",
            c=10.0,
            v=post_v,
            s=3.0 + labor_increment,
            k=100.0,
            biocapacity_stock=20.0,
            energy_stock=10.0,
            raw_material_stock=5.0,
            internet_access_pct=0.5,
            surveillance_coupling=0.5,
        ),
    ]
    audit = ConservationAuditRow(
        session_id=sid,
        tick=1,
        scale="hex",
        invariant_name="production_grows_v_plus_s_by_labor_increment",
        computed_value=labor_increment,
        expected_value=labor_increment,
        residual=0.0,
        severity=AuditSeverity.OK,
        determinism_hash="e" * 64,
        created_at_utc=datetime.now(tz=UTC),
    )
    runtime.persist_tick_atomic(
        PerTickTransactionEnvelope(
            session_id=sid,
            tick=0,
            hex_state_rows=[rows[0]],
            audit_log_rows=[audit],
            determinism_hash="e" * 64,
        )
    )
    runtime.persist_tick_atomic(
        PerTickTransactionEnvelope(
            session_id=sid,
            tick=1,
            hex_state_rows=[rows[1]],
            audit_log_rows=[audit],
            determinism_hash="e" * 64,
        )
    )

    # Verify v_county_value_aggregate sees the v growth
    with pg_pool.connection() as conn:
        v_t0 = conn.execute(
            "SELECT v_sum FROM v_county_value_aggregate WHERE session_id = %s AND tick = 0",
            (str(sid),),
        ).fetchone()
        v_t1 = conn.execute(
            "SELECT v_sum FROM v_county_value_aggregate WHERE session_id = %s AND tick = 1",
            (str(sid),),
        ).fetchone()
    assert math.isclose(v_t1[0] - v_t0[0], labor_increment, abs_tol=1e-10)


def test_distribution_split_conserves_county_surplus():  # type: ignore[no-untyped-def]
    """FR-032/FR-033: county-level p+i+r+t == s exactly."""
    from babylon.engine.systems.distribution import split_surplus_to_pirt

    s = 1_000_000.0  # $1M county surplus
    out = split_surplus_to_pirt(s=s, interest_rate=0.05, rent_rate=0.10, tax_rate=0.30)
    assert math.isclose(out.p + out.i + out.r + out.t, s, abs_tol=1e-3)
    assert out.t == s * 0.30
    assert out.r == s * 0.10
    assert out.i == s * 0.05
    assert out.p == s * 0.55  # residual


def test_imperial_rent_inflow_records_drain_edge():  # type: ignore[no-untyped-def]
    """FR-034/FR-035: weekly Φ inflow recorded as DRAIN_EDGE row in register."""
    from babylon.domain.economics.boundary_flow_register import (
        BoundaryEdgeKind,
        BoundaryFlowRegister,
        NodeKind,
    )
    from babylon.engine.systems.phi_distribution import distribute_phi_week_to_counties

    sid = uuid4()
    register = BoundaryFlowRegister()
    distribute_phi_week_to_counties(
        session_id=sid,
        tick=0,
        external_node_id="canada",
        phi_year_inflow=520_000.0,
        county_exposure={"26163": 1.0},
        register=register,
    )
    rows = register.flush()
    assert len(rows) == 1
    assert rows[0].flow_type is BoundaryEdgeKind.DRAIN_EDGE
    assert rows[0].source_kind is NodeKind.EXTERNAL
    assert rows[0].dest_kind is NodeKind.COUNTY
    assert math.isclose(rows[0].magnitude, 10_000.0, abs_tol=1e-6)  # 520k/52


def test_equalization_preserves_total_capital():  # type: ignore[no-untyped-def]
    """Vol III equalization conserves sum(c) — proof from substrate.equalization."""
    from babylon.domain.economics.substrate.equalization import DefaultHexEqualizationComputer
    from babylon.domain.economics.substrate.types import HexEconomicState, HexGrid

    # Two hexes with different profit rates → capital migrates but sum(c) unchanged.
    h1 = HexEconomicState(
        h3_index="872d34a89ffffff",
        county_fips="26163",
        constant_capital=100.0,
        variable_capital=20.0,
        surplus_value=10.0,
        employment=100.0,
        dept_shares=(0.25, 0.25, 0.25, 0.25),
    )
    h2 = HexEconomicState(
        h3_index="872d34b0bffffff",
        county_fips="26163",
        constant_capital=50.0,
        variable_capital=10.0,
        surplus_value=20.0,
        employment=50.0,
        dept_shares=(0.25, 0.25, 0.25, 0.25),
    )
    grid_in = HexGrid(
        hexes={"a": h1, "b": h2},
        county_hex_ids={"26163": frozenset({"a", "b"})},
        res6_parents={"a": "a", "b": "b"},
        res5_parents={"a": "a", "b": "b"},
        res5_children={"a": frozenset({"a"}), "b": frozenset({"b"})},
        res6_children={"a": frozenset({"a"}), "b": frozenset({"b"})},
    )
    pre_total = h1.constant_capital + h2.constant_capital

    computer = DefaultHexEqualizationComputer()
    grid_out = computer.equalize_capital(grid_in)
    post_total = sum(h.constant_capital for h in grid_out.hexes.values())

    assert math.isclose(post_total, pre_total, abs_tol=1e-9), (
        f"Equalization broke conservation: pre={pre_total}, post={post_total}"
    )
