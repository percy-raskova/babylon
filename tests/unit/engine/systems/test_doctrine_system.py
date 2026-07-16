"""Unit tests for the DoctrineSystem (Unit 4) — the per-org doctrine loop."""

from __future__ import annotations

import hashlib
import json

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
    def test_hydrated_json_native_attrs_step_identically(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        # Mid-session resume: hydrate_graph yields JSON-native attrs (list ids,
        # str-keyed tags) rather than the typed tuple/DoctrineTag forms
        # to_graph writes. The doctrine loop must treat both identically or a
        # resumed session would silently diverge from an unbroken one.
        typed = {
            "cadre_level": 0.5,
            "acquired_doctrine_ids": ("class_consciousness",),
            "theoretical_labor": 10.0,
            "doctrine_tags": {DoctrineTag.CLASS_ANALYSIS: 1.2},
        }
        json_native = {
            "cadre_level": 0.5,
            "acquired_doctrine_ids": ["class_consciousness"],
            "theoretical_labor": 10.0,
            "doctrine_tags": {"class_analysis": 1.2},
        }
        assert step_organization(typed, tree, defines) == step_organization(
            json_native, tree, defines
        )

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


class TestDoctrineDeterminism:
    """Determinism-in-motion for the doctrine loop (2026-07-15 review, D1).

    The 5 qa:regression goldens carry zero organization nodes, so their
    byte-identity gate proves the DoctrineSystem is a NO-OP there — not that
    it is deterministic when it actually runs. This harness is the org-bearing
    coverage: a 100-tick hash chain over every doctrine attr on a 3-org graph,
    pinned as a golden. Doctrine math is pure IEEE-754 add/multiply (decay,
    accrual — no libm transcendentals), so the chain is reproducible across
    platforms; if it moves, doctrine behavior changed and the change must be
    deliberate (regenerate the constant and say so in the commit, per the
    Unit-6 regenerate-and-document obligation in ADR073).
    """

    TICKS = 100
    # Regenerate: run _chain_digest() and paste; see class docstring.
    GOLDEN_CHAIN = "04b604d543dd75af07cdc220dfa015e88f3b3a45beb056821a20e3bec246ede7"

    @staticmethod
    def _chain_digest() -> str:
        state = WorldState(
            tick=0,
            entities={},
            territories={},
            relationships=[],
            organizations={
                # Two orgs with IDENTICAL states exercise the (cost_tl, node_id)
                # tie-break; the third's different cadre rate staggers acquisition.
                "org_a": _org(id="org_a", name="A", cadre_level=0.5),
                "org_b": _org(id="org_b", name="B", cadre_level=0.5),
                "org_c": _org(id="org_c", name="C", cadre_level=0.17),
            },
        )
        graph = state.to_graph()
        defines = DoctrineDefines()
        tree = load_doctrine_tree()
        chain = hashlib.sha256()
        for _ in range(TestDoctrineDeterminism.TICKS):
            compute_doctrine(graph, defines, tree)
            payload = {
                str(node.id): {
                    "acquired": list(node.attributes.get("acquired_doctrine_ids", ())),
                    "tl": repr(node.attributes.get("theoretical_labor", 0.0)),
                    "tags": {
                        str(k): repr(v) for k, v in node.attributes.get("doctrine_tags", {}).items()
                    },
                }
                for node in graph.query_nodes(node_type="organization")
            }
            assert len(payload) == 3, "org filter broke — chain would be vacuously stable"
            chain.update(json.dumps(payload, sort_keys=True).encode())
        return chain.hexdigest()

    def test_two_independent_runs_produce_identical_chains(self) -> None:
        assert self._chain_digest() == self._chain_digest()

    def test_chain_matches_pinned_golden(self) -> None:
        assert self._chain_digest() == self.GOLDEN_CHAIN


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
