"""Unit tests for the single Postgres DSN-resolution seam (T1.2 keel).

Covers the precedence order (canonical > legacy > default), legacy-name
back-compat fallback (including the Django ``POSTGRES_*`` split-var scheme),
and the ADR099 unix-socket DSN-form guardrail.
"""

from __future__ import annotations

import pytest
from psycopg.conninfo import conninfo_to_dict

from babylon.config.dsn import CANONICAL_DSN_ENV_VAR, postgres_split_dsn, resolve_dsn

pytestmark = pytest.mark.unit


class TestResolveDsnPrecedence:
    def test_canonical_wins_over_legacy_and_default(self) -> None:
        env = {
            "BABYLON_DSN": "host=canonical port=1 dbname=c user=c password=c",
            "BABYLON_PG_DSN": "host=legacy port=2 dbname=l user=l password=l",
        }
        result = resolve_dsn(
            legacy_env="BABYLON_PG_DSN",
            default="host=fallback",
            env=env,
        )
        assert result == env["BABYLON_DSN"]

    def test_legacy_wins_over_default_when_canonical_unset(self) -> None:
        env = {"BABYLON_PG_DSN": "host=legacy port=2 dbname=l user=l password=l"}
        result = resolve_dsn(legacy_env="BABYLON_PG_DSN", default="host=fallback", env=env)
        assert result == env["BABYLON_PG_DSN"]

    def test_falls_back_to_default_when_nothing_set(self) -> None:
        result = resolve_dsn(legacy_env="BABYLON_PG_DSN", default="host=fallback", env={})
        assert result == "host=fallback"

    def test_returns_none_when_no_default_and_nothing_set(self) -> None:
        assert resolve_dsn(legacy_env="BABYLON_PG_DSN", env={}) is None

    def test_legacy_sequence_checked_in_order(self) -> None:
        env = {"BABYLON_TEST_PG_DSN": "host=test-fallback"}
        result = resolve_dsn(
            legacy_env=("BABYLON_PG_DSN", "BABYLON_TEST_PG_DSN"),
            env=env,
        )
        assert result == "host=test-fallback"

        env_both = {
            "BABYLON_PG_DSN": "host=primary-legacy",
            "BABYLON_TEST_PG_DSN": "host=test-fallback",
        }
        result_both = resolve_dsn(
            legacy_env=("BABYLON_PG_DSN", "BABYLON_TEST_PG_DSN"),
            env=env_both,
        )
        assert result_both == "host=primary-legacy"

    def test_empty_string_env_var_treated_as_unset(self) -> None:
        env = {"BABYLON_DSN": "", "BABYLON_PG_DSN": ""}
        result = resolve_dsn(legacy_env="BABYLON_PG_DSN", default="host=fallback", env=env)
        assert result == "host=fallback"

    def test_default_environ_used_when_env_arg_omitted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(CANONICAL_DSN_ENV_VAR, raising=False)
        monkeypatch.setenv("BABYLON_PG_DSN", "host=from-real-environ")
        assert resolve_dsn(legacy_env="BABYLON_PG_DSN") == "host=from-real-environ"


class TestResolveDsnUnixSocketForm:
    def test_canonical_unix_socket_dsn_passes_through_unchanged(self) -> None:
        env = {"BABYLON_DSN": "host=/var/run/postgresql dbname=babylon"}
        result = resolve_dsn(env=env)
        assert result == env["BABYLON_DSN"]
        # And it must actually be a legal, parseable unix-socket DSN.
        assert conninfo_to_dict(result)["host"] == "/var/run/postgresql"

    def test_legacy_unix_socket_url_form_passes_through_unchanged(self) -> None:
        url = "postgresql://babylon@/babylon?host=/var/run/postgresql"
        result = resolve_dsn(legacy_env="BABYLON_PG_DSN", env={"BABYLON_PG_DSN": url})
        assert result == url
        assert conninfo_to_dict(result)["host"] == "/var/run/postgresql"


class TestPostgresSplitDsn:
    def test_uses_field_level_defaults_when_nothing_set(self) -> None:
        dsn = postgres_split_dsn({})
        params = conninfo_to_dict(dsn)
        assert params["host"] == "localhost"
        assert params["port"] == "5432"
        assert params["dbname"] == "babylon"
        assert params["user"] == "babylon"
        assert params["password"] == "babylon"

    def test_each_field_overridden_independently(self) -> None:
        env = {"POSTGRES_HOST": "db.example"}
        dsn = postgres_split_dsn(env)
        params = conninfo_to_dict(dsn)
        assert params["host"] == "db.example"
        # unset fields keep their own defaults, not blanked out.
        assert params["dbname"] == "babylon"
        assert params["port"] == "5432"

    def test_unix_socket_host_directory(self) -> None:
        env = {"POSTGRES_HOST": "/var/run/postgresql", "POSTGRES_DB": "babylon"}
        dsn = postgres_split_dsn(env)
        params = conninfo_to_dict(dsn)
        assert params["host"] == "/var/run/postgresql"
        assert params["dbname"] == "babylon"

    def test_custom_defaults_are_honored(self) -> None:
        dsn = postgres_split_dsn(
            {}, host="custom-host", port="9999", dbname="d", user="u", password="p"
        )
        params = conninfo_to_dict(dsn)
        assert params["host"] == "custom-host"
        assert params["port"] == "9999"
        assert params["dbname"] == "d"
        assert params["user"] == "u"
        assert params["password"] == "p"


class TestResolveDsnWithPostgresSplitAsDefault:
    """Mirrors how web/babylon_web/settings/base.py composes the two functions."""

    def test_canonical_still_wins_over_split_default(self) -> None:
        env = {
            "BABYLON_DSN": "host=canonical",
            "POSTGRES_HOST": "should-be-ignored",
        }
        result = resolve_dsn(default=postgres_split_dsn(env), env=env)
        assert result == "host=canonical"

    def test_split_vars_apply_when_canonical_unset(self) -> None:
        env = {"POSTGRES_HOST": "split-host", "POSTGRES_DB": "split-db"}
        result = resolve_dsn(default=postgres_split_dsn(env), env=env)
        params = conninfo_to_dict(result)
        assert params["host"] == "split-host"
        assert params["dbname"] == "split-db"
