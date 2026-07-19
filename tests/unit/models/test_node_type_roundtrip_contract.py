"""Contract: every ``WorldState`` entity family is findable by its ``NodeType``.

The test that would have caught the 2026-07-18 faction bug directly, and the
one that catches its next sibling. For each entity family, build a
``WorldState`` holding exactly one member, run the REAL ``to_graph()``, and
assert ``query_nodes(node_type=NodeType.X)`` finds it.

**Why this is fixture-independent.** It never hand-stamps ``_node_type``. The
node type under assertion comes from :class:`NodeType` and the node itself
comes from production's own serializer, so fixture and production cannot agree
on a convention production does not emit — the closed loop that made the
faction bug invisible cannot form here.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.models.entities.balkanization_faction import BalkanizationFaction
from babylon.models.entities.industry import IndustryHyperedge
from babylon.models.entities.institution import (
    Institution,
    InternalBalanceOfForces,
    ReproductionMechanism,
)
from babylon.models.entities.organization import StateApparatus
from babylon.models.entities.social_class import SocialClass
from babylon.models.entities.sovereign import Sovereign
from babylon.models.entities.territory import Territory
from babylon.models.enums import NodeType
from babylon.models.world_state import WorldState

pytestmark = pytest.mark.unit

#: Entity IDs are pattern-constrained per family (e.g. ``^C[0-9]{3,}$`` for
#: SocialClass, ``^FAC_[A-Z][A-Z0-9_]*$`` for factions), so each row carries
#: its own legal id rather than sharing one.

#: ``(NodeType, WorldState field, entity id, member)`` — one row per family that
#: ``to_graph()`` emits a node for. Adding a family to ``to_graph()`` without
#: adding a row here leaves that family's queryability unpinned.
_FAMILIES: list[tuple[NodeType, str, str, Any]] = [
    (
        NodeType.SOCIAL_CLASS,
        "entities",
        "C001",
        SocialClass(id="C001", name="Workers", role="internal_proletariat"),
    ),
    (
        NodeType.TERRITORY,
        "territories",
        "T001",
        Territory(id="T001", name="Wayne", sector_type="industrial"),
    ),
    (
        NodeType.ORGANIZATION,
        "organizations",
        "ORG_BUREAU",
        StateApparatus(
            id="ORG_BUREAU",
            name="Bureau",
            class_character="bourgeois",
            jurisdiction="municipal",
        ),
    ),
    (
        NodeType.INSTITUTION,
        "institutions",
        "INST_SCHOOL",
        Institution(
            id="INST_SCHOOL",
            name="School",
            apparatus_type="isa_educational",
            social_function="education",
            internal_balance=InternalBalanceOfForces(
                liberal_technocratic=0.5,
                revanchist_fascist=0.2,
                institutionalist_bonapartist=0.3,
            ),
            reproduction=ReproductionMechanism(),
        ),
    ),
    (
        NodeType.INDUSTRY,
        "industries",
        "31",
        IndustryHyperedge(
            naics_2digit="31",
            naics_label="Manufacturing",
            department_weights={"dept_i": 1.0},
        ),
    ),
    (
        NodeType.SOVEREIGN,
        "sovereigns",
        "SOV_REPUBLIC",
        Sovereign(
            id="SOV_REPUBLIC",
            name="Republic",
            sovereignty_type="recognized_state",
            color_hex="#123456",
            extraction_policy="continue",
            founded_tick=0,
        ),
    ),
    (
        NodeType.FACTION,
        "factions",
        "FAC_FRONT",
        BalkanizationFaction(
            id="FAC_FRONT",
            name="Front",
            ideology="decolonial",
            colonial_stance="abolish",
            is_settler_formation=False,
            extraction_modifier=1.0,
            violence_modifier=1.0,
            metabolic_reduction=0.0,
            color_hex="#654321",
            founded_tick=0,
        ),
    ),
]


@pytest.mark.parametrize(
    ("node_type", "field", "entity_id", "member"),
    _FAMILIES,
    ids=[row[0].value for row in _FAMILIES],
)
def test_entity_family_is_findable_by_its_node_type(
    node_type: NodeType, field: str, entity_id: str, member: Any
) -> None:
    """``to_graph()`` must stamp the family with the ``NodeType`` that finds it.

    A mismatch here is the exact defect shape that silently disabled
    ``RED_SETTLER_TRAP_DETECTED``, secession enumeration and
    ``FASCIST_RECRUITMENT``: the node exists on the graph, but every query for
    it returns nothing, forever.
    """
    graph = WorldState(tick=0, **{field: {entity_id: member}}).to_graph()

    found = [node.id for node in graph.query_nodes(node_type=node_type)]

    assert found == [entity_id], (
        f"{field}: to_graph() emitted a node that query_nodes("
        f"node_type=NodeType.{node_type.name}) cannot find. Production stamps "
        f"and production queries have diverged."
    )


def test_every_stamped_family_is_covered() -> None:
    """Guard the parametrization itself against a silently-added family.

    Counts the ``_node_type=`` stamps in ``to_graph()``'s own source. If a new
    entity family starts emitting nodes, this reds until a row is added above —
    the "grows with the codebase" property that keeps the contract honest.
    """
    import ast
    import inspect

    from babylon.models import world_state as module

    stamped: set[str] = set()
    tree = ast.parse(inspect.getsource(module))
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr != "add_node":
            continue
        for kw in node.keywords:
            if kw.arg == "_node_type" and isinstance(kw.value, ast.Attribute):
                stamped.add(kw.value.attr)

    covered = {node_type.name for node_type, _field, _id, _member in _FAMILIES}
    assert stamped == covered, (
        f"to_graph() stamps {sorted(stamped)} but the contract covers "
        f"{sorted(covered)}. Add the missing family to _FAMILIES."
    )
