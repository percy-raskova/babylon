"""Tests for StruggleSystem - Terminal Crisis Dynamics.

Peripheral Revolt Mechanic (Phase 2):
When P(S|R) > P(S|A) for PERIPHERY_PROLETARIAT, revolt severs EXPLOITATION edges.

This models the anti-colonial revolution that cuts off imperial extraction,
triggering the cascade: no extraction → no wages → LA decomposition → carceral turn.

See ai/terminal-crisis-dynamics.md for full theory.
"""

from __future__ import annotations

from collections.abc import Generator

import networkx as nx
import pytest

from babylon.engine.graph import BabylonGraph
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.struggle import StruggleSystem
from babylon.models.enums import EdgeType, EventType, SocialRole


@pytest.fixture
def services() -> Generator[ServiceContainer, None, None]:
    """Create a ServiceContainer for testing."""
    container = ServiceContainer.create()
    yield container
    container.database.close()


def _create_imperial_circuit(graph: nx.DiGraph[str]) -> None:
    """Create a minimal imperial circuit with EXPLOITATION edges.

    Nodes:
    - P_w: Periphery proletariat (source of extraction)
    - Comprador: Periphery bourgeoisie (intermediary)
    - C_b: Core bourgeoisie (receives tribute)
    - C_w: Labor aristocracy (receives super-wages)

    Edges:
    - P_w --EXPLOITATION--> Comprador (periphery extraction)
    - P_w --EXPLOITATION--> C_b (direct exploitation - for testing)
    """
    # Periphery proletariat
    graph.add_node(
        "P_w",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=100.0,
        population=1000,
        active=True,
        organization=0.3,
        repression_faced=0.5,
        p_acquiescence=0.2,  # Low - desperate
        p_revolution=0.6,  # High - organized
        _node_type="social_class",
    )

    # Comprador bourgeoisie
    graph.add_node(
        "Comprador",
        role=SocialRole.COMPRADOR_BOURGEOISIE,
        wealth=500.0,
        population=10,
        active=True,
        _node_type="social_class",
    )

    # Core bourgeoisie
    graph.add_node(
        "C_b",
        role=SocialRole.CORE_BOURGEOISIE,
        wealth=10000.0,
        population=100,
        active=True,
        _node_type="social_class",
    )

    # Labor aristocracy
    graph.add_node(
        "C_w",
        role=SocialRole.LABOR_ARISTOCRACY,
        wealth=2000.0,
        population=500,
        active=True,
        _node_type="social_class",
    )

    # EXPLOITATION edges from periphery
    graph.add_edge(
        "P_w",
        "Comprador",
        edge_type=EdgeType.EXPLOITATION,
        extraction_rate=0.5,
    )
    graph.add_edge(
        "P_w",
        "C_b",
        edge_type=EdgeType.EXPLOITATION,
        extraction_rate=0.3,
    )


