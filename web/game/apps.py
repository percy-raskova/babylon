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
        # In stub mode, create tables that are normally unmanaged
        # (created by Postgres runtime DDL, not Django migrations)
        if getattr(settings, "STUB_CREATE_TABLES", False):
            self._create_stub_tables()

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

    def _create_stub_tables(self) -> None:
        """Create tables for unmanaged models (stub/dev mode only)."""
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS game_session (
                    id TEXT PRIMARY KEY,
                    player_id INTEGER,
                    scenario TEXT NOT NULL DEFAULT 'wayne_county',
                    current_tick INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active',
                    config_json TEXT NOT NULL DEFAULT '{}',
                    game_defines_json TEXT NOT NULL DEFAULT '{}',
                    trace_level TEXT NOT NULL DEFAULT 'NONE',
                    rng_seed INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS game_turn (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT REFERENCES game_session(id),
                    tick INTEGER NOT NULL DEFAULT 0,
                    org_id TEXT NOT NULL,
                    verb TEXT NOT NULL,
                    action_type TEXT,
                    target_id TEXT,
                    target_community TEXT,
                    params_json TEXT,
                    submitted_at TEXT NOT NULL DEFAULT (datetime('now')),
                    resolved INTEGER NOT NULL DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_result (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT REFERENCES game_session(id),
                    tick INTEGER NOT NULL DEFAULT 0,
                    org_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    target_id TEXT,
                    target_community TEXT,
                    initiative_score REAL NOT NULL DEFAULT 0,
                    action_cost REAL NOT NULL DEFAULT 0,
                    success INTEGER NOT NULL DEFAULT 0,
                    consciousness_delta REAL,
                    heat_delta REAL,
                    details TEXT
                )
            """)
        logger.info("Stub tables created (game_session, game_turn, action_result)")
