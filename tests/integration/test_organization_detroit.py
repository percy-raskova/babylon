"""Integration tests: Organization Base Model — Detroit scenarios (Feature 031, T033).

Nine end-to-end scenarios from quickstart.md validating the full Organization
Base Model across all subtypes, composition calculators, consciousness effect,
topology classification, key figure identification, and graph round-trip.
"""

from __future__ import annotations

import networkx as nx
import pytest
from pydantic import ValidationError

from babylon.config.defines import OrganizationDefines
from babylon.domain.organizations.composition import (
    class_composition,
    lifecycle_composition,
)
from babylon.domain.organizations.topology import (
    classify_topology,
    cohesion_loss_on_removal,
    identify_key_figures,
)
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
    LegalStanding,
    OrgType,
    ServiceType,
    TopologyType,
)
from babylon.models.world_state import WorldState
from babylon.topology.graph import BabylonGraph

# =========================================================================
# Shared Detroit Fixtures
# =========================================================================


@pytest.fixture
def detroit_pd() -> StateApparatus:
    """Scenario 1: Detroit PD as StateApparatus."""
    return StateApparatus(
        id="org_detroit_pd",
        name="Detroit Police Department",
        class_character=ClassCharacter.BOURGEOIS,
        cohesion=0.7,
        cadre_level=0.5,
        budget=300_000_000.0,
        legal_standing=LegalStanding.SOVEREIGN,
        consciousness_tendency=ConsciousnessTendency.LIBERAL,
        territory_ids=["territory_detroit"],
        headquarters_id="territory_detroit",
        heat=0.0,
        jurisdiction=JurisdictionLevel.MUNICIPAL,
        violence_capacity=0.7,
        surveillance_capacity=0.4,
        legal_authority=["arrest", "search_warrant", "civil_asset_forfeiture"],
        intel_methodology=IntelMethodology(
            centrality_analysis=True,
            equivalence_analysis=False,
            template_matching=False,
            temporal_analysis=False,
            observation_ceiling=0.2,
        ),
    )


@pytest.fixture
def ford() -> Business:
    """Scenario 2: Ford Motor as Business."""
    return Business(
        id="org_ford",
        name="Ford Motor Company",
        class_character=ClassCharacter.BOURGEOIS,
        cohesion=0.8,
        cadre_level=0.2,
        budget=158_000_000_000.0,
        legal_standing=LegalStanding.CHARTERED,
        consciousness_tendency=ConsciousnessTendency.LIBERAL,
        territory_ids=["territory_detroit", "territory_dearborn"],
        headquarters_id="territory_dearborn",
        heat=0.0,
        sector="Motor Vehicle Manufacturing",
        employment_count=31_000,
        surplus_extraction_rate=0.45,
        revenue=158_000_000_000.0,
    )


