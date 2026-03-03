"""Game app configuration."""

from __future__ import annotations

import logging
import os

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)

_pool = None


class GameConfig(AppConfig):
    """Django app for game API and engine bridge."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "game"

    def ready(self) -> None:
        """Initialize EngineBridge for PostgreSQL-backed runtime.

        Skips initialization for SQLite-based test settings.
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
            from psycopg_pool import ConnectionPool

            from babylon.persistence.postgres_runtime import PostgresRuntime
        except Exception:
            logger.exception("Failed to import persistence dependencies for EngineBridge init")
            return

        host = str(db.get("HOST", "localhost"))
        port = str(db.get("PORT", "5432"))
        name = str(db.get("NAME", "babylon"))
        user = str(db.get("USER", "babylon"))
        password = str(db.get("PASSWORD", "babylon"))
        conninfo = f"host={host} port={port} dbname={name} user={user} password={password}"

        try:
            global _pool
            _pool = ConnectionPool(conninfo=conninfo, min_size=1, max_size=4, timeout=10)
            persistence = PostgresRuntime(_pool)
            try:
                persistence.init_schema()
            except Exception as exc:
                logger.warning("PostgreSQL schema init had non-fatal error: %s", exc)
            game_api.init_bridge(persistence)
            logger.info("EngineBridge initialized via GameConfig.ready")
        except Exception:
            logger.exception("Failed to initialize EngineBridge")
