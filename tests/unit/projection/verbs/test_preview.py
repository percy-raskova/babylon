"""Contract tests for the verb preview projection (WO-38, spec-116 parity).

Preview == resolution: the consciousness estimate a player sees BEFORE
committing a verb comes from the same pure helper the EDUCATE / CAMPAIGN /
AID resolvers use (:func:`babylon.ooda.action_effects.compute_consciousness_delta`),
with ``doctrine`` threaded exactly as each resolver threads it — EDUCATE and
CAMPAIGN pass it, AID never does. Heuristic verbs pin their documented
simpler deltas. Ports the disabled
``tests/unit/web/test_engine_bridge.py::TestExpectedDeltas`` behavioral
assertions into the projection layer (test-port ledger updated in WO-38).
Fixture-fed — no engine tick, no database.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.models.enums import ActionType
from babylon.models.enums.topology import EdgeType, NodeType
from babylon.ooda.action_effects import compute_consciousness_delta
from babylon.projection.verbs.preview import (
    CANONICAL_VERBS,
    VERB_TO_ACTION_TYPE,
    preview_consciousness_delta,
    preview_verb,
)
from babylon.topology import BabylonGraph

ORG = "org-player"
TARGET = "sc-wayne-proles"
TERRITORY = "T001"


def _graph(*, cohesion: float = 0.6, budget: float = 10.0, heat: float = 0.1) -> BabylonGraph:
    """One org with a TENANCY-linked proletariat community on one territory."""
    graph = BabylonGraph()
    graph.add_node(
        ORG,
        NodeType.ORGANIZATION,
        id=ORG,
        name="The Union",
        org_type="political_faction",
        cadre_level=0.5,
        cohesion=cohesion,
        budget=budget,
        heat=heat,
        consciousness_tendency="revolutionary",
        territory_ids=[TERRITORY],
    )
    graph.add_node(TERRITORY, NodeType.TERRITORY, county_fips="26163")
    graph.add_node(
        TARGET,
        NodeType.SOCIAL_CLASS,
        name="Wayne proletariat",
        population=1000,
        class_consciousness=0.4,
    )
    graph.add_edge(TARGET, TERRITORY, EdgeType.TENANCY)
    return graph


class TestVerbMapping:
    """The nine canonical player verbs map onto engine ActionTypes, pinned."""

    def test_the_nine_canonical_verbs_and_their_action_types(self) -> None:
        assert VERB_TO_ACTION_TYPE == {
            "educate": ActionType.EDUCATE,
            "reproduce": ActionType.RECRUIT,
            "attack": ActionType.ATTACK_INFRASTRUCTURE,
            "mobilize": ActionType.PROTEST,
            "campaign": ActionType.PROPAGANDIZE,
            "aid": ActionType.PROVIDE_SERVICE,
            "investigate": ActionType.MAP_NETWORK,
            "move": ActionType.MOVE,
            "negotiate": ActionType.PROPOSE_ALLIANCE,
        }
        assert frozenset(VERB_TO_ACTION_TYPE) == CANONICAL_VERBS


class TestResolverParity:
    """preview == resolution for the consciousness verbs (spec-116 FR-4.4)."""

    @pytest.mark.parametrize("verb", ["educate", "campaign"])
    def test_educate_and_campaign_previews_include_doctrine_exactly_like_their_resolvers(
        self, verb: str
    ) -> None:
        """resolve_educate/resolve_campaign pass doctrine=defines.doctrine —
        the preview must reproduce that call signature, not omit it."""
        graph = _graph()
        defines = GameDefines()
        expected = compute_consciousness_delta(
            dict(graph.nodes[ORG]),
            TARGET,
            VERB_TO_ACTION_TYPE[verb],
            graph,
            defines.ooda,
            defines.organization,
            defines.doctrine,
        )
        assert expected is not None
        got = preview_consciousness_delta(
            dict(graph.nodes[ORG]), TARGET, VERB_TO_ACTION_TYPE[verb], graph
        )
        assert got == float(expected.collective_identity_delta)

    def test_aid_preview_omits_doctrine_exactly_like_resolve_aid(self) -> None:
        """resolve_aid calls compute_consciousness_delta WITHOUT doctrine —
        passing it unconditionally would over-state AID's estimate."""
        graph = _graph()
        defines = GameDefines()
        expected = compute_consciousness_delta(
            dict(graph.nodes[ORG]),
            TARGET,
            ActionType.PROVIDE_SERVICE,
            graph,
            defines.ooda,
            defines.organization,
            None,
        )
        assert expected is not None
        got = preview_consciousness_delta(
            dict(graph.nodes[ORG]), TARGET, ActionType.PROVIDE_SERVICE, graph
        )
        assert got == float(expected.collective_identity_delta)

    def test_doctrine_bonus_reaches_the_educate_preview(self) -> None:
        """An org carrying CLASS_ANALYSIS doctrine tags previews a strictly
        larger EDUCATE delta than the same org without them (ADR073 Step-7.5
        bonus, threaded through the resolver signature)."""
        bare = _graph()
        tagged = _graph()
        tagged.update_node(ORG, doctrine_tags={"class_analysis": 5.0})
        bare_delta = preview_consciousness_delta(
            dict(bare.nodes[ORG]), TARGET, ActionType.EDUCATE, bare
        )
        tagged_delta = preview_consciousness_delta(
            dict(tagged.nodes[ORG]), TARGET, ActionType.EDUCATE, tagged
        )
        assert tagged_delta > bare_delta


