"""Behavioral contract for headless balkanization seeding (P25 U6, ADR132).

The FACTION honest-empty repair: ``apply_balkanization_seed`` gives every
engine scenario the spec-070 political layer (4 BalkanizationFactions,
3 Sovereigns, county-FIPS-resolved INFLUENCES, total CLAIMS coverage via the
literal pass + the ADR080 SOV_USA_FED fallback) — shapes that were produced
ONLY by the disabled legacy web bridge before this unit.
"""

from __future__ import annotations

import pytest

from babylon.engine.scenarios.balkanization_seed import apply_balkanization_seed
from babylon.engine.scenarios.single_county import create_single_county_scenario
from babylon.models.entities.territory import Territory
from babylon.models.enums import EdgeType, SectorType
from babylon.models.world_state import WorldState

pytestmark = pytest.mark.unit

_WAYNE_FIPS = "26163"
_ALL_FACTIONS = {
    "FAC_WORKERS_CONGRESS",
    "FAC_DECOLONIAL",
    "FAC_RESTORATIONIST",
    "FAC_LIBERAL_IMPERIAL",
}
_ALL_SOVEREIGNS = {"SOV_USA_FED", "SOV_CAN_FED", "SOV_EXTERIOR_NULL"}


def _seeded_single_county() -> WorldState:
    state, _config, _defines = create_single_county_scenario()
    return apply_balkanization_seed(state)


def _claims(state: WorldState) -> list:
    return [r for r in state.relationships if r.edge_type == EdgeType.CLAIMS]


def _influences(state: WorldState) -> list:
    return [r for r in state.relationships if r.edge_type == EdgeType.INFLUENCES]


class TestPoliticalEntitySeeding:
    def test_seeds_all_factions_and_sovereigns(self) -> None:
        state = _seeded_single_county()
        assert set(state.factions) == _ALL_FACTIONS
        assert set(state.sovereigns) == _ALL_SOVEREIGNS

    def test_input_state_is_untouched(self) -> None:
        state, _config, _defines = create_single_county_scenario()
        before = len(state.relationships)
        apply_balkanization_seed(state)
        assert len(state.relationships) == before
        assert state.factions == {}


class TestCountyFipsInfluenceResolution:
    def test_county_territory_gets_all_four_faction_influences(self) -> None:
        state = _seeded_single_county()
        influences = _influences(state)
        assert {r.source_id for r in influences} == _ALL_FACTIONS
        assert all(r.target_id == "T001" for r in influences)

    def test_influence_values_match_the_committed_seed(self) -> None:
        """The Wayne territory receives the seed's Wayne county values —
        including the REAL 2024 Republican vote share for RESTORATIONIST."""
        from babylon.data.game.balkanization import load_seed_influences

        wayne_seed = {
            e["faction_id"]: e["influence_level"]
            for e in load_seed_influences()
            if e["territory_id"] == _WAYNE_FIPS
        }
        state = _seeded_single_county()
        for rel in _influences(state):
            assert rel.influence_level == pytest.approx(wayne_seed[rel.source_id])
        restorationist = next(r for r in _influences(state) if r.source_id == "FAC_RESTORATIONIST")
        assert restorationist.influence_level == pytest.approx(0.3372)
        assert restorationist.support_type == "electoral"

    def test_abstract_territory_gets_no_influences(self) -> None:
        """A territory with neither county_fips nor a mapped h3_index (the
        two_node-style abstract terrain) receives no INFLUENCES — but is
        still claimed (fallback), preserving SC-017 coverage."""
        from babylon.engine.scenarios._legacy import create_two_node_scenario

        state, _config, _defines = create_two_node_scenario()
        seeded = apply_balkanization_seed(state)
        assert _influences(seeded) == []
        claims = _claims(seeded)
        assert {r.target_id for r in claims} == set(seeded.territories)

    def test_hex_territories_resolve_through_the_injected_map(self) -> None:
        """Hex-grain scenarios broadcast the county's intensive influence
        value to every hex in the county (constant broadcast — exact for an
        intensive quantity)."""
        hex_a = "862749b27ffffff"
        hex_b = "862749b2fffffff"
        state = WorldState(
            tick=0,
            entities={},
            territories={
                hex_a: Territory(
                    id=hex_a, h3_index=hex_a, name="Wayne hex A", sector_type=SectorType.RESIDENTIAL
                ),
                hex_b: Territory(
                    id=hex_b, h3_index=hex_b, name="Wayne hex B", sector_type=SectorType.RESIDENTIAL
                ),
            },
            relationships=[],
            event_log=[],
        )
        seeded = apply_balkanization_seed(
            state, hex_to_county={hex_a: _WAYNE_FIPS, hex_b: _WAYNE_FIPS}
        )
        influences = _influences(seeded)
        assert len(influences) == 8  # 4 factions x 2 hexes
        by_target: dict[str, dict[str, float]] = {}
        for rel in influences:
            by_target.setdefault(rel.target_id, {})[rel.source_id] = rel.influence_level
        assert by_target[hex_a] == by_target[hex_b]  # constant broadcast


