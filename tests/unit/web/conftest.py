"""Test configuration for Django web tests.

Uses SQLite in-memory for fast unit tests.
Integration tests in tests/integration/web/ use PostgreSQL.

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
    if _model.__name__ == "HexState":
        _model._meta.db_table = "sim_hex_states"

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
    """CREATE TABLE IF NOT EXISTS sim_hex_states (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id CHAR(32) NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
        tick INTEGER NOT NULL,
        h3_index VARCHAR(20) NOT NULL,
        county_fips VARCHAR(5) NOT NULL,
        county_name VARCHAR(50) NOT NULL,
        profit_rate REAL,
        exploitation_rate REAL,
        occ REAL,
        imperial_rent REAL,
        heat REAL,
        org_presence INTEGER DEFAULT 0,
        dominant_class VARCHAR(30),
        population INTEGER,
        UNIQUE(game_id, tick, h3_index)
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
