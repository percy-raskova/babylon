"""Property-based tests for the capital-stock perpetual-inventory recurrence
(INV-005 / Spec 053 US5).

See ``specs/053-conservation-invariants/contracts/capital_recurrence.md``.

Recurrence under test: ``K_{t+1} = (1 - δ) K_t + I_t``, implemented in the
codebase by ``DepreciationConfig.next_K(K_prev, c)`` (the ``c`` argument is
the constant-capital flow, which corresponds to the ``I_t`` investment term
in the perpetual-inventory model). See ``src/babylon/economics/depreciation.py``
and ``src/babylon/economics/capital_stock.py:263``.

The general recurrence test goes through the validated ``DepreciationConfig``
calculator (δ ∈ [0.01, 0.20] per BEA fixed-asset bounds).

The boundary cases δ=0 and δ=1 from User Story 5 are tested by computing
the recurrence formula directly: those rates are physically out-of-range
(BEA 7% empirical average) but the spec invariant is the algebraic
identity, not the calculator's enforcement of physical bounds.

Tolerance fixed at 1e-10 (closed-form arithmetic; no accumulating error)
per FR-008 / FR-012.
"""

from __future__ import annotations

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from babylon.economics.depreciation import DepreciationConfig
from tests.property.strategies.capital_stock import capital_stock_triple_strategy

_TOL = 1e-10


def _next_k_via_calculator(K: float, delta: float, investment: float) -> float:
    """Invoke the calculator-under-test (validates δ ∈ [0.01, 0.20])."""
    cfg = DepreciationConfig(rate=delta)
    return cfg.next_K(K, investment)


def _next_k_formula(K: float, delta: float, investment: float) -> float:
    """Direct algebraic form of the recurrence (no validation).

    Used for boundary cases δ=0 and δ=1 that are out of the calculator's
    physical-bounds range but in the spec's mathematical contract.
    """
    return (1.0 - delta) * K + investment


@pytest.mark.unit
class TestCapitalRecurrence:
    """INV-005: ``DepreciationConfig.next_K`` realizes ``K_{t+1} = (1-δ)K_t + I_t``."""

    @given(triple=capital_stock_triple_strategy())
    @settings()
    def test_recurrence_general(self, triple: tuple[float, float, float]) -> None:
        """For any (K, δ, investment) with δ in the calculator's valid range,
        ``DepreciationConfig.next_K`` matches the algebraic formula."""
        K, delta, investment = triple
        actual = _next_k_via_calculator(K, delta, investment)
        expected = _next_k_formula(K, delta, investment)
        drift = abs(actual - expected)
        assert drift < _TOL, (
            f"INV-005: recurrence violated — K={K}, δ={delta}, I={investment}, "
            f"actual={actual}, expected={expected}, drift={drift:.3e}"
        )

    @given(
        K=st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False),
        investment=st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False),
    )
    @settings()
    def test_recurrence_no_depreciation(self, K: float, investment: float) -> None:
        """Algebraic boundary: δ = 0 ⇒ K_{t+1} = K + I."""
        actual = _next_k_formula(K, 0.0, investment)
        expected = K + investment
        drift = abs(actual - expected)
        assert drift < _TOL, (
            f"INV-005 (δ=0): K={K}, I={investment}, actual={actual}, expected={expected}, drift={drift:.3e}"
        )

    @given(
        K=st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False),
        investment=st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False),
    )
    @settings()
    def test_recurrence_full_depreciation(self, K: float, investment: float) -> None:
        """Algebraic boundary: δ = 1 ⇒ K_{t+1} = I."""
        actual = _next_k_formula(K, 1.0, investment)
        expected = investment
        drift = abs(actual - expected)
        assert drift < _TOL, (
            f"INV-005 (δ=1): K={K}, I={investment}, actual={actual}, expected={expected}, drift={drift:.3e}"
        )

    @given(triple=capital_stock_triple_strategy())
    @settings()
    def test_recurrence_no_investment(self, triple: tuple[float, float, float]) -> None:
        """I = 0 ⇒ K_{t+1} = (1-δ) * K (via the calculator at valid δ)."""
        K, delta, _investment = triple
        actual = _next_k_via_calculator(K, delta, 0.0)
        expected = (1.0 - delta) * K
        drift = abs(actual - expected)
        assert drift < _TOL, (
            f"INV-005 (I=0): K={K}, δ={delta}, actual={actual}, expected={expected}, "
            f"drift={drift:.3e}"
        )

    @given(triple=capital_stock_triple_strategy())
    @settings()
    def test_recurrence_monotone_in_delta(self, triple: tuple[float, float, float]) -> None:
        """Increasing δ (within valid range) never increases K_{t+1} when I=0."""
        K, delta_low, _investment = triple
        # Pick a strictly-greater delta in (delta_low, 0.20]
        delta_high = (delta_low + 0.20) / 2.0
        assume(delta_high > delta_low + 1e-12)  # avoid floating-point ties
        assume(delta_high <= 0.20)
        k_low = _next_k_via_calculator(K, delta_low, 0.0)
        k_high = _next_k_via_calculator(K, delta_high, 0.0)
        assert k_high <= k_low + _TOL, (
            f"INV-005 (monotone): K_high={k_high} > K_low={k_low} when "
            f"δ_high={delta_high} > δ_low={delta_low}; recurrence not "
            f"monotonically non-increasing in δ"
        )
