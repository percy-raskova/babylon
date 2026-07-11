"""Property test: geometric weekly depreciation inverse identity (T035).

For any annual rate ``r`` in [0, 1):
    (1 - delta_weekly(r))^52 ≈ 1 - r  to within 1e-12

Same identity for :func:`alpha_weekly`.
"""

from __future__ import annotations

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.domain.economics.geometric_depreciation import alpha_weekly, delta_weekly


@pytest.mark.cross_scale
@pytest.mark.property
@given(annual=st.floats(min_value=0.0, max_value=0.999, allow_nan=False, allow_infinity=False))
@settings(max_examples=200, deadline=1000)
def test_delta_weekly_inverse_identity(annual: float) -> None:
    d_weekly = delta_weekly(annual)
    reconstructed_annual = 1.0 - (1.0 - d_weekly) ** 52
    assert math.isclose(reconstructed_annual, annual, abs_tol=1e-12)


@pytest.mark.cross_scale
@pytest.mark.property
@given(annual=st.floats(min_value=0.0, max_value=0.999, allow_nan=False, allow_infinity=False))
@settings(max_examples=200, deadline=1000)
def test_alpha_weekly_inverse_identity(annual: float) -> None:
    a_weekly = alpha_weekly(annual)
    reconstructed_annual = 1.0 - (1.0 - a_weekly) ** 52
    assert math.isclose(reconstructed_annual, annual, abs_tol=1e-12)
