"""Regression tests for game app startup initialization.

These tests ensure ``GameConfig.ready()`` initializes the EngineBridge for
PostgreSQL-backed environments and skips initialization for non-Postgres test
settings.
"""

from __future__ import annotations

import importlib
import sys
import types

import pytest
from django.conf import settings

from game.apps import GameConfig


@pytest.mark.unit
def test_ready_skips_for_non_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    """Do not initialize the bridge when DB engine is not PostgreSQL/PostGIS."""
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(
        settings,
        "DATABASES",
        {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
    )

    from game import api as game_api

    monkeypatch.setattr(game_api, "_bridge_instance", None)
    called: dict[str, bool] = {"init": False}

    def _spy_init_bridge(_persistence: object) -> None:
        called["init"] = True

    monkeypatch.setattr(game_api, "init_bridge", _spy_init_bridge)

    app_module = importlib.import_module("game")
    config = GameConfig("game", app_module)
    config.ready()

    assert called["init"] is False


@pytest.mark.unit
def test_ready_initializes_bridge_for_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    """Initialize bridge for PostgreSQL engine and call init_schema safely."""
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(
        settings,
        "DATABASES",
        {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "HOST": "localhost",
                "PORT": "5432",
                "NAME": "babylon",
                "USER": "babylon",
                "PASSWORD": "babylon",
            }
        },
    )

    fake_psycopg_pool = types.ModuleType("psycopg_pool")
    fake_runtime_module = types.ModuleType("babylon.persistence.postgres_runtime")

    class FakeConnectionPool:
        """Minimal pool stub matching constructor contract."""

        def __init__(
            self,
            *,
            conninfo: str,
            min_size: int,
            max_size: int,
            timeout: int,
        ) -> None:
            self.conninfo = conninfo
            self.min_size = min_size
            self.max_size = max_size
            self.timeout = timeout

    class FakePostgresRuntime:
        """Runtime stub exposing init_schema hook used at startup."""

        def __init__(self, pool: FakeConnectionPool) -> None:
            self.pool = pool
            self.schema_initialized = False

        def init_schema(self) -> None:
            self.schema_initialized = True

    fake_psycopg_pool.ConnectionPool = FakeConnectionPool
    fake_runtime_module.PostgresRuntime = FakePostgresRuntime

    monkeypatch.setitem(sys.modules, "psycopg_pool", fake_psycopg_pool)
    monkeypatch.setitem(
        sys.modules,
        "babylon.persistence.postgres_runtime",
        fake_runtime_module,
    )

    from game import api as game_api

    monkeypatch.setattr(game_api, "_bridge_instance", None)
    captured: dict[str, object] = {}

    def _spy_init_bridge(persistence: object) -> None:
        captured["persistence"] = persistence

    monkeypatch.setattr(game_api, "init_bridge", _spy_init_bridge)

    app_module = importlib.import_module("game")
    config = GameConfig("game", app_module)
    config.ready()

    assert "persistence" in captured
    persistence = captured["persistence"]
    assert isinstance(persistence, FakePostgresRuntime)
    assert persistence.schema_initialized is True
    assert "dbname=babylon" in persistence.pool.conninfo


@pytest.mark.unit
def test_ready_noop_when_bridge_already_initialized(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip startup initialization if bridge singleton already exists."""
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(
        settings,
        "DATABASES",
        {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
            }
        },
    )

    from game import api as game_api

    monkeypatch.setattr(game_api, "_bridge_instance", object())
    called: dict[str, bool] = {"init": False}

    def _spy_init_bridge(_persistence: object) -> None:
        called["init"] = True

    monkeypatch.setattr(game_api, "init_bridge", _spy_init_bridge)

    app_module = importlib.import_module("game")
    config = GameConfig("game", app_module)
    config.ready()

    assert called["init"] is False


@pytest.mark.unit
def test_ready_continues_when_schema_init_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bridge init should proceed even if schema bootstrap raises."""
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(
        settings,
        "DATABASES",
        {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "HOST": "localhost",
                "PORT": "5432",
                "NAME": "babylon",
                "USER": "babylon",
                "PASSWORD": "babylon",
            }
        },
    )

    fake_psycopg_pool = types.ModuleType("psycopg_pool")
    fake_runtime_module = types.ModuleType("babylon.persistence.postgres_runtime")

    class FakeConnectionPool:
        def __init__(
            self,
            *,
            conninfo: str,
            min_size: int,
            max_size: int,
            timeout: int,
        ) -> None:
            self.conninfo = conninfo
            self.min_size = min_size
            self.max_size = max_size
            self.timeout = timeout

    class FakePostgresRuntime:
        def __init__(self, pool: FakeConnectionPool) -> None:
            self.pool = pool

        def init_schema(self) -> None:
            raise RuntimeError("partitioned tables cannot be unlogged")

    fake_psycopg_pool.ConnectionPool = FakeConnectionPool
    fake_runtime_module.PostgresRuntime = FakePostgresRuntime

    monkeypatch.setitem(sys.modules, "psycopg_pool", fake_psycopg_pool)
    monkeypatch.setitem(
        sys.modules,
        "babylon.persistence.postgres_runtime",
        fake_runtime_module,
    )

    from game import api as game_api

    monkeypatch.setattr(game_api, "_bridge_instance", None)
    called: dict[str, bool] = {"init": False}

    def _spy_init_bridge(_persistence: object) -> None:
        called["init"] = True

    monkeypatch.setattr(game_api, "init_bridge", _spy_init_bridge)

    app_module = importlib.import_module("game")
    config = GameConfig("game", app_module)
    config.ready()

    assert called["init"] is True
