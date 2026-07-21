"""Contract tests for :func:`babylon.projection.social_class.project_social_class`.

Mirrors ``tests/unit/projection/test_county.py``'s discipline for a
per-social-class dossier: one producer per field, honest ``None`` for every
absent quantity, deterministic output. Fixture-fed — no engine tick, no
database — per the keel's fixture-first discipline.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.enums import SocialRole
from babylon.models.enums.topology import NodeType
from babylon.models.world_state import WorldState
from babylon.persistence.county_aggregation import _ideology_to_ternary
from babylon.projection.social_class import project_social_class, social_class_statblocks
from babylon.topology import BabylonGraph

WAYNE = "26163"
CLASS_ID = "C004"

_DISTRIBUTION = {
    "bourgeoisie": 0.077,
    "petit_bourgeoisie": 0.191,
    "labor_aristocracy": 0.226,
    "proletariat": 0.382,
    "lumpenproletariat": 0.124,
}


def _make_entity(
    eid: str = CLASS_ID,
    *,
    county_fips: str | None = WAYNE,
    population: int = 100,
    wealth: float = 0.56,
    organization: float = 0.4,
    repression_faced: float = 0.2,
    p_acquiescence: float = 0.61,
    p_revolution: float = 0.44,
    class_consciousness: float = 0.5,
    national_identity: float = 0.5,
    role: SocialRole = SocialRole.LABOR_ARISTOCRACY,
) -> SocialClass:
    """Build a SocialClass with the fields ``project_social_class`` projects."""
    return SocialClass(
        id=eid,
        name=f"Test {eid}",
        role=role,
        wealth=wealth,
        ideology=IdeologicalProfile(
            class_consciousness=class_consciousness,
            national_identity=national_identity,
        ),
        organization=organization,
        repression_faced=repression_faced,
        p_acquiescence=p_acquiescence,
        p_revolution=p_revolution,
        population=population,
        county_fips=county_fips,
    )


def _world(*entities: SocialClass) -> WorldState:
    """Wrap entities in a minimal WorldState."""
    return WorldState(entities={entity.id: entity for entity in entities})


def _graph_with_class(entity: SocialClass) -> BabylonGraph:
    """A graph carrying ``entity`` as a ``SOCIAL_CLASS`` node, model_dump-stamped
    exactly the way ``WorldState.to_graph`` stamps it in production."""
    graph = BabylonGraph()
    graph.add_node(entity.id, NodeType.SOCIAL_CLASS, **entity.model_dump())
    return graph


def _add_wayne_territory(graph: BabylonGraph) -> BabylonGraph:
    """Attach a Wayne County territory node carrying a class distribution."""
    graph.add_node(
        "T001",
        NodeType.TERRITORY,
        county_fips=WAYNE,
        tick_class_distribution=dict(_DISTRIBUTION),
    )
    return graph


class TestFullDossier:
    """Every field populated when the class node and its county both attribute data."""

    def test_projects_every_field(self) -> None:
        """A fully-attributed class yields a dossier with no absences."""
        entity = _make_entity()
        graph = _add_wayne_territory(_graph_with_class(entity))
        world = _world(entity)

        view = project_social_class(CLASS_ID, graph=graph, world=world, tick=847)

        assert view.class_id == CLASS_ID
        assert view.verified_tick == 847
        assert view.role == SocialRole.LABOR_ARISTOCRACY
        assert view.county_fips == WAYNE
        assert view.population == 100
        assert view.wealth == pytest.approx(0.56)
        assert view.organization == pytest.approx(0.4)
        assert view.repression_faced == pytest.approx(0.2)
        assert view.p_acquiescence == pytest.approx(0.61)
        assert view.p_revolution == pytest.approx(0.44)
        assert view.county_class_composition is not None
        assert view.county_class_composition.proletariat == pytest.approx(0.382)

    def test_consciousness_matches_bridge_mapping(self) -> None:
        """The simplex equals this class's own ideology bridge mapping."""
        entity = _make_entity(class_consciousness=0.8, national_identity=0.1)
        graph = _graph_with_class(entity)
        world = _world(entity)

        view = project_social_class(CLASS_ID, graph=graph, world=world, tick=1)
        r, l_, f = _ideology_to_ternary(0.8, 0.1)

        assert view.consciousness is not None
        assert view.consciousness.revolutionary == pytest.approx(r)
        assert view.consciousness.liberal == pytest.approx(l_)
        assert view.consciousness.fascist == pytest.approx(f)


