"""Behavioral contract for the electoral fixture scenario (P25 U5, ADR131).

The producer layer the ambient machine reads: NPC PoliticalFaction orgs (two
duopoly machines + two latent currents), weighted MEMBERSHIP edges party →
social_class, and donor-dependence TRANSACTIONAL funding Business → party.
NOT one of the six qa:regression scenarios — byte-safety by disjointness.
"""

import pytest

from babylon.engine.scenarios.electoral_fixture import create_electoral_fixture_scenario
from babylon.models.entities.organization import Business, PoliticalFaction
from babylon.models.enums import EdgeType, OrgType
from babylon.models.world_state import WorldState


def _build() -> WorldState:
    state, _config, _defines = create_electoral_fixture_scenario()
    return state


def test_seeds_the_duopoly_and_the_latent_currents():
    state = _build()
    factions = {
        org_id: org
        for org_id, org in state.organizations.items()
        if isinstance(org, PoliticalFaction)
    }
    assert len(factions) == 4
    ideologies = {f.ideology for f in factions.values()}
    assert "liberal_imperial" in ideologies
    assert "restorationist" in ideologies
    assert "social_democratic" in ideologies
    assert "fascist" in ideologies
    assert all(not f.is_player for f in factions.values())  # ambient machine: all NPC


def test_membership_edges_reach_the_class_base():
    graph = _build().to_graph()
    membership = [
        (s, t)
        for s, t, d in graph.edges(data=True)
        if d.get("edge_type") == EdgeType.MEMBERSHIP.value
    ]
    assert len(membership) >= 4  # every party holds at least one class link
    sources = {s for s, _ in membership}
    assert "org/party-liberal" in sources
    assert "org/party-restorationist" in sources


def test_donor_dependence_is_a_transactional_flow():
    state = _build()
    donors = [o for o in state.organizations.values() if isinstance(o, Business)]
    assert donors, "the fixture seeds a finance donor"
    graph = state.to_graph()
    funding = [
        (s, t, d.get("value_flow", 0.0))
        for s, t, d in graph.edges(data=True)
        if d.get("edge_type") == EdgeType.TRANSACTIONAL.value and s == "org/donor-finance"
    ]
    assert funding, "donor funding edges exist"
    assert all(flow > 0.0 for _, _, flow in funding)
    # The duopoly machines are donor-funded; the socdem current is not.
    funded = {t for _, t, _ in funding}
    assert {"org/party-liberal", "org/party-restorationist"} <= funded
    assert "org/party-socdem" not in funded


def test_balkanization_layer_is_seeded():
    """U6 (ADR132): the electoral scenario carries BOTH political entity
    families — PoliticalFaction orgs (U5) and the spec-070 layer
    (BalkanizationFaction nodes, Sovereigns, Wayne's real electoral
    INFLUENCES, SOV_USA_FED's literal claim on the FIPS-grounded T001)."""
    state = _build()
    assert set(state.factions) == {
        "FAC_WORKERS_CONGRESS",
        "FAC_DECOLONIAL",
        "FAC_RESTORATIONIST",
        "FAC_LIBERAL_IMPERIAL",
    }
    assert set(state.sovereigns) == {
        "SOV_USA_FED",
        "SOV_CAN_FED",
        "SOV_EXTERIOR_NULL",
        "SOV_MI_STATE",  # U9: the ADMINISTERS child (ADR135)
    }
    assert state.territories["T001"].county_fips == "26163"

    influences = [r for r in state.relationships if r.edge_type == EdgeType.INFLUENCES]
    assert {r.source_id for r in influences} == set(state.factions)
    assert all(r.target_id == "T001" for r in influences)
    restorationist = next(r for r in influences if r.source_id == "FAC_RESTORATIONIST")
    assert restorationist.influence_level == pytest.approx(0.3372)  # real Wayne 2024

    claims = [r for r in state.relationships if r.edge_type == EdgeType.CLAIMS]
    assert [(r.source_id, r.target_id) for r in claims] == [("SOV_USA_FED", "T001")]


def test_graph_round_trip_preserves_the_parties():
    state = _build()
    restored = WorldState.from_graph(state.to_graph(), tick=state.tick)
    parties = {
        org_id: org
        for org_id, org in restored.organizations.items()
        if isinstance(org, PoliticalFaction)
    }
    assert set(parties) == {
        "org/party-liberal",
        "org/party-restorationist",
        "org/party-socdem",
        "org/party-fascist",
    }
    assert parties["org/party-liberal"].org_type == OrgType.POLITICAL_FACTION
    assert parties["org/party-fascist"].ideology == "fascist"


def test_u9_veto_terrain_institution_and_administers_dag():
    """U9 (ADR135): the fixture carries the FIRST production Institution
    node (RSA_JUDICIAL bench, its liberal_technocratic weight = the
    strike-down tolerance base) and the FIRST ADMINISTERS edge ever built
    (SOV_USA_FED → SOV_MI_STATE, the preemption DAG)."""
    from babylon.models.enums import ApparatusType

    state = _build()
    judiciary = state.institutions["INST_FED_JUDICIARY"]
    assert judiciary.apparatus_type is ApparatusType.RSA_JUDICIAL
    assert judiciary.internal_balance.liberal_technocratic == pytest.approx(0.6)

    administers = [r for r in state.relationships if r.edge_type == EdgeType.ADMINISTERS]
    assert [(r.source_id, r.target_id) for r in administers] == [("SOV_USA_FED", "SOV_MI_STATE")]
    assert state.sovereigns["SOV_MI_STATE"].ruling_faction_id is None


def test_u9_veto_terrain_survives_the_graph_round_trip():
    """The judiciary node and the ADMINISTERS edge reconstruct from the
    graph — the veto terrain is durable state, not builder-only decoration."""
    state = _build()
    restored = WorldState.from_graph(state.to_graph(), tick=state.tick)
    assert "INST_FED_JUDICIARY" in restored.institutions
    balance = restored.institutions["INST_FED_JUDICIARY"].internal_balance
    assert balance.liberal_technocratic == pytest.approx(0.6)
    assert "SOV_MI_STATE" in restored.sovereigns
    administers = [r for r in restored.relationships if r.edge_type == EdgeType.ADMINISTERS]
    assert [(r.source_id, r.target_id) for r in administers] == [("SOV_USA_FED", "SOV_MI_STATE")]
