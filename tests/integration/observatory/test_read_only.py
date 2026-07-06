"""Read-only guarantee — proven against the LIVE ``sim`` alias (spec-096, US3).

The alias opens every connection ``default_transaction_read_only=on``; a write
must be rejected by Postgres. Reads on the same connection must still succeed.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from django.db import DatabaseError, connections

pytestmark = pytest.mark.integration


class TestSimAliasReadOnly:
    def test_read_succeeds(self, sim_alias: str, django_db_blocker: Any) -> None:
        with django_db_blocker.unblock(), connections[sim_alias].cursor() as cur:
            cur.execute("SELECT 1")
            assert cur.fetchone()[0] == 1

    def test_insert_is_rejected_as_read_only(self, sim_alias: str, django_db_blocker: Any) -> None:
        with django_db_blocker.unblock(), connections[sim_alias].cursor() as cur:
            with pytest.raises(DatabaseError) as excinfo:
                cur.execute(
                    "INSERT INTO tick_commit "
                    "(session_id, tick, determinism_hash, hex_rows_written, is_checkpoint) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (str(uuid4()), 999_999, "0" * 64, 0, False),
                )
            assert "read-only" in str(excinfo.value).lower()

    def test_ddl_is_rejected_as_read_only(self, sim_alias: str, django_db_blocker: Any) -> None:
        with django_db_blocker.unblock(), connections[sim_alias].cursor() as cur:
            with pytest.raises(DatabaseError) as excinfo:
                cur.execute("CREATE TABLE observatory_should_not_exist (n int)")
            assert "read-only" in str(excinfo.value).lower()

    def test_router_refuses_sim_migrations(self, sim_alias: str) -> None:
        from observatory.router import SimDatabaseRouter

        router = SimDatabaseRouter()
        assert router.allow_migrate(sim_alias, "auth") is False
        assert router.allow_migrate(sim_alias, "game", model_name="GameSession") is False
