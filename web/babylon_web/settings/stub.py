"""Stub development settings — SQLite + StubEngineBridge.

Runs the Django server without PostgreSQL or the Babylon engine.
All API endpoints return correctly-shaped mock data.

Usage::

    DJANGO_SETTINGS_MODULE=babylon_web.settings.stub python manage.py runserver
"""

from __future__ import annotations

from pathlib import Path

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "testserver"]  # noqa: S104

# Override database to SQLite (no Postgres dependency)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(Path(BASE_DIR) / "db.sqlite3"),  # noqa: F405
    },
}

# CORS — allow Vite dev server
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "x-csrftoken",
    "x-request-id",
]

# Silence SQL debug logging in stub mode
LOGGING["loggers"]["django.db.backends"]["level"] = "WARNING"  # type: ignore[index]  # noqa: F405

# Signal to game app that it should create unmanaged tables at startup
# (GameSession, PlayerAction, ActionResult are managed=False in production
# because they're created by the Postgres runtime DDL)
STUB_CREATE_TABLES = True

# spec-096: the stub config has no read-only "sim" alias, so the Observatory
# has nothing to read — keep it off so its endpoints 404 rather than raise
# ConnectionDoesNotExist.
OBSERVATORY_ENABLED = False

# Spec 061 US7 (T111): BABYLON_MOCK_MODE removed.
# StubEngineBridge remains for SQLite-only dev/test configurations
# (see web.game.api._get_bridge fallback path).
