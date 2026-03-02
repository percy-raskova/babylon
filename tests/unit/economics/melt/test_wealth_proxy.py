"""Unit tests for DefaultWealthProxyCalculator.

Targeted mutation-killing tests for weighted precarity formula,
clamping logic, missing data handling, and Feature 038 ClassSystemDefines
integration (equity_factor + trust_land_discount).
"""

from __future__ import annotations

import pytest
from tests.constants import ClassSystemDefaults

from babylon.economics.melt.wealth_proxy import DefaultWealthProxyCalculator

CS = ClassSystemDefaults()


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


class TestEstimateLaShareMutationKillers:
    """Mutation-killing tests for estimate_la_share."""

    def test_known_fips_uses_formula(self) -> None:
        """LA share = homeownership * equity_factor."""
        calc = DefaultWealthProxyCalculator(
            homeownership_data={"00000": 0.70},
            equity_factor=0.6,
        )
        result = calc.estimate_la_share("00000", 2022)
        assert abs(result - 0.70 * 0.6) < 1e-10

    def test_unknown_fips_returns_national_average(self) -> None:
        """Unknown FIPS falls back to NATIONAL_LA_SHARE."""
        calc = DefaultWealthProxyCalculator(homeownership_data={})
        result = calc.estimate_la_share("99999", 2022)
        assert result == DefaultWealthProxyCalculator.NATIONAL_LA_SHARE

    def test_custom_equity_factor(self) -> None:
        """Custom equity_factor changes the LA share result."""
        calc = DefaultWealthProxyCalculator(
            homeownership_data={"00000": 0.80},
            equity_factor=0.5,
        )
        result = calc.estimate_la_share("00000", 2022)
        assert abs(result - 0.80 * 0.5) < 1e-10

    def test_homeownership_zero_returns_zero(self) -> None:
        """Homeownership=0 produces LA share=0."""
        calc = DefaultWealthProxyCalculator(homeownership_data={"00000": 0.0})
        result = calc.estimate_la_share("00000", 2022)
        assert result == 0.0

    def test_homeownership_one_returns_equity_factor(self) -> None:
        """Homeownership=1.0 produces LA share = equity_factor."""
        calc = DefaultWealthProxyCalculator(homeownership_data={"00000": 1.0})
        result = calc.estimate_la_share("00000", 2022)
        assert abs(result - DefaultWealthProxyCalculator.EQUITY_FACTOR) < 1e-10


class TestEstimateWealthPercentileMutationKillers:
    """Mutation-killing tests for estimate_wealth_percentile."""

    def test_unknown_fips_returns_50_true(self) -> None:
        """Unknown FIPS returns (50.0, True)."""
        calc = DefaultWealthProxyCalculator(homeownership_data={})
        percentile, is_est = calc.estimate_wealth_percentile("99999", 2022)
        assert percentile == 50.0
        assert is_est is True

    def test_national_average_homeownership_returns_50(self) -> None:
        """Homeownership at national average produces ~50th percentile."""
        calc = DefaultWealthProxyCalculator(
            homeownership_data={"00000": DefaultWealthProxyCalculator.NATIONAL_HOMEOWNERSHIP}
        )
        percentile, is_est = calc.estimate_wealth_percentile("00000", 2022)
        # ratio = 0.65/0.65 = 1.0, percentile = 50*1.0 = 50
        assert percentile == pytest.approx(50.0)
        assert is_est is True

    def test_high_homeownership_clamped_at_95(self) -> None:
        """Very high homeownership clamped at 95th percentile."""
        calc = DefaultWealthProxyCalculator(homeownership_data={"00000": 1.0})
        percentile, _ = calc.estimate_wealth_percentile("00000", 2022)
        # ratio = 1.0/0.65 = 1.538, 50*1.538 = 76.9 → not clamped
        # Need even higher to hit 95: 95/50 = 1.9, 1.9*0.65 = 1.235 (>1)
        # So with homeownership=2.0 (artificial), 50*2.0/0.65 = 153.8 → clamped to 95
        calc2 = DefaultWealthProxyCalculator(homeownership_data={"00000": 2.0})
        percentile2, _ = calc2.estimate_wealth_percentile("00000", 2022)
        assert percentile2 == 95.0

    def test_low_homeownership_clamped_at_5(self) -> None:
        """Very low homeownership clamped at 5th percentile."""
        calc = DefaultWealthProxyCalculator(homeownership_data={"00000": 0.01})
        percentile, _ = calc.estimate_wealth_percentile("00000", 2022)
        # ratio = 0.01/0.65 = 0.0154, 50*0.0154 = 0.77 → clamped to 5
        assert percentile == 5.0

    def test_is_estimated_always_true(self) -> None:
        """is_estimated is always True for county data."""
        calc = DefaultWealthProxyCalculator(homeownership_data={"00000": 0.65})
        _, is_est = calc.estimate_wealth_percentile("00000", 2022)
        assert is_est is True

    def test_exact_percentile_formula(self) -> None:
        """Verify exact percentile = min(95, max(5, 50 * ratio))."""
        calc = DefaultWealthProxyCalculator(homeownership_data={"00000": 0.78})
        percentile, _ = calc.estimate_wealth_percentile("00000", 2022)
        expected = 50.0 * (0.78 / DefaultWealthProxyCalculator.NATIONAL_HOMEOWNERSHIP)
        assert percentile == pytest.approx(expected, rel=1e-9)


