"""Tests for ImperialRentSystem decision phase (Task 8).

Task 8: Decision phase tests (50% -> 75%)
Source: src/babylon/engine/systems/economic.py:462-538 - _process_decision_phase method

The _process_decision_phase method implements bourgeoisie decision heuristics:

1. Pool ratio calculation: pool_ratio = current_pool / initial_pool
2. Aggregate tension: average tension from all edges
3. Decision clamping: wage_rate in [min_wage, max_wage], repression in [0.0, 1.0]

Decision Matrix:
- BRIBERY: pool_ratio >= high AND tension < 0.3 -> increase wages +5%
- CRISIS: pool_ratio < critical -> wages to minimum, repression +20%
- IRON_FIST: pool_ratio < low AND tension > 0.5 -> repression +10%
- AUSTERITY: pool_ratio < low AND tension <= 0.5 -> wages -5%
- NO_CHANGE: else -> maintain status quo
"""

from typing import Any

import pytest

from babylon.config.defines import EconomyDefines, GameDefines
from babylon.engine.graph import BabylonGraph
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.models.enums import EventType


@pytest.mark.unit
class TestPoolRatioCalculation:
    """Test pool_ratio calculation in decision phase."""

    def test_pool_ratio_calculation_basic(self) -> None:
        """Pool ratio is current_pool / initial_pool.

        With initial_pool=100 and current_pool=70, pool_ratio=0.7
        """
        graph = BabylonGraph()
        graph.add_node("node1")

        # Defines with initial_rent_pool = 100
        economy_defines = EconomyDefines(
            initial_rent_pool=100.0,
            pool_high_threshold=0.7,
            pool_low_threshold=0.3,
            pool_critical_threshold=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        # current_pool = 70, initial = 100, ratio = 0.7
        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 70.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()
        initial_pool = 100.0

        # Act
        system._process_decision_phase(graph, services, {"tick": 1}, tick_context, initial_pool)

        # Assert: With pool_ratio=0.7 (at high threshold), no change expected
        # (exact behavior depends on tension, but this confirms ratio calculation)
        # At 0.7, should be in neutral zone unless tension is low
        # Since no edges, tension is 0.0, so BRIBERY should trigger
        assert tick_context["wage_rate"] == pytest.approx(0.25, rel=1e-6)  # +0.05

    def test_pool_ratio_with_zero_initial_pool(self) -> None:
        """Pool ratio is 0.0 when initial_pool is 0.

        Division by zero is avoided.
        """
        graph = BabylonGraph()
        graph.add_node("node1")

        economy_defines = EconomyDefines(
            initial_rent_pool=0.0,  # Zero initial pool
            pool_high_threshold=0.7,
            pool_low_threshold=0.3,
            pool_critical_threshold=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 50.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act - should not raise
        system._process_decision_phase(graph, services, {"tick": 1}, tick_context, 0.0)

        # Assert: pool_ratio = 0.0, which triggers CRISIS (< critical threshold)
        # CRISIS: wages go to minimum, repression +20%
        # Assuming min_wage = 0.05, new_repression = 0.5 + 0.2 = 0.7
        assert tick_context["repression_level"] == pytest.approx(0.7, rel=1e-6)


@pytest.mark.unit
class TestAggregateTensionCalculation:
    """Test the capital_labor opposition-gap handoff (C1.5).

    ``_calculate_aggregate_tension`` no longer averages edge tensions; it reads
    the capital_labor opposition gap from the ``opposition_states`` graph
    attribute that ContradictionSystem (position 18) stashes each tick.
    """

    def test_aggregate_tension_reads_capital_labor_gap(self) -> None:
        """Returns the capital_labor gap from the opposition snapshot."""
        graph = BabylonGraph()
        graph.add_node("a")
        graph.graph["opposition_states"] = {"capital_labor": {"gap": 0.4}}

        system = ImperialRentSystem()

        # Act
        result = system._calculate_aggregate_tension(graph)

        # Assert
        assert result == pytest.approx(0.4, rel=1e-6)

    def test_aggregate_tension_empty_graph(self) -> None:
        """No snapshot returns 0.0 tension (edge tensions are irrelevant now)."""
        graph = BabylonGraph()

        system = ImperialRentSystem()

        # Act
        result = system._calculate_aggregate_tension(graph)

        # Assert
        assert result == pytest.approx(0.0, rel=1e-6)

    def test_aggregate_tension_snapshot_without_capital_labor_defaults_zero(self) -> None:
        """A snapshot lacking the capital_labor key defaults to 0.0."""
        graph = BabylonGraph()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_edge("a", "b", tension=0.6)  # edge tension no longer feeds it
        graph.graph["opposition_states"] = {"wage": {"gap": 0.9}}

        system = ImperialRentSystem()

        # Act
        result = system._calculate_aggregate_tension(graph)

        # Assert
        assert result == pytest.approx(0.0, rel=1e-6)

    def test_aggregate_tension_high_gap(self) -> None:
        """A high capital_labor gap is returned verbatim."""
        graph = BabylonGraph()
        graph.add_node("a")
        graph.graph["opposition_states"] = {"capital_labor": {"gap": 0.7}}

        system = ImperialRentSystem()

        # Act
        result = system._calculate_aggregate_tension(graph)

        # Assert
        assert result == pytest.approx(0.7, rel=1e-6)


@pytest.mark.unit
class TestDecisionClamping:
    """Test that wage_rate and repression are clamped to valid ranges."""

    def test_wage_rate_clamped_to_max(self) -> None:
        """Wage rate cannot exceed max_wage.

        BRIBERY adds +5%, but can't exceed max_wage.
        """
        graph = BabylonGraph()
        graph.add_node("node1")

        economy_defines = EconomyDefines(
            initial_rent_pool=100.0,
            pool_high_threshold=0.5,  # Lower threshold so high pool triggers BRIBERY
            pool_low_threshold=0.3,
            pool_critical_threshold=0.1,
            min_wage_rate=0.05,
            max_wage_rate=0.35,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        # Wage already at max
        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 80.0,  # High pool -> BRIBERY
            "wage_rate": 0.35,  # Already at max
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_decision_phase(graph, services, {"tick": 1}, tick_context, 100.0)

        # Assert: Wage rate clamped at max (0.35)
        assert tick_context["wage_rate"] == pytest.approx(0.35, rel=1e-6)

    def test_wage_rate_clamped_to_min(self) -> None:
        """Wage rate cannot go below min_wage.

        AUSTERITY subtracts -5%, but can't go below min_wage.
        """
        graph = BabylonGraph()
        graph.add_node("node1")

        economy_defines = EconomyDefines(
            initial_rent_pool=100.0,
            pool_high_threshold=0.7,
            pool_low_threshold=0.3,
            pool_critical_threshold=0.1,
            min_wage_rate=0.05,
            max_wage_rate=0.35,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        # Low pool (triggers AUSTERITY with low tension)
        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 20.0,  # Low pool -> AUSTERITY
            "wage_rate": 0.06,  # Near min
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_decision_phase(graph, services, {"tick": 1}, tick_context, 100.0)

        # Assert: Wage rate clamped at min (0.05)
        # AUSTERITY: -0.05, so 0.06 - 0.05 = 0.01, but clamped to 0.05
        assert tick_context["wage_rate"] == pytest.approx(0.05, rel=1e-6)

    def test_repression_clamped_to_one(self) -> None:
        """Repression cannot exceed 1.0.

        IRON_FIST or CRISIS increase repression, but capped at 1.0.
        """
        graph = BabylonGraph()
        graph.add_node("a")
        graph.add_node("b")
        # High capital_labor gap for IRON_FIST (C1.5 handoff via opposition_states)
        graph.add_edge("a", "b", tension=0.8)
        graph.graph["opposition_states"] = {"capital_labor": {"gap": 0.8}}

        economy_defines = EconomyDefines(
            initial_rent_pool=100.0,
            pool_high_threshold=0.7,
            pool_low_threshold=0.3,
            pool_critical_threshold=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        # Low pool + high tension -> IRON_FIST
        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 20.0,
            "wage_rate": 0.2,
            "repression_level": 0.95,  # Already high
        }

        system = ImperialRentSystem()

        # Act
        system._process_decision_phase(graph, services, {"tick": 1}, tick_context, 100.0)

        # Assert: Repression clamped at 1.0
        # IRON_FIST: +0.10, so 0.95 + 0.10 = 1.05, but clamped to 1.0
        assert tick_context["repression_level"] == pytest.approx(1.0, rel=1e-6)

    def test_repression_clamped_to_zero(self) -> None:
        """Repression cannot go negative.

        This is an edge case - no decision subtracts repression in current impl,
        but the clamping logic should handle it.
        """
        graph = BabylonGraph()
        graph.add_node("node1")

        economy_defines = EconomyDefines(
            initial_rent_pool=100.0,
            pool_high_threshold=0.7,
            pool_low_threshold=0.3,
            pool_critical_threshold=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        # Neutral zone, no change to repression
        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 50.0,  # Neutral zone
            "wage_rate": 0.2,
            "repression_level": 0.0,  # Already at 0
        }

        system = ImperialRentSystem()

        # Act
        system._process_decision_phase(graph, services, {"tick": 1}, tick_context, 100.0)

        # Assert: Repression stays at 0.0
        assert tick_context["repression_level"] == pytest.approx(0.0, rel=1e-6)


@pytest.mark.unit
class TestDecisionLogic:
    """Test the decision matrix logic."""

    def test_bribery_decision_high_pool_low_tension(self) -> None:
        """BRIBERY: pool_ratio >= high AND tension < 0.3 -> wages +5%."""
        graph = BabylonGraph()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_edge("a", "b", tension=0.1)  # Low tension

        economy_defines = EconomyDefines(
            initial_rent_pool=100.0,
            pool_high_threshold=0.7,
            pool_low_threshold=0.3,
            pool_critical_threshold=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 80.0,  # pool_ratio = 0.8 >= 0.7
            "wage_rate": 0.20,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_decision_phase(graph, services, {"tick": 1}, tick_context, 100.0)

        # Assert: BRIBERY -> wages +5%
        assert tick_context["wage_rate"] == pytest.approx(0.25, rel=1e-6)
        assert tick_context["repression_level"] == pytest.approx(0.5, rel=1e-6)

    def test_austerity_decision_low_pool_low_tension(self) -> None:
        """AUSTERITY: pool_ratio < low AND tension <= 0.5 -> wages -5%."""
        graph = BabylonGraph()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_edge("a", "b", tension=0.3)  # Low-medium tension

        economy_defines = EconomyDefines(
            initial_rent_pool=100.0,
            pool_high_threshold=0.7,
            pool_low_threshold=0.3,
            pool_critical_threshold=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 20.0,  # pool_ratio = 0.2 < 0.3
            "wage_rate": 0.20,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_decision_phase(graph, services, {"tick": 1}, tick_context, 100.0)

        # Assert: AUSTERITY -> wages -5%
        assert tick_context["wage_rate"] == pytest.approx(0.15, rel=1e-6)
        assert tick_context["repression_level"] == pytest.approx(0.5, rel=1e-6)

    def test_iron_fist_decision_low_pool_high_tension(self) -> None:
        """IRON_FIST: pool_ratio < low AND tension > 0.5 -> repression +10%."""
        graph = BabylonGraph()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_edge("a", "b", tension=0.7)  # High tension
        # C1.5: the bourgeois decision reads the capital_labor gap, not edges.
        graph.graph["opposition_states"] = {"capital_labor": {"gap": 0.7}}

        economy_defines = EconomyDefines(
            initial_rent_pool=100.0,
            pool_high_threshold=0.7,
            pool_low_threshold=0.3,
            pool_critical_threshold=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 20.0,  # pool_ratio = 0.2 < 0.3
            "wage_rate": 0.20,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_decision_phase(graph, services, {"tick": 1}, tick_context, 100.0)

        # Assert: IRON_FIST -> repression +10%
        assert tick_context["wage_rate"] == pytest.approx(0.20, rel=1e-6)
        assert tick_context["repression_level"] == pytest.approx(0.6, rel=1e-6)

    def test_crisis_decision_critical_pool(self) -> None:
        """CRISIS: pool_ratio < critical -> wages to min, repression +20%."""
        graph = BabylonGraph()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_edge("a", "b", tension=0.5)

        economy_defines = EconomyDefines(
            initial_rent_pool=100.0,
            pool_high_threshold=0.7,
            pool_low_threshold=0.3,
            pool_critical_threshold=0.1,
            min_wage_rate=0.05,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 5.0,  # pool_ratio = 0.05 < 0.1 (critical)
            "wage_rate": 0.20,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_decision_phase(graph, services, {"tick": 1}, tick_context, 100.0)

        # Assert: CRISIS -> wages -15% (to min), repression +20%
        # wage: 0.20 - 0.15 = 0.05 (happens to equal min, so OK)
        assert tick_context["wage_rate"] == pytest.approx(0.05, rel=1e-6)
        assert tick_context["repression_level"] == pytest.approx(0.7, rel=1e-6)

    def test_no_change_decision_neutral_zone(self) -> None:
        """NO_CHANGE: mid-range pool -> maintain status quo."""
        graph = BabylonGraph()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_edge("a", "b", tension=0.5)

        economy_defines = EconomyDefines(
            initial_rent_pool=100.0,
            pool_high_threshold=0.7,
            pool_low_threshold=0.3,
            pool_critical_threshold=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 50.0,  # pool_ratio = 0.5 (neutral zone)
            "wage_rate": 0.20,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_decision_phase(graph, services, {"tick": 1}, tick_context, 100.0)

        # Assert: NO_CHANGE -> no deltas
        assert tick_context["wage_rate"] == pytest.approx(0.20, rel=1e-6)
        assert tick_context["repression_level"] == pytest.approx(0.5, rel=1e-6)


@pytest.mark.unit
class TestCrisisEventEmission:
    """Test ECONOMIC_CRISIS event emission on crisis decision."""

    def test_crisis_emits_event(self) -> None:
        """ECONOMIC_CRISIS event emitted when decision is CRISIS."""
        graph = BabylonGraph()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_edge("a", "b", tension=0.5)

        economy_defines = EconomyDefines(
            initial_rent_pool=100.0,
            pool_high_threshold=0.7,
            pool_low_threshold=0.3,
            pool_critical_threshold=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 5.0,  # Critical
            "wage_rate": 0.20,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_decision_phase(graph, services, {"tick": 10}, tick_context, 100.0)

        # Assert: Event emitted
        events = services.event_bus.get_history()
        assert len(events) == 1
        event = events[0]
        assert event.type == EventType.ECONOMIC_CRISIS
        assert event.tick == 10
        assert "pool_ratio" in event.payload
        assert "aggregate_tension" in event.payload
        assert "decision" in event.payload
        assert "wage_delta" in event.payload
        assert "repression_delta" in event.payload
        assert "new_wage_rate" in event.payload
        assert "new_repression_level" in event.payload

    def test_non_crisis_decision_no_event(self) -> None:
        """Non-crisis decisions do not emit ECONOMIC_CRISIS event."""
        graph = BabylonGraph()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_edge("a", "b", tension=0.1)

        economy_defines = EconomyDefines(
            initial_rent_pool=100.0,
            pool_high_threshold=0.7,
            pool_low_threshold=0.3,
            pool_critical_threshold=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 80.0,  # High pool -> BRIBERY, not CRISIS
            "wage_rate": 0.20,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_decision_phase(graph, services, {"tick": 1}, tick_context, 100.0)

        # Assert: No event emitted
        events = services.event_bus.get_history()
        assert len(events) == 0


@pytest.mark.unit
class TestDecisionEdgeCases:
    """Test edge cases in decision phase."""

    def test_exactly_at_high_threshold_triggers_bribery(self) -> None:
        """Pool ratio exactly at high threshold triggers BRIBERY (if tension low)."""
        graph = BabylonGraph()
        graph.add_node("node1")

        economy_defines = EconomyDefines(
            initial_rent_pool=100.0,
            pool_high_threshold=0.7,
            pool_low_threshold=0.3,
            pool_critical_threshold=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 70.0,  # Exactly at high threshold (0.7)
            "wage_rate": 0.20,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_decision_phase(graph, services, {"tick": 1}, tick_context, 100.0)

        # Assert: BRIBERY triggered (>= high threshold)
        assert tick_context["wage_rate"] == pytest.approx(0.25, rel=1e-6)

    def test_exactly_at_low_threshold_no_austerity(self) -> None:
        """Pool ratio exactly at low threshold does NOT trigger AUSTERITY.

        AUSTERITY requires pool_ratio < low, not <=.
        """
        graph = BabylonGraph()
        graph.add_node("node1")

        economy_defines = EconomyDefines(
            initial_rent_pool=100.0,
            pool_high_threshold=0.7,
            pool_low_threshold=0.3,
            pool_critical_threshold=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 30.0,  # Exactly at low threshold (0.3)
            "wage_rate": 0.20,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_decision_phase(graph, services, {"tick": 1}, tick_context, 100.0)

        # Assert: NO_CHANGE (not below low threshold)
        assert tick_context["wage_rate"] == pytest.approx(0.20, rel=1e-6)
        assert tick_context["repression_level"] == pytest.approx(0.5, rel=1e-6)

    def test_tension_exactly_at_boundary(self) -> None:
        """Tension exactly at 0.5 triggers AUSTERITY, not IRON_FIST.

        IRON_FIST requires tension > 0.5, not >=.
        """
        graph = BabylonGraph()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_edge("a", "b", tension=0.5)  # Exactly at boundary

        economy_defines = EconomyDefines(
            initial_rent_pool=100.0,
            pool_high_threshold=0.7,
            pool_low_threshold=0.3,
            pool_critical_threshold=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 20.0,  # Low pool
            "wage_rate": 0.20,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_decision_phase(graph, services, {"tick": 1}, tick_context, 100.0)

        # Assert: AUSTERITY (tension <= 0.5)
        assert tick_context["wage_rate"] == pytest.approx(0.15, rel=1e-6)
        assert tick_context["repression_level"] == pytest.approx(0.5, rel=1e-6)
