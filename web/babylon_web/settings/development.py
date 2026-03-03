"""Development-specific settings.

DEBUG enabled, CORS open for Vite dev server, TCP postgres.
"""

from __future__ import annotations

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# CORS — allow Vite dev server
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "x-csrftoken",
    "x-request-id",
]

# Development: enable SQL query logging for debugging
LOGGING["loggers"]["django.db.backends"]["level"] = "DEBUG"  # type: ignore[index]  # noqa: F405
