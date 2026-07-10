"""Development-specific settings.

DEBUG enabled, CORS open for Vite dev servers, TCP postgres.
"""

from __future__ import annotations

import os

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# spec-096: the Observatory debug dashboard is a development tool — ON here.
OBSERVATORY_ENABLED = True

# CORS/CSRF — the cockpit is THE frontend on 5173 since the spec-112
# cutover. A missing origin makes Django 403 EVERY browser POST
# (login/create/submit/resolve) — found live by the B6 parity gate.
# BABYLON_EXTRA_DEV_ORIGINS (comma-separated) extends the list without
# repeating this class of defect for future ports.
_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
_DEV_ORIGINS += [
    origin.strip()
    for origin in os.environ.get("BABYLON_EXTRA_DEV_ORIGINS", "").split(",")
    if origin.strip()
]
CORS_ALLOWED_ORIGINS = list(_DEV_ORIGINS)
CSRF_TRUSTED_ORIGINS = list(_DEV_ORIGINS)
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
