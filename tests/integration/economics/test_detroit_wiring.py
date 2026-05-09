"""End-to-end integration test for Detroit vertical slice wiring.

Feature: 020-detroit-vertical-slice
Task: T017

Tests the full pipeline: from_sqlite() with years parameter wires
economics calculators into ServiceContainer, enabling TickDynamicsSystem
to execute its full 8-step pipeline with real QCEW/BEA data.

Requires: marxist-data-3NF.sqlite with QCEW data for FIPS 26163/26125.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Skip entire module if database not available
_DB_PATH = Path("data/sqlite/marxist-data-3NF.sqlite")


@pytest.mark.integration
class TestDetroitWiring:
    """End-to-end test: real data -> real economics -> real game ticks."""

    @pytest.fixture(autouse=True)
    def _require_database(self) -> None:
        """Skip all tests if database is not available."""
        if not _DB_PATH.exists():
            pytest.skip(f"Database not found at {_DB_PATH}")

    def test_from_sqlite_wires_calculators(self) -> None:
        """from_sqlite with years param produces non-None calculators."""
        from babylon.engine.simulation import Simulation

        sim = Simulation.from_sqlite(
            ["26163", "26125"],
            year=2022,
            years=[2022],
        )

        assert sim._calculator_overrides is not None
        assert "melt_calculator" in sim._calculator_overrides
        assert "tensor_registry" in sim._calculator_overrides
        # Vol III financial (11) + Vol II circulation (3) + Vol I production (3) + base (7)
        # Spec 057: base count is 7 (was 8 — 'imperial_rent_calculator' removed in
        # commit a5f73139; new Leontief pipeline wires 4 fields directly via
        # ServiceContainer, not through this factory).
        assert len(sim._calculator_overrides) == 24
        # Key volume-specific calculators present
        assert "interest_calculator" in sim._calculator_overrides
        assert "distribution_calculator" in sim._calculator_overrides
        assert "turnover_profile_source" in sim._calculator_overrides
        assert "reserve_army_data_source" in sim._calculator_overrides

    def test_single_tick_runs_without_error(self) -> None:
        """A single simulation tick completes without error."""
        from babylon.engine.simulation import Simulation

        sim = Simulation.from_sqlite(
            ["26163", "26125"],
            year=2022,
            years=[2022],
        )

        # Should not raise
        sim.step()

    def test_year_boundary_produces_tick_state(self) -> None:
        """After 52 ticks, TickDynamicsSystem writes state to persistent context."""
        from babylon.economics.tick.graph_bridge import _reconstruct_tick_state
        from babylon.engine.simulation import Simulation

        sim = Simulation.from_sqlite(
            ["26163", "26125"],
            year=2022,
            years=[2022],
        )

        # Run to first year boundary
        for _ in range(52):
            sim.step()

        # Verify tick state via persistent_context snapshots
        # (to_graph() round-trip loses tick_* attributes — see CLAUDE.md gotchas)
        snapshots = sim._persistent_context.get("_tick_dynamics_snapshots", [])
        assert len(snapshots) >= 1, "No tick dynamics snapshots after 52 ticks"

        tick_state = _reconstruct_tick_state(snapshots[-1])
        assert tick_state is not None
        assert tick_state.year >= 2022
        assert len(tick_state.county_states) >= 1

    def test_get_time_series_returns_records(self) -> None:
        """get_time_series() returns records after year boundary."""
        from babylon.engine.simulation import Simulation

        sim = Simulation.from_sqlite(
            ["26163", "26125"],
            year=2022,
            years=[2022],
        )

        # Run one full year (52 ticks)
        for _ in range(52):
            sim.step()

        records = sim.get_time_series()

        # Must have records (2 counties x 1 year boundary)
        assert len(records) >= 1
        first = records[0]
        assert "year" in first
        assert "fips" in first
        assert "la_share" in first
        assert "data_source" in first

    def test_time_series_includes_volume_fields(self) -> None:
        """Time series records contain Vol I/II/III fields after year boundary."""
        from babylon.engine.simulation import Simulation

        sim = Simulation.from_sqlite(
            ["26163", "26125"],
            year=2022,
            years=[2022],
        )

        for _ in range(52):
            sim.step()

        records = sim.get_time_series()
        assert len(records) >= 1
        first = records[0]

        # Vol I production fields
        assert "capital_stock" in first
        assert "median_wage" in first
        assert "employment" in first
        assert first["capital_stock"] is not None
        assert first["capital_stock"] > 0

        # Vol II circulation fields (always present via default)
        assert "circuit_money" in first
        assert "liquidity_ratio" in first

        # Vol III finance fields (keys present, values may be None without FRED)
        assert "surplus_total" in first
        assert "interest_payments" in first
        assert "profit_of_enterprise" in first
        assert "overaccumulation" in first
        assert "profit_squeeze" in first

        # Profit rate must be a reasonable value, not capital_stock
        assert "profit_rate" in first
        if first["profit_rate"] is not None:
            assert -1.0 < first["profit_rate"] < 1.0, (
                f"profit_rate={first['profit_rate']} looks like capital_stock, not a rate"
            )

    def test_calculator_overrides_none_without_years(self) -> None:
        """from_sqlite WITHOUT years param does NOT wire calculators."""
        from babylon.engine.simulation import Simulation

        sim = Simulation.from_sqlite(
            ["26163", "26125"],
            year=2022,
        )

        assert sim._calculator_overrides is None
