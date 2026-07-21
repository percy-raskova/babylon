"""Contract tests for :func:`babylon.projection.state.project_state`.

The state read-model's behavioral contract: one producer per field
(generalizing ``project_county``'s ruling to a multi-county rollup), honest
``None`` for every unattributed quantity, deterministic output. Fixture-fed —
no engine tick, no database — per the keel's fixture-first discipline.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.enums import SocialRole
from babylon.models.enums.topology import EdgeType, NodeType
from babylon.models.world_state import WorldState
from babylon.persistence.county_aggregation import _ideology_to_ternary
from babylon.projection.state import project_state, state_statblocks
from babylon.topology import BabylonGraph

MICHIGAN = "26"
WAYNE = "26163"
GENESEE = "26065"

_DIST_WAYNE = {
    "bourgeoisie": 0.1,
    "petit_bourgeoisie": 0.1,
    "labor_aristocracy": 0.2,
    "proletariat": 0.5,
    "lumpenproletariat": 0.1,
}
_DIST_GENESEE = {
    "bourgeoisie": 0.05,
    "petit_bourgeoisie": 0.15,
    "labor_aristocracy": 0.1,
    "proletariat": 0.4,
    "lumpenproletariat": 0.3,
}


def _make_entity(
    eid: str,
    *,
    county_fips: str | None,
    population: int = 100,
    p_acquiescence: float = 0.5,
    p_revolution: float = 0.3,
    class_consciousness: float = 0.5,
    national_identity: float = 0.5,
) -> SocialClass:
    """Build a SocialClass with the spec-065 attribution fields set."""
    return SocialClass(
        id=eid,
        name=f"Test {eid}",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=1.0,
        ideology=IdeologicalProfile(
            class_consciousness=class_consciousness,
            national_identity=national_identity,
        ),
        p_acquiescence=p_acquiescence,
        p_revolution=p_revolution,
        population=population,
        county_fips=county_fips,
    )


def _world(*entities: SocialClass) -> WorldState:
    """Wrap entities in a minimal WorldState."""
    return WorldState(entities={entity.id: entity for entity in entities})


def _one_county_graph() -> BabylonGraph:
    """A graph with one fully-attributed Wayne territory under one sovereign."""
    graph = BabylonGraph()
    graph.add_node(
        "T001",
        NodeType.TERRITORY,
        county_fips=WAYNE,
        tick_median_wage=19.85,
        tick_phi_hour=412.7,
        tick_bifurcation_score=-0.32,
        tick_class_distribution=dict(_DIST_WAYNE),
        legitimation_index=0.71,
    )
    graph.add_node("SOV_USA", NodeType.SOVEREIGN, name="United States")
    graph.add_edge("SOV_USA", "T001", EdgeType.CLAIMS)
    return graph


def _two_county_graph(*, agree_sovereign: bool) -> BabylonGraph:
    """A graph with two Michigan territories (Wayne + Genesee).

    :param agree_sovereign: if ``True``, both territories are claimed by the
        same sovereign; if ``False``, each is claimed by a different one.
    """
    graph = BabylonGraph()
    graph.add_node(
        "T001",
        NodeType.TERRITORY,
        county_fips=WAYNE,
        tick_median_wage=20.0,
        tick_phi_hour=100.0,
        tick_bifurcation_score=-0.2,
        tick_class_distribution=dict(_DIST_WAYNE),
        legitimation_index=0.6,
    )
    graph.add_node(
        "T002",
        NodeType.TERRITORY,
        county_fips=GENESEE,
        tick_median_wage=30.0,
        tick_phi_hour=50.0,
        tick_bifurcation_score=0.4,
        tick_class_distribution=dict(_DIST_GENESEE),
        legitimation_index=0.8,
    )
    graph.add_node("SOV_USA", NodeType.SOVEREIGN, name="United States")
    graph.add_edge("SOV_USA", "T001", EdgeType.CLAIMS)
    if agree_sovereign:
        graph.add_edge("SOV_USA", "T002", EdgeType.CLAIMS)
    else:
        graph.add_node("SOV_RED_OGV", NodeType.SOVEREIGN, name="Claimant Two")
        graph.add_edge("SOV_RED_OGV", "T002", EdgeType.CLAIMS)
    return graph


def _two_county_world() -> WorldState:
    """Wayne (pop 300) + Genesee (pop 100), distinct ideology points."""
    return _world(
        _make_entity(
            "C001",
            county_fips=WAYNE,
            population=300,
            p_acquiescence=0.6,
            p_revolution=0.4,
            class_consciousness=0.8,
            national_identity=0.1,
        ),
        _make_entity(
            "C002",
            county_fips=GENESEE,
            population=100,
            p_acquiescence=1.0,
            p_revolution=0.0,
            class_consciousness=0.2,
            national_identity=0.6,
        ),
    )


class TestSingleCountyRollup:
    """A one-county state reduces exactly to that county's own values."""

    def test_projects_every_field_from_its_sole_county(self) -> None:
        world = _world(
            _make_entity(
                "C001",
                county_fips=WAYNE,
                population=300,
                p_acquiescence=0.61,
                p_revolution=0.44,
                class_consciousness=0.8,
                national_identity=0.1,
            ),
        )
        view = project_state(MICHIGAN, graph=_one_county_graph(), world=world, tick=847)

        assert view.state_fips == MICHIGAN
        assert view.verified_tick == 847
        assert view.population == 300
        assert view.median_wage == pytest.approx(19.85)
        assert view.imperial_rent_phi == pytest.approx(412.7)
        assert view.bifurcation_score == pytest.approx(-0.32)
        assert view.legitimacy == pytest.approx(0.71)
        assert view.sovereign_id == "SOV_USA"
        assert view.class_composition is not None
        assert view.class_composition.proletariat == pytest.approx(0.5)
        assert view.p_acquiescence == pytest.approx(0.61)
        assert view.p_revolution == pytest.approx(0.44)


