"""Unit tests for the national Cadre Council player org (Blocker B1).

RED PHASE TDD: ``create_us_scenario()`` (the ``us_nationwide`` canonical
campaign, aliased in ``web/game/engine_bridge.py``) seeded ZERO
organizations before this fix -- ``player_org_id`` was ``None`` and every
player-org-keyed surface (fog reach, doctrine tree, verb-target queries)
had nothing to key off. Owner ruling (2026-07-18): seed exactly ONE
national player org -- a single Cadre Council -- mirroring how
``_legacy_wayne.py`` builds ``ORG001`` for the Wayne County scenario.

``cadre_level`` must be >= 0.24 (owner-ruled B2): ``theoretical_labor``
accrues at ``cadre_level * study_allocation`` per tick
(``engine/systems/doctrine.py``), ``study_allocation`` is the fixed
midpoint of the ratified [0.15, 0.25] band = 0.20, and the cheapest
non-root doctrine node (``trade_unionism``) costs 25 TL. Solving
``25 / (cadre * 0.2) <= 520`` (the campaign length) gives
``cadre >= 0.25`` -- the value ownership ruled to actually use.
"""

from __future__ import annotations

import pytest

from babylon.engine.scenarios import create_us_scenario
from babylon.engine.scenarios.business_seeds import build_seeded_businesses
from babylon.models.entities.organization import CivilSocietyOrg
from babylon.models.enums import EdgeType, OrgType
from babylon.models.world_state import WorldState

pytestmark = pytest.mark.unit


class TestUSScenarioHasAPlayerOrg:
    """``create_us_scenario()`` must seed exactly one player-keyed org."""

    def test_player_org_id_is_set(self) -> None:
        state, _config, _defines = create_us_scenario()
        assert state.player_org_id is not None

    def test_player_org_id_names_a_real_organization(self) -> None:
        state, _config, _defines = create_us_scenario()
        assert state.player_org_id in state.organizations

    def test_exactly_one_player_org_plus_seeded_businesses(self) -> None:
        """Owner ruling: ONE national PLAYER org, not a multi-org player
        contract -- every player-org-keyed surface assumes a single
        ``player_org_id``. ADR086 additionally seeds real-QCEW ``Business``
        NPCs (``BIZ_US_*``), so the total org count is 1 player + the seed
        count (was ``== 1`` before ADR086)."""
        state, _config, _defines = create_us_scenario()
        seeded = build_seeded_businesses("US", [])
        businesses = [o for o in state.organizations.values() if o.org_type == OrgType.BUSINESS]
        assert len(businesses) == len(seeded)
        assert len(state.organizations) == 1 + len(seeded)
        # Exactly one player-keyed org remains (the single-player_org_id contract).
        assert state.player_org_id is not None
        assert isinstance(state.organizations[state.player_org_id], CivilSocietyOrg)

    def test_player_org_is_civil_society_type(self) -> None:
        """Mirrors ``_legacy_wayne.py``'s ``ORG001`` shape exactly."""
        state, _config, _defines = create_us_scenario()
        org = state.organizations[state.player_org_id]  # type: ignore[index]
        assert isinstance(org, CivilSocietyOrg)


class TestCadreLevelMeetsB2Floor:
    """Owner ruling B2: cadre_level >= 0.24 (use 0.25) or trade_unionism is
    unreachable in a 520-tick campaign."""

    def test_cadre_level_at_least_point_two_four(self) -> None:
        state, _config, _defines = create_us_scenario()
        org = state.organizations[state.player_org_id]  # type: ignore[index]
        assert org.cadre_level >= 0.24

    def test_cadre_level_is_the_ruled_point_two_five(self) -> None:
        state, _config, _defines = create_us_scenario()
        org = state.organizations[state.player_org_id]  # type: ignore[index]
        assert org.cadre_level == pytest.approx(0.25)


class TestPlayerOrgHasARealStartingRegion:
    """The org must have real ``territory_ids`` -- present in the scenario's
    own territory dict, not fabricated IDs -- so PRESENCE edges (``to_graph``,
    ``world_state.py:698-704``) actually materialize."""

    def test_territory_ids_nonempty(self) -> None:
        state, _config, _defines = create_us_scenario()
        org = state.organizations[state.player_org_id]  # type: ignore[index]
        assert len(org.territory_ids) > 0

    def test_territory_ids_are_real_scenario_territories(self) -> None:
        state, _config, _defines = create_us_scenario()
        org = state.organizations[state.player_org_id]  # type: ignore[index]
        for tid in org.territory_ids:
            assert tid in state.territories, (
                f"org territory_id {tid!r} names no real territory in this scenario"
            )


class TestPresenceEdgesMaterialize:
    """``WorldState.to_graph()`` must derive real PRESENCE edges from the
    org's ``territory_ids`` (world_state.py:698-704) -- the structural fact
    ``game.fog.reach.organizing_reach``'s first hop depends on."""

    def test_presence_edges_exist_in_graph(self) -> None:
        state, _config, _defines = create_us_scenario()
        graph = state.to_graph()
        org = state.organizations[state.player_org_id]  # type: ignore[index]

        presence_targets = {
            edge.target_id
            for edge in graph.query_edges(edge_type=EdgeType.PRESENCE.value)
            if edge.source_id == state.player_org_id
        }
        assert presence_targets == set(org.territory_ids)


class TestSeedsRealBusinesses:
    """ADR086: ``us_nationwide`` seeds QCEW-sourced ``Business`` NPCs the player
    can see and MOBILIZE against, sized from REAL BLS private-sector employment."""

    def test_business_employment_matches_the_seed_artifact(self) -> None:
        state, _config, _defines = create_us_scenario()
        seeded = build_seeded_businesses("US", [])
        by_id = {o.id: o for o in state.organizations.values()}
        for biz_id, expected in seeded.items():
            assert biz_id in by_id, f"seeded business {biz_id} missing from scenario"
            assert by_id[biz_id].employment_count == expected.employment_count
            assert by_id[biz_id].employment_count > 0

    def test_businesses_share_a_player_territory(self) -> None:
        """MOBILIZE eligibility + fog reach need the businesses to live in a
        territory the player org is present in (``get_mobilize_targets`` walks
        the player's ``territory_ids``)."""
        state, _config, _defines = create_us_scenario()
        player = state.organizations[state.player_org_id]  # type: ignore[index]
        player_territories = set(player.territory_ids)
        businesses = [o for o in state.organizations.values() if o.org_type == OrgType.BUSINESS]
        assert businesses, "no Business orgs seeded"
        for biz in businesses:
            assert player_territories & set(biz.territory_ids), (
                f"business {biz.id} shares no territory with the player org"
            )


class TestReturnsWorldStateTuple:
    def test_returns_worldstate_and_config_tuple(self) -> None:
        result = create_us_scenario()
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], WorldState)