@pytest.mark.unit
class TestPeripheralRevolt:
    """Peripheral revolt severs EXPLOITATION edges when revolution > acquiescence."""

    def test_revolt_severs_exploitation_edges_when_p_rev_gt_p_acq(
        self, services: ServiceContainer
    ) -> None:
        """When P(S|R) > P(S|A), periphery severs EXPLOITATION edges.

        This models anti-colonial revolution cutting off imperial extraction.
        The periphery says: "We'd rather fight than accept these conditions."
        """
        graph = BabylonGraph()
        _create_imperial_circuit(graph)

        # Verify edges exist before revolt
        exploitation_edges_before = [
            (u, v)
            for u, v, d in graph.edges(data=True)
            if d.get("edge_type") == EdgeType.EXPLOITATION
        ]
        assert len(exploitation_edges_before) == 2, "Should have 2 EXPLOITATION edges"

        system = StruggleSystem()
        system.step(graph, services, {"tick": 1})

        # After revolt: EXPLOITATION edges from P_w should be severed
        exploitation_edges_after = [
            (u, v)
            for u, v, d in graph.edges(data=True)
            if d.get("edge_type") == EdgeType.EXPLOITATION
        ]
        assert len(exploitation_edges_after) == 0, "Revolt should sever EXPLOITATION edges"

    def test_no_revolt_when_p_acq_gt_p_rev(self, services: ServiceContainer) -> None:
        """No revolt when P(S|A) > P(S|R) - acquiescence is rational.

        When conditions are survivable through compliance, revolt doesn't occur.
        """
        graph = BabylonGraph()
        _create_imperial_circuit(graph)

        # Override P_w to be acquiescent (high P(S|A), low P(S|R))
        graph.nodes["P_w"]["p_acquiescence"] = 0.8  # Comfortable
        graph.nodes["P_w"]["p_revolution"] = 0.2  # Low org, high repression

        system = StruggleSystem()
        system.step(graph, services, {"tick": 1})

        # EXPLOITATION edges should remain intact
        exploitation_edges = [
            (u, v)
            for u, v, d in graph.edges(data=True)
            if d.get("edge_type") == EdgeType.EXPLOITATION
        ]
        assert len(exploitation_edges) == 2, "No revolt = edges remain"

    def test_revolt_emits_peripheral_revolt_event(self, services: ServiceContainer) -> None:
        """PERIPHERAL_REVOLT event emitted with edges_severed count."""
        graph = BabylonGraph()
        _create_imperial_circuit(graph)

        captured_events: list = []
        services.event_bus.subscribe(
            EventType.PERIPHERAL_REVOLT,
            lambda e: captured_events.append(e),
        )

        system = StruggleSystem()
        system.step(graph, services, {"tick": 1})

        assert len(captured_events) == 1, "Should emit exactly one PERIPHERAL_REVOLT"
        event = captured_events[0]
        assert event.payload["node_id"] == "P_w"
        assert event.payload["edges_severed"] == 2

    def test_revolt_only_severs_outgoing_exploitation_edges(
        self, services: ServiceContainer
    ) -> None:
        """Revolt severs edges where the revolting entity is the SOURCE.

        EXPLOITATION edges point FROM exploited TO exploiter.
        P_w as SOURCE means "P_w is being exploited by target".
        Revolt severs these edges (P_w stops being exploited).
        """
        graph = BabylonGraph()
        _create_imperial_circuit(graph)

        # Add a non-exploitation edge that should NOT be severed
        graph.add_edge(
            "P_w",
            "C_w",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.5,
        )

        system = StruggleSystem()
        system.step(graph, services, {"tick": 1})

        # SOLIDARITY edge should remain
        solidarity_edges = [
            (u, v)
            for u, v, d in graph.edges(data=True)
            if d.get("edge_type") == EdgeType.SOLIDARITY
        ]
        assert len(solidarity_edges) == 1, "SOLIDARITY edges preserved"

    def test_inactive_entity_does_not_revolt(self, services: ServiceContainer) -> None:
        """Dead/inactive entities cannot revolt."""
        graph = BabylonGraph()
        _create_imperial_circuit(graph)

        # Mark P_w as inactive (dead)
        graph.nodes["P_w"]["active"] = False

        system = StruggleSystem()
        system.step(graph, services, {"tick": 1})

        # Edges should remain (dead can't revolt)
        exploitation_edges = [
            (u, v)
            for u, v, d in graph.edges(data=True)
            if d.get("edge_type") == EdgeType.EXPLOITATION
        ]
        assert len(exploitation_edges) == 2

    def test_revolt_occurs_at_threshold_equality(self, services: ServiceContainer) -> None:
        """Revolt does NOT occur when P(S|R) == P(S|A) (need strict >)."""
        graph = BabylonGraph()
        _create_imperial_circuit(graph)

        # Equal probabilities - not enough for revolt
        graph.nodes["P_w"]["p_acquiescence"] = 0.5
        graph.nodes["P_w"]["p_revolution"] = 0.5

        system = StruggleSystem()
        system.step(graph, services, {"tick": 1})

        exploitation_edges = [
            (u, v)
            for u, v, d in graph.edges(data=True)
            if d.get("edge_type") == EdgeType.EXPLOITATION
        ]
        assert len(exploitation_edges) == 2, "Equality = no revolt"


