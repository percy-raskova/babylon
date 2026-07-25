"""``_open_postgres_pool`` resolves its DSN through the T1.2 config seam.

Precedence + legacy-name fallback are pinned exhaustively in
``tests/unit/config/test_dsn.py`` against ``babylon.config.dsn.resolve_dsn``
directly; these tests pin the runner's *specific* legacy names
(``BABYLON_PG_DSN`` then ``BABYLON_TEST_PG_DSN``) and its missing-DSN error.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.engine.headless_runner import runner as runner_mod


def _clear_dsn_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("BABYLON_DSN", "BABYLON_PG_DSN", "BABYLON_TEST_PG_DSN"):
        monkeypatch.delenv(name, raising=False)


class _FakePool:
    def __init__(self, dsn: str, **kwargs: Any) -> None:
        self.dsn = dsn
        self.kwargs = kwargs


def test_raises_when_no_dsn_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_dsn_env(monkeypatch)
    with pytest.raises(runner_mod.PostgresUnreachableError, match="BABYLON_DSN"):
        runner_mod._open_postgres_pool()


def test_uses_babylon_pg_dsn_over_babylon_test_pg_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_dsn_env(monkeypatch)
    monkeypatch.setenv("BABYLON_PG_DSN", "host=runner-primary")
    monkeypatch.setenv("BABYLON_TEST_PG_DSN", "host=runner-fallback")
    monkeypatch.setattr("psycopg_pool.ConnectionPool", _FakePool)

    pool = runner_mod._open_postgres_pool()
    assert pool.dsn == "host=runner-primary"


def test_falls_back_to_babylon_test_pg_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_dsn_env(monkeypatch)
    monkeypatch.setenv("BABYLON_TEST_PG_DSN", "host=runner-fallback")
    monkeypatch.setattr("psycopg_pool.ConnectionPool", _FakePool)

    pool = runner_mod._open_postgres_pool()
    assert pool.dsn == "host=runner-fallback"


def test_canonical_babylon_dsn_wins_over_legacy_names(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_dsn_env(monkeypatch)
    monkeypatch.setenv("BABYLON_DSN", "host=canonical")
    monkeypatch.setenv("BABYLON_PG_DSN", "host=runner-primary")
    monkeypatch.setattr("psycopg_pool.ConnectionPool", _FakePool)

    pool = runner_mod._open_postgres_pool()
    assert pool.dsn == "host=canonical"
