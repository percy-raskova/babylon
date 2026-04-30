"""Test-specific settings for Postgres-backed tests via testcontainers.

Inherits from base, then overrides DATABASES at runtime when the
testcontainers fixture injects the ephemeral Postgres DSN.

The initial DATABASES config here is a placeholder — the actual
connection parameters are injected by the ``postgres_db`` fixture
in ``tests/unit/web/conftest.py`` before Django creates the test DB.
"""

from __future__ import annotations

from .base import *  # noqa: F401, F403

DEBUG = False

SECRET_KEY = "test-secret-key-not-for-production"  # noqa: S105

# Placeholder — overridden at runtime by conftest.py when
# testcontainers spins up the ephemeral Postgres instance.
# This default allows Django to start and run non-DB tests
# even if the container hasn't been created yet.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "test",
        "USER": "test",
        "PASSWORD": "test",
        "HOST": "localhost",
        "PORT": "5432",
    },
}

# Faster password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
