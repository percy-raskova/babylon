"""Tests for default value handling in economic and survival systems (Task 9).

Task 9: Default value tests
Files: economic.py, survival.py

Tests verifying that `.get()` fallback values are used correctly when
node/edge attributes are missing:
- Missing wealth defaults to 0.0
- Missing subsistence_threshold uses defines default
- Missing tension defaults to 0.0
- Missing organization uses defines default
- Missing repression_faced uses defines default
"""

from typing import Any

import networkx as nx
import pytest

from babylon.config.defines import (
    EconomyDefines,
    GameDefines,
    SurvivalDefines,
    TensionDefines,
)
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.contradiction import ContradictionSystem
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.engine.systems.survival import SurvivalSystem
from babylon.models.enums import EdgeType


@pytest.mark.unit
class TestMissingWealthDefaultsToZero:
    """Test that missing wealth attribute defaults to 0.0."""

    def test_extraction_missing_worker_wealth_defaults_zero(self) -> None:
        """Worker node without wealth attribute uses 0.0 default.

        Imperial rent extraction: rent = alpha * wealth * (1 - consciousness)
        With wealth=0, rent=0 regardless of other parameters.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()

        # Worker WITHOUT wealth attribute
        graph.add_node("worker", ideology={"class_consciousness": 0.2})
        graph.add_node("owner", wealth=10.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)

        services = ServiceContainer.create()

        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 100.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()
        initial_owner_wealth = graph.nodes["owner"]["wealth"]

        # Act
        system._process_extraction_phase(graph, services, {"tick": 1}, tick_context)

        # Assert: No rent extracted (worker wealth defaulted to 0)
        # Owner wealth unchanged
        assert graph.nodes["owner"]["wealth"] == pytest.approx(initial_owner_wealth, rel=1e-6)
        # No events emitted (rent < 0.01 threshold)
        events = services.event_bus.get_history()
        assert len(events) == 0

    def test_survival_missing_wealth_defaults_zero(self) -> None:
        """Node without wealth attribute uses 0.0 for P(S|A) calculation.

        P(S|A) with wealth=0 and subsistence=0.3 should be low.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()

        # Node WITHOUT wealth attribute
        graph.add_node(
            "worker",
            organization=0.5,
            repression_faced=0.3,
            subsistence_threshold=0.3,
        )

        services = ServiceContainer.create()
        system = SurvivalSystem()

        # Act
        system.step(graph, services, {"tick": 1})

        # Assert: p_acquiescence should be calculated using wealth=0
        # Sigmoid at (0.0 - 0.3) * k should give low P(S|A)
        # With default steepness_k=10, exp(-10 * (0 - 0.3)) = exp(3) ~ 20
        # P(S|A) = 1 / (1 + 20) ~ 0.047
        assert "p_acquiescence" in graph.nodes["worker"]
        assert graph.nodes["worker"]["p_acquiescence"] < 0.1  # Low probability

    def test_contradiction_missing_wealth_defaults_zero(self) -> None:
        """Nodes without wealth attribute use 0.0 in wealth gap calculation."""
        graph: nx.DiGraph[str] = nx.DiGraph()

        # Source WITHOUT wealth
        graph.add_node("worker")
        # Target with wealth
        graph.add_node("owner", wealth=10.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION, tension=0.0)

        services = ServiceContainer.create()
        system = ContradictionSystem()

        # Act
        system.step(graph, services, {"tick": 1})

        # Assert: Tension should be calculated based on wealth gap
        # gap = |0.0 - 10.0| = 10.0, normalized and added to tension
        # (Exact calculation depends on accumulation rate and normalization)
        assert "tension" in graph.edges["worker", "owner"]