class TestClaimsCoverage:
    def test_every_territory_claimed_exactly_once(self) -> None:
        """The literal pass and the FR-040b fallback never double-claim."""
        state = _seeded_single_county()
        claims = _claims(state)
        assert sorted(r.target_id for r in claims) == sorted(state.territories)

    def test_wayne_claim_comes_from_the_literal_seed_pass(self) -> None:
        """SOV_USA_FED's seed file claim on FIPS 26163 resolves onto the
        Wayne territory node (the county-FIPS namespace fix made the
        literal pass live — before U6 it was a permanent no-op)."""
        state = _seeded_single_county()
        wayne_claims = [r for r in _claims(state) if r.target_id == "T001"]
        assert len(wayne_claims) == 1
        claim = wayne_claims[0]
        assert claim.source_id == "SOV_USA_FED"
        assert claim.control_level == 1.0
        assert claim.legal_status == "de_jure"

    def test_exterior_null_never_claims_interior_territories(self) -> None:
        """ADR080: SOV_EXTERIOR_NULL stays reserved for genuinely external
        nodes; interior territories always resolve to SOV_USA_FED."""
        state = _seeded_single_county()
        assert all(r.source_id != "SOV_EXTERIOR_NULL" for r in _claims(state))

    def test_external_namespace_claims_are_skipped(self) -> None:
        """'canada' / 'rest_of_usa' claims never bind to scenario
        territories (they are persistence.external_node registry IDs)."""
        state = _seeded_single_county()
        claim_sources = {r.source_id for r in _claims(state)}
        assert "SOV_CAN_FED" not in claim_sources


class TestDeterminismAndRoundTrip:
    def test_seeding_is_deterministic(self) -> None:
        a = _seeded_single_county()
        b = _seeded_single_county()
        assert [r.model_dump() for r in a.relationships] == [
            r.model_dump() for r in b.relationships
        ]

    def test_political_layer_survives_graph_round_trip(self) -> None:
        """to_graph stamps NodeType.FACTION / NodeType.SOVEREIGN and
        from_graph reconstructs the full layer — the projection and system
        consumers read exactly these shapes."""
        state = _seeded_single_county()
        graph = state.to_graph()
        faction_nodes = [n for n, d in graph.nodes(data=True) if d.get("_node_type") == "faction"]
        sovereign_nodes = [
            n for n, d in graph.nodes(data=True) if d.get("_node_type") == "sovereign"
        ]
        assert set(faction_nodes) == _ALL_FACTIONS
        assert set(sovereign_nodes) == _ALL_SOVEREIGNS

        restored = WorldState.from_graph(graph, tick=state.tick)
        assert set(restored.factions) == _ALL_FACTIONS
        assert set(restored.sovereigns) == _ALL_SOVEREIGNS
        assert sorted(
            (r.source_id, r.target_id)
            for r in restored.relationships
            if r.edge_type == EdgeType.INFLUENCES
        ) == sorted((r.source_id, r.target_id) for r in _influences(state))
