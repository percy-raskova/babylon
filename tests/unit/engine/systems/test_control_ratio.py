"""Tests for ControlRatioSystem - Terminal Crisis Dynamics Phase 5.

The Control Ratio tracks the guard:prisoner ratio. When enforcers can't
control the prisoner population (prisoners > enforcers × CONTROL_CAPACITY),
a CONTROL_RATIO_CRISIS occurs, triggering the terminal decision.

User specification: 1:20 ratio (1 guard can control 20 prisoners).

This models the mathematical limit of incarceration as surplus population
management. When the carceral state can't contain the surplus, the system
must choose between revolution (if organized) or genocide (if not).

See ai-docs/terminal-crisis-dynamics.md for full theory.
"""

from __future__ import annotations

from collections.abc import Generator

import networkx as nx
import pytest

from babylon.engine.event_bus import Event
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.control_ratio import ControlRatioSystem
from babylon.models.enums import EventType, SocialRole


@pytest.fixture
def services() -> Generator[ServiceContainer, None, None]:
    """Create a ServiceContainer for testing."""
    container = ServiceContainer.create()
    yield container
    container.database.close()


def _create_stable_carceral_state(graph: nx.DiGraph[str]) -> None:
    """Create a carceral state where enforcers control the population.

    With CONTROL_CAPACITY = 20:
    - 100 enforcers can control 2000 prisoners
    - We'll have 100 enforcers and 1500 prisoners (within capacity)
    """
    # Carceral enforcers
    graph.add_node(
        "Enforcer",
        role=SocialRole.CARCERAL_ENFORCER,
        wealth=500.0,
        population=100,
        active=True,
        organization=0.2,
        _node_type="social_class",
    )

    # Internal proletariat (prisoners/precariat)
    graph.add_node(
        "Int_P",
        role=SocialRole.INTERNAL_PROLETARIAT,
        wealth=50.0,
        population=1500,  # 100 * 20 = 2000 capacity, 1500 is within
        active=True,
        organization=0.3,
        _node_type="social_class",
    )

    # Lumpenproletariat (also counted as prisoners)
    graph.add_node(
        "Lumpen",
        role=SocialRole.LUMPENPROLETARIAT,
        wealth=20.0,
        population=300,  # Total prisoners = 1500 + 300 = 1800, still < 2000
        active=True,
        organization=0.1,
        _node_type="social_class",
    )


def _create_unstable_carceral_state(graph: nx.DiGraph[str]) -> None:
    """Create a carceral state where prisoners exceed control capacity.

    With CONTROL_CAPACITY = 20:
    - 100 enforcers can control 2000 prisoners
    - We'll have 100 enforcers and 2500 prisoners (exceeds capacity)
    """
    # Carceral enforcers
    graph.add_node(
        "Enforcer",
        role=SocialRole.CARCERAL_ENFORCER,
        wealth=500.0,
        population=100,
        active=True,
        organization=0.2,
        _node_type="social_class",
    )

    # Internal proletariat (prisoners/precariat)
    graph.add_node(
        "Int_P",
        role=SocialRole.INTERNAL_PROLETARIAT,
        wealth=50.0,
        population=2000,  # 100 * 20 = 2000 capacity, we have more
        active=True,
        organization=0.3,  # Medium organization
        _node_type="social_class",
    )

    # Lumpenproletariat
    graph.add_node(
        "Lumpen",
        role=SocialRole.LUMPENPROLETARIAT,
        wealth=20.0,
        population=500,  # Total prisoners = 2000 + 500 = 2500, exceeds 2000
        active=True,
        organization=0.2,
        _node_type="social_class",
    )


