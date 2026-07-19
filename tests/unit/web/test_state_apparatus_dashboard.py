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
    organizations = [
        _serialize_organization(o, player_org_id=state.player_org_id)
        for o in state.organizations.values()
    ]
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


def _wayne_dashboard_fog_aware() -> dict[str, object]:
    """The REAL player-facing path (:meth:`EngineBridge.get_state_apparatus_dashboard`
    threads ``reach``/``ledger``/``tick`` through ``_serialize_organization`` —
    :func:`_wayne_dashboard` above deliberately does not, so it never
    exercises fog at all). Bypasses the DB-backed ``_derive_intel_ledger``
    (no persistence handle in a unit test) with the empty
    :class:`~game.fog.ledger.IntelLedger`, mirroring
    ``TestVerbEligibilityAgreesWithTargetsRealWayneCounty``'s own pattern in
    ``test_engine_bridge.py``.
    """
    from game.engine_bridge import (
        _build_initial_state_for_scenario,
        _build_state_apparatus_dashboard,
        _current_intel_aging_ticks,
        _current_organizing_reach,
        _serialize_organization,
    )
    from game.fog.ledger import IntelLedger

    state = _build_initial_state_for_scenario("wayne_county")
    graph = state.to_graph()
    reach = _current_organizing_reach(graph)
    staleness_ticks, unknown_ticks = _current_intel_aging_ticks()
    organizations = [
        _serialize_organization(
            o,
            player_org_id=state.player_org_id,
            reach=reach,
            ledger=IntelLedger(),
            tick=state.tick,
        )
        for o in state.organizations.values()
    ]
    return _build_state_apparatus_dashboard(state, organizations, recent_actions=[])


class TestStateApparatusDashboardNullHeatBudgetContract:
    """Root cause of the R1 regression (task #49 post-merge e2e sweep):
    ``StateOrgList`` (``StateApparatusDashboard.tsx``) called
    ``org.heat.toFixed(2)`` with no null guard. Investigation (see
    ``ai/state.yaml``/session notes) ruled out the initial hypothesis that
    ADR086's seeded BOURGEOIS Business orgs were the cause — verified by
    rebuilding ``create_wayne_county_scenario`` with
    ``build_seeded_businesses`` monkeypatched to return ``{}``: ORG002's
    heat is masked either way. The REAL cause is Track 1 Task 4/5's
    reach-based org fog (``game.fog.filter.apply_fog``,
    ``ORG_POLITICAL_FIELDS`` includes ``heat``) combined with
    ``organizing_reach`` (``web/game/fog/reach.py``) never including any
    org id other than the player's own — so ORG002 (Detroit PD, a
    non-player org) is masked in EVERY wayne_county session, business orgs
    or not. This is the SAME contract ``test_org_internal_state_fog.py``'s
    ``TestBuildStateApparatusDashboardHeatFog`` already pins with hand-built
    ``_StubOrg`` fixtures; these tests pin it against the REAL, ADR086
    business-orgs-present scenario end-to-end (the "red first" integration
    gap the fixture-only tests left open — they never proved the real
    scenario's ORG002 actually hits this path).
    """

    def test_wayne_county_seeds_business_orgs_alongside_the_state_org(self) -> None:
        """Sanity check: this scenario genuinely carries ADR086's seeded
        BOURGEOIS Business orgs (the class this investigation ruled out as
        the cause of R1 — confirmed present, not merely assumed)."""
        from babylon.models.enums import ClassCharacter, OrgType
        from game.engine_bridge import _build_initial_state_for_scenario

        state = _build_initial_state_for_scenario("wayne_county")
        business_orgs = [o for o in state.organizations.values() if o.org_type == OrgType.BUSINESS]
        assert business_orgs, "wayne_county must seed >=1 Business org (ADR086)"
        assert all(o.class_character == ClassCharacter.BOURGEOIS for o in business_orgs)

    def test_every_dashboard_org_entry_budget_is_always_numeric(self) -> None:
        """budget is MATERIAL (never in ``ORG_POLITICAL_FIELDS``) — every
        dashboard entry's budget must be a real float, fog or not."""
        dashboard = _wayne_dashboard_fog_aware()
        orgs = dashboard["organizations"]
        assert orgs, "wayne_county must seed >=1 state_apparatus org (ORG002)"
        for org in orgs:  # type: ignore[union-attr]
            assert isinstance(org["budget"], float)

    def test_detroit_pd_heat_is_masked_outside_the_players_organizing_reach(self) -> None:
        """The actual, currently-live contract: ORG002 is a non-player org
        and ``organizing_reach`` never includes any org id but the
        player's own (``web/game/fog/reach.py``), so ORG002's heat is
        honestly ``None`` (masked), never a fabricated ``0.0``. This is
        NOT a business-org effect — it reproduces identically with zero
        Business orgs seeded (see the class docstring)."""
        dashboard = _wayne_dashboard_fog_aware()
        orgs = {org["id"]: org for org in dashboard["organizations"]}  # type: ignore[union-attr]
        assert orgs["ORG002"]["heat"] is None
        assert dashboard["total_heat"] is None
        assert dashboard["heat_orgs_masked"] == 1
        assert dashboard["heat_orgs_visible"] == 0

    def test_detroit_pd_heat_is_real_and_numeric_once_in_reach(self) -> None:
        """No overcorrection: once ORG002 IS in the player's organizing
        reach, its heat renders as a real number again, not permanently
        null — the fog gate is reach-conditional, not a dead field."""
        from game.engine_bridge import (
            _build_initial_state_for_scenario,
            _build_state_apparatus_dashboard,
            _serialize_organization,
        )
        from game.fog.ledger import IntelLedger

        state = _build_initial_state_for_scenario("wayne_county")
        organizations = [
            _serialize_organization(
                o,
                player_org_id=state.player_org_id,
                reach=frozenset({"ORG002"}),
                ledger=IntelLedger(),
                tick=state.tick,
            )
            for o in state.organizations.values()
        ]
        dashboard = _build_state_apparatus_dashboard(state, organizations, recent_actions=[])
        org002 = next(o for o in dashboard["organizations"] if o["id"] == "ORG002")  # type: ignore[union-attr]

        assert isinstance(org002["heat"], float)
        assert isinstance(dashboard["total_heat"], float)
        assert dashboard["heat_orgs_masked"] == 0
