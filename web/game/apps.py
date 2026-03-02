"""Game app configuration."""

from __future__ import annotations

from django.apps import AppConfig


class GameConfig(AppConfig):
    """Django app for game API and engine bridge."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "game"
