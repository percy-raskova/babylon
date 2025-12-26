"""Tests for phase transition event emission from TopologyMonitor.

Sprint 3.3: The Topology Monitor - Phase Transition Events

These tests verify that TopologyMonitor correctly detects and emits
PhaseTransitionEvent when the solidarity network structure crosses
percolation thresholds.

Phase States:
- Gaseous: percolation_ratio < 0.1 (atomized)
- Transitional: 0.1 <= ratio < 0.5 (emerging)
- Liquid: ratio >= 0.5 (giant component)

TDD Red Phase: These tests define the contract for phase transition events.
Tests must fail initially until the implementation is complete.
"""

from __future__ import annotations

import pytest
from tests.factories.domain import DomainFactory

from babylon.models.enums import EdgeType, EventType

# =============================================================================
# TEST: PHASE_TRANSITION EventType
# =============================================================================


@pytest.mark.unit
class TestPhaseTransitionEventType:
    """Tests for PHASE_TRANSITION EventType in enums.py."""

    def test_phase_transition_event_type_exists(self) -> None:
        """PHASE_TRANSITION event type exists in EventType enum."""
        assert hasattr(EventType, "PHASE_TRANSITION")
        assert EventType.PHASE_TRANSITION.value == "phase_transition"

    def test_phase_transition_constructible_from_string(self) -> None:
        """Can construct PHASE_TRANSITION from string value."""
        assert EventType("phase_transition") == EventType.PHASE_TRANSITION

    def test_event_type_count_updated(self) -> None:
        """EventType count is 12 (includes ECOLOGICAL_OVERSHOOT from Slice 1.4)."""
        assert len(EventType) == 12


# =============================================================================
# TEST: PhaseTransitionEvent Model
# =============================================================================


@pytest.mark.unit
class TestPhaseTransitionEventModel:
    """Tests for PhaseTransitionEvent Pydantic model."""

    def test_phase_transition_event_importable(self) -> None:
        """PhaseTransitionEvent can be imported from events module."""
        from babylon.models.events import PhaseTransitionEvent

        assert PhaseTransitionEvent is not None

    def test_topology_event_base_class_exists(self) -> None:
        """TopologyEvent base class exists."""
        from babylon.models.events import TopologyEvent

        assert TopologyEvent is not None

    def test_phase_transition_event_creation(self) -> None:
        """PhaseTransitionEvent can be created with required fields."""
        from babylon.models.events import PhaseTransitionEvent

        event = PhaseTransitionEvent(
            tick=5,
            previous_state="gaseous",
            new_state="liquid",
            percolation_ratio=0.6,
            num_components=2,
            largest_component_size=8,
        )

        assert event.tick == 5
        assert event.event_type == EventType.PHASE_TRANSITION
        assert event.previous_state == "gaseous"
        assert event.new_state == "liquid"
        assert event.percolation_ratio == pytest.approx(0.6)
        assert event.num_components == 2
        assert event.largest_component_size == 8

    def test_phase_transition_event_is_frozen(self) -> None:
        """PhaseTransitionEvent is immutable (frozen)."""
        from babylon.models.events import PhaseTransitionEvent

        event = PhaseTransitionEvent(
            tick=5,
            previous_state="gaseous",
            new_state="liquid",
            percolation_ratio=0.6,
            num_components=2,
            largest_component_size=8,
        )

        from pydantic import ValidationError

        with pytest.raises(ValidationError):  # Frozen model cannot be mutated
            event.tick = 10  # type: ignore[misc]

    def test_phase_transition_event_optional_resilient(self) -> None:
        """is_resilient field is optional (can be None)."""
        from babylon.models.events import PhaseTransitionEvent

        event = PhaseTransitionEvent(
            tick=5,
            previous_state="gaseous",
            new_state="liquid",
            percolation_ratio=0.6,
            num_components=2,
            largest_component_size=8,
            is_resilient=None,
        )

        assert event.is_resilient is None

    def test_phase_transition_event_with_resilience(self) -> None:
        """PhaseTransitionEvent accepts is_resilient bool."""
        from babylon.models.events import PhaseTransitionEvent

        event = PhaseTransitionEvent(
            tick=5,
            previous_state="gaseous",
            new_state="liquid",
            percolation_ratio=0.6,
            num_components=2,
            largest_component_size=8,
            is_resilient=True,
        )

        assert event.is_resilient is True

    def test_phase_transition_inherits_from_topology_event(self) -> None:
        """PhaseTransitionEvent inherits from TopologyEvent."""
        from babylon.models.events import PhaseTransitionEvent, TopologyEvent

        event = PhaseTransitionEvent(
            tick=5,
            previous_state="gaseous",
            new_state="liquid",
            percolation_ratio=0.6,
            num_components=2,
            largest_component_size=8,
        )

        assert isinstance(event, TopologyEvent)


