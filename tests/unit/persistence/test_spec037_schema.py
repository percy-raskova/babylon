"""Unit tests for Spec 037 game-journal schema DDL constants.

These tests validate that the DDL strings exist, contain expected
table/view names, and that the aggregate list includes all new entries.
No Postgres connection required — pure string inspection.
"""

from __future__ import annotations

import pytest

from babylon.persistence.postgres_schema import (
    COMMUNITY_SNAPSHOT_DDL,
    ECONOMIC_SUMMARY_DDL,
    EDGE_SNAPSHOT_DDL,
    GAME_DEFINES_SNAPSHOT_DDL,
    HEX_ACTIVITY_DDL,
    HEX_MAP_DDL,
    ORG_SNAPSHOT_DDL,
    POSTGRES_SCHEMA_DDL,
    SPEC037_INDEXES_DDL,
    TERRITORY_SNAPSHOT_DDL,
    TICK_EVENT_DDL,
    V_HEX_AID_DDL,
    V_HEX_ECONOMIC_DDL,
    V_HEX_HEAT_DDL,
    V_HEX_INTEL_DDL,
    V_HEX_MOBILIZE_DDL,
)


@pytest.mark.unit
class TestSpec037DomainTables:
    """Layer 7: Static domain tables written once at game init."""

    def test_hex_map_ddl_creates_table(self) -> None:
        assert "CREATE TABLE IF NOT EXISTS hex_map" in HEX_MAP_DDL

    def test_hex_map_has_composite_pk(self) -> None:
        assert "PRIMARY KEY (game_id, h3_index)" in HEX_MAP_DDL

    def test_hex_map_has_postgis_geom(self) -> None:
        assert "geometry(Polygon, 4326)" in HEX_MAP_DDL

    def test_hex_map_has_fips_columns(self) -> None:
        assert "county_fips" in HEX_MAP_DDL
        assert "state_fips" in HEX_MAP_DDL

    def test_game_defines_snapshot_ddl(self) -> None:
        assert "CREATE TABLE IF NOT EXISTS game_defines_snapshot" in GAME_DEFINES_SNAPSHOT_DDL
        assert "JSONB NOT NULL" in GAME_DEFINES_SNAPSHOT_DDL
        assert "REFERENCES game_session(id)" in GAME_DEFINES_SNAPSHOT_DDL


@pytest.mark.unit
class TestSpec037SnapshotTables:
    """Layer 8: Per-tick append-only snapshot tables."""

    def test_territory_snapshot_ddl(self) -> None:
        assert "CREATE TABLE IF NOT EXISTS territory_snapshot" in TERRITORY_SNAPSHOT_DDL

    def test_territory_snapshot_pk(self) -> None:
        assert "PRIMARY KEY (game_id, tick, county_fips)" in TERRITORY_SNAPSHOT_DDL

    def test_territory_snapshot_value_tensor(self) -> None:
        """All 12 ValueTensor4x3 columns present."""
        for dept in ["i", "iia", "iib", "iii"]:
            for component in ["c", "v", "s"]:
                col = f"{component}_dept_{dept}"
                assert col in TERRITORY_SNAPSHOT_DDL, f"Missing column: {col}"

    def test_territory_snapshot_class_distribution(self) -> None:
        for cls in [
            "pop_bourgeoisie",
            "pop_petit_bourgeoisie",
            "pop_labor_aristocracy",
            "pop_proletariat",
            "pop_lumpenproletariat",
            "pop_total",
        ]:
            assert cls in TERRITORY_SNAPSHOT_DDL

    def test_territory_snapshot_check_constraints(self) -> None:
        assert "ck_territory_tick_positive" in TERRITORY_SNAPSHOT_DDL
        assert "ck_territory_pop_nonneg" in TERRITORY_SNAPSHOT_DDL

    def test_org_snapshot_ddl(self) -> None:
        assert "CREATE TABLE IF NOT EXISTS org_snapshot" in ORG_SNAPSHOT_DDL
        assert "PRIMARY KEY (game_id, tick, org_id)" in ORG_SNAPSHOT_DDL

    def test_org_snapshot_type_check(self) -> None:
        assert "ck_org_type_valid" in ORG_SNAPSHOT_DDL
        for org_type in ["state_apparatus", "business", "political_faction", "civil_society"]:
            assert org_type in ORG_SNAPSHOT_DDL

    def test_org_snapshot_ooda_columns(self) -> None:
        assert "ooda_phase" in ORG_SNAPSHOT_DDL
        assert "action_points" in ORG_SNAPSHOT_DDL

    def test_edge_snapshot_ddl(self) -> None:
        assert "CREATE TABLE IF NOT EXISTS edge_snapshot" in EDGE_SNAPSHOT_DDL
        assert "PRIMARY KEY (game_id, tick, source_id, target_id, edge_type)" in EDGE_SNAPSHOT_DDL

    def test_edge_snapshot_mode_check(self) -> None:
        assert "ck_edge_mode_valid" in EDGE_SNAPSHOT_DDL
        for mode in ["EXTRACTIVE", "TRANSACTIONAL", "SOLIDARISTIC", "ANTAGONISTIC", "CO_OPTIVE"]:
            assert mode in EDGE_SNAPSHOT_DDL

    def test_community_snapshot_ddl(self) -> None:
        assert "CREATE TABLE IF NOT EXISTS community_snapshot" in COMMUNITY_SNAPSHOT_DDL
        assert "PRIMARY KEY (game_id, tick, community_id)" in COMMUNITY_SNAPSHOT_DDL

    def test_community_snapshot_checks(self) -> None:
        assert "ck_tendency_valid" in COMMUNITY_SNAPSHOT_DDL
        assert "ck_category_valid" in COMMUNITY_SNAPSHOT_DDL

    def test_hex_activity_ddl(self) -> None:
        assert "CREATE TABLE IF NOT EXISTS hex_activity" in HEX_ACTIVITY_DDL
        assert "PRIMARY KEY (game_id, tick, h3_index)" in HEX_ACTIVITY_DDL
        assert "org_ids" in HEX_ACTIVITY_DDL

    def test_economic_summary_ddl(self) -> None:
        assert "CREATE TABLE IF NOT EXISTS economic_summary" in ECONOMIC_SUMMARY_DDL
        assert "PRIMARY KEY (game_id, tick)" in ECONOMIC_SUMMARY_DDL
        assert "percolation_ratio" in ECONOMIC_SUMMARY_DDL
        assert "fascist_convergence" in ECONOMIC_SUMMARY_DDL

    def test_tick_event_ddl(self) -> None:
        assert "CREATE TABLE IF NOT EXISTS tick_event" in TICK_EVENT_DDL
        assert "PRIMARY KEY (game_id, tick, event_id)" in TICK_EVENT_DDL
        assert "summary" in TICK_EVENT_DDL