class TestPreviewVerb:
    """The full per-verb preview: deltas, cost, probability, warnings."""

    def test_educate_preview_carries_resolver_parity_delta(self) -> None:
        graph = _graph(cohesion=0.6)
        view = preview_verb(graph, ORG, "educate", target_id=TARGET)
        expected = round(
            preview_consciousness_delta(dict(graph.nodes[ORG]), TARGET, ActionType.EDUCATE, graph),
            4,
        )
        assert view.estimated_consciousness_delta == expected
        assert view.estimated_heat_delta == 0.01
        assert view.success_probability == round(min(0.95, 0.4 + 0.6 * 0.5), 4)

    def test_aid_preview_cools_heat(self) -> None:
        view = preview_verb(_graph(), ORG, "aid", target_id=TARGET)
        assert view.estimated_heat_delta == -0.01

    def test_attack_preview_pins_the_documented_heuristic(self) -> None:
        graph = _graph(cohesion=0.5)
        view = preview_verb(graph, ORG, "attack", target_id=TARGET)
        assert view.estimated_consciousness_delta == 0.02
        assert view.estimated_heat_delta == round(0.08 * 0.5, 4)
        assert view.success_probability == round(min(0.8, 0.3 + 0.5 * 0.4), 4)

    def test_reproduce_preview_pins_the_documented_heuristic(self) -> None:
        view = preview_verb(_graph(cohesion=0.5), ORG, "reproduce")
        assert view.estimated_consciousness_delta == 0.01
        assert view.estimated_heat_delta == -0.01
        assert view.success_probability == round(min(0.95, 0.5 + 0.5 * 0.4), 4)

    @pytest.mark.parametrize("verb", ["investigate", "negotiate", "move"])
    def test_low_impact_verbs_preview_zero_deltas(self, verb: str) -> None:
        view = preview_verb(_graph(cohesion=0.5), ORG, verb, target_id=TERRITORY)
        assert view.estimated_consciousness_delta == 0.0
        assert view.estimated_heat_delta == 0.0
        assert view.success_probability == round(min(0.9, 0.6 + 0.5 * 0.3), 4)

    def test_affected_territories_are_org_territories_plus_target(self) -> None:
        view = preview_verb(_graph(), ORG, "educate", target_id=TARGET)
        assert view.affected_territory_ids == (TERRITORY, TARGET)

    def test_insufficient_budget_warns(self) -> None:
        view = preview_verb(_graph(budget=0.0), ORG, "educate", target_id=TARGET)
        assert "Insufficient budget for this action" in view.warnings

    def test_elevated_heat_warns(self) -> None:
        view = preview_verb(_graph(heat=0.9), ORG, "educate", target_id=TARGET)
        assert "Organization heat is already elevated" in view.warnings

    def test_missing_org_is_a_dead_preview_with_a_warning(self) -> None:
        view = preview_verb(_graph(), "org-ghost", "educate", target_id=TARGET)
        assert view.success_probability == 0.0
        assert view.warnings == ("Organization 'org-ghost' not found",)

    def test_missing_target_warns_and_estimates_nothing(self) -> None:
        view = preview_verb(_graph(), ORG, "educate", target_id="sc-ghost")
        assert view.estimated_consciousness_delta == 0.0
        assert "Target 'sc-ghost' not found in current state" in view.warnings

    def test_under_eviction_target_warns(self) -> None:
        graph = _graph()
        graph.update_node(TARGET, under_eviction=True)
        view = preview_verb(graph, ORG, "educate", target_id=TARGET)
        assert "Target territory is under eviction" in view.warnings

    def test_unknown_verb_raises_loudly(self) -> None:
        with pytest.raises(ValueError, match="not a canonical verb"):
            preview_verb(_graph(), ORG, "vibe", target_id=TARGET)