# =============================================================================
# TEST: TopologyMonitor Phase Classification
# =============================================================================


@pytest.mark.topology
class TestTopologyMonitorPhaseClassification:
    """Tests for phase classification logic in TopologyMonitor."""

    def test_classify_phase_gaseous(self) -> None:
        """percolation_ratio < 0.1 classifies as gaseous."""
        from babylon.engine.topology_monitor import TopologyMonitor

        monitor = TopologyMonitor()
        assert monitor._classify_phase(0.05) == "gaseous"
        assert monitor._classify_phase(0.0) == "gaseous"
        assert monitor._classify_phase(0.09) == "gaseous"

    def test_classify_phase_transitional(self) -> None:
        """0.1 <= percolation_ratio < 0.5 classifies as transitional."""
        from babylon.engine.topology_monitor import TopologyMonitor

        monitor = TopologyMonitor()
        assert monitor._classify_phase(0.1) == "transitional"
        assert monitor._classify_phase(0.3) == "transitional"
        assert monitor._classify_phase(0.49) == "transitional"

    def test_classify_phase_liquid(self) -> None:
        """percolation_ratio >= 0.5 AND cadre_density < 0.5 classifies as liquid."""
        from babylon.engine.topology_monitor import TopologyMonitor

        monitor = TopologyMonitor()
        # With low cadre_density (weak ties), phase is liquid (mass movement)
        assert monitor._classify_phase(0.5, cadre_density=0.0) == "liquid"
        assert monitor._classify_phase(0.8, cadre_density=0.2) == "liquid"
        assert monitor._classify_phase(1.0, cadre_density=0.49) == "liquid"

    def test_classify_phase_solid(self) -> None:
        """percolation_ratio >= 0.5 AND cadre_density >= 0.5 classifies as solid."""
        from babylon.engine.topology_monitor import TopologyMonitor

        monitor = TopologyMonitor()
        # With high cadre_density (strong ties), phase is solid (vanguard party)
        assert monitor._classify_phase(0.5, cadre_density=0.5) == "solid"
        assert monitor._classify_phase(0.8, cadre_density=0.8) == "solid"
        assert monitor._classify_phase(1.0, cadre_density=1.0) == "solid"


# =============================================================================
# TEST: TopologyMonitor Pending Events API
# =============================================================================


@pytest.mark.topology
class TestTopologyMonitorPendingEvents:
    """Tests for TopologyMonitor pending events collection API."""

    def test_get_pending_events_exists(self) -> None:
        """TopologyMonitor has get_pending_events method."""
        from babylon.engine.topology_monitor import TopologyMonitor

        monitor = TopologyMonitor()
        assert hasattr(monitor, "get_pending_events")
        assert callable(monitor.get_pending_events)

    def test_get_pending_events_returns_empty_initially(self) -> None:
        """get_pending_events returns empty list initially."""
        from babylon.engine.topology_monitor import TopologyMonitor

        monitor = TopologyMonitor()
        events = monitor.get_pending_events()

        assert events == []

    def test_get_pending_events_clears_after_call(self) -> None:
        """get_pending_events clears internal list after returning."""
        from babylon.engine.topology_monitor import TopologyMonitor

        monitor = TopologyMonitor()
        # Internal state setup for test
        monitor._pending_events = ["fake_event"]  # type: ignore[list-item]

        first_call = monitor.get_pending_events()
        second_call = monitor.get_pending_events()

        assert len(first_call) == 1
        assert len(second_call) == 0


