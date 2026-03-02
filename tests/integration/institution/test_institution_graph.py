"""Integration tests for Institution graph round-trip (Feature 040, US1).

Validates:
- Institution nodes survive to_graph() -> from_graph() round-trip
- Nested models (InternalBalanceOfForces, ReproductionMechanism) preserved
- frozenset fields (legal_authorities, jurisdiction) reconstructed
- PRESENCE and HOUSES edges created in to_graph()
- Computed fields excluded in from_graph()
"""

from __future__ import annotations

import pytest

from babylon.models.entities.institution import (
    Institution,
    InternalBalanceOfForces,
    ReproductionMechanism,
    SpawningBlueprint,
)
from babylon.models.entities.organization import StateApparatus
from babylon.models.entities.territory import Territory
from babylon.models.enums import (
    ApparatusType,
    ClassCharacter,
    ClassInscription,
    EdgeType,
    JurisdictionLevel,
    LifecyclePhase,
    OperationalProfile,
    OrgType,
    RulingClassFraction,
    SectorType,
    SocialFunction,
)
from babylon.models.world_state import WorldState


@pytest.fixture()
def doj_institution() -> Institution:
    """DOJ institution fixture."""
    return Institution(
        id="doj",
        name="Department of Justice",
        apparatus_type=ApparatusType.RSA_JUDICIAL,
        social_function=SocialFunction.ADJUDICATION,
        class_inscription=ClassInscription.BOURGEOIS,
        internal_balance=InternalBalanceOfForces(
            liberal_technocratic=0.5,
            revanchist_fascist=0.3,
            institutionalist_bonapartist=0.2,
            internal_contestation=0.3,
        ),
        budget=1_000_000.0,
        legal_authorities=frozenset(["federal_prosecution", "civil_rights_enforcement"]),
        personnel_capacity=500,
        formalization_level=0.95,
        institutional_inertia=0.8,
        legitimacy=0.7,
        housed_org_ids=["fbi"],
        territory_ids=["T001"],
        jurisdiction=frozenset(["national"]),
        lifecycle_function=None,
        reproduction=ReproductionMechanism(
            recruitment_pipeline=True,
            training_program=True,
            succession_protocol=True,
            budget_independence=0.8,
            legal_self_perpetuation=True,
        ),
        spawning_blueprints=[
            SpawningBlueprint(
                org_type=OrgType.STATE_APPARATUS,
                default_class_character=ClassCharacter.BOURGEOIS,
                base_attributes={"jurisdiction": "national"},
            ),
        ],
    )


@pytest.fixture()
def dps_institution() -> Institution:
    """Detroit Public Schools ISA institution fixture."""
    return Institution(
        id="dps",
        name="Detroit Public Schools",
        apparatus_type=ApparatusType.ISA_EDUCATIONAL,
        social_function=SocialFunction.EDUCATION,
        class_inscription=ClassInscription.CONTESTED,
        internal_balance=InternalBalanceOfForces(
            liberal_technocratic=0.6,
            revanchist_fascist=0.2,
            institutionalist_bonapartist=0.2,
        ),
        budget=500_000.0,
        personnel_capacity=3000,
        legitimacy=0.5,
        territory_ids=["T002"],
        lifecycle_function=LifecyclePhase.D_DEPENDENT,
        reproduction=ReproductionMechanism(
            recruitment_pipeline=True,
            training_program=True,
            succession_protocol=True,
            budget_independence=0.3,
            legal_self_perpetuation=True,
        ),
    )


@pytest.fixture()
def territory_national() -> Territory:
    """National territory fixture."""
    return Territory(
        id="T001",
        name="National",
        sector_type=SectorType.GOVERNMENT,
        profile=OperationalProfile.HIGH_PROFILE,
    )


@pytest.fixture()
def fbi_org() -> StateApparatus:
    """FBI organization fixture."""
    return StateApparatus(
        id="fbi",
        name="Federal Bureau of Investigation",
        class_character="bourgeois",
        jurisdiction=JurisdictionLevel.NATIONAL,
        violence_capacity=0.5,
        surveillance_capacity=0.8,
        territory_ids=["T001"],
    )


