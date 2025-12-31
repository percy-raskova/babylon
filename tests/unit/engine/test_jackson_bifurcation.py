"""Unit tests for George Jackson Bifurcation Logic.

TDD tests for the Power Vacuum scenario in the Imperial Circuit.
When the Comprador becomes insolvent (wealth < subsistence_threshold),
a bifurcation occurs based on the Periphery Proletariat's revolutionary
capacity (organization * class_consciousness).

Outcomes:
- capacity >= JACKSON_THRESHOLD (0.4): Revolutionary Offensive
- capacity < JACKSON_THRESHOLD: Fascist Revanchism

These tests are written BEFORE implementation (RED phase of TDD).
"""

from __future__ import annotations

import random
from collections.abc import Generator
from typing import TYPE_CHECKING

import networkx as nx
import pytest

from babylon.config.defines import GameDefines, StruggleDefines
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.struggle import StruggleSystem
from babylon.models.enums import EventType, SocialRole

if TYPE_CHECKING:
    from babylon.engine.event_bus import Event


@pytest.fixture
def services() -> Generator[ServiceContainer, None, None]:
    """Create a ServiceContainer for testing."""
    container = ServiceContainer.create()
    yield container
    container.database.close()


@pytest.fixture
def seeded_random() -> Generator[None, None, None]:
    """Seed random for deterministic tests."""
    random.seed(42)
    yield
    # No cleanup needed - random state persists


def _create_test_graph(
    comprador_wealth: float = 2.0,
    comprador_subsistence: float = 5.0,
    p_w_organization: float = 0.5,
    p_w_class_consciousness: float = 0.5,
    include_core_worker: bool = True,
    c_w_national_identity: float = 0.3,
    c_w_p_acquiescence: float = 0.4,
) -> nx.DiGraph:
    """Create a test graph with Comprador, Periphery Proletariat, and optionally Core Worker.

    Args:
        comprador_wealth: Comprador's current wealth.
        comprador_subsistence: Comprador's subsistence threshold.
        p_w_organization: Periphery worker's organization level.
        p_w_class_consciousness: Periphery worker's class consciousness.
        include_core_worker: Whether to include a Labor Aristocracy node.
        c_w_national_identity: Core worker's national identity.
        c_w_p_acquiescence: Core worker's acquiescence probability.

    Returns:
        NetworkX DiGraph with test entities.
    """
    graph: nx.DiGraph = nx.DiGraph()

    # Comprador Bourgeoisie (p_c)
    graph.add_node(
        "C001",
        role=SocialRole.COMPRADOR_BOURGEOISIE,
        wealth=comprador_wealth,
        subsistence_threshold=comprador_subsistence,
        _node_type="entity",
    )

    # Periphery Proletariat (p_w)
    graph.add_node(
        "C002",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=10.0,
        organization=p_w_organization,
        ideology={
            "class_consciousness": p_w_class_consciousness,
            "national_identity": 0.3,
            "agitation": 0.1,
        },
        p_revolution=0.2,
        p_acquiescence=0.5,
        repression_faced=0.01,  # Very low repression to avoid spark interference
        _node_type="entity",
    )

    # Labor Aristocracy / Core Worker (c_w)
    if include_core_worker:
        graph.add_node(
            "C003",
            role=SocialRole.LABOR_ARISTOCRACY,
            wealth=50.0,
            organization=0.1,
            ideology={
                "class_consciousness": 0.1,
                "national_identity": c_w_national_identity,
                "agitation": 0.0,
            },
            p_revolution=0.05,
            p_acquiescence=c_w_p_acquiescence,
            repression_faced=0.01,
            _node_type="entity",
        )

    return graph


def _create_services_with_defines(defines: GameDefines) -> ServiceContainer:
    """Create a ServiceContainer with custom defines for testing."""
    return ServiceContainer.create(defines=defines)


