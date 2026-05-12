"""Drop the orphan ``sim.hex_states`` table and ``sim`` schema.

Spec 061 FR-030 (Real Backend Wire-Up):
    The ``sim.hex_states`` table created by migration 0002 is no longer
    written or read anywhere — it predates the spec 037 normalized
    ``hex_state`` table and the snapshot pipeline. The Django backend's
    ``seed_hex_data`` management command does NOT target it; the engine's
    persistence layer does not touch it. Drop both the table and the
    enclosing schema.

This migration is **forward-only** by design: the table held only
fixture-era data that the spec 061 cutover migration (``0007``) also
purges.
"""

from __future__ import annotations

from django.db import migrations


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP TABLE IF EXISTS sim.hex_states CASCADE;")
    schema_editor.execute("DROP SCHEMA IF EXISTS sim CASCADE;")


def backwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    # Forward-only per FR-030. Re-creating the orphan table would
    # reintroduce dead state that has no writers or readers.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("game", "0005_game_session_snapshot_json"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
