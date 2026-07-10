# web/game/migrations/0002_hex_states_schema.py
from django.db import migrations

from babylon.persistence.postgres_schema import (
    ACTION_RESULT_DDL,
    GAME_SESSION_DDL,
    GAME_TURN_DDL,
)


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    if schema_editor.connection.vendor == "postgresql":
        # Game-management tables first — the hex SQL below FK-references
        # game_session, yet no migration created these before spec-112:
        # every long-lived DB got them from engine init, so a from-zero
        # Django migrate had NEVER worked (found by the first CI run after
        # the 2026-07-10 Actions re-enable). Idempotent IF NOT EXISTS —
        # existing databases are untouched.
        schema_editor.execute(GAME_SESSION_DDL)
        schema_editor.execute(GAME_TURN_DDL)
        schema_editor.execute(ACTION_RESULT_DDL)

        schema_editor.execute("CREATE SCHEMA IF NOT EXISTS sim;")
        schema_editor.execute("""
            CREATE TABLE IF NOT EXISTS sim.hex_states (
                id          SERIAL PRIMARY KEY,
                game_id     UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
                tick        INTEGER NOT NULL,
                h3_index    VARCHAR(20) NOT NULL,
                county_fips VARCHAR(5) NOT NULL,
                county_name VARCHAR(50) NOT NULL,
                profit_rate       DOUBLE PRECISION,
                exploitation_rate DOUBLE PRECISION,
                occ               DOUBLE PRECISION,
                imperial_rent     DOUBLE PRECISION,
                heat              DOUBLE PRECISION,
                org_presence      INTEGER DEFAULT 0,
                dominant_class    VARCHAR(30),
                population        INTEGER,
                UNIQUE(game_id, tick, h3_index)
            );
        """)
        schema_editor.execute(
            "CREATE INDEX IF NOT EXISTS idx_hex_game_tick ON sim.hex_states(game_id, tick);"
        )


def backwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("DROP TABLE IF EXISTS sim.hex_states CASCADE;")
        schema_editor.execute("DROP SCHEMA IF EXISTS sim CASCADE;")


class Migration(migrations.Migration):
    dependencies = [
        ("game", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