@pytest.mark.unit
class TestSpec037CompositionViews:
    """Layer 9: Composition views for React map layers."""

    def test_v_hex_economic_joins_correctly(self) -> None:
        assert "CREATE OR REPLACE VIEW v_hex_economic" in V_HEX_ECONOMIC_DDL
        assert "hex_map h" in V_HEX_ECONOMIC_DDL
        assert "territory_snapshot t" in V_HEX_ECONOMIC_DDL

    def test_v_hex_mobilize_has_left_join(self) -> None:
        assert "LEFT JOIN hex_activity" in V_HEX_MOBILIZE_DDL
        assert "mobilizable_pop" in V_HEX_MOBILIZE_DDL

    def test_v_hex_aid_view(self) -> None:
        assert "CREATE OR REPLACE VIEW v_hex_aid" in V_HEX_AID_DDL
        assert "reproduction_deficit" in V_HEX_AID_DDL

    def test_v_hex_heat_filters_zero(self) -> None:
        assert "WHERE a.heat_total > 0" in V_HEX_HEAT_DDL

    def test_v_hex_intel_is_comprehensive(self) -> None:
        """Intel view should include all territory + hex activity columns."""
        assert "faction_finance_capital" in V_HEX_INTEL_DDL
        assert "faction_security_state" in V_HEX_INTEL_DDL
        assert "faction_settler_populist" in V_HEX_INTEL_DDL
        assert "org_count" in V_HEX_INTEL_DDL


@pytest.mark.unit
class TestSpec037Indexes:
    """Spec 037 index declarations."""

    def test_index_count(self) -> None:
        """21 indexes defined for the 9 new tables."""
        assert len(SPEC037_INDEXES_DDL) == 21

    def test_all_tables_have_tick_index(self) -> None:
        """Every snapshot table should have a game_id+tick index."""
        tick_indexed = [
            idx for idx in SPEC037_INDEXES_DDL if "game_id, tick" in idx and "ON " in idx
        ]
        # territory, org, edge, community, hex_activity, tick_event = 6 tick indexes
        assert len(tick_indexed) >= 6

    def test_partial_index_for_hot_hexes(self) -> None:
        """hex_activity should have a partial index on heat_total > 0."""
        hot_idx = [idx for idx in SPEC037_INDEXES_DDL if "heat_total > 0" in idx]
        assert len(hot_idx) == 1


@pytest.mark.unit
class TestSpec037AggregatedDDL:
    """POSTGRES_SCHEMA_DDL includes all Spec 037 entries."""

    @pytest.mark.parametrize(
        "ddl_const",
        [
            HEX_MAP_DDL,
            GAME_DEFINES_SNAPSHOT_DDL,
            TERRITORY_SNAPSHOT_DDL,
            ORG_SNAPSHOT_DDL,
            EDGE_SNAPSHOT_DDL,
            COMMUNITY_SNAPSHOT_DDL,
            HEX_ACTIVITY_DDL,
            ECONOMIC_SUMMARY_DDL,
            TICK_EVENT_DDL,
            V_HEX_ECONOMIC_DDL,
            V_HEX_MOBILIZE_DDL,
            V_HEX_AID_DDL,
            V_HEX_HEAT_DDL,
            V_HEX_INTEL_DDL,
        ],
    )
    def test_included_in_aggregate_list(self, ddl_const: str) -> None:
        assert ddl_const in POSTGRES_SCHEMA_DDL

    def test_spec037_indexes_in_aggregate(self) -> None:
        for idx in SPEC037_INDEXES_DDL:
            assert idx in POSTGRES_SCHEMA_DDL
