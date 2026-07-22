"""Behavioral contract for the electoral fixture scenario (P25 U5, ADR131).

The producer layer the ambient machine reads: NPC PoliticalFaction orgs (two
duopoly machines + two latent currents), weighted MEMBERSHIP edges party →
social_class, and donor-dependence TRANSACTIONAL funding Business → party.
NOT one of the six qa:regression scenarios — byte-safety by disjointness.
"""

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