@pytest.mark.unit
class TestPowerVacuumTrigger:
    """Tests for when POWER_VACUUM event should be emitted."""

    def test_power_vacuum_triggers_on_comprador_insolvency(
        self, services: ServiceContainer, seeded_random: None
    ) -> None:
        """POWER_VACUUM emitted when comprador wealth < subsistence_threshold."""
        # Arrange: Comprador is INSOLVENT (wealth=2.0 < subsistence=5.0)
        graph = _create_test_graph(
            comprador_wealth=2.0,
            comprador_subsistence=5.0,
            p_w_organization=0.5,
            p_w_class_consciousness=0.5,
        )
        context = {"tick": 1}

        # Collect events
        events: list[Event] = []
        services.event_bus.subscribe(EventType.POWER_VACUUM, events.append)

        # Act
        system = StruggleSystem()
        system.step(graph, services, context)

        # Assert: POWER_VACUUM event emitted
        assert len(events) == 1, f"Expected 1 POWER_VACUUM event, got {len(events)}"
        event = events[0]
        assert event.payload["comprador_id"] == "C001"
        assert event.payload["comprador_wealth"] == 2.0
        assert event.payload["subsistence_threshold"] == 5.0

    def test_no_power_vacuum_when_comprador_solvent(
        self, services: ServiceContainer, seeded_random: None
    ) -> None:
        """No POWER_VACUUM when comprador wealth >= subsistence_threshold."""
        # Arrange: Comprador is SOLVENT (wealth=10.0 > subsistence=5.0)
        graph = _create_test_graph(
            comprador_wealth=10.0,
            comprador_subsistence=5.0,
        )
        context = {"tick": 1}

        events: list[Event] = []
        services.event_bus.subscribe(EventType.POWER_VACUUM, events.append)

        # Act
        system = StruggleSystem()
        system.step(graph, services, context)

        # Assert: No POWER_VACUUM event
        assert len(events) == 0, f"Expected no events, got {len(events)}"

    def test_no_power_vacuum_without_comprador(
        self, services: ServiceContainer, seeded_random: None
    ) -> None:
        """No POWER_VACUUM when there is no Comprador entity."""
        graph: nx.DiGraph = nx.DiGraph()
        # Only add a periphery proletariat, no comprador
        graph.add_node(
            "C001",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=10.0,
            organization=0.5,
            ideology={"class_consciousness": 0.5, "national_identity": 0.3, "agitation": 0.1},
            repression_faced=0.01,
            _node_type="entity",
        )

        context = {"tick": 1}

        events: list[Event] = []
        services.event_bus.subscribe(EventType.POWER_VACUUM, events.append)

        system = StruggleSystem()
        system.step(graph, services, context)

        assert len(events) == 0


@pytest.mark.unit
class TestRevolutionaryOffensive:
    """Tests for Revolutionary Offensive outcome (capacity >= JACKSON_THRESHOLD)."""

    def test_revolutionary_offensive_when_capacity_above_threshold(
        self, services: ServiceContainer, seeded_random: None
    ) -> None:
        """Revolutionary Offensive when organization * consciousness >= 0.4."""
        # Arrange: capacity = 0.8 * 0.6 = 0.48 >= 0.4
        graph = _create_test_graph(
            comprador_wealth=2.0,
            comprador_subsistence=5.0,
            p_w_organization=0.8,
            p_w_class_consciousness=0.6,
        )
        context = {"tick": 1}

        events: list[Event] = []
        services.event_bus.subscribe(EventType.REVOLUTIONARY_OFFENSIVE, events.append)

        # Act
        system = StruggleSystem()
        system.step(graph, services, context)

        # Assert: REVOLUTIONARY_OFFENSIVE event emitted
        assert len(events) == 1, f"Expected 1 REVOLUTIONARY_OFFENSIVE, got {len(events)}"
        event = events[0]
        assert event.payload["periphery_id"] == "C002"
        assert event.payload["revolutionary_capacity"] == pytest.approx(0.48)
        assert "narrative_hint" in event.payload

    def test_p_revolution_set_to_one_on_revolutionary_offensive(
        self, services: ServiceContainer, seeded_random: None
    ) -> None:
        """p_w.p_revolution = 1.0 during Revolutionary Offensive."""
        # Arrange: capacity = 0.8 * 0.6 = 0.48 >= 0.4
        graph = _create_test_graph(
            comprador_wealth=2.0,
            comprador_subsistence=5.0,
            p_w_organization=0.8,
            p_w_class_consciousness=0.6,
        )
        context = {"tick": 1}

        # Verify initial state
        assert graph.nodes["C002"]["p_revolution"] == 0.2

        # Act
        system = StruggleSystem()
        system.step(graph, services, context)

        # Assert: p_revolution set to 1.0
        assert graph.nodes["C002"]["p_revolution"] == 1.0

    def test_agitation_boosted_on_revolutionary_offensive(
        self, services: ServiceContainer, seeded_random: None
    ) -> None:
        """p_w.agitation += 0.5 during Revolutionary Offensive."""
        # Arrange: capacity = 0.8 * 0.6 = 0.48 >= 0.4
        graph = _create_test_graph(
            comprador_wealth=2.0,
            comprador_subsistence=5.0,
            p_w_organization=0.8,
            p_w_class_consciousness=0.6,
        )
        context = {"tick": 1}

        initial_agitation = graph.nodes["C002"]["ideology"]["agitation"]

        # Act
        system = StruggleSystem()
        system.step(graph, services, context)

        # Assert: agitation increased by 0.5 (default boost)
        new_agitation = graph.nodes["C002"]["ideology"]["agitation"]
        expected_boost = services.defines.struggle.revolutionary_agitation_boost
        assert new_agitation == pytest.approx(initial_agitation + expected_boost)

    def test_boundary_capacity_at_jackson_threshold(
        self, services: ServiceContainer, seeded_random: None
    ) -> None:
        """Revolutionary path taken when capacity == exactly 0.4."""
        # Arrange: capacity = 0.8 * 0.5 = 0.4 (exactly at threshold)
        graph = _create_test_graph(
            comprador_wealth=2.0,
            comprador_subsistence=5.0,
            p_w_organization=0.8,
            p_w_class_consciousness=0.5,
        )
        context = {"tick": 1}

        revolutionary_events: list[Event] = []
        fascist_events: list[Event] = []
        services.event_bus.subscribe(EventType.REVOLUTIONARY_OFFENSIVE, revolutionary_events.append)
        services.event_bus.subscribe(EventType.FASCIST_REVANCHISM, fascist_events.append)

        # Act
        system = StruggleSystem()
        system.step(graph, services, context)

        # Assert: Revolutionary path taken (>= comparison)
        assert len(revolutionary_events) == 1, "Should take revolutionary path at threshold"
        assert len(fascist_events) == 0, "Should NOT take fascist path"


