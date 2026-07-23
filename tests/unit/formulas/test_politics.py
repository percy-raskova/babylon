"""Property laws for the pure politics kernel (P25 U7, ADR133).

The program's behavioral contracts in pure form, provable before any system
wiring exists: L-VALVE (hope suppresses organizing, monotone in valve
strength), L-CEILING (the social wage never exceeds measured surplus — reform
routes value, never mints it), L-HOPE-MATERIAL (no hope without a promise
trace: H = 0 whenever no platform improves the counterfactual P(S|A)), and
L-PRZ (Przeworski-Sprague: platform breadth trades off against mean base
alignment).
"""

import pytest

from babylon.formulas.politics import (
    counterfactual_hope_gain,
    delivery_gap,
    delivery_ratio,
    hope_field,
    interest_fit,
    platform_vector,
    sw_deliverable,
    valve_multiplier,
)


class TestLValve:
    """L-VALVE: conversion x= (1 - v*H); dConv/dH <= 0, monotone in v."""

    def test_multiplier_decreases_monotonically_in_hope(self) -> None:
        hopes = [0.0, 0.2, 0.5, 0.8, 1.0]
        multipliers = [valve_multiplier(h, valve_strength=0.6) for h in hopes]
        assert multipliers == sorted(multipliers, reverse=True)

    def test_multiplier_is_monotone_in_valve_strength(self) -> None:
        strengths = [0.0, 0.3, 0.6, 1.0]
        multipliers = [valve_multiplier(0.5, valve_strength=v) for v in strengths]
        assert multipliers == sorted(multipliers, reverse=True)

    def test_zero_hope_never_throttles(self) -> None:
        assert valve_multiplier(0.0, valve_strength=1.0) == 1.0

    def test_saturated_hope_at_full_strength_halts_conversion(self) -> None:
        assert valve_multiplier(1.0, valve_strength=1.0) == 0.0

    def test_multiplier_never_negative_or_amplifying(self) -> None:
        for h in (0.0, 0.5, 1.0):
            for v in (0.0, 0.5, 1.0):
                assert 0.0 <= valve_multiplier(h, valve_strength=v) <= 1.0


class TestLCeiling:
    """L-CEILING: SW_delivered <= t_claim + phi_slice - debt_service, and never negative."""

    def test_delivery_capped_by_the_funding_identity(self) -> None:
        delivered = sw_deliverable(promised=100.0, t_claim=30.0, phi_slice=20.0, debt_service=10.0)
        assert delivered == 40.0  # min(100, 30+20-10)

    def test_full_delivery_when_funded(self) -> None:
        assert sw_deliverable(promised=25.0, t_claim=30.0, phi_slice=20.0, debt_service=0.0) == 25.0

    def test_delivery_never_negative_even_under_debt_burden(self) -> None:
        assert sw_deliverable(promised=50.0, t_claim=5.0, phi_slice=0.0, debt_service=30.0) == 0.0

    def test_ceiling_law_holds_across_a_sweep(self) -> None:
        # Politics routes value, never mints it: delivered <= funded, always.
        for promised in (0.0, 10.0, 200.0):
            for t in (0.0, 25.0):
                for phi in (0.0, 15.0):
                    for debt in (0.0, 12.0, 60.0):
                        delivered = sw_deliverable(
                            promised=promised, t_claim=t, phi_slice=phi, debt_service=debt
                        )
                        assert delivered <= max(0.0, t + phi - debt) + 1e-12
                        assert delivered <= promised

    def test_delivery_ratio_bounds_and_empty_promise(self) -> None:
        assert delivery_ratio(delivered=40.0, promised=100.0) == pytest.approx(0.4)
        assert (
            delivery_ratio(delivered=0.0, promised=0.0) == 1.0
        )  # nothing promised, nothing betrayed

    def test_delivery_gap_is_promise_minus_delivery(self) -> None:
        assert delivery_gap(promised=100.0, delivered=40.0) == pytest.approx(60.0)
        assert delivery_gap(promised=40.0, delivered=40.0) == 0.0


