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
