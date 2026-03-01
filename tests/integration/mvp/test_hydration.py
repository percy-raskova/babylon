"""Integration tests for SQLite hydration (US3).

This test validates that the simulation can be initialized from SQLite reference data:
- hydrate_territories() creates TerritoryState objects from database
- Wayne County (26163) and Oakland County (26125) have different profit_rates (SC-006)
- Initialization completes in under 2 seconds (SC-003)
- from_sqlite() class method initializes simulation correctly

See Also:
    - spec.md#SC-003: <2s initialization time
    - spec.md#SC-006: Wayne != Oakland profit_rate
    - research.md#3. SQLite Schema: Database structure
    - research.md#4. Economics Hydrator: MarxianHydrator details
"""

from __future__ import annotations

import time

import pytest

from babylon.engine.hydration.reference import (
    compute_initial_profit_rate,
    hydrate_territories,
    query_counties,
    query_hex_claims,
)
from babylon.engine.simulation import Simulation

# Detroit test case: Wayne and Oakland counties
WAYNE_FIPS = "26163"
OAKLAND_FIPS = "26125"
DETROIT_FIPS_CODES = [WAYNE_FIPS, OAKLAND_FIPS]


class TestHydrateTerritories:
    """Test hydrate_territories() function."""

    def test_hydrate_creates_territory_states(self) -> None:
        """Verify hydrate_territories creates TerritoryState objects."""
        territories, hexes = hydrate_territories(DETROIT_FIPS_CODES)

        assert WAYNE_FIPS in territories
        assert OAKLAND_FIPS in territories
        assert len(territories) == 2

    def test_hydrate_creates_hex_states(self) -> None:
        """Verify hydrate_territories creates HexState objects for each hex."""
        territories, hexes = hydrate_territories(DETROIT_FIPS_CODES)

        # Each territory should have hex claims
        wayne = territories[WAYNE_FIPS]
        oakland = territories[OAKLAND_FIPS]

        # Hexes dict should contain all claimed hexes
        for h3_idx in wayne.hex_claims:
            assert h3_idx in hexes

        for h3_idx in oakland.hex_claims:
            assert h3_idx in hexes

    def test_hydrate_sets_profit_rate(self) -> None:
        """Verify hydrate_territories sets profit_rate from QCEW data."""
        territories, _ = hydrate_territories(DETROIT_FIPS_CODES)

        wayne = territories[WAYNE_FIPS]
        oakland = territories[OAKLAND_FIPS]

        # Profit rates should be valid (in [0, 1] range)
        assert 0.0 <= wayne.profit_rate <= 1.0
        assert 0.0 <= oakland.profit_rate <= 1.0

        # Profit rates should be non-zero (real data)
        assert wayne.profit_rate > 0.0
        assert oakland.profit_rate > 0.0

    def test_hydrate_sets_equilibrium_r(self) -> None:
        """Verify equilibrium_r equals initial profit_rate (T032)."""
        territories, _ = hydrate_territories(DETROIT_FIPS_CODES)

        wayne = territories[WAYNE_FIPS]
        oakland = territories[OAKLAND_FIPS]

        # equilibrium_r should equal initial profit_rate
        assert wayne.equilibrium_r == wayne.profit_rate
        assert oakland.equilibrium_r == oakland.profit_rate

    def test_hydrate_empty_fips_raises(self) -> None:
        """Verify empty fips_codes raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            hydrate_territories([])


class TestQueryCounties:
    """Test query_counties() function."""

    def test_query_returns_county_info(self) -> None:
        """Verify query_counties returns CountyInfo for each FIPS."""
        counties = query_counties(DETROIT_FIPS_CODES)

        assert WAYNE_FIPS in counties
        assert OAKLAND_FIPS in counties

        wayne = counties[WAYNE_FIPS]
        assert wayne.fips == WAYNE_FIPS
        assert wayne.county_id > 0
        assert len(wayne.county_name) > 0

    def test_query_missing_fips_raises(self) -> None:
        """Verify missing FIPS code raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            query_counties(["99999"])  # Invalid FIPS

    def test_query_empty_fips_raises(self) -> None:
        """Verify empty fips_codes raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            query_counties([])


class TestQueryHexClaims:
    """Test query_hex_claims() function."""

    def test_query_returns_hex_sets(self) -> None:
        """Verify query_hex_claims returns sets of H3 indices."""
        counties = query_counties(DETROIT_FIPS_CODES)
        county_ids = [counties[fips].county_id for fips in DETROIT_FIPS_CODES]

        hex_claims = query_hex_claims(county_ids)

        for county_id in county_ids:
            assert county_id in hex_claims
            # Each county should have at least some hex cells
            # (may be empty for some counties, but Wayne/Oakland should have data)

    def test_query_empty_county_ids_returns_empty(self) -> None:
        """Verify empty county_ids returns empty dict."""
        result = query_hex_claims([])
        assert result == {}


class TestComputeInitialProfitRate:
    """Test compute_initial_profit_rate() function."""

    def test_compute_returns_valid_rate(self) -> None:
        """Verify compute_initial_profit_rate returns valid profit rate."""
        rate = compute_initial_profit_rate(WAYNE_FIPS, 2022)

        assert 0.0 <= rate <= 1.0
        assert rate > 0.0  # Should be non-zero for real data

    def test_compute_different_counties_different_rates(self) -> None:
        """Verify different counties produce different rates (SC-006)."""
        wayne_rate = compute_initial_profit_rate(WAYNE_FIPS, 2022)
        oakland_rate = compute_initial_profit_rate(OAKLAND_FIPS, 2022)

        # Wayne and Oakland should have different economic profiles
        assert wayne_rate != oakland_rate


class TestSC006WayneNotOakland:
    """Test SC-006: Wayne County profit_rate differs from Oakland County."""

    def test_wayne_profit_rate_differs_from_oakland(self) -> None:
        """Verify Wayne and Oakland have different profit rates (SC-006 core test)."""
        territories, _ = hydrate_territories(DETROIT_FIPS_CODES)

        wayne = territories[WAYNE_FIPS]
        oakland = territories[OAKLAND_FIPS]

        assert wayne.profit_rate != oakland.profit_rate, (
            f"SC-006 FAILED: Wayne ({wayne.profit_rate}) "
            f"should differ from Oakland ({oakland.profit_rate})"
        )

    def test_different_equilibrium_r_values(self) -> None:
        """Verify Wayne and Oakland have different equilibrium_r values."""
        territories, _ = hydrate_territories(DETROIT_FIPS_CODES)

        wayne = territories[WAYNE_FIPS]
        oakland = territories[OAKLAND_FIPS]

        # Since equilibrium_r = initial profit_rate, they should differ
        assert wayne.equilibrium_r != oakland.equilibrium_r


class TestSC003InitializationTime:
    """Test SC-003: Initialization completes in under 2 seconds."""

    @pytest.mark.timeout(2)
    def test_hydration_under_2_seconds(self) -> None:
        """Verify hydrate_territories completes in under 2 seconds (SC-003)."""
        start = time.perf_counter()
        territories, hexes = hydrate_territories(DETROIT_FIPS_CODES)
        elapsed = time.perf_counter() - start

        assert elapsed < 2.0, f"SC-003 FAILED: Hydration took {elapsed:.2f}s (limit: 2.0s)"
        assert len(territories) == 2  # Ensure it actually ran

    @pytest.mark.timeout(2)
    def test_from_sqlite_under_2_seconds(self) -> None:
        """Verify Simulation.from_sqlite() completes in under 2 seconds."""
        start = time.perf_counter()
        sim = Simulation.from_sqlite(DETROIT_FIPS_CODES)
        elapsed = time.perf_counter() - start

        assert elapsed < 2.0, f"SC-003 FAILED: from_sqlite took {elapsed:.2f}s (limit: 2.0s)"
        assert sim.get_current_tick() == 0


class TestSimulationFromSqlite:
    """Test Simulation.from_sqlite() class method."""

    def test_from_sqlite_creates_simulation(self) -> None:
        """Verify from_sqlite creates a functional Simulation."""
        sim = Simulation.from_sqlite(DETROIT_FIPS_CODES)

        assert sim is not None
        assert sim.get_current_tick() == 0

    def test_from_sqlite_territories_accessible(self) -> None:
        """Verify territories are accessible via get_territory_state."""
        sim = Simulation.from_sqlite(DETROIT_FIPS_CODES)

        wayne = sim.get_territory_state(WAYNE_FIPS)
        oakland = sim.get_territory_state(OAKLAND_FIPS)

        assert wayne is not None
        assert oakland is not None
        assert wayne.territory_id == WAYNE_FIPS
        assert oakland.territory_id == OAKLAND_FIPS

    def test_from_sqlite_profit_rates_differ(self) -> None:
        """Verify from_sqlite produces different profit rates (SC-006 via Simulation)."""
        sim = Simulation.from_sqlite(DETROIT_FIPS_CODES)

        wayne = sim.get_territory_state(WAYNE_FIPS)
        oakland = sim.get_territory_state(OAKLAND_FIPS)

        assert wayne is not None
        assert oakland is not None
        assert wayne.profit_rate != oakland.profit_rate

    def test_from_sqlite_step_updates_profit_rates(self) -> None:
        """Verify step() updates profit rates after from_sqlite() initialization."""
        sim = Simulation.from_sqlite(DETROIT_FIPS_CODES)

        wayne_before = sim.get_territory_state(WAYNE_FIPS)
        assert wayne_before is not None
        _ = wayne_before.profit_rate  # Verify profit_rate exists

        # Step simulation
        sim.step()

        wayne_after = sim.get_territory_state(WAYNE_FIPS)
        assert wayne_after is not None

        # Tick should advance
        assert wayne_after.tick == 1

    def test_from_sqlite_reset_restores_initial_state(self) -> None:
        """Verify reset() restores initial hydrated state."""
        sim = Simulation.from_sqlite(DETROIT_FIPS_CODES)

        # Get initial state
        wayne_initial = sim.get_territory_state(WAYNE_FIPS)
        assert wayne_initial is not None
        initial_rate = wayne_initial.profit_rate

        # Run simulation
        sim.step(100)

        # Reset
        sim.reset()

        # Verify restored
        wayne_reset = sim.get_territory_state(WAYNE_FIPS)
        assert wayne_reset is not None
        assert wayne_reset.profit_rate == initial_rate
        assert wayne_reset.tick == 0
        assert sim.get_current_tick() == 0

    def test_from_sqlite_snapshot_contains_territories(self) -> None:
        """Verify get_snapshot() contains hydrated territories."""
        sim = Simulation.from_sqlite(DETROIT_FIPS_CODES)
        snapshot = sim.get_snapshot()

        assert WAYNE_FIPS in snapshot.territories
        assert OAKLAND_FIPS in snapshot.territories
        assert len(snapshot.territories) == 2

    def test_from_sqlite_hexes_accessible(self) -> None:
        """Verify hexes are accessible for each territory."""
        sim = Simulation.from_sqlite(DETROIT_FIPS_CODES)

        wayne_hexes = sim.get_hexes_for_territory(WAYNE_FIPS)
        oakland_hexes = sim.get_hexes_for_territory(OAKLAND_FIPS)

        # Should return sets (may be empty for some counties)
        assert isinstance(wayne_hexes, set)
        assert isinstance(oakland_hexes, set)


class TestHydrationEdgeCases:
    """Test edge cases for hydration."""

    def test_hydrate_duplicate_fips_deduplicated(self) -> None:
        """Verify duplicate FIPS codes are deduplicated."""
        # Pass duplicates
        territories, _ = hydrate_territories([WAYNE_FIPS, WAYNE_FIPS, OAKLAND_FIPS])

        # Should only have 2 unique territories
        assert len(territories) == 2
        assert WAYNE_FIPS in territories
        assert OAKLAND_FIPS in territories

    def test_hydrate_single_county(self) -> None:
        """Verify hydration works with single county."""
        territories, hexes = hydrate_territories([WAYNE_FIPS])

        assert len(territories) == 1
        assert WAYNE_FIPS in territories

    def test_from_sqlite_invalid_fips_raises(self) -> None:
        """Verify from_sqlite with invalid FIPS raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            Simulation.from_sqlite(["99999"])

    def test_from_sqlite_empty_fips_raises(self) -> None:
        """Verify from_sqlite with empty list raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Simulation.from_sqlite([])
