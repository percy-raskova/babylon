"""Contract tests for :func:`babylon.projection.organization.project_organization`.

The organization read-model's behavioral contract: one producer per field,
honest ``None`` for every unattributed quantity, deterministic output.
Fixture-fed — no engine tick, no database — per the keel's fixture-first
discipline. Also pins the :class:`~babylon.projection.view_models.OrganizationView`
shape contract (frozen, ``extra="forbid"``, hydration) — folded into this
module rather than ``tests/unit/projection/test_view_models.py`` to avoid a
second parallel-WO collision point on that shared file (WO-18 deviation,
noted in the integrator report).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.entities.organization import PoliticalFaction
from babylon.models.enums import ClassCharacter, ConsciousnessTendency, LegalStanding, OrgType
from babylon.models.enums.topology import EdgeType, NodeType
from babylon.models.world_state import WorldState
from babylon.projection.fog.filter import ORG_POLITICAL_FIELDS
from babylon.projection.organization import (
    MATERIAL_VIEW_FIELDS,
    POLITICAL_VIEW_FIELDS,
    org_statblocks,
    project_organization,
)
from babylon.projection.view_models import OrganizationView, hydrate_record
from babylon.topology import BabylonGraph

ORG_ID = "org_rwp"


def _rwp_org(org_id: str = ORG_ID) -> PoliticalFaction:
    """The world's roster entry — mirrors ``test_organization_detroit.py``'s RWP fixture."""
    return PoliticalFaction(
        id=org_id,
        name="Revolutionary Workers Party",
        class_character=ClassCharacter.PROLETARIAN,
        cohesion=0.6,
        cadre_level=0.7,
        budget=5_000.0,
        legal_standing=LegalStanding.REGISTERED,
        consciousness_tendency=ConsciousnessTendency.REVOLUTIONARY,
        territory_ids=["territory_detroit"],
        headquarters_id="territory_detroit",
        heat=0.3,
        ideology="Marxism-Leninism",
        is_player=True,
        relationship_to_player="self",
    )


def _world(*, known: bool = True, org_id: str = ORG_ID) -> WorldState:
    """A ``WorldState`` whose roster does (or does not) know ``org_id``."""
    if not known:
        return WorldState()
    return WorldState(organizations={org_id: _rwp_org(org_id)})


def _full_graph(org_id: str = ORG_ID, **overrides: object) -> BabylonGraph:
    """A graph carrying a fully-attributed ``organization`` node for ``org_id``."""
    graph = BabylonGraph()
    attrs: dict[str, object] = {
        "name": "Revolutionary Workers Party",
        "org_type": OrgType.POLITICAL_FACTION,
        "class_character": ClassCharacter.PROLETARIAN,
        "legal_standing": LegalStanding.REGISTERED,
        "budget": 5_000.0,
        "territory_ids": ["territory_detroit"],
        "headquarters_id": "territory_detroit",
        "is_institution": False,
        "heat": 0.3,
        "consciousness_tendency": ConsciousnessTendency.REVOLUTIONARY,
        "cohesion": 0.6,
        "cadre_level": 0.7,
    }
    attrs.update(overrides)
    graph.add_node(org_id, NodeType.ORGANIZATION, **attrs)
    return graph


class TestFullDossier:
    """Every field populated when the org node is fully attributed."""

    def test_projects_every_field(self) -> None:
        """A fully-attributed organization yields a dossier with no absences."""
        view = project_organization(ORG_ID, graph=_full_graph(), world=_world(), tick=847)

        assert view.kind == "organization"
        assert view.org_id == ORG_ID
        assert view.verified_tick == 847
        assert view.name == "Revolutionary Workers Party"
        assert view.org_type == OrgType.POLITICAL_FACTION
        assert view.class_character == ClassCharacter.PROLETARIAN
        assert view.legal_standing == LegalStanding.REGISTERED
        assert view.budget == pytest.approx(5_000.0)
        assert view.territory_ids == ("territory_detroit",)
        assert view.headquarters_id == "territory_detroit"
        assert view.is_institution is False
        assert view.heat == pytest.approx(0.3)
        assert view.consciousness_tendency == ConsciousnessTendency.REVOLUTIONARY
        assert view.cohesion == pytest.approx(0.6)
        assert view.cadre_level == pytest.approx(0.7)

    def test_empty_territory_ids_is_a_real_fact_not_an_absence(self) -> None:
        """Zero territories is a positive fact — the field is present, not ``None``."""
        view = project_organization(
            ORG_ID,
            graph=_full_graph(territory_ids=[]),
            world=_world(),
            tick=1,
        )
        assert view.territory_ids == ()


class TestHonestAbsence:
    """Missing producers project as None — never a default (III.11)."""

    def test_unknown_to_both_graph_and_world_yields_all_none(self) -> None:
        """An id neither the graph nor the world knows projects a bare dossier."""
        view = project_organization(
            "org_nobody_has_heard_of", graph=BabylonGraph(), world=_world(known=False), tick=5
        )

        assert view.name is None
        assert view.org_type is None
        assert view.class_character is None
        assert view.legal_standing is None
        assert view.budget is None
        assert view.territory_ids is None
        assert view.headquarters_id is None
        assert view.is_institution is None
        assert view.heat is None
        assert view.consciousness_tendency is None
        assert view.cohesion is None
        assert view.cadre_level is None

    def test_single_county_scenario_seeds_zero_organizations(self) -> None:
        """The WO-18 no-producer contingency: an empty world roster, by itself,
        yields an all-absent dossier even with a live-looking graph node."""
        view = project_organization(ORG_ID, graph=_full_graph(), world=_world(known=False), tick=5)
        assert view.name is None
        assert view.budget is None

    def test_world_roster_entry_without_a_graph_node_yields_all_none(self) -> None:
        """The world knows the org, but no matching graph node exists — absent.

        Reads strictly from the graph (the module docstring's ``one
        producer per field`` ruling); a roster entry alone never fabricates
        field values.
        """
        view = project_organization(ORG_ID, graph=BabylonGraph(), world=_world(), tick=5)
        assert view.name is None
        assert view.cohesion is None

    def test_graph_node_of_a_different_type_is_not_projected(self) -> None:
        """A same-id node that isn't an ``organization`` node is never mistaken for one."""
        graph = BabylonGraph()
        graph.add_node(ORG_ID, NodeType.TERRITORY, county_fips="26163")
        view = project_organization(ORG_ID, graph=graph, world=_world(), tick=5)
        assert view.name is None

    def test_a_partially_attributed_node_leaves_only_the_missing_keys_none(self) -> None:
        """A node carrying only SOME attribute keys projects the rest ``None``."""
        graph = BabylonGraph()
        graph.add_node(ORG_ID, NodeType.ORGANIZATION, name="Ford Motor Company", budget=1_000.0)
        view = project_organization(ORG_ID, graph=graph, world=_world(), tick=5)

        assert view.name == "Ford Motor Company"
        assert view.budget == pytest.approx(1_000.0)
        assert view.org_type is None
        assert view.territory_ids is None
        assert view.cohesion is None


