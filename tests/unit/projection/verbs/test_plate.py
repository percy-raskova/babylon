"""Contract tests for the verb-plate view provider (WO-38).

The plate lists all nine Article V verbs in canonical order, each with its
target-existence eligibility (the SAME predicates the per-verb target lists
apply), player-facing ``(reason, remedy)`` copy when ineligible, and
affordability via :func:`babylon.models.vanguard_resources.check_can_afford`
(the same function that gates submission, so the plate can never disagree
with a submit rejection). Ports the eligibility half of the disabled
``test_engine_bridge.py`` verb-plate assertions. Fixture-fed — no engine,
no database.
"""

from __future__ import annotations

from babylon.models.enums.topology import EdgeType, NodeType
from babylon.projection.verbs.copy import VERB_INELIGIBILITY_COPY
from babylon.projection.verbs.plate import build_verb_plate
from babylon.projection.verbs.preview import VERB_TO_ACTION_TYPE
from babylon.topology import BabylonGraph

ORG = "org-player"
TERRITORY = "T001"


def _rich_graph() -> BabylonGraph:
    """A world where every one of the nine verbs is eligible."""
    graph = BabylonGraph()
    graph.add_node(
        ORG,
        NodeType.ORGANIZATION,
        id=ORG,
        name="The Union",
        org_type="political_faction",
        cadre_level=0.6,
        cohesion=0.6,
        budget=50.0,
        heat=0.1,
        territory_ids=[TERRITORY],
    )
    graph.add_node(TERRITORY, NodeType.TERRITORY, county_fips="26163")
    graph.add_node(
        "sc-proles",
        NodeType.SOCIAL_CLASS,
        name="Wayne proletariat",
        population=1000,
    )
    graph.add_edge("sc-proles", TERRITORY, EdgeType.TENANCY)
    graph.add_node(
        "org-shop",
        NodeType.ORGANIZATION,
        name="Chamber of Commerce",
        org_type="business",
        territory_ids=[TERRITORY],
    )
    graph.add_node(
        "inst-court",
        NodeType.INSTITUTION,
        name="County Court",
        territory_ids=[TERRITORY],
    )
    return graph


def _barren_graph() -> BabylonGraph:
    """The org alone in an empty world — almost nothing is eligible."""
    graph = BabylonGraph()
    graph.add_node(
        ORG,
        NodeType.ORGANIZATION,
        id=ORG,
        name="The Union",
        org_type="political_faction",
        cadre_level=0.6,
        cohesion=0.6,
        budget=50.0,
        heat=0.1,
        territory_ids=[],
    )
    return graph


class TestBuildVerbPlate:
    def test_all_nine_verbs_in_canonical_order(self) -> None:
        plate = build_verb_plate(_rich_graph(), ORG, tick=7)
        assert plate is not None
        assert tuple(row.verb for row in plate.verbs) == tuple(VERB_TO_ACTION_TYPE)
        assert plate.tick == 7
        assert plate.org_id == ORG

    def test_rich_world_makes_every_verb_eligible(self) -> None:
        plate = build_verb_plate(_rich_graph(), ORG, tick=0)
        assert plate is not None
        assert all(row.eligible for row in plate.verbs)
        assert all(row.reason is None and row.remedy is None for row in plate.verbs)

    def test_barren_world_shows_reason_and_remedy_never_hides(self) -> None:
        plate = build_verb_plate(_barren_graph(), ORG, tick=0)
        assert plate is not None
        by_verb = {row.verb: row for row in plate.verbs}
        assert by_verb["reproduce"].eligible  # always targets the acting org
        for verb in (
            "educate",
            "aid",
            "attack",
            "mobilize",
            "campaign",
            "move",
            "investigate",
            "negotiate",
        ):
            row = by_verb[verb]
            assert not row.eligible
            assert (row.reason, row.remedy) == VERB_INELIGIBILITY_COPY[verb]

    def test_affordability_rides_along_but_never_gates_eligibility(self) -> None:
        graph = _rich_graph()
        graph.update_node(ORG, budget=0.0)
        plate = build_verb_plate(graph, ORG, tick=0)
        assert plate is not None
        broke_rows = [row for row in plate.verbs if not row.can_afford]
        assert broke_rows, "a zero-budget org must fail affordability somewhere"
        assert all(row.afford_note for row in broke_rows)
        assert all(row.eligible for row in plate.verbs)  # eligibility unchanged

    def test_missing_org_is_an_honest_none(self) -> None:
        assert build_verb_plate(_rich_graph(), "org-ghost", tick=0) is None

    def test_plate_carries_resolver_parity_previews(self) -> None:
        """Each row embeds the same preview `preview_verb` computes standalone."""
        graph = _rich_graph()
        plate = build_verb_plate(graph, ORG, tick=0)
        assert plate is not None
        educate = next(row for row in plate.verbs if row.verb == "educate")
        assert educate.preview is not None
        assert educate.preview.estimated_heat_delta == 0.01


