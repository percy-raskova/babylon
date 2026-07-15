"""Unit tests for the DoctrineSystem (Unit 4) — the per-org doctrine loop."""

from __future__ import annotations

import pytest

from babylon.config.defines.doctrine import DoctrineDefines
from babylon.domain.doctrine import load_doctrine_tree
from babylon.engine.systems.doctrine import (
    DoctrineSystem,
    compute_doctrine,
    step_organization,
)
from babylon.models.entities.doctrine import DoctrineTree
from babylon.models.entities.organization import PoliticalFaction
from babylon.models.enums import (
    ClassCharacter,
    ConsciousnessTendency,
    LegalStanding,
    OrgType,
)
from babylon.models.enums.doctrine import DoctrineTag
from babylon.models.world_state import WorldState

pytestmark = pytest.mark.unit


@pytest.fixture
def tree() -> DoctrineTree:
    return load_doctrine_tree()


@pytest.fixture
def defines() -> DoctrineDefines:
    return DoctrineDefines()


def _org(**overrides: object) -> PoliticalFaction:
    base: dict[str, object] = {
        "id": "vanguard",
        "name": "Vanguard Party",
        "org_type": OrgType.POLITICAL_FACTION,
        "class_character": ClassCharacter.PROLETARIAN,
        "ideology": "marxism-leninism",
        "cohesion": 0.5,
        "cadre_level": 0.5,
        "budget": 1000.0,
        "legal_standing": LegalStanding.UNDERGROUND,
        "consciousness_tendency": ConsciousnessTendency.REVOLUTIONARY,
    }
    base.update(overrides)
    return PoliticalFaction(**base)  # type: ignore[arg-type]


class TestStepOrganization:
    def test_bootstraps_the_free_root_and_accrues_labour(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        acquired, tl, tags, sprung = step_organization({"cadre_level": 0.5}, tree, defines)
        assert tree.root_id in acquired
        # TL accrued = 0.5 (cadre) × 0.20 (midpoint allocation) = 0.10; root is free.
        assert tl == pytest.approx(0.10)
        # root seeds CLASS_ANALYSIS (+1); no decay applied to same-tick acquisition.
        assert tags[DoctrineTag.CLASS_ANALYSIS] == pytest.approx(1.0)
        assert sprung == []

    def test_tags_decay_across_ticks(self, tree: DoctrineTree, defines: DoctrineDefines) -> None:
        # Start already holding the root with a seeded tag, no cadre (no new TL).
        attrs = {
            "cadre_level": 0.0,
            "acquired_doctrine_ids": (tree.root_id,),
            "theoretical_labor": 0.0,
            "doctrine_tags": {DoctrineTag.CLASS_ANALYSIS: 100.0},
        }
        _, _, tags, _ = step_organization(attrs, tree, defines)
        assert tags[DoctrineTag.CLASS_ANALYSIS] == pytest.approx(99.45)  # 100 × (1 − 0.0055)

    def test_reachable_trap_fires_when_condition_holds(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        # adventurism: parent urban_guerrilla, condition "MASS_LINK <= 0".
        attrs = {
            "cadre_level": 0.0,
            "acquired_doctrine_ids": (tree.root_id, "urban_guerrilla"),
            "theoretical_labor": 0.0,
            "doctrine_tags": {DoctrineTag.MILITANCY: 5.0},  # MASS_LINK absent ⇒ 0
        }
        acquired, _, _, sprung = step_organization(attrs, tree, defines)
        assert "adventurism" in sprung
        assert "adventurism" in acquired

    def test_trap_dormant_when_condition_unmet(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        attrs = {
            "cadre_level": 0.0,
            "acquired_doctrine_ids": (tree.root_id, "urban_guerrilla"),
            "theoretical_labor": 0.0,
            "doctrine_tags": {DoctrineTag.MASS_LINK: 5.0},  # MASS_LINK > 0 ⇒ safe
        }
        _, _, _, sprung = step_organization(attrs, tree, defines)
        assert sprung == []


class TestComputeDoctrineOverGraph:
    def test_writes_state_onto_the_org_node(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        state = WorldState(
            tick=0,
            entities={},
            territories={},
            relationships=[],
            organizations={"vanguard": _org()},
        )
        graph = state.to_graph()
        sprung = compute_doctrine(graph, defines, tree)
        node = graph.nodes["vanguard"]
        assert tree.root_id in node["acquired_doctrine_ids"]
        assert node["theoretical_labor"] == pytest.approx(0.10)
        assert sprung == []

    def test_no_org_nodes_is_a_noop(self, tree: DoctrineTree, defines: DoctrineDefines) -> None:
        # A territory-only graph (like the qa:regression scenarios) is untouched.
        state = WorldState(tick=0, entities={}, territories={}, relationships=[])
        graph = state.to_graph()
        assert compute_doctrine(graph, defines, tree) == []


class TestDoctrineSystemAdapter:
    def test_system_runs_over_a_graph(self, tree: DoctrineTree) -> None:
        from unittest.mock import MagicMock

        state = WorldState(
            tick=0,
            entities={},
            territories={},
            relationships=[],
            organizations={"vanguard": _org()},
        )
        graph = state.to_graph()
        services = MagicMock()
        services.defines.doctrine = DoctrineDefines()
        DoctrineSystem().step(graph, services, {})
        assert tree.root_id in graph.nodes["vanguard"]["acquired_doctrine_ids"]