class TestGetClassDistributionMutationKillers:
    """Mutation-killing tests for get_class_distribution_estimate."""

    def test_no_data_returns_none(self) -> None:
        """No homeownership or precarity data returns None."""
        calc = DefaultWealthProxyCalculator(homeownership_data={}, precarity_data={})
        result = calc.get_class_distribution_estimate("99999", 2022)
        assert result is None

    def test_distribution_sums_to_one(self) -> None:
        """All class shares sum to 1.0."""
        calc = DefaultWealthProxyCalculator(
            homeownership_data={"00000": 0.65},
            precarity_data={
                "00000": {
                    "u3_rate": 0.05,
                    "u6_rate": 0.10,
                    "pter_rate": 0.04,
                    "nilf_want_work": 0.03,
                    "incarceration_rate": 0.015,
                }
            },
        )
        result = calc.get_class_distribution_estimate("00000", 2022)
        assert result is not None
        total = sum(result.values())
        assert total == pytest.approx(1.0, rel=1e-9)

    def test_bourgeoisie_fixed_at_1pct(self) -> None:
        """Bourgeoisie share is always 0.01."""
        calc = DefaultWealthProxyCalculator(homeownership_data={"00000": 0.65})
        result = calc.get_class_distribution_estimate("00000", 2022)
        assert result is not None
        assert result["bourgeoisie"] == 0.01

    def test_petit_bourgeoisie_fixed_at_9pct(self) -> None:
        """Petit bourgeoisie share is always 0.09."""
        calc = DefaultWealthProxyCalculator(homeownership_data={"00000": 0.65})
        result = calc.get_class_distribution_estimate("00000", 2022)
        assert result is not None
        assert result["petit_bourgeoisie"] == 0.09

    def test_la_share_from_homeownership(self) -> None:
        """LA share comes from estimate_la_share formula."""
        calc = DefaultWealthProxyCalculator(homeownership_data={"00000": 0.70})
        result = calc.get_class_distribution_estimate("00000", 2022)
        assert result is not None
        expected_la = 0.70 * DefaultWealthProxyCalculator.EQUITY_FACTOR
        assert result["labor_aristocracy"] == pytest.approx(expected_la, rel=1e-9)

    def test_fallback_split_when_no_precarity_data(self) -> None:
        """Without precarity data, bottom split is 70% proletariat, 30% lumpen."""
        calc = DefaultWealthProxyCalculator(
            homeownership_data={"00000": 0.65},
            precarity_data={},  # No precarity data
        )
        result = calc.get_class_distribution_estimate("00000", 2022)
        assert result is not None
        la = result["labor_aristocracy"]
        bottom = 1.0 - 0.10 - la
        assert result["proletariat"] == pytest.approx(bottom * 0.70, rel=1e-9)
        assert result["lumpenproletariat"] == pytest.approx(bottom * 0.30, rel=1e-9)

    def test_with_precarity_lumpen_capped_at_bottom_share(self) -> None:
        """Lumpen share cannot exceed bottom share (1.0 - top10 - la)."""
        calc = DefaultWealthProxyCalculator(
            homeownership_data={"00000": 0.90},  # High LA → small bottom
            precarity_data={
                "00000": {
                    "u3_rate": 0.0,
                    "u6_rate": 0.0,
                    "pter_rate": 0.0,
                    "nilf_want_work": 2.0,  # Would produce huge lumpen
                    "incarceration_rate": 0.0,
                }
            },
        )
        result = calc.get_class_distribution_estimate("00000", 2022)
        assert result is not None
        la = result["labor_aristocracy"]
        bottom = 1.0 - 0.10 - la
        assert result["lumpenproletariat"] <= bottom + 1e-10
        assert result["proletariat"] >= -1e-10

    def test_only_precarity_data_present(self) -> None:
        """With only precarity data (no homeownership), uses national LA average."""
        calc = DefaultWealthProxyCalculator(
            homeownership_data={},
            precarity_data={
                "00000": {
                    "u3_rate": 0.05,
                    "u6_rate": 0.10,
                    "pter_rate": 0.04,
                    "nilf_want_work": 0.03,
                    "incarceration_rate": 0.015,
                }
            },
        )
        result = calc.get_class_distribution_estimate("00000", 2022)
        assert result is not None
        assert result["labor_aristocracy"] == DefaultWealthProxyCalculator.NATIONAL_LA_SHARE

    def test_all_five_classes_present(self) -> None:
        """Result dict has all 5 class keys."""
        calc = DefaultWealthProxyCalculator(homeownership_data={"00000": 0.65})
        result = calc.get_class_distribution_estimate("00000", 2022)
        assert result is not None
        expected_keys = {
            "bourgeoisie",
            "petit_bourgeoisie",
            "labor_aristocracy",
            "proletariat",
            "lumpenproletariat",
        }
        assert set(result.keys()) == expected_keys


