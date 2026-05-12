"""Drop the now-unused ``snapshot_json`` column on ``game_session``.

Spec 061 (Real Backend Wire-Up): the ``snapshot_json`` column was added
by migration ``0005`` for the legacy ``MockEngineBridge`` to stash a
whole-session JSONB blob. The real ``EngineBridge`` writes normalized
snapshot tables (``territory_snapshot``, ``org_snapshot``, etc.) and
never reads or writes ``snapshot_json``. Now that migration ``0007`` has
purged all fixture-era rows, the column carries no data and no writers.

The reverse migration re-creates the column for symmetry with ``0005``,
though the spec-061 cutover does not contemplate going back.
"""

from __future__ import annotations

from django.db import migrations


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE game_session DROP COLUMN IF EXISTS snapshot_json;")


def backwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "ALTER TABLE game_session "
        "ADD COLUMN IF NOT EXISTS snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb;"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("game", "0007_purge_fixture_sessions"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
