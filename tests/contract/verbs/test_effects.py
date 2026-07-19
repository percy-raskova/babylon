"""Contract: per-verb effect classes (verb-dispatch engine).

Each canonical verb must produce its characteristic REAL effect when dispatched
through :func:`babylon.engine.actions.resolve_player_action` — proving the
resolvers are no longer blind ``success=True`` no-ops.
"""

from __future__ import annotations

import copy

import pytest

from babylon.engine.actions import resolve_player_action
from babylon.models.enums import ActionType, EdgeType
from babylon.ooda.layer3 import process_layer3
from babylon.ooda.types import Action, ActionResult
from tests.contract.verbs.conftest import (
    CLASS_ID,
    HOME_TERRITORY,
    ORG_ID,
    OTHER_TERRITORY,
    RIVAL_ID,
    org_attrs,
)

pytestmark = pytest.mark.contract


def _dispatch(verb_graph, services, action_type, target_id, **params) -> ActionResult:
    action = Action(
        org_id=ORG_ID,
        action_type=action_type,
        target_id=target_id,
        params=params,
    )
    return resolve_player_action(action, org_attrs(verb_graph), verb_graph, services)


class TestConsciousnessVerbs:
    """educate / campaign route through the five-factor CI machinery."""

    def test_educate_produces_consciousness_delta(self, verb_graph, services) -> None:
        result = _dispatch(verb_graph, services, ActionType.EDUCATE, CLASS_ID)
        assert result.success is True
        assert result.consciousness_delta is not None
        assert result.consciousness_delta.collective_identity_delta != 0.0

    def test_campaign_produces_consciousness_delta(self, verb_graph, services) -> None:
        result = _dispatch(verb_graph, services, ActionType.PROPAGANDIZE, CLASS_ID)
        assert result.success is True
        assert result.consciousness_delta is not None
        assert result.consciousness_delta.collective_identity_delta != 0.0


class TestDoctrineTheoryBonus:
    """Unit 6b feedback: CLASS_ANALYSIS scales consciousness-raising.

    Corpus (doctrine-tree-mvp.yaml tag effects): "High: Correct
    prioritization, theory bonus." An org with accumulated class-analysis
    doctrine raises consciousness faster than the same org without it.
    """

    def test_class_analysis_amplifies_educate_delta(self, verb_graph, services) -> None:
        plain = _dispatch(verb_graph, services, ActionType.EDUCATE, CLASS_ID)
        assert plain.consciousness_delta is not None

        verb_graph.update_node(ORG_ID, doctrine_tags={"class_analysis": 10.0})
        theorized = _dispatch(verb_graph, services, ActionType.EDUCATE, CLASS_ID)
        assert theorized.consciousness_delta is not None

        expected_factor = 1.0 + services.defines.doctrine.theory_bonus_per_class_analysis * 10.0
        assert theorized.consciousness_delta.collective_identity_delta == pytest.approx(
            plain.consciousness_delta.collective_identity_delta * expected_factor
        )

    def test_zero_class_analysis_is_exactly_the_plain_delta(self, verb_graph, services) -> None:
        plain = _dispatch(verb_graph, services, ActionType.EDUCATE, CLASS_ID)
        verb_graph.update_node(ORG_ID, doctrine_tags={"class_analysis": 0.0})
        untheorized = _dispatch(verb_graph, services, ActionType.EDUCATE, CLASS_ID)
        assert untheorized.consciousness_delta is not None
        assert plain.consciousness_delta is not None
        assert (
            untheorized.consciousness_delta.collective_identity_delta
            == plain.consciousness_delta.collective_identity_delta
        )


