# web/game/migrations/0003_spec037_simulation_tables.py
"""Spec 037: Game-journal snapshot tables, domain tables, and composition views.

These tables are owned by the engine (DDL via postgres_schema.py). Django uses
unmanaged models (managed=False) for read access. This migration executes raw
SQL to ensure the tables exist when Django starts up, regardless of whether the
engine has already initialized the schema.
"""

from django.db import migrations

from babylon.persistence.postgres_schema import (
    COMMUNITY_SNAPSHOT_DDL,
    ECONOMIC_SUMMARY_DDL,
    EDGE_SNAPSHOT_DDL,
    GAME_DEFINES_SNAPSHOT_DDL,
    HEX_ACTIVITY_DDL,
    HEX_LATEST_DDL,
    HEX_MAP_DDL,
    HEX_SUBSTRATE_DDL,
    ORG_SNAPSHOT_DDL,
    SIMULATION_EVENT_DDL,
    SPEC037_INDEXES_DDL,
    TERRITORY_SNAPSHOT_DDL,
    TICK_EVENT_DDL,
    V_HEX_AID_DDL,
    V_HEX_ECONOMIC_DDL,
    V_HEX_HEAT_DDL,
    V_HEX_INTEL_DDL,
    V_HEX_MOBILIZE_DDL,
)


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    if schema_editor.connection.vendor != "postgresql":
        return

    # Domain tables (static)
    schema_editor.execute(HEX_MAP_DDL)
    schema_editor.execute(GAME_DEFINES_SNAPSHOT_DDL)

    # Snapshot tables (per-tick, append-only)
    schema_editor.execute(TERRITORY_SNAPSHOT_DDL)
    schema_editor.execute(ORG_SNAPSHOT_DDL)
    schema_editor.execute(EDGE_SNAPSHOT_DDL)
    schema_editor.execute(COMMUNITY_SNAPSHOT_DDL)
    schema_editor.execute(HEX_ACTIVITY_DDL)
    schema_editor.execute(ECONOMIC_SUMMARY_DDL)
    schema_editor.execute(TICK_EVENT_DDL)

    # The composition views all read hex_latest — engine-owned (the R7
    # cache, paired with the R8 hex_substrate it references) and, like
    # game_session in 0002, never migration-created before spec-112.
    # Idempotent; existing databases untouched.
    schema_editor.execute(HEX_SUBSTRATE_DDL)
    schema_editor.execute(HEX_LATEST_DDL)

    # simulation_event is likewise engine-owned and required by 0009's
    # unique-index migration on a fresh database.
    schema_editor.execute(SIMULATION_EVENT_DDL)

    # Composition views
    schema_editor.execute(V_HEX_ECONOMIC_DDL)
    schema_editor.execute(V_HEX_MOBILIZE_DDL)
    schema_editor.execute(V_HEX_AID_DDL)
    schema_editor.execute(V_HEX_HEAT_DDL)
    schema_editor.execute(V_HEX_INTEL_DDL)

    # Indexes
    for idx_ddl in SPEC037_INDEXES_DDL:
        schema_editor.execute(idx_ddl)


def backwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    if schema_editor.connection.vendor != "postgresql":
        return

    # Drop views first (depend on tables)
    for view in [
        "v_hex_intel",
        "v_hex_heat",
        "v_hex_aid",
        "v_hex_mobilize",
        "v_hex_economic",
    ]:
        schema_editor.execute(f"DROP VIEW IF EXISTS {view} CASCADE;")

    # Drop tables in reverse dependency order
    for table in [
        "tick_event",
        "economic_summary",
        "hex_activity",
        "community_snapshot",
        "edge_snapshot",
        "org_snapshot",
        "territory_snapshot",
        "game_defines_snapshot",
        "hex_map",
    ]:
        schema_editor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")


class Migration(migrations.Migration):
    dependencies = [
        ("game", "0002_hex_states_schema"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