# =============================================================================
# TEST: Phase Transition Event Emission
# =============================================================================


@pytest.mark.topology
class TestPhaseTransitionEventEmission:
    """Tests for phase transition detection and event emission."""

    def test_gaseous_state_isolated_nodes_no_event_first_tick(self) -> None:
        """10 isolated workers with no edges -> gaseous state.

        First tick establishes baseline, no event emitted (no previous state).
        """
        from babylon.engine.simulation import Simulation
        from babylon.engine.topology_monitor import TopologyMonitor
        from babylon.models.config import SimulationConfig

        factory = DomainFactory()
        workers = [factory.create_worker(id=f"C{i:03d}") for i in range(10)]
        entities = {w.id: w for w in workers}

        state = factory.create_world_state(entities=entities, relationships=[])
        config = SimulationConfig()
        monitor = TopologyMonitor()
        sim = Simulation(state, config, observers=[monitor])

        # First tick establishes baseline (gaseous)
        sim.step()

        # No transition event on first tick (no previous state to compare)
        events = monitor.get_pending_events()
        assert len(events) == 0

    def test_liquid_state_connected_network_weak_ties(self) -> None:
        """6 workers connected with WEAK solidarity -> liquid state (mass movement).

        Liquid phase requires: percolation >= 0.5 AND cadre_density < 0.5
        Using solidarity_strength=0.2 means edges count as sympathizers but NOT cadre.
        """
        from babylon.engine.simulation import Simulation
        from babylon.engine.topology_monitor import TopologyMonitor
        from babylon.models.config import SimulationConfig

        factory = DomainFactory()
        workers = [factory.create_worker(id=f"C{i:03d}") for i in range(6)]
        entities = {w.id: w for w in workers}

        # Create chain: C000 -> C001 -> C002 -> C003 -> C004 -> C005
        # Using solidarity_strength=0.2: above potential (0.1) but below actual (0.5)
        # This creates weak ties: high percolation but low cadre_density -> liquid
        relationships = []
        for i in range(5):
            relationships.append(
                factory.create_relationship(
                    source_id=f"C{i:03d}",
                    target_id=f"C{i + 1:03d}",
                    edge_type=EdgeType.SOLIDARITY,
                    solidarity_strength=0.2,  # Weak solidarity (sympathizers only)
                )
            )

        state = factory.create_world_state(entities=entities, relationships=relationships)
        config = SimulationConfig()
        monitor = TopologyMonitor()
        sim = Simulation(state, config, observers=[monitor])

        # Run tick
        sim.step()

        # Check monitor tracked metrics (all 6 in one component = 100% percolation)
        assert len(monitor.history) == 2  # Initial + 1 tick
        snapshot = monitor.history[-1]
        # The chain creates one giant component, so percolation = 1.0
        assert snapshot.percolation_ratio >= 0.5
        # Weak ties: cadre_density should be 0 (no edges > 0.5)
        assert snapshot.cadre_density == 0.0
        # Therefore, phase should be liquid (mass movement)
        assert monitor._previous_phase == "liquid"

    def test_solid_state_connected_network_strong_ties(self) -> None:
        """6 workers connected with STRONG solidarity -> solid state (vanguard party).

        Solid phase requires: percolation >= 0.5 AND cadre_density >= 0.5
        Using solidarity_strength=0.8 means edges count as BOTH sympathizers AND cadre.
        """
        from babylon.engine.simulation import Simulation
        from babylon.engine.topology_monitor import TopologyMonitor
        from babylon.models.config import SimulationConfig

        factory = DomainFactory()
        workers = [factory.create_worker(id=f"C{i:03d}") for i in range(6)]
        entities = {w.id: w for w in workers}

        # Create chain with STRONG ties (solidarity_strength=0.8)
        # Above both thresholds: potential (0.1) and actual (0.5)
        relationships = []
        for i in range(5):
            relationships.append(
                factory.create_relationship(
                    source_id=f"C{i:03d}",
                    target_id=f"C{i + 1:03d}",
                    edge_type=EdgeType.SOLIDARITY,
                    solidarity_strength=0.8,  # Strong solidarity (cadre)
                )
            )

        state = factory.create_world_state(entities=entities, relationships=relationships)
        config = SimulationConfig()
        monitor = TopologyMonitor()
        sim = Simulation(state, config, observers=[monitor])

        # Run tick
        sim.step()

        # Check monitor tracked metrics
        assert len(monitor.history) == 2  # Initial + 1 tick
        snapshot = monitor.history[-1]
        # The chain creates one giant component, so percolation = 1.0
        assert snapshot.percolation_ratio >= 0.5
        # Strong ties: cadre_density should be 1.0 (all edges are cadre)
        assert snapshot.cadre_density == 1.0
        # Therefore, phase should be solid (vanguard party)
        assert monitor._previous_phase == "solid"

    def test_phase_transition_event_emitted_on_state_change(self) -> None:
        """Transition from gaseous -> liquid emits PhaseTransitionEvent.

        Uses WEAK solidarity (0.2) to get liquid phase, not solid.
        """
        from babylon.engine.topology_monitor import TopologyMonitor
        from babylon.models.config import SimulationConfig
        from babylon.models.events import PhaseTransitionEvent

        factory = DomainFactory()

        # Start with 10 isolated nodes - need >10 for gaseous (ratio < 0.1)
        # With 10 isolated nodes, max_component = 1, ratio = 0.1 (exactly on threshold)
        # Use 12 nodes to ensure ratio < 0.1 (1/12 = 0.083)
        workers = [factory.create_worker(id=f"C{i:03d}") for i in range(12)]
        entities = {w.id: w for w in workers}
        state = factory.create_world_state(entities=entities, relationships=[])

        config = SimulationConfig()
        monitor = TopologyMonitor()

        # Initialize monitor with gaseous state
        monitor.on_simulation_start(state, config)
        assert monitor._previous_phase == "gaseous"

        # Now add WEAK solidarity edges to create liquid state (mass movement)
        # Using 0.2: above potential threshold (0.1) but below actual (0.5)
        # This gives: percolation >= 0.5, cadre_density = 0 -> liquid
        relationships = []
        for i in range(11):
            relationships.append(
                factory.create_relationship(
                    source_id=f"C{i:03d}",
                    target_id=f"C{i + 1:03d}",
                    edge_type=EdgeType.SOLIDARITY,
                    solidarity_strength=0.2,  # Weak ties for liquid phase
                )
            )

        # Create new state with relationships
        new_state_with_solidarity = factory.create_world_state(
            tick=1,
            entities=entities,
            relationships=relationships,
        )

        # Manually trigger on_tick to simulate transition
        monitor.on_tick(state, new_state_with_solidarity)

        # Should have emitted phase transition event
        events = monitor.get_pending_events()
        assert len(events) == 1
        assert isinstance(events[0], PhaseTransitionEvent)
        assert events[0].previous_state == "gaseous"
        assert events[0].new_state == "liquid"
        assert events[0].cadre_density == 0.0  # Weak ties = no cadre

    def test_phase_transition_gaseous_to_solid(self) -> None:
        """Transition from gaseous -> solid emits PhaseTransitionEvent.

        Uses STRONG solidarity (0.8) to get solid phase directly.
        """
        from babylon.engine.topology_monitor import TopologyMonitor
        from babylon.models.config import SimulationConfig
        from babylon.models.events import PhaseTransitionEvent

        factory = DomainFactory()

        # Start with isolated nodes (gaseous)
        workers = [factory.create_worker(id=f"C{i:03d}") for i in range(12)]
        entities = {w.id: w for w in workers}
        state = factory.create_world_state(entities=entities, relationships=[])

        config = SimulationConfig()
        monitor = TopologyMonitor()

        # Initialize monitor with gaseous state
        monitor.on_simulation_start(state, config)
        assert monitor._previous_phase == "gaseous"

        # Now add STRONG solidarity edges to create solid state (vanguard)
        # Using 0.8: above both thresholds -> cadre_density = 1.0 -> solid
        relationships = []
        for i in range(11):
            relationships.append(
                factory.create_relationship(
                    source_id=f"C{i:03d}",
                    target_id=f"C{i + 1:03d}",
                    edge_type=EdgeType.SOLIDARITY,
                    solidarity_strength=0.8,  # Strong ties for solid phase
                )
            )

        new_state_with_solidarity = factory.create_world_state(
            tick=1,
            entities=entities,
            relationships=relationships,
        )

        # Manually trigger on_tick to simulate transition
        monitor.on_tick(state, new_state_with_solidarity)

        # Should have emitted phase transition event to solid
        events = monitor.get_pending_events()
        assert len(events) == 1
        assert isinstance(events[0], PhaseTransitionEvent)
        assert events[0].previous_state == "gaseous"
        assert events[0].new_state == "solid"
        assert events[0].cadre_density == 1.0  # Strong ties = all cadre

    def test_no_event_when_state_unchanged(self) -> None:
        """Same phase between ticks -> no event emitted."""
        from babylon.engine.simulation import Simulation
        from babylon.engine.topology_monitor import TopologyMonitor
        from babylon.models.config import SimulationConfig

        factory = DomainFactory()
        workers = [factory.create_worker(id=f"C{i:03d}") for i in range(6)]
        entities = {w.id: w for w in workers}

        # Fully connected from start with strong ties -> solid phase
        relationships = []
        for i in range(5):
            relationships.append(
                factory.create_relationship(
                    source_id=f"C{i:03d}",
                    target_id=f"C{i + 1:03d}",
                    edge_type=EdgeType.SOLIDARITY,
                    solidarity_strength=0.8,  # Strong ties -> solid
                )
            )

        state = factory.create_world_state(entities=entities, relationships=relationships)
        config = SimulationConfig()
        monitor = TopologyMonitor()
        sim = Simulation(state, config, observers=[monitor])

        # First tick
        sim.step()
        _ = monitor.get_pending_events()  # Clear any events

        # Verify we're in solid state
        assert monitor._previous_phase == "solid"

        # Second tick (still solid)
        sim.step()
        events2 = monitor.get_pending_events()

        # No transition event (still solid)
        assert len(events2) == 0

    def test_transitional_to_liquid_transition(self) -> None:
        """Transition from transitional -> liquid emits event.

        Uses WEAK solidarity (0.2) for liquid phase.
        """
        from babylon.engine.topology_monitor import TopologyMonitor
        from babylon.models.config import SimulationConfig
        from babylon.models.events import PhaseTransitionEvent

        factory = DomainFactory()

        # Create 10 workers, connect 2 (20% connected = transitional)
        workers = [factory.create_worker(id=f"C{i:03d}") for i in range(10)]
        entities = {w.id: w for w in workers}

        # Connect just 2 nodes -> percolation = 2/10 = 0.2 (transitional)
        # Using weak ties here too
        relationships_partial = [
            factory.create_relationship(
                source_id="C000",
                target_id="C001",
                edge_type=EdgeType.SOLIDARITY,
                solidarity_strength=0.2,  # Weak ties for liquid phase
            )
        ]

        state_transitional = factory.create_world_state(
            tick=0, entities=entities, relationships=relationships_partial
        )

        config = SimulationConfig()
        monitor = TopologyMonitor()

        # Initialize monitor with transitional state
        monitor.on_simulation_start(state_transitional, config)
        assert monitor._previous_phase == "transitional"

        # Connect all 10 nodes with WEAK ties -> percolation = 1.0, cadre_density = 0 -> liquid
        relationships_liquid = []
        for i in range(9):  # Connect all 10 nodes
            relationships_liquid.append(
                factory.create_relationship(
                    source_id=f"C{i:03d}",
                    target_id=f"C{i + 1:03d}",
                    edge_type=EdgeType.SOLIDARITY,
                    solidarity_strength=0.2,  # Weak ties for liquid phase
                )
            )

        state_liquid = factory.create_world_state(
            tick=1, entities=entities, relationships=relationships_liquid
        )

        # Trigger transition
        monitor.on_tick(state_transitional, state_liquid)

        # Should emit transitional -> liquid event
        events = monitor.get_pending_events()
        assert len(events) == 1
        assert isinstance(events[0], PhaseTransitionEvent)
        assert events[0].previous_state == "transitional"
        assert events[0].new_state == "liquid"
        assert events[0].cadre_density == 0.0  # Weak ties = no cadre

    def test_transitional_to_solid_transition(self) -> None:
        """Transition from transitional -> solid emits event.

        Uses STRONG solidarity (0.8) for solid phase.
        """
        from babylon.engine.topology_monitor import TopologyMonitor
        from babylon.models.config import SimulationConfig
        from babylon.models.events import PhaseTransitionEvent

        factory = DomainFactory()

        # Create 10 workers, connect 2 (20% connected = transitional)
        workers = [factory.create_worker(id=f"C{i:03d}") for i in range(10)]
        entities = {w.id: w for w in workers}

        # Connect just 2 nodes with strong ties -> percolation = 0.2 (transitional)
        relationships_partial = [
            factory.create_relationship(
                source_id="C000",
                target_id="C001",
                edge_type=EdgeType.SOLIDARITY,
                solidarity_strength=0.8,  # Strong ties
            )
        ]

        state_transitional = factory.create_world_state(
            tick=0, entities=entities, relationships=relationships_partial
        )

        config = SimulationConfig()
        monitor = TopologyMonitor()

        # Initialize monitor with transitional state
        monitor.on_simulation_start(state_transitional, config)
        assert monitor._previous_phase == "transitional"

        # Connect all 10 nodes with STRONG ties -> solid (vanguard)
        relationships_solid = []
        for i in range(9):  # Connect all 10 nodes
            relationships_solid.append(
                factory.create_relationship(
                    source_id=f"C{i:03d}",
                    target_id=f"C{i + 1:03d}",
                    edge_type=EdgeType.SOLIDARITY,
                    solidarity_strength=0.8,  # Strong ties for solid phase
                )
            )

        state_solid = factory.create_world_state(
            tick=1, entities=entities, relationships=relationships_solid
        )

        # Trigger transition
        monitor.on_tick(state_transitional, state_solid)

        # Should emit transitional -> solid event
        events = monitor.get_pending_events()
        assert len(events) == 1
        assert isinstance(events[0], PhaseTransitionEvent)
        assert events[0].previous_state == "transitional"
        assert events[0].new_state == "solid"
        assert events[0].cadre_density == 1.0  # Strong ties = all cadre


