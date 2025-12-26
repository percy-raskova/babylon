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
from tests.assertions import Assert
from tests.factories.domain import DomainFactory

from babylon.engine.services import ServiceContainer
from babylon.engine.simulation_engine import step
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.models.config import SimulationConfig
from babylon.models.enums import EdgeType, EventType, SocialRole

# RED Phase imports - these don't exist yet and will cause import errors
from babylon.models.events import ExtractionEvent


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
        # BUG FIX: Wages come from tribute_inflow, not accumulated wealth
        tick_context = {
            "tribute_inflow": 1.0,  # Provides basis for wage calculation
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
        # Nominal wage = tribute_inflow * wage_rate = 1.0 * 0.2 = 0.2
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

        # BUG FIX: Wages come from tribute_inflow, not accumulated wealth
        tick_context = {
            "tribute_inflow": 1.0,  # Provides basis for wage calculation
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
            "tribute_inflow": 1.0,  # BUG FIX: Wages come from tribute, not wealth
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
        # Nominal wage = tribute_inflow * wage_rate = 1.0 * 0.5 = 0.5
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
            "tribute_inflow": 1.0,  # BUG FIX: Wages come from tribute, not wealth
            "wages_outflow": 0.0,
            "subsidy_outflow": 0.0,
            "current_pool": 100.0,
            "wage_rate": 0.2,
            "repression_level": 0.5,
        }

        system._process_wages_phase(graph, services, {}, tick_context)

        worker_data = graph.nodes["worker"]
        # unearned_increment should be set (wages = 1.0 * 0.2 = 0.2)
        assert "unearned_increment" in worker_data
        # It should equal effective_wealth - wealth
        expected_increment = worker_data["effective_wealth"] - worker_data["wealth"]
        assert worker_data["unearned_increment"] == pytest.approx(expected_increment, rel=1e-6)


class TestStructuredEventsInWorldState:
    """Sprint 3.1: Test that structured Pydantic events persist in WorldState.

    RED Phase: These tests define the contract for typed events in WorldState.

    Current State:
    - EventBus publishes Event dataclass with type, tick, payload
    - WorldState only has event_log: list[str] for backward compatibility
    - Events are lost after step() completes (only string summary preserved)

    Goal:
    - WorldState.events: list[SimulationEvent] - typed Pydantic events
    - ExtractionEvent, SolidarityEvent, etc. - domain-specific event types
    - Events persist across the simulation for analysis/replay

    Test Intent:
    - After step(), WorldState.events should contain typed event objects
    - ExtractionEvent should have source_id, target_id, amount fields
    - DomainFactory should accept events parameter
    - Backward compatibility: event_log should still be populated
    """

    @pytest.mark.unit
    def test_extraction_event_in_world_state(self) -> None:
        """After step(), an ExtractionEvent should appear in new_state.events.

        This test verifies that when imperial rent is extracted during a tick,
        the resulting WorldState contains a structured ExtractionEvent in its
        events list, not just a string in event_log.

        The event should be a Pydantic model enabling downstream analysis.
        """
        # Arrange
        factory = DomainFactory()
        worker = factory.create_worker(wealth=0.5)
        owner = factory.create_owner(wealth=0.5)
        relationship = factory.create_relationship(
            source_id=worker.id,
            target_id=owner.id,
            edge_type=EdgeType.EXPLOITATION,
        )
        state = factory.create_world_state(
            entities={worker.id: worker, owner.id: owner},
            relationships=[relationship],
        )

        # Act
        new_state = step(state, SimulationConfig())

        # Assert - At least one ExtractionEvent should exist
        # Note: Don't check exact count - StruggleSystem may add random spark events
        Assert(new_state).has_event(ExtractionEvent)

    @pytest.mark.unit
    def test_extraction_event_has_correct_payload(self) -> None:
        """ExtractionEvent should have correct source_id, target_id, amount.

        This test verifies that the ExtractionEvent contains the actual
        economic data from the imperial rent extraction - who extracted
        from whom, and how much was taken.

        These fields enable:
        - AI narrative generation ("Worker lost $X to Owner")
        - Economic analysis (total extraction over time)
        - Network flow visualization
        """
        # Arrange - Use valid C-prefixed IDs per SocialClass id pattern
        factory = DomainFactory()
        worker = factory.create_worker(id="C001", wealth=1.0)
        owner = factory.create_owner(id="C002", wealth=5.0)
        relationship = factory.create_relationship(
            source_id=worker.id,
            target_id=owner.id,
            edge_type=EdgeType.EXPLOITATION,
        )
        state = factory.create_world_state(
            entities={worker.id: worker, owner.id: owner},
            relationships=[relationship],
        )

        # Act
        new_state = step(state, SimulationConfig())

        # Assert - Verify typed event with correct fields
        Assert(new_state).has_event(
            ExtractionEvent,
            source_id="C001",
            target_id="C002",
        )
        # Amount should be positive (wealth was extracted)
        Assert(new_state).has_event(ExtractionEvent, amount_gt=0.0)

    @pytest.mark.unit
    def test_domain_factory_creates_state_with_events(self) -> None:
        """DomainFactory.create_world_state(events=[...]) should work.

        This test verifies that the DomainFactory can accept a list of
        pre-existing events when creating a WorldState. This enables:
        - Testing event-dependent logic with known events
        - Replaying simulations from a known event history
        - Creating counterfactual scenarios
        """
        # Arrange
        factory = DomainFactory()
        worker = factory.create_worker()

        # Create a pre-existing event with valid IDs
        event = ExtractionEvent(
            tick=5,
            source_id="C001",
            target_id="C002",
            amount=0.1,
        )

        # Act - events parameter now exists (GREEN phase)
        state = factory.create_world_state(
            entities={worker.id: worker},
            events=[event],
        )

        # Assert
        Assert(state).has_events_count(1)
        Assert(state).has_event(ExtractionEvent, tick=5)

    @pytest.mark.unit
    def test_event_log_still_works_for_backward_compatibility(self) -> None:
        """Both events and event_log should be populated after step().

        This test ensures backward compatibility: the existing event_log
        (list[str]) should still be populated alongside the new typed
        events list. This allows gradual migration and ensures existing
        code that reads event_log continues to work.
        """
        # Arrange
        factory = DomainFactory()
        worker = factory.create_worker(wealth=0.5)
        owner = factory.create_owner(wealth=0.5)
        relationship = factory.create_relationship(
            source_id=worker.id,
            target_id=owner.id,
            edge_type=EdgeType.EXPLOITATION,
        )
        state = factory.create_world_state(
            entities={worker.id: worker, owner.id: owner},
            relationships=[relationship],
        )

        # Act
        new_state = step(state, SimulationConfig())

        # Assert - Both should be populated
        # Typed events list (at least one extraction event)
        # Note: Don't check exact count - StruggleSystem may add random spark events
        Assert(new_state).has_event(ExtractionEvent)
        # Legacy string log (backward compatibility)
        assert len(new_state.event_log) > 0
        assert any("SURPLUS_EXTRACTION" in log for log in new_state.event_log)
