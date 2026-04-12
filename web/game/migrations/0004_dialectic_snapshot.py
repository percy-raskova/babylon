"""Django migration: Dialectic JSONB snapshot table.

Creates the ``dialectic_snapshot`` table for persisting v2 dialectic
state as tick-keyed JSONB. This is a Django-managed table (unlike the
Feature 037 ``managed = False`` tables), following the user's directive
to use Django's migration framework for v2 persistence.
"""

from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Create dialectic_snapshot table for v2 engine state."""

    dependencies = [
        ("game", "0003_spec037_simulation_tables"),
    ]

    operations = [
        migrations.CreateModel(
            name="DialecticSnapshot",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("tick", models.IntegerField(db_index=True)),
                (
                    "dialectic_id",
                    models.UUIDField(
                        db_index=True,
                        help_text="Maps to Dialectic.id from the engine.",
                    ),
                ),
                (
                    "type_tag",
                    models.CharField(
                        max_length=64,
                        db_index=True,
                        help_text="Discriminator for Dialectic subclass.",
                    ),
                ),
                ("weight", models.FloatField()),
                (
                    "state_json",
                    models.JSONField(
                        help_text="Full serialized Dialectic via Pydantic model_dump()."
                    ),
                ),
                (
                    "parent_id",
                    models.UUIDField(
                        null=True,
                        blank=True,
                        help_text="Predecessor dialectic if produced by sublation.",
                    ),
                ),
                (
                    "game",
                    models.ForeignKey(
                        to="game.GameSession",
                        on_delete=django.db.models.deletion.CASCADE,
                        db_column="game_id",
                    ),
                ),
            ],
            options={
                "db_table": "dialectic_snapshot",
                "ordering": ["tick"],
            },
        ),
        migrations.AddConstraint(
            model_name="dialecticsnapshot",
            constraint=models.UniqueConstraint(
                fields=["game", "tick", "dialectic_id"],
                name="uq_dialectic_snapshot",
            ),
        ),
        # Morphism snapshot table
        migrations.CreateModel(
            name="MorphismSnapshot",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("tick", models.IntegerField(db_index=True)),
                (
                    "morphism_id",
                    models.UUIDField(db_index=True),
                ),
                ("source_dialectic_id", models.UUIDField()),
                ("target_dialectic_id", models.UUIDField()),
                (
                    "relation",
                    models.CharField(max_length=32),
                ),
                ("weight", models.FloatField(default=1.0)),
                (
                    "metadata_json",
                    models.JSONField(default=dict),
                ),
                (
                    "game",
                    models.ForeignKey(
                        to="game.GameSession",
                        on_delete=django.db.models.deletion.CASCADE,
                        db_column="game_id",
                    ),
                ),
            ],
            options={
                "db_table": "morphism_snapshot",
                "ordering": ["tick"],
            },
        ),
        migrations.AddConstraint(
            model_name="morphismsnapshot",
            constraint=models.UniqueConstraint(
                fields=["game", "tick", "morphism_id"],
                name="uq_morphism_snapshot",
            ),
        ),
    ]
