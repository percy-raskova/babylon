"""Single Postgres DSN-resolution seam (T1.2 keel; ADR099 deployment guardrail).

Three independent naming schemes for "which Postgres do I talk to" had
accumulated across the codebase before this module existed:

- the headless runner's ``BABYLON_PG_DSN`` (libpq keyword string, falling
  back to ``BABYLON_TEST_PG_DSN``; :func:`babylon.engine.headless_runner.
  runner._open_postgres_pool`);
- Django's split ``POSTGRES_HOST``/``POSTGRES_PORT``/``POSTGRES_DB``/
  ``POSTGRES_USER``/``POSTGRES_PASSWORD`` vars
  (``web/babylon_web/settings/base.py``'s ``DATABASES["default"]``);
- ``babylon doctor``'s ``BABYLON_DATABASE_URL`` (``babylon.cli.doctor``).

This module is the ONE place that resolves a DSN from the environment.
Every call site above (plus ``web/observatory/db.py``'s read-only "sim"
alias, which already shared the runner's ``BABYLON_PG_DSN`` scheme) now
calls :func:`resolve_dsn` instead of reading ``os.environ`` directly.

Precedence (highest wins)
-------------------------
1. ``BABYLON_DSN`` — the new canonical env var. Sets every call site's DSN
   in one place; accepts both libpq keyword form
   (``host=... port=... dbname=... user=... password=...``) and URL form
   (``postgresql://user:pass@host:port/dbname``), including unix-socket
   forms (``host=/var/run/postgresql``, or the URL-encoded socket-path
   variant) — ADR099's local-first guardrail requires every connection
   path to work over a unix socket with no hardcoded ``localhost:5433``.
2. The caller's own legacy env var name(s), passed as ``legacy_env``, in
   the order given. **DEPRECATED** — kept for back-compat only:
   ``BABYLON_PG_DSN`` / ``BABYLON_TEST_PG_DSN`` (runner + sim alias),
   ``BABYLON_DATABASE_URL`` (doctor), and the Django ``POSTGRES_*`` split
   vars (assembled by :func:`postgres_split_dsn`, itself deprecated).
3. ``default`` — the caller-supplied fallback DSN (each call site keeps
   its own historical default; this module does not invent a shared one).

``resolve_dsn`` never parses or validates the returned string — it is a
raw DSN, handed to ``psycopg.connect``/``psycopg_pool.ConnectionPool``
(both accept keyword or URL form) or, for Django, to
``psycopg.conninfo.conninfo_to_dict`` (see ``web/observatory/db.py``).
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from typing import overload

from psycopg.conninfo import make_conninfo

#: The new canonical env var (T1.2 keel). Every call site checks this
#: first, ahead of any legacy scheme it historically used.
CANONICAL_DSN_ENV_VAR = "BABYLON_DSN"

#: Historical field-level defaults for the Django ``POSTGRES_*`` split-var
#: scheme (``web/babylon_web/settings/base.py``'s original hardcoded
#: values) — preserved here so :func:`postgres_split_dsn` reproduces the
#: exact prior behavior when none of the five vars is set.
_POSTGRES_SPLIT_DEFAULTS: Mapping[str, str] = {
    "host": "localhost",
    "port": "5432",
    "dbname": "babylon",
    "user": "babylon",
    "password": "babylon",
}

#: Maps a libpq keyword to the legacy Django env var that overrides it.
_POSTGRES_SPLIT_ENV_VARS: Mapping[str, str] = {
    "host": "POSTGRES_HOST",
    "port": "POSTGRES_PORT",
    "dbname": "POSTGRES_DB",
    "user": "POSTGRES_USER",
    "password": "POSTGRES_PASSWORD",
}


@overload
def resolve_dsn(
    *,
    legacy_env: str | Sequence[str] = ...,
    default: str,
    env: Mapping[str, str] | None = ...,
) -> str: ...


@overload
def resolve_dsn(
    *,
    legacy_env: str | Sequence[str] = ...,
    default: None = ...,
    env: Mapping[str, str] | None = ...,
) -> str | None: ...


def resolve_dsn(
    *,
    legacy_env: str | Sequence[str] = (),
    default: str | None = None,
    env: Mapping[str, str] | None = None,
) -> str | None:
    """Resolve a Postgres DSN via the ONE documented precedence chain.

    :param legacy_env: a single legacy env var name, or an ordered sequence
        of names, checked in order after the canonical var and before
        ``default``. Pass the caller's historical env var(s) — e.g. the
        runner passes ``("BABYLON_PG_DSN", "BABYLON_TEST_PG_DSN")``.
    :param default: the fallback DSN to use if neither the canonical var
        nor any ``legacy_env`` name is set (and not empty). ``None`` (the
        default) means "unconfigured" is a legal outcome the caller must
        handle — the runner and doctor both do.
    :param env: the environment mapping to read; defaults to
        ``os.environ``. Overridable for tests.
    :returns: the resolved DSN string, or ``default`` (possibly ``None``)
        if nothing in the environment is set. An env var present but set
        to the empty string is treated as unset, matching
        ``os.environ.get(name) or fallback`` idioms already in use at the
        call sites this replaces.
    """
    active_env = os.environ if env is None else env

    canonical = active_env.get(CANONICAL_DSN_ENV_VAR)
    if canonical:
        return canonical

    names = (legacy_env,) if isinstance(legacy_env, str) else tuple(legacy_env)
    for name in names:
        value = active_env.get(name)
        if value:
            return value

    return default


def postgres_split_dsn(
    env: Mapping[str, str] | None = None,
    *,
    host: str = _POSTGRES_SPLIT_DEFAULTS["host"],
    port: str = _POSTGRES_SPLIT_DEFAULTS["port"],
    dbname: str = _POSTGRES_SPLIT_DEFAULTS["dbname"],
    user: str = _POSTGRES_SPLIT_DEFAULTS["user"],
    password: str = _POSTGRES_SPLIT_DEFAULTS["password"],
) -> str:
    """Assemble a libpq DSN from the legacy Django ``POSTGRES_*`` split vars.

    **DEPRECATED** scheme — prefer setting ``BABYLON_DSN`` directly. This
    function exists only so :func:`resolve_dsn`'s ``default`` parameter can
    reproduce ``web/babylon_web/settings/base.py``'s historical behavior:
    each of the five fields falls back *independently* to its own default
    (``localhost``/``5432``/``babylon``/``babylon``/``babylon``) when its
    specific ``POSTGRES_*`` var is unset — unlike :func:`resolve_dsn`'s own
    all-or-nothing legacy tiers.

    ``host`` (hence ``POSTGRES_HOST``) may be a unix-socket directory
    (e.g. ``/var/run/postgresql``, the ADR099 local-first deployment form)
    — libpq's conninfo string treats a ``host`` value starting with ``/``
    as a socket directory, no special-casing needed here.

    :param env: the environment mapping to read; defaults to
        ``os.environ``.
    :param host: default host if ``POSTGRES_HOST`` is unset.
    :param port: default port if ``POSTGRES_PORT`` is unset.
    :param dbname: default database name if ``POSTGRES_DB`` is unset.
    :param user: default user if ``POSTGRES_USER`` is unset.
    :param password: default password if ``POSTGRES_PASSWORD`` is unset.
    :returns: a libpq keyword DSN string.
    """
    active_env = os.environ if env is None else env
    defaults = {
        "host": host,
        "port": port,
        "dbname": dbname,
        "user": user,
        "password": password,
    }
    values = {
        field: active_env.get(_POSTGRES_SPLIT_ENV_VARS[field], defaults[field])
        for field in defaults
    }
    return make_conninfo(
        host=values["host"],
        port=str(values["port"]),
        dbname=values["dbname"],
        user=values["user"],
        password=values["password"],
    )


__all__ = [
    "CANONICAL_DSN_ENV_VAR",
    "postgres_split_dsn",
    "resolve_dsn",
]