@pytest.mark.unit
class TestControlRatioSystem:
    """ControlRatioSystem tracks guard:prisoner ratio and triggers crisis."""

    def test_no_crisis_when_within_capacity(self, services: ServiceContainer) -> None:
        """No CONTROL_RATIO_CRISIS when enforcers can control prisoners."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_stable_carceral_state(graph)

        captured_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.CONTROL_RATIO_CRISIS,
            lambda e: captured_events.append(e),
        )

        system = ControlRatioSystem()
        system.step(graph, services, {"tick": 1})

        assert len(captured_events) == 0, "No crisis when within capacity"

    def test_crisis_when_exceeds_capacity(self, services: ServiceContainer) -> None:
        """CONTROL_RATIO_CRISIS emitted when prisoners > enforcers × capacity."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_unstable_carceral_state(graph)

        captured_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.CONTROL_RATIO_CRISIS,
            lambda e: captured_events.append(e),
        )

        system = ControlRatioSystem()
        system.step(graph, services, {"tick": 1})

        assert len(captured_events) == 1, "Should emit CONTROL_RATIO_CRISIS"
        event = captured_events[0]
        assert event.payload["enforcer_population"] == 100
        assert event.payload["prisoner_population"] == 2500
        assert event.payload["control_capacity"] == 20
        assert event.payload["max_controllable"] == 2000  # 100 * 20

    def test_crisis_includes_ratio_calculation(self, services: ServiceContainer) -> None:
        """Crisis event includes the actual ratio for narrative layer."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_unstable_carceral_state(graph)

        captured_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.CONTROL_RATIO_CRISIS,
            lambda e: captured_events.append(e),
        )

        system = ControlRatioSystem()
        system.step(graph, services, {"tick": 1})

        event = captured_events[0]
        # Actual ratio: 2500 / 100 = 25:1 (capacity is 20:1)
        assert event.payload["actual_ratio"] == pytest.approx(25.0)
        assert event.payload["over_capacity_by"] == 500  # 2500 - 2000

    def test_inactive_entities_not_counted(self, services: ServiceContainer) -> None:
        """Inactive (dead) entities don't count toward population."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_unstable_carceral_state(graph)

        # Mark the lumpen as inactive
        graph.nodes["Lumpen"]["active"] = False

        # Now we have 2000 prisoners, 100 enforcers
        # Capacity = 100 * 20 = 2000, exactly at capacity (no crisis)

        captured_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.CONTROL_RATIO_CRISIS,
            lambda e: captured_events.append(e),
        )

        system = ControlRatioSystem()
        system.step(graph, services, {"tick": 1})

        # At exactly capacity - no crisis (need to EXCEED)
        assert len(captured_events) == 0

    def test_no_enforcers_triggers_immediate_crisis(self, services: ServiceContainer) -> None:
        """If no enforcers exist, any prisoners trigger crisis."""
        graph: nx.DiGraph[str] = nx.DiGraph()

        # Only prisoners, no enforcers
        graph.add_node(
            "Int_P",
            role=SocialRole.INTERNAL_PROLETARIAT,
            wealth=50.0,
            population=100,  # Any positive number
            active=True,
            organization=0.5,
            _node_type="social_class",
        )

        captured_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.CONTROL_RATIO_CRISIS,
            lambda e: captured_events.append(e),
        )

        system = ControlRatioSystem()
        system.step(graph, services, {"tick": 1})

        assert len(captured_events) == 1
        event = captured_events[0]
        assert event.payload["enforcer_population"] == 0
        assert event.payload["control_capacity"] == 20

    def test_no_prisoners_no_crisis(self, services: ServiceContainer) -> None:
        """No crisis if there are no prisoners to control."""
        graph: nx.DiGraph[str] = nx.DiGraph()

        # Only enforcers, no prisoners
        graph.add_node(
            "Enforcer",
            role=SocialRole.CARCERAL_ENFORCER,
            wealth=500.0,
            population=100,
            active=True,
            _node_type="social_class",
        )

        captured_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.CONTROL_RATIO_CRISIS,
            lambda e: captured_events.append(e),
        )

        system = ControlRatioSystem()
        system.step(graph, services, {"tick": 1})

        assert len(captured_events) == 0, "No prisoners = no crisis"

    def test_crisis_includes_narrative_hint(self, services: ServiceContainer) -> None:
        """CONTROL_RATIO_CRISIS includes narrative for AI observer."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_unstable_carceral_state(graph)

        captured_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.CONTROL_RATIO_CRISIS,
            lambda e: captured_events.append(e),
        )

        system = ControlRatioSystem()
        system.step(graph, services, {"tick": 1})

        assert len(captured_events) == 1
        assert "narrative_hint" in captured_events[0].payload


@pytest.mark.unit
class TestTerminalDecision:
    """Terminal decision triggered when control ratio inverts."""

    def test_revolution_when_high_organization(self, services: ServiceContainer) -> None:
        """TERMINAL_DECISION outcome='revolution' when prisoners organized.

        When average prisoner organization exceeds threshold (default 0.5),
        prisoners and guards unite in revolution.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()

        # High-org enforcers
        graph.add_node(
            "Enforcer",
            role=SocialRole.CARCERAL_ENFORCER,
            wealth=500.0,
            population=100,
            active=True,
            organization=0.6,  # Guards also organized!
            _node_type="social_class",
        )

        # High-org prisoners
        graph.add_node(
            "Int_P",
            role=SocialRole.INTERNAL_PROLETARIAT,
            wealth=50.0,
            population=2500,  # Exceeds capacity
            active=True,
            organization=0.7,  # High organization
            _node_type="social_class",
        )

        captured_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.TERMINAL_DECISION,
            lambda e: captured_events.append(e),
        )

        system = ControlRatioSystem()
        system.step(graph, services, {"tick": 1})

        assert len(captured_events) == 1
        event = captured_events[0]
        assert event.payload["outcome"] == "revolution"
        assert event.payload["avg_organization"] >= 0.5

    def test_genocide_when_low_organization(self, services: ServiceContainer) -> None:
        """TERMINAL_DECISION outcome='genocide' when prisoners disorganized.

        When average organization is below threshold, the system turns
        genocidal to eliminate surplus population.
        """
        graph: nx.DiGraph[str] = nx.DiGraph()

        # Enforcers
        graph.add_node(
            "Enforcer",
            role=SocialRole.CARCERAL_ENFORCER,
            wealth=500.0,
            population=100,
            active=True,
            organization=0.2,  # Low org guards
            _node_type="social_class",
        )

        # Low-org prisoners
        graph.add_node(
            "Int_P",
            role=SocialRole.INTERNAL_PROLETARIAT,
            wealth=50.0,
            population=2500,  # Exceeds capacity
            active=True,
            organization=0.2,  # Low organization - atomized
            _node_type="social_class",
        )

        captured_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.TERMINAL_DECISION,
            lambda e: captured_events.append(e),
        )

        system = ControlRatioSystem()
        system.step(graph, services, {"tick": 1})

        assert len(captured_events) == 1
        event = captured_events[0]
        assert event.payload["outcome"] == "genocide"
        assert event.payload["avg_organization"] < 0.5

    def test_terminal_decision_includes_narrative_hint(self, services: ServiceContainer) -> None:
        """TERMINAL_DECISION includes narrative hint for AI observer."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_unstable_carceral_state(graph)

        captured_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.TERMINAL_DECISION,
            lambda e: captured_events.append(e),
        )

        system = ControlRatioSystem()
        system.step(graph, services, {"tick": 1})

        assert len(captured_events) == 1
        assert "narrative_hint" in captured_events[0].payload

    def test_no_terminal_decision_when_no_crisis(self, services: ServiceContainer) -> None:
        """TERMINAL_DECISION only emitted during control ratio crisis."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_stable_carceral_state(graph)  # Within capacity

        captured_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.TERMINAL_DECISION,
            lambda e: captured_events.append(e),
        )

        system = ControlRatioSystem()
        system.step(graph, services, {"tick": 1})

        assert len(captured_events) == 0, "No crisis = no terminal decision"

    def test_terminal_decision_considers_all_prisoner_classes(
        self, services: ServiceContainer
    ) -> None:
        """Organization average includes both Int_P and Lumpen."""
        graph: nx.DiGraph[str] = nx.DiGraph()

        # Enforcers
        graph.add_node(
            "Enforcer",
            role=SocialRole.CARCERAL_ENFORCER,
            wealth=500.0,
            population=100,
            active=True,
            organization=0.3,
            _node_type="social_class",
        )

        # High-org internal proletariat (larger pop)
        graph.add_node(
            "Int_P",
            role=SocialRole.INTERNAL_PROLETARIAT,
            wealth=50.0,
            population=2000,
            active=True,
            organization=0.6,  # 2000 * 0.6 = 1200 "org units"
            _node_type="social_class",
        )

        # Low-org lumpen (smaller pop)
        graph.add_node(
            "Lumpen",
            role=SocialRole.LUMPENPROLETARIAT,
            wealth=20.0,
            population=500,
            active=True,
            organization=0.2,  # 500 * 0.2 = 100 "org units"
            _node_type="social_class",
        )

        # Total prisoners: 2500 (exceeds 100 * 20 = 2000 capacity)
        # Weighted avg org: (1200 + 100) / 2500 = 0.52 (revolution!)

        captured_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.TERMINAL_DECISION,
            lambda e: captured_events.append(e),
        )

        system = ControlRatioSystem()
        system.step(graph, services, {"tick": 1})

        event = captured_events[0]
        assert event.payload["outcome"] == "revolution"
        # Weighted average: (2000*0.6 + 500*0.2) / 2500 = 0.52
        assert event.payload["avg_organization"] == pytest.approx(0.52)
