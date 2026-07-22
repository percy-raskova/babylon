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
from tests.unit.state_ai.conftest import (
    make_org_solidarity_biconnected_clusters_with_unique_bridge,
    make_org_solidarity_double_star_with_bridge,
)

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
_SURVEIL_BIASED_HEAT = 0.2  # surveil_state's escalation_ladder rank (3) / max_rank (15)

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

# Every candidate given the SAME heat -- isolates SURVEIL's isolation
# score as the sole driver of target choice (no heat confound at all).
_UNIFORM_HEAT = 0.5

# Per-candidate heat values for the biconnected-clusters-with-unique-bridge
# fixture: ``bridge`` deliberately gets the LOWEST heat of any candidate
# (every other node is 0.6-0.9) so that Infiltrate picking it can only be
# explained by the (unique, untied) cutset score -- heat actively argues
# AGAINST bridge here.
_UNIQUE_BRIDGE_CANDIDATE_HEATS: dict[str, float] = {
    "org_bridge": 0.1,
    "org_hub_a": 0.9,
    "org_hub_b": 0.85,
    "org_leafA1": 0.8,
}
_UNIQUE_BRIDGE_OTHER_HEAT = 0.6


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


def _make_unique_bridge_graph() -> BabylonGraph:
    """The biconnected-clusters-with-unique-bridge fixture, with ``bridge``
    given the LOWEST heat of any candidate (see
    ``_UNIQUE_BRIDGE_CANDIDATE_HEATS``) -- heat actively argues against
    ``bridge`` winning, isolating the cutset score as the only possible
    explanation for Infiltrate picking it anyway."""
    graph = make_org_solidarity_biconnected_clusters_with_unique_bridge()
    graph.add_node(_ORG_ID, NodeType.ORGANIZATION, org_type=OrgType.STATE_APPARATUS.value, heat=0.0)
    for node_id in graph.nodes:
        if node_id == _ORG_ID:
            continue
        heat = _UNIQUE_BRIDGE_CANDIDATE_HEATS.get(node_id, _UNIQUE_BRIDGE_OTHER_HEAT)
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
    Sparrow centrality/cutset/degree functions (isolation is 1 - degree,
    never sparrow.py's misleadingly-named ``identified_singletons``)."""

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

    def test_isolation_scores_rank_the_leaves_highest(self) -> None:
        """SURVEIL's isolation score is 1 - degree_centrality: the LEAST
        connected nodes (leaves) rank highest, the hubs lowest -- the
        opposite ranking from RAID's centrality (Constitution I.21:
        Surveil targets the periphery, Raid targets the hub). Regression
        guard for the review fix: this must NOT be
        ``analysis.identified_singletons`` (sparrow.py's "singleton" means
        critical hub -- the inverse of what this test asserts)."""
        graph = _make_double_star_graph()
        candidates = _gather_repress_target_candidates(_ORG_ID, graph)
        assert candidates is not None
        scores = _compute_sparrow_topology_scores(candidates, graph)

        isolation = scores[StateActionType.SURVEIL]
        assert isolation["org_leafA1"] == max(isolation.values())
        assert isolation["org_leafB1"] == max(isolation.values())
        assert isolation["org_bridge"] < isolation["org_leafA1"]
        assert isolation["org_hub_a"] < isolation["org_bridge"]
        assert isolation["org_hub_b"] < isolation["org_bridge"]
        # And it is exactly the complement of RAID's centrality score
        # keyed by degree alone -- not a copy of the old singleton set.
        assert isolation["org_hub_a"] != scores[StateActionType.RAID]["org_hub_a"]

    def test_cutset_scores_flag_the_unique_articulation_point(self) -> None:
        """On a graph engineered so ``bridge`` is the SOLE cut vertex (see
        :func:`make_org_solidarity_biconnected_clusters_with_unique_bridge`
        's docstring for the graph-theoretic proof), the cutset score is
        1.0 for ``bridge`` and 0.0 for every other node -- no tie, unlike
        the tree-shaped double-star fixture where hub_a/hub_b are honest
        cut vertices too."""
        prefix = "org_"
        graph = make_org_solidarity_biconnected_clusters_with_unique_bridge(prefix)
        graph.add_node(
            _ORG_ID, NodeType.ORGANIZATION, org_type=OrgType.STATE_APPARATUS.value, heat=0.0
        )
        for node_id in graph.nodes:
            if node_id == _ORG_ID:
                continue
            graph.update_node(node_id, org_type=OrgType.CIVIL_SOCIETY.value, heat=0.5)

        candidates = _gather_repress_target_candidates(_ORG_ID, graph)
        assert candidates is not None
        scores = _compute_sparrow_topology_scores(candidates, graph)

        cutset = scores[StateActionType.INFILTRATE]
        assert cutset[f"{prefix}bridge"] == 1.0
        for suffix in (
            "hub_a",
            "leafA1",
            "leafA2",
            "leafA3",
            "hub_b",
            "leafB1",
            "leafB2",
            "leafB3",
        ):
            assert cutset[f"{prefix}{suffix}"] == 0.0

    def test_empty_solidarity_subgraph_yields_all_zero_centrality_and_cutset_scores(self) -> None:
        """No SOLIDARITY edges among candidates (the common case today --
        no verb writes org-to-org SOLIDARITY yet) -> RAID/LIQUIDATE/
        INFILTRATE (centrality- and cutset-based) are honestly all-zero,
        never a fabricated structural signal -- there are no edges to
        compute either metric from."""
        graph = BabylonGraph()
        for org_id in ("org_a", "org_b", "org_c"):
            graph.add_node(org_id, NodeType.ORGANIZATION, heat=0.5)
        candidates = [(oid, 0.5) for oid in ("org_a", "org_b", "org_c")]

        scores = _compute_sparrow_topology_scores(candidates, graph)

        for mode in (
            StateActionType.RAID,
            StateActionType.LIQUIDATE,
            StateActionType.INFILTRATE,
        ):
            assert all(v == 0.0 for v in scores[mode].values())

    def test_empty_solidarity_subgraph_yields_uniform_isolation_scores(self) -> None:
        """SURVEIL (isolation-based) is the opposite case from RAID/
        LIQUIDATE/INFILTRATE above: zero SOLIDARITY edges is the
        textbook-purest form of isolation (I.21: "vulnerable because they
        lack solidarity edges"), so every candidate honestly scores 1.0
        (uniformly maximally isolated), not 0.0. A uniform non-zero
        multiplier still ranks candidates by heat alone (multiplying every
        score by the same constant changes no ordering), so this remains
        behaviorally identical to the heat-only fallback despite the score
        value itself being non-zero."""
        graph = BabylonGraph()
        for org_id in ("org_a", "org_b", "org_c"):
            graph.add_node(org_id, NodeType.ORGANIZATION, heat=0.5)
        candidates = [(oid, 0.5) for oid in ("org_a", "org_b", "org_c")]

        scores = _compute_sparrow_topology_scores(candidates, graph)

        assert all(v == 1.0 for v in scores[StateActionType.SURVEIL].values())

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
    picks the hub, Infiltrate picks the bridge, Surveil picks the
    periphery (Constitution I.21)."""

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

    def test_infiltrate_targets_the_unique_bridge_despite_lowest_heat(self) -> None:
        """Review-fix strengthening of ``test_infiltrate_targets_the_bridge``
        above: that test's double-star fixture is a tree, so its cutset is
        {hub_a, hub_b, bridge} (all tied at score 1.0) and bridge only wins
        because it ALSO has the highest heat -- the topology claim there
        rests on heat as much as structure. Here ``bridge`` is the graph's
        SOLE articulation point (cutset score 1.0, everyone else 0.0 --
        no tie) AND has the LOWEST heat of any candidate (0.1, vs. 0.6-0.9
        for everyone else) -- heat argues AGAINST bridge winning. Infiltrate
        still resolves to ``org_bridge``, which can only be explained by
        the cutset/topology score: this isolates topology as the sole
        driver, with heat held adversarial rather than merely absent."""
        graph = _make_unique_bridge_graph()
        candidates = _gather_repress_target_candidates(_ORG_ID, graph)
        assert candidates is not None
        topology_scores = _compute_sparrow_topology_scores(candidates, graph)
        assert topology_scores[StateActionType.INFILTRATE]["org_bridge"] == 1.0
        assert all(
            v == 0.0
            for k, v in topology_scores[StateActionType.INFILTRATE].items()
            if k != "org_bridge"
        )

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

    def test_surveil_targets_an_isolated_leaf_not_the_hub(self) -> None:
        """Constitution I.21: Surveil targets isolation/periphery, the
        OPPOSITE of Raid's hub-hunting (review fix -- prior to this fix,
        Surveil was wired to sparrow.py's ``identified_singletons``, which
        actually means "critical hub", so it silently targeted the SAME
        node set as Raid). Every candidate is given the SAME heat
        (``_UNIFORM_HEAT``) so heat cannot influence which of the 8
        structurally-symmetric leaves wins -- only the isolation score
        (identical for all 8) and the deterministic id tie-break can, so
        the winner MUST be a leaf, never a hub or the bridge."""
        graph = _make_double_star_graph()
        real_candidates = _gather_repress_target_candidates(_ORG_ID, graph)
        assert real_candidates is not None
        candidates = [(cid, _UNIFORM_HEAT) for cid, _ in real_candidates]
        topology_scores = _compute_sparrow_topology_scores(candidates, graph)

        ai = RuleBasedStateAI()
        actions = ai.select_action(
            org_id=_ORG_ID,
            faction_balance=FactionBalance(**_SECURITY_STATE_BALANCE),
            budget=_make_budget(),
            heat=_SURVEIL_BIASED_HEAT,
            defines=GameDefines().state_ai,
            rng_seed=0,
            target_candidates=candidates,
            sparrow_topology_scores=topology_scores,
        )

        assert len(actions) == 1
        assert actions[0].sub_verb == StateActionType.SURVEIL
        assert actions[0].target_id not in {"org_hub_a", "org_hub_b", "org_bridge"}
        assert actions[0].target_id.startswith("org_leaf")

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