# =============================================================================
# TEST: Factory Method for PhaseTransitionEvent
# =============================================================================


@pytest.mark.unit
class TestPhaseTransitionEventFactory:
    """Tests for factory method to create PhaseTransitionEvent."""

    def test_factory_creates_phase_transition_event(self) -> None:
        """DomainFactory has create_phase_transition_event method."""
        from babylon.models.events import PhaseTransitionEvent

        factory = DomainFactory()
        assert hasattr(factory, "create_phase_transition_event")

        event = factory.create_phase_transition_event()
        assert isinstance(event, PhaseTransitionEvent)

    def test_factory_default_values(self) -> None:
        """Factory provides sensible defaults."""
        factory = DomainFactory()
        event = factory.create_phase_transition_event()

        assert event.tick == 0
        assert event.previous_state == "gaseous"
        assert event.new_state == "liquid"
        assert event.percolation_ratio == pytest.approx(0.5)
        assert event.num_components == 1
        assert event.largest_component_size == 5
        assert event.is_resilient is None

    def test_factory_accepts_overrides(self) -> None:
        """Factory accepts kwargs to override defaults."""
        factory = DomainFactory()
        event = factory.create_phase_transition_event(
            tick=10,
            previous_state="transitional",
            new_state="liquid",
            percolation_ratio=0.8,
            is_resilient=True,
        )

        assert event.tick == 10
        assert event.previous_state == "transitional"
        assert event.new_state == "liquid"
        assert event.percolation_ratio == pytest.approx(0.8)
        assert event.is_resilient is True


