"""Spec-066 T010: WorldState graph round-trip preserves EXPLOITATION relationships.

The US2 engine integration mutates a single in-memory `nx.DiGraph` across
all 520 ticks; the runner converts ``WorldState`` → graph at hydration
and back to ``WorldState`` after each tick. This test fixes the contract:
any EXPLOITATION ``Relationship`` seeded into ``WorldState.relationships``
MUST survive a ``to_graph()`` -> ``from_graph()`` cycle (otherwise the
``ImperialRentSystem`` has no edges to walk and no Φ to extract).

Per Phase 0 R1: round-trip preserves all standard Relationship fields
because the edge stores ``rel.edge_data`` and ``from_graph`` reconstructs
relationships from every edge that isn't a service edge (PRESENCE,
HOUSES, etc.).
"""

from __future__ import annotations

import pytest

from babylon.config.defines._assembler import GameDefines
from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.models import Relationship, SocialClass, WorldState
from babylon.models.enums import EdgeType

pytestmark = [pytest.mark.unit]


def test_relationships_survive_round_trip() -> None:
    """T010: EXPLOITATION Relationship seeded into WorldState survives to_graph -> from_graph."""
    prol: SocialClass = create_proletariat(id="C001", county_fips="26163")
    bourg: SocialClass = create_bourgeoisie(id="C002", county_fips="26163")
    rel = Relationship(
        source_id="C001",
        target_id="C002",
        edge_type=EdgeType.EXPLOITATION,
        value_flow=0.0,
        tension=0.1,
    )

    state = WorldState(
        tick=0,
        entities={"C001": prol, "C002": bourg},
        relationships=[rel],
        config=GameDefines(),
    )

    graph = state.to_graph()
    assert ("C001", "C002") in graph.edges, "EXPLOITATION edge missing from graph"

    round_tripped = WorldState.from_graph(graph, tick=0)

    exploitation_rels = [
        r for r in round_tripped.relationships if r.edge_type == EdgeType.EXPLOITATION
    ]
    assert len(exploitation_rels) == 1, (
        f"expected exactly one EXPLOITATION relationship after round-trip, "
        f"got {len(exploitation_rels)}: "
        f"{[(r.source_id, r.target_id, r.edge_type) for r in round_tripped.relationships]}"
    )
    recovered = exploitation_rels[0]
    assert recovered.source_id == "C001"
    assert recovered.target_id == "C002"
    assert recovered.tension == pytest.approx(0.1)
