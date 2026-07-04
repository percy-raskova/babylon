"""Production-specific settings.

DEBUG off, strict security headers, Unix socket postgres.
"""

from __future__ import annotations

import os

from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

# spec-096: the Observatory exposes internal simulation data — OFF in production
# so end users never reach the debug dashboard.
OBSERVATORY_ENABLED = False

# HTTPS / security
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Cloudflare terminates TLS — Django sees HTTP internally.
# Without this, CSRF middleware rejects all POSTs as insecure.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CSRF_TRUSTED_ORIGINS = [
    f"https://{host.strip()}"
    for host in os.environ.get("ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

# Unix socket for Postgres (Cloudflare deployment)
DATABASES["default"]["HOST"] = os.environ.get(  # noqa: F405
    "POSTGRES_HOST",
    "/var/run/postgresql",
)
