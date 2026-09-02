"""Static contracts for the one-way committed-tick V2 PostgreSQL activation."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PERSISTENCE = ROOT / "rust" / "crates" / "babylon-persistence"
PREPARATION = PERSISTENCE / "migrations" / "0010_committed_tick_v2_preparation.sql"
ACTIVATION = PERSISTENCE / "migrations" / "0011_committed_tick_v2_activation.sql"

INCOMPATIBLE_RELATIONS = (
    "babylon_state.campaign",
    "babylon_state.campaign_foundation",
    "babylon_state.tick_commit",
    "babylon_state.tick_action_batch_v1",
    "babylon_state.graph_node_v1",
    "babylon_state.graph_node_f64_v1",
    "babylon_state.graph_edge_v1",
    "babylon_state.graph_hyperedge_v1",
    "babylon_state.graph_hyperedge_member_v1",
    "babylon_state.graph_edge_f64_v1",
    "babylon_state.graph_node_currency_v1",
    "babylon_state.graph_hyperedge_f64_v1",
    "babylon_state.world_register_v1",
    "babylon_state.territory_state_v1",
    "babylon_state.territory_state_field_v1",
    "babylon_state.hex_state_delta_v1",
    "babylon_state.organization_state_v1",
    "babylon_state.organization_territory_v1",
    "babylon_state.organization_state_field_v1",
    "babylon_state.tick_event_v1",
    "babylon_state.tick_event_field_v1",
    "babylon_state.checkpoint_manifest",
    "babylon_state.checkpoint_section_v1",
    "babylon_state.archive_dirty_receipt_v1",
)


def test_v2_activation_has_a_dedicated_compiled_registry() -> None:
    source = (PERSISTENCE / "src" / "schema_epoch.rs").read_text()

    assert "pub(crate) const CURRENT_SCHEMA_EPOCH: usize = 7;" in source
    assert 'include_str!("../migrations/0010_committed_tick_v2_preparation.sql")' in source
    assert 'include_str!("../migrations/0011_committed_tick_v2_activation.sql")' in source
    assert "pub fn compiled_committed_tick_v2_activation_migrations(" in source
    assert "MigrationVersion::try_from(10)" in source
    assert "MigrationVersion::try_from(11)" in source


def test_preparation_creates_the_receipt_event_inventory_and_ledger_shapes() -> None:
    sql = PREPARATION.read_text()

    for relation in (
        "babylon_meta.committed_tick_v2_authority_ledger",
        "babylon_meta.committed_tick_v2_incompatible_inventory",
        "babylon_state.tick_choice_receipt_v1",
        "babylon_state.tick_choice_receipt_branch_v1",
        "babylon_state.tick_choice_receipt_carrier_element_v1",
        "babylon_state.tick_event_v2",
        "babylon_state.tick_event_field_v2",
    ):
        assert f"CREATE TABLE {relation}" in sql

    assert sql.count("NUMERIC(20, 0)") >= 5
    assert "18446744073709551615" in sql
    assert "18446744073709551616" in sql
    assert "DEFERRABLE INITIALLY DEFERRED" in sql
    assert "choice_receipt_ordinal" in sql
    assert "REFERENCES babylon_state.tick_choice_receipt_v1" in sql
    assert "CREATE CONSTRAINT TRIGGER" in sql
    assert "DEFERRABLE INITIALLY DEFERRED" in sql
    for relation in INCOMPATIBLE_RELATIONS:
        assert f"'{relation}'" in sql
        assert f"FROM {relation}" in sql
    for destructive in ("DROP TABLE", "TRUNCATE", "DELETE FROM"):
        assert destructive not in sql.upper()


def test_activation_refuses_any_nonzero_or_drifted_inventory_before_v2_authority() -> None:
    sql = ACTIVATION.read_text()

    assert "LOCK TABLE" in sql
    assert "IN ACCESS EXCLUSIVE MODE" in sql
    assert "committed_tick_v2_activation_refused_incompatible_inventory" in sql
    assert "ERRCODE = 'P0001'" in sql
    for relation in INCOMPATIBLE_RELATIONS:
        assert f"'{relation}'" in sql
        assert f"FROM {relation}" in sql
    assert "DROP CONSTRAINT tick_commit_envelope_layout_v1" in sql
    assert "ADD CONSTRAINT tick_commit_envelope_layout_v2" in sql
    assert "CHECK (envelope_layout_version = 2)" in sql
    assert sql.count("DROP TABLE") == 2
    assert sql.index("DROP TABLE babylon_state.tick_event_field_v1") < sql.index(
        "DROP TABLE babylon_state.tick_event_v1"
    )
    assert "committed_tick_v2_authority_ledger" not in sql
    for destructive in ("TRUNCATE", "DELETE FROM"):
        assert destructive not in sql.upper()