class TestInstitutionGraphRoundTrip:
    """Test that institutions survive to_graph() -> from_graph() round-trip."""

    @pytest.mark.integration
    def test_basic_round_trip(
        self,
        doj_institution: Institution,
        territory_national: Territory,
        fbi_org: StateApparatus,
    ) -> None:
        """Institution should survive full graph round-trip."""
        state = WorldState(
            institutions={"doj": doj_institution},
            territories={"T001": territory_national},
            organizations={"fbi": fbi_org},
        )

        G = state.to_graph()
        reconstructed = WorldState.from_graph(G, tick=0)

        # Institution preserved
        assert "doj" in reconstructed.institutions
        doj = reconstructed.institutions["doj"]
        assert doj.name == "Department of Justice"
        assert doj.apparatus_type == ApparatusType.RSA_JUDICIAL
        assert doj.social_function == SocialFunction.ADJUDICATION

    @pytest.mark.integration
    def test_nested_models_preserved(
        self,
        doj_institution: Institution,
        territory_national: Territory,
        fbi_org: StateApparatus,
    ) -> None:
        """Nested InternalBalanceOfForces and ReproductionMechanism preserved."""
        state = WorldState(
            institutions={"doj": doj_institution},
            territories={"T001": territory_national},
            organizations={"fbi": fbi_org},
        )

        G = state.to_graph()
        reconstructed = WorldState.from_graph(G, tick=0)

        doj = reconstructed.institutions["doj"]
        # InternalBalanceOfForces
        assert doj.internal_balance.liberal_technocratic == 0.5
        assert doj.internal_balance.revanchist_fascist == 0.3
        assert doj.internal_balance.institutionalist_bonapartist == 0.2
        assert doj.internal_balance.internal_contestation == 0.3
        # hegemonic_fraction (computed) should work after reconstruction
        assert doj.internal_balance.hegemonic_fraction == RulingClassFraction.LIBERAL_TECHNOCRATIC

        # ReproductionMechanism
        assert doj.reproduction.recruitment_pipeline is True
        assert doj.reproduction.budget_independence == 0.8
        # reproduction_capacity (computed) should work
        assert doj.reproduction.reproduction_capacity > 0.8

    @pytest.mark.integration
    def test_frozenset_fields_preserved(
        self,
        doj_institution: Institution,
        territory_national: Territory,
        fbi_org: StateApparatus,
    ) -> None:
        """frozenset fields (legal_authorities, jurisdiction) survive round-trip."""
        state = WorldState(
            institutions={"doj": doj_institution},
            territories={"T001": territory_national},
            organizations={"fbi": fbi_org},
        )

        G = state.to_graph()
        reconstructed = WorldState.from_graph(G, tick=0)

        doj = reconstructed.institutions["doj"]
        assert isinstance(doj.legal_authorities, frozenset)
        assert "federal_prosecution" in doj.legal_authorities
        assert "civil_rights_enforcement" in doj.legal_authorities
        assert isinstance(doj.jurisdiction, frozenset)
        assert "national" in doj.jurisdiction

    @pytest.mark.integration
    def test_presence_edges_created(
        self,
        doj_institution: Institution,
        territory_national: Territory,
        fbi_org: StateApparatus,
    ) -> None:
        """to_graph() should create PRESENCE edges to territory_ids."""
        state = WorldState(
            institutions={"doj": doj_institution},
            territories={"T001": territory_national},
            organizations={"fbi": fbi_org},
        )

        G = state.to_graph()
        assert G.has_edge("doj", "T001")
        edge_data = G.edges["doj", "T001"]
        assert edge_data["edge_type"] == EdgeType.PRESENCE.value

    @pytest.mark.integration
    def test_houses_edges_created(
        self,
        doj_institution: Institution,
        territory_national: Territory,
        fbi_org: StateApparatus,
    ) -> None:
        """to_graph() should create HOUSES edges to housed_org_ids."""
        state = WorldState(
            institutions={"doj": doj_institution},
            territories={"T001": territory_national},
            organizations={"fbi": fbi_org},
        )

        G = state.to_graph()
        assert G.has_edge("doj", "fbi")
        edge_data = G.edges["doj", "fbi"]
        assert edge_data["edge_type"] == EdgeType.HOUSES.value

    @pytest.mark.integration
    def test_multiple_institutions_round_trip(
        self,
        doj_institution: Institution,
        dps_institution: Institution,
        territory_national: Territory,
    ) -> None:
        """Multiple institutions should all survive round-trip."""
        state = WorldState(
            institutions={"doj": doj_institution, "dps": dps_institution},
            territories={"T001": territory_national},
        )

        G = state.to_graph()
        reconstructed = WorldState.from_graph(G, tick=0)

        assert len(reconstructed.institutions) == 2
        assert "doj" in reconstructed.institutions
        assert "dps" in reconstructed.institutions

    @pytest.mark.integration
    def test_spawning_blueprints_preserved(
        self,
        doj_institution: Institution,
        territory_national: Territory,
    ) -> None:
        """Spawning blueprints should survive round-trip."""
        state = WorldState(
            institutions={"doj": doj_institution},
            territories={"T001": territory_national},
        )

        G = state.to_graph()
        reconstructed = WorldState.from_graph(G, tick=0)

        doj = reconstructed.institutions["doj"]
        assert len(doj.spawning_blueprints) == 1
        bp = doj.spawning_blueprints[0]
        assert bp.org_type == OrgType.STATE_APPARATUS
        assert bp.default_class_character == ClassCharacter.BOURGEOIS

    @pytest.mark.integration
    def test_lifecycle_function_preserved(
        self,
        dps_institution: Institution,
    ) -> None:
        """lifecycle_function should survive round-trip."""
        state = WorldState(
            institutions={"dps": dps_institution},
        )

        G = state.to_graph()
        reconstructed = WorldState.from_graph(G, tick=0)

        dps = reconstructed.institutions["dps"]
        assert dps.lifecycle_function == LifecyclePhase.D_DEPENDENT
