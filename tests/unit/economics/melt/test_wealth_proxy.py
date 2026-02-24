"""Unit tests for DefaultWealthProxyCalculator.estimate_lumpen_share.

Targeted mutation-killing tests for weighted precarity formula,
clamping logic, and missing data handling.
"""

from __future__ import annotations

from babylon.economics.melt.wealth_proxy import DefaultWealthProxyCalculator


class TestEstimateLumpenShareMutationKillers:
    """Targeted tests to kill mutation survivors in estimate_lumpen_share.

    Tests isolate each weight coefficient, verify exact arithmetic,
    and check clamping boundaries to catch mutmut operator swaps.
    """

    def test_missing_fips_returns_none(self) -> None:
        """Unknown FIPS code returns None (no data available)."""
        calc = DefaultWealthProxyCalculator(precarity_data={})
        result = calc.estimate_lumpen_share("99999", 2022)
        assert result is None

    def test_all_zeros_returns_zero(self) -> None:
        """All indicators at zero produces lumpen_share=0.0 exactly."""
        data = {
            "00000": {
                "u3_rate": 0.0,
                "u6_rate": 0.0,
                "pter_rate": 0.0,
                "nilf_want_work": 0.0,
                "incarceration_rate": 0.0,
            }
        }
        calc = DefaultWealthProxyCalculator(precarity_data=data)
        result = calc.estimate_lumpen_share("00000", 2022)
        assert result == 0.0

    def test_nilf_weight_isolated(self) -> None:
        """Only nilf_want_work=0.1, rest=0 → NILF_WEIGHT * 0.1."""
        data = {
            "00000": {
                "u3_rate": 0.0,
                "u6_rate": 0.0,
                "pter_rate": 0.0,
                "nilf_want_work": 0.1,
                "incarceration_rate": 0.0,
            }
        }
        calc = DefaultWealthProxyCalculator(precarity_data=data)
        result = calc.estimate_lumpen_share("00000", 2022)
        expected = DefaultWealthProxyCalculator.NILF_WEIGHT * 0.1
        assert result is not None
        assert abs(result - expected) < 1e-10

    def test_u6_gap_weight_isolated(self) -> None:
        """Only u3=0.04, u6=0.10 → U6_GAP_WEIGHT * (0.10 - 0.04)."""
        data = {
            "00000": {
                "u3_rate": 0.04,
                "u6_rate": 0.10,
                "pter_rate": 0.0,
                "nilf_want_work": 0.0,
                "incarceration_rate": 0.0,
            }
        }
        calc = DefaultWealthProxyCalculator(precarity_data=data)
        result = calc.estimate_lumpen_share("00000", 2022)
        expected = DefaultWealthProxyCalculator.U6_GAP_WEIGHT * (0.10 - 0.04)
        assert result is not None
        assert abs(result - expected) < 1e-10

    def test_incarceration_weight_isolated(self) -> None:
        """Only incarceration=0.1 → INCARCERATION_WEIGHT * 0.1."""
        data = {
            "00000": {
                "u3_rate": 0.0,
                "u6_rate": 0.0,
                "pter_rate": 0.0,
                "nilf_want_work": 0.0,
                "incarceration_rate": 0.1,
            }
        }
        calc = DefaultWealthProxyCalculator(precarity_data=data)
        result = calc.estimate_lumpen_share("00000", 2022)
        expected = DefaultWealthProxyCalculator.INCARCERATION_WEIGHT * 0.1
        assert result is not None
        assert abs(result - expected) < 1e-10

    def test_pter_weight_with_half_factor(self) -> None:
        """Only pter=0.10 → PTER_WEIGHT * 0.10 * 0.5."""
        data = {
            "00000": {
                "u3_rate": 0.0,
                "u6_rate": 0.0,
                "pter_rate": 0.10,
                "nilf_want_work": 0.0,
                "incarceration_rate": 0.0,
            }
        }
        calc = DefaultWealthProxyCalculator(precarity_data=data)
        result = calc.estimate_lumpen_share("00000", 2022)
        expected = DefaultWealthProxyCalculator.PTER_WEIGHT * 0.10 * 0.5
        assert result is not None
        assert abs(result - expected) < 1e-10

    def test_all_indicators_combined_exact(self) -> None:
        """Known values produce exact weighted sum."""
        data = {
            "00000": {
                "u3_rate": 0.04,
                "u6_rate": 0.10,
                "pter_rate": 0.05,
                "nilf_want_work": 0.03,
                "incarceration_rate": 0.02,
            }
        }
        calc = DefaultWealthProxyCalculator(precarity_data=data)
        result = calc.estimate_lumpen_share("00000", 2022)
        expected = (
            0.4 * 0.03  # NILF_WEIGHT * nilf
            + 0.3 * (0.10 - 0.04)  # U6_GAP_WEIGHT * gap
            + 0.2 * 0.02  # INCARCERATION_WEIGHT * incarceration
            + 0.1 * 0.05 * 0.5  # PTER_WEIGHT * pter * 0.5
        )
        assert result is not None
        assert abs(result - expected) < 1e-10

    def test_negative_u6_gap(self) -> None:
        """u3 > u6 produces negative gap term, reducing share."""
        data = {
            "00000": {
                "u3_rate": 0.10,
                "u6_rate": 0.05,
                "pter_rate": 0.0,
                "nilf_want_work": 0.0,
                "incarceration_rate": 0.0,
            }
        }
        calc = DefaultWealthProxyCalculator(precarity_data=data)
        result = calc.estimate_lumpen_share("00000", 2022)
        expected = DefaultWealthProxyCalculator.U6_GAP_WEIGHT * (0.05 - 0.10)
        assert result is not None
        assert abs(result - expected) < 1e-10

    def test_clamped_below_50pct_unchanged(self) -> None:
        """share=0.03 (well below 0.5) → returns 0.03 unchanged."""
        data = {
            "00000": {
                "u3_rate": 0.04,
                "u6_rate": 0.10,
                "pter_rate": 0.0,
                "nilf_want_work": 0.0,
                "incarceration_rate": 0.0,
            }
        }
        calc = DefaultWealthProxyCalculator(precarity_data=data)
        result = calc.estimate_lumpen_share("00000", 2022)
        assert result is not None
        assert result < 0.50
        # Exact: U6_GAP_WEIGHT * 0.06 = 0.3 * 0.06 = 0.018
        assert abs(result - 0.018) < 1e-10

    def test_clamped_at_exactly_50pct(self) -> None:
        """Inputs yielding exactly 0.5 → returns 0.5."""
        # NILF_WEIGHT=0.4, so nilf=1.25 → 0.4*1.25=0.5
        data = {
            "00000": {
                "u3_rate": 0.0,
                "u6_rate": 0.0,
                "pter_rate": 0.0,
                "nilf_want_work": 1.25,
                "incarceration_rate": 0.0,
            }
        }
        calc = DefaultWealthProxyCalculator(precarity_data=data)
        result = calc.estimate_lumpen_share("00000", 2022)
        assert result == 0.50

    def test_clamped_above_50pct(self) -> None:
        """Large inputs producing >0.5 → clamped to 0.5."""
        data = {
            "00000": {
                "u3_rate": 0.0,
                "u6_rate": 0.0,
                "pter_rate": 0.0,
                "nilf_want_work": 2.0,  # 0.4 * 2.0 = 0.8
                "incarceration_rate": 0.0,
            }
        }
        calc = DefaultWealthProxyCalculator(precarity_data=data)
        result = calc.estimate_lumpen_share("00000", 2022)
        assert result == 0.50

    def test_default_zero_for_missing_fields(self) -> None:
        """Data dict with missing keys defaults to 0.0 for each."""
        data = {"00000": {}}  # All keys missing
        calc = DefaultWealthProxyCalculator(precarity_data=data)
        result = calc.estimate_lumpen_share("00000", 2022)
        assert result == 0.0
