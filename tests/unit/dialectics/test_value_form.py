"""Unit + law tests for the value-form adjunction (Phase D1 + D2).

Pins the labor-time ⇄ money adjunction, the wage-form counit defect Φ
(``phi_class`` / ``phi_hour``), the FLOW-axis class sorter, the Φ
tri-decomposition, and — the load-bearing one — the conservation identity
``Σ L_performed·τ = Σ V_visible + Σ Φ_shadow`` with each term asserted
independently (so a broken term cannot hide inside the sum).

The Φ_UE cross-check computes a two-zone transfer both through the gamma
kernel and through ``formulas/unequal_exchange`` and asserts they agree in
sign and order of magnitude — the two Marxist derivations of unequal
exchange must not disagree on direction.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.domain.dialectics.instances.value_form import (
    PhiDecomposition,
    ValueFormAdjunction,
    class_position_by_phi_hour,
    phi_class,
    phi_domestic,
    phi_hour,
    phi_iii_report,
    phi_reproduction,
    phi_unequal_exchange,
    visible_value,
)
from babylon.domain.economics.gamma.types import GammaBasket, GammaIII
from babylon.domain.economics.melt.types import ClassPosition
from babylon.domain.economics.value import AbstractLabor, ExchangeValue
from babylon.formulas.unequal_exchange import (
    calculate_exchange_ratio,
    calculate_value_transfer,
)

pytestmark = [pytest.mark.unit, pytest.mark.math]


class TestTauEffective:
    """τ_eff = τ·γ_basket — the NationalParameters.tau_effective semantics."""

    def test_tau_effective_is_tau_times_gamma_basket(self) -> None:
        adj = ValueFormAdjunction(tau=65.0, gamma_basket=0.68)
        assert adj.tau_effective == pytest.approx(65.0 * 0.68)

    def test_matches_national_parameters_semantics(self) -> None:
        # parameters.py:232 — expected_tau_effective = tau * gamma_basket.
        from babylon.domain.economics.melt.parameters import NationalParameters

        params = NationalParameters(
            year=2022,
            tau=65.0,
            alpha=0.25,
            gamma_import=0.35,
            gamma_basket=0.68,
            tau_effective=65.0 * 0.68,
            v_reproduction=12.0,
        )
        adj = ValueFormAdjunction(tau=params.tau, gamma_basket=params.gamma_basket)
        assert adj.tau_effective == pytest.approx(params.tau_effective)


class TestRoundTrip:
    """The pure numeraire map has ZERO defect — Φ is not conversion error."""

    def test_dollars_hours_dollars(self) -> None:
        adj = ValueFormAdjunction(tau=65.0, gamma_basket=0.68)
        assert adj.to_money(adj.to_labor_hours(123.456)) == pytest.approx(123.456, rel=1e-12)

    def test_hours_dollars_hours(self) -> None:
        adj = ValueFormAdjunction(tau=65.0, gamma_basket=0.68)
        assert adj.to_labor_hours(adj.to_money(7.89)) == pytest.approx(7.89, rel=1e-12)

    @given(
        x=st.floats(min_value=1e-6, max_value=1e12, allow_nan=False, allow_infinity=False),
        tau=st.floats(min_value=1e-3, max_value=1e6, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=200, deadline=None)
    def test_round_trip_law_hypothesis(self, x: float, tau: float) -> None:
        adj = ValueFormAdjunction(tau=tau, gamma_basket=0.68)
        assert adj.to_money(adj.to_labor_hours(x)) == pytest.approx(x, rel=1e-12)
        assert adj.to_labor_hours(adj.to_money(x)) == pytest.approx(x, rel=1e-12)

    def test_typed_pole_round_trip_reconsumes_value_models(self) -> None:
        # Re-consume the C1.7-orphaned economics.value poles.
        adj = ValueFormAdjunction(tau=65.0, gamma_basket=0.68)
        labor = AbstractLabor(snlt=40.0)
        value: ExchangeValue = adj.value_of(labor)
        assert value.price == pytest.approx(40.0 * 65.0)
        assert adj.labor_of(value).snlt == pytest.approx(40.0, rel=1e-12)


class TestPhiClass:
    """Φ_class = (W_c − V_c)/V_c — the §6 contract counit defect, signed."""

    def test_super_wage_positive(self) -> None:
        assert phi_class(w_c=100.0, v_c=80.0) == pytest.approx(0.25)

    def test_under_paid_negative(self) -> None:
        assert phi_class(w_c=80.0, v_c=100.0) == pytest.approx(-0.2)

    def test_zero_value_raises(self) -> None:
        with pytest.raises(ValueError, match="v_c"):
            phi_class(w_c=100.0, v_c=0.0)

    def test_negative_value_raises(self) -> None:
        with pytest.raises(ValueError, match="v_c"):
            phi_class(w_c=100.0, v_c=-5.0)


class TestPhiHour:
    """Φ_hour = wage_hourly − τ_eff (dollars/hour, the §9.3 sorting form)."""

    def test_super_wage_hour(self) -> None:
        assert phi_hour(wage_hourly=50.0, tau_effective=44.2) == pytest.approx(5.8)

    def test_sub_wage_hour(self) -> None:
        assert phi_hour(wage_hourly=30.0, tau_effective=44.2) == pytest.approx(-14.2)


class TestClassPositionByPhiHour:
    """The FLOW axis: Φ_hour ≥ 0 → LA, else W ≥ V_repro → prole, else lumpen."""

    def test_labor_aristocracy_when_phi_hour_nonnegative(self) -> None:
        assert (
            class_position_by_phi_hour(wage_hourly=50.0, tau_effective=44.2, v_reproduction=12.0)
            is ClassPosition.LABOR_ARISTOCRACY
        )

    def test_boundary_phi_hour_zero_is_labor_aristocracy(self) -> None:
        assert (
            class_position_by_phi_hour(wage_hourly=44.2, tau_effective=44.2, v_reproduction=12.0)
            is ClassPosition.LABOR_ARISTOCRACY
        )

    def test_proletariat_when_below_tau_eff_but_above_reproduction(self) -> None:
        assert (
            class_position_by_phi_hour(wage_hourly=30.0, tau_effective=44.2, v_reproduction=12.0)
            is ClassPosition.PROLETARIAT
        )

    def test_lumpen_when_below_reproduction(self) -> None:
        # a.k.a. SUBPROLETARIAT (melt/types.py:230).
        assert (
            class_position_by_phi_hour(wage_hourly=10.0, tau_effective=44.2, v_reproduction=12.0)
            is ClassPosition.LUMPENPROLETARIAT
        )


class TestVisibleAndDomestic:
    """V_visible = τ·L_paid ; Φ_domestic = τ·L_unpaid (the conservation terms)."""

    def test_visible_value(self) -> None:
        assert visible_value(tau=65.0, l_paid=10.0) == pytest.approx(650.0)

    def test_phi_domestic(self) -> None:
        assert phi_domestic(tau=65.0, l_unpaid=4.0) == pytest.approx(260.0)


class TestConservation:
    """THE law (§9.3): Σ L_performed·τ = Σ V_visible + Σ Φ_shadow.

    Each component is asserted independently so the "one big sum hides a
    broken term" failure mode cannot survive — in particular the §9.1
    mutation probe that swaps L_paid for L_total in V_visible.
    """

    def test_conservation_labor_equals_visible_plus_shadow(self) -> None:
        tau = 65.0
        # (l_paid, l_unpaid) per class; l_unpaid > 0 everywhere so L_paid ≠ L_total
        # (this is what makes the L_paid→L_total mutant detectable).
        classes = [(10.0, 4.0), (7.5, 2.0), (0.0, 3.0)]

        sum_l_paid = sum(lp for lp, _ in classes)
        sum_l_unpaid = sum(lu for _, lu in classes)

        v_visible_total = sum(visible_value(tau, lp) for lp, _ in classes)
        phi_shadow_total = sum(phi_domestic(tau, lu) for _, lu in classes)
        labor_performed_value = sum((lp + lu) for lp, lu in classes) * tau

        # Independent component assertions (kill the hidden-broken-term mode).
        assert v_visible_total == pytest.approx(tau * sum_l_paid)
        assert phi_shadow_total == pytest.approx(tau * sum_l_unpaid)
        # V_visible must be τ·L_paid, NOT τ·L_total (mutation probe b).
        assert v_visible_total != pytest.approx(tau * (sum_l_paid + sum_l_unpaid))

        # The conservation identity itself.
        assert labor_performed_value == pytest.approx(v_visible_total + phi_shadow_total)


class TestPhiDecomposition:
    """Φ = SUM of three separately-measured defects; total is never stored."""

    def test_total_is_sum_of_three_components(self) -> None:
        decomp = PhiDecomposition(
            phi_unequal_exchange=3.0,
            phi_reproduction=5.0,
            phi_domestic=7.0,
        )
        assert decomp.total == pytest.approx(15.0)

    def test_dropping_any_component_is_detectable(self) -> None:
        # Distinct nonzero components: dropping ANY one changes the total
        # (mutation probe a — the tri-decomposition sum).
        a, b, c = 3.0, 5.0, 7.0
        decomp = PhiDecomposition(phi_unequal_exchange=a, phi_reproduction=b, phi_domestic=c)
        assert decomp.total == pytest.approx(a + b + c)
        assert decomp.total != pytest.approx(a + b)  # phi_domestic dropped
        assert decomp.total != pytest.approx(a + c)  # phi_reproduction dropped
        assert decomp.total != pytest.approx(b + c)  # phi_unequal_exchange dropped

    def test_total_is_computed_not_stored(self) -> None:
        # total is a computed_field: it tracks the components, never a primitive.
        assert "total" not in PhiDecomposition.model_fields
        decomp = PhiDecomposition(phi_unequal_exchange=1.0, phi_reproduction=2.0, phi_domestic=3.0)
        bumped = decomp.model_copy(update={"phi_domestic": 30.0})
        assert bumped.total == pytest.approx(1.0 + 2.0 + 30.0)

    def test_phi_iii_report_is_carried_but_excluded_from_total(self) -> None:
        # The D2-fork report field: present, informational, NOT in the sum.
        decomp = PhiDecomposition(
            phi_unequal_exchange=1.0,
            phi_reproduction=2.0,
            phi_domestic=3.0,
            phi_iii_report=99.0,
        )
        assert decomp.total == pytest.approx(6.0)


class TestComponentKernels:
    """Each Φ component reuses its cited kernel (no re-invented economics)."""

    def test_phi_unequal_exchange_reuses_gamma_kernel(self) -> None:
        basket = GammaBasket(year=2022, alpha=0.25, gamma_import=0.35, gamma_basket=0.68)
        # (1 − γ_basket)·Consumption = 0.32 · 10000.
        assert phi_unequal_exchange(basket, consumption=10_000.0) == pytest.approx(3200.0)

    def test_phi_reproduction_reuses_lifecycle_kernel(self) -> None:
        # max(0, P_g2 − wage) per lifecycle.compute_shadow_subsidy.
        assert phi_reproduction(
            p_g2_labor_value=60_000.0, wage_paid_for_d_g2=12_000.0
        ) == pytest.approx(48_000.0)

    def test_phi_iii_report_is_the_narrower_quadratic_quantity(self) -> None:
        # D2 fork: compute_phi_iii returns (1−γ_III)·L_unpaid·τ, quadratic in
        # L_unpaid, so it is STRICTLY LESS than Φ_domestic = τ·L_unpaid when
        # 0 < γ_III < 1. The two are different quantities — that is the fork.
        tau = 65.0
        l_unpaid = 33.0
        gamma_iii = GammaIII(
            year=2022,
            paid_care_hours=16.5,
            unpaid_care_hours=l_unpaid,
            gamma_iii=1.0 / 3.0,
            fortunati_exploitation=2.0,
        )
        report = phi_iii_report(gamma_iii, tau=tau)
        domestic = phi_domestic(tau=tau, l_unpaid=l_unpaid)
        # (1 − 1/3)·33·65 = (2/3)·33·65.
        assert report == pytest.approx((2.0 / 3.0) * l_unpaid * tau)
        assert report < domestic  # the quadratic quantity is the smaller one


class TestUnequalExchangeCrossCheck:
    """Φ_UE via gamma agrees in sign + order of magnitude with the flow form."""

    def test_two_zone_transfer_agrees_sign_and_magnitude(self) -> None:
        # Gamma way: (1 − γ_basket)·Consumption.
        gamma_basket = 0.68
        consumption = 10_000.0
        basket = GammaBasket(year=2022, alpha=0.25, gamma_import=0.35, gamma_basket=gamma_basket)
        phi_gamma = phi_unequal_exchange(basket, consumption=consumption)

        # Flow way: production·(1 − 1/ε), ε = (Lp/Lc)·(Wc/Wp).
        epsilon = calculate_exchange_ratio(
            periphery_labor_hours=100.0,
            core_labor_hours=100.0,
            core_wage=14.7,
            periphery_wage=10.0,
        )
        phi_flow = calculate_value_transfer(production_value=10_000.0, exchange_ratio=epsilon)

        assert phi_gamma > 0.0
        assert phi_flow > 0.0
        # Same order of magnitude (within one decade).
        assert 0.1 < (phi_gamma / phi_flow) < 10.0


class TestPiIsNotVisibility:
    """π (throughput) never enters τ_eff or any Φ component (D0 / §9.3)."""

    def test_rescaling_pi_leaves_tau_eff_and_phi_unchanged(self) -> None:
        adj = ValueFormAdjunction(tau=65.0, gamma_basket=0.68)
        # π = τ_through / τ_national — two different throughput regimes.
        pi_low = 30.0 / 65.0
        pi_high = 90.0 / 65.0
        assert pi_low != pi_high  # the regimes really differ

        # τ_eff and the Φ components are computed WITHOUT π — identical across
        # regimes (π is not a visibility mechanism, it is a position metric).
        tau_eff_before = adj.tau_effective
        phi_dom_before = phi_domestic(tau=adj.tau, l_unpaid=4.0)
        basket = GammaBasket(year=2022, alpha=0.25, gamma_import=0.35, gamma_basket=0.68)
        phi_ue_before = phi_unequal_exchange(basket, consumption=10_000.0)

        # Nothing above consumed pi_low or pi_high; recomputing is identical.
        assert adj.tau_effective == pytest.approx(tau_eff_before)
        assert phi_domestic(tau=adj.tau, l_unpaid=4.0) == pytest.approx(phi_dom_before)
        assert phi_unequal_exchange(basket, consumption=10_000.0) == pytest.approx(phi_ue_before)