class TestHonestAbsence:
    """Missing producers project as None — never a default (III.11)."""

    def test_absent_class_id_yields_all_none_fields(self) -> None:
        """A class id tracked nowhere projects an all-None dossier."""
        view = project_social_class("C999", graph=BabylonGraph(), world=_world(), tick=5)

        assert view.class_id == "C999"
        assert view.verified_tick == 5
        assert view.role is None
        assert view.county_fips is None
        assert view.population is None
        assert view.wealth is None
        assert view.organization is None
        assert view.repression_faced is None
        assert view.p_acquiescence is None
        assert view.p_revolution is None
        assert view.consciousness is None
        assert view.county_class_composition is None

    def test_unattributed_class_has_no_composition(self) -> None:
        """A class with no county attribution has no nesting composition."""
        entity = _make_entity(county_fips=None)
        graph = _graph_with_class(entity)
        world = _world(entity)

        view = project_social_class(CLASS_ID, graph=graph, world=world, tick=5)

        assert view.county_fips is None
        assert view.county_class_composition is None
        assert view.wealth is not None  # this class's own fields still project

    def test_attributed_class_with_no_territory_has_no_composition(self) -> None:
        """An attributed class whose county has no territory node yet is None."""
        entity = _make_entity(county_fips=WAYNE)
        graph = _graph_with_class(entity)  # no territory node at all
        world = _world(entity)

        view = project_social_class(CLASS_ID, graph=graph, world=world, tick=5)

        assert view.county_fips == WAYNE
        assert view.county_class_composition is None

    def test_node_present_in_graph_but_not_world_projects_absence(self) -> None:
        """The committed WorldState is the existence authority, not the graph
        alone: a stray graph node no longer tracked in ``world.entities``
        projects absence rather than trusting the lingering graph data."""
        entity = _make_entity()
        graph = _graph_with_class(entity)

        view = project_social_class(CLASS_ID, graph=graph, world=_world(), tick=5)

        assert view.role is None
        assert view.wealth is None

    def test_wrong_node_type_at_the_same_id_projects_absence(self) -> None:
        """A node sharing the id but carrying a different ``_node_type`` is
        never read through as if it were this class (shape-mismatch guard)."""
        entity = _make_entity()
        world = _world(entity)
        graph = BabylonGraph()
        graph.add_node(CLASS_ID, NodeType.TERRITORY, county_fips=WAYNE)

        view = project_social_class(CLASS_ID, graph=graph, world=world, tick=5)

        assert view.role is None
        assert view.wealth is None


class TestLoudFailure:
    """A present-but-wrong value raises; only a missing one is absence."""

    def test_malformed_county_class_distribution_raises(self) -> None:
        """A distribution dict with missing shares fails validation loudly."""
        entity = _make_entity(county_fips=WAYNE)
        graph = _graph_with_class(entity)
        graph.add_node(
            "T001",
            NodeType.TERRITORY,
            county_fips=WAYNE,
            tick_class_distribution={"proletariat": 1.0},
        )
        world = _world(entity)

        with pytest.raises(ValidationError):
            project_social_class(CLASS_ID, graph=graph, world=world, tick=1)


class TestDeterminism:
    """Identical inputs yield identical frozen dossiers."""

    def test_double_projection_is_identical(self) -> None:
        """Two projections of the same state compare equal."""
        entity = _make_entity()
        graph = _add_wayne_territory(_graph_with_class(entity))
        world = _world(entity)

        first = project_social_class(CLASS_ID, graph=graph, world=world, tick=847)
        second = project_social_class(CLASS_ID, graph=graph, world=world, tick=847)

        assert first == second
        assert first.model_dump() == second.model_dump()


class TestSocialClassStatblocks:
    """The per-kind statblock provider factory dispatches on a bound subject."""

    def test_resolves_rows_for_the_bound_subject_only(self) -> None:
        """The built provider answers its own subject and refuses all others."""
        entity = _make_entity()
        graph = _add_wayne_territory(_graph_with_class(entity))
        world = _world(entity)
        view = project_social_class(CLASS_ID, graph=graph, world=world, tick=5)

        provider = social_class_statblocks(view)

        rows = provider(f"social_class/{CLASS_ID}")
        assert rows is not None
        assert ("role", "labor_aristocracy") in rows

        assert provider("social_class/C999") is None
        assert provider("county/26163") is None
