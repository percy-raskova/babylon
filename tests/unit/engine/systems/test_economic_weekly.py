"""Tests for weekly tick conversion in economic systems.

TDD Red Phase: These tests define the contract for weekly tick conversion.

Epoch 0 Physics Hardening:
- 1 tick = 7 days (weekly resolution)
- 52 weeks = 1 year
- Annual economic rates are converted to per-tick rates via division by 52

This ensures that:
- Running 52 ticks produces expected annual outcomes
- Economic flows are properly scaled to the simulation's temporal resolution
- Compounding behavior is predictable over game years

The weekly tick model provides:
- Enough granularity for political events (weekly news cycles)
- Reasonable simulation run times (52 ticks per game year)
- Clean arithmetic (52 divides evenly into many annual rates)
"""

from __future__ import annotations

import networkx as nx
import pytest

from babylon.config.defines import GameDefines
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.models.enums import EdgeType, SocialRole

# =============================================================================
# WEEKLY CONVERSION TESTS (RED PHASE)
# =============================================================================


@pytest.mark.red_phase
@pytest.mark.topology
class TestWeeklyConversion:
    """Test that economic flows use weekly tick conversion.

    Economic rates in the simulation are configured as annual rates
    (e.g., super_wage_rate = 0.52 means 52% of tribute goes to wages per year).

    These rates must be converted to per-tick rates by dividing by
    weeks_per_year (52 by default):
    - annual_rate = 0.52
    - per_tick_rate = 0.52 / 52 = 0.01 (1% per tick)

    Over 52 ticks (1 game year), the cumulative effect matches the annual rate.
    """

    def test_wages_use_weekly_conversion(self) -> None:
        """Wage rate is divided by weeks_per_year (52) for per-tick calculation.

        Setup: Configure annual_wage_rate = 0.52 (52% annual)
        Expected: per_tick_rate = 0.52 / 52 = 0.01 (1% per tick)

        This test runs a single tick and verifies that only 1/52 of the
        annual wage rate is applied.
        """
        # Arrange: Graph with wages edge
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "bourgeoisie",
            wealth=1.0,
            role=SocialRole.CORE_BOURGEOISIE,
        )
        graph.add_node(
            "worker",
            wealth=0.0,
            role=SocialRole.LABOR_ARISTOCRACY,
        )
        graph.add_edge("bourgeoisie", "worker", edge_type=EdgeType.WAGES)

        # Configure annual wage rate at 52% (should become 1% per tick)
        defines = GameDefines()
        # We need to verify that defines.timescale.weeks_per_year == 52
        assert defines.timescale.weeks_per_year == 52

        services = ServiceContainer.create()
        system = ImperialRentSystem()

        # Simulate tribute inflow of 1.0 (basis for wage calculation)
        tick_context = {
            "tribute_inflow": 1.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 100.0,
            "wage_rate": 0.52,  # 52% annual rate
            "repression_level": 0.5,
        }

        # Act
        system._process_wages_phase(graph, services, {"tick": 1}, tick_context)

        # Assert: Worker should receive 1% of tribute (0.01), not 52%
        worker_wealth = graph.nodes["worker"]["wealth"]
        # Expected: 1.0 * 0.52 / 52 = 0.01
        assert worker_wealth == pytest.approx(0.01, rel=0.01)

    def test_52_week_cycle_returns_to_annual_rate(self) -> None:
        """Running 52 ticks with weekly conversion equals annual rate.

        If we apply 1% per tick for 52 ticks using simple interest:
        - Cumulative = 52 * 0.01 = 0.52 (52%)

        With compound interest:
        - (1.01)^52 = 1.68 (68% growth)

        This test verifies that the simulation uses simple interest
        (additive) for wages, resulting in the annual rate over 52 ticks.
        """
        # Arrange: Graph with wages edge
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "bourgeoisie",
            wealth=100.0,  # Large enough for 52 payments
            role=SocialRole.CORE_BOURGEOISIE,
        )
        graph.add_node(
            "worker",
            wealth=0.0,
            role=SocialRole.LABOR_ARISTOCRACY,
        )
        graph.add_edge("bourgeoisie", "worker", edge_type=EdgeType.WAGES)

        # Verify timescale defines exist (this assertion will fail in RED phase)
        defines = GameDefines()
        assert hasattr(defines, "timescale")  # Use defines to avoid unused variable

        services = ServiceContainer.create()
        system = ImperialRentSystem()

        annual_wage_rate = 0.52  # 52% annual
        initial_tribute = 1.0

        # Act: Run 52 ticks (1 game year)
        total_wages_paid = 0.0
        for tick in range(52):
            tick_context = {
                "tribute_inflow": initial_tribute,
                "wages_outflow": 0.0,
                "subsidy_outflow": 0.0,
                "current_pool": 100.0,
                "wage_rate": annual_wage_rate,
                "repression_level": 0.5,
            }

            # Track wages before this tick
            worker_wealth_before = graph.nodes["worker"]["wealth"]

            system._process_wages_phase(graph, services, {"tick": tick}, tick_context)

            # Calculate wages paid this tick
            worker_wealth_after = graph.nodes["worker"]["wealth"]
            wages_this_tick = worker_wealth_after - worker_wealth_before
            total_wages_paid += wages_this_tick

        # Assert: Total wages over 52 weeks equals annual rate
        # Expected: 52 * (1.0 * 0.52 / 52) = 0.52
        assert total_wages_paid == pytest.approx(0.52, rel=0.01)

    def test_extraction_uses_weekly_conversion(self) -> None:
        """Imperial rent extraction is also scaled to weekly ticks.

        The extraction_efficiency coefficient represents annual extraction.
        Per-tick extraction should be: annual_rate / 52.
        """
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "worker",
            wealth=1.0,
            role=SocialRole.PERIPHERY_PROLETARIAT,
        )
        graph.add_node(
            "owner",
            wealth=0.0,
            role=SocialRole.COMPRADOR_BOURGEOISIE,
        )
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)

        defines = GameDefines()
        # annual extraction_efficiency should be divided by 52
        assert defines.timescale.weeks_per_year == 52

        services = ServiceContainer.create()
        system = ImperialRentSystem()

        # Act
        system._process_extraction_phase(graph, services, {"tick": 1})

        # Assert: Extraction should be 1/52 of annual rate
        # If annual extraction_efficiency is 0.8, per-tick is 0.8/52 = 0.0154
        owner_wealth = graph.nodes["owner"]["wealth"]
        # With worker wealth = 1.0, per-tick extraction = 1.0 * 0.8 / 52
        expected_weekly_extraction = 1.0 * defines.economy.extraction_efficiency / 52
        assert owner_wealth == pytest.approx(expected_weekly_extraction, rel=0.01)


