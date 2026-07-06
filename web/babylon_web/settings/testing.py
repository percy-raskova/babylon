"""Test-specific settings.

Uses SQLite in-memory for fast unit tests without PostGIS.
"""

from __future__ import annotations

from .base import *  # noqa: F401, F403

DEBUG = False

SECRET_KEY = "test-secret-key-not-for-production"  # noqa: S105

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

# spec-096: this config drops the read-only "sim" alias, so the Observatory
# has nothing to read — disable it so endpoints 404 (gated) instead of raising
# ConnectionDoesNotExist. Tests that exercise the Observatory opt in explicitly
# via the `settings` fixture / integration `sim_alias` fixture.
OBSERVATORY_ENABLED = False

# Faster password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
