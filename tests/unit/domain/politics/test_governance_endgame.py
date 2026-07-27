"""The governance endgame's pure math (P25 U12 commit D1, ADR139).

The SYRIZA fork (the-electoral-question.md §3.5): first ceiling contact in
office opens the fork; both arms are standing math. The arm and the rupture
geometry are pure functions of already-measured quantities — no RNG, no new
primitives, no adjudication (the endgame detector only observes, I.11).
"""

from __future__ import annotations

import pytest

from babylon.domain.politics.governance_endgame import (
    GovernanceArm,
    RuptureGeometry,
    betrayal_crossed,
    dual_power_live,
    phi_share,
    resolve_governance_arm,
    rupture_geometry,
)


class TestPhiShare:
    """Φ-inflow as a share of measured surplus — D's Φ-starved-state predicate
    and E's periphery-mirror measure share this one function."""

    def test_share_is_the_plain_ratio(self) -> None:
        assert phi_share(25.0, 100.0) == pytest.approx(0.25)

    def test_no_measured_surplus_reads_as_zero_share(self) -> None:
        # Honest absence: a sovereign with no measured surplus has NO rent
        # cushion — share 0.0, not a fabricated ratio or an exception.
        assert phi_share(10.0, 0.0) == 0.0
        assert phi_share(0.0, 0.0) == 0.0


class TestBetrayalCrossed:
    """b(c) = Σgap crossing ``betrayal_threshold`` — the SYRIZA-voter curve."""

    def test_crossing_at_and_above_threshold(self) -> None:
        assert betrayal_crossed(1.0, 1.0)
        assert betrayal_crossed(1.5, 1.0)

    def test_below_threshold_holds(self) -> None:
        assert not betrayal_crossed(0.99, 1.0)

    def test_nonpositive_threshold_never_crosses(self) -> None:
        # A disabled threshold (0.0) is a mod switch, not an always-fire.
        assert not betrayal_crossed(5.0, 0.0)


class TestDualPowerLive:
    """The @17.5 structural predicate read live: >= 2 active claimants on any
    territory in the governing sovereign's claimed set."""

    def test_two_active_claimants_is_dual_power(self) -> None:
        claims = {"T001": (("SOV_A", 0.6), ("ORG_COMMUNE", 0.3))}
        assert dual_power_live(claims)

    def test_single_claimant_is_not(self) -> None:
        claims = {"T001": (("SOV_A", 0.6),), "T002": (("SOV_A", 1.0),)}
        assert not dual_power_live(claims)

    def test_zero_control_rows_do_not_count(self) -> None:
        claims = {"T001": (("SOV_A", 0.6), ("ORG_COMMUNE", 0.0))}
        assert not dual_power_live(claims)

    def test_empty_mapping_is_not_dual_power(self) -> None:
        assert not dual_power_live({})


class TestResolveGovernanceArm:
    """RUPTURE requires the organs AND an uncaptured party; everything else
    administers the veto (SYRIZA held no organs — capitulation was the
    standing math, not a moral failure)."""

    def test_no_organs_capitulates(self) -> None:
        arm = resolve_governance_arm(
            institutional_pull=0.0, capture_threshold=0.5, organs_live=False
        )
        assert arm is GovernanceArm.CAPITULATE

    def test_captured_party_capitulates_even_with_organs(self) -> None:
        arm = resolve_governance_arm(
            institutional_pull=0.7, capture_threshold=0.5, organs_live=True
        )
        assert arm is GovernanceArm.CAPITULATE

    def test_uncaptured_party_with_organs_ruptures(self) -> None:
        arm = resolve_governance_arm(
            institutional_pull=0.2, capture_threshold=0.5, organs_live=True
        )
        assert arm is GovernanceArm.RUPTURE

    def test_capture_boundary_is_inclusive(self) -> None:
        # AT the threshold = captured (Michels drift has done its work).
        arm = resolve_governance_arm(
            institutional_pull=0.5, capture_threshold=0.5, organs_live=True
        )
        assert arm is GovernanceArm.CAPITULATE


class TestRuptureGeometry:
    """On the rupture arm (organs already live by construction): the synthesis
    window needs bridges AND the Φ-starved state; anything less is the
    Allende geometry."""

    def test_bridges_and_starved_state_open_the_synthesis_window(self) -> None:
        geometry = rupture_geometry(bridges_present=True, phi_starved=True)
        assert geometry is RuptureGeometry.SYNTHESIS

    def test_no_bridges_is_allende(self) -> None:
        assert rupture_geometry(bridges_present=False, phi_starved=True) is (
            RuptureGeometry.ALLENDE
        )

    def test_rent_cushioned_state_is_allende(self) -> None:
        # A state still fed by Φ can afford its own repression: the organs
        # face the intact machinery (UP faced exactly this).
        assert rupture_geometry(bridges_present=True, phi_starved=False) is (
            RuptureGeometry.ALLENDE
        )
