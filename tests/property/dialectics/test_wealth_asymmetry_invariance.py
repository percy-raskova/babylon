"""Property test: wealth-asymmetry gaps are exactly numeraire-invariant.

In the spirit of ``tests/property/invariants/test_numeraire_invariance.py``
(spec-060): a dimensionless ratio of monetary quantities cannot depend on
the monetary unit. The wealth-asymmetry gap and balance divide by the pole
sum, so scaling BOTH poles by any ``k > 0`` must leave them invariant to
1e-12 relative tolerance — this is the structural reason the Lawverian
contradiction measure cannot saturate the way the old dollar-scale
accumulator did.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.formulas.contradiction import (
    calculate_wealth_asymmetry_balance,
    calculate_wealth_asymmetry_gap,
)

pytestmark = [pytest.mark.property, pytest.mark.math]

_REL_TOL = 1e-12

# Poles bounded away from the zero-guard so the ratio is well defined; k spans
# six orders of magnitude in each direction (cents ... millions-of-dollars).
_wealths = st.floats(min_value=1e-3, max_value=1e6, allow_nan=False, allow_infinity=False)
_scales = st.floats(min_value=1e-3, max_value=1e6, allow_nan=False, allow_infinity=False)


@given(a=_wealths, b=_wealths, k=_scales)
@settings(max_examples=200, deadline=None)
def test_gap_invariant_under_rescaling(a: float, b: float, k: float) -> None:
    base = calculate_wealth_asymmetry_gap(a, b)
    scaled = calculate_wealth_asymmetry_gap(a * k, b * k)
    assert scaled == pytest.approx(base, rel=_REL_TOL, abs=1e-15)


@given(a=_wealths, b=_wealths, k=_scales)
@settings(max_examples=200, deadline=None)
def test_balance_invariant_under_rescaling(a: float, b: float, k: float) -> None:
    base = calculate_wealth_asymmetry_balance(a, b)
    scaled = calculate_wealth_asymmetry_balance(a * k, b * k)
    assert scaled == pytest.approx(base, rel=_REL_TOL, abs=1e-15)


@given(a=_wealths, b=_wealths)
@settings(max_examples=200, deadline=None)
def test_gap_is_magnitude_of_balance(a: float, b: float) -> None:
    assert calculate_wealth_asymmetry_gap(a, b) == pytest.approx(
        abs(calculate_wealth_asymmetry_balance(a, b)), abs=1e-15
    )