class TestEducateDoctrineStudy:
    """Educate(Doctrine) sub-verb — the Study order (DoctrineSystem Unit 7b).

    A ``doctrine_node_id`` param turns EDUCATE into a standing study order the
    DoctrineSystem honors (save-toward-target instead of greedy). The Article V
    roster is untouched — this is a target type of the existing Educate verb,
    exactly as Investigate carries Territory/Org/Edge sub-verbs.
    """

    def test_study_order_sets_standing_target(self, verb_graph, services) -> None:
        result = _dispatch(
            verb_graph, services, ActionType.EDUCATE, ORG_ID, doctrine_node_id="trade_unionism"
        )
        assert result.success is True
        assert result.direct_effects["study_target_id"] == "trade_unionism"
        assert verb_graph.nodes[ORG_ID]["study_target_id"] == "trade_unionism"

    def test_trap_target_refused_loudly(self, verb_graph, services) -> None:
        result = _dispatch(
            verb_graph, services, ActionType.EDUCATE, ORG_ID, doctrine_node_id="adventurism"
        )
        assert result.success is False
        assert "trap" in (result.failure_reason or "").lower()
        assert verb_graph.nodes[ORG_ID].get("study_target_id") is None

    def test_unknown_node_refused_loudly(self, verb_graph, services) -> None:
        result = _dispatch(
            verb_graph, services, ActionType.EDUCATE, ORG_ID, doctrine_node_id="no_such_node"
        )
        assert result.success is False
        assert "no_such_node" in (result.failure_reason or "")

    def test_already_acquired_target_refused(self, verb_graph, services) -> None:
        verb_graph.update_node(ORG_ID, acquired_doctrine_ids=("class_consciousness",))
        result = _dispatch(
            verb_graph,
            services,
            ActionType.EDUCATE,
            ORG_ID,
            doctrine_node_id="class_consciousness",
        )
        assert result.success is False
        assert "already" in (result.failure_reason or "").lower()

    def test_plain_educate_unchanged_by_the_sub_verb(self, verb_graph, services) -> None:
        # No doctrine_node_id param → the classic consciousness path, untouched.
        result = _dispatch(verb_graph, services, ActionType.EDUCATE, CLASS_ID)
        assert result.success is True
        assert result.consciousness_delta is not None


class TestAidTransfer:
    """aid conserves value: org budget loss == target wealth gain × efficiency."""

    def test_aid_transfers_budget_to_wealth(self, verb_graph, services) -> None:
        budget_before = float(verb_graph.nodes[ORG_ID]["budget"])
        wealth_before = float(verb_graph.nodes[CLASS_ID]["wealth"])

        result = _dispatch(
            verb_graph, services, ActionType.PROVIDE_SERVICE, CLASS_ID, transfer_amount=10.0
        )

        assert result.success is True
        assert result.direct_effects["amount_transferred"] == 10.0
        efficiency = result.direct_effects["efficiency"]
        assert float(verb_graph.nodes[ORG_ID]["budget"]) == pytest.approx(budget_before - 10.0)
        assert float(verb_graph.nodes[CLASS_ID]["wealth"]) == pytest.approx(
            wealth_before + 10.0 * efficiency
        )

    def test_aid_insufficient_budget_fails_loud(self, verb_graph, services) -> None:
        result = _dispatch(
            verb_graph, services, ActionType.PROVIDE_SERVICE, CLASS_ID, transfer_amount=1e9
        )
        assert result.success is False
        assert result.failure_reason is not None


