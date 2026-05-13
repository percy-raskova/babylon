"""Distribution system tests (T059 / FR-032 / FR-033)."""

from __future__ import annotations

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.engine.systems.distribution import (
    DistributionSplit,
    split_surplus_to_pirt,
)


@pytest.mark.cross_scale
class TestDistributionSplit:
    def test_default_rates_round_to_s(self) -> None:
        s = 100.0
        out = split_surplus_to_pirt(s=s)
        assert math.isclose(out.p + out.i + out.r + out.t, s, abs_tol=1e-10)

    def test_zero_surplus_zero_split(self) -> None:
        out = split_surplus_to_pirt(s=0.0)
        assert out.p == out.i == out.r == out.t == 0.0

    def test_p_is_residual(self) -> None:
        s = 100.0
        out = split_surplus_to_pirt(s=s, interest_rate=0.10, rent_rate=0.20, tax_rate=0.30)
        assert out.t == 30.0
        assert out.r == 20.0
        assert out.i == 10.0
        assert out.p == 40.0

    def test_negative_s_routed_entirely_to_p(self) -> None:
        """Defensive: negative surplus does not split; conservation preserved."""
        out = split_surplus_to_pirt(s=-5.0)
        assert out.p == -5.0
        assert out.i == out.r == out.t == 0.0

    def test_rejects_rate_above_one(self) -> None:
        with pytest.raises(ValueError):
            split_surplus_to_pirt(s=100.0, interest_rate=1.5)

    def test_rejects_negative_rate(self) -> None:
        with pytest.raises(ValueError):
            split_surplus_to_pirt(s=100.0, rent_rate=-0.1)

    def test_rejects_sum_above_one(self) -> None:
        with pytest.raises(ValueError, match="exceeds 1.0"):
            split_surplus_to_pirt(s=100.0, interest_rate=0.5, rent_rate=0.4, tax_rate=0.4)


@pytest.mark.cross_scale
@pytest.mark.property
class TestDistributionSplitPropertyBased:
    """FR-032/FR-033 conservation under Hypothesis-generated inputs."""

    @given(
        s=st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False),
        i_rate=st.floats(min_value=0.0, max_value=0.3, allow_nan=False),
        r_rate=st.floats(min_value=0.0, max_value=0.3, allow_nan=False),
        t_rate=st.floats(min_value=0.0, max_value=0.3, allow_nan=False),
    )
    @settings(max_examples=200, deadline=1000)
    def test_conservation_holds_for_any_rates_below_sum_1(
        self, s: float, i_rate: float, r_rate: float, t_rate: float
    ) -> None:
        out = split_surplus_to_pirt(s=s, interest_rate=i_rate, rent_rate=r_rate, tax_rate=t_rate)
        assert math.isclose(out.p + out.i + out.r + out.t, s, abs_tol=max(1e-9, abs(s) * 1e-12))
        assert isinstance(out, DistributionSplit)
