from django.db import migrations


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "ALTER TABLE game_session ADD COLUMN IF NOT EXISTS snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb;"
    )


def backwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("ALTER TABLE game_session DROP COLUMN IF EXISTS snapshot_json;")


class Migration(migrations.Migration):
    dependencies = [
        ("game", "0004_dialectic_snapshot"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
