"""State Apparatus dashboard (spec-111 C2) — the anti-inert contract.

``get_state_apparatus_dashboard`` / ``_build_state_apparatus_dashboard`` were
written when NO scenario seeded a ``state_apparatus`` org, so their docstrings
long promised "an honest empty list for every session today". That is now
STALE: wayne_county seeds the Detroit Police Department (``ORG002``, a
``StateApparatus`` — ``_legacy_wayne.py::_create_state_apparatus_org``, commit
``70d6e3f2``), and the RuleBasedStateAI drives it every tick (tasks #72/#73).

These tests PIN the dashboard as NON-EMPTY for the canonical scenario, so the
"faith in a dead endpoint" regression (a panel rendering over a permanently
empty payload — the legitimation-index trap) can never silently return. If a
future refactor drops the state-org seeding, these go red loudly.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def _wayne_dashboard() -> dict[str, object]:
    from game.engine_bridge import (
        _build_initial_state_for_scenario,
        _build_state_apparatus_dashboard,
        _serialize_organization,
    )

    state = _build_initial_state_for_scenario("wayne_county")
    organizations = [_serialize_organization(o) for o in state.organizations.values()]
    return _build_state_apparatus_dashboard(state, organizations, recent_actions=[])


class TestStateApparatusDashboardIsReal:
    """The Detroit PD is seeded — the dashboard is a live surface, not a stub."""

    def test_wayne_county_seeds_a_state_apparatus_org(self) -> None:
        dashboard = _wayne_dashboard()
        assert dashboard["org_count"] >= 1, (
            "wayne_county must seed >=1 state_apparatus org (ORG002)"
        )
        assert len(dashboard["organizations"]) == dashboard["org_count"]

    def test_every_dashboard_org_is_state_apparatus_typed(self) -> None:
        dashboard = _wayne_dashboard()
        orgs = dashboard["organizations"]
        assert orgs  # non-empty (guarded above; explicit here for clarity)
        for org in orgs:  # type: ignore[union-attr]
            assert org["org_type"] == "state_apparatus"

    def test_detroit_pd_is_present(self) -> None:
        dashboard = _wayne_dashboard()
        ids = {org["id"] for org in dashboard["organizations"]}  # type: ignore[union-attr]
        assert "ORG002" in ids, "the Detroit Police Department (ORG002) must be surfaced"

    def test_aggregate_budget_and_heat_are_real_floats(self) -> None:
        dashboard = _wayne_dashboard()
        assert isinstance(dashboard["total_repression_budget"], float)
        assert isinstance(dashboard["total_heat"], float)
        # Detroit PD is seeded with a repression budget > 0 (a police force with
        # no budget would be a modelling error, not honest-null).
        assert dashboard["total_repression_budget"] > 0.0

    def test_state_finances_is_an_honest_empty_map(self) -> None:
        """No scenario seeds WorldState.state_finances yet (III.11): an honest
        empty map, distinct from the org list which IS seeded."""
        dashboard = _wayne_dashboard()
        assert dashboard["state_finances"] == {}

    def test_payload_carries_the_full_contract_shape(self) -> None:
        dashboard = _wayne_dashboard()
        for key in (
            "tick",
            "organizations",
            "org_count",
            "total_repression_budget",
            "total_heat",
            "state_finances",
            "recent_actions",
        ):
            assert key in dashboard, f"contract key {key!r} missing from dashboard payload"
