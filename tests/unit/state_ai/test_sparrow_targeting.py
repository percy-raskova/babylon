"""Unit tests for Sparrow topological REPRESS targeting (Constitution I.21,
Adversary Train task W3).

Before this fix, ``select_repress_target`` sorted candidates by
``Heat * Visibility`` with ``visibility`` hardcoded to ``1.0`` for every
candidate (an honest interim stand-in, per its own docstring). These tests
pin the real wiring: the Sparrow module (``ooda/attention/sparrow.py``,
Feature 039) already computes centrality/cutset/singleton structure on any
observed subgraph; this train connects that computation to the REPRESS
decision path per the ratified targeting-mode correspondence (Constitution
I.21): Surveil -> singleton, Infiltrate -> cutset, Raid/Liquidate ->
centrality.

Material grounding (Aleksandrov Test): the state hunting SOLIDARITY-graph
hubs and bridges IS the material relation the Sparrow/Krebs network-
vulnerability doctrine names (``ai/spec-prompts/enemy-ai/coin.md`` #1) --
covert-network disruption targets an organization's structural position in
the player's organizing network, not raw heat/activity.

See Also:
    ``tests/unit/state_ai/test_decision_targeting.py``: the pre-W3 pure
    Heat x Visibility contract -- those tests must keep passing unchanged
    (``topology_scores=None`` / ``sparrow_topology_scores=None`` defaults).
    ``tests/unit/state_ai/test_sparrow.py``: the underlying centrality/
    cutset/singleton algorithms this train reuses, unmodified.
"""

from __future__ import annotations

from babylon.config.defines import GameDefines
from babylon.models.entities.state_apparatus_ai import FactionBalance, StateBudget
from babylon.models.enums import NodeType, OrgType, StateActionType
from babylon.ooda.npc_stub import (
    _compute_sparrow_topology_scores,
    _gather_repress_target_candidates,
    select_npc_actions,
)
from babylon.ooda.state_ai.decision import RuleBasedStateAI, select_repress_target
from babylon.topology.graph import BabylonGraph
from tests.unit.state_ai.conftest import make_org_solidarity_double_star_with_bridge

_ORG_ID = "apparatus_detroit_pd"

# Pure Security-State faction balance + the two heat values (empirically
# verified, see the class docstrings below) that make RAID and INFILTRATE
# respectively win RuleBasedStateAI's verb-scoring competition by a wide
# margin (>>0.01, the rng tiebreaker's ceiling) under the default
# StateApparatusAIDefines escalation ladder.
_SECURITY_STATE_BALANCE: dict[str, float] = {
    "finance_capital": 0.0,
    "security_state": 1.0,
    "settler_populist": 0.0,
    "stability": 0.5,
    "legitimacy": 0.5,
}
_RAID_BIASED_HEAT = 0.667
_INFILTRATE_BIASED_HEAT = 0.333

# Per-candidate heat values for the double-star-with-bridge fixture. Bridge
# is given the highest heat so it wins the tie among the three cutset
# members {hub_a, hub_b, bridge} (all score 1.0 under INFILTRATE mode);
# hub_a is given a higher heat than hub_b so it (not its symmetric twin)
# wins the RAID/centrality tie.
_CANDIDATE_HEATS: dict[str, float] = {
    "org_hub_a": 0.6,
    "org_hub_b": 0.4,
    "org_bridge": 0.8,
}
_LEAF_HEAT = 0.3


def _make_double_star_graph() -> BabylonGraph:
    """The Sparrow fixture graph, plus a heat attribute on every org node
    and an excluded STATE_APPARATUS org (``_ORG_ID``)."""
    graph = make_org_solidarity_double_star_with_bridge()
    graph.add_node(_ORG_ID, NodeType.ORGANIZATION, org_type=OrgType.STATE_APPARATUS.value, heat=0.0)
    for node_id in graph.nodes:
        if node_id == _ORG_ID:
            continue
        heat = _CANDIDATE_HEATS.get(node_id, _LEAF_HEAT)
        graph.update_node(node_id, org_type=OrgType.CIVIL_SOCIETY.value, heat=heat)
    return graph


def _make_budget() -> StateBudget:
    return StateBudget(
        revenue=100.0,
        available=100.0,
        allocated={
            StateActionType.ADMINISTER: 15.0,
            StateActionType.DEVELOP: 15.0,
            StateActionType.RESEARCH: 10.0,
            StateActionType.CO_OPT: 20.0,
            StateActionType.REPRESS: 30.0,
            StateActionType.WITHDRAW: 10.0,
        },
        imperial_rent_pool=50.0,
    )


# ===========================================================================
# select_repress_target — pure function, topology_scores dimension
# ===========================================================================


