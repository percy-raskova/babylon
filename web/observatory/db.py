"""Read-only ``sim`` database alias construction (spec-096).

The Observatory reads the headless simulation runner's Postgres through a
second Django database alias. This module turns the libpq DSN used by
``tools/tick_probe.py`` (``BABYLON_PG_DSN``) into a Django ``DATABASES`` entry
that is **read-only at the server level** — every connection opens with
``default_transaction_read_only=on``, so any write raises
``psycopg.errors.ReadOnlySqlTransaction``.

See Also:
    :mod:`observatory.router`: refuses migrations for this alias.
    :mod:`tools.tick_probe`: the DSN shape reused here.
"""

from __future__ import annotations

import os
from typing import Any

from psycopg.conninfo import conninfo_to_dict

#: libpq command-line option that pins every connection read-only server-side.
SIM_READ_ONLY_OPTION = "-c default_transaction_read_only=on"

#: Default target — the canonical local simulation Postgres (spec-089 storage
#: stack). Overridable via the ``BABYLON_PG_DSN`` environment variable.
_DEFAULT_SIM_DSN = "host=localhost port=5433 dbname=babylon_test user=test password=test"


def default_sim_dsn() -> str:
    """Return the simulation DSN, honouring ``BABYLON_PG_DSN`` if set.

    Returns:
        A libpq keyword DSN string (the ``tools/tick_probe.py`` default).
    """
    return os.environ.get("BABYLON_PG_DSN", _DEFAULT_SIM_DSN)


def build_sim_database_alias(dsn: str) -> dict[str, Any]:
    """Build a read-only Django ``DATABASES`` entry from a Postgres DSN.

    Accepts both the libpq keyword form
    (``host=... port=... dbname=... user=... password=...``) and the URL form
    (``postgresql://user:pass@host:port/dbname``); parsing is delegated to
    libpq via :func:`psycopg.conninfo.conninfo_to_dict`.

    The plain ``postgresql`` backend is used (not PostGIS): the value-aggregate
    views and ``tick_commit`` return no geometry, so GIS is unnecessary.

    Args:
        dsn: A Postgres connection string (keyword or URL form).

    Returns:
        A Django database-alias configuration dict with the read-only
        connection option applied and ``TEST.MIRROR`` set so Django's test
        runner never tries to create/destroy this external database.
    """
    params = conninfo_to_dict(dsn)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": params.get("dbname", ""),
        "USER": params.get("user", ""),
        "PASSWORD": params.get("password", ""),
        "HOST": params.get("host", ""),
        "PORT": str(params.get("port", "")),
        "OPTIONS": {"options": SIM_READ_ONLY_OPTION},
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": False,
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "TIME_ZONE": None,
        # The sim DB is external and read-only — Django's test runner must not
        # attempt to create a test copy of it. MIRROR makes it defer to the
        # default alias during framework test-DB setup.
        "TEST": {"MIRROR": "default"},
    }


__all__ = ["SIM_READ_ONLY_OPTION", "build_sim_database_alias", "default_sim_dsn"]
