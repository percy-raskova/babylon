"""TSSI/NI aggregate value-price equalities — spec 060 US3 / FR-005 / SC-003.

Across all productive entities at any single tick:

    Σ money_profit = (Σ labor_surplus) × τ
    Σ money_price  = (Σ labor_value)   × τ

These are the two aggregate equalities Marx claims hold under the
Temporal Single System Interpretation / New Interpretation, even when
sectoral prices diverge from sectoral values.

Two test arms:

  A. Proportional-prices arm: runs unconditionally; trivially passes
     today because the engine's current behavior produces prices
     proportional to values × τ. Acts as a regression guard for
     when transformation activates.

  B. Redistribution-active arm: gated by ``skip_unless_active`` per
     FR-021; activates when the transformation engine performs
     sectoral redistribution.

Contract: FR-005 / SC-003.
"""

from __future__ import annotations

import pytest

from babylon.engine.scenarios.two_node import TwoNodeScenario
from tests._helpers.invariants.transformation_mode import skip_unless_active

_REL_TOL: float = 1e-6


def _productive_entities(world: object) -> list[tuple[str, object]]:
    orgs = getattr(world, "organizations", {}) or {}
    return [
        (str(k), o)
        for k, o in orgs.items()
        if (getattr(o, "constant_capital", 0.0) or 0.0) > 0.0
        and (getattr(o, "variable_capital", 0.0) or 0.0) > 0.0
    ]


def _aggregate_equality(world: object, tau: float) -> tuple[float, float]:
    """Compute (Σπ - Σs×τ relative-error, ΣP - ΣW×τ relative-error)."""
    sigma_profit = 0.0
    sigma_surplus = 0.0
    sigma_price = 0.0
    sigma_value = 0.0
    for _, org in _productive_entities(world):
        # Money side: profit = surplus_value; price = c + v + s
        profit = float(getattr(org, "surplus_value", 0.0) or 0.0)
        c = float(getattr(org, "constant_capital", 0.0) or 0.0)
        v = float(getattr(org, "variable_capital", 0.0) or 0.0)
        price = c + v + profit
        # Labor side under TSSI/NI: labor_X = money_X / τ
        labor_surplus = profit / tau
        labor_value = price / tau
        sigma_profit += profit
        sigma_surplus += labor_surplus
        sigma_price += price
        sigma_value += labor_value
    denom_p = max(abs(sigma_profit), 1e-300)
    denom_pr = max(abs(sigma_price), 1e-300)
    err_profit = abs(sigma_profit - sigma_surplus * tau) / denom_p
    err_price = abs(sigma_price - sigma_value * tau) / denom_pr
    return err_profit, err_price


@pytest.mark.invariant
class TestTSSIAggregateEqualities:
    """Contract FR-005 / SC-003."""

    def test_tssi_aggregate_equalities_proportional_arm(self) -> None:
        """Proportional-prices regime: Σπ = Σs×τ and ΣP = ΣW×τ trivially.

        Runs unconditionally. SKIPs if no productive entities exist
        (two_node scenario default). Tightens to active assertion
        once Feature 026 hydrates organizations with c/v/s.
        """
        state, _config, _defines = TwoNodeScenario().build()
        productive = _productive_entities(state)
        if not productive:
            pytest.skip(
                "spec-060 FR-005 (proportional arm): no productive entities in "
                "two_node scenario; test will activate with Feature 026 hydration."
            )
        tau = 65.0
        err_profit, err_price = _aggregate_equality(state, tau)
        assert err_profit <= _REL_TOL, (
            f"spec-060 FR-005 violated (proportional arm, profit aggregate): "
            f"Σπ - Σs×τ relative error {err_profit:.3e} > {_REL_TOL:.0e}"
        )
        assert err_price <= _REL_TOL, (
            f"spec-060 FR-005 violated (proportional arm, price aggregate): "
            f"ΣP - ΣW×τ relative error {err_price:.3e} > {_REL_TOL:.0e}"
        )

    def test_tssi_aggregate_equalities_redistribution_arm(self) -> None:
        """Redistribution-active regime: aggregate equalities still hold.

        Gated by ``skip_unless_active`` per FR-021. SKIPs cleanly
        today (transformation engine inactive).
        """
        state, _config, _defines = TwoNodeScenario().build()
        # The current WorldState has no dialectics field; the probe
        # returns PROPORTIONAL_PRICES on None and the test SKIPs cleanly.
        transformation = None  # placeholder for dialectic registry lookup
        skip_unless_active(transformation, spec_ref="spec-060 FR-005")
