"""Django database-alias construction for both DSN roles (spec-096, T1.2 keel).

The Observatory reads the headless simulation runner's Postgres through a
second, read-only Django database alias ("sim"). This module turns a DSN
into a Django ``DATABASES`` entry for either that alias or the ordinary
read/write "default" (product) alias.

DSN resolution for both roles now goes through the ONE config seam,
:mod:`babylon.config.dsn` — this file is allowlisted in
``tests/unit/web/test_import_boundary.py`` for that single, read-only,
config-only import (same precedent as ``babylon_web/health/views.py``'s
``babylon.config.llm_config`` exception): it never invokes engine
mechanics, only resolves connection strings.

See Also:
    :mod:`observatory.router`: refuses migrations for the "sim" alias.
    :mod:`tools.tick_probe`: the DSN shape reused here.
    :mod:`babylon.config.dsn`: precedence + legacy-name back-compat.
"""

from __future__ import annotations

from typing import Any

from psycopg.conninfo import conninfo_to_dict

from babylon.config.dsn import postgres_split_dsn, resolve_dsn

#: libpq command-line option that pins every connection read-only server-side.
SIM_READ_ONLY_OPTION = "-c default_transaction_read_only=on"

#: Default target — the canonical local simulation Postgres (spec-089 storage
#: stack). Overridable via ``BABYLON_DSN`` (canonical) or the deprecated
#: ``BABYLON_PG_DSN`` environment variable.
_DEFAULT_SIM_DSN = "host=localhost port=5433 dbname=babylon_test user=test password=test"


def default_sim_dsn() -> str:
    """Return the simulation DSN, honouring ``BABYLON_DSN``/``BABYLON_PG_DSN``.

    Returns:
        A libpq keyword DSN string (the ``tools/tick_probe.py`` default).
    """
    return resolve_dsn(legacy_env="BABYLON_PG_DSN", default=_DEFAULT_SIM_DSN)


def default_primary_dsn(*, host_default: str = "localhost") -> str:
    """Return the product ("default") DSN, honouring ``BABYLON_DSN`` then the
    deprecated Django ``POSTGRES_*`` split vars (see
    :func:`babylon.config.dsn.postgres_split_dsn`).

    ``host_default`` is a pure fallback — it only takes effect when
    *neither* ``BABYLON_DSN`` nor ``POSTGRES_HOST`` is set. It exists so a
    caller (``production.py``'s unix-socket deployment default) can change
    what "unconfigured" resolves to without ever clobbering a HOST the
    canonical or legacy env vars already resolved (T1.2 K2 review fix —
    previously ``production.py`` patched ``DATABASES["default"]["HOST"]``
    after the fact, unconditionally, defeating ``BABYLON_DSN``).

    Args:
        host_default: fallback host used only when neither ``BABYLON_DSN``
            nor ``POSTGRES_HOST`` is set. Defaults to ``"localhost"`` (the
            historical Django default, used by ``base.py``/``development.py``).

    Returns:
        A libpq keyword DSN string.
    """
    return resolve_dsn(default=postgres_split_dsn(host=host_default))


def _database_alias_from_dsn(dsn: str, *, engine: str) -> dict[str, Any]:
    """Parse a DSN into the connection keys Django's SQL backends require.

    Accepts both the libpq keyword form
    (``host=... port=... dbname=... user=... password=...``) and the URL form
    (``postgresql://user:pass@host:port/dbname``), including unix-socket
    forms; parsing is delegated to libpq via
    :func:`psycopg.conninfo.conninfo_to_dict`.

    Args:
        dsn: A Postgres connection string (keyword or URL form).
        engine: The Django ``ENGINE`` dotted path for this alias.

    Returns:
        The common subset of a Django database-alias configuration dict
        (``ENGINE``/``NAME``/``USER``/``PASSWORD``/``HOST``/``PORT``); role
        -specific keys (read-only options, ``TEST.MIRROR``, …) are layered
        on by the caller.
    """
    params = conninfo_to_dict(dsn)
    return {
        "ENGINE": engine,
        "NAME": params.get("dbname", ""),
        "USER": params.get("user", ""),
        "PASSWORD": params.get("password", ""),
        "HOST": params.get("host", ""),
        "PORT": str(params.get("port", "")),
    }


def build_sim_database_alias(dsn: str) -> dict[str, Any]:
    """Build a read-only Django ``DATABASES`` entry from a Postgres DSN.

    The plain ``postgresql`` backend is used (not PostGIS): the value-aggregate
    views and ``tick_commit`` return no geometry, so GIS is unnecessary.

    Args:
        dsn: A Postgres connection string (keyword or URL form).

    Returns:
        A Django database-alias configuration dict with the read-only
        connection option applied and ``TEST.MIRROR`` set so Django's test
        runner never tries to create/destroy this external database.
    """
    alias = _database_alias_from_dsn(dsn, engine="django.db.backends.postgresql")
    alias.update(
        {
            "OPTIONS": {"options": SIM_READ_ONLY_OPTION},
            "CONN_MAX_AGE": 0,
            "CONN_HEALTH_CHECKS": False,
            "ATOMIC_REQUESTS": False,
            "AUTOCOMMIT": True,
            "TIME_ZONE": None,
            # The sim DB is external and read-only — Django's test runner must
            # not attempt to create a test copy of it. MIRROR makes it defer
            # to the default alias during framework test-DB setup.
            "TEST": {"MIRROR": "default"},
        }
    )
    return alias


def build_primary_database_alias(dsn: str) -> dict[str, Any]:
    """Build the read/write Django ``default`` (product) alias from a DSN.

    Unlike :func:`build_sim_database_alias`, this is an ordinary read/write
    PostGIS connection — none of the sim alias's read-only/mirror settings
    apply; Django's own defaults hold for everything else.

    Args:
        dsn: A Postgres connection string (keyword or URL form).

    Returns:
        A Django database-alias configuration dict for the PostGIS backend.
    """
    return _database_alias_from_dsn(dsn, engine="django.contrib.gis.db.backends.postgis")


__all__ = [
    "SIM_READ_ONLY_OPTION",
    "build_primary_database_alias",
    "build_sim_database_alias",
    "default_primary_dsn",
    "default_sim_dsn",
]