class TestMassWorkSolidarity:
    """Unit 6 write side (ADR087): EDUCATE/PROPAGANDIZE/PROVIDE_SERVICE
    create-or-strengthen an org -> class SOLIDARITY edge when targeting a
    social_class node, amplified by the org's MASS_LINK doctrine tag.
    PROTEST stays a solidarity CONSUMER (``mobilize.py``'s
    ``_count_solidarity_edges``), never a producer — untested here, covered
    by ``TestMobilize``.
    """

    @pytest.mark.parametrize(
        "action_type",
        [ActionType.PROVIDE_SERVICE, ActionType.EDUCATE, ActionType.PROPAGANDIZE],
    )
    def test_mass_work_verb_creates_solidarity_edge_to_class(
        self, verb_graph, services, action_type
    ) -> None:
        assert verb_graph.get_edge_data(ORG_ID, CLASS_ID) is None
        _dispatch(verb_graph, services, action_type, CLASS_ID)
        edge = verb_graph.get_edge(ORG_ID, CLASS_ID, EdgeType.SOLIDARITY.value)
        assert edge is not None
        assert edge.attributes["solidarity_strength"] == pytest.approx(
            services.defines.doctrine.mass_work_solidarity_gain
        )

    def test_repeated_dispatch_strengthens_rather_than_overwrites(
        self, verb_graph, services
    ) -> None:
        _dispatch(verb_graph, services, ActionType.PROPAGANDIZE, CLASS_ID)
        first = verb_graph.get_edge(ORG_ID, CLASS_ID, EdgeType.SOLIDARITY.value)
        assert first is not None
        first_strength = first.attributes["solidarity_strength"]

        _dispatch(verb_graph, services, ActionType.PROPAGANDIZE, CLASS_ID)
        second = verb_graph.get_edge(ORG_ID, CLASS_ID, EdgeType.SOLIDARITY.value)
        assert second is not None
        assert second.attributes["solidarity_strength"] > first_strength

    def test_solidarity_strength_is_capped_at_one(self, verb_graph, services) -> None:
        max_dispatches = 100  # fixed upper bound (static-analysis friendly, III bound rule)
        for _ in range(max_dispatches):
            _dispatch(verb_graph, services, ActionType.PROPAGANDIZE, CLASS_ID)
        edge = verb_graph.get_edge(ORG_ID, CLASS_ID, EdgeType.SOLIDARITY.value)
        assert edge is not None
        assert edge.attributes["solidarity_strength"] == pytest.approx(1.0)

    def test_mass_link_tag_amplifies_the_gain(self, verb_graph, services) -> None:
        verb_graph.update_node(ORG_ID, doctrine_tags={"mass_link": 5.0})
        _dispatch(verb_graph, services, ActionType.PROPAGANDIZE, CLASS_ID)
        edge = verb_graph.get_edge(ORG_ID, CLASS_ID, EdgeType.SOLIDARITY.value)
        assert edge is not None
        doctrine = services.defines.doctrine
        expected = doctrine.mass_work_solidarity_gain * (1.0 + doctrine.mass_link_weight * 5.0)
        assert edge.attributes["solidarity_strength"] == pytest.approx(expected)

    def test_zero_mass_link_is_exactly_the_base_gain(self, verb_graph, services) -> None:
        verb_graph.update_node(ORG_ID, doctrine_tags={"mass_link": 0.0})
        _dispatch(verb_graph, services, ActionType.PROPAGANDIZE, CLASS_ID)
        edge = verb_graph.get_edge(ORG_ID, CLASS_ID, EdgeType.SOLIDARITY.value)
        assert edge is not None
        assert edge.attributes["solidarity_strength"] == pytest.approx(
            services.defines.doctrine.mass_work_solidarity_gain
        )

    def test_targeting_a_non_class_node_is_a_no_op(self, verb_graph, services) -> None:
        # ORG_ID already carries a PRESENCE edge to HOME_TERRITORY (seeded by
        # to_graph() from territory_ids) — a target-type no-op must leave it
        # completely untouched, not just skip creating a NEW edge.
        before = verb_graph.get_edge_data(ORG_ID, HOME_TERRITORY)
        assert before is not None
        assert before["edge_type"] == "presence"
        _dispatch(verb_graph, services, ActionType.PROPAGANDIZE, HOME_TERRITORY)
        after = verb_graph.get_edge_data(ORG_ID, HOME_TERRITORY)
        assert after == before, "a non-social_class target must never gain/alter an edge"

    def test_study_sub_verb_does_not_create_a_solidarity_edge(self, verb_graph, services) -> None:
        # EDUCATE(Doctrine)'s target is the acting org itself, not a class —
        # apply_mass_work_solidarity's own target-type check would no-op
        # regardless, but this pins the sub-verb branch never even targets
        # a class.
        _dispatch(
            verb_graph, services, ActionType.EDUCATE, ORG_ID, doctrine_node_id="trade_unionism"
        )
        assert verb_graph.get_edge_data(ORG_ID, CLASS_ID) is None


class TestReproduce:
    """reproduce (cadre training) raises cadre_level and cohesion."""

    def test_cadre_training_raises_cadre_and_cohesion(self, verb_graph, services) -> None:
        cadre_before = float(verb_graph.nodes[ORG_ID]["cadre_level"])
        cohesion_before = float(verb_graph.nodes[ORG_ID]["cohesion"])

        result = _dispatch(
            verb_graph, services, ActionType.RECRUIT, HOME_TERRITORY, mode="cadre_training"
        )

        assert result.success is True
        assert float(verb_graph.nodes[ORG_ID]["cadre_level"]) > cadre_before
        assert float(verb_graph.nodes[ORG_ID]["cohesion"]) > cohesion_before