@pytest.mark.unit
class TestMissingSubsistenceUsesDefinesDefault:
    """Test that missing subsistence_threshold uses defines.survival.default_subsistence."""

    def test_survival_missing_subsistence_uses_default(self) -> None:
        """Node without subsistence_threshold uses defines default.

        With default_subsistence=0.3, a node with wealth=0.3 should have
        P(S|A) ~ 0.5 (at the threshold).
        """
        graph: nx.DiGraph[str] = nx.DiGraph()

        # Node WITHOUT subsistence_threshold
        graph.add_node(
            "worker",
            wealth=0.3,  # At default subsistence threshold
            organization=0.5,
            repression_faced=0.5,
            # No subsistence_threshold - should use default
        )

        # Custom defines with specific default_subsistence
        survival_defines = SurvivalDefines(
            default_subsistence=0.3,
            steepness_k=10.0,
        )
        defines = GameDefines(survival=survival_defines)
        services = ServiceContainer.create(defines=defines)
        system = SurvivalSystem()

        # Act
        system.step(graph, services, {"tick": 1})

        # Assert: P(S|A) should be ~0.5 (at threshold)
        assert "p_acquiescence" in graph.nodes["worker"]
        assert graph.nodes["worker"]["p_acquiescence"] == pytest.approx(0.5, rel=0.01)

    def test_subsidy_missing_subsistence_uses_default(self) -> None:
        """Client state without subsistence_threshold uses defines default.

        The P(S|A) calculation in subsidy phase should use the default.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node("core_bourgeoisie", wealth=100.0)
        graph.add_node(
            "client_state",
            wealth=0.3,  # At subsistence
            organization=0.5,
            repression_faced=0.5,
            # No subsistence_threshold
        )

        graph.add_edge(
            "core_bourgeoisie",
            "client_state",
            edge_type=EdgeType.CLIENT_STATE,
            subsidy_cap=10.0,
        )

        economy_defines = EconomyDefines(
            subsidy_trigger_threshold=0.5,
            subsidy_conversion_rate=0.1,
        )
        survival_defines = SurvivalDefines(
            default_subsistence=0.3,
            steepness_k=10.0,
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

        # Act - should not raise, uses default subsistence
        system._process_subsidy_phase(graph, services, {"tick": 1}, tick_context)

        # Assert: Method ran without error
        # At wealth=subsistence, P(S|A)~0.5, with org=0.5, repression=0.5,
        # P(S|R) = 0.5/0.5 = 1.0, ratio = 1.0/0.5 = 2.0 > threshold
        # So subsidy should trigger
        assert tick_context["subsidy_outflow"] > 0.0


@pytest.mark.unit
class TestMissingTensionDefaultsToZero:
    """Test that missing tension attribute defaults to 0.0."""

    def test_aggregate_tension_missing_attribute_defaults_zero(self) -> None:
        """Edges without tension attribute default to 0.0 in aggregate calculation."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_node("c")

        # One edge WITH tension, one WITHOUT
        graph.add_edge("a", "b", tension=0.6)
        graph.add_edge("b", "c")  # No tension attribute

        system = ImperialRentSystem()

        # Act
        result = system._calculate_aggregate_tension(graph)

        # Assert: mean([0.6, 0.0]) = 0.3
        assert result == pytest.approx(0.3, rel=1e-6)

    def test_contradiction_missing_tension_starts_at_zero(self) -> None:
        """Edge without tension attribute starts accumulation from 0.0."""
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node("worker", wealth=0.0)
        graph.add_node("owner", wealth=10.0)
        # Edge WITHOUT tension attribute
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)

        tension_defines = TensionDefines(accumulation_rate=0.05)
        defines = GameDefines(tension=tension_defines)
        services = ServiceContainer.create(defines=defines)
        system = ContradictionSystem()

        # Act
        system.step(graph, services, {"tick": 1})

        # Assert: Tension accumulated from 0.0
        assert "tension" in graph.edges["worker", "owner"]
        # Starting from 0, with wealth gap 10, some tension should accumulate
        assert graph.edges["worker", "owner"]["tension"] >= 0.0