class TestMultiCountyRollup:
    """Two counties in one state combine by the WO-16 weighting rules."""

    def test_population_sums_across_counties(self) -> None:
        view = project_state(
            MICHIGAN,
            graph=_two_county_graph(agree_sovereign=True),
            world=_two_county_world(),
            tick=1,
        )
        assert view.population == 400

    def test_survival_is_population_weighted_across_counties(self) -> None:
        view = project_state(
            MICHIGAN,
            graph=_two_county_graph(agree_sovereign=True),
            world=_two_county_world(),
            tick=1,
        )
        assert view.p_acquiescence == pytest.approx((0.6 * 300 + 1.0 * 100) / 400)
        assert view.p_revolution == pytest.approx((0.4 * 300 + 0.0 * 100) / 400)

    def test_consciousness_is_population_weighted_across_counties(self) -> None:
        view = project_state(
            MICHIGAN,
            graph=_two_county_graph(agree_sovereign=True),
            world=_two_county_world(),
            tick=1,
        )
        r_a, l_a, f_a = _ideology_to_ternary(0.8, 0.1)
        r_b, l_b, f_b = _ideology_to_ternary(0.2, 0.6)

        assert view.consciousness is not None
        assert view.consciousness.revolutionary == pytest.approx((r_a * 300 + r_b * 100) / 400)
        assert view.consciousness.liberal == pytest.approx((l_a * 300 + l_b * 100) / 400)
        assert view.consciousness.fascist == pytest.approx((f_a * 300 + f_b * 100) / 400)

    def test_median_wage_is_population_weighted_across_territories(self) -> None:
        view = project_state(
            MICHIGAN,
            graph=_two_county_graph(agree_sovereign=True),
            world=_two_county_world(),
            tick=1,
        )
        assert view.median_wage == pytest.approx((20.0 * 300 + 30.0 * 100) / 400)

    def test_legitimacy_is_population_weighted_across_territories(self) -> None:
        view = project_state(
            MICHIGAN,
            graph=_two_county_graph(agree_sovereign=True),
            world=_two_county_world(),
            tick=1,
        )
        assert view.legitimacy == pytest.approx((0.6 * 300 + 0.8 * 100) / 400)

    def test_bifurcation_score_is_population_weighted_across_territories(self) -> None:
        view = project_state(
            MICHIGAN,
            graph=_two_county_graph(agree_sovereign=True),
            world=_two_county_world(),
            tick=1,
        )
        assert view.bifurcation_score == pytest.approx((-0.2 * 300 + 0.4 * 100) / 400)

    def test_class_composition_is_population_weighted_across_territories(self) -> None:
        view = project_state(
            MICHIGAN,
            graph=_two_county_graph(agree_sovereign=True),
            world=_two_county_world(),
            tick=1,
        )
        assert view.class_composition is not None
        assert view.class_composition.bourgeoisie == pytest.approx((0.1 * 300 + 0.05 * 100) / 400)
        assert view.class_composition.petit_bourgeoisie == pytest.approx(
            (0.1 * 300 + 0.15 * 100) / 400
        )
        assert view.class_composition.labor_aristocracy == pytest.approx(
            (0.2 * 300 + 0.1 * 100) / 400
        )
        assert view.class_composition.proletariat == pytest.approx((0.5 * 300 + 0.4 * 100) / 400)
        assert view.class_composition.lumpenproletariat == pytest.approx(
            (0.1 * 300 + 0.3 * 100) / 400
        )

    def test_imperial_rent_phi_sums_across_territories(self) -> None:
        view = project_state(
            MICHIGAN,
            graph=_two_county_graph(agree_sovereign=True),
            world=_two_county_world(),
            tick=1,
        )
        assert view.imperial_rent_phi == pytest.approx(100.0 + 50.0)

    def test_sovereign_id_projects_when_every_territory_agrees(self) -> None:
        view = project_state(
            MICHIGAN,
            graph=_two_county_graph(agree_sovereign=True),
            world=_two_county_world(),
            tick=1,
        )
        assert view.sovereign_id == "SOV_USA"

    def test_sovereign_id_is_none_when_territories_disagree(self) -> None:
        view = project_state(
            MICHIGAN,
            graph=_two_county_graph(agree_sovereign=False),
            world=_two_county_world(),
            tick=1,
        )
        assert view.sovereign_id is None


