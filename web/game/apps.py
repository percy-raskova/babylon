"""Game app configuration."""

from __future__ import annotations

import logging
import os

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class GameConfig(AppConfig):
    """Django app for game API and engine bridge."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "game"

    def ready(self) -> None:
        """Initialize EngineBridge for PostgreSQL-backed runtime.

        Skips initialization for SQLite-based test settings.
        All engine/persistence imports are delegated to ``engine_bridge.py``
        to preserve the import boundary (FR-008).
        """
        if settings.DEBUG and os.environ.get("RUN_MAIN") != "true":
            return

        db = settings.DATABASES.get("default", {})
        engine = str(db.get("ENGINE", ""))
        if "postgresql" not in engine and "postgis" not in engine:
            return

        from game import api as game_api

        if game_api._bridge_instance is not None:
            return

        try:
            from game.engine_bridge import init_persistence

            persistence = init_persistence(db)
            game_api.init_bridge(persistence)
            logger.info("EngineBridge initialized via GameConfig.ready")
        except Exception:
            logger.exception("Failed to initialize EngineBridge")
