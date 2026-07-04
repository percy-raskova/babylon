"""Django app configuration for the Observatory."""

from __future__ import annotations

from django.apps import AppConfig


class ObservatoryConfig(AppConfig):
    """Observatory app: read-only dashboard over the simulation database.

    Deliberately minimal — no ``ready()`` engine boot (unlike ``GameConfig``).
    The Observatory holds no state and owns no tables; it only reads the
    ``sim`` alias through declared SQL views.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "observatory"
    verbose_name = "Observatory (sim-db debug dashboard)"
