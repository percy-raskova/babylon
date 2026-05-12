"""Add idempotency constraints to ``action_result`` and ``simulation_event``.

Spec 061 FR-004 (Real Backend Wire-Up): tick resolution must be
retry-safe. ``ON CONFLICT DO NOTHING`` requires a uniqueness target.
Neither table has one natively — both use ``BIGSERIAL id`` as their
primary key, which is monotonic but offers no semantic dedup.

This migration adds two **unique indexes** (not constraints) so that
nullable natural-key components (``target_id``, ``target_community``,
``entity_id``, ``community_type``) participate via ``COALESCE`` —
because SQL ``UNIQUE`` constraints treat NULL as distinct from itself.

The chosen natural keys:

- ``action_result``: ``(session_id, tick, org_id, action_type,
  COALESCE(target_id, ''), COALESCE(target_community, ''))`` — one row
  per (session, tick, org, action_type, target). Retries of the same
  action against the same target collapse to one row via the
  ``persist_full_tick`` ``ON CONFLICT`` clause introduced in spec 061
  T015.
- ``simulation_event``: ``(session_id, tick, event_type,
  COALESCE(entity_id, ''), COALESCE(community_type, ''))`` — one row
  per distinct event signature per tick.

The pre-spec-061 ``action_result`` and ``simulation_event`` tables are
empty after ``0007_purge_fixture_sessions`` runs, so no pre-existing
duplicates need to be reconciled before the index is created.
"""

from __future__ import annotations

from django.db import migrations


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_action_result_session_tick_natural "
        "ON action_result ("
        "    session_id, tick, org_id, action_type, "
        "    COALESCE(target_id, ''), COALESCE(target_community, '')"
        ");"
    )
    schema_editor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_simulation_event_session_tick_natural "
        "ON simulation_event ("
        "    session_id, tick, event_type, "
        "    COALESCE(entity_id, ''), COALESCE(community_type, '')"
        ");"
    )


def backwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP INDEX IF EXISTS ux_simulation_event_session_tick_natural;")
    schema_editor.execute("DROP INDEX IF EXISTS ux_action_result_session_tick_natural;")


class Migration(migrations.Migration):
    dependencies = [
        ("game", "0008_drop_snapshot_json"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
