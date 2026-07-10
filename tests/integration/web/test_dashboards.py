"""Spec-109 A4: real summary/economy/communities dashboards.

``EngineBridge.get_game_summary`` / ``get_economy_dashboard`` /
``get_communities_dashboard`` used to return ``{}`` / ``{"communities":
[]}`` unconditionally — pure stubs. These tests drive the real bridge
against Postgres (same pattern as ``test_full_persistence.py``) and assert
each dashboard surfaces real, non-fabricated values after create + two
resolves (Constitution III.11: no invented values — every asserted field
must trace to a value the engine actually computed).

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


def _resolved_session(bridge: object) -> uuid.UUID:
    """Create a wayne_county session and resolve two ticks."""
    session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)  # type: ignore[attr-defined]
    bridge.resolve_tick(session_id)  # type: ignore[attr-defined]
    bridge.resolve_tick(session_id)  # type: ignore[attr-defined]
    return session_id  # type: ignore[no-any-return]


class TestGameSummary:
    """get_game_summary: top-bar aggregate."""

    def test_summary_after_create_has_real_fields(self, bridge: object) -> None:
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)  # type: ignore[attr-defined]

        summary = bridge.get_game_summary(session_id)  # type: ignore[attr-defined]

        assert summary["tick"] == 0
        # imperial_rent_pool defaults to 100.0 in GlobalEconomy — always present.
        assert summary["imperial_rent"] is not None
        assert summary["avg_consciousness"] is not None
        assert summary["population_total"] is not None
        assert summary["population_total"] > 0
        assert summary["org_count"] >= 0
        assert summary["class_count"] > 0
        assert summary["event_counts"] == {"critical": 0, "warning": 0, "informational": 0}
        # Never fabricated — the engine has no c/v/s decomposition.
        assert summary["profit_rate"] is None

    def test_summary_tick_advances_after_resolves(self, bridge: object) -> None:
        session_id = _resolved_session(bridge)

        summary = bridge.get_game_summary(session_id)  # type: ignore[attr-defined]

        assert summary["tick"] == 2
        assert summary["imperial_rent"] is not None
        assert summary["avg_consciousness"] is not None


class TestEconomyDashboard:
    """get_economy_dashboard: dashboard-wide economy aggregate."""

    def test_economy_dashboard_after_create_has_real_fields(self, bridge: object) -> None:
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)  # type: ignore[attr-defined]

        economy = bridge.get_economy_dashboard(session_id)  # type: ignore[attr-defined]

        assert economy["tick"] == 0
        assert economy["imperial_rent_pool"] is not None
        assert economy["current_super_wage_rate"] is not None
        assert isinstance(economy["wealth_by_class_role"], dict)
        assert economy["wealth_by_class_role"]  # wayne_county seeds several classes
        assert all(v >= 0.0 for v in economy["wealth_by_class_role"].values())
        # Never fabricated.
        assert economy["profit_rate"] is None
        assert economy["occ"] is None

    def test_economy_dashboard_wage_flow_after_resolves(self, bridge: object) -> None:
        session_id = _resolved_session(bridge)

        economy = bridge.get_economy_dashboard(session_id)  # type: ignore[attr-defined]

        assert economy["tick"] == 2
        # wayne_county seeds a WAGES edge (bourgeoisie -> suburban PB); after
        # resolves the wage-payment system should have moved real value.
        assert economy["wage_flow_total"] >= 0.0
        assert isinstance(economy["value_produced"], float)
        assert isinstance(economy["rent_extracted"], float)


class TestCommunitiesDashboard:
    """get_communities_dashboard: SOLIDARITY-edge connected components."""

    def test_communities_surface_the_seeded_solidarity_edge(self, bridge: object) -> None:
        """wayne_county seeds one SOLIDARITY edge (Detroit proletariat <->
        Dearborn workers) at tick 0 — it must surface as one community."""
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)  # type: ignore[attr-defined]

        result = bridge.get_communities_dashboard(session_id)  # type: ignore[attr-defined]

        communities = result["communities"]
        assert len(communities) >= 1
        community = communities[0]
        assert community["member_count"] >= 2
        assert len(community["member_ids"]) == community["member_count"]
        assert community["total_solidarity_strength"] > 0.0
        assert community["id"]

    def test_communities_stable_after_resolves(self, bridge: object) -> None:
        session_id = _resolved_session(bridge)

        result = bridge.get_communities_dashboard(session_id)  # type: ignore[attr-defined]

        assert len(result["communities"]) >= 1
