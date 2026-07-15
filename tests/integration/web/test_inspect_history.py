"""Spec-111 C2: real inspect-history endpoints.

Post-A1, ``org_snapshot``/``territory_snapshot`` carry one real row per
``(session, tick, entity)`` — written every resolve via
``EngineBridge._persist_snapshots_safe``. Before this lane,
``EngineBridge`` had no method to read that history back out for the
inspector's history tab. These tests drive the real bridge against
Postgres (same pattern as ``test_dashboards.py``) and assert the new
``get_org_history``/``get_territory_history`` methods surface real,
per-tick, non-fabricated rows (Constitution III.11).

Program 17 Wave 2 W2.5b (owner ruling 3) adds ``class_snapshot``/
``get_class_history`` — the survival-probability duel chart's real
backing history, mirroring the org/territory pattern exactly.

Requires a running PostgreSQL instance. Skip with:
``pytest -m "not requires_postgres"``.
"""

from __future__ import annotations

import os
import uuid

import pytest

pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(
        not os.environ.get("POSTGRES_HOST"),
        reason="PostgreSQL not configured (set POSTGRES_HOST)",
    ),
]

# wayne_county's sole seeded org (the player org, see _create_player_org).
_WAYNE_PLAYER_ORG_ID = "ORG001"
# Every wayne_county web session stamps all 81 hex territories with this
# real FIPS (see EngineBridge._seed_wayne_county_fips / WAYNE_COUNTY_FIPS).
_WAYNE_COUNTY_FIPS = "26163"
# Dearborn Industrial Workers — the sole PERIPHERY_PROLETARIAT (struggling)
# role in wayne_county, so the only class that can ever produce a real
# UPRISING/revolutionary_pressure rupture marker (see
# babylon.engine.scenarios._legacy_wayne, struggle.py _STRUGGLING_ROLES).
_DEARBORN_WORKERS_ID = "C004"


@pytest.fixture
def _django_setup() -> None:
    """Ensure Django is configured before running tests."""
    import django
    from django.conf import settings

    if not settings.configured:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "babylon_web.settings.development")
        django.setup()


@pytest.fixture
def bridge(_django_setup: None) -> object:
    """Create an EngineBridge connected to PostgreSQL."""
    from psycopg_pool import ConnectionPool

    from babylon.persistence.postgres_runtime import PostgresRuntime

    conninfo = (
        f"dbname={os.environ.get('POSTGRES_DB', 'babylon_test')} "
        f"host={os.environ.get('POSTGRES_HOST', 'localhost')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"user={os.environ.get('POSTGRES_USER', 'babylon')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', 'babylon')}"
    )
    pool = ConnectionPool(conninfo=conninfo, min_size=1, max_size=2, open=True)
    persistence = PostgresRuntime(pool)

    from game.engine_bridge import EngineBridge

    return EngineBridge(persistence)


def _resolved_session(bridge: object, n_resolves: int = 2) -> uuid.UUID:
    """Create a wayne_county session and resolve ``n_resolves`` ticks."""
    session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)  # type: ignore[attr-defined]
    for _ in range(n_resolves):
        bridge.resolve_tick(session_id)  # type: ignore[attr-defined]
    return session_id  # type: ignore[no-any-return]


class TestOrgHistory:
    """get_org_history: real per-tick org_snapshot rows."""

    def test_org_history_grows_across_resolves(self, bridge: object) -> None:
        session_id = _resolved_session(bridge, n_resolves=2)

        result = bridge.get_org_history(session_id, _WAYNE_PLAYER_ORG_ID)  # type: ignore[attr-defined]

        assert result["org_id"] == _WAYNE_PLAYER_ORG_ID
        history = result["history"]
        # One row per resolved tick (0, 1, 2) — persisted at create + each resolve.
        assert len(history) == 3
        ticks = [row["tick"] for row in history]
        assert ticks == sorted(ticks)  # oldest-tick-first
        assert ticks == [0, 1, 2]
        # Real fields from _org_snapshot_rows: material_resources <- budget,
        # coherence <- cohesion — never None for a seeded org.
        for row in history:
            assert row["org_type"] == "civil_society"
            assert row["material_resources"] is not None
            assert row["coherence"] is not None
            assert isinstance(row["attributes"], dict)

    def test_org_history_unknown_org_is_honest_empty(self, bridge: object) -> None:
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)  # type: ignore[attr-defined]

        result = bridge.get_org_history(session_id, "NOT_A_REAL_ORG")  # type: ignore[attr-defined]

        assert result["org_id"] == "NOT_A_REAL_ORG"
        assert result["history"] == []


class TestTerritoryHistory:
    """get_territory_history: real per-tick territory_snapshot rows."""

    def test_territory_history_grows_across_resolves(self, bridge: object) -> None:
        session_id = _resolved_session(bridge, n_resolves=2)

        result = bridge.get_territory_history(session_id, _WAYNE_COUNTY_FIPS)  # type: ignore[attr-defined]

        assert result["county_fips"] == _WAYNE_COUNTY_FIPS
        history = result["history"]
        assert len(history) == 3
        ticks = [row["tick"] for row in history]
        assert ticks == [0, 1, 2]
        for row in history:
            assert row["pop_total"] is not None
            assert row["pop_total"] > 0
            assert isinstance(row["attributes"], dict)

    def test_territory_history_unknown_fips_is_honest_empty(self, bridge: object) -> None:
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)  # type: ignore[attr-defined]

        result = bridge.get_territory_history(session_id, "99999")  # type: ignore[attr-defined]

        assert result["county_fips"] == "99999"
        assert result["history"] == []


class TestClassHistory:
    """get_class_history: real per-tick class_snapshot rows + rupture markers
    (Program 17 Wave 2 W2.5b, owner ruling 3)."""

    def test_class_history_grows_across_resolves(self, bridge: object) -> None:
        session_id = _resolved_session(bridge, n_resolves=2)

        result = bridge.get_class_history(session_id, _DEARBORN_WORKERS_ID)  # type: ignore[attr-defined]

        assert result["class_id"] == _DEARBORN_WORKERS_ID
        history = result["history"]
        # One row per resolved tick (0, 1, 2) — persisted at create + each resolve.
        assert len(history) == 3
        ticks = [row["tick"] for row in history]
        assert ticks == sorted(ticks)  # oldest-tick-first
        assert ticks == [0, 1, 2]
        # Real fields from _class_snapshot_rows: role is a required, never-null
        # SocialClass field; p_acquiescence/p_revolution are the survival duel's
        # two series — real (if legitimately 0.0-at-tick-0) SurvivalSystem output.
        for row in history:
            assert row["role"] == "periphery_proletariat"
            assert row["p_acquiescence"] is not None
            assert row["p_revolution"] is not None
            assert isinstance(row["attributes"], dict)
        # Ruptures: honest per Constitution III.11 — no assertion on count (a
        # deterministic-but-stochastic-gated UPRISING may or may not fire in
        # 2 resolves), only that the mechanism returns the real, typed shape.
        assert isinstance(result["ruptures"], list)
        for rupture in result["ruptures"]:
            assert rupture["type"] == "uprising"
            assert rupture["data"]["trigger"] == "revolutionary_pressure"

    def test_class_history_unknown_class_id_is_honest_empty(self, bridge: object) -> None:
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)  # type: ignore[attr-defined]

        result = bridge.get_class_history(session_id, "NOT_A_REAL_CLASS")  # type: ignore[attr-defined]

        assert result["class_id"] == "NOT_A_REAL_CLASS"
        assert result["history"] == []
        assert result["ruptures"] == []
