"""Tests for ControlRatioSystem - Terminal Crisis Dynamics Phase 5.

The Control Ratio tracks the guard:prisoner ratio. When enforcers can't
control the prisoner population (prisoners > enforcers × control_capacity),
a CONTROL_RATIO_CRISIS occurs, triggering the terminal decision.

Default: 1:4 ratio (tunable via GameDefines.carceral.control_capacity).
Real-world: US average ~4:1, Federal baseline 15:1, crisis >200:1.

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


def _create_test_context(
    tick: int = 1,
    *,
    include_crisis_tick: bool = False,
) -> dict[str, object]:
    """Create a test context with required persistent data.

    The ControlRatioSystem requires _class_decomposition_tick to know when
    to start checking the control ratio. For raw dict contexts, persistent
    data is stored directly in the dict (not nested).

    We set _class_decomposition_tick to a tick in the past so the system
    runs immediately (control_ratio_delay default is 52).

    Args:
        tick: Current tick number.
        include_crisis_tick: If True, also set _control_ratio_crisis_tick
            so TERMINAL_DECISION fires immediately.
    """
    context: dict[str, object] = {
        "tick": tick,
        "_class_decomposition_tick": tick - 100,  # Decomposition happened 100 ticks ago
    }
    if include_crisis_tick:
        # Crisis happened in the past, so terminal decision can fire now
        context["_control_ratio_crisis_tick"] = tick - 10
        context["_control_crisis_emitted"] = True  # Prevent re-emitting crisis
    return context


def _create_stable_carceral_state(graph: nx.DiGraph[str]) -> None:
    """Create a carceral state where enforcers control the population.

    With default control_capacity = 4 (from GameDefines):
    - 100 enforcers can control 400 prisoners
    - We'll have 100 enforcers and 350 prisoners (within capacity)
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
        population=250,  # 100 * 4 = 400 capacity, 250 is within
        active=True,
        organization=0.3,
        _node_type="social_class",
    )

    # Lumpenproletariat (also counted as prisoners)
    graph.add_node(
        "Lumpen",
        role=SocialRole.LUMPENPROLETARIAT,
        wealth=20.0,
        population=100,  # Total prisoners = 250 + 100 = 350, still < 400
        active=True,
        organization=0.1,
        _node_type="social_class",
    )


def _create_unstable_carceral_state(graph: nx.DiGraph[str]) -> None:
    """Create a carceral state where prisoners exceed control capacity.

    With default control_capacity = 4 (from GameDefines):
    - 100 enforcers can control 400 prisoners
    - We'll have 100 enforcers and 500 prisoners (exceeds capacity)
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
        population=350,  # 100 * 4 = 400 capacity, we exceed that
        active=True,
        organization=0.3,  # Medium organization
        _node_type="social_class",
    )

    # Lumpenproletariat
    graph.add_node(
        "Lumpen",
        role=SocialRole.LUMPENPROLETARIAT,
        wealth=20.0,
        population=150,  # Total prisoners = 350 + 150 = 500, exceeds 400
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
        system.step(graph, services, _create_test_context())

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
        system.step(graph, services, _create_test_context())

        assert len(captured_events) == 1, "Should emit CONTROL_RATIO_CRISIS"
        event = captured_events[0]
        assert event.payload["enforcer_population"] == 100
        assert event.payload["prisoner_population"] == 500  # 350 Int_P + 150 Lumpen
        assert event.payload["control_capacity"] == 4  # GameDefines default
        assert event.payload["max_controllable"] == 400  # 100 * 4

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
        system.step(graph, services, _create_test_context())

        event = captured_events[0]
        # Actual ratio: 500 / 100 = 5:1 (capacity is 4:1)
        assert event.payload["actual_ratio"] == pytest.approx(5.0)
        assert event.payload["over_capacity_by"] == 100  # 500 - 400

    def test_inactive_entities_not_counted(self, services: ServiceContainer) -> None:
        """Inactive (dead) entities don't count toward population."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_unstable_carceral_state(graph)

        # Mark the lumpen as inactive
        graph.nodes["Lumpen"]["active"] = False

        # Now we have 350 prisoners, 100 enforcers
        # Capacity = 100 * 4 = 400, 350 < 400 (no crisis)

        captured_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.CONTROL_RATIO_CRISIS,
            lambda e: captured_events.append(e),
        )

        system = ControlRatioSystem()
        system.step(graph, services, _create_test_context())

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
        system.step(graph, services, _create_test_context())

        assert len(captured_events) == 1
        event = captured_events[0]
        assert event.payload["enforcer_population"] == 0
        assert event.payload["control_capacity"] == 4  # GameDefines default

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
        system.step(graph, services, _create_test_context())

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
        system.step(graph, services, _create_test_context())

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
        system.step(graph, services, _create_test_context(include_crisis_tick=True))

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
        system.step(graph, services, _create_test_context(include_crisis_tick=True))

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
        system.step(graph, services, _create_test_context(include_crisis_tick=True))

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
        system.step(graph, services, _create_test_context())

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

        # Total prisoners: 2500 (exceeds 100 * 4 = 400 capacity)
        # Weighted avg org: (1200 + 100) / 2500 = 0.52 (revolution!)

        captured_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.TERMINAL_DECISION,
            lambda e: captured_events.append(e),
        )

        system = ControlRatioSystem()
        system.step(graph, services, _create_test_context(include_crisis_tick=True))

        event = captured_events[0]
        assert event.payload["outcome"] == "revolution"
        # Weighted average: (2000*0.6 + 500*0.2) / 2500 = 0.52
        assert event.payload["avg_organization"] == pytest.approx(0.52)


