"""Postgres-backed contract tests for unmanaged Django models.

These tests run against a real PostgreSQL container (via testcontainers)
to verify that:

1. The canonical DDL creates tables that Django can actually query.
2. ``managed=False`` models with ``primary_key=True`` map correctly
   to composite-PK Postgres tables.
3. The DDL and Django models agree on column names at runtime (not
   just via static parsing as in ``test_schema_parity.py``).

Run with::

    mise run test:pg

Requires Docker. Tests are skipped if Docker is unavailable.
"""

from __future__ import annotations

import uuid

import pytest

# ─── All tests in this module require the real Postgres container ───
pytestmark = [pytest.mark.postgres]


@pytest.mark.django_db
class TestGameSessionOnPostgres:
    """Verify GameSession CRUD against real Postgres DDL."""

    def test_create_and_retrieve(self) -> None:
        from game.models import GameSession

        session_id = uuid.uuid4()
        GameSession.objects.create(
            id=session_id,
            scenario="wayne_county",
            current_tick=0,
            status="active",
        )

        retrieved = GameSession.objects.get(id=session_id)
        assert retrieved.scenario == "wayne_county"
        assert retrieved.current_tick == 0
        assert retrieved.status == "active"

    def test_update_tick(self) -> None:
        from game.models import GameSession

        session_id = uuid.uuid4()
        GameSession.objects.create(
            id=session_id,
            scenario="two_node",
            current_tick=0,
            status="active",
        )

        GameSession.objects.filter(id=session_id).update(current_tick=5)
        refreshed = GameSession.objects.get(id=session_id)
        assert refreshed.current_tick == 5

    def test_snapshot_json_is_jsonb(self) -> None:
        """Verify that JSONB columns work — SQLite can't test this."""
        import json

        from game.models import GameSession

        session_id = uuid.uuid4()
        snapshot = {"tick": 3, "orgs": [{"name": "Detroit Workers' Council"}]}
        GameSession.objects.create(
            id=session_id,
            scenario="wayne_county",
            snapshot_json=json.dumps(snapshot),
        )

        retrieved = GameSession.objects.get(id=session_id)
        stored = retrieved.snapshot_json
        if isinstance(stored, str):
            stored = json.loads(stored)
        assert stored["tick"] == 3
        assert stored["orgs"][0]["name"] == "Detroit Workers' Council"


@pytest.mark.django_db
class TestHexStateOnPostgres:
    """Verify HexState queries against real Postgres with composite PK."""

    def _create_session(self) -> uuid.UUID:
        from game.models import GameSession

        session_id = uuid.uuid4()
        GameSession.objects.create(
            id=session_id,
            scenario="wayne_county",
            current_tick=1,
            status="active",
        )
        return session_id

    def test_hex_state_insert_and_query(self) -> None:
        """Django queries hex_latest without crashing on missing 'id'."""
        from game.models import HexState

        game_id = self._create_session()
        HexState.objects.create(
            game_id=game_id,
            tick=1,
            h3_index="872a10000ffffff",
            county_fips="26163",
            county_name="Wayne",
            state_fips="26",
            center_lat=42.3314,
            center_lng=-83.0458,
            heat=0.5,
        )

        hexes = HexState.objects.filter(game_id=game_id)
        assert hexes.count() == 1
        assert hexes.first().county_name == "Wayne"  # type: ignore[union-attr]

    def test_hex_state_unique_constraint(self) -> None:
        """Composite UNIQUE(game_id, h3_index) is enforced."""
        from django.db import IntegrityError

        from game.models import HexState

        game_id = self._create_session()
        kwargs = {
            "game_id": game_id,
            "tick": 1,
            "h3_index": "872a10000ffffff",
            "county_fips": "26163",
            "county_name": "Wayne",
            "state_fips": "26",
            "center_lat": 42.3314,
            "center_lng": -83.0458,
        }
        HexState.objects.create(**kwargs)

        with pytest.raises(IntegrityError):
            HexState.objects.create(**kwargs)


@pytest.mark.django_db
class TestPlayerActionOnPostgres:
    """Verify PlayerAction (game_turn) against real Postgres."""

    def test_create_action(self) -> None:
        from game.models import GameSession, PlayerAction

        session_id = uuid.uuid4()
        GameSession.objects.create(
            id=session_id,
            scenario="wayne_county",
            current_tick=1,
            status="active",
        )

        PlayerAction.objects.create(
            session_id=session_id,
            tick=1,
            org_id="wayne_county_organizing_committee",
            verb="educate",
            target_id="detroit",
        )

        actions = PlayerAction.objects.filter(session_id=session_id)
        assert actions.count() == 1
        assert actions.first().verb == "educate"  # type: ignore[union-attr]


@pytest.mark.django_db
class TestDDLColumnCoverage:
    """Verify Django model fields match real Postgres columns at runtime.

    Uses raw psycopg connections to query ``information_schema.columns``.
    This is the runtime complement to the static DDL parsing in
    ``test_schema_parity.py``.
    """

    def test_game_session_columns_match(self, tc_pg_dsn: str) -> None:
        import psycopg

        with psycopg.connect(tc_pg_dsn) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'game_session'"
            )
            pg_columns = {row[0] for row in cur.fetchall()}

        from game.models import GameSession

        model_fields = {f.column for f in GameSession._meta.get_fields() if hasattr(f, "column")}
        missing_in_pg = model_fields - pg_columns
        assert not missing_in_pg, f"Missing in Postgres: {missing_in_pg}"

    def test_hex_latest_columns_match(self, tc_pg_dsn: str) -> None:
        import psycopg

        with psycopg.connect(tc_pg_dsn) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'hex_latest'"
            )
            pg_columns = {row[0] for row in cur.fetchall()}

        from game.models import HexState

        model_fields = {f.column for f in HexState._meta.get_fields() if hasattr(f, "column")}
        missing_in_pg = model_fields - pg_columns
        assert not missing_in_pg, f"Missing in Postgres: {missing_in_pg}"

    def test_game_turn_columns_match(self, tc_pg_dsn: str) -> None:
        import psycopg

        with psycopg.connect(tc_pg_dsn) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'game_turn'"
            )
            pg_columns = {row[0] for row in cur.fetchall()}

        from game.models import PlayerAction

        model_fields = {f.column for f in PlayerAction._meta.get_fields() if hasattr(f, "column")}
        missing_in_pg = model_fields - pg_columns
        assert not missing_in_pg, f"Missing in Postgres: {missing_in_pg}"

    def test_action_result_columns_match(self, tc_pg_dsn: str) -> None:
        import psycopg

        with psycopg.connect(tc_pg_dsn) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'action_result'"
            )
            pg_columns = {row[0] for row in cur.fetchall()}

        from game.models import ActionResult

        model_fields = {f.column for f in ActionResult._meta.get_fields() if hasattr(f, "column")}
        missing_in_pg = model_fields - pg_columns
        assert not missing_in_pg, f"Missing in Postgres: {missing_in_pg}"