class TestSelectRepressTargetTopologyScores:
    """The Sparrow topology score can outrank raw heat, but only when it
    carries real signal -- never collapses to a pure id tie-break."""

    def test_topology_score_overrides_higher_raw_heat(self) -> None:
        """A lower-heat, high-centrality candidate beats a higher-heat,
        zero-centrality one once topology_scores carries real signal."""
        candidates = [("org_low_heat_hub", 0.2), ("org_high_heat_leaf", 0.9)]
        topology_scores = {"org_low_heat_hub": 1.0, "org_high_heat_leaf": 0.0}
        assert (
            select_repress_target(_ORG_ID, candidates, topology_scores=topology_scores)
            == "org_low_heat_hub"
        )

    def test_missing_candidate_key_defaults_to_zero(self) -> None:
        """A candidate absent from topology_scores is honestly scored 0.0
        (no fabricated structural signal), not treated as neutral."""
        candidates = [("org_scored", 0.3), ("org_unscored", 0.9)]
        topology_scores = {"org_scored": 1.0}
        assert (
            select_repress_target(_ORG_ID, candidates, topology_scores=topology_scores)
            == "org_scored"
        )

    def test_all_zero_topology_scores_falls_back_to_heat_only(self) -> None:
        """When every eligible candidate's topology score is 0.0 (no
        structural signal this tick), the Blind Giant reverts to the
        pre-W3 plain heat*visibility sort rather than degenerating to a
        pure id tie-break. "org_apple" sorts first lexicographically but
        has the lower heat -- a broken all-zero-multiplier sort would
        pick it by id; the correct fallback picks "org_zebra" by heat."""
        candidates = [("org_apple", 0.2), ("org_zebra", 0.9)]
        topology_scores = {"org_apple": 0.0, "org_zebra": 0.0}
        assert (
            select_repress_target(_ORG_ID, candidates, topology_scores=topology_scores)
            == "org_zebra"
        )

    def test_topology_scores_none_matches_legacy_behavior(self) -> None:
        """``topology_scores=None`` (the default) is byte-for-byte the
        pre-W3 contract -- see test_decision_targeting.py for the full
        suite this must keep agreeing with."""
        candidates = [("org_low", 0.2), ("org_high", 0.9), ("org_mid", 0.5)]
        assert select_repress_target(_ORG_ID, candidates) == "org_high"


# ===========================================================================
# _compute_sparrow_topology_scores — real graph topology, real sparrow.py
# ===========================================================================


class TestComputeSparrowTopologyScores:
    """Scores derived from a real SOLIDARITY subgraph via the unmodified
    Sparrow centrality/cutset/singleton functions."""

    def test_centrality_scores_rank_the_hubs_highest(self) -> None:
        graph = _make_double_star_graph()
        candidates = _gather_repress_target_candidates(_ORG_ID, graph)
        assert candidates is not None
        scores = _compute_sparrow_topology_scores(candidates, graph)

        centrality = scores[StateActionType.RAID]
        assert centrality["org_hub_a"] == max(centrality.values())
        assert centrality["org_hub_b"] == max(centrality.values())
        assert centrality["org_bridge"] < centrality["org_hub_a"]
        assert centrality["org_leafA1"] < centrality["org_bridge"]

    def test_raid_and_liquidate_share_centrality_scores(self) -> None:
        graph = _make_double_star_graph()
        candidates = _gather_repress_target_candidates(_ORG_ID, graph)
        assert candidates is not None
        scores = _compute_sparrow_topology_scores(candidates, graph)
        assert scores[StateActionType.RAID] == scores[StateActionType.LIQUIDATE]

    def test_cutset_scores_flag_the_bridge(self) -> None:
        graph = _make_double_star_graph()
        candidates = _gather_repress_target_candidates(_ORG_ID, graph)
        assert candidates is not None
        scores = _compute_sparrow_topology_scores(candidates, graph)

        cutset = scores[StateActionType.INFILTRATE]
        assert cutset["org_bridge"] == 1.0
        # A tree-shaped join makes every non-leaf node on the unique
        # connecting path a cut vertex too (same property as a plain path
        # graph's inner nodes, test_sparrow.py::TestSparrowCutsets) --
        # asserted honestly rather than claiming bridge is the sole cutset.
        assert cutset["org_hub_a"] == 1.0
        assert cutset["org_hub_b"] == 1.0
        assert cutset["org_leafA1"] == 0.0
        assert cutset["org_leafB1"] == 0.0

    def test_empty_solidarity_subgraph_yields_all_zero_scores(self) -> None:
        """No SOLIDARITY edges among candidates (the common case today --
        no verb writes org-to-org SOLIDARITY yet) -> every mode's score
        map is honestly all-zero, never a fabricated structural signal."""
        graph = BabylonGraph()
        for org_id in ("org_a", "org_b", "org_c"):
            graph.add_node(org_id, NodeType.ORGANIZATION, heat=0.5)
        candidates = [(oid, 0.5) for oid in ("org_a", "org_b", "org_c")]

        scores = _compute_sparrow_topology_scores(candidates, graph)

        for mode in (
            StateActionType.RAID,
            StateActionType.LIQUIDATE,
            StateActionType.INFILTRATE,
            StateActionType.SURVEIL,
        ):
            assert all(v == 0.0 for v in scores[mode].values())

    def test_deterministic_across_repeated_calls(self) -> None:
        """Pure function of the graph's current SOLIDARITY edges -- same
        graph in, same scores out, every time (Constitution III.7)."""
        graph = _make_double_star_graph()
        candidates = _gather_repress_target_candidates(_ORG_ID, graph)
        assert candidates is not None

        first = _compute_sparrow_topology_scores(candidates, graph)
        second = _compute_sparrow_topology_scores(candidates, graph)
        assert first == second


