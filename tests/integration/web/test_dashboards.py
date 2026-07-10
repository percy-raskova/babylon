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


class TestEdgesDashboard:
    """get_edges_dashboard: real edge aggregates (spec 111 C2)."""

    def test_edges_dashboard_after_create_has_real_counts(self, bridge: object) -> None:
        """wayne_county's own scenario seeds 85 relationships (81 tenancy, 2
        exploitation, 1 wages, 1 solidarity); the bridge's spec-070
        balkanization seed layer (_seed_balkanization_layer) adds more
        (INFLUENCES/PRESENCE) on top — all real graph edges at tick 0,
        before any resolve."""
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)  # type: ignore[attr-defined]

        edges = bridge.get_edges_dashboard(session_id)  # type: ignore[attr-defined]

        assert edges["tick"] == 0
        assert edges["total_edges"] >= 85
        assert sum(edges["counts_by_type"].values()) == edges["total_edges"]
        assert edges["counts_by_type"]["tenancy"] == 81
        assert edges["counts_by_type"]["exploitation"] == 2
        assert edges["counts_by_type"]["wages"] == 1
        assert edges["counts_by_type"]["solidarity"] == 1
        # edge_mode is only populated once EdgeTransitionSystem has run.
        assert edges["counts_by_mode"] == {}
        assert isinstance(edges["top_by_value_flow"], list)
        assert isinstance(edges["top_by_tension"], list)
        assert len(edges["top_by_value_flow"]) <= 10
        stats = edges["solidarity_strength_stats"]
        assert stats["count"] == 1
        assert stats["avg"] is not None

    def test_edges_dashboard_after_resolves_stable(self, bridge: object) -> None:
        session_id = _resolved_session(bridge)

        edges = bridge.get_edges_dashboard(session_id)  # type: ignore[attr-defined]

        assert edges["tick"] == 2
        assert edges["total_edges"] >= 85
        assert sum(edges["counts_by_type"].values()) == edges["total_edges"]


class TestStateApparatusDashboard:
    """get_state_apparatus_dashboard: real state-org data (spec 111 C2)."""

    def test_state_apparatus_dashboard_honest_empty_for_wayne_county(self, bridge: object) -> None:
        """wayne_county's sole seeded org is CIVIL_SOCIETY (the player org) —
        no scenario seeds a STATE_APPARATUS org or StateFinance record, so
        this is an honest empty, not a fabricated placeholder (III.11)."""
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)  # type: ignore[attr-defined]

        result = bridge.get_state_apparatus_dashboard(session_id)  # type: ignore[attr-defined]

        assert result["tick"] == 0
        assert result["organizations"] == []
        assert result["org_count"] == 0
        assert result["total_repression_budget"] == 0.0
        assert result["total_heat"] == 0.0
        assert result["state_finances"] == {}
        assert result["recent_actions"] == []

    def test_state_apparatus_dashboard_after_resolves(self, bridge: object) -> None:
        session_id = _resolved_session(bridge)

        result = bridge.get_state_apparatus_dashboard(session_id)  # type: ignore[attr-defined]

        assert result["tick"] == 2
        assert isinstance(result["recent_actions"], list)


class TestInfrastructure:
    """get_infrastructure: honest transport-substrate contract (spec 111 C2)."""

    def test_infrastructure_honest_empty(self, bridge: object) -> None:
        """No production caller writes infrastructure_link_state yet
        (Amendment O is PENDING CODE) — an honest empty edges list beats a
        fabricated corridor network (III.11)."""
        session_id = bridge.create_game(scenario="wayne_county", rng_seed=0)  # type: ignore[attr-defined]

        result = bridge.get_infrastructure(session_id)  # type: ignore[attr-defined]

        assert result["tick"] == 0
        assert result["nodes"] == []
        assert result["edges"] == []


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