@pytest.mark.unit
class TestFascistRevanchism:
    """Tests for Fascist Revanchism outcome (capacity < JACKSON_THRESHOLD)."""

    def test_fascist_revanchism_when_capacity_below_threshold(
        self, services: ServiceContainer, seeded_random: None
    ) -> None:
        """Fascist Revanchism when organization * consciousness < 0.4."""
        # Arrange: capacity = 0.2 * 0.3 = 0.06 < 0.4
        graph = _create_test_graph(
            comprador_wealth=2.0,
            comprador_subsistence=5.0,
            p_w_organization=0.2,
            p_w_class_consciousness=0.3,
            c_w_national_identity=0.3,
            c_w_p_acquiescence=0.4,
        )
        context = {"tick": 1}

        events: list[Event] = []
        services.event_bus.subscribe(EventType.FASCIST_REVANCHISM, events.append)

        # Act
        system = StruggleSystem()
        system.step(graph, services, context)

        # Assert: FASCIST_REVANCHISM event emitted
        assert len(events) == 1, f"Expected 1 FASCIST_REVANCHISM, got {len(events)}"
        event = events[0]
        assert event.payload["core_worker_id"] == "C003"
        assert event.payload["revolutionary_capacity"] == pytest.approx(0.06)
        assert "narrative_hint" in event.payload

    def test_core_worker_national_identity_increased(
        self, services: ServiceContainer, seeded_random: None
    ) -> None:
        """c_w.national_identity += 0.2 during Fascist Revanchism."""
        # Arrange: capacity = 0.2 * 0.3 = 0.06 < 0.4
        graph = _create_test_graph(
            comprador_wealth=2.0,
            comprador_subsistence=5.0,
            p_w_organization=0.2,
            p_w_class_consciousness=0.3,
            c_w_national_identity=0.3,
        )
        context = {"tick": 1}

        initial_identity = graph.nodes["C003"]["ideology"]["national_identity"]

        # Act
        system = StruggleSystem()
        system.step(graph, services, context)

        # Assert: national_identity increased
        new_identity = graph.nodes["C003"]["ideology"]["national_identity"]
        expected_boost = services.defines.struggle.fascist_identity_boost
        assert new_identity == pytest.approx(initial_identity + expected_boost)

    def test_core_worker_acquiescence_increased(
        self, services: ServiceContainer, seeded_random: None
    ) -> None:
        """c_w.p_acquiescence += 0.2 during Fascist Revanchism."""
        # Arrange: capacity = 0.2 * 0.3 = 0.06 < 0.4
        graph = _create_test_graph(
            comprador_wealth=2.0,
            comprador_subsistence=5.0,
            p_w_organization=0.2,
            p_w_class_consciousness=0.3,
            c_w_p_acquiescence=0.4,
        )
        context = {"tick": 1}

        initial_acquiescence = graph.nodes["C003"]["p_acquiescence"]

        # Act
        system = StruggleSystem()
        system.step(graph, services, context)

        # Assert: p_acquiescence increased
        new_acquiescence = graph.nodes["C003"]["p_acquiescence"]
        expected_boost = services.defines.struggle.fascist_acquiescence_boost
        assert new_acquiescence == pytest.approx(initial_acquiescence + expected_boost)

    def test_fascist_revanchism_without_core_worker(
        self, services: ServiceContainer, seeded_random: None
    ) -> None:
        """Fascist path emits event but skips c_w modification if no core worker."""
        # Arrange: No core worker in graph
        graph = _create_test_graph(
            comprador_wealth=2.0,
            comprador_subsistence=5.0,
            p_w_organization=0.2,
            p_w_class_consciousness=0.3,
            include_core_worker=False,
        )
        context = {"tick": 1}

        events: list[Event] = []
        services.event_bus.subscribe(EventType.FASCIST_REVANCHISM, events.append)

        # Act
        system = StruggleSystem()
        system.step(graph, services, context)

        # Assert: Event still emitted, just with no core_worker_id
        assert len(events) == 1
        assert events[0].payload.get("core_worker_id") is None

    def test_national_identity_clamped_at_one(
        self, services: ServiceContainer, seeded_random: None
    ) -> None:
        """national_identity should not exceed 1.0 after boost."""
        # Arrange: Core worker already at high national identity
        graph = _create_test_graph(
            comprador_wealth=2.0,
            comprador_subsistence=5.0,
            p_w_organization=0.2,
            p_w_class_consciousness=0.3,
            c_w_national_identity=0.95,  # Near max
        )
        context = {"tick": 1}

        # Act
        system = StruggleSystem()
        system.step(graph, services, context)

        # Assert: Clamped to 1.0
        assert graph.nodes["C003"]["ideology"]["national_identity"] == 1.0

    def test_p_acquiescence_clamped_at_one(
        self, services: ServiceContainer, seeded_random: None
    ) -> None:
        """p_acquiescence should not exceed 1.0 after boost."""
        # Arrange: Core worker already at high acquiescence
        graph = _create_test_graph(
            comprador_wealth=2.0,
            comprador_subsistence=5.0,
            p_w_organization=0.2,
            p_w_class_consciousness=0.3,
            c_w_p_acquiescence=0.95,  # Near max
        )
        context = {"tick": 1}

        # Act
        system = StruggleSystem()
        system.step(graph, services, context)

        # Assert: Clamped to 1.0
        assert graph.nodes["C003"]["p_acquiescence"] == 1.0