class TestAttack:
    """attack raises acting-org heat AND routes the infra delta through layer 3."""

    def test_attack_infra_channel_fires_via_layer3(self, verb_graph, services) -> None:
        heat_before = float(verb_graph.nodes[ORG_ID]["heat"])
        result = _dispatch(verb_graph, services, ActionType.ATTACK_INFRASTRUCTURE, HOME_TERRITORY)
        assert result.success is True
        # Acting-org heat rose (a real graph write).
        assert float(verb_graph.nodes[ORG_ID]["heat"]) > heat_before

        # The ATTACK ActionResult routes through layer 3, decrementing the
        # target territory's infrastructure (default 0.5 -> 0.4).
        summary = process_layer3([result], verb_graph, services.defines.ooda)
        assert summary["infrastructure_updates"] == 1
        assert float(verb_graph.nodes[HOME_TERRITORY]["infrastructure"]) < 0.5

    def test_attack_self_heat_gain_is_defines_driven(self, verb_graph) -> None:
        """The self-heat coefficient is OODADefines.attack_self_heat_gain, not a literal.

        spec-116 FR-116-4.4 promotes the old ``_ATTACK_SELF_HEAT_GAIN = 0.1``
        module literal into GameDefines so the web bridge's per-target heat
        estimate and the resolver share one source of truth.
        """
        from babylon.config.defines import GameDefines
        from babylon.engine.services import ServiceContainer

        defines = GameDefines()
        modded = defines.model_copy(
            update={"ooda": defines.ooda.model_copy(update={"attack_self_heat_gain": 0.25})}
        )
        services = ServiceContainer.create(defines=modded)

        heat_before = float(verb_graph.nodes[ORG_ID]["heat"])
        result = _dispatch(verb_graph, services, ActionType.ATTACK_INFRASTRUCTURE, HOME_TERRITORY)

        assert result.success is True
        assert float(verb_graph.nodes[ORG_ID]["heat"]) == pytest.approx(heat_before + 0.25)
        assert result.direct_effects["heat_self_delta"] == pytest.approx(0.25)


class TestMobilize:
    """mobilize routes agitation into a class target, heat into a territory."""

    def test_agitation_routes_into_social_class(self, verb_graph, services) -> None:
        agitation_before = float(verb_graph.nodes[CLASS_ID]["ideology"]["agitation"])
        result = _dispatch(verb_graph, services, ActionType.PROTEST, CLASS_ID, sl_committed=2.0)
        assert result.success is True
        assert result.direct_effects["turnout"] > 0.0
        assert float(verb_graph.nodes[CLASS_ID]["ideology"]["agitation"]) > agitation_before

    def test_heat_routes_into_territory(self, verb_graph, services) -> None:
        heat_before = float(verb_graph.nodes[HOME_TERRITORY]["heat"])
        result = _dispatch(
            verb_graph, services, ActionType.PROTEST, HOME_TERRITORY, sl_committed=2.0
        )
        assert result.success is True
        assert float(verb_graph.nodes[HOME_TERRITORY]["heat"]) > heat_before


class TestInvestigate:
    """investigate reveals attributes WITHOUT mutating any graph state."""

    def test_no_graph_mutation_but_effects_reported(self, verb_graph, services) -> None:
        before = copy.deepcopy(dict(verb_graph.nodes(data=True)))
        result = _dispatch(verb_graph, services, ActionType.MAP_NETWORK, CLASS_ID)
        after = dict(verb_graph.nodes(data=True))

        assert result.success is True
        assert result.direct_effects["revealed"]
        assert before == after, "INVESTIGATE mutated the graph"


class TestMove:
    """move rewrites the acting org's territory_ids."""

    def test_relocate_rewrites_territory_ids(self, verb_graph, services) -> None:
        result = _dispatch(verb_graph, services, ActionType.MOVE, OTHER_TERRITORY)
        assert result.success is True
        assert verb_graph.nodes[ORG_ID]["territory_ids"] == [OTHER_TERRITORY]

    def test_move_to_non_territory_fails_loud(self, verb_graph, services) -> None:
        result = _dispatch(verb_graph, services, ActionType.MOVE, CLASS_ID)
        assert result.success is False
        assert result.failure_reason is not None


class TestNegotiate:
    """negotiate flips an antagonistic edge to TRANSACTIONAL."""

    def test_flips_exploitation_to_transactional(self, verb_graph, services) -> None:
        verb_graph.add_edge(ORG_ID, RIVAL_ID, edge_type=EdgeType.EXPLOITATION.value)
        result = _dispatch(verb_graph, services, ActionType.PROPOSE_ALLIANCE, RIVAL_ID)
        assert result.success is True
        assert result.direct_effects["edge_flipped"] is True
        assert verb_graph.get_edge_data(ORG_ID, RIVAL_ID)["edge_type"] == (
            EdgeType.TRANSACTIONAL.value
        )

    def test_creates_edge_when_none_exists(self, verb_graph, services) -> None:
        assert verb_graph.get_edge_data(ORG_ID, RIVAL_ID) is None
        result = _dispatch(verb_graph, services, ActionType.PROPOSE_ALLIANCE, RIVAL_ID)
        assert result.success is True
        assert verb_graph.get_edge_data(ORG_ID, RIVAL_ID)["edge_type"] == (
            EdgeType.TRANSACTIONAL.value
        )
