"""Integration test fixtures for Django web tests against real PostgreSQL.

Overrides ``django_db_setup`` to register an ephemeral PostGIS container as
the ``"postgres"`` database alias, leaving ``DATABASES["default"]`` (SQLite)
untouched. This prevents session-scoped pollution of the default alias from
leaking into unit tests that share the same pytest session.

Lifecycle:
1. Start PostGIS container via testcontainers
2. Register the container as ``DATABASES["postgres"]``
3. Run Django migrations against the ``postgres`` alias
4. Apply canonical DDL for unmanaged tables (game_session, etc.)
5. On session teardown: restore ``DATABASES`` to its pre-mutation state

Tests that exercise the Postgres backend must opt in via
``@pytest.mark.django_db(databases=["postgres"])`` and direct ORM calls to
the alias with ``Manager.using("postgres")``.
"""

from __future__ import annotations

import contextlib
import logging
import os
import uuid
from collections.abc import Generator
from typing import Any

import pytest

logger = logging.getLogger(__name__)

requires_postgres = pytest.mark.requires_postgres

POSTGRES_ALIAS = "postgres"


def postgres_available() -> bool:
    """Check if PostgreSQL connection details are configured."""
    return os.environ.get("POSTGRES_HOST", "") != ""


@pytest.fixture
def unique_session_id() -> uuid.UUID:
    """Generate a unique UUID for each test to avoid conflicts."""
    return uuid.uuid4()


# ─── Testcontainers lifecycle ─────────────────────────────────────


@pytest.fixture(scope="session")
def _pg_container() -> Generator[dict[str, Any], None, None]:
    """Start an ephemeral PostGIS container for the test session."""
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip("testcontainers[postgres] not installed")
        return

    container = PostgresContainer(
        image="postgis/postgis:16-3.4-alpine",
        username="test",
        password="test",  # noqa: S106
        dbname="babylon_test",
    )

    try:
        container.start()
    except Exception as exc:
        pytest.skip(f"Docker unavailable: {exc}")
        return

    params = {
        "host": container.get_container_host_ip(),
        "port": container.get_exposed_port(5432),
        "user": container.username,
        "password": container.password,
        "dbname": container.dbname,
    }
    logger.info(
        "Testcontainers PG at %s:%s/%s",
        params["host"],
        params["port"],
        params["dbname"],
    )

    yield params

    container.stop()
    logger.info("Testcontainers Postgres stopped")


@pytest.fixture(scope="session")
def _pg_django_configured(
    _pg_container: dict[str, Any],
) -> Generator[dict[str, Any], None, None]:
    """Register the testcontainers Postgres as the ``"postgres"`` DB alias.

    Adds a new entry to ``settings.DATABASES`` rather than overwriting
    ``"default"``. This keeps the SQLite default available for unit tests
    that run in the same pytest session and prevents the AUTOINCREMENT
    DDL pollution that would otherwise occur when those tests' setup
    fixture executes against a Postgres connection.

    On session teardown the original ``DATABASES`` mapping is restored
    and any cached ``DatabaseWrapper`` for the alias is closed and
    purged from Django's connection handler.
    """
    params = _pg_container

    from django.conf import settings
    from django.db import connections

    # Snapshot the original mapping so we can restore on teardown.
    original_aliases = set(settings.DATABASES.keys())
    had_alias_before = POSTGRES_ALIAS in original_aliases
    pre_existing_alias_config = (
        dict(settings.DATABASES[POSTGRES_ALIAS]) if had_alias_before else None
    )

    settings.DATABASES[POSTGRES_ALIAS] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": params["dbname"],
        "USER": params["user"],
        "PASSWORD": params["password"],
        "HOST": params["host"],
        "PORT": str(params["port"]),
        "OPTIONS": {},
        "AUTOCOMMIT": True,
        "ATOMIC_REQUESTS": False,
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": False,
        "TIME_ZONE": None,
        "TEST": {
            "NAME": params["dbname"],
            "CHARSET": None,
            "COLLATION": None,
            "MIGRATE": True,
            "MIRROR": None,
            # Break Django's implicit dependency on the "default" alias.
            # Without this, ``setup_databases`` raises ``ImproperlyConfigured:
            # Circular dependency in TEST[DEPENDENCIES]`` whenever a test only
            # requests the ``postgres`` alias — Django wants to set up
            # ``default`` first by default, but the test list excludes it.
            "DEPENDENCIES": [],
        },
    }

    # Invalidate Django's @cached_property so the new alias is observed.
    if "settings" in connections.__dict__:
        del connections.__dict__["settings"]
    connections._settings = settings.DATABASES

    yield params

    # ── Teardown: drop the alias and purge any cached wrapper ──
    try:
        connections[POSTGRES_ALIAS].close()
    except Exception:  # noqa: BLE001 — connection may already be closed
        logger.debug("Could not close %s connection cleanly", POSTGRES_ALIAS)

    local = connections._connections
    with contextlib.suppress(AttributeError):
        delattr(local, POSTGRES_ALIAS)

    if had_alias_before and pre_existing_alias_config is not None:
        settings.DATABASES[POSTGRES_ALIAS] = pre_existing_alias_config
    else:
        settings.DATABASES.pop(POSTGRES_ALIAS, None)

    if "settings" in connections.__dict__:
        del connections.__dict__["settings"]
    connections._settings = settings.DATABASES