class TestLoudFailure:
    """A present-but-wrong value raises; only a missing one is absence."""

    def test_out_of_range_cohesion_raises(self) -> None:
        """A cohesion value outside ``[0, 1]`` fails validation loudly."""
        graph = _full_graph(cohesion=1.5)
        with pytest.raises(ValidationError):
            project_organization(ORG_ID, graph=graph, world=_world(), tick=1)

    def test_unrecognized_org_type_raises(self) -> None:
        """A string that isn't a real ``OrgType`` member fails validation loudly."""
        graph = _full_graph(org_type="not_a_real_org_type")
        with pytest.raises(ValidationError):
            project_organization(ORG_ID, graph=graph, world=_world(), tick=1)


class TestDeterminism:
    """Identical inputs yield identical frozen dossiers."""

    def test_double_projection_is_identical(self) -> None:
        """Two projections of the same state compare equal."""
        graph = _full_graph()
        world = _world()

        first = project_organization(ORG_ID, graph=graph, world=world, tick=847)
        second = project_organization(ORG_ID, graph=graph, world=world, tick=847)

        assert first == second
        assert first.model_dump() == second.model_dump()


class TestFogFieldSplit:
    """The documented material/political field split is a verifiable claim.

    ``apply_fog`` is deliberately never called here (WO-18: fog gating is
    Lane E WO-41's job) — this only pins that the module's OWN declared
    political-field list is a real subset of the canonical
    :data:`~babylon.projection.fog.filter.ORG_POLITICAL_FIELDS`, so the
    docstring's claim can't silently drift from the source of truth.
    """

    def test_political_view_fields_are_a_subset_of_org_political_fields(self) -> None:
        assert set(POLITICAL_VIEW_FIELDS) <= set(ORG_POLITICAL_FIELDS)

    def test_material_and_political_fields_partition_the_declared_optionals(self) -> None:
        identity = {"kind", "org_id", "verified_tick"}
        declared = set(OrganizationView.model_fields) - identity
        assert set(MATERIAL_VIEW_FIELDS) | set(POLITICAL_VIEW_FIELDS) == declared
        assert set(MATERIAL_VIEW_FIELDS).isdisjoint(POLITICAL_VIEW_FIELDS)