class TestClassSystemDefinesIntegration:
    """T018: WealthProxyCalculator reads equity_factor from ClassSystemDefines (FR-005)."""

    @pytest.mark.unit
    def test_reads_equity_factor_from_defines(self) -> None:
        """equity_factor sourced from ClassSystemDefines when provided."""
        from babylon.config.defines import ClassSystemDefines

        defines = ClassSystemDefines(equity_factor=0.7)
        calc = DefaultWealthProxyCalculator(
            homeownership_data={"00000": 0.80},
            class_system_defines=defines,
        )
        result = calc.estimate_la_share("00000", 2022)
        assert result == pytest.approx(0.80 * 0.7)

    @pytest.mark.unit
    def test_explicit_equity_factor_overrides_defines(self) -> None:
        """Explicit equity_factor parameter takes priority over ClassSystemDefines."""
        from babylon.config.defines import ClassSystemDefines

        defines = ClassSystemDefines(equity_factor=0.7)
        calc = DefaultWealthProxyCalculator(
            homeownership_data={"00000": 0.80},
            equity_factor=0.5,
            class_system_defines=defines,
        )
        result = calc.estimate_la_share("00000", 2022)
        assert result == pytest.approx(0.80 * 0.5)

    @pytest.mark.unit
    def test_default_reads_from_game_defines(self) -> None:
        """No explicit equity_factor or defines -> uses GameDefines default (0.6)."""
        calc = DefaultWealthProxyCalculator(homeownership_data={"00000": 0.80})
        result = calc.estimate_la_share("00000", 2022)
        assert result == pytest.approx(0.80 * CS.EQUITY_FACTOR)

    @pytest.mark.unit
    def test_trust_land_discount_on_reservation_county(self) -> None:
        """Reservation-county homeownership discounted by trust_land_discount."""
        from babylon.config.defines import ClassSystemDefines

        defines = ClassSystemDefines()
        # Use a known reservation FIPS
        reservation_fips = "46102"  # Oglala Lakota County, SD
        calc = DefaultWealthProxyCalculator(
            homeownership_data={reservation_fips: 0.60},
            class_system_defines=defines,
            reservation_fips={reservation_fips},
        )
        result = calc.estimate_la_share(reservation_fips, 2022)
        # Effective homeownership = 0.60 * trust_land_discount (0.5) = 0.30
        # LA share = 0.30 * equity_factor (0.6) = 0.18
        expected = 0.60 * CS.TRUST_LAND_DISCOUNT * CS.EQUITY_FACTOR
        assert result == pytest.approx(expected)

    @pytest.mark.unit
    def test_non_reservation_county_unaffected(self) -> None:
        """Non-reservation counties are not affected by trust_land_discount."""
        from babylon.config.defines import ClassSystemDefines

        defines = ClassSystemDefines()
        calc = DefaultWealthProxyCalculator(
            homeownership_data={"26125": 0.78},
            class_system_defines=defines,
            reservation_fips={"46102"},
        )
        result = calc.estimate_la_share("26125", 2022)
        # No discount applied — standard formula
        expected = 0.78 * CS.EQUITY_FACTOR
        assert result == pytest.approx(expected)

    @pytest.mark.unit
    def test_reservation_discount_also_affects_wealth_percentile(self) -> None:
        """Reservation discount flows through to wealth percentile estimate."""
        from babylon.config.defines import ClassSystemDefines

        defines = ClassSystemDefines()
        reservation_fips = "46102"
        calc = DefaultWealthProxyCalculator(
            homeownership_data={reservation_fips: 0.60},
            class_system_defines=defines,
            reservation_fips={reservation_fips},
        )
        percentile, is_est = calc.estimate_wealth_percentile(reservation_fips, 2022)
        # Effective homeownership = 0.60 * 0.5 = 0.30
        # Ratio = 0.30 / 0.65 = 0.4615...
        # Percentile = 50 * 0.4615... = 23.08
        effective_ownership = 0.60 * CS.TRUST_LAND_DISCOUNT
        expected_percentile = 50.0 * (effective_ownership / 0.65)
        assert percentile == pytest.approx(expected_percentile)
        assert is_est is True