class TestLHopeMaterial:
    """L-HOPE-MATERIAL: H = 0 whenever no platform improves counterfactual P(S|A)."""

    def test_no_promise_no_hope(self) -> None:
        # A platform whose promised overlay does not raise P(S|A) contributes zero.
        assert hope_field(((0.8, 0.9, 0.0),)) == 0.0

    def test_worsening_platform_contributes_zero_not_negative(self) -> None:
        assert hope_field(((0.8, 0.9, -0.2),)) == 0.0

    def test_hope_is_allegiance_and_viability_weighted(self) -> None:
        h = hope_field(((0.5, 0.4, 0.3),))
        assert h == pytest.approx(0.5 * 0.4 * 0.3)

    def test_counterfactual_gain_is_the_sigmoid_delta(self) -> None:
        gain = counterfactual_hope_gain(
            wealth=90.0, subsistence=100.0, promised_transfer=20.0, steepness_k=0.1
        )
        assert gain > 0.0
        no_gain = counterfactual_hope_gain(
            wealth=90.0, subsistence=100.0, promised_transfer=0.0, steepness_k=0.1
        )
        assert no_gain == 0.0

    def test_empty_terrain_reads_zero(self) -> None:
        assert hope_field(()) == 0.0


class TestLPrz:
    """L-PRZ: platform breadth up => mean base interest-alignment down."""

    def test_broadening_dilutes_the_original_base(self) -> None:
        core_interest = (1.0, 0.0)
        orthogonal_interest = (0.0, 1.0)
        narrow = platform_vector(((1.0, core_interest),), donor_terms=(), donor_weight=0.0)
        broad = platform_vector(
            ((1.0, core_interest), (1.0, orthogonal_interest)), donor_terms=(), donor_weight=0.0
        )
        assert interest_fit(core_interest, broad) < interest_fit(core_interest, narrow)

    def test_donor_pull_drags_platform_from_base(self) -> None:
        base_interest = (1.0, 0.0)
        donor_interest = (0.0, 1.0)
        without = platform_vector(((1.0, base_interest),), donor_terms=(), donor_weight=0.0)
        with_donor = platform_vector(
            ((1.0, base_interest),), donor_terms=((1.0, donor_interest),), donor_weight=0.5
        )
        assert interest_fit(base_interest, with_donor) < interest_fit(base_interest, without)

    def test_platform_is_normalized(self) -> None:
        vec = platform_vector(((2.0, (3.0, 4.0)),), donor_terms=(), donor_weight=0.0)
        assert sum(x * x for x in vec) == pytest.approx(1.0)

    def test_empty_platform_is_zero_vector(self) -> None:
        assert platform_vector((), donor_terms=(), donor_weight=0.0) == ()


class TestAllegianceDrift:
    """U8 (ADR134): the §2.2 drift law in pure form — align/media/contact
    pull toward a party, betrayal pushes away; absent producers contribute
    exactly zero through their defaulted terms."""

    def test_sign_structure(self) -> None:
        from babylon.formulas.politics import allegiance_drift

        pull = allegiance_drift(fit=0.8, contact=1.0, align_rate=0.05, contact_rate=0.03)
        assert pull == pytest.approx(0.05 * 0.8 + 0.03 * 1.0)
        pushed = allegiance_drift(
            fit=0.0,
            contact=0.0,
            align_rate=0.05,
            contact_rate=0.03,
            delivery_gap_term=2.0,
            betrayal_rate=0.1,
        )
        assert pushed == pytest.approx(-0.2)

    def test_absent_producers_are_exact_zeros(self) -> None:
        """Media (ISA_COMM) and betrayal (U9 delivery gaps) default to zero
        terms — honest absence, never a fabricated weight."""
        from babylon.formulas.politics import allegiance_drift

        assert allegiance_drift(
            fit=0.5, contact=0.0, align_rate=0.0, contact_rate=0.0
        ) == pytest.approx(0.0)