# =============================================================================
# TIMESCALE DEFINES INTEGRATION TESTS (RED PHASE)
# =============================================================================


@pytest.mark.red_phase
@pytest.mark.unit
class TestTimescaleInEconomicSystem:
    """Test that economic system reads timescale from GameDefines."""

    def test_system_uses_defines_weeks_per_year(self) -> None:
        """ImperialRentSystem should read weeks_per_year from GameDefines.

        The system should not hardcode 52; it should read from:
        services.defines.timescale.weeks_per_year

        This allows:
        - Fast simulation mode (fewer weeks per year)
        - Longer simulations (more weeks per year)
        - Historical accuracy tuning
        """
        # Arrange: Create services with custom defines
        # Note: GameDefines is frozen, so we need a different approach
        # For now, verify the default is 52
        services = ServiceContainer.create()

        # Assert: Services should expose timescale (via services.defines)
        assert hasattr(services.defines, "timescale")
        assert services.defines.timescale.weeks_per_year == 52

    def test_custom_weeks_per_year_affects_calculations(self) -> None:
        """If weeks_per_year is changed, economic calculations adapt.

        Example: If weeks_per_year = 26 (bi-weekly resolution):
        - annual_rate = 0.52
        - per_tick_rate = 0.52 / 26 = 0.02 (2% per tick)

        This test verifies that the system correctly reads and uses
        the timescale configuration.
        """
        # This test requires the ability to create GameDefines with
        # custom timescale settings, which is a GREEN phase implementation
        #
        # For RED phase, we just verify the attribute structure exists
        defines = GameDefines()

        # These assertions will fail until TimescaleDefines is implemented
        assert hasattr(defines, "timescale")
        assert hasattr(defines.timescale, "weeks_per_year")
        assert hasattr(defines.timescale, "tick_duration_days")
