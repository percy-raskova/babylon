"""Game app configuration."""

from __future__ import annotations

import contextlib
import datetime as _dt
import logging
import os
import sys
import time

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class GameConfig(AppConfig):
    """Django app for game API and engine bridge.

    Spec 061 FR-006 / FR-007 (Real Backend Wire-Up): boot must surface
    engine-init failures loudly. Three in-process retries with
    exponential backoff handle transient DB unavailability; on
    persistent failure, the worker exits non-zero so that systemd's
    own restart loop can take over (research.md R3 + R4).
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "game"

    # Class-level flag prevents the multi-call ready() footgun in test
    # contexts (per Django 5.2 docs: "in some corner cases — particularly
    # in tests — ready() might be called more than once, so write
    # idempotent methods or use a flag").
    _initialized: bool = False

    # Diagnostic state surfaced by /health/detail/ (spec 061 FR-009).
    last_boot_attempts: int = 0
    boot_succeeded_at: _dt.datetime | None = None

    def ready(self) -> None:
        """Initialize EngineBridge for PostgreSQL-backed runtime.

        Skips initialization for SQLite-based test settings.
        All engine/persistence imports are delegated to ``engine_bridge.py``
        to preserve the import boundary (FR-008).
        """
        if GameConfig._initialized:
            return

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
            GameConfig._initialized = True
            return

        self._initialize_engine_with_retry()

    def _initialize_engine_with_retry(self, max_attempts: int = 3) -> None:
        """Try to initialize the engine bridge up to ``max_attempts`` times.

        On exhaustion, log loudly and call ``sys.exit(1)`` so the worker
        process terminates non-zero. systemd then handles the
        longer-timescale restart loop with exponential backoff per
        research.md R3.

        Per FR-007 (clarified): hybrid retry-then-exit. Three in-process
        retries (1s, 2s) handle transient DB blips cheaply; persistent
        outages are escalated to the supervisor.
        """
        from game import api as game_api
        from game.engine_bridge import init_persistence

        db = settings.DATABASES.get("default", {})
        for attempt in range(1, max_attempts + 1):
            try:
                persistence = init_persistence(db)
                game_api.init_bridge(persistence)
                GameConfig._initialized = True
                GameConfig.last_boot_attempts = attempt
                GameConfig.boot_succeeded_at = _dt.datetime.now(_dt.UTC)
                logger.info(
                    "EngineBridge initialized via GameConfig.ready (attempt %d/%d)",
                    attempt,
                    max_attempts,
                )
                return
            except Exception:
                logger.exception(
                    "EngineBridge init failed (attempt %d/%d); backing off",
                    attempt,
                    max_attempts,
                )
                if attempt == max_attempts:
                    GameConfig.last_boot_attempts = attempt
                    logger.error("Worker exiting with status 1 — engine init exhausted retries")
                    sys.exit(1)
                time.sleep(2 ** (attempt - 1))

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
                    snapshot_json TEXT NOT NULL DEFAULT '{}',
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
            # Ensure snapshot_json column exists on pre-existing tables
            with contextlib.suppress(Exception):
                cursor.execute(
                    "ALTER TABLE game_session ADD COLUMN snapshot_json TEXT NOT NULL DEFAULT '{}'"
                )
        logger.info("Stub tables created (game_session, game_turn, action_result)")
