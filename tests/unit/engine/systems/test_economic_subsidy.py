"""Tests for ImperialRentSystem subsidy phase (Task 7).

Task 7: Subsidy phase tests (51.4% -> 80%)
Source: src/babylon/engine/systems/economic.py:337-461 - _process_subsidy_phase method

The _process_subsidy_phase method implements "The Iron Lung" - imperial subsidies
to client states when they become unstable. This tests:

1. Subsidy trigger logic (stability_ratio calculation):
   - When p_acquiescence > 0: stability_ratio = p_revolution / p_acquiescence
   - When p_acquiescence = 0 AND p_revolution > 0: stability_ratio = 1.0 (crisis)
   - When p_acquiescence = 0 AND p_revolution = 0: stability_ratio = 0.0

2. Subsidy amount calculation:
   - max_subsidy = min(subsidy_cap, tribute_inflow * conversion_rate)
   - Capped at source_wealth
   - Capped at available_pool

3. Repression boost application:
   - new_repression = min(1.0, target_repression + repression_boost)
   - Verify repression never exceeds 1.0
"""

from typing import Any

import networkx as nx
import pytest

from babylon.config.defines import EconomyDefines, GameDefines, SurvivalDefines
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.models.enums import EdgeType, EventType


@pytest.mark.unit
class TestSubsidyTriggerLogic:
    """Test the stability_ratio calculation that triggers subsidies.

    Subsidy triggers when P(S|R) >= threshold * P(S|A), i.e., when
    stability_ratio = p_revolution / p_acquiescence >= subsidy_trigger_threshold.
    """

    def test_stable_client_no_subsidy_triggered(self) -> None:
        """Client state with low stability_ratio receives no subsidy.

        When p_revolution is low relative to p_acquiescence, the client
        state is stable and doesn't need imperial intervention.
        """
        # Arrange: Graph with CLIENT_STATE edge
        graph: nx.DiGraph[str] = nx.DiGraph()

        # Source: Core bourgeoisie with wealth to spend
        graph.add_node(
            "core_bourgeoisie",
            wealth=10.0,
        )

        # Target: Stable client state (high wealth = high P(S|A), low org = low P(S|R))
        graph.add_node(
            "client_state",
            wealth=1.0,  # High wealth -> high P(S|A) via sigmoid
            organization=0.05,  # Low org -> low P(S|R)
            repression_faced=0.5,  # Moderate repression
            subsistence_threshold=0.3,
        )

        # CLIENT_STATE edge with subsidy cap
        graph.add_edge(
            "core_bourgeoisie",
            "client_state",
            edge_type=EdgeType.CLIENT_STATE,
            subsidy_cap=5.0,
        )

        # High threshold so subsidy doesn't trigger easily
        economy_defines = EconomyDefines(
            subsidy_trigger_threshold=0.9,  # Require near-crisis to trigger
            subsidy_conversion_rate=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 5.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 50.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()
        initial_source_wealth = graph.nodes["core_bourgeoisie"]["wealth"]
        initial_target_repression = graph.nodes["client_state"]["repression_faced"]

        # Act
        system._process_subsidy_phase(graph, services, {"tick": 1}, tick_context)

        # Assert: No subsidy should have been sent
        # Source wealth unchanged
        assert graph.nodes["core_bourgeoisie"]["wealth"] == pytest.approx(
            initial_source_wealth, rel=1e-6
        )
        # Target repression unchanged
        assert graph.nodes["client_state"]["repression_faced"] == pytest.approx(
            initial_target_repression, rel=1e-6
        )
        # No subsidy outflow
        assert tick_context["subsidy_outflow"] == pytest.approx(0.0, abs=0.01)

    def test_unstable_client_triggers_subsidy(self) -> None:
        """Client state with high stability_ratio triggers subsidy.

        When p_revolution is high relative to p_acquiescence (revolution
        becomes a rational survival strategy), the core provides a subsidy.
        """
        # Arrange: Graph with CLIENT_STATE edge
        graph: nx.DiGraph[str] = nx.DiGraph()

        # Source: Core bourgeoisie with wealth
        graph.add_node(
            "core_bourgeoisie",
            wealth=10.0,
        )

        # Target: Unstable client state (low wealth = low P(S|A), high org = high P(S|R))
        graph.add_node(
            "client_state",
            wealth=0.0,  # Zero wealth -> very low P(S|A)
            organization=0.8,  # High org -> high P(S|R)
            repression_faced=0.2,  # Low repression -> high P(S|R) = 0.8/0.2 = 4.0
            subsistence_threshold=0.3,
        )

        graph.add_edge(
            "core_bourgeoisie",
            "client_state",
            edge_type=EdgeType.CLIENT_STATE,
            subsidy_cap=5.0,
        )

        # Low threshold so subsidy triggers
        economy_defines = EconomyDefines(
            subsidy_trigger_threshold=0.5,
            subsidy_conversion_rate=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 5.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 50.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()
        initial_source_wealth = graph.nodes["core_bourgeoisie"]["wealth"]
        initial_target_repression = graph.nodes["client_state"]["repression_faced"]

        # Act
        system._process_subsidy_phase(graph, services, {"tick": 1}, tick_context)

        # Assert: Subsidy should have been sent
        # Source wealth decreased
        assert graph.nodes["core_bourgeoisie"]["wealth"] < initial_source_wealth
        # Target repression increased
        assert graph.nodes["client_state"]["repression_faced"] > initial_target_repression
        # Subsidy outflow recorded
        assert tick_context["subsidy_outflow"] > 0.0

    def test_zero_acquiescence_with_revolution_triggers_crisis_subsidy(self) -> None:
        """When p_acquiescence=0 and p_revolution>0, stability_ratio=1.0 (crisis).

        This is the edge case where acquiescence through compliance is
        impossible (zero wealth), but revolutionary capacity exists.
        The stability_ratio should be 1.0, triggering subsidy.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node("core_bourgeoisie", wealth=10.0)

        # Client with zero wealth and high steepness_k ensures P(S|A) is essentially 0
        # Very high organization ensures P(S|R) > 0
        graph.add_node(
            "client_state",
            wealth=-10.0,  # Far below subsistence -> P(S|A) approaches 0
            organization=0.9,
            repression_faced=0.1,
            subsistence_threshold=0.5,
        )

        graph.add_edge(
            "core_bourgeoisie",
            "client_state",
            edge_type=EdgeType.CLIENT_STATE,
            subsidy_cap=5.0,
        )

        # Threshold below 1.0 so crisis triggers subsidy
        economy_defines = EconomyDefines(
            subsidy_trigger_threshold=0.8,
            subsidy_conversion_rate=0.1,
        )
        # High steepness ensures sigmoid is near 0 for negative wealth
        survival_defines = SurvivalDefines(
            steepness_k=20.0,  # High steepness
        )
        defines = GameDefines(economy=economy_defines, survival=survival_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 5.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 50.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()
        initial_source_wealth = graph.nodes["core_bourgeoisie"]["wealth"]

        # Act
        system._process_subsidy_phase(graph, services, {"tick": 1}, tick_context)

        # Assert: Crisis subsidy should have been sent
        assert graph.nodes["core_bourgeoisie"]["wealth"] < initial_source_wealth
        assert tick_context["subsidy_outflow"] > 0.0

    def test_zero_acquiescence_zero_revolution_no_subsidy(self) -> None:
        """When p_acquiescence=0 and p_revolution=0, stability_ratio=0.0.

        This is the edge case where both survival strategies are impossible.
        No subsidy is needed because there's no revolutionary threat.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node("core_bourgeoisie", wealth=10.0)

        # Client with zero wealth (P(S|A) ~ 0) and zero organization (P(S|R) = 0)
        graph.add_node(
            "client_state",
            wealth=-10.0,  # Far below subsistence
            organization=0.0,  # Zero org -> P(S|R) = 0
            repression_faced=0.5,
            subsistence_threshold=0.5,
        )

        graph.add_edge(
            "core_bourgeoisie",
            "client_state",
            edge_type=EdgeType.CLIENT_STATE,
            subsidy_cap=5.0,
        )

        economy_defines = EconomyDefines(
            subsidy_trigger_threshold=0.1,  # Even low threshold
            subsidy_conversion_rate=0.1,
        )
        survival_defines = SurvivalDefines(
            steepness_k=20.0,
        )
        defines = GameDefines(economy=economy_defines, survival=survival_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 5.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 50.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()
        initial_source_wealth = graph.nodes["core_bourgeoisie"]["wealth"]

        # Act
        system._process_subsidy_phase(graph, services, {"tick": 1}, tick_context)

        # Assert: No subsidy because stability_ratio = 0 < threshold
        assert graph.nodes["core_bourgeoisie"]["wealth"] == pytest.approx(
            initial_source_wealth, rel=1e-6
        )
        assert tick_context["subsidy_outflow"] == pytest.approx(0.0, abs=0.01)


@pytest.mark.unit
class TestSubsidyAmountCalculation:
    """Test subsidy amount calculation and capping logic."""

    def test_subsidy_capped_at_subsidy_cap(self) -> None:
        """Subsidy cannot exceed the subsidy_cap on the edge.

        max_subsidy = min(subsidy_cap, tribute_inflow * conversion_rate)
        """
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node("core_bourgeoisie", wealth=100.0)
        graph.add_node(
            "client_state",
            wealth=0.0,
            organization=0.9,
            repression_faced=0.1,
            subsistence_threshold=0.3,
        )

        # Very low subsidy cap
        graph.add_edge(
            "core_bourgeoisie",
            "client_state",
            edge_type=EdgeType.CLIENT_STATE,
            subsidy_cap=0.5,  # Cap at 0.5
        )

        economy_defines = EconomyDefines(
            subsidy_trigger_threshold=0.1,
            subsidy_conversion_rate=0.5,  # High rate would give 50.0 * 0.5 = 25
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 50.0,  # Large inflow
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 100.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_subsidy_phase(graph, services, {"tick": 1}, tick_context)

        # Assert: Subsidy capped at 0.5 (subsidy_cap)
        assert tick_context["subsidy_outflow"] == pytest.approx(0.5, rel=1e-6)

    def test_subsidy_capped_at_source_wealth(self) -> None:
        """Subsidy cannot exceed source (bourgeoisie) wealth.

        Even if subsidy_cap is high, can't spend more than you have.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node("core_bourgeoisie", wealth=0.3)  # Low wealth
        graph.add_node(
            "client_state",
            wealth=0.0,
            organization=0.9,
            repression_faced=0.1,
            subsistence_threshold=0.3,
        )

        graph.add_edge(
            "core_bourgeoisie",
            "client_state",
            edge_type=EdgeType.CLIENT_STATE,
            subsidy_cap=10.0,  # High cap
        )

        economy_defines = EconomyDefines(
            subsidy_trigger_threshold=0.1,
            subsidy_conversion_rate=0.5,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 50.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 100.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_subsidy_phase(graph, services, {"tick": 1}, tick_context)

        # Assert: Subsidy capped at source wealth (0.3)
        assert tick_context["subsidy_outflow"] == pytest.approx(0.3, rel=1e-6)
        # Source wealth should be zero after subsidy
        assert graph.nodes["core_bourgeoisie"]["wealth"] == pytest.approx(0.0, rel=1e-6)

    def test_subsidy_capped_at_available_pool(self) -> None:
        """Subsidy cannot exceed available pool.

        Sprint 3.4.4: Pool tracking means subsidy is limited by current_pool.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node("core_bourgeoisie", wealth=100.0)  # High wealth
        graph.add_node(
            "client_state",
            wealth=0.0,
            organization=0.9,
            repression_faced=0.1,
            subsistence_threshold=0.3,
        )

        graph.add_edge(
            "core_bourgeoisie",
            "client_state",
            edge_type=EdgeType.CLIENT_STATE,
            subsidy_cap=50.0,  # High cap
        )

        economy_defines = EconomyDefines(
            subsidy_trigger_threshold=0.1,
            subsidy_conversion_rate=0.5,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 50.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 0.2,  # Very low pool
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_subsidy_phase(graph, services, {"tick": 1}, tick_context)

        # Assert: Subsidy capped at available pool (0.2)
        assert tick_context["subsidy_outflow"] == pytest.approx(0.2, rel=1e-6)
        assert tick_context["current_pool"] == pytest.approx(0.0, rel=1e-6)

    def test_negligible_subsidy_skipped(self) -> None:
        """Subsidies <= 0.01 are considered negligible and skipped.

        Floating point noise should not trigger subsidy events.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node("core_bourgeoisie", wealth=100.0)
        graph.add_node(
            "client_state",
            wealth=0.0,
            organization=0.9,
            repression_faced=0.1,
            subsistence_threshold=0.3,
        )

        graph.add_edge(
            "core_bourgeoisie",
            "client_state",
            edge_type=EdgeType.CLIENT_STATE,
            subsidy_cap=0.005,  # Negligible cap
        )

        economy_defines = EconomyDefines(
            subsidy_trigger_threshold=0.1,
            subsidy_conversion_rate=0.5,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.01,  # Small inflow
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 100.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()
        initial_wealth = graph.nodes["core_bourgeoisie"]["wealth"]

        # Act
        system._process_subsidy_phase(graph, services, {"tick": 1}, tick_context)

        # Assert: No subsidy (negligible amount)
        assert graph.nodes["core_bourgeoisie"]["wealth"] == pytest.approx(initial_wealth, rel=1e-6)
        assert tick_context["subsidy_outflow"] == pytest.approx(0.0, abs=0.01)


@pytest.mark.unit
class TestRepressionBoostApplication:
    """Test that repression boost is correctly applied and capped."""

    def test_repression_boost_applied(self) -> None:
        """Subsidy converts to repression boost on target.

        repression_boost = max_subsidy * subsidy_conversion_rate
        new_repression = target_repression + repression_boost
        """
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node("core_bourgeoisie", wealth=100.0)
        graph.add_node(
            "client_state",
            wealth=0.0,
            organization=0.9,
            repression_faced=0.2,  # Starting repression
            subsistence_threshold=0.3,
        )

        graph.add_edge(
            "core_bourgeoisie",
            "client_state",
            edge_type=EdgeType.CLIENT_STATE,
            subsidy_cap=10.0,
        )

        # Conversion rate 0.1 -> subsidy of 1.0 gives 0.1 repression boost
        economy_defines = EconomyDefines(
            subsidy_trigger_threshold=0.1,
            subsidy_conversion_rate=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 50.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 100.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_subsidy_phase(graph, services, {"tick": 1}, tick_context)

        # Assert: Repression increased
        # max_subsidy = min(10.0, 50.0 * 0.1) = 5.0
        # repression_boost = 5.0 * 0.1 = 0.5
        # new_repression = 0.2 + 0.5 = 0.7
        assert graph.nodes["client_state"]["repression_faced"] == pytest.approx(0.7, rel=1e-6)

    def test_repression_capped_at_one(self) -> None:
        """Repression cannot exceed 1.0 even with large subsidies.

        new_repression = min(1.0, target_repression + repression_boost)
        """
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node("core_bourgeoisie", wealth=100.0)
        graph.add_node(
            "client_state",
            wealth=0.0,
            organization=0.9,
            repression_faced=0.8,  # Already high repression
            subsistence_threshold=0.3,
        )

        graph.add_edge(
            "core_bourgeoisie",
            "client_state",
            edge_type=EdgeType.CLIENT_STATE,
            subsidy_cap=50.0,  # Large cap
        )

        # High conversion rate for large boost
        economy_defines = EconomyDefines(
            subsidy_trigger_threshold=0.1,
            subsidy_conversion_rate=0.5,  # 50% conversion
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 50.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 100.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_subsidy_phase(graph, services, {"tick": 1}, tick_context)

        # Assert: Repression capped at 1.0
        # max_subsidy = min(50.0, 50.0 * 0.5) = 25.0
        # repression_boost = 25.0 * 0.5 = 12.5
        # new_repression = min(1.0, 0.8 + 12.5) = 1.0
        assert graph.nodes["client_state"]["repression_faced"] == pytest.approx(1.0, rel=1e-6)


@pytest.mark.unit
class TestSubsidyEventEmission:
    """Test that IMPERIAL_SUBSIDY events are correctly emitted."""

    def test_subsidy_emits_event(self) -> None:
        """IMPERIAL_SUBSIDY event emitted when subsidy is sent."""
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node("core_bourgeoisie", wealth=100.0)
        graph.add_node(
            "client_state",
            wealth=0.0,
            organization=0.9,
            repression_faced=0.2,
            subsistence_threshold=0.3,
        )

        graph.add_edge(
            "core_bourgeoisie",
            "client_state",
            edge_type=EdgeType.CLIENT_STATE,
            subsidy_cap=10.0,
        )

        economy_defines = EconomyDefines(
            subsidy_trigger_threshold=0.1,
            subsidy_conversion_rate=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 50.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 100.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_subsidy_phase(graph, services, {"tick": 5}, tick_context)

        # Assert: Event emitted
        events = services.event_bus.get_history()
        assert len(events) == 1
        event = events[0]
        assert event.type == EventType.IMPERIAL_SUBSIDY
        assert event.tick == 5
        assert event.payload["source_id"] == "core_bourgeoisie"
        assert event.payload["target_id"] == "client_state"
        assert event.payload["amount"] > 0
        assert event.payload["repression_boost"] > 0
        assert event.payload["mechanism"] == "client_state_subsidy"
        assert "stability_ratio" in event.payload


@pytest.mark.unit
class TestSubsidyEdgeCases:
    """Test edge cases in subsidy phase processing."""

    def test_non_client_state_edges_ignored(self) -> None:
        """Only CLIENT_STATE edges trigger subsidy logic."""
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node("core_bourgeoisie", wealth=100.0)
        graph.add_node(
            "other_entity",
            wealth=0.0,
            organization=0.9,
            repression_faced=0.2,
            subsistence_threshold=0.3,
        )

        # EXPLOITATION edge, not CLIENT_STATE
        graph.add_edge(
            "core_bourgeoisie",
            "other_entity",
            edge_type=EdgeType.EXPLOITATION,
            subsidy_cap=10.0,
        )

        economy_defines = EconomyDefines(
            subsidy_trigger_threshold=0.1,
            subsidy_conversion_rate=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 50.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 100.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()
        initial_wealth = graph.nodes["core_bourgeoisie"]["wealth"]

        # Act
        system._process_subsidy_phase(graph, services, {"tick": 1}, tick_context)

        # Assert: No subsidy processed
        assert graph.nodes["core_bourgeoisie"]["wealth"] == pytest.approx(initial_wealth, rel=1e-6)
        assert tick_context["subsidy_outflow"] == pytest.approx(0.0, abs=0.01)

    def test_string_edge_type_converted(self) -> None:
        """String edge_type is converted to EdgeType enum."""
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node("core_bourgeoisie", wealth=100.0)
        graph.add_node(
            "client_state",
            wealth=0.0,
            organization=0.9,
            repression_faced=0.2,
            subsistence_threshold=0.3,
        )

        # String edge type (from serialization)
        graph.add_edge(
            "core_bourgeoisie",
            "client_state",
            edge_type="client_state",  # String, not enum
            subsidy_cap=10.0,
        )

        economy_defines = EconomyDefines(
            subsidy_trigger_threshold=0.1,
            subsidy_conversion_rate=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 50.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 100.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_subsidy_phase(graph, services, {"tick": 1}, tick_context)

        # Assert: Subsidy processed (string was converted)
        assert tick_context["subsidy_outflow"] > 0.0

    def test_missing_subsidy_cap_defaults_to_zero(self) -> None:
        """Missing subsidy_cap on edge defaults to 0.0, meaning no subsidy."""
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node("core_bourgeoisie", wealth=100.0)
        graph.add_node(
            "client_state",
            wealth=0.0,
            organization=0.9,
            repression_faced=0.2,
            subsistence_threshold=0.3,
        )

        # No subsidy_cap on edge
        graph.add_edge(
            "core_bourgeoisie",
            "client_state",
            edge_type=EdgeType.CLIENT_STATE,
            # No subsidy_cap
        )

        economy_defines = EconomyDefines(
            subsidy_trigger_threshold=0.1,
            subsidy_conversion_rate=0.1,
        )
        defines = GameDefines(economy=economy_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 50.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 100.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_subsidy_phase(graph, services, {"tick": 1}, tick_context)

        # Assert: No subsidy (cap defaults to 0.0)
        assert tick_context["subsidy_outflow"] == pytest.approx(0.0, abs=0.01)

    def test_missing_node_attributes_use_defaults(self) -> None:
        """Missing node attributes use defines defaults."""
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node("core_bourgeoisie", wealth=100.0)
        # Target with minimal attributes
        graph.add_node(
            "client_state",
            wealth=0.0,
            # Missing: organization, repression_faced, subsistence_threshold
        )

        graph.add_edge(
            "core_bourgeoisie",
            "client_state",
            edge_type=EdgeType.CLIENT_STATE,
            subsidy_cap=10.0,
        )

        economy_defines = EconomyDefines(
            subsidy_trigger_threshold=0.1,
            subsidy_conversion_rate=0.1,
        )
        # Set specific defaults
        survival_defines = SurvivalDefines(
            default_organization=0.5,
            default_repression=0.3,
            default_subsistence=0.2,
        )
        defines = GameDefines(economy=economy_defines, survival=survival_defines)
        services = ServiceContainer.create(defines=defines)

        tick_context: dict[str, Any] = {
            "tribute_inflow": 50.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 100.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act - should not raise, uses defaults
        system._process_subsidy_phase(graph, services, {"tick": 1}, tick_context)

        # Assert: Method ran without error, defaults were used
        # With default org=0.5, repression=0.3, P(S|R) = 0.5/0.3 ~ 1.67
        # With wealth=0, P(S|A) is low, so stability_ratio is high -> triggers subsidy
        assert tick_context["subsidy_outflow"] > 0.0
