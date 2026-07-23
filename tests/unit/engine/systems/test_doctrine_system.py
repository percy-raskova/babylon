"""Unit tests for the DoctrineSystem (Unit 4) — the per-org doctrine loop."""

from __future__ import annotations

import hashlib
import json
import random

import pytest

from babylon.config.defines.doctrine import DoctrineDefines
from babylon.config.defines.politics import PoliticsDefines
from babylon.domain.doctrine import load_doctrine_tree
from babylon.engine.actions._mass_work import apply_mass_work_solidarity
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.doctrine import (
    DoctrineSystem,
    compute_doctrine,
    step_organization,
)
from babylon.models.entities.doctrine import DoctrineTree
from babylon.models.entities.organization import PoliticalFaction
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import SocialClass
from babylon.models.enums import (
    ClassCharacter,
    ConsciousnessTendency,
    EdgeType,
    EventType,
    LegalStanding,
    OrgType,
    SocialRole,
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


#: The politics coefficients compute_doctrine needs (P25 U11 commit E): the
#: absorbing-state @coeff DSL thresholds (an unknown @coeff fails loud, so every
#: call site passes them) + the officeholder-capture rate + the practice→tag
#: drift rates. Values mirror the PoliticsDefines defaults.
_COEFFS = {
    "solidarity_liquidation_floor": 0.05,
    "co_optive_liquidation_threshold": 0.6,
    "petty_bourgeois_liquidation_threshold": 0.6,
    "office_capture_rate": 0.02,
    "reformist_theory_decay": 0.02,
    "class_analysis_veto_decay": 0.03,
    "co_optive_dependence_drift": 0.02,
    "split_asset_retention": 0.4,
}


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
        acquired, tl, _, _, target = step_organization(attrs, tree, defines, coeffs=_COEFFS)
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
        acquired, tl, _, _, target = step_organization(attrs, tree, defines, coeffs=_COEFFS)
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
        acquired, _, _, _, target = step_organization(attrs, tree, defines, coeffs=_COEFFS)
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
        sprung = compute_doctrine(graph, defines, tree, coeffs=_COEFFS)
        node = graph.nodes["vanguard"]
        assert tree.root_id in node["acquired_doctrine_ids"]
        assert node["theoretical_labor"] == pytest.approx(0.10)
        assert sprung == []

    def test_no_org_nodes_is_a_noop(self, tree: DoctrineTree, defines: DoctrineDefines) -> None:
        # A territory-only graph (like the qa:regression scenarios) is untouched.
        state = WorldState(tick=0, entities={}, territories={}, relationships=[])
        graph = state.to_graph()
        assert compute_doctrine(graph, defines, tree, coeffs=_COEFFS) == []

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
        events = compute_doctrine(
            graph, defines, tree, tick=interval, rng=_AlwaysSucceed(), coeffs=_COEFFS
        )

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
            graph,
            defines,
            tree,
            tick=defines.congress_interval_ticks - 1,
            rng=random.Random(0),
            coeffs=_COEFFS,
        )
        # model default is {} — a non-congress tick must not update it
        assert graph.nodes["vanguard"]["congress_tag_snapshot"] == {}


