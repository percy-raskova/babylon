"""Property laws for the monetary anchor's honest-absence contract.

Design: docs/superpowers/specs/2026-07-18-vol3-money-scissors-design.md §3.3.

Contract clause 2 — absence is the NORMAL steady state, not an error path. Real
federal coverage runs 2010-2024; a canonical campaign runs 2010-2109, so the
anchor reads absent for roughly 85% of it. These are laws over the whole input
space rather than examples, because the absent branch is the default branch.

Contract clause 3 — pure, deterministic, no RNG, no clock, no I/O.
"""

from __future__ import annotations

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.domain.economics.credit.types import FictitiousCapitalStock
from babylon.domain.economics.distribution.types import SurplusValueDistribution
from babylon.domain.economics.monetary.anchor import (
    NATIONAL_FIPS,
    UNKNOWN_YEAR,
    fictitious_anchor,
    serviceability_anchor,
)
from babylon.domain.economics.tensor import NoDataSentinel

_MONEY = st.floats(
    min_value=0.0,
    max_value=1e12,
    allow_nan=False,
    allow_infinity=False,
)
_YEARS = st.integers(min_value=2010, max_value=2040)
_FIPS = st.integers(min_value=0, max_value=99999).map(lambda n: f"{n:05d}")


@st.composite
def _stocks(draw: st.DrawFn) -> FictitiousCapitalStock:
    """Any valid FictitiousCapitalStock."""
    return FictitiousCapitalStock(
        year=draw(_YEARS),
        government_debt=draw(_MONEY),
        corporate_equity=draw(_MONEY),
        corporate_debt=draw(_MONEY),
        household_debt=draw(_MONEY),
        derivatives_notional=draw(_MONEY),
    )


@st.composite
def _distributions(draw: st.DrawFn) -> SurplusValueDistribution:
    """Any valid SurplusValueDistribution (claims may exceed surplus)."""
    return SurplusValueDistribution(
        fips_code=draw(_FIPS),
        year=draw(_YEARS),
        total_surplus_produced=draw(_MONEY),
        interest_payments=draw(_MONEY),
        ground_rent=draw(_MONEY),
        taxes_on_surplus=draw(_MONEY),
    )


@pytest.mark.property
@given(real_output=st.one_of(st.none(), _MONEY))
@settings(max_examples=200, deadline=1000)
def test_absent_stock_is_always_an_honest_sentinel(real_output: float | None) -> None:
    """No stock: sentinel with a non-empty reason, whatever the other input."""
    result = fictitious_anchor(None, real_output)
    assert isinstance(result, NoDataSentinel)
    assert not isinstance(result, float)
    assert result.fips == NATIONAL_FIPS
    assert result.year == UNKNOWN_YEAR
    assert result.reason.strip() != ""


@pytest.mark.property
@given(stock=_stocks())
@settings(max_examples=200, deadline=1000)
def test_absent_real_output_is_always_an_honest_sentinel(
    stock: FictitiousCapitalStock,
) -> None:
    """No real output: sentinel carrying the stock's own year."""
    result = fictitious_anchor(stock, None)
    assert isinstance(result, NoDataSentinel)
    assert result.year == stock.year
    assert result.reason.strip() != ""


@pytest.mark.property
@given(stock=_stocks(), real_output=st.one_of(st.none(), _MONEY))
@settings(max_examples=300, deadline=1000)
def test_fictitious_anchor_is_finite_or_absent_never_between(
    stock: FictitiousCapitalStock,
    real_output: float | None,
) -> None:
    """Every outcome is either a finite float or a reasoned sentinel."""
    result = fictitious_anchor(stock, real_output)
    if isinstance(result, NoDataSentinel):
        assert result.reason.strip() != ""
    else:
        assert math.isfinite(result)


@pytest.mark.property
@given(distribution=st.one_of(st.none(), _distributions()))
@settings(max_examples=300, deadline=1000)
def test_serviceability_anchor_is_finite_or_absent_never_between(
    distribution: SurplusValueDistribution | None,
) -> None:
    """Every outcome is either a finite non-negative float or a reasoned sentinel."""
    result = serviceability_anchor(distribution)
    if isinstance(result, NoDataSentinel):
        assert result.reason.strip() != ""
    else:
        assert math.isfinite(result)
        assert result >= 0.0


@st.composite
def _zero_surplus_distributions(draw: st.DrawFn) -> SurplusValueDistribution:
    """A SurplusValueDistribution with the denominator forced to exactly zero.

    ``_distributions()`` skip-filtered down to this case would need Hypothesis
    to land on an exact ``0.0`` by chance from a ``[0.0, 1e12]`` float range —
    astronomically unlikely, and under this project's ``derandomize=True``
    default profile (``tests/conftest.py``, Constitution III.7) it is not a
    matter of luck varying run to run: it is the *same* miss every time,
    making the law permanently vacuous rather than merely flaky. Forcing the
    zero here keeps the law itself deterministic instead of relying on a
    deterministic non-hit.
    """
    return SurplusValueDistribution(
        fips_code=draw(_FIPS),
        year=draw(_YEARS),
        total_surplus_produced=0.0,
        interest_payments=draw(_MONEY),
        ground_rent=draw(_MONEY),
        taxes_on_surplus=draw(_MONEY),
    )


@pytest.mark.property
@given(distribution=_zero_surplus_distributions())
@settings(max_examples=200, deadline=1000)
def test_zero_surplus_is_always_absence_never_a_zero_burden(
    distribution: SurplusValueDistribution,
) -> None:
    """A zero denominator never resolves to a fabricated 0.0 burden."""
    result = serviceability_anchor(distribution)
    assert isinstance(result, NoDataSentinel)
    assert result.fips == distribution.fips_code
    assert result.year == distribution.year


@pytest.mark.property
@given(stock=_stocks(), real_output=_MONEY, distribution=_distributions())
@settings(max_examples=200, deadline=1000)
def test_anchors_are_pure_and_bit_deterministic(
    stock: FictitiousCapitalStock,
    real_output: float,
    distribution: SurplusValueDistribution,
) -> None:
    """Repeated calls on identical inputs return bit-identical results."""
    first_f = fictitious_anchor(stock, real_output)
    second_f = fictitious_anchor(stock, real_output)
    if isinstance(first_f, NoDataSentinel):
        assert isinstance(second_f, NoDataSentinel)
        assert first_f.reason == second_f.reason
    else:
        assert isinstance(second_f, float)
        assert first_f.hex() == second_f.hex()

    first_s = serviceability_anchor(distribution)
    second_s = serviceability_anchor(distribution)
    if isinstance(first_s, NoDataSentinel):
        assert isinstance(second_s, NoDataSentinel)
        assert first_s.reason == second_s.reason
    else:
        assert isinstance(second_s, float)
        assert first_s.hex() == second_s.hex()


@pytest.mark.property
@given(real_output=st.floats(min_value=0.01, max_value=1e12, allow_nan=False, allow_infinity=False))
@settings(max_examples=200, deadline=1000)
def test_zero_claims_is_always_absence_never_a_zero_anchor(real_output: float) -> None:
    """A zero numerator never resolves to a fabricated 0.0 log-anchor."""
    empty = FictitiousCapitalStock(
        year=2020,
        government_debt=0.0,
        corporate_equity=0.0,
        corporate_debt=0.0,
        household_debt=0.0,
    )
    result = fictitious_anchor(empty, real_output)
    assert isinstance(result, NoDataSentinel)
    assert result.year == 2020
