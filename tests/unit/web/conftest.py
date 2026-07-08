"""Test configuration for Django web tests.

Uses SQLite in-memory for fast unit tests (default).
Postgres-backed integration tests live in ``tests/integration/web/``.

Unmanaged models (managed=False) are temporarily set to managed=True
so Django creates the tables in the test SQLite database.
Note: pytest-django configures Django via ``django_settings_module`` in
pyproject.toml before conftest loads. The fallback ``settings.configure()``
block only runs when pytest-django is not available.
"""

from __future__ import annotations

import django
import pytest
from django.conf import settings

# Fallback: configure Django if pytest-django hasn't already done so
if not settings.configured:
    settings.configure(
        **{
            "DEBUG": False,
            "SECRET_KEY": "test-secret-key-not-for-production",
            "DATABASES": {
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                },
            },
            "INSTALLED_APPS": [
                "django.contrib.admin",
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "django.contrib.sessions",
                "django.contrib.messages",
                "django.contrib.staticfiles",
                "rest_framework",
                "corsheaders",
                "game.apps.GameConfig",
                "accounts.apps.AccountsConfig",
            ],
            "ROOT_URLCONF": "babylon_web.urls",
            "MIDDLEWARE": [
                "django.middleware.security.SecurityMiddleware",
                "corsheaders.middleware.CorsMiddleware",
                "django.contrib.sessions.middleware.SessionMiddleware",
                "django.middleware.common.CommonMiddleware",
                "django.middleware.csrf.CsrfViewMiddleware",
                "django.contrib.auth.middleware.AuthenticationMiddleware",
                "django.contrib.messages.middleware.MessageMiddleware",
                "django.middleware.clickjacking.XFrameOptionsMiddleware",
            ],
            "TEMPLATES": [
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "DIRS": [],
                    "APP_DIRS": True,
                    "OPTIONS": {
                        "context_processors": [
                            "django.template.context_processors.debug",
                            "django.template.context_processors.request",
                            "django.contrib.auth.context_processors.auth",
                            "django.contrib.messages.context_processors.messages",
                        ],
                    },
                },
            ],
            "REST_FRAMEWORK": {
                "DEFAULT_AUTHENTICATION_CLASSES": [
                    "rest_framework.authentication.SessionAuthentication",
                ],
                "DEFAULT_PERMISSION_CLASSES": [
                    "rest_framework.permissions.IsAuthenticated",
                ],
                "DEFAULT_RENDERER_CLASSES": [
                    "rest_framework.renderers.JSONRenderer",
                ],
            },
            "DEFAULT_AUTO_FIELD": "django.db.models.BigAutoField",
            "PASSWORD_HASHERS": [
                "django.contrib.auth.hashers.MD5PasswordHasher",
            ],
        }
    )
    django.setup()

# Override managed=False models to managed=True for test DB creation.
# This runs regardless of how Django was configured (pytest-django or fallback).
from game.models import ActionResult, GameSession, HexState, PlayerAction

for _model in (GameSession, PlayerAction, ActionResult, HexState):
    _model._meta.managed = True  # type: ignore[misc]

_UNMANAGED_TABLE_SQL = [
    """CREATE TABLE IF NOT EXISTS game_session (
        id CHAR(32) PRIMARY KEY,
        player_id INTEGER,
        scenario VARCHAR(64) NOT NULL,
        current_tick INTEGER NOT NULL DEFAULT 0,
        status VARCHAR(16) NOT NULL DEFAULT 'active',
        config_json TEXT NOT NULL DEFAULT '{}',
        game_defines_json TEXT NOT NULL DEFAULT '{}',
        trace_level VARCHAR(8) NOT NULL DEFAULT 'NONE',
        rng_seed BIGINT NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS game_turn (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id CHAR(32) NOT NULL REFERENCES game_session(id),
        tick INTEGER NOT NULL,
        org_id VARCHAR(64) NOT NULL,
        verb VARCHAR(16) NOT NULL,
        action_type VARCHAR(32),
        target_id VARCHAR(64),
        target_community VARCHAR(32),
        params_json TEXT,
        submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        resolved BOOLEAN NOT NULL DEFAULT 0,
        UNIQUE(session_id, tick, org_id)
    )""",
    """CREATE TABLE IF NOT EXISTS action_result (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id CHAR(32) NOT NULL REFERENCES game_session(id),
        tick INTEGER NOT NULL,
        org_id VARCHAR(64) NOT NULL,
        action_type VARCHAR(32) NOT NULL,
        target_id VARCHAR(64),
        target_community VARCHAR(32),
        initiative_score REAL NOT NULL,
        action_cost REAL NOT NULL,
        success BOOLEAN NOT NULL,
        consciousness_delta REAL,
        heat_delta REAL,
        details TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS hex_latest (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id CHAR(32) NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
        tick INTEGER NOT NULL,
        h3_index VARCHAR(20) NOT NULL,
        county_fips VARCHAR(5) NOT NULL,
        county_name VARCHAR(100) NOT NULL,
        bea_ea_code VARCHAR(8),
        msa_code VARCHAR(10),
        state_fips VARCHAR(2) NOT NULL DEFAULT '26',
        center_lat REAL NOT NULL,
        center_lng REAL NOT NULL,
        profit_rate REAL,
        exploitation_rate REAL,
        occ REAL,
        imperial_rent REAL,
        g33_visibility REAL,
        pop_bourgeoisie INTEGER DEFAULT 0,
        pop_petit_bourgeoisie INTEGER DEFAULT 0,
        pop_labor_aristocracy INTEGER DEFAULT 0,
        pop_proletariat INTEGER DEFAULT 0,
        pop_lumpenproletariat INTEGER DEFAULT 0,
        pop_total INTEGER DEFAULT 0,
        dominant_class VARCHAR(24),
        faction_finance_capital REAL,
        faction_security_state REAL,
        faction_settler_populist REAL,
        heat REAL DEFAULT 0.0,
        heat_delta REAL DEFAULT 0.0,
        org_count INTEGER DEFAULT 0,
        actions_taken INTEGER DEFAULT 0,
        was_target BOOLEAN DEFAULT 0,
        terrain_type VARCHAR(16) DEFAULT 'LAND',
        water_coverage REAL DEFAULT 0.0,
        internet_access BOOLEAN DEFAULT 0,
        UNIQUE(game_id, h3_index)
    )""",
]


@pytest.fixture(autouse=True, scope="session")
def _create_unmanaged_tables(django_db_setup: None, django_db_blocker: object) -> None:  # type: ignore[type-arg, unused-ignore]
    """Create tables for unmanaged models (managed=False) in the test DB.

    Django migrations skip ``managed=False`` models, so we create them
    with raw SQL to match the schema in ``postgres_schema.py``.
    """
    from django.db import connection

    with django_db_blocker.unblock(), connection.cursor() as cursor:  # type: ignore[union-attr]
        for sql in _UNMANAGED_TABLE_SQL:
            cursor.execute(sql)
