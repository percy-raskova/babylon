"""Unit tests for the DoctrineSystem (Unit 4) — the per-org doctrine loop."""

from __future__ import annotations

import hashlib
import json
import random

import pytest

from babylon.config.defines.doctrine import DoctrineDefines
from babylon.domain.doctrine import load_doctrine_tree
from babylon.engine.services import ServiceContainer
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
    EventType,
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

    def test_study_target_suspends_greedy_and_saves(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        # Unlocked (root held) but unaffordable target: the org SAVES — no
        # greedy purchase happens even though cheaper nodes are affordable.
        attrs = {
            "cadre_level": 0.0,
            "acquired_doctrine_ids": (tree.root_id, "trade_unionism"),
            "theoretical_labor": 60.0,  # enough for a cheap greedy buy (50)
            "study_target_id": "democratic_centralism",
        }
        cost = tree.nodes["democratic_centralism"].cost_tl
        assert cost > 60.0, "fixture invalid: target must be unaffordable"
        acquired, tl, _, _, target = step_organization(attrs, tree, defines)
        assert acquired == (tree.root_id, "trade_unionism")  # nothing bought
        assert tl == pytest.approx(60.0)  # nothing spent
        assert target == "democratic_centralism"  # order stands

    def test_study_target_acquired_when_affordable_then_cleared(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        cost = tree.nodes["democratic_centralism"].cost_tl
        attrs = {
            "cadre_level": 0.0,
            "acquired_doctrine_ids": (tree.root_id, "trade_unionism"),
            "theoretical_labor": float(cost),
            "study_target_id": "democratic_centralism",
        }
        acquired, tl, _, _, target = step_organization(attrs, tree, defines)
        assert "democratic_centralism" in acquired
        assert tl == pytest.approx(0.0)
        assert target is None

    def test_locked_study_target_keeps_greedy_running(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        # Target's parents not held: greedy continues (builds toward it), the
        # order stands — directed saving toward a locked node would deadlock.
        attrs = {
            "cadre_level": 0.0,
            "acquired_doctrine_ids": (tree.root_id,),
            "theoretical_labor": 1000.0,
            "study_target_id": "urban_guerrilla",  # needs armed_vanguard first
        }
        assert not all(p in (tree.root_id,) for p in tree.nodes["urban_guerrilla"].parents), (
            "fixture invalid: target must be locked"
        )
        acquired, _, _, _, target = step_organization(attrs, tree, defines)
        assert len(acquired) > 1  # greedy bought something
        assert target == "urban_guerrilla"

    def test_invalid_or_trap_study_target_clears(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        for bad in ("no_such_node", "adventurism", tree.root_id):
            attrs = {
                "cadre_level": 0.0,
                "acquired_doctrine_ids": (tree.root_id,),
                "theoretical_labor": 0.0,
                "study_target_id": bad,
            }
            _, _, _, _, target = step_organization(attrs, tree, defines)
            assert target is None, f"{bad!r} should clear the order"

    def test_bootstraps_the_free_root_and_accrues_labour(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        acquired, tl, tags, sprung, _ = step_organization({"cadre_level": 0.5}, tree, defines)
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
        _, _, tags, _, _ = step_organization(attrs, tree, defines)
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
        acquired, _, _, sprung, _ = step_organization(attrs, tree, defines)
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
        _, _, _, sprung, _ = step_organization(attrs, tree, defines)
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

    def test_congress_tick_purges_and_rebaselines(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        class _AlwaysSucceed(random.Random):
            def random(self) -> float:  # noqa: A003 - mirrors random.Random
                return 0.0

        trapped = _org(
            acquired_doctrine_ids=("class_consciousness", "urban_guerrilla", "adventurism"),
            theoretical_labor=400.0,
            doctrine_tags={DoctrineTag.MILITANCY: 5.0},
        )
        state = WorldState(
            tick=0,
            entities={},
            territories={},
            relationships=[],
            organizations={"vanguard": trapped},
        )
        graph = state.to_graph()
        interval = defines.congress_interval_ticks
        events = compute_doctrine(graph, defines, tree, tick=interval, rng=_AlwaysSucceed())

        assert ("vanguard", "adventurism", "escaped") in events
        node = graph.nodes["vanguard"]
        assert "adventurism" not in node["acquired_doctrine_ids"]
        # the congress re-baselined the snapshot for the next period
        assert node["congress_tag_snapshot"]
        # attempt cost spent, then the ordinary tick step ran on top
        assert node["theoretical_labor"] < 400.0 - defines.trap_escape_tl + 1.0

    def test_non_congress_tick_never_touches_the_snapshot(
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
        compute_doctrine(
            graph, defines, tree, tick=defines.congress_interval_ticks - 1, rng=random.Random(0)
        )
        # model default is {} — a non-congress tick must not update it
        assert graph.nodes["vanguard"]["congress_tag_snapshot"] == {}


class TestDoctrineDeterminism:
    """Determinism-in-motion for the doctrine loop (2026-07-15 review, D1).

    The 5 qa:regression goldens carry zero organization nodes, so their
    byte-identity gate proves the DoctrineSystem is a NO-OP there — not that
    it is deterministic when it actually runs. This harness is the org-bearing
    coverage: a 100-tick hash chain over every doctrine attr on a 3-org graph,
    pinned as a golden — including the tick-52/104 Party Congresses with a real
    seeded purge roll (org_c starts inside the adventurism trap with the TL to
    attempt self-criticism). Doctrine math is pure IEEE-754 add/multiply and
    the roll comes from a fixed-seed ``random.Random``, so the chain is
    reproducible across platforms; if it moves, doctrine behavior changed and
    the change must be deliberate (regenerate the constant and say so in the
    commit, per the Unit-6 regenerate-and-document obligation in ADR073).

    GOLDEN_CHAIN history: 04b604d5… (Unit 4, congress-free) → regenerated for
    Unit 5 (congress wired: tick/rng params + snapshot in the payload +
    trapped org_c — a DELIBERATE, documented behavior change).
    """

    TICKS = 100
    # Regenerate: run _chain_digest() and paste; see class docstring.
    GOLDEN_CHAIN = "8a5caa58a173dd6d0a251cdfb531302fd3cef8f5423d65d6f78a4b4095705c23"

    @staticmethod
    def _chain_digest() -> str:
        state = WorldState(
            tick=0,
            entities={},
            territories={},
            relationships=[],
            organizations={
                # Two orgs with IDENTICAL states exercise the (cost_tl, node_id)
                # tie-break. org_c starts trapped + holding EVERY purchasable
                # node — the greedy acquirer has nothing left to buy, so its
                # 400 TL survives to tick 52 and the congress attempts a real
                # purge (exercises the seeded roll path; an earlier fixture let
                # greedy drain the wallet first and the roll never happened).
                "org_a": _org(id="org_a", name="A", cadre_level=0.5),
                "org_b": _org(id="org_b", name="B", cadre_level=0.5),
                "org_c": _org(
                    id="org_c",
                    name="C",
                    cadre_level=0.17,
                    acquired_doctrine_ids=(
                        "class_consciousness",
                        "trade_unionism",
                        "electoral_socialism",
                        "coalition_politics",
                        "democratic_centralism",
                        "mass_line",
                        "united_front",
                        "armed_vanguard",
                        "urban_guerrilla",
                        "adventurism",
                    ),
                    theoretical_labor=400.0,
                    doctrine_tags={DoctrineTag.MILITANCY: 5.0},
                ),
            },
        )
        graph = state.to_graph()
        defines = DoctrineDefines()
        tree = load_doctrine_tree()
        rng = random.Random(0xD0C7)
        chain = hashlib.sha256()
        for i in range(TestDoctrineDeterminism.TICKS):
            compute_doctrine(graph, defines, tree, tick=i + 1, rng=rng)
            payload = {
                str(node.id): {
                    "acquired": list(node.attributes.get("acquired_doctrine_ids", ())),
                    "tl": repr(node.attributes.get("theoretical_labor", 0.0)),
                    "tags": {
                        str(k): repr(v) for k, v in node.attributes.get("doctrine_tags", {}).items()
                    },
                    "snapshot": {
                        str(k): repr(v)
                        for k, v in node.attributes.get("congress_tag_snapshot", {}).items()
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


class TestDoctrineSystemEventPublication:
    """ADR073 Unit 6a: DoctrineSystem.step publishes DoctrineEvents onto the
    event bus the same way StruggleSystem publishes UPRISING (mirrors
    tests/unit/engine/systems/test_struggle.py's event-bus subscription
    pattern)."""

    def test_sprung_trap_publishes_doctrine_trap_sprung_event(self) -> None:
        # adventurism: parent urban_guerrilla, condition "MASS_LINK <= 0" —
        # same fixture as TestStepOrganization.test_reachable_trap_fires_
        # when_condition_holds, but driven through the real System + a real
        # ServiceContainer's event bus instead of the pure function.
        trapped = _org(
            acquired_doctrine_ids=("class_consciousness", "urban_guerrilla"),
            theoretical_labor=0.0,
            doctrine_tags={DoctrineTag.MILITANCY: 5.0},
        )
        state = WorldState(
            tick=0,
            entities={},
            territories={},
            relationships=[],
            organizations={"vanguard": trapped},
        )
        graph = state.to_graph()

        services = ServiceContainer.create()
        captured: list = []
        services.event_bus.subscribe(
            EventType.DOCTRINE_TRAP_SPRUNG,
            lambda e: captured.append(e),
        )
        try:
            DoctrineSystem().step(graph, services, {"tick": 1})
        finally:
            services.database.close()

        assert len(captured) == 1
        assert captured[0].payload["org_id"] == "vanguard"
        assert captured[0].payload["node_id"] == "adventurism"
        assert "adventurism" in graph.nodes["vanguard"]["acquired_doctrine_ids"]

    def test_no_trap_publishes_no_doctrine_events(self) -> None:
        """A fresh org (no reachable trap) publishes nothing — no false positives."""
        state = WorldState(
            tick=0,
            entities={},
            territories={},
            relationships=[],
            organizations={"vanguard": _org()},
        )
        graph = state.to_graph()

        services = ServiceContainer.create()
        captured: list = []
        for kind in (
            EventType.DOCTRINE_TRAP_SPRUNG,
            EventType.DOCTRINE_TRAP_ESCAPED,
            EventType.DOCTRINE_PURGE_FAILED,
        ):
            services.event_bus.subscribe(kind, lambda e: captured.append(e))
        try:
            DoctrineSystem().step(graph, services, {"tick": 1})
        finally:
            services.database.close()

        assert captured == []