@pytest.mark.topology
class TestControlRatioMutationKillers:
    """Targeted tests to kill mutation survivors in ControlRatioSystem.step."""

    def test_exactly_at_capacity_no_crisis(self, services: ServiceContainer) -> None:
        """prisoners == enforcers * capacity → no crisis (tests <= boundary)."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        # 100 enforcers * 4 capacity = 400 max; prisoners exactly 400
        graph.add_node(
            "Enforcer",
            role=SocialRole.CARCERAL_ENFORCER,
            population=100,
            active=True,
            _node_type="social_class",
        )
        graph.add_node(
            "Int_P",
            role=SocialRole.INTERNAL_PROLETARIAT,
            population=400,
            active=True,
            organization=0.5,
            _node_type="social_class",
        )

        captured: list[Event] = []
        services.event_bus.subscribe(EventType.CONTROL_RATIO_CRISIS, lambda e: captured.append(e))

        system = ControlRatioSystem()
        system.step(graph, services, _create_test_context())

        assert len(captured) == 0, "Exactly at capacity → no crisis"

    def test_one_over_capacity_triggers_crisis(self, services: ServiceContainer) -> None:
        """prisoners == enforcers * capacity + 1 → crisis (tests <= vs <)."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        # 100 enforcers * 4 = 400 max; prisoners = 401
        graph.add_node(
            "Enforcer",
            role=SocialRole.CARCERAL_ENFORCER,
            population=100,
            active=True,
            _node_type="social_class",
        )
        graph.add_node(
            "Int_P",
            role=SocialRole.INTERNAL_PROLETARIAT,
            population=401,
            active=True,
            organization=0.5,
            _node_type="social_class",
        )

        captured: list[Event] = []
        services.event_bus.subscribe(EventType.CONTROL_RATIO_CRISIS, lambda e: captured.append(e))

        system = ControlRatioSystem()
        system.step(graph, services, _create_test_context())

        assert len(captured) == 1, "One over capacity → crisis"
        assert captured[0].payload["over_capacity_by"] == 1

    def test_delay_gate_blocks_early(self, services: ServiceContainer) -> None:
        """tick < decomp_tick + delay → return early (no processing)."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_unstable_carceral_state(graph)

        captured: list[Event] = []
        services.event_bus.subscribe(EventType.CONTROL_RATIO_CRISIS, lambda e: captured.append(e))

        delay = services.defines.carceral.control_ratio_delay  # 52
        # decomp at tick 10, delay=52, so need tick >= 62 to process
        context: dict[str, object] = {
            "tick": 10 + delay - 1,  # tick=61, just before threshold
            "_class_decomposition_tick": 10,
        }

        system = ControlRatioSystem()
        system.step(graph, services, context)

        assert len(captured) == 0, "Delay gate blocks early tick"

    def test_delay_gate_opens_exactly(self, services: ServiceContainer) -> None:
        """tick == decomp_tick + delay → processes (tests < vs <=)."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_unstable_carceral_state(graph)

        captured: list[Event] = []
        services.event_bus.subscribe(EventType.CONTROL_RATIO_CRISIS, lambda e: captured.append(e))

        delay = services.defines.carceral.control_ratio_delay  # 52
        context: dict[str, object] = {
            "tick": 10 + delay,  # tick=62, exactly at threshold
            "_class_decomposition_tick": 10,
        }

        system = ControlRatioSystem()
        system.step(graph, services, context)

        assert len(captured) == 1, "Delay gate opens at exact tick"

    def test_terminal_delay_blocks(self, services: ServiceContainer) -> None:
        """tick == crisis_tick → terminal delay blocks (needs crisis_tick + delay)."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_unstable_carceral_state(graph)

        terminal_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.TERMINAL_DECISION, lambda e: terminal_events.append(e)
        )

        tick = 100
        context: dict[str, object] = {
            "tick": tick,
            "_class_decomposition_tick": tick - 100,
            "_control_ratio_crisis_tick": tick,  # Crisis just happened
            "_control_crisis_emitted": True,
        }

        system = ControlRatioSystem()
        system.step(graph, services, context)

        # tick=100 < crisis_tick(100) + delay(1) = 101 → blocks
        assert len(terminal_events) == 0, "Terminal delay blocks at crisis_tick"

    def test_terminal_delay_fires(self, services: ServiceContainer) -> None:
        """tick == crisis_tick + terminal_delay → fires terminal decision."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_unstable_carceral_state(graph)

        terminal_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.TERMINAL_DECISION, lambda e: terminal_events.append(e)
        )

        terminal_delay = services.defines.carceral.terminal_decision_delay  # 1
        crisis_tick = 100
        context: dict[str, object] = {
            "tick": crisis_tick + terminal_delay,  # tick=101
            "_class_decomposition_tick": 0,
            "_control_ratio_crisis_tick": crisis_tick,
            "_control_crisis_emitted": True,
        }

        system = ControlRatioSystem()
        system.step(graph, services, context)

        assert len(terminal_events) == 1, "Terminal fires at crisis_tick + delay"

    def test_crisis_emitted_once_on_repeated_steps(self, services: ServiceContainer) -> None:
        """Step twice at same unstable state → only 1 crisis event total."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_unstable_carceral_state(graph)

        captured: list[Event] = []
        services.event_bus.subscribe(EventType.CONTROL_RATIO_CRISIS, lambda e: captured.append(e))

        system = ControlRatioSystem()
        context = _create_test_context(tick=200)
        system.step(graph, services, context)
        assert len(captured) == 1

        # Step again — crisis flag should prevent re-emission
        context["tick"] = 201
        system.step(graph, services, context)
        assert len(captured) == 1, "Crisis emitted only once"

    def test_terminal_emitted_flag_causes_early_return(self, services: ServiceContainer) -> None:
        """_terminal_decision_emitted=True → immediate return, no processing."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        _create_unstable_carceral_state(graph)

        crisis_events: list[Event] = []
        terminal_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.CONTROL_RATIO_CRISIS, lambda e: crisis_events.append(e)
        )
        services.event_bus.subscribe(
            EventType.TERMINAL_DECISION, lambda e: terminal_events.append(e)
        )

        context: dict[str, object] = {
            "tick": 200,
            "_class_decomposition_tick": 0,
            "_terminal_decision_emitted": True,  # Already fired
        }

        system = ControlRatioSystem()
        system.step(graph, services, context)

        assert len(crisis_events) == 0, "No crisis when terminal already emitted"
        assert len(terminal_events) == 0, "No terminal re-emission"

    def test_avg_organization_exact_calculation(self, services: ServiceContainer) -> None:
        """Weighted avg org = sum(pop*org) / total_pop, verify exact value."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "Enforcer",
            role=SocialRole.CARCERAL_ENFORCER,
            population=10,
            active=True,
            _node_type="social_class",
        )
        # Pop=300, org=0.8 → weighted=240
        graph.add_node(
            "Int_P",
            role=SocialRole.INTERNAL_PROLETARIAT,
            population=300,
            active=True,
            organization=0.8,
            _node_type="social_class",
        )
        # Pop=200, org=0.3 → weighted=60
        graph.add_node(
            "Lumpen",
            role=SocialRole.LUMPENPROLETARIAT,
            population=200,
            active=True,
            organization=0.3,
            _node_type="social_class",
        )
        # Total pop=500, org_sum=300, avg=300/500=0.6

        terminal_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.TERMINAL_DECISION, lambda e: terminal_events.append(e)
        )

        system = ControlRatioSystem()
        system.step(graph, services, _create_test_context(include_crisis_tick=True))

        assert len(terminal_events) == 1
        assert terminal_events[0].payload["avg_organization"] == pytest.approx(0.6)

    def test_revolution_at_exact_threshold(self, services: ServiceContainer) -> None:
        """avg_org == revolution_threshold (0.5) → revolution (>= boundary)."""
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node(
            "Enforcer",
            role=SocialRole.CARCERAL_ENFORCER,
            population=10,
            active=True,
            _node_type="social_class",
        )
        # All prisoners with org=0.5 exactly
        graph.add_node(
            "Int_P",
            role=SocialRole.INTERNAL_PROLETARIAT,
            population=500,
            active=True,
            organization=0.5,
            _node_type="social_class",
        )

        terminal_events: list[Event] = []
        services.event_bus.subscribe(
            EventType.TERMINAL_DECISION, lambda e: terminal_events.append(e)
        )

        system = ControlRatioSystem()
        system.step(graph, services, _create_test_context(include_crisis_tick=True))

        assert len(terminal_events) == 1
        assert terminal_events[0].payload["outcome"] == "revolution"
        assert terminal_events[0].payload["avg_organization"] == pytest.approx(0.5)
