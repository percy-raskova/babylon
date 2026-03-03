"""Production-specific settings.

DEBUG off, strict security headers, Unix socket postgres.
"""

from __future__ import annotations

import os

from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

# HTTPS / security
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Unix socket for Postgres (Cloudflare deployment)
DATABASES["default"]["HOST"] = os.environ.get(  # noqa: F405
    "POSTGRES_HOST",
    "/var/run/postgresql",
)
