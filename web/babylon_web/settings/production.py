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

# Unix socket for Postgres (Cloudflare deployment). Recomputed via the same
# DSN seam base.py used (rather than patching HOST after the fact) so a HOST
# BABYLON_DSN already resolved is never clobbered — T1.2 K2 review fix: the
# old `DATABASES["default"]["HOST"] = os.environ.get("POSTGRES_HOST", ...)`
# unconditionally overwrote HOST even when BABYLON_DSN was the only override
# set, yielding a Frankenstein config (NAME/USER/PASSWORD/PORT from
# BABYLON_DSN, HOST from the hardcoded socket). `POSTGRES_HOST` still wins
# when explicitly set; only the "nothing configured" fallback changes, from
# base.py's "localhost" to the unix socket.
DATABASES["default"] = build_primary_database_alias(  # noqa: F405
    default_primary_dsn(host_default="/var/run/postgresql")  # noqa: F405
)
