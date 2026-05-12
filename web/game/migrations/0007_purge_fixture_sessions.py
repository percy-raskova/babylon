"""Cutover: purge all pre-spec-061 ``game_session`` rows and their dependents.

Spec 061 FR-033 (Real Backend Wire-Up):
    Pre-cutover sessions were written by ``MockEngineBridge`` into the
    ``snapshot_json`` JSONB blob on ``game_session``. The post-cutover
    ``EngineBridge`` writes normalized snapshot tables instead. These
    two persistence shapes are architecturally orthogonal — there is no
    in-place upgrade path. The cutover migration discards all pre-existing
    sessions; players start fresh against the real engine.

The ``DELETE FROM game_session`` cascades via ``ON DELETE CASCADE``
foreign keys to every session-scoped table: ``game_turn``,
``action_result``, ``simulation_event``, ``node_state``, ``edge_state``,
the spec 037 snapshot tables, ``tick_log``, ``tick_summary``,
``hex_state``, ``community_state``, ``community_membership``,
``contradiction_field``, ``edge_curvature``, etc.

**Forward-only.** There is no recovery path for fixture-era sessions.
Per FR-033 (clarified): the cutover removes them, period.
"""

from __future__ import annotations

from django.db import migrations


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DELETE FROM game_session;")


def backwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("game", "0006_drop_sim_hex_states"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
