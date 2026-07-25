"""Contract tests for :func:`babylon.projection.county.project_county`.

The county read-model's behavioral contract: one producer per field, honest
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
from babylon.projection.county import project_county
from babylon.topology import BabylonGraph

WAYNE = "26163"

_DISTRIBUTION = {
    "bourgeoisie": 0.077,
    "petit_bourgeoisie": 0.191,
    "labor_aristocracy": 0.226,
    "proletariat": 0.382,
    "lumpenproletariat": 0.124,
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


def _full_graph() -> BabylonGraph:
    """A graph with one fully-attributed Wayne territory under one sovereign."""
    graph = BabylonGraph()
    graph.add_node(
        "T001",
        NodeType.TERRITORY,
        county_fips=WAYNE,
        tick_median_wage=19.85,
        tick_phi_hour=412.7,
        tick_bifurcation_score=-0.32,
        tick_class_distribution=dict(_DISTRIBUTION),
        legitimation_index=0.71,
        habitability=0.83,
    )
    graph.add_node("SOV_USA", NodeType.SOVEREIGN, name="United States")
    graph.add_edge("SOV_USA", "T001", EdgeType.CLAIMS)
    return graph


class TestFullDossier:
    """Every field populated when every producer has attributed data."""

    def test_projects_every_field(self) -> None:
        """A fully-attributed county yields a dossier with no absences."""
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
            _make_entity(
                "C002",
                county_fips=WAYNE,
                population=100,
                p_acquiescence=0.9,
                p_revolution=0.1,
                class_consciousness=0.2,
                national_identity=0.6,
            ),
        )
        view = project_county(WAYNE, graph=_full_graph(), world=world, tick=847)

        assert view.county_fips == WAYNE
        assert view.verified_tick == 847
        assert view.population == 400
        assert view.median_wage == pytest.approx(19.85)
        assert view.imperial_rent_phi == pytest.approx(412.7)
        assert view.bifurcation_score == pytest.approx(-0.32)
        assert view.legitimacy == pytest.approx(0.71)
        assert view.habitability == pytest.approx(0.83)
        assert view.sovereign_id == "SOV_USA"
        assert view.class_composition is not None
        assert view.class_composition.proletariat == pytest.approx(0.382)

    def test_survival_means_are_population_weighted(self) -> None:
        """P(S|A)/P(S|R) match the spec-065 pop-weighted aggregation."""
        world = _world(
            _make_entity(
                "C001", county_fips=WAYNE, population=300, p_acquiescence=0.6, p_revolution=0.4
            ),
            _make_entity(
                "C002", county_fips=WAYNE, population=100, p_acquiescence=1.0, p_revolution=0.0
            ),
        )
        view = project_county(WAYNE, graph=_full_graph(), world=world, tick=1)

        assert view.p_acquiescence == pytest.approx((0.6 * 300 + 1.0 * 100) / 400)
        assert view.p_revolution == pytest.approx((0.4 * 300 + 0.0 * 100) / 400)

    def test_consciousness_matches_bridge_mapping(self) -> None:
        """The simplex equals the pop-weighted ideology bridge mapping."""
        world = _world(
            _make_entity(
                "C001",
                county_fips=WAYNE,
                population=100,
                class_consciousness=0.8,
                national_identity=0.1,
            ),
        )
        view = project_county(WAYNE, graph=_full_graph(), world=world, tick=1)
        r, l_, f = _ideology_to_ternary(0.8, 0.1)

        assert view.consciousness is not None
        assert view.consciousness.revolutionary == pytest.approx(r)
        assert view.consciousness.liberal == pytest.approx(l_)
        assert view.consciousness.fascist == pytest.approx(f)


class TestHonestAbsence:
    """Missing producers project as None — never a default (III.11)."""

    def test_bare_territory_yields_none_fields(self) -> None:
        """A territory with no tick attributes projects all-None quantities."""
        graph = BabylonGraph()
        graph.add_node("T001", NodeType.TERRITORY, county_fips=WAYNE)
        view = project_county(WAYNE, graph=graph, world=_world(), tick=5)

        assert view.median_wage is None
        assert view.imperial_rent_phi is None
        assert view.bifurcation_score is None
        assert view.legitimacy is None
        assert view.class_composition is None
        assert view.habitability is None
        assert view.sovereign_id is None

    def test_unattributed_county_has_no_consciousness(self) -> None:
        """No attributed entities → None, NOT the (0.3, 0.6, 0.1) substrate default.

        The aggregator's substrate default is a deliberate engine-side
        semantic; projected into a dossier it would fabricate a liberal-leaning
        reading for a county nobody has investigated. The projection converts
        the sentinel to honest absence.
        """
        other_county = _make_entity("C009", county_fips="26125", population=500)
        view = project_county(WAYNE, graph=_full_graph(), world=_world(other_county), tick=5)

        assert view.consciousness is None
        assert view.population is None
        assert view.p_acquiescence is None
        assert view.p_revolution is None

    def test_no_territory_node_still_projects_entity_fields(self) -> None:
        """Entity-sourced fields survive a county with no territory node."""
        world = _world(_make_entity("C001", county_fips=WAYNE, population=250))
        view = project_county(WAYNE, graph=BabylonGraph(), world=world, tick=9)

        assert view.population == 250
        assert view.p_acquiescence is not None
        assert view.median_wage is None
        assert view.habitability is None
        assert view.sovereign_id is None

    def test_contested_claims_project_no_single_sovereign(self) -> None:
        """Two CLAIMS edges on the territory → sovereign_id is None."""
        graph = _full_graph()
        graph.add_node("SOV_RED_OGV", NodeType.SOVEREIGN, name="Claimant Two")
        graph.add_edge("SOV_RED_OGV", "T001", EdgeType.CLAIMS)
        view = project_county(WAYNE, graph=graph, world=_world(), tick=5)

        assert view.sovereign_id is None


class TestLoudFailure:
    """A present-but-wrong value raises; only a missing one is absence."""

    def test_malformed_class_distribution_raises(self) -> None:
        """A distribution dict with missing shares fails validation loudly."""
        graph = BabylonGraph()
        graph.add_node(
            "T001",
            NodeType.TERRITORY,
            county_fips=WAYNE,
            tick_class_distribution={"proletariat": 1.0},
        )
        with pytest.raises(ValidationError):
            project_county(WAYNE, graph=graph, world=_world(), tick=1)

    def test_out_of_range_habitability_raises(self) -> None:
        """A present ``habitability`` outside ``[0, 1]`` fails validation loudly."""
        graph = BabylonGraph()
        graph.add_node("T001", NodeType.TERRITORY, county_fips=WAYNE, habitability=1.5)
        with pytest.raises(ValidationError):
            project_county(WAYNE, graph=graph, world=_world(), tick=1)


class TestDeterminism:
    """Identical inputs yield identical frozen dossiers."""

    def test_double_projection_is_identical(self) -> None:
        """Two projections of the same state compare equal."""
        world = _world(_make_entity("C001", county_fips=WAYNE, population=100))
        graph = _full_graph()

        first = project_county(WAYNE, graph=graph, world=world, tick=847)
        second = project_county(WAYNE, graph=graph, world=world, tick=847)

        assert first == second
        assert first.model_dump() == second.model_dump()