def _create_minimal_struggle_graph(
    *,
    repression: float = 0.5,
    agitation: float = 0.5,
    p_acq: float = 0.5,
    p_rev: float = 0.0,
    wealth: float = 100.0,
    role: SocialRole = SocialRole.PERIPHERY_PROLETARIAT,
    active: bool = True,
    solidarity_edges: int = 0,
    solidarity_strength: float = 0.0,
) -> nx.DiGraph[str]:
    """Create a minimal graph for testing StruggleSystem.step main loop.

    Creates a single target node with configurable attributes, and optionally
    SOLIDARITY edges for testing solidarity infrastructure gain.
    """
    graph = BabylonGraph()

    graph.add_node(
        "target",
        role=role,
        wealth=wealth,
        population=1000,
        active=active,
        repression_faced=repression,
        p_acquiescence=p_acq,
        p_revolution=p_rev,
        ideology={"class_consciousness": 0.0, "national_identity": 0.5, "agitation": agitation},
        _node_type="social_class",
    )

    # Add solidarity source nodes and edges if requested
    for i in range(solidarity_edges):
        source_id = f"solidarity_source_{i}"
        graph.add_node(
            source_id,
            role=SocialRole.LUMPENPROLETARIAT,
            wealth=10.0,
            population=100,
            active=True,
            _node_type="social_class",
        )
        graph.add_edge(
            source_id,
            "target",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=solidarity_strength,
        )

    return graph