@pytest.mark.unit
class TestConfigurationOverrides:
    """Tests for configurable thresholds and boost values."""

    def test_custom_jackson_threshold(self, seeded_random: None) -> None:
        """Custom jackson_threshold changes bifurcation point."""
        # Arrange: capacity = 0.2 * 0.3 = 0.06
        # With threshold=0.05, this should trigger Revolutionary Offensive
        custom_defines = GameDefines(struggle=StruggleDefines(jackson_threshold=0.05))
        graph = _create_test_graph(
            comprador_wealth=2.0,
            comprador_subsistence=5.0,
            p_w_organization=0.2,
            p_w_class_consciousness=0.3,
        )
        svc = _create_services_with_defines(defines=custom_defines)
        context = {"tick": 1}

        revolutionary_events: list[Event] = []
        svc.event_bus.subscribe(EventType.REVOLUTIONARY_OFFENSIVE, revolutionary_events.append)

        try:
            # Act
            system = StruggleSystem()
            system.step(graph, svc, context)

            # Assert: Revolutionary path taken with lower threshold
            assert len(revolutionary_events) == 1
        finally:
            svc.database.close()

    def test_custom_agitation_boost(self, seeded_random: None) -> None:
        """Custom revolutionary_agitation_boost changes agitation increase."""
        custom_boost = 0.8
        custom_defines = GameDefines(
            struggle=StruggleDefines(revolutionary_agitation_boost=custom_boost)
        )
        graph = _create_test_graph(
            comprador_wealth=2.0,
            comprador_subsistence=5.0,
            p_w_organization=0.8,
            p_w_class_consciousness=0.6,
        )
        svc = _create_services_with_defines(defines=custom_defines)
        context = {"tick": 1}

        initial_agitation = graph.nodes["C002"]["ideology"]["agitation"]

        try:
            # Act
            system = StruggleSystem()
            system.step(graph, svc, context)

            # Assert: Custom boost applied
            new_agitation = graph.nodes["C002"]["ideology"]["agitation"]
            assert new_agitation == pytest.approx(initial_agitation + custom_boost)
        finally:
            svc.database.close()
