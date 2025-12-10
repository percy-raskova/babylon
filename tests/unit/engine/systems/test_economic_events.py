"""Tests for ImperialRentSystem event emission and PPP model.

RED Phase: These tests define the contract for SURPLUS_EXTRACTION events.
The ImperialRentSystem must emit events when imperial rent is extracted,
enabling the AI Narrative layer to react to economic exploitation dynamics.

Test Intent:
- SURPLUS_EXTRACTION event emitted when rent > 0.01
- No event when rent is negligible (floating point noise)
- Event payload contains source_id, target_id, amount, mechanism

PPP Model Tests (Sprint PPP):
- Wages phase calculates effective wealth using PPP multiplier
- High superwage_multiplier -> Higher effective wealth -> Higher P(S|A)
- Low superwage_multiplier -> Lower effective wealth -> Lower P(S|A)
"""

import networkx as nx
import pytest

from babylon.engine.services import ServiceContainer
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.models.config import SimulationConfig
from babylon.models.enums import EdgeType, EventType, SocialRole


class TestImperialRentSystemEvents:
    """Test event emission from ImperialRentSystem."""

    @pytest.mark.unit
    def test_rent_extraction_emits_event(self) -> None:
        """SURPLUS_EXTRACTION event emitted when rent > 0.01."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("worker", wealth=0.5, ideology=0.0)
        graph.add_node("owner", wealth=0.5)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 5}
        system = ImperialRentSystem()

        # Act
        system.step(graph, services, context)

        # Assert
        events = services.event_bus.get_history()
        assert len(events) == 1
        event = events[0]
        assert event.type == EventType.SURPLUS_EXTRACTION
        assert event.tick == 5
        assert event.payload["source_id"] == "worker"
        assert event.payload["target_id"] == "owner"
        assert event.payload["amount"] > 0.01
        assert event.payload["mechanism"] == "imperial_rent"

    @pytest.mark.unit
    def test_no_event_on_zero_rent(self) -> None:
        """No event when rent is negligible (< 0.01)."""
        # Arrange: Worker with 0 wealth = 0 rent
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("worker", wealth=0.0, ideology=0.0)
        graph.add_node("owner", wealth=0.5)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)

        services = ServiceContainer.create()
        context: dict[str, int] = {"tick": 1}
        system = ImperialRentSystem()

        # Act
        system.step(graph, services, context)

        # Assert
        events = services.event_bus.get_history()
        assert len(events) == 0


class TestPPPWagesModel:
    """Test Purchasing Power Parity (PPP) model for super-wages.

    PPP Model: Super-wages manifest as purchasing power, not direct cash.
    The labor aristocracy receives nominal wages, but their effective wealth
    is increased by the PPP multiplier based on imperial extraction.

    Formula:
        PPP Multiplier = 1 + (extraction_efficiency * superwage_multiplier * ppp_impact)
        Effective Wealth = Nominal Wealth + (Nominal Wage * (PPP Multiplier - 1))

    The "unearned increment" = Effective Wealth - Nominal Wealth
    This represents cheap commodities from the periphery.
    """

    @pytest.mark.unit
    def test_high_superwage_multiplier_increases_effective_wealth(self) -> None:
        """High superwage_multiplier -> Higher PPP -> Higher effective wealth."""
        # Arrange: Graph with WAGES edge
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "bourgeoisie",
            wealth=1.0,
            role=SocialRole.CORE_BOURGEOISIE,
        )
        graph.add_node(
            "worker",
            wealth=0.5,
            role=SocialRole.LABOR_ARISTOCRACY,
        )
        graph.add_edge("bourgeoisie", "worker", edge_type=EdgeType.WAGES)

        # High superwage multiplier config
        high_sw_config = SimulationConfig(
            superwage_multiplier=1.5,
            superwage_ppp_impact=0.5,
            extraction_efficiency=0.8,
            super_wage_rate=0.2,
        )
        services = ServiceContainer.create(config=high_sw_config)
        context: dict[str, int] = {"tick": 1}
        system = ImperialRentSystem()

        # Initialize tick_context with economy defaults
        tick_context = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 100.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        # Act: Process wages phase directly
        system._process_wages_phase(graph, services, context, tick_context)

        # Assert: Worker should have effective_wealth set
        worker_data = graph.nodes["worker"]
        assert "effective_wealth" in worker_data
        # PPP_mult = 1 + (0.8 * 1.5 * 0.5) = 1.6
        # Nominal wage = 1.0 * 0.2 = 0.2
        # effective_wealth_gain = 0.2 * (1.6 - 1) = 0.12
        # Total effective = 0.5 + 0.2 + 0.12 = 0.82
        # Or: effective = (initial_wealth + nominal_wage) + ppp_bonus
        assert worker_data["effective_wealth"] > worker_data["wealth"]

    @pytest.mark.unit
    def test_low_superwage_multiplier_minimal_ppp_bonus(self) -> None:
        """Low superwage_multiplier -> Lower PPP -> Minimal effective wealth bonus."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "bourgeoisie",
            wealth=1.0,
            role=SocialRole.CORE_BOURGEOISIE,
        )
        graph.add_node(
            "worker",
            wealth=0.5,
            role=SocialRole.LABOR_ARISTOCRACY,
        )
        graph.add_edge("bourgeoisie", "worker", edge_type=EdgeType.WAGES)

        # Low superwage multiplier config
        low_sw_config = SimulationConfig(
            superwage_multiplier=0.3,
            superwage_ppp_impact=0.5,
            extraction_efficiency=0.8,
            super_wage_rate=0.2,
        )
        services = ServiceContainer.create(config=low_sw_config)
        context: dict[str, int] = {"tick": 1}
        system = ImperialRentSystem()

        tick_context = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 100.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        # Act
        system._process_wages_phase(graph, services, context, tick_context)

        # Assert
        worker_data = graph.nodes["worker"]
        # PPP_mult = 1 + (0.8 * 0.3 * 0.5) = 1.12
        # Much smaller bonus than high superwage case
        assert "effective_wealth" in worker_data
        # The PPP bonus should still exist but be smaller
        ppp_bonus = worker_data["effective_wealth"] - worker_data["wealth"]
        # With low SW (0.3), bonus should be less than with high SW (1.5)
        assert ppp_bonus > 0  # Still some bonus
        assert ppp_bonus < 0.2  # But smaller than the wage itself

    @pytest.mark.unit
    def test_ppp_multiplier_formula(self) -> None:
        """Test PPP multiplier formula: 1 + (extraction * sw_mult * impact)."""
        # Arrange
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("bourgeoisie", wealth=1.0, role=SocialRole.CORE_BOURGEOISIE)
        graph.add_node("worker", wealth=0.0, role=SocialRole.LABOR_ARISTOCRACY)
        graph.add_edge("bourgeoisie", "worker", edge_type=EdgeType.WAGES)

        # Known values for calculation
        config = SimulationConfig(
            superwage_multiplier=1.0,  # Neutral
            superwage_ppp_impact=0.5,
            extraction_efficiency=0.8,
            super_wage_rate=0.5,  # 50% wage rate = 0.5 wages
        )
        services = ServiceContainer.create(config=config)
        system = ImperialRentSystem()

        tick_context = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 100.0,
            "wage_rate": 0.5,
            "repression_level": 0.5,
        }

        # Act
        system._process_wages_phase(graph, services, {}, tick_context)

        # Assert
        # PPP_mult = 1 + (0.8 * 1.0 * 0.5) = 1.4
        # Nominal wage = 1.0 * 0.5 = 0.5
        # PPP bonus = 0.5 * (1.4 - 1) = 0.2
        # effective_wealth = 0.0 + 0.5 + 0.2 = 0.7
        worker_data = graph.nodes["worker"]
        assert worker_data["wealth"] == pytest.approx(0.5, rel=1e-6)  # Nominal
        expected_effective = 0.5 + (0.5 * 0.4)  # 0.5 + 0.2 = 0.7
        assert worker_data["effective_wealth"] == pytest.approx(expected_effective, rel=1e-6)

    @pytest.mark.unit
    def test_unearned_increment_recorded(self) -> None:
        """Test that unearned increment (PPP bonus) is recorded on worker node."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("bourgeoisie", wealth=1.0, role=SocialRole.CORE_BOURGEOISIE)
        graph.add_node("worker", wealth=0.2, role=SocialRole.LABOR_ARISTOCRACY)
        graph.add_edge("bourgeoisie", "worker", edge_type=EdgeType.WAGES)

        config = SimulationConfig(
            superwage_multiplier=1.5,
            superwage_ppp_impact=0.5,
            extraction_efficiency=0.8,
            super_wage_rate=0.2,
        )
        services = ServiceContainer.create(config=config)
        system = ImperialRentSystem()

        tick_context = {
            "tribute_inflow": 0.0,
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 100.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system._process_wages_phase(graph, services, {}, tick_context)

        worker_data = graph.nodes["worker"]
        # unearned_increment should be set
        assert "unearned_increment" in worker_data
        # It should equal effective_wealth - wealth
        expected_increment = worker_data["effective_wealth"] - worker_data["wealth"]
        assert worker_data["unearned_increment"] == pytest.approx(expected_increment, rel=1e-6)
