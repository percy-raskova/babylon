"""Shared fixtures for the verb-dispatch contract suite.

Builds a small, fully-valid :class:`~babylon.models.world_state.WorldState`
(one revolutionary PoliticalFaction, a rival faction, two territories, one
SocialClass) and exposes it as a :class:`~babylon.engine.graph.BabylonGraph`.
Because it is assembled from real entity models, ``WorldState.from_graph``
reconstructs it cleanly — which is exactly what ``test_roundtrip`` asserts the
resolvers preserve.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from babylon.engine.services import ServiceContainer
from babylon.models.entities.organization import PoliticalFaction
from babylon.models.entities.social_class import SocialClass
from babylon.models.entities.territory import Territory
from babylon.models.enums import (
    ClassCharacter,
    ConsciousnessTendency,
    SectorType,
    SocialRole,
)
from babylon.models.world_state import WorldState

if TYPE_CHECKING:
    from babylon.engine.graph import BabylonGraph

#: Canonical node ids used throughout the verb contract suite.
ORG_ID = "ORGP"
RIVAL_ID = "ORGQ"
CLASS_ID = "C001"
HOME_TERRITORY = "T001"
OTHER_TERRITORY = "T002"


def build_verb_world() -> WorldState:
    """Assemble a minimal, round-trip-valid WorldState for verb tests."""
    workers = SocialClass(
        id=CLASS_ID, name="Detroit Workers", role=SocialRole.PERIPHERY_PROLETARIAT
    )
    home = Territory(id=HOME_TERRITORY, name="Detroit", sector_type=SectorType.INDUSTRIAL)
    other = Territory(id=OTHER_TERRITORY, name="Dearborn", sector_type=SectorType.INDUSTRIAL)
    vanguard = PoliticalFaction(
        id=ORG_ID,
        name="Vanguard",
        class_character=ClassCharacter.PROLETARIAN,
        ideology="Marxism-Leninism-Maoism",
        cohesion=0.5,
        cadre_level=0.4,
        budget=100.0,
        consciousness_tendency=ConsciousnessTendency.REVOLUTIONARY,
        territory_ids=[HOME_TERRITORY],
    )
    rival = PoliticalFaction(
        id=RIVAL_ID,
        name="Rival Bloc",
        class_character=ClassCharacter.PROLETARIAN,
        ideology="Reformism",
        cohesion=0.3,
        cadre_level=0.2,
        budget=50.0,
        territory_ids=[HOME_TERRITORY],
    )
    return WorldState(
        tick=0,
        entities={CLASS_ID: workers},
        territories={HOME_TERRITORY: home, OTHER_TERRITORY: other},
        organizations={ORG_ID: vanguard, RIVAL_ID: rival},
    )


@pytest.fixture
def verb_graph() -> BabylonGraph:
    """Fresh BabylonGraph for one test (never shared — resolvers mutate it)."""
    return build_verb_world().to_graph()


@pytest.fixture
def services() -> ServiceContainer:
    """Default ServiceContainer (real GameDefines) for resolver dispatch."""
    return ServiceContainer.create()


def org_attrs(graph: BabylonGraph, org_id: str = ORG_ID) -> dict[str, Any]:
    """Snapshot copy of an org node's attributes (as the OODA seam passes)."""
    return dict(graph.nodes[org_id])
