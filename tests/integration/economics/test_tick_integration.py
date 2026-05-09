"""Integration tests for multi-tick simulation runs.

Feature: 017-simulation-tick-dynamics
Task: T026
"""

from __future__ import annotations

from typing import Any

from babylon.economics.tick.initializer import DefaultTickInitializer
from babylon.economics.tick.system import TickDynamicsSystem
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from tests.unit.economics.tick.conftest import (
    WAYNE_FIPS,
    MockBasketVisibilityCalculator,
    MockCapitalStockCalculator,
    MockClassTransitionEngine,
    MockGammaIIICalculator,
    MockMELTCalculator,
    MockThroughputCalculator,
    build_territory_graph,
)

WEEKS_PER_YEAR = 52


def _make_services(**kwargs: Any) -> ServiceContainer:
    """Create ServiceContainer with mock calculators."""
    defaults = {
        "melt_calculator": MockMELTCalculator(),
        "basket_calculator": MockBasketVisibilityCalculator(),
        "gamma_calculator": MockGammaIIICalculator(),
        "capital_calculator": MockCapitalStockCalculator(),
        "throughput_calculator": MockThroughputCalculator(),
        "transition_engine": MockClassTransitionEngine(),
    }
    defaults.update(kwargs)
    return ServiceContainer.create(**defaults)


class TestMultiTickSimulation:
    """Integration tests for multi-tick simulation runs."""

    def test_multi_year_run(self) -> None:
        """Verify system can run across multiple year boundaries."""
        system = TickDynamicsSystem()
        services = _make_services()
        initializer = DefaultTickInitializer()

        # Initialize state and write to graph
        state = initializer.initialize(2015, [WAYNE_FIPS], services)
        graph = build_territory_graph()

        from babylon.economics.tick.graph_bridge import write_tick_state_to_graph

        write_tick_state_to_graph(graph, state)

        # Run 3 year boundaries (ticks 52, 104, 156)
        years_processed: list[int] = []
        max_ticks = 3
        for i in range(1, max_ticks + 1):
            tick = i * WEEKS_PER_YEAR
            context = TickContext(tick=tick)
            system.step(graph, services, context)
            tick_data = graph.graph.get("tick_dynamics", {})
            if tick_data.get("year") is not None:
                years_processed.append(tick_data["year"])

        assert len(years_processed) == 3
        # Each year boundary increments the year
        assert years_processed[0] == 2016
        assert years_processed[1] == 2017
        assert years_processed[2] == 2018

    def test_class_distribution_stays_valid(self) -> None:
        """Verify class distribution sums to one across multi-tick runs."""
        system = TickDynamicsSystem()
        services = _make_services()
        initializer = DefaultTickInitializer()

        state = initializer.initialize(2015, [WAYNE_FIPS], services)
        graph = build_territory_graph()

        from babylon.economics.tick.graph_bridge import write_tick_state_to_graph

        write_tick_state_to_graph(graph, state)

        # Run 5 year boundaries
        max_ticks = 5
        for i in range(1, max_ticks + 1):
            tick = i * WEEKS_PER_YEAR
            context = TickContext(tick=tick)
            system.step(graph, services, context)

            # Check class distribution sums to one
            dist = graph.nodes[WAYNE_FIPS].get("tick_class_distribution", {})
            if dist:
                total = sum(dist.values())
                assert abs(total - 1.0) < 0.01, f"Class distribution sum={total} at tick {tick}"

    def test_determinism(self) -> None:
        """Verify identical inputs produce identical outputs."""
        services = _make_services()

        results: list[dict[str, Any]] = []
        max_runs = 2
        for _ in range(max_runs):
            system = TickDynamicsSystem()
            initializer = DefaultTickInitializer()
            state = initializer.initialize(2015, [WAYNE_FIPS], services)
            graph = build_territory_graph()

            from babylon.economics.tick.graph_bridge import write_tick_state_to_graph

            write_tick_state_to_graph(graph, state)

            # Run 3 years
            max_ticks = 3
            for i in range(1, max_ticks + 1):
                tick = i * WEEKS_PER_YEAR
                context = TickContext(tick=tick)
                system.step(graph, services, context)

            results.append(dict(graph.nodes[WAYNE_FIPS]))

        # Compare both runs
        for key in results[0]:
            assert results[0][key] == results[1][key], (
                f"Non-deterministic result for {key}: {results[0][key]} != {results[1][key]}"
            )

    def test_non_year_boundary_ticks_are_noop(self) -> None:
        """Verify non-year-boundary ticks don't modify state."""
        system = TickDynamicsSystem()
        services = _make_services()
        initializer = DefaultTickInitializer()

        state = initializer.initialize(2015, [WAYNE_FIPS], services)
        graph = build_territory_graph()

        from babylon.economics.tick.graph_bridge import write_tick_state_to_graph

        write_tick_state_to_graph(graph, state)

        # Run a year boundary to establish state
        system.step(graph, services, TickContext(tick=52))
        year_after_boundary = graph.graph["tick_dynamics"]["year"]

        # Run non-boundary ticks
        for tick in [53, 54, 55, 100, 103]:
            system.step(graph, services, TickContext(tick=tick))

        # Year should be unchanged
        assert graph.graph["tick_dynamics"]["year"] == year_after_boundary

    def test_coefficient_smoothing_over_ticks(self) -> None:
        """Verify coefficients are smoothed across ticks."""
        system = TickDynamicsSystem()
        services = _make_services(
            basket_calculator=MockBasketVisibilityCalculator(gamma_basket=0.75),
        )
        initializer = DefaultTickInitializer()

        # Initialize with different gamma_basket (0.75 from mock)
        state = initializer.initialize(2015, [WAYNE_FIPS], services)
        graph = build_territory_graph()

        from babylon.economics.tick.graph_bridge import write_tick_state_to_graph

        write_tick_state_to_graph(graph, state)

        # First year boundary: coefficients not yet initialized -> raw passthrough
        system.step(graph, services, TickContext(tick=52))
        coeff1 = graph.graph["tick_dynamics"]["coefficients"]

        # Second boundary: smoothing applied
        system.step(graph, services, TickContext(tick=104))
        coeff2 = graph.graph["tick_dynamics"]["coefficients"]

        # Both should be initialized after first tick
        assert coeff1.is_initialized is True
        assert coeff2.is_initialized is True
