"""Test fixtures for organization unit tests (Feature 031, T013).

Provides factory fixtures for all 4 Detroit subtypes, KeyFigure,
and edge helpers for all 5 organization edge types.
"""

from __future__ import annotations

import pytest

from babylon.models.entities.organization import (
    Business,
    CivilSocietyOrg,
    IntelMethodology,
    KeyFigure,
    PoliticalFaction,
    StateApparatus,
)
from babylon.models.enums import (
    ClassCharacter,
    ConsciousnessTendency,
    EdgeType,
    JurisdictionLevel,
    ServiceType,
)
from babylon.topology.graph import BabylonGraph


@pytest.fixture
def detroit_pd() -> StateApparatus:
    """Detroit Police Department — MUNICIPAL state apparatus."""
    return StateApparatus(
        id="sa-detroit-pd",
        name="Detroit Police Department",
        class_character=ClassCharacter.BOURGEOIS,
        jurisdiction=JurisdictionLevel.MUNICIPAL,
        violence_capacity=0.6,
        surveillance_capacity=0.4,
        intel_methodology=IntelMethodology.local_pd(),
        territory_ids=["t-detroit-downtown", "t-detroit-midtown"],
        headquarters_id="t-detroit-downtown",
        consciousness_tendency=ConsciousnessTendency.LIBERAL,
        is_institution=True,
        institutional_persistence=0.9,
    )


@pytest.fixture
def ford_motor() -> Business:
    """Ford Motor Company — BOURGEOIS business."""
    return Business(
        id="biz-ford",
        name="Ford Motor Company",
        class_character=ClassCharacter.BOURGEOIS,
        sector="Automotive Manufacturing",
        employment_count=5000,
        surplus_extraction_rate=0.3,
        revenue=1000.0,
        cadre_level=0.1,
        cohesion=0.9,
        territory_ids=["t-detroit-dearborn"],
        headquarters_id="t-detroit-dearborn",
        consciousness_tendency=ConsciousnessTendency.LIBERAL,
    )


@pytest.fixture
def revolutionary_workers_party() -> PoliticalFaction:
    """Revolutionary Workers Party — PROLETARIAN political faction."""
    return PoliticalFaction(
        id="pf-rwp",
        name="Revolutionary Workers Party",
        class_character=ClassCharacter.PROLETARIAN,
        ideology="Marxism-Leninism",
        is_player=True,
        cadre_level=0.7,
        cohesion=0.6,
        consciousness_tendency=ConsciousnessTendency.REVOLUTIONARY,
        territory_ids=["t-detroit-downtown"],
        headquarters_id="t-detroit-downtown",
    )


@pytest.fixture
def first_baptist_church() -> CivilSocietyOrg:
    """First Baptist Church — PROLETARIAN civil society org."""
    return CivilSocietyOrg(
        id="cso-fbc",
        name="First Baptist Church",
        class_character=ClassCharacter.PROLETARIAN,
        service_type=ServiceType.RELIGIOUS,
        legitimacy=0.7,
        cadre_level=0.3,
        cohesion=0.8,
        consciousness_tendency=ConsciousnessTendency.LIBERAL,
        territory_ids=["t-detroit-midtown"],
        headquarters_id="t-detroit-midtown",
    )


@pytest.fixture
def sample_key_figure() -> KeyFigure:
    """Sample key figure for testing."""
    return KeyFigure(
        id="kf-001",
        name="Grace Lee Boggs",
        organization_id="pf-rwp",
        role="Chairman",
        structural_importance=0.9,
        is_singleton=True,
    )


@pytest.fixture
def org_graph(
    detroit_pd: StateApparatus,
    ford_motor: Business,
    revolutionary_workers_party: PoliticalFaction,
    first_baptist_church: CivilSocietyOrg,
    sample_key_figure: KeyFigure,
) -> BabylonGraph:
    """Graph with all 4 Detroit org subtypes, a key figure, and edges."""
    G = BabylonGraph()

    # Add territory nodes
    for tid in ["t-detroit-downtown", "t-detroit-midtown", "t-detroit-dearborn"]:
        G.add_node(tid, _node_type="territory", id=tid, name=tid)

    # Add organization nodes
    for org in [detroit_pd, ford_motor, revolutionary_workers_party, first_baptist_church]:
        G.add_node(org.id, _node_type="organization", **org.model_dump())
        for tid in org.territory_ids:
            G.add_edge(org.id, tid, edge_type=EdgeType.PRESENCE)

    # Add key figure node
    G.add_node(
        sample_key_figure.id,
        _node_type="key_figure",
        **sample_key_figure.model_dump(),
    )

    # Add MEMBERSHIP edge
    G.add_edge(
        revolutionary_workers_party.id,
        "social-class-proletariat",
        edge_type=EdgeType.MEMBERSHIP,
        weight=100,
    )

    # Add RECRUITMENT edge
    G.add_edge(
        revolutionary_workers_party.id,
        "social-class-proletariat",
        edge_type=EdgeType.RECRUITMENT,
    )

    # Add EMPLOYMENT edge
    G.add_edge(
        ford_motor.id,
        "social-class-labor-aristocracy",
        edge_type=EdgeType.EMPLOYMENT,
        weight=5000,
    )

    # Add COMMAND edge
    G.add_edge(
        sample_key_figure.id,
        "kf-002",
        edge_type=EdgeType.COMMAND,
    )

    return G