class TestOrgStatblocks:
    """The per-kind statblock provider (WO-18's Wave-1 shared-file discipline)."""

    def test_it_answers_only_for_its_own_subject(self) -> None:
        view = project_organization(ORG_ID, graph=_full_graph(), world=_world(), tick=5)
        provider = org_statblocks(view)

        rows = provider(f"organization/{ORG_ID}")
        assert rows is not None
        assert ("name", "Revolutionary Workers Party") in rows

    def test_it_returns_none_for_any_other_subject(self) -> None:
        view = project_organization(ORG_ID, graph=_full_graph(), world=_world(), tick=5)
        provider = org_statblocks(view)

        assert provider("organization/some-other-org") is None
        assert provider(f"county/{ORG_ID}") is None


class TestOrganizationViewShape:
    """The :class:`OrganizationView` model contract (frozen, extra-forbid, hydration)."""

    def test_it_is_frozen(self) -> None:
        view = OrganizationView(org_id=ORG_ID, verified_tick=1)
        with pytest.raises(ValidationError):
            view.org_id = "different"  # type: ignore[misc]

    def test_extra_keys_are_rejected(self) -> None:
        with pytest.raises(ValidationError):
            OrganizationView(org_id=ORG_ID, verified_tick=1, undeclared_field=1)  # type: ignore[call-arg]

    def test_minimal_record_defaults_optionals_to_none(self) -> None:
        view = OrganizationView(org_id=ORG_ID, verified_tick=1)
        assert view.name is None
        assert view.territory_ids is None
        assert view.cadre_level is None

    def test_hydrate_record_dispatches_organization_by_kind(self) -> None:
        payload = {"kind": "organization", "org_id": ORG_ID, "verified_tick": 1, "budget": 500.0}
        record = hydrate_record(payload)
        assert isinstance(record, OrganizationView)
        assert record.budget == pytest.approx(500.0)

    def test_org_id_requires_at_least_one_character(self) -> None:
        with pytest.raises(ValidationError):
            OrganizationView(org_id="", verified_tick=1)


class TestEdgeIndependence:
    """Existence of unrelated edges never leaks into the dossier."""

    def test_a_wages_edge_between_unrelated_nodes_does_not_affect_projection(self) -> None:
        graph = _full_graph()
        graph.add_node("C001", NodeType.SOCIAL_CLASS, wealth=1.0)
        graph.add_edge("C001", ORG_ID, EdgeType.MEMBERSHIP)
        view = project_organization(ORG_ID, graph=graph, world=_world(), tick=1)
        assert view.name == "Revolutionary Workers Party"