@pytest.mark.unit
class TestMissingOrganizationUsesDefault:
    """Test that missing organization attribute uses defines default."""

    def test_survival_missing_organization_uses_default(self) -> None:
        """Node without organization uses defines.DEFAULT_ORGANIZATION.

        P(S|R) = organization / repression
        """
        graph: nx.DiGraph[str] = nx.DiGraph()

        # Node WITHOUT organization
        graph.add_node(
            "worker",
            wealth=0.5,
            # No organization
            repression_faced=0.5,
            subsistence_threshold=0.3,
        )

        # Custom defines with specific default
        survival_defines = SurvivalDefines(
            default_organization=0.2,
            default_repression=0.5,
        )
        defines = GameDefines(survival=survival_defines)
        services = ServiceContainer.create(defines=defines)
        system = SurvivalSystem()

        # Act
        system.step(graph, services, {"tick": 1})

        # Assert: P(S|R) should use default organization
        # P(S|R) = 0.2 / 0.5 = 0.4
        assert "p_revolution" in graph.nodes["worker"]
        assert graph.nodes["worker"]["p_revolution"] == pytest.approx(0.4, rel=0.01)


@pytest.mark.unit
class TestMissingRepressionUsesDefault:
    """Test that missing repression_faced attribute uses defines default."""

    def test_survival_missing_repression_uses_default(self) -> None:
        """Node without repression_faced uses defines.DEFAULT_REPRESSION_FACED.

        P(S|R) = organization / repression
        """
        graph: nx.DiGraph[str] = nx.DiGraph()

        # Node WITHOUT repression_faced
        graph.add_node(
            "worker",
            wealth=0.5,
            organization=0.4,
            # No repression_faced
            subsistence_threshold=0.3,
        )

        # Custom defines with specific default
        survival_defines = SurvivalDefines(
            default_organization=0.1,
            default_repression=0.4,
        )
        defines = GameDefines(survival=survival_defines)
        services = ServiceContainer.create(defines=defines)
        system = SurvivalSystem()

        # Act
        system.step(graph, services, {"tick": 1})

        # Assert: P(S|R) should use default repression
        # With org=0.4 (specified), repression=0.4 (default), P(S|R) = 0.4/0.4 = 1.0
        assert "p_revolution" in graph.nodes["worker"]
        assert graph.nodes["worker"]["p_revolution"] == pytest.approx(1.0, rel=0.01)

    def test_subsidy_missing_repression_uses_default(self) -> None:
        """Client state without repression_faced uses defines default.

        P(S|R) calculation in subsidy phase should use the default.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node("core_bourgeoisie", wealth=100.0)
        graph.add_node(
            "client_state",
            wealth=0.0,
            organization=0.8,
            # No repression_faced - will use default
            subsistence_threshold=0.3,
        )

        graph.add_edge(
            "core_bourgeoisie",
            "client_state",
            edge_type=EdgeType.CLIENT_STATE,
            subsidy_cap=10.0,
        )

        economy_defines = EconomyDefines(
            subsidy_trigger_threshold=0.5,
            subsidy_conversion_rate=0.1,
        )
        survival_defines = SurvivalDefines(
            default_repression=0.5,  # Default repression
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

        # Act - should not raise, uses default repression
        system._process_subsidy_phase(graph, services, {"tick": 1}, tick_context)

        # Assert: Method ran and subsidy was processed
        # With org=0.8, default repression=0.5, P(S|R) = 0.8/0.5 = 1.6 (capped at 1.0)
        # With very low wealth, P(S|A) is very low
        # Stability ratio is high, so subsidy should trigger
        assert tick_context["subsidy_outflow"] > 0.0


@pytest.mark.unit
class TestMissingEdgeFlowDefaults:
    """Test that missing value_flow and other edge attributes default correctly."""

    def test_extraction_creates_value_flow(self) -> None:
        """Extraction phase creates value_flow attribute on edge.

        Even if value_flow was missing before, it should be set after.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()

        graph.add_node("worker", wealth=1.0, ideology={"class_consciousness": 0.0})
        graph.add_node("owner", wealth=0.0)
        # Edge WITHOUT value_flow
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)

        services = ServiceContainer.create()

        tick_context: dict[str, Any] = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 100.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system = ImperialRentSystem()

        # Act
        system._process_extraction_phase(graph, services, {"tick": 1}, tick_context)

        # Assert: value_flow should now exist on edge
        assert "value_flow" in graph.edges["worker", "owner"]
        # With extraction efficiency 0.8, rent = 0.8 * 1.0 * (1-0) = 0.8
        assert graph.edges["worker", "owner"]["value_flow"] == pytest.approx(0.8, rel=1e-6)
