# Spec-109 A2: hex_latest gains a JSONB ``attributes`` column for
# graph-only per-territory attrs (currently ``habitability``) that have
# no dedicated column yet. The physical column already exists in fresh
# Postgres deployments via postgres_schema.py's HEX_LATEST_DDL
# (``attributes JSONB DEFAULT '{}'::jsonb`` — pre-existing, forward-compat);
# this migration brings Django's model/migration state into agreement with
# that DDL and creates the column for real on SQLite-backed unit tests.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("game", "0012_alter_gameeventlog_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="hexstate",
            name="attributes",
            field=models.JSONField(default=dict),
        ),
    ]