@pytest.mark.unit
class TestStruggleSystemStep:
    """Targeted tests to kill mutation survivors in StruggleSystem.step main loop.

    Tests isolate spark probability, uprising condition, wealth destruction,
    solidarity infrastructure gain, consciousness boost, and filtering logic.
    """

    # ── Spark probability ────────────────────────────────────────────

    def test_spark_roll_ignores_global_random_state(self) -> None:
        """III.7: spark outcome is a pure function of tick, not global RNG."""
        import random as global_rng

        from babylon.config.defines import GameDefines, StruggleDefines

        outcomes: list[int] = []
        for seed in (1, 2):  # global first rolls 0.134 vs 0.956 straddle prob=0.5
            custom = StruggleDefines(spark_probability_scale=0.5)
            svc = ServiceContainer.create(defines=GameDefines(struggle=custom))
            graph = _create_minimal_struggle_graph(repression=1.0, agitation=0.0)
            captured: list = []
            svc.event_bus.subscribe(EventType.EXCESSIVE_FORCE, lambda e, c=captured: c.append(e))
            global_rng.seed(seed)
            StruggleSystem().step(graph, svc, {"tick": 1})
            outcomes.append(len(captured))
            svc.database.close()

        assert outcomes[0] == outcomes[1]

    def test_no_spark_when_repression_zero(self, services: ServiceContainer) -> None:
        """repression=0 → spark_prob=0 → no EXCESSIVE_FORCE event."""
        graph = _create_minimal_struggle_graph(repression=0.0, agitation=1.0)

        captured: list = []
        services.event_bus.subscribe(
            EventType.EXCESSIVE_FORCE,
            lambda e: captured.append(e),
        )

        system = StruggleSystem()
        # Run multiple times to confirm determinism
        for tick in range(20):
            system.step(graph, services, {"tick": tick})

        assert len(captured) == 0, "Zero repression should never produce a spark"

    def test_guaranteed_spark_with_max_repression(self, services: ServiceContainer) -> None:
        """repression=1.0 with spark_scale > 1.0 → spark always fires."""
        from babylon.config.defines import GameDefines, StruggleDefines

        graph = _create_minimal_struggle_graph(repression=1.0, agitation=0.0)

        # Set spark_scale > 1.0 to guarantee spark_probability > 1.0
        custom_struggle = StruggleDefines(spark_probability_scale=1.0)
        custom_defines = GameDefines(struggle=custom_struggle)
        custom_services = ServiceContainer.create(defines=custom_defines)

        captured: list = []
        custom_services.event_bus.subscribe(
            EventType.EXCESSIVE_FORCE,
            lambda e: captured.append(e),
        )

        system = StruggleSystem()
        system.step(graph, custom_services, {"tick": 1})

        assert len(captured) == 1, "Spark probability >= 1.0 should always fire"
        custom_services.database.close()

    def test_spark_probability_is_repression_times_scale(self, services: ServiceContainer) -> None:
        """spark_prob = repression * spark_scale; the tick-seeded roll decides."""
        from babylon.engine.systems.base import resolve_rng

        # Default spark_scale = 0.1, repression = 0.5 → prob = 0.05
        graph = _create_minimal_struggle_graph(repression=0.5, agitation=0.0)

        # III.7: the roll is the first draw of the tick-seeded stream
        # (0.13636... at tick=1) — above prob 0.05, so no spark.
        expected_roll = resolve_rng(services, tick=1).random()

        captured: list = []
        services.event_bus.subscribe(
            EventType.EXCESSIVE_FORCE,
            lambda e: captured.append(e),
        )

        system = StruggleSystem()
        system.step(graph, services, {"tick": 1})

        assert expected_roll > 0.05
        assert len(captured) == 0

    # ── Uprising condition ───────────────────────────────────────────

    def test_uprising_requires_agitation_above_threshold(self, services: ServiceContainer) -> None:
        """agitation == threshold exactly → NO uprising (strict >)."""
        # threshold default = 0.1, agitation = 0.1 (exactly at threshold)
        graph = _create_minimal_struggle_graph(repression=1.0, agitation=0.1, p_rev=0.8, p_acq=0.2)

        # Override spark_scale to guarantee spark
        from babylon.config.defines import GameDefines, StruggleDefines

        custom = StruggleDefines(spark_probability_scale=1.0)
        svc = ServiceContainer.create(defines=GameDefines(struggle=custom))

        captured_uprisings: list = []
        svc.event_bus.subscribe(
            EventType.UPRISING,
            lambda e: captured_uprisings.append(e),
        )

        system = StruggleSystem()
        system.step(graph, svc, {"tick": 1})

        # agitation == threshold → strict > means NO uprising
        assert len(captured_uprisings) == 0
        svc.database.close()

    def test_uprising_with_revolutionary_pressure_only(self, services: ServiceContainer) -> None:
        """No spark needed: p_rev > p_acq + agitation > threshold → uprising."""
        # High agitation above threshold, revolutionary pressure (p_rev > p_acq)
        graph = _create_minimal_struggle_graph(
            repression=0.0,  # No spark possible
            agitation=0.5,  # Above threshold (0.1)
            p_rev=0.8,
            p_acq=0.2,
        )

        captured_uprisings: list = []
        services.event_bus.subscribe(
            EventType.UPRISING,
            lambda e: captured_uprisings.append(e),
        )

        system = StruggleSystem()
        system.step(graph, services, {"tick": 1})

        assert len(captured_uprisings) == 1
        assert captured_uprisings[0].payload["trigger"] == "revolutionary_pressure"

    def test_no_uprising_without_agitation_despite_spark(self, services: ServiceContainer) -> None:
        """Spark fires but agitation=0 → no uprising."""
        from babylon.config.defines import GameDefines, StruggleDefines

        graph = _create_minimal_struggle_graph(
            repression=1.0,
            agitation=0.0,  # Below threshold
        )

        custom = StruggleDefines(spark_probability_scale=1.0)
        svc = ServiceContainer.create(defines=GameDefines(struggle=custom))

        captured_sparks: list = []
        captured_uprisings: list = []
        svc.event_bus.subscribe(EventType.EXCESSIVE_FORCE, lambda e: captured_sparks.append(e))
        svc.event_bus.subscribe(EventType.UPRISING, lambda e: captured_uprisings.append(e))

        system = StruggleSystem()
        system.step(graph, svc, {"tick": 1})

        assert len(captured_sparks) == 1, "Spark should fire"
        assert len(captured_uprisings) == 0, "No uprising without agitation"
        svc.database.close()

    def test_no_uprising_when_neither_spark_nor_pressure(self, services: ServiceContainer) -> None:
        """High agitation but no trigger (no spark + p_acq > p_rev) → no uprising."""
        graph = _create_minimal_struggle_graph(
            repression=0.0,  # No spark
            agitation=1.0,  # High
            p_acq=0.8,
            p_rev=0.2,  # No revolutionary pressure
        )

        captured_uprisings: list = []
        services.event_bus.subscribe(EventType.UPRISING, lambda e: captured_uprisings.append(e))

        system = StruggleSystem()
        system.step(graph, services, {"tick": 1})

        assert len(captured_uprisings) == 0

    def test_uprising_with_spark_and_agitation(self, services: ServiceContainer) -> None:
        """Spark + agitation > threshold → uprising (baseline positive case)."""
        from babylon.config.defines import GameDefines, StruggleDefines

        graph = _create_minimal_struggle_graph(
            repression=1.0,
            agitation=0.5,  # Above threshold
        )

        custom = StruggleDefines(spark_probability_scale=1.0)
        svc = ServiceContainer.create(defines=GameDefines(struggle=custom))

        captured_uprisings: list = []
        svc.event_bus.subscribe(EventType.UPRISING, lambda e: captured_uprisings.append(e))

        system = StruggleSystem()
        system.step(graph, svc, {"tick": 1})

        assert len(captured_uprisings) == 1
        assert captured_uprisings[0].payload["trigger"] == "spark"
        svc.database.close()

    # ── Wealth destruction ───────────────────────────────────────────

    def test_wealth_after_uprising(self, services: ServiceContainer) -> None:
        """wealth *= (1 - destruction_rate): 100 * (1-0.05) = 95."""
        from babylon.config.defines import GameDefines, StruggleDefines

        graph = _create_minimal_struggle_graph(repression=1.0, agitation=0.5, wealth=100.0)

        custom = StruggleDefines(spark_probability_scale=1.0, wealth_destruction_rate=0.3)
        svc = ServiceContainer.create(defines=GameDefines(struggle=custom))

        system = StruggleSystem()
        system.step(graph, svc, {"tick": 1})

        # 100 * (1 - 0.3) = 70
        assert graph.nodes["target"]["wealth"] == pytest.approx(70.0)
        svc.database.close()

    def test_zero_destruction_rate_preserves_wealth(self, services: ServiceContainer) -> None:
        """destruction_rate=0 → wealth unchanged after uprising."""
        from babylon.config.defines import GameDefines, StruggleDefines

        graph = _create_minimal_struggle_graph(repression=1.0, agitation=0.5, wealth=100.0)

        custom = StruggleDefines(spark_probability_scale=1.0, wealth_destruction_rate=0.0)
        svc = ServiceContainer.create(defines=GameDefines(struggle=custom))

        system = StruggleSystem()
        system.step(graph, svc, {"tick": 1})

        assert graph.nodes["target"]["wealth"] == pytest.approx(100.0)
        svc.database.close()

    def test_full_destruction_rate_zeros_wealth(self, services: ServiceContainer) -> None:
        """destruction_rate=1.0 → wealth = 0 after uprising."""
        from babylon.config.defines import GameDefines, StruggleDefines

        graph = _create_minimal_struggle_graph(repression=1.0, agitation=0.5, wealth=200.0)

        custom = StruggleDefines(spark_probability_scale=1.0, wealth_destruction_rate=1.0)
        svc = ServiceContainer.create(defines=GameDefines(struggle=custom))

        system = StruggleSystem()
        system.step(graph, svc, {"tick": 1})

        assert graph.nodes["target"]["wealth"] == pytest.approx(0.0)
        svc.database.close()

    # ── Solidarity infrastructure ────────────────────────────────────

    def test_solidarity_strength_increases_on_uprising(self, services: ServiceContainer) -> None:
        """Uprising increases solidarity_strength on incoming SOLIDARITY edges."""
        from babylon.config.defines import GameDefines, StruggleDefines

        graph = _create_minimal_struggle_graph(
            repression=1.0,
            agitation=0.5,
            solidarity_edges=1,
            solidarity_strength=0.3,
        )

        custom = StruggleDefines(spark_probability_scale=1.0, solidarity_gain_per_uprising=0.2)
        svc = ServiceContainer.create(defines=GameDefines(struggle=custom))

        system = StruggleSystem()
        system.step(graph, svc, {"tick": 1})

        # Check solidarity edge strength: 0.3 + 0.2 = 0.5
        edge_data = graph.edges["solidarity_source_0", "target"]
        assert edge_data["solidarity_strength"] == pytest.approx(0.5)
        svc.database.close()

    def test_solidarity_clamped_at_one(self, services: ServiceContainer) -> None:
        """Solidarity strength clamped to max 1.0 (not 1.1)."""
        from babylon.config.defines import GameDefines, StruggleDefines

        graph = _create_minimal_struggle_graph(
            repression=1.0,
            agitation=0.5,
            solidarity_edges=1,
            solidarity_strength=0.9,
        )

        custom = StruggleDefines(spark_probability_scale=1.0, solidarity_gain_per_uprising=0.2)
        svc = ServiceContainer.create(defines=GameDefines(struggle=custom))

        system = StruggleSystem()
        system.step(graph, svc, {"tick": 1})

        # 0.9 + 0.2 = 1.1 → clamped to 1.0
        edge_data = graph.edges["solidarity_source_0", "target"]
        assert edge_data["solidarity_strength"] == pytest.approx(1.0)
        svc.database.close()

    # ── Consciousness boost ──────────────────────────────────────────

    def test_consciousness_boost_is_half_solidarity_gain(self, services: ServiceContainer) -> None:
        """Consciousness boost = solidarity_gain * 0.5."""
        from babylon.config.defines import GameDefines, StruggleDefines

        graph = _create_minimal_struggle_graph(repression=1.0, agitation=0.5)

        custom = StruggleDefines(spark_probability_scale=1.0, solidarity_gain_per_uprising=0.4)
        svc = ServiceContainer.create(defines=GameDefines(struggle=custom))

        system = StruggleSystem()
        system.step(graph, svc, {"tick": 1})

        # Initial consciousness = 0.0, boost = 0.4 * 0.5 = 0.2
        ideology = graph.nodes["target"]["ideology"]
        assert ideology["class_consciousness"] == pytest.approx(0.2)
        svc.database.close()

    # ── Filtering ────────────────────────────────────────────────────

    def test_non_struggling_role_skipped(self, services: ServiceContainer) -> None:
        """CORE_BOURGEOISIE should not be processed by struggle system."""
        from babylon.config.defines import GameDefines, StruggleDefines

        graph = _create_minimal_struggle_graph(
            role=SocialRole.CORE_BOURGEOISIE,
            repression=1.0,
            agitation=1.0,
        )

        custom = StruggleDefines(spark_probability_scale=1.0)
        svc = ServiceContainer.create(defines=GameDefines(struggle=custom))

        captured: list = []
        svc.event_bus.subscribe(EventType.EXCESSIVE_FORCE, lambda e: captured.append(e))
        svc.event_bus.subscribe(EventType.UPRISING, lambda e: captured.append(e))

        system = StruggleSystem()
        system.step(graph, svc, {"tick": 1})

        assert len(captured) == 0, "Non-struggling roles should produce no events"
        svc.database.close()

    def test_inactive_entity_skipped(self, services: ServiceContainer) -> None:
        """Inactive entities should not produce spark or uprising events."""
        from babylon.config.defines import GameDefines, StruggleDefines

        graph = _create_minimal_struggle_graph(
            active=False,
            repression=1.0,
            agitation=1.0,
        )

        custom = StruggleDefines(spark_probability_scale=1.0)
        svc = ServiceContainer.create(defines=GameDefines(struggle=custom))

        captured: list = []
        svc.event_bus.subscribe(EventType.EXCESSIVE_FORCE, lambda e: captured.append(e))
        svc.event_bus.subscribe(EventType.UPRISING, lambda e: captured.append(e))

        system = StruggleSystem()
        system.step(graph, svc, {"tick": 1})

        assert len(captured) == 0, "Inactive entities should produce no events"
        svc.database.close()