class TestHonestAbsence:
    """Missing producers project as None — never a default (III.11)."""

    def test_bare_territories_yield_none_fields(self) -> None:
        """Territories with no tick attributes project all-None quantities."""
        graph = BabylonGraph()
        graph.add_node("T001", NodeType.TERRITORY, county_fips=WAYNE)
        graph.add_node("T002", NodeType.TERRITORY, county_fips=GENESEE)
        view = project_state(MICHIGAN, graph=graph, world=_world(), tick=5)

        assert view.median_wage is None
        assert view.imperial_rent_phi is None
        assert view.bifurcation_score is None
        assert view.legitimacy is None
        assert view.class_composition is None
        assert view.sovereign_id is None
        assert view.population is None
        assert view.consciousness is None

    def test_unattributed_state_has_no_consciousness(self) -> None:
        """No entities attributed to this state -> None, not a fabricated default."""
        other_state_entity = _make_entity("C009", county_fips="48201", population=500)
        view = project_state(
            MICHIGAN,
            graph=_two_county_graph(agree_sovereign=True),
            world=_world(other_state_entity),
            tick=5,
        )

        assert view.consciousness is None
        assert view.population is None
        assert view.p_acquiescence is None
        assert view.p_revolution is None

    def test_no_territory_node_still_projects_entity_fields(self) -> None:
        """Entity-sourced fields survive a state with no territory node at all."""
        world = _world(_make_entity("C001", county_fips=WAYNE, population=250))
        view = project_state(MICHIGAN, graph=BabylonGraph(), world=world, tick=9)

        assert view.population == 250
        assert view.p_acquiescence is not None
        assert view.median_wage is None
        assert view.sovereign_id is None

    def test_contested_claim_on_a_single_territory_yields_no_sovereign(self) -> None:
        """Two CLAIMS edges on one territory -> state sovereign_id is None."""
        graph = _one_county_graph()
        graph.add_node("SOV_RED_OGV", NodeType.SOVEREIGN, name="Claimant Two")
        graph.add_edge("SOV_RED_OGV", "T001", EdgeType.CLAIMS)
        view = project_state(MICHIGAN, graph=graph, world=_world(), tick=5)

        assert view.sovereign_id is None


class TestLoudFailure:
    """A present-but-wrong value raises; only a missing one is absence."""

    def test_malformed_class_distribution_on_any_territory_raises(self) -> None:
        """A distribution dict with missing shares fails validation loudly."""
        graph = BabylonGraph()
        graph.add_node(
            "T001",
            NodeType.TERRITORY,
            county_fips=WAYNE,
            tick_class_distribution={"proletariat": 1.0},
        )
        world = _world(_make_entity("C001", county_fips=WAYNE, population=100))
        with pytest.raises(ValidationError):
            project_state(MICHIGAN, graph=graph, world=world, tick=1)


class TestDeterminism:
    """Identical inputs yield identical frozen dossiers."""

    def test_double_projection_is_identical(self) -> None:
        """Two projections of the same multi-county state compare equal."""
        world = _two_county_world()
        graph = _two_county_graph(agree_sovereign=True)

        first = project_state(MICHIGAN, graph=graph, world=world, tick=847)
        second = project_state(MICHIGAN, graph=graph, world=world, tick=847)

        assert first == second
        assert first.model_dump() == second.model_dump()


class TestStateStatblocks:
    """The Wave-1 demo statblock provider for ``state/<fips>``."""

    def test_unknown_subject_returns_none(self) -> None:
        assert state_statblocks("state/48") is None
        assert state_statblocks("county/26163") is None

    def test_known_subject_returns_fixture_derived_rows(self) -> None:
        rows = state_statblocks("state/26")
        assert rows is not None
        assert ("population", "2") in rows
        assert ("median_wage", "21.00") in rows