class TestMassWorkSolidarityDecay:
    """Unit 6 write side (ADR087): ``compute_doctrine`` decays each org's
    OUTGOING mass-work SOLIDARITY edges every tick -- a mass link not
    renewed by work withers, floored at 0. Built via the REAL producer
    (:func:`~babylon.engine.actions._mass_work.apply_mass_work_solidarity`),
    never a hand-stamped edge (see ``test_ideology.py``'s
    ``TestOrganizationSourcedSolidarity`` for why)."""

    def test_org_sourced_edge_decays_each_tick(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        workers = SocialClass(id="C900", name="Workers", role=SocialRole.PERIPHERY_PROLETARIAT)
        state = WorldState(
            tick=0, entities={"C900": workers}, territories={}, organizations={"vanguard": _org()}
        )
        graph = state.to_graph()
        apply_mass_work_solidarity(
            graph, "vanguard", dict(graph.nodes["vanguard"]), "C900", defines
        )
        seeded = graph.get_edge("vanguard", "C900", EdgeType.SOLIDARITY.value)
        assert seeded is not None
        before = seeded.attributes["solidarity_strength"]

        compute_doctrine(graph, defines, tree, coeffs=_COEFFS)

        after_edge = graph.get_edge("vanguard", "C900", EdgeType.SOLIDARITY.value)
        assert after_edge is not None
        after = after_edge.attributes["solidarity_strength"]
        assert after == pytest.approx(before * (1.0 - defines.mass_work_solidarity_decay_rate))

    def test_decay_floors_at_zero_never_negative(self, tree: DoctrineTree) -> None:
        # Test-only large decay rate purely for observability over a
        # handful of ticks (mirrors the contract test's own precedent).
        fast_decay = DoctrineDefines(mass_work_solidarity_decay_rate=0.9)
        workers = SocialClass(id="C900", name="Workers", role=SocialRole.PERIPHERY_PROLETARIAT)
        state = WorldState(
            tick=0, entities={"C900": workers}, territories={}, organizations={"vanguard": _org()}
        )
        graph = state.to_graph()
        apply_mass_work_solidarity(
            graph, "vanguard", dict(graph.nodes["vanguard"]), "C900", fast_decay
        )

        max_ticks = 50  # fixed upper bound
        for _ in range(max_ticks):
            compute_doctrine(graph, fast_decay, tree, coeffs=_COEFFS)
            edge = graph.get_edge("vanguard", "C900", EdgeType.SOLIDARITY.value)
            assert edge is not None
            assert edge.attributes["solidarity_strength"] >= 0.0

    def test_class_sourced_solidarity_edges_are_untouched_by_doctrine_decay(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        """Regression: the two static SocialClass -> SocialClass SOLIDARITY
        producers (``scenarios/_legacy.py`` + ``_legacy_wayne.py``) must
        never be decayed by DoctrineSystem -- its loop only touches an ORG
        node's OWN outgoing edges, never a class-sourced edge."""
        worker_a = SocialClass(id="C900", name="Worker A", role=SocialRole.PERIPHERY_PROLETARIAT)
        worker_b = SocialClass(id="C901", name="Worker B", role=SocialRole.LABOR_ARISTOCRACY)
        solidarity = Relationship(
            source_id="C900",
            target_id="C901",
            edge_type=EdgeType.SOLIDARITY,
            solidarity_strength=0.5,
        )
        state = WorldState(
            tick=0,
            entities={"C900": worker_a, "C901": worker_b},
            territories={},
            relationships=[solidarity],
            organizations={"vanguard": _org()},
        )
        graph = state.to_graph()

        compute_doctrine(graph, defines, tree, coeffs=_COEFFS)

        edge = graph.get_edge("C900", "C901", EdgeType.SOLIDARITY.value)
        assert edge is not None
        assert edge.attributes["solidarity_strength"] == pytest.approx(0.5)


class TestLiquidationAbsorbingState:
    """P25 U11 (ADR137, §3.1): liquidationism is no longer a purchasable node but
    a MEASURED absorbing state — SOLIDARITY_MASS collapsed AND CO_OPTIVE_SHARE
    high AND the base embourgeoised (PETTY_BOURGEOIS_DRIFT). The topology decides;
    "you are not told you liquidated; you measurably did."
    """

    def _coopted(self) -> PoliticalFaction:
        # Holds trade_unionism (liquidationism reachable), cadre 0.17 ⟹
        # PETTY_BOURGEOIS_DRIFT 0.83, too poor to buy anything this tick.
        return _org(
            id="coopted",
            name="Co-opted",
            cadre_level=0.17,
            acquired_doctrine_ids=("class_consciousness", "trade_unionism"),
            theoretical_labor=5.0,
        )

    def test_co_opted_org_falls_into_liquidationism(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        state = WorldState(
            tick=0,
            entities={},
            territories={},
            relationships=[],
            organizations={"coopted": self._coopted(), "host": _org(id="host", name="Host")},
        )
        graph = state.to_graph()
        graph.add_edge("coopted", "host", EdgeType.TRANSACTIONAL.value, edge_mode="co_optive")
        events = compute_doctrine(graph, defines, tree, coeffs=_COEFFS)
        assert ("coopted", "liquidationism", "sprung") in events
        assert "liquidationism" in graph.nodes["coopted"]["acquired_doctrine_ids"]

    def test_a_live_solidarity_base_defeats_the_absorbing_state(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        # Same co-optive tie and cadre, but a live SOLIDARITY out-edge keeps
        # SOLIDARITY_MASS above the floor — autonomous capacity is proof against
        # liquidation, whatever the co-optation.
        workers = SocialClass(id="C900", name="Workers", role=SocialRole.PERIPHERY_PROLETARIAT)
        state = WorldState(
            tick=0,
            entities={"C900": workers},
            territories={},
            relationships=[],
            organizations={"coopted": self._coopted(), "host": _org(id="host", name="Host")},
        )
        graph = state.to_graph()
        graph.add_edge("coopted", "host", EdgeType.TRANSACTIONAL.value, edge_mode="co_optive")
        graph.add_edge("coopted", "C900", EdgeType.SOLIDARITY.value, solidarity_strength=0.5)
        events = compute_doctrine(graph, defines, tree, coeffs=_COEFFS)
        assert ("coopted", "liquidationism", "sprung") not in events
        assert "liquidationism" not in graph.nodes["coopted"]["acquired_doctrine_ids"]

    def test_reachable_but_unco_opted_org_stays_free(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        # Holds trade_unionism but has no co-optive ties: CO_OPTIVE_SHARE 0 keeps
        # the absorbing state dormant — the fork is a real dilemma, not a doom.
        state = WorldState(
            tick=0,
            entities={},
            territories={},
            relationships=[],
            organizations={"free": self._coopted().model_copy(update={"id": "free"})},
        )
        graph = state.to_graph()
        events = compute_doctrine(graph, defines, tree, coeffs=_COEFFS)
        assert ("free", "liquidationism", "sprung") not in events


class TestOfficeholderCapture:
    """P25 U11 (§3.1/§3.3): a governing org's office_tenure + institutional_pull
    accrue (Michels' iron law as a rate), and PRACTICE erodes its theory — the
    re-founded reformist trunk's tag drift, never acquisition tag_deltas."""

    def _gov_org(self) -> PoliticalFaction:
        return _org(
            id="gov",
            name="Gov",
            cadre_level=0.5,
            cohesion=0.5,
            acquired_doctrine_ids=("class_consciousness", "trade_unionism", "entryism"),
            theoretical_labor=0.0,
            doctrine_tags={DoctrineTag.CLASS_ANALYSIS: 5.0, DoctrineTag.MASS_LINK: 3.0},
        )

    def _graph(self, *, governs: bool = False, delivery_gap: float = 0.0):
        state = WorldState(
            tick=0,
            entities={},
            territories={},
            relationships=[],
            organizations={"gov": self._gov_org(), "host": _org(id="host", name="Host")},
        )
        graph = state.to_graph()
        if governs:
            graph.set_graph_attr(
                "electoral_governments", {"S1": {"party_id": "gov", "formed_tick": 0, "share": 0.5}}
            )
        if delivery_gap > 0.0:
            graph.set_graph_attr(
                "policy_delivery",
                {"C1": {"incumbent_id": "gov", "promised": delivery_gap, "delivered": 0.0}},
            )
        return graph

    def _ca(self, graph) -> float:
        return graph.nodes["gov"]["doctrine_tags"][DoctrineTag.CLASS_ANALYSIS]

    def test_governing_org_accrues_tenure_and_pull(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        graph = self._graph(governs=True)
        compute_doctrine(graph, defines, tree, coeffs=_COEFFS)
        node = graph.nodes["gov"]
        assert node["office_tenure"] == pytest.approx(1.0)
        assert node["institutional_pull"] > 0.0

    def test_out_of_office_no_accrual_and_hysteresis(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        graph = self._graph(governs=False)
        compute_doctrine(graph, defines, tree, coeffs=_COEFFS)
        node = graph.nodes["gov"]
        assert node["office_tenure"] == pytest.approx(0.0)
        assert node["institutional_pull"] == pytest.approx(0.0)

    def test_institutional_pull_erodes_class_analysis(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        gov = self._graph(governs=True)
        free = self._graph(governs=False)
        compute_doctrine(gov, defines, tree, coeffs=_COEFFS)
        compute_doctrine(free, defines, tree, coeffs=_COEFFS)
        assert self._ca(gov) < self._ca(free)  # Michels theory-rot, below plain decay

    def test_delivery_gap_erodes_class_analysis(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        withgap = self._graph(governs=False, delivery_gap=1.0)
        nogap = self._graph(governs=False)
        compute_doctrine(withgap, defines, tree, coeffs=_COEFFS)
        compute_doctrine(nogap, defines, tree, coeffs=_COEFFS)
        assert self._ca(withgap) < self._ca(nogap)  # the veto's trace rots theory

    def test_co_optive_dependence_erodes_mass_link(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        withco = self._graph(governs=False)
        withco.add_edge("gov", "host", EdgeType.TRANSACTIONAL.value, edge_mode="co_optive")
        noco = self._graph(governs=False)
        compute_doctrine(withco, defines, tree, coeffs=_COEFFS)
        compute_doctrine(noco, defines, tree, coeffs=_COEFFS)
        gov_ml = withco.nodes["gov"]["doctrine_tags"][DoctrineTag.MASS_LINK]
        free_ml = noco.nodes["gov"]["doctrine_tags"][DoctrineTag.MASS_LINK]
        assert gov_ml < free_ml  # a base held by concessions is not a mass link


class TestCadreValveDecouple:
    """P25 U11 commit G (§3.2): principled abstention is immune to Michels.

    ``abstention_boycott`` is the only stance whose ``DoctrineCapability`` sets
    ``cadre_valve_decouple``. An org holding it still records the FACT of office
    (tenure accrues — the register says it governs) but seats no cadre, so no
    institutional pull accrues and no pull-driven theory rot follows. That
    immunity is exactly what the stance's sect-isolation cost buys.
    """

    def _org_holding(self, *stances: str) -> PoliticalFaction:
        return _org(
            id="gov",
            name="Gov",
            cadre_level=0.5,
            cohesion=0.5,
            acquired_doctrine_ids=("class_consciousness", "trade_unionism", *stances),
            theoretical_labor=0.0,
            doctrine_tags={DoctrineTag.CLASS_ANALYSIS: 5.0, DoctrineTag.MASS_LINK: 3.0},
        )

    def _governing_graph(self, *stances: str):
        state = WorldState(
            tick=0,
            entities={},
            territories={},
            relationships=[],
            organizations={"gov": self._org_holding(*stances)},
        )
        graph = state.to_graph()
        graph.set_graph_attr(
            "electoral_governments", {"S1": {"party_id": "gov", "formed_tick": 0, "share": 0.5}}
        )
        return graph

    def test_abstentionist_records_tenure_but_takes_no_pull(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        graph = self._governing_graph("abstention_boycott")
        compute_doctrine(graph, defines, tree, coeffs=_COEFFS)
        node = graph.nodes["gov"]
        assert node["office_tenure"] == pytest.approx(1.0), "the office is still a fact"
        assert node["institutional_pull"] == pytest.approx(0.0), "no cadre seated, no capture"

    def test_a_non_decoupled_stance_is_captured_on_the_same_graph(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        """The control: identical shape, entryism instead of abstention."""
        graph = self._governing_graph("entryism")
        compute_doctrine(graph, defines, tree, coeffs=_COEFFS)
        node = graph.nodes["gov"]
        assert node["office_tenure"] == pytest.approx(1.0)
        assert node["institutional_pull"] > 0.0

    def test_decoupling_spares_the_pull_driven_theory_rot(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        abstain = self._governing_graph("abstention_boycott")
        entry = self._governing_graph("entryism")
        compute_doctrine(abstain, defines, tree, coeffs=_COEFFS)
        compute_doctrine(entry, defines, tree, coeffs=_COEFFS)
        abstain_ca = abstain.nodes["gov"]["doctrine_tags"][DoctrineTag.CLASS_ANALYSIS]
        entry_ca = entry.nodes["gov"]["doctrine_tags"][DoctrineTag.CLASS_ANALYSIS]
        assert abstain_ca > entry_ca


class TestPoliticalFormRegister:
    """P25 U11 commit H (§3.4): DoctrineSystem publishes the org-scale poles.

    The register is the producer half of the ``political_form`` opposition's
    organizational reading — the seam ContradictionSystem @18.0 threads one tick
    later (I-ORD). Owner row: ``sentinels/superstructure/registry.py``.
    """

    def _graph(self, *, governs: bool, mass_link: float):
        org = _org(
            id="gov",
            name="Gov",
            cadre_level=0.5,
            cohesion=0.5,
            acquired_doctrine_ids=("class_consciousness", "trade_unionism", "entryism"),
            theoretical_labor=0.0,
            doctrine_tags={DoctrineTag.MASS_LINK: mass_link},
        )
        state = WorldState(
            tick=0, entities={}, territories={}, relationships=[], organizations={"gov": org}
        )
        graph = state.to_graph()
        if governs:
            graph.set_graph_attr(
                "electoral_governments", {"S1": {"party_id": "gov", "formed_tick": 0, "share": 0.5}}
            )
        return graph

    def test_org_less_world_publishes_nothing(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        """Byte-safety for the qa six: no orgs, no register, no fabricated
        (0, 0) organizational position (III.11)."""
        state = WorldState(tick=0, entities={}, territories={}, relationships=[], organizations={})
        graph = state.to_graph()
        compute_doctrine(graph, defines, tree, coeffs=_COEFFS)
        assert graph.get_graph_attr("political_form_org_positions", None) is None

    def test_every_org_gets_a_bounded_position(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        graph = self._graph(governs=False, mass_link=1.0)
        compute_doctrine(graph, defines, tree, coeffs=_COEFFS)
        register = graph.get_graph_attr("political_form_org_positions", None)
        assert register is not None
        position = register["gov"]
        assert 0.0 <= position["self_organization"] <= 1.0
        assert 0.0 <= position["representation"] <= 1.0

    def test_mass_link_raises_the_self_organization_pole(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        weak = self._graph(governs=False, mass_link=0.0)
        strong = self._graph(governs=False, mass_link=5.0)
        compute_doctrine(weak, defines, tree, coeffs=_COEFFS)
        compute_doctrine(strong, defines, tree, coeffs=_COEFFS)
        weak_a = weak.get_graph_attr("political_form_org_positions", None)["gov"]
        strong_a = strong.get_graph_attr("political_form_org_positions", None)["gov"]
        assert strong_a["self_organization"] > weak_a["self_organization"]

    def test_holding_office_raises_the_representation_pole(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        out = self._graph(governs=False, mass_link=1.0)
        seated = self._graph(governs=True, mass_link=1.0)
        compute_doctrine(out, defines, tree, coeffs=_COEFFS)
        compute_doctrine(seated, defines, tree, coeffs=_COEFFS)
        out_b = out.get_graph_attr("political_form_org_positions", None)["gov"]
        seated_b = seated.get_graph_attr("political_form_org_positions", None)["gov"]
        assert seated_b["representation"] > out_b["representation"]


class TestLineStruggleSplit:
    """P25 U11 (§3.3): an org holding >1 reformist stance resolves the line
    struggle at congress — consolidates to its newest line, sheds the earlier
    branches' assets (split_asset_retention), and publishes LINE_STRUGGLE_SPLIT."""

    def test_congress_consolidates_stances_and_sheds_assets(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        splitter = _org(
            id="splitter",
            name="Splitter",
            cadre_level=0.5,
            acquired_doctrine_ids=(
                "class_consciousness",
                "trade_unionism",
                "abstention_boycott",
                "entryism",
            ),
            theoretical_labor=100.0,
        )
        state = WorldState(
            tick=0,
            entities={},
            territories={},
            relationships=[],
            organizations={"splitter": splitter},
        )
        graph = state.to_graph()
        interval = defines.congress_interval_ticks
        events = compute_doctrine(
            graph, defines, tree, tick=interval, rng=random.Random(0), coeffs=_COEFFS
        )
        node = graph.nodes["splitter"]
        acquired = node["acquired_doctrine_ids"]
        # Consolidated to the newest stance (entryism); the earlier one is shed.
        assert "entryism" in acquired
        assert "abstention_boycott" not in acquired
        assert any(kind == "line_split" and org == "splitter" for org, _, kind in events)
        # TL retained at split_asset_retention (× 0.4), then the ordinary tick ran.
        assert node["theoretical_labor"] < 100.0 * 0.4 + 1.0

    def test_single_stance_org_holds_no_line_struggle(
        self, tree: DoctrineTree, defines: DoctrineDefines
    ) -> None:
        steady = _org(
            id="steady",
            name="Steady",
            cadre_level=0.5,
            acquired_doctrine_ids=("class_consciousness", "trade_unionism", "entryism"),
            theoretical_labor=100.0,
        )
        state = WorldState(
            tick=0,
            entities={},
            territories={},
            relationships=[],
            organizations={"steady": steady},
        )
        graph = state.to_graph()
        interval = defines.congress_interval_ticks
        events = compute_doctrine(
            graph, defines, tree, tick=interval, rng=random.Random(0), coeffs=_COEFFS
        )
        assert not any(kind == "line_split" for _, _, kind in events)
        assert "entryism" in graph.nodes["steady"]["acquired_doctrine_ids"]

    def test_system_publishes_line_struggle_split_event(self, defines: DoctrineDefines) -> None:
        # The real System + a real ServiceContainer bus: U11 is the first
        # PUBLISHER of LINE_STRUGGLE_SPLIT (payload + builder + severity landed U2).
        splitter = _org(
            id="splitter",
            name="Splitter",
            cadre_level=0.5,
            acquired_doctrine_ids=(
                "class_consciousness",
                "trade_unionism",
                "abstention_boycott",
                "entryism",
            ),
            theoretical_labor=100.0,
        )
        state = WorldState(
            tick=0,
            entities={},
            territories={},
            relationships=[],
            organizations={"splitter": splitter},
        )
        graph = state.to_graph()
        services = ServiceContainer.create()
        captured: list = []
        services.event_bus.subscribe(EventType.LINE_STRUGGLE_SPLIT, lambda e: captured.append(e))
        try:
            DoctrineSystem().step(
                graph, services, TickContext(tick=defines.congress_interval_ticks)
            )
        finally:
            services.database.close()

        assert len(captured) == 1
        assert captured[0].payload["org_id"] == "splitter"
        assert captured[0].payload["new_stance"] == "entryism"
        assert captured[0].payload["old_stance"] == "abstention_boycott"
        assert captured[0].payload["assets_retained"] == pytest.approx(0.4)


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
    trapped org_c) → 8a5caa58… → regenerated for P25 U11 commit D (the doctrine
    fork's STRUCTURE: the reformist trunk is replaced by the five electoral
    stances forked under trade_unionism with ZERO acquisition tag_deltas, plus
    liquidationism as a single-parent absorbing-state trap — the greedy
    auto-acquire now walks a different node/cost set) → 117cc594… → regenerated
    for P25 U11 commit E (the fork's BEHAVIOR: the measured practice env now
    drives trap firing — org_c gains a ``co_optive`` tie and, with no SOLIDARITY
    base and cadre 0.17, enters the liquidationism ABSORBING STATE via its
    ``@coeff`` condition) → 6626c287… → regenerated for commit E2 (officeholder
    capture + practice→tag drift: org_c also holds office via the
    electoral_governments register, so office_tenure + institutional_pull accrue
    — now HASHED in the payload — and co-optive dependence erodes MASS_LINK) →
    095125a1… → regenerated for commit F (line-changes-as-splits: org_c holds all
    five reformist stances, so the tick-52 congress resolves the line struggle —
    consolidates to its newest line, sheds the others and retains only
    split_asset_retention of its TL) → 28ccad1f… → regenerated for commit G (the
    cadre valve: org_c holds ``abstention_boycott``, whose DoctrineCapability sets
    ``cadre_valve_decouple``, so while it governs it now records office_tenure but
    accrues NO institutional_pull — and therefore none of the pull-driven theory
    rot either). All DELIBERATE, documented behavior changes.

    Commit-G attribution was PROVED, not assumed: with ``_decouples_cadre_valve``
    forced to ``False`` the chain reproduces 28ccad1f… byte-for-byte, so the whole
    drift is the cadre valve and nothing else.
    """

    TICKS = 100
    # Regenerate: run _chain_digest() and paste; see class docstring.
    GOLDEN_CHAIN = "11e0bb2e868805bdec0c026fe8a355f2daf7d6bef7a0476a66da1906f96e7ad2"

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
                        # Every purchasable node held except the liquidationism
                        # trap, so greedy has nothing left to buy and the 400 TL
                        # survives to the tick-52 congress purge. P25 U11: the
                        # reformist chain is now the five electoral stances.
                        "class_consciousness",
                        "trade_unionism",
                        "abstention_boycott",
                        "class_struggle_elections",
                        "entryism",
                        "independent_ballot_line",
                        "governance_road",
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
        # A co-optive tie on org_c (cadre 0.17 → PETTY_BOURGEOIS_DRIFT 0.83, and
        # no SOLIDARITY out-edges → SOLIDARITY_MASS 0) drives it into the
        # liquidationism absorbing state — the practice-gated firing path the
        # golden must cover (P25 U11 commit E; agent-4 fixture-coverage fix).
        graph.add_edge("org_c", "org_a", EdgeType.TRANSACTIONAL.value, edge_mode="co_optive")
        # org_c also holds office (electoral_governments register, read one tick
        # stale) → officeholder capture accrues office_tenure + institutional_pull
        # each tick, covering the §3.3 capture path in the golden.
        graph.set_graph_attr(
            "electoral_governments",
            {"SOV1": {"party_id": "org_c", "formed_tick": 0, "share": 0.5}},
        )
        defines = DoctrineDefines()
        tree = load_doctrine_tree()
        rng = random.Random(0xD0C7)
        chain = hashlib.sha256()
        for i in range(TestDoctrineDeterminism.TICKS):
            compute_doctrine(graph, defines, tree, tick=i + 1, rng=rng, coeffs=_COEFFS)
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
                    # P25 U11 commit E2: officeholder capture is hashed so the
                    # chain covers office_tenure + institutional_pull accrual.
                    "office": repr(node.attributes.get("office_tenure", 0.0)),
                    "pull": repr(node.attributes.get("institutional_pull", 0.0)),
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
        # DoctrineSystem.step now reads the politics coefficients (P25 U11) —
        # a MagicMock would hand back un-float()-able mocks, so stub the real one.
        services.defines.politics = PoliticsDefines()
        DoctrineSystem().step(graph, services, TickContext())
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
            DoctrineSystem().step(graph, services, TickContext(tick=1))
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
            DoctrineSystem().step(graph, services, TickContext(tick=1))
        finally:
            services.database.close()

        assert captured == []
