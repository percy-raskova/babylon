"""Unit tests for the read-only ``sim`` database alias builder (spec-096).

The Observatory reads the simulation runner's Postgres through a second Django
database alias. ``build_sim_database_alias`` parses the libpq keyword DSN used
by ``tools/tick_probe.py`` into Django connection params and pins the
connection read-only at the server level.
"""

from __future__ import annotations

import pytest

from observatory.db import (
    SIM_READ_ONLY_OPTION,
    build_sim_database_alias,
    default_sim_dsn,
)

pytestmark = pytest.mark.unit

_DSN = "host=localhost port=5433 dbname=babylon_test user=test password=test"


class TestBuildSimDatabaseAlias:
    def test_parses_core_connection_params(self) -> None:
        alias = build_sim_database_alias(_DSN)
        assert alias["ENGINE"] == "django.db.backends.postgresql"
        assert alias["NAME"] == "babylon_test"
        assert alias["USER"] == "test"
        assert alias["PASSWORD"] == "test"  # noqa: S105 — test fixture value
        assert alias["HOST"] == "localhost"
        assert str(alias["PORT"]) == "5433"

    def test_connection_is_read_only(self) -> None:
        alias = build_sim_database_alias(_DSN)
        assert alias["OPTIONS"]["options"] == SIM_READ_ONLY_OPTION
        assert "default_transaction_read_only=on" in alias["OPTIONS"]["options"]

    def test_does_not_participate_in_django_test_db_creation(self) -> None:
        # A MIRROR of the default alias tells Django's test runner not to try
        # to create/destroy a test database for this external, read-only DB.
        alias = build_sim_database_alias(_DSN)
        assert alias["TEST"]["MIRROR"] == "default"

    def test_default_dsn_targets_canonical_local_sim_db(self) -> None:
        dsn = default_sim_dsn()
        assert "port=5433" in dsn
        assert "dbname=babylon_test" in dsn

    def test_env_override_is_respected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "BABYLON_PG_DSN",
            "host=db.example port=6000 dbname=other user=u password=p",
        )
        alias = build_sim_database_alias(default_sim_dsn())
        assert alias["HOST"] == "db.example"
        assert str(alias["PORT"]) == "6000"
        assert alias["NAME"] == "other"

    def test_url_style_dsn_is_also_accepted(self) -> None:
        alias = build_sim_database_alias(
            "postgresql://u:p@h:5432/simdb",
        )
        assert alias["NAME"] == "simdb"
        assert alias["USER"] == "u"
        assert alias["HOST"] == "h"
        assert str(alias["PORT"]) == "5432"