@pytest.fixture
def rwp() -> PoliticalFaction:
    """Scenario 3: Revolutionary Workers Party as PoliticalFaction."""
    return PoliticalFaction(
        id="org_rwp",
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


@pytest.fixture
def church() -> CivilSocietyOrg:
    """Scenario 4: First Baptist Church as CivilSocietyOrg."""
    return CivilSocietyOrg(
        id="org_first_baptist",
        name="First Baptist Church of Detroit",
        class_character=ClassCharacter.CONTESTED,
        cohesion=0.8,
        cadre_level=0.3,
        budget=500_000.0,
        legal_standing=LegalStanding.REGISTERED,
        consciousness_tendency=ConsciousnessTendency.LIBERAL,
        territory_ids=["territory_detroit"],
        headquarters_id="territory_detroit",
        heat=0.0,
        service_type=ServiceType.RELIGIOUS,
        legitimacy=0.7,
    )


# =========================================================================
# Scenario 1: Detroit PD as StateApparatus (US1, SC-001)
# =========================================================================


class TestScenario1DetroitPD:
    """StateApparatus instantiation with Sparrow-grounded intel methodology."""

    @pytest.mark.integration
    def test_org_type(self, detroit_pd: StateApparatus) -> None:
        assert detroit_pd.org_type == OrgType.STATE_APPARATUS

    @pytest.mark.integration
    def test_legal_standing(self, detroit_pd: StateApparatus) -> None:
        assert detroit_pd.legal_standing == LegalStanding.SOVEREIGN

    @pytest.mark.integration
    def test_intel_observation_ceiling(self, detroit_pd: StateApparatus) -> None:
        assert detroit_pd.intel_methodology.observation_ceiling == 0.2

    @pytest.mark.integration
    def test_intel_centrality_enabled(self, detroit_pd: StateApparatus) -> None:
        assert detroit_pd.intel_methodology.centrality_analysis is True

    @pytest.mark.integration
    def test_intel_equivalence_disabled(self, detroit_pd: StateApparatus) -> None:
        assert detroit_pd.intel_methodology.equivalence_analysis is False

    @pytest.mark.integration
    def test_frozen_immutability(self, detroit_pd: StateApparatus) -> None:
        with pytest.raises(ValidationError):
            detroit_pd.heat = 0.5  # type: ignore[misc]


# =========================================================================
# Scenario 2: Ford Motor as Business (US1, SC-001)
# =========================================================================


class TestScenario2FordMotor:
    """Business instantiation with QCEW-derived employment data."""

    @pytest.mark.integration
    def test_org_type(self, ford: Business) -> None:
        assert ford.org_type == OrgType.BUSINESS

    @pytest.mark.integration
    def test_employment_count(self, ford: Business) -> None:
        assert ford.employment_count == 31_000

    @pytest.mark.integration
    def test_surplus_extraction_rate(self, ford: Business) -> None:
        assert ford.surplus_extraction_rate == 0.45

    @pytest.mark.integration
    def test_consciousness_tendency(self, ford: Business) -> None:
        assert ford.consciousness_tendency == ConsciousnessTendency.LIBERAL


# =========================================================================
# Scenario 3: Revolutionary Workers Party as PoliticalFaction (US1, SC-001)
# =========================================================================


class TestScenario3RWP:
    """PoliticalFaction instantiation — player's revolutionary faction."""

    @pytest.mark.integration
    def test_org_type(self, rwp: PoliticalFaction) -> None:
        assert rwp.org_type == OrgType.POLITICAL_FACTION

    @pytest.mark.integration
    def test_consciousness_tendency(self, rwp: PoliticalFaction) -> None:
        assert rwp.consciousness_tendency == ConsciousnessTendency.REVOLUTIONARY

    @pytest.mark.integration
    def test_is_player(self, rwp: PoliticalFaction) -> None:
        assert rwp.is_player is True


# =========================================================================
# Scenario 4: Mainstream Church as CivilSocietyOrg (US1, SC-001)
# =========================================================================


class TestScenario4Church:
    """CivilSocietyOrg instantiation — liberal civil society."""

    @pytest.mark.integration
    def test_org_type(self, church: CivilSocietyOrg) -> None:
        assert church.org_type == OrgType.CIVIL_SOCIETY

    @pytest.mark.integration
    def test_service_type(self, church: CivilSocietyOrg) -> None:
        assert church.service_type == ServiceType.RELIGIOUS

    @pytest.mark.integration
    def test_legitimacy(self, church: CivilSocietyOrg) -> None:
        assert church.legitimacy == 0.7

    @pytest.mark.integration
    def test_consciousness_tendency(self, church: CivilSocietyOrg) -> None:
        assert church.consciousness_tendency == ConsciousnessTendency.LIBERAL


# =========================================================================
# Scenario 5: Class Composition (US2, SC-002)
# =========================================================================


class TestScenario5ClassComposition:
    """Class composition via MEMBERSHIP edges."""

    @pytest.mark.integration
    def test_class_distribution(self) -> None:
        """RWP membership: 500 industrial, 300 service, 50 petty-bourgeois."""
        G = BabylonGraph()
        G.add_node("org_rwp", _node_type="organization")
        G.add_node("sc-ind", _node_type="social_class", role="proletariat_industrial")
        G.add_node("sc-svc", _node_type="social_class", role="proletariat_service")
        G.add_node("sc-pb", _node_type="social_class", role="petty_bourgeoisie")
        G.add_edge("org_rwp", "sc-ind", edge_type=EdgeType.MEMBERSHIP, weight=500)
        G.add_edge("org_rwp", "sc-svc", edge_type=EdgeType.MEMBERSHIP, weight=300)
        G.add_edge("org_rwp", "sc-pb", edge_type=EdgeType.MEMBERSHIP, weight=50)

        result = class_composition("org_rwp", G)
        assert result.axis == "class"
        assert result.total_members == pytest.approx(850.0)
        assert result.distribution["proletariat_industrial"] == pytest.approx(500 / 850)
        assert result.distribution["proletariat_service"] == pytest.approx(300 / 850)
        assert result.distribution["petty_bourgeoisie"] == pytest.approx(50 / 850)
        assert abs(sum(result.distribution.values()) - 1.0) < 0.01


# =========================================================================
# Scenario 6: Lifecycle Composition (US2, SC-002)
# =========================================================================


class TestScenario6LifecycleComposition:
    """D/P/D' lifecycle distribution via MEMBERSHIP edges."""

    @pytest.mark.integration
    def test_lifecycle_distribution(self) -> None:
        """Church: 200 youth, 600 adult, 200 elder."""
        G = BabylonGraph()
        G.add_node("org_first_baptist", _node_type="organization")
        G.add_node("sc-youth", _node_type="social_class", lifecycle_phase="youth")
        G.add_node("sc-adult", _node_type="social_class", lifecycle_phase="adult")
        G.add_node("sc-elder", _node_type="social_class", lifecycle_phase="elder")
        G.add_edge("org_first_baptist", "sc-youth", edge_type=EdgeType.MEMBERSHIP, weight=200)
        G.add_edge("org_first_baptist", "sc-adult", edge_type=EdgeType.MEMBERSHIP, weight=600)
        G.add_edge("org_first_baptist", "sc-elder", edge_type=EdgeType.MEMBERSHIP, weight=200)

        result = lifecycle_composition("org_first_baptist", G)
        assert result.axis == "lifecycle"
        assert result.total_members == pytest.approx(1000.0)
        assert result.distribution["youth"] == pytest.approx(0.2)
        assert result.distribution["adult"] == pytest.approx(0.6)
        assert result.distribution["elder"] == pytest.approx(0.2)


# =========================================================================
# Scenario 7: Consciousness Effect — Revolutionary Faction (US3, SC-003)
# =========================================================================


class TestScenario8KeyFigures:
    """STAR topology identification and key figure analysis."""

    @pytest.fixture
    def star_graph(self) -> nx.DiGraph[str]:
        """Church COMMAND graph: pastor as hub, 3 deacons as leaves."""
        G = BabylonGraph()
        nodes = ["kf_pastor", "kf_deacon_1", "kf_deacon_2", "kf_deacon_3"]
        for n in nodes:
            G.add_node(n, _node_type="key_figure", name=n, role="key_figure")
        G.add_edge("kf_pastor", "kf_deacon_1", edge_type=EdgeType.COMMAND)
        G.add_edge("kf_pastor", "kf_deacon_2", edge_type=EdgeType.COMMAND)
        G.add_edge("kf_pastor", "kf_deacon_3", edge_type=EdgeType.COMMAND)
        return G

    @pytest.mark.integration
    def test_star_topology_detected(self, star_graph: nx.DiGraph[str]) -> None:
        members = ["kf_pastor", "kf_deacon_1", "kf_deacon_2", "kf_deacon_3"]
        topo = classify_topology("org_first_baptist", members, star_graph)
        assert topo.topology_type == TopologyType.STAR

    @pytest.mark.integration
    def test_pastor_is_sole_key_figure(self, star_graph: nx.DiGraph[str]) -> None:
        members = ["kf_pastor", "kf_deacon_1", "kf_deacon_2", "kf_deacon_3"]
        key_figs = identify_key_figures("org_first_baptist", members, star_graph)
        assert len(key_figs) == 1
        assert key_figs[0].id == "kf_pastor"
        assert key_figs[0].is_singleton is True

    @pytest.mark.integration
    def test_cohesion_loss_on_pastor_removal(self) -> None:
        """Removing pastor from church (cohesion 0.8): 0.8 - 0.2 = 0.6."""
        defines = OrganizationDefines()
        new_cohesion = cohesion_loss_on_removal(
            current_cohesion=0.8,
            removed_count=1,
            defines=defines,
        )
        assert new_cohesion == pytest.approx(0.6)


# =========================================================================
# Scenario 9: Graph Round-Trip (US1, SC-001/SC-007)
# =========================================================================


class TestScenario9GraphRoundTrip:
    """Organization survives WorldState to_graph/from_graph round-trip."""

    @pytest.mark.integration
    def test_round_trip_preserves_orgs(
        self,
        detroit_pd: StateApparatus,
        ford: Business,
        rwp: PoliticalFaction,
        church: CivilSocietyOrg,
    ) -> None:
        """All 4 subtypes survive serialization round-trip."""
        pastor = KeyFigure(
            id="kf_pastor",
            name="Pastor Johnson",
            organization_id="org_first_baptist",
            role="pastor",
            structural_importance=0.9,
            is_singleton=True,
        )
        deacon = KeyFigure(
            id="kf_deacon_1",
            name="Deacon Smith",
            organization_id="org_first_baptist",
            role="deacon",
        )

        world = WorldState(
            tick=0,
            organizations={
                "org_detroit_pd": detroit_pd,
                "org_ford": ford,
                "org_rwp": rwp,
                "org_first_baptist": church,
            },
            key_figures={
                "kf_pastor": pastor,
                "kf_deacon_1": deacon,
            },
        )

        graph = world.to_graph()
        reconstructed = WorldState.from_graph(graph, tick=0)

        # All organizations survive
        assert len(reconstructed.organizations) == 4

        # Correct subtypes reconstructed
        assert isinstance(reconstructed.organizations["org_detroit_pd"], StateApparatus)
        assert isinstance(reconstructed.organizations["org_ford"], Business)
        assert isinstance(reconstructed.organizations["org_rwp"], PoliticalFaction)
        assert isinstance(reconstructed.organizations["org_first_baptist"], CivilSocietyOrg)

        # Field fidelity
        assert reconstructed.organizations["org_ford"].employment_count == 31_000
        assert (
            reconstructed.organizations["org_detroit_pd"].intel_methodology.observation_ceiling
            == 0.2
        )
        assert reconstructed.organizations["org_rwp"].is_player is True
        assert reconstructed.organizations["org_first_baptist"].legitimacy == 0.7

        # Key figures survive
        assert len(reconstructed.key_figures) == 2
        assert reconstructed.key_figures["kf_pastor"].organization_id == "org_first_baptist"

    @pytest.mark.integration
    def test_graph_node_types(
        self,
        detroit_pd: StateApparatus,
        church: CivilSocietyOrg,
    ) -> None:
        """Graph nodes carry correct _node_type markers."""
        pastor = KeyFigure(
            id="kf_pastor",
            name="Pastor Johnson",
            organization_id="org_first_baptist",
            role="pastor",
        )

        world = WorldState(
            tick=0,
            organizations={
                "org_detroit_pd": detroit_pd,
                "org_first_baptist": church,
            },
            key_figures={"kf_pastor": pastor},
        )

        graph = world.to_graph()
        assert graph.nodes["org_detroit_pd"]["_node_type"] == "organization"
        assert graph.nodes["org_first_baptist"]["_node_type"] == "organization"
        assert graph.nodes["kf_pastor"]["_node_type"] == "key_figure"
