"""RED-then-GREEN: USScenario territories are county-keyed (#39 T4, Amendment U).

Re-keys ``create_us_scenario``'s territories from res-3 H3 hexes to one
Territory per US county, sourced from the committed
``us_county_territories.json`` artifact (no reference-DB access at build
time — see ``babylon.engine.scenarios.us_county_data``). These tests are
therefore fast/unit-tier despite pinning real per-county data.
"""

from __future__ import annotations

import pytest

from babylon.engine.scenarios import create_us_scenario
from babylon.engine.scenarios.us_county_data import load_county_data
from babylon.models.enums import EdgeType

pytestmark = pytest.mark.unit


class TestTerritoriesAreCountyKeyed:
    def test_territory_count_matches_artifact_county_count(self) -> None:
        state, _config, _defines = create_us_scenario()
        data = load_county_data()
        assert len(state.territories) == len(data["counties"])

    def test_every_territory_has_an_opaque_t_prefixed_id(self) -> None:
        state, _config, _defines = create_us_scenario()
        for tid in state.territories:
            assert tid.startswith("T")
            assert tid[1:].isdigit()

    def test_every_territory_carries_a_real_5char_county_fips(self) -> None:
        state, _config, _defines = create_us_scenario()
        data = load_county_data()
        expected_fips = {c["fips"] for c in data["counties"]}
        seen_fips = set()
        for territory in state.territories.values():
            assert territory.county_fips is not None
            assert len(territory.county_fips) == 5
            assert territory.county_fips in expected_fips
            seen_fips.add(territory.county_fips)
        assert seen_fips == expected_fips

    def test_h3_index_is_none_on_every_territory(self) -> None:
        state, _config, _defines = create_us_scenario()
        for territory in state.territories.values():
            assert territory.h3_index is None


class TestFipsSortedDeterminism:
    def test_two_constructions_give_identical_id_to_county_fips_mapping(self) -> None:
        state_a, _config_a, _defines_a = create_us_scenario()
        state_b, _config_b, _defines_b = create_us_scenario()
        mapping_a = {tid: t.county_fips for tid, t in state_a.territories.items()}
        mapping_b = {tid: t.county_fips for tid, t in state_b.territories.items()}
        assert mapping_a == mapping_b

    def test_ids_are_fips_sorted(self) -> None:
        """T0001, T0002, ... assigned over FIPS-ascending order (the
        WorldStateBridge idiom, not e.g. insertion/dict order)."""
        state, _config, _defines = create_us_scenario()
        ordered_ids = sorted(state.territories, key=lambda tid: int(tid[1:]))
        fips_in_id_order = [state.territories[tid].county_fips for tid in ordered_ids]
        assert fips_in_id_order == sorted(fips_in_id_order)


class TestResolveCountyIdentityAgainstGraph:
    def test_resolve_county_identity_returns_real_fips_post_to_graph(self) -> None:
        from babylon.domain.economics.tick.graph_bridge import resolve_county_identity

        state, _config, _defines = create_us_scenario()
        graph = state.to_graph()
        any_tid = next(iter(state.territories))
        node = graph.get_node(any_tid)
        assert node is not None
        identity = resolve_county_identity(node)
        assert identity == state.territories[any_tid].county_fips
        assert identity is not None
        assert len(identity) == 5


class TestOrgTerritoryIdsAndTenancyAreCountyGrain:
    def test_player_org_territory_ids_are_real_scenario_territories(self) -> None:
        state, _config, _defines = create_us_scenario()
        org = state.organizations[state.player_org_id]  # type: ignore[index]
        assert len(org.territory_ids) > 0
        for tid in org.territory_ids:
            assert tid in state.territories

    def test_tenancy_edges_land_on_county_grain_territories(self) -> None:
        state, _config, _defines = create_us_scenario()
        tenancy_edges = [r for r in state.relationships if r.edge_type == EdgeType.TENANCY]
        assert tenancy_edges, "expected at least one TENANCY edge"
        for edge in tenancy_edges:
            territory = state.territories[edge.target_id]
            assert territory.county_fips is not None
            assert territory.h3_index is None


class TestNoFabricatedAdjacency:
    """No real county-adjacency reference source exists (dim_county_geometry
    is boundary geometry, not a precomputed adjacency table) -- Constitution
    III.11 forbids deriving adjacency from geometry. Zero ADJACENCY edges,
    same as the pre-T4 hex scenario (which also never emitted any)."""

    def test_no_adjacency_edges_are_emitted(self) -> None:
        state, _config, _defines = create_us_scenario()
        adjacency_edges = [r for r in state.relationships if r.edge_type == EdgeType.ADJACENCY]
        assert adjacency_edges == []


class TestRawMaterialStockIsStampedFromArtifact:
    """#39 T6: raw_material_stock is stamped straight from the artifact's
    raw_material_value_millions -- never fabricated, never a live DB read
    at scenario-build time (D-T6-2)."""

    def test_every_territory_matches_the_artifact_value(self) -> None:
        state, _config, _defines = create_us_scenario()
        data = load_county_data()
        by_fips = {c["fips"]: c["raw_material_value_millions"] for c in data["counties"]}
        for territory in state.territories.values():
            assert territory.county_fips in by_fips
            assert territory.raw_material_stock == by_fips[territory.county_fips]

    def test_gap_counties_carry_none(self) -> None:
        state, _config, _defines = create_us_scenario()
        data = load_county_data()
        gap_fips = {
            gap["fips"] for gap in data["gaps"] if gap["field"] == "raw_material_value_millions"
        }
        assert gap_fips, "expected at least one raw_material_value_millions gap in the artifact"
        by_county_fips = {t.county_fips: t for t in state.territories.values()}
        for fips in gap_fips:
            assert by_county_fips[fips].raw_material_stock is None

    def test_seeded_counties_carry_a_nonnegative_stock(self) -> None:
        state, _config, _defines = create_us_scenario()
        seeded = [
            t.raw_material_stock
            for t in state.territories.values()
            if t.raw_material_stock is not None
        ]
        assert len(seeded) > 0
        assert all(v >= 0.0 for v in seeded)


class TestRawMaterialCapacityIsStampedFromArtifact:
    """#39 T6 M1: raw_material_capacity (the persisted regeneration ceiling)
    is stamped from the SAME artifact value as raw_material_stock -- the two
    fields must always agree at scenario-build time."""

    def test_capacity_equals_stock_for_every_territory(self) -> None:
        state, _config, _defines = create_us_scenario()
        for territory in state.territories.values():
            assert territory.raw_material_capacity == territory.raw_material_stock

    def test_gap_counties_carry_none_capacity(self) -> None:
        state, _config, _defines = create_us_scenario()
        data = load_county_data()
        gap_fips = {
            gap["fips"] for gap in data["gaps"] if gap["field"] == "raw_material_value_millions"
        }
        by_county_fips = {t.county_fips: t for t in state.territories.values()}
        for fips in gap_fips:
            assert by_county_fips[fips].raw_material_capacity is None