class TestCandidateTargetIds:
    """Unit "verb-targeting" (shell-interconnect): every verb row also
    surfaces the honest entity ids behind its own eligibility boolean, not
    just the boolean — a picker enumerates real targets without touching
    the graph itself."""

    def test_reproduce_candidate_set_is_empty_self_targeting(self) -> None:
        """``reproduce`` always targets the acting org itself (its own
        eligibility row's comment) — it has no EXPLICIT-target candidates."""
        plate = build_verb_plate(_rich_graph(), ORG, tick=0)
        assert plate is not None
        reproduce = next(row for row in plate.verbs if row.verb == "reproduce")
        assert reproduce.candidate_target_ids == ()

    def test_educate_candidate_set_is_the_real_reachable_social_class(self) -> None:
        plate = build_verb_plate(_rich_graph(), ORG, tick=0)
        assert plate is not None
        educate = next(row for row in plate.verbs if row.verb == "educate")
        assert educate.candidate_target_ids == ("sc-proles",)

    def test_aid_candidate_set_unions_social_class_and_org_in_reach(self) -> None:
        plate = build_verb_plate(_rich_graph(), ORG, tick=0)
        assert plate is not None
        aid = next(row for row in plate.verbs if row.verb == "aid")
        assert aid.candidate_target_ids == ("org-shop", "sc-proles")

    def test_attack_candidate_set_unions_org_and_institution_in_reach(self) -> None:
        plate = build_verb_plate(_rich_graph(), ORG, tick=0)
        assert plate is not None
        attack = next(row for row in plate.verbs if row.verb == "attack")
        assert attack.candidate_target_ids == ("inst-court", "org-shop")

    def test_mobilize_candidate_set_is_only_the_business_civil_society_org(self) -> None:
        plate = build_verb_plate(_rich_graph(), ORG, tick=0)
        assert plate is not None
        mobilize = next(row for row in plate.verbs if row.verb == "mobilize")
        assert mobilize.candidate_target_ids == ("org-shop",)

    def test_campaign_and_move_candidate_sets_are_every_territory_node(self) -> None:
        plate = build_verb_plate(_rich_graph(), ORG, tick=0)
        assert plate is not None
        by_verb = {row.verb: row for row in plate.verbs}
        assert by_verb["campaign"].candidate_target_ids == (TERRITORY,)
        assert by_verb["move"].candidate_target_ids == (TERRITORY,)

    def test_investigate_candidate_set_is_the_orgs_own_territories(self) -> None:
        plate = build_verb_plate(_rich_graph(), ORG, tick=0)
        assert plate is not None
        investigate = next(row for row in plate.verbs if row.verb == "investigate")
        assert investigate.candidate_target_ids == (TERRITORY,)

    def test_negotiate_candidate_set_is_every_other_org_anywhere(self) -> None:
        plate = build_verb_plate(_rich_graph(), ORG, tick=0)
        assert plate is not None
        negotiate = next(row for row in plate.verbs if row.verb == "negotiate")
        assert negotiate.candidate_target_ids == ("org-shop",)

    def test_barren_world_candidate_sets_are_empty_wherever_ineligible(self) -> None:
        plate = build_verb_plate(_barren_graph(), ORG, tick=0)
        assert plate is not None
        for row in plate.verbs:
            assert row.candidate_target_ids == (), (
                f"{row.verb}: expected no candidates on the barren fixture, "
                f"found {row.candidate_target_ids!r}"
            )

    def test_candidate_target_ids_are_always_sorted_for_determinism(self) -> None:
        plate = build_verb_plate(_rich_graph(), ORG, tick=0)
        assert plate is not None
        for row in plate.verbs:
            assert row.candidate_target_ids == tuple(sorted(row.candidate_target_ids))
