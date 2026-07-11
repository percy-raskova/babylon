"""Spec-071: DecompositionSystem creates the carceral-enforcer target on demand.

The bridged canonical world seeds no CARCERAL_ENFORCER / INTERNAL_PROLETARIAT
entity, so the enforcer branch of LA decomposition used to no-op. 071's crisis
tests induce SUPERWAGE_CRISIS, so the gap is closed: the system creates the
targets when absent (baseline-preserving — the canonical decade never
decomposes).
"""

from __future__ import annotations

from collections.abc import Generator

import pytest

from babylon.engine.services import ServiceContainer
from babylon.engine.systems.decomposition import DecompositionSystem, _find_entity_by_role
from babylon.models.enums import EventType, SocialRole
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


@pytest.fixture
def services() -> Generator[ServiceContainer, None, None]:
    container = ServiceContainer.create()
    yield container
    container.database.close()


def _add_dying_la(g: BabylonGraph) -> None:
    """An LA about to die (wealth < subsistence, population > 0) => decomposes now."""
    g.add_node(
        "C001",
        "social_class",
        role=SocialRole.LABOR_ARISTOCRACY.value,
        wealth=1.0,
        subsistence_threshold=5.0,
        population=500,
        active=True,
        county_fips="26163",
        s_bio=0.01,
        s_class=0.0,
    )


class TestEnforcerCreation:
    def test_enforcer_and_internal_proletariat_created_on_demand(
        self, services: ServiceContainer
    ) -> None:
        g = BabylonGraph()
        _add_dying_la(g)
        # No CARCERAL_ENFORCER / INTERNAL_PROLETARIAT nodes exist.
        assert _find_entity_by_role(g, SocialRole.CARCERAL_ENFORCER, include_inactive=True) is None

        events: list = []
        services.event_bus.subscribe(
            EventType.CLASS_DECOMPOSITION.value, lambda e: events.append(e)
        )
        DecompositionSystem().step(g, services, {"tick": 5, "persistent_data": {}})

        enforcer = _find_entity_by_role(g, SocialRole.CARCERAL_ENFORCER, include_inactive=True)
        internal = _find_entity_by_role(g, SocialRole.INTERNAL_PROLETARIAT, include_inactive=True)
        assert enforcer is not None, "enforcer must be created on demand"
        assert internal is not None, "internal proletariat must be created on demand"

        enforcer_frac = services.defines.carceral.enforcer_fraction
        prole_frac = services.defines.carceral.proletariat_fraction
        assert enforcer[1]["population"] == int(500 * enforcer_frac)
        assert internal[1]["population"] == int(500 * prole_frac)
        assert enforcer[1]["active"] is True
        assert len(events) == 1
        assert events[0].payload["population_transferred"]["to_enforcer"] > 0

    def test_created_ids_are_pattern_valid(self, services: ServiceContainer) -> None:
        import re

        g = BabylonGraph()
        _add_dying_la(g)
        DecompositionSystem().step(g, services, {"tick": 5, "persistent_data": {}})
        enforcer = _find_entity_by_role(g, SocialRole.CARCERAL_ENFORCER, include_inactive=True)
        internal = _find_entity_by_role(g, SocialRole.INTERNAL_PROLETARIAT, include_inactive=True)
        assert re.fullmatch(r"C[0-9]{3}", enforcer[0])
        assert re.fullmatch(r"C[0-9]{3}", internal[0])
        assert enforcer[0] != internal[0]

    def test_created_targets_survive_from_graph(self, services: ServiceContainer) -> None:
        """Design B: on-demand targets must be model-complete node payloads.

        ``_create_target_entity`` historically omitted ``id`` AND ``name``
        (both required on SocialClass — ``id`` pattern ``^C[0-9]{3,}$``,
        ``name`` min_length=1), so the next ``WorldState.from_graph``
        raised ValidationError and killed the facade round-trip.
        """
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.world_state import WorldState

        la = SocialClass(
            id="C001",
            name="Labor Aristocracy",
            role=SocialRole.LABOR_ARISTOCRACY,
            wealth=1.0,
            subsistence_threshold=5.0,
            population=500,
            active=True,
            county_fips="26163",
            s_bio=0.01,
            s_class=0.0,
        )
        state = WorldState(tick=5, entities={"C001": la})
        graph = state.to_graph()

        DecompositionSystem().step(graph, services, {"tick": 5, "persistent_data": {}})

        restored = WorldState.from_graph(graph, tick=6)  # must not raise
        created = {eid: e for eid, e in restored.entities.items() if eid != "C001"}
        assert created, "decomposition must create target entities"
        for node_id, entity in created.items():
            assert entity.id == node_id
            assert entity.name, f"created entity {node_id} must carry a non-empty name"
