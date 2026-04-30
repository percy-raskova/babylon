"""Integration test fixtures for Django web tests against real PostgreSQL.

Overrides ``django_db_setup`` to use an ephemeral PostGIS container.

Lifecycle:
1. Start PostGIS container via testcontainers
2. Reconfigure Django DATABASES to point at the container
3. Run Django migrations (creates auth_user, contenttypes, etc.)
4. Apply canonical DDL for unmanaged tables (game_session, etc.)
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
def _pg_django_configured(_pg_container: dict[str, Any]) -> dict[str, Any]:
    """Reconfigure Django DATABASES to point at the testcontainers Postgres.

    This modifies settings and resets the connection handler so that
    all subsequent Django database access uses Postgres.
    """
    params = _pg_container

    from django.conf import settings

    settings.DATABASES["default"] = {
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
        },
    }

    # Force Django's ConnectionHandler to forget all cached state.
    #
    # Django's ConnectionHandler.settings is a @cached_property:
    # once read during django.setup(), it caches the SQLite config.
    # The _connections attribute uses asgiref.Local, which stores
    # attributes in _storage (not directly on the object).
    from django.db import connections

    connections.close_all()

    # 1. Invalidate the @cached_property so settings are re-read
    if "settings" in connections.__dict__:
        del connections.__dict__["settings"]

    # 2. Reset the internal _settings to point at new DATABASES
    connections._settings = settings.DATABASES

    # 3. Delete cached DatabaseWrapper objects from asgiref.Local.
    #    vars() on asgiref.Local returns internal fields, not stored
    #    attributes — must delete known aliases explicitly.
    local = connections._connections
    for alias in settings.DATABASES:
        with contextlib.suppress(AttributeError):
            delattr(local, alias)

    return params


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

        # Phase 2: Run framework migrations, fake game migrations
        from django.core.management import call_command

        call_command("migrate", "contenttypes", verbosity=0)
        call_command("migrate", "auth", verbosity=0)
        call_command("migrate", "sessions", verbosity=0)
        # Fake game migrations — DDL already created those tables
        call_command("migrate", "game", "--fake", verbosity=0)
        # syncdb creates tables for apps without migrations (accounts)
        call_command("migrate", "--run-syncdb", verbosity=0)

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