# ─── pytest-django integration ────────────────────────────────────


@pytest.fixture(scope="session")
def django_db_setup(
    request: pytest.FixtureRequest,  # noqa: ARG001
    _pg_django_configured: dict[str, Any],
    django_test_environment: None,  # noqa: ARG001
    django_db_blocker: Any,
) -> Generator[None, None, None]:
    """Replace pytest-django's default DB setup.

    Order matters:
    1. Unblock DB blocker
    2. Run Django migrations (creates auth_user, etc.)
    3. Apply canonical DDL (creates unmanaged game tables)
    4. Yield to let tests run
    """
    import psycopg

    params = _pg_django_configured
    dsn = (
        f"host={params['host']} port={params['port']} "
        f"dbname={params['dbname']} user={params['user']} "
        f"password={params['password']}"
    )

    with django_db_blocker.unblock():
        # Phase 1: Canonical DDL for ALL tables (including game tables)
        # Must run FIRST because some tables have FK dependencies
        from babylon.persistence.postgres_schema import POSTGRES_SCHEMA_DDL

        with psycopg.connect(dsn, autocommit=True) as conn:
            for ddl in POSTGRES_SCHEMA_DDL:
                try:
                    conn.execute(ddl)
                except psycopg.errors.UndefinedObject as exc:
                    logger.warning("Skipping DDL (missing ext): %s", exc)
                except psycopg.errors.DuplicateTable:
                    pass
                except psycopg.errors.DuplicateObject:
                    pass
                except psycopg.errors.InFailedSqlTransaction:
                    pass
                except Exception:
                    logger.warning("DDL warning (non-fatal)", exc_info=True)

        # Phase 2: Run framework migrations on the postgres alias
        from django.core.management import call_command

        db_arg = f"--database={POSTGRES_ALIAS}"
        call_command("migrate", "contenttypes", db_arg, verbosity=0)
        call_command("migrate", "auth", db_arg, verbosity=0)
        call_command("migrate", "sessions", db_arg, verbosity=0)
        # Fake game migrations — DDL already created those tables
        call_command("migrate", "game", "--fake", db_arg, verbosity=0)
        # syncdb creates tables for apps without migrations (accounts)
        call_command("migrate", "--run-syncdb", db_arg, verbosity=0)

        yield


@pytest.fixture(scope="session")
def tc_pg_dsn(_pg_django_configured: dict[str, Any]) -> str:
    """Return a psycopg-compatible DSN for raw queries."""
    params = _pg_django_configured
    return (
        f"host={params['host']} port={params['port']} "
        f"dbname={params['dbname']} user={params['user']} "
        f"password={params['password']}"
    )
