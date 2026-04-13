"""Shared fixtures for game tests.

Creates unmanaged tables (managed=False models) since Django's test runner
doesn't create them automatically.
"""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]
from django.db import connection


@pytest.fixture(autouse=True)  # type: ignore[untyped-decorator]
def _create_unmanaged_tables() -> None:
    """Create tables for unmanaged models before each test class."""
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
