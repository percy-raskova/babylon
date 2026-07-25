"""DSN-seam regression for ``tools/vault_regression.py`` (T1.2 K2 review fix).

``_pg_reachable()`` (and ``_bake_detroit_tri_county``'s ``setdefault``)
previously read ``BABYLON_TEST_PG_DSN``/``_DSN_DEFAULT`` directly, bypassing
the canonical ``BABYLON_DSN`` seam (:mod:`babylon.config.dsn`) that the
runner leg they gate (``runner_run``, via
:mod:`babylon.engine.headless_runner.runner`) actually resolves through —
so the reachability gate could report the target unreachable, or probe a
different Postgres than the bake would actually use. Both call sites now
share one helper, ``_resolve_detroit_pg_dsn()``, mirroring the runner's own
precedence exactly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TOOLS_DIR = _REPO_ROOT / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import vault_regression  # type: ignore[import-not-found]  # noqa: E402

pytestmark = pytest.mark.unit

_ENV_NAMES = ("BABYLON_DSN", "BABYLON_PG_DSN", "BABYLON_TEST_PG_DSN")


class TestResolveDetroitPgDsn:
    def test_default_when_nothing_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in _ENV_NAMES:
            monkeypatch.delenv(name, raising=False)
        assert vault_regression._resolve_detroit_pg_dsn() == vault_regression._DSN_DEFAULT

    def test_canonical_babylon_dsn_wins_over_legacy_test_pg_dsn(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            "BABYLON_TEST_PG_DSN", "host=legacy-target port=5433 dbname=x user=x password=x"
        )
        monkeypatch.setenv(
            "BABYLON_DSN", "host=canonical-target port=5432 dbname=c user=c password=c"
        )
        dsn = vault_regression._resolve_detroit_pg_dsn()
        assert "host=canonical-target" in dsn
        assert "legacy-target" not in dsn

    def test_legacy_test_pg_dsn_still_honored_without_canonical(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("BABYLON_DSN", raising=False)
        monkeypatch.delenv("BABYLON_PG_DSN", raising=False)
        monkeypatch.setenv(
            "BABYLON_TEST_PG_DSN", "host=legacy-target port=5433 dbname=x user=x password=x"
        )
        dsn = vault_regression._resolve_detroit_pg_dsn()
        assert "host=legacy-target" in dsn


class TestPgReachableHonorsTheSeam:
    def test_probes_the_canonical_target_not_the_hardcoded_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_pg_reachable() must probe whatever _resolve_detroit_pg_dsn()
        resolves — not a hardcoded default — so the reachability gate never
        disagrees with the bake it gates about which Postgres to target.
        """
        monkeypatch.setenv(
            "BABYLON_DSN", "host=canonical-target port=5432 dbname=c user=c password=c"
        )
        seen: dict[str, str] = {}

        class _FakeConn:
            def close(self) -> None:
                pass

        def _fake_connect(dsn: str, **kwargs: object) -> _FakeConn:
            seen["dsn"] = dsn
            return _FakeConn()

        import psycopg

        monkeypatch.setattr(psycopg, "connect", _fake_connect)
        assert vault_regression._pg_reachable() is True
        assert "host=canonical-target" in seen["dsn"]
