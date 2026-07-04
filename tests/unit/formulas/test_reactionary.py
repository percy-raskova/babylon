"""Spec-071: reactionary formula unit tests.

The fascism branch of the George Jackson bifurcation (Constitution I.4).
Pure, deterministic formulas — the mathematical core of the reactionary
subject.
"""

from __future__ import annotations

import pytest

from babylon.formulas.consciousness_routing import (
    apply_fr_gate,
    assimilation_ratio,
    ideological_contestation,
    normalize_to_simplex,
)
from babylon.formulas.reactionary import (
    calculate_defection_probability,
    calculate_entitlement_effective,
    calculate_fascist_pull,
    calculate_spontaneous_riot_risk,
)

pytestmark = pytest.mark.math


class TestFascistPull:
    def test_zero_agitation_zero_pull(self) -> None:
        # Hegemony: no crisis agitation -> no fascist pull (crisis-gated).
        assert calculate_fascist_pull(agitation=0.0, entitlement=0.8, solidarity=0.0) == 0.0

    def test_solidarity_suppresses_pull(self) -> None:
        no_sol = calculate_fascist_pull(agitation=2.0, entitlement=0.8, solidarity=0.0)
        with_sol = calculate_fascist_pull(agitation=2.0, entitlement=0.8, solidarity=0.9)
        assert with_sol < no_sol

    def test_formula_matches_definition(self) -> None:
        # Fascist_Pull = Agitation * (Entitlement / (Solidarity + eps))
        eps = 0.1
        agitation, entitlement, solidarity = 2.0, 0.8, 0.3
        expected = agitation * (entitlement / (solidarity + eps))
        assert calculate_fascist_pull(
            agitation=agitation, entitlement=entitlement, solidarity=solidarity, epsilon=eps
        ) == pytest.approx(expected)

    def test_zero_solidarity_no_div_by_zero(self) -> None:
        # eps guard: solidarity=0 must not raise.
        val = calculate_fascist_pull(agitation=1.0, entitlement=0.5, solidarity=0.0, epsilon=0.1)
        assert val == pytest.approx(1.0 * (0.5 / 0.1))

    def test_higher_entitlement_higher_pull(self) -> None:
        low = calculate_fascist_pull(agitation=1.0, entitlement=0.2, solidarity=0.0)
        high = calculate_fascist_pull(agitation=1.0, entitlement=0.8, solidarity=0.0)
        assert high > low


class TestDefectionProbability:
    def test_sigmoid_midpoint(self) -> None:
        # chauvinism == discipline -> 0.5
        assert calculate_defection_probability(chauvinism=0.5, discipline=0.5) == pytest.approx(0.5)

    def test_monotonic_in_chauvinism(self) -> None:
        lo = calculate_defection_probability(chauvinism=0.2, discipline=0.5)
        hi = calculate_defection_probability(chauvinism=0.9, discipline=0.5)
        assert hi > lo

    def test_bounded_probability(self) -> None:
        for chi in (0.0, 0.5, 1.0):
            p = calculate_defection_probability(chauvinism=chi, discipline=0.3)
            assert 0.0 <= p <= 1.0


class TestSpontaneousRiotRisk:
    def test_discipline_gates_volatility(self) -> None:
        # riot_risk = volatility * (1 - discipline)
        assert calculate_spontaneous_riot_risk(volatility=0.8, discipline=0.0) == pytest.approx(0.8)
        assert calculate_spontaneous_riot_risk(volatility=0.8, discipline=1.0) == pytest.approx(0.0)

    def test_zero_volatility_zero_risk(self) -> None:
        assert calculate_spontaneous_riot_risk(volatility=0.0, discipline=0.0) == 0.0

    def test_clamped_to_unit(self) -> None:
        # Even with out-of-range discipline the risk stays in [0, 1].
        assert 0.0 <= calculate_spontaneous_riot_risk(volatility=1.0, discipline=-0.5) <= 1.0


class TestEntitlementEffective:
    def test_baseline_passthrough(self) -> None:
        # With no crisis modifier, effective entitlement equals base.
        assert calculate_entitlement_effective(base_entitlement=0.8, threat=0.0) == pytest.approx(
            0.8
        )

    def test_threat_amplifies_entitlement(self) -> None:
        # A threatened stake reacts harder (>= base), clamped to 1.0.
        assert calculate_entitlement_effective(base_entitlement=0.8, threat=1.0) >= 0.8
        assert calculate_entitlement_effective(base_entitlement=0.8, threat=1.0) <= 1.0


class TestRLFSimplex:
    """ADR051 §9.4 constraints deferred to spec-071."""

    def test_normalize_sums_to_one_liberal_default(self) -> None:
        r, lib, f = normalize_to_simplex(0.0, 0.0, 0.0)
        assert (r, lib, f) == (0.0, 1.0, 0.0)  # all-zero -> pure liberal
        r, lib, f = normalize_to_simplex(0.2, 0.0, 0.3)
        assert r + lib + f == pytest.approx(1.0)
        assert lib == pytest.approx(0.5)  # residual to liberal

    def test_normalize_scales_down_when_over_one(self) -> None:
        r, lib, f = normalize_to_simplex(1.0, 1.0, 2.0)
        assert r + lib + f == pytest.approx(1.0)

    def test_assimilation_ratio(self) -> None:
        assert assimilation_ratio(0.3, 0.1) == pytest.approx(0.25)
        assert assimilation_ratio(0.0, 0.0) == 0.0

    def test_contestation_diagnostic_bounds(self) -> None:
        assert ideological_contestation(1.0, 0.0, 0.0) == pytest.approx(0.0)
        assert ideological_contestation(1 / 3, 1 / 3, 1 / 3) == pytest.approx(1.0)

    def test_contestation_permutation_symmetric(self) -> None:
        # Entropy cannot carry the Jackson asymmetry: (r,l,f) and (f,l,r)
        # give the same contestation. This is WHY the gate lives elsewhere.
        assert ideological_contestation(0.5, 0.3, 0.2) == pytest.approx(
            ideological_contestation(0.2, 0.3, 0.5)
        )

    def test_fr_gate_forbidden_by_default(self) -> None:
        # f->r forbidden unless all three preconditions hold.
        assert (
            apply_fr_gate(0.3, proletarianizing=True, adjacent_r=True, has_solidarity=False) == 0.0
        )
        assert (
            apply_fr_gate(0.3, proletarianizing=False, adjacent_r=True, has_solidarity=True) == 0.0
        )

    def test_fr_gate_open_when_all_hold(self) -> None:
        assert apply_fr_gate(
            0.3, proletarianizing=True, adjacent_r=True, has_solidarity=True
        ) == pytest.approx(0.3)