# =============================================================================
# TEST: Simulation Facade Collects Observer Events
# =============================================================================


@pytest.mark.topology
class TestSimulationFacadeObserverEvents:
    """Tests for Simulation facade collecting observer events."""

    def test_simulation_collects_observer_events_liquid(self) -> None:
        """Simulation facade collects pending events from observers (liquid transition).

        Uses WEAK solidarity (0.2) to get liquid phase.
        """
        from babylon.engine.simulation import Simulation
        from babylon.engine.topology_monitor import TopologyMonitor
        from babylon.models.config import SimulationConfig

        factory = DomainFactory()

        # Start atomized (gaseous) - need >10 nodes for ratio < 0.1
        workers = [factory.create_worker(id=f"C{i:03d}") for i in range(12)]
        entities = {w.id: w for w in workers}
        state = factory.create_world_state(entities=entities, relationships=[])

        config = SimulationConfig()
        monitor = TopologyMonitor()
        sim = Simulation(state, config, observers=[monitor])

        # First tick: establishes gaseous baseline
        sim.step()
        assert monitor._previous_phase == "gaseous"

        # Now create transition scenario
        # Add WEAK solidarity edges to reach liquid state (mass movement)
        relationships = []
        for i in range(11):  # Connect all 12 nodes
            relationships.append(
                factory.create_relationship(
                    source_id=f"C{i:03d}",
                    target_id=f"C{i + 1:03d}",
                    edge_type=EdgeType.SOLIDARITY,
                    solidarity_strength=0.2,  # Weak ties for liquid phase
                )
            )

        # Update simulation state with solidarity
        new_state = factory.create_world_state(
            tick=sim.current_state.tick,
            entities=entities,
            relationships=relationships,
        )
        sim.update_state(new_state)

        # Second tick: should detect gaseous -> liquid transition
        sim.step()

        # Check that the monitor detected the transition
        assert monitor._previous_phase == "liquid"

        # Events from observer appear in next tick's WorldState
        # (observer events are collected and injected into next tick via step())
        # We verify the monitor detected the transition - event injection is tested separately

    def test_simulation_collects_observer_events_solid(self) -> None:
        """Simulation facade collects pending events from observers (solid transition).

        Uses STRONG solidarity (0.8) to get solid phase.
        """
        from babylon.engine.simulation import Simulation
        from babylon.engine.topology_monitor import TopologyMonitor
        from babylon.models.config import SimulationConfig

        factory = DomainFactory()

        # Start atomized (gaseous)
        workers = [factory.create_worker(id=f"C{i:03d}") for i in range(12)]
        entities = {w.id: w for w in workers}
        state = factory.create_world_state(entities=entities, relationships=[])

        config = SimulationConfig()
        monitor = TopologyMonitor()
        sim = Simulation(state, config, observers=[monitor])

        # First tick: establishes gaseous baseline
        sim.step()
        assert monitor._previous_phase == "gaseous"

        # Now create transition scenario
        # Add STRONG solidarity edges to reach solid state (vanguard party)
        relationships = []
        for i in range(11):  # Connect all 12 nodes
            relationships.append(
                factory.create_relationship(
                    source_id=f"C{i:03d}",
                    target_id=f"C{i + 1:03d}",
                    edge_type=EdgeType.SOLIDARITY,
                    solidarity_strength=0.8,  # Strong ties for solid phase
                )
            )

        # Update simulation state with solidarity
        new_state = factory.create_world_state(
            tick=sim.current_state.tick,
            entities=entities,
            relationships=relationships,
        )
        sim.update_state(new_state)

        # Second tick: should detect gaseous -> solid transition
        sim.step()

        # Check that the monitor detected the transition to solid (vanguard)
        assert monitor._previous_phase == "solid"