# ===========================================================================
# RuleBasedStateAI.select_action — end-to-end, real graph + real dispatch
# ===========================================================================


class TestSparrowEndToEndTargeting:
    """Given a player org graph with a clear hub and a clear bridge: Raid
    picks the hub, Infiltrate picks the bridge (Constitution I.21)."""

    def test_raid_targets_the_hub(self) -> None:
        graph = _make_double_star_graph()
        candidates = _gather_repress_target_candidates(_ORG_ID, graph)
        assert candidates is not None
        topology_scores = _compute_sparrow_topology_scores(candidates, graph)

        ai = RuleBasedStateAI()
        actions = ai.select_action(
            org_id=_ORG_ID,
            faction_balance=FactionBalance(**_SECURITY_STATE_BALANCE),
            budget=_make_budget(),
            heat=_RAID_BIASED_HEAT,
            defines=GameDefines().state_ai,
            rng_seed=0,
            target_candidates=candidates,
            sparrow_topology_scores=topology_scores,
        )

        assert len(actions) == 1
        assert actions[0].sub_verb == StateActionType.RAID
        assert actions[0].target_id == "org_hub_a"

    def test_infiltrate_targets_the_bridge(self) -> None:
        graph = _make_double_star_graph()
        candidates = _gather_repress_target_candidates(_ORG_ID, graph)
        assert candidates is not None
        topology_scores = _compute_sparrow_topology_scores(candidates, graph)

        ai = RuleBasedStateAI()
        actions = ai.select_action(
            org_id=_ORG_ID,
            faction_balance=FactionBalance(**_SECURITY_STATE_BALANCE),
            budget=_make_budget(),
            heat=_INFILTRATE_BIASED_HEAT,
            defines=GameDefines().state_ai,
            rng_seed=0,
            target_candidates=candidates,
            sparrow_topology_scores=topology_scores,
        )

        assert len(actions) == 1
        assert actions[0].sub_verb == StateActionType.INFILTRATE
        assert actions[0].target_id == "org_bridge"

    def test_public_dispatch_surface_targets_the_hub(self) -> None:
        """Same proof, through the real public entry point
        (``select_npc_actions``) rather than internals -- confirms the
        wiring is reachable end-to-end, not just correct in isolation."""
        from babylon.config.defines import OODADefines

        graph = _make_double_star_graph()
        actions = select_npc_actions(
            org_id=_ORG_ID,
            org_attrs={
                "org_type": OrgType.STATE_APPARATUS.value,
                "heat": _RAID_BIASED_HEAT,
                "faction_balance": _SECURITY_STATE_BALANCE,
                "rng_seed": 0,
            },
            target_id="community_1",
            defines=OODADefines(),
            graph=graph,
        )

        assert len(actions) == 1
        assert actions[0].target_id == "org_hub_a"

    def test_determinism_same_graph_same_seed_same_target(self) -> None:
        """Same graph + same seed -> identical target, every time."""
        graph = _make_double_star_graph()
        candidates = _gather_repress_target_candidates(_ORG_ID, graph)
        assert candidates is not None
        topology_scores = _compute_sparrow_topology_scores(candidates, graph)

        results = []
        max_runs = 5
        for _ in range(max_runs):
            ai = RuleBasedStateAI()
            actions = ai.select_action(
                org_id=_ORG_ID,
                faction_balance=FactionBalance(**_SECURITY_STATE_BALANCE),
                budget=_make_budget(),
                heat=_INFILTRATE_BIASED_HEAT,
                defines=GameDefines().state_ai,
                rng_seed=7,
                target_candidates=candidates,
                sparrow_topology_scores=topology_scores,
            )
            results.append(tuple((a.sub_verb, a.target_id) for a in actions))

        assert len(set(results)) == 1
        assert results[0] == ((StateActionType.INFILTRATE, "org_bridge"),)