class TestApplyAllegianceDrift:
    """Mass discipline: the allegiance distribution over (parties ∪
    abstention) is a partition of the class's political existence —
    deltas move mass, they never mint or destroy it."""

    def test_conserves_unit_mass(self) -> None:
        from babylon.formulas.politics import apply_allegiance_drift

        parties, abstention = apply_allegiance_drift(allegiance=(0.2, 0.1), deltas=(0.05, -0.02))
        assert sum(parties) + abstention == pytest.approx(1.0)
        assert parties[0] == pytest.approx(0.25)
        assert parties[1] == pytest.approx(0.08)

    def test_clamps_at_zero(self) -> None:
        from babylon.formulas.politics import apply_allegiance_drift

        parties, abstention = apply_allegiance_drift(allegiance=(0.1,), deltas=(-0.5,))
        assert parties == (0.0,)
        assert abstention == pytest.approx(1.0)

    def test_oversubscription_rescales_to_unit(self) -> None:
        from babylon.formulas.politics import apply_allegiance_drift

        parties, abstention = apply_allegiance_drift(allegiance=(0.7, 0.6), deltas=(0.2, 0.2))
        assert sum(parties) == pytest.approx(1.0)
        assert abstention == 0.0
        assert parties[0] > parties[1]  # relative order preserved

    def test_empty_party_set_is_all_abstention(self) -> None:
        from babylon.formulas.politics import apply_allegiance_drift

        parties, abstention = apply_allegiance_drift(allegiance=(), deltas=())
        assert parties == ()
        assert abstention == 1.0


class TestTurnoutShare:
    """The U10 turnout law: base x loyal_mass x hope - w*repression, clamped."""

    def test_full_loyalty_full_hope_no_repression_gives_base(self) -> None:
        from babylon.formulas.politics import turnout_share

        assert turnout_share(
            base_turnout=0.55,
            loyal_mass=1.0,
            hope=1.0,
            repression_faced=0.0,
            suppression_weight=0.2,
        ) == pytest.approx(0.55)

    def test_collapsed_hope_collapses_turnout(self) -> None:
        """The legitimation death spiral: no believed acquiescence
        arithmetic, nothing to vote for."""
        from babylon.formulas.politics import turnout_share

        assert turnout_share(0.55, 1.0, 0.0, 0.0, 0.2) == 0.0

    def test_suppression_subtracts_class_differentially(self) -> None:
        from babylon.formulas.politics import turnout_share

        base = turnout_share(0.8, 1.0, 1.0, 0.0, 0.5)
        suppressed = turnout_share(0.8, 1.0, 1.0, 0.4, 0.5)
        assert suppressed == pytest.approx(base - 0.5 * 0.4)
        assert suppressed < base

    def test_result_is_bounded_in_unit_interval(self) -> None:
        from babylon.formulas.politics import turnout_share

        # Over-suppression floors at 0, never negative.
        assert turnout_share(0.9, 1.0, 1.0, 1.0, 5.0) == 0.0
        # Gross over 1 (pathological inputs) clamps at 1.
        assert turnout_share(2.0, 1.0, 1.0, 0.0, 0.2) == 1.0

    def test_monotone_increasing_in_hope_and_loyalty(self) -> None:
        from babylon.formulas.politics import turnout_share

        lo = turnout_share(0.55, 0.3, 0.3, 0.1, 0.2)
        hi = turnout_share(0.55, 0.9, 0.9, 0.1, 0.2)
        assert hi > lo


class TestCompetitiveness:
    """Competitiveness = 1 - (share1 - share2), normalized; feeds legitimation."""

    def test_exact_tie_is_maximally_competitive(self) -> None:
        from babylon.formulas.politics import competitiveness

        assert competitiveness([0.5, 0.5]) == pytest.approx(1.0)

    def test_blowout_is_barely_competitive(self) -> None:
        from babylon.formulas.politics import competitiveness

        assert competitiveness([0.95, 0.05]) == pytest.approx(0.1)

    def test_normalizes_arbitrary_scale(self) -> None:
        from babylon.formulas.politics import competitiveness

        # 60/40 split regardless of absolute magnitude.
        assert competitiveness([600.0, 400.0]) == pytest.approx(0.8)

    def test_fewer_than_two_contestants_is_no_contest(self) -> None:
        from babylon.formulas.politics import competitiveness

        assert competitiveness([1.0]) == 0.0
        assert competitiveness([]) == 0.0
        assert competitiveness([0.0, 0.0]) == 0.0

    def test_ignores_trailing_also_rans(self) -> None:
        """Only the top-two margin sets competitiveness (FPTP is winner vs
        runner-up)."""
        from babylon.formulas.politics import competitiveness

        assert competitiveness([0.5, 0.3, 0.2]) == pytest.approx(0.8)
