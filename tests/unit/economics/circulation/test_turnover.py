"""Tests for Capital Volume II turnover and annual surplus value.

Feature: 023-capital-volume-ii
Tasks: T031-T034

Tests for compute_annual_surplus_value, compare_turnover_advantage,
TurnoverProfileSource protocol, DefaultTurnoverProfileSource, and
get_weighted_turnover_profile.
"""

from __future__ import annotations

from babylon.domain.economics.circulation.defaults import (
    DEFAULT_TURNOVER_PROFILES,
    FALLBACK_PROFILE,
)
from babylon.domain.economics.circulation.turnover import (
    DefaultTurnoverProfileSource,
    compare_turnover_advantage,
    compute_annual_surplus_value,
    get_weighted_turnover_profile,
)
from babylon.domain.economics.circulation.types import (
    AnnualSurplusValue,
    TurnoverProfile,
)
from babylon.models.types import Currency

from .conftest import TEST_YEAR, WAYNE_COUNTY_FIPS

# =============================================================================
# T031: compute_annual_surplus_value tests
# =============================================================================


class TestComputeAnnualSurplusValue:
    """Tests for annualized surplus value computation per Capital II Ch. 16."""

    def test_marx_example_fast_turnover(self) -> None:
        """Marx's example: s/v=100%, 60-day turnover -> ~608% annual rate.

        Capital II Ch. 16: A capital with variable capital v=1000,
        surplus per cycle s=1000, turnover time 60 days.
        turnovers_per_year = 365/60 = 6.0833
        annual_surplus = 1000 * 6.0833 = 6083.33
        annual_rate = (s/v) * turnovers = 1.0 * 6.0833 = 6.0833 (608.33%)
        """
        result = compute_annual_surplus_value(
            variable_capital=Currency(1000.0),
            surplus_per_cycle=Currency(1000.0),
            turnover_time_days=60,
        )

        assert isinstance(result, AnnualSurplusValue)
        # Annual rate should be ~6.08 (608%)
        assert abs(result.annual_rate_of_surplus_value - (365.0 / 60.0)) < 0.01
        # Annual surplus = 1000 * 365/60 = 6083.33
        expected_surplus = 1000.0 * (365.0 / 60.0)
        assert abs(result.annual_surplus_value - expected_surplus) < 1.0

    def test_marx_example_slow_turnover(self) -> None:
        """Marx's example: s/v=100%, 182-day turnover -> ~200% annual rate.

        turnovers_per_year = 365/182 = 2.0055
        annual_rate = 1.0 * 2.0055 = 2.0055 (200.55%)
        """
        result = compute_annual_surplus_value(
            variable_capital=Currency(1000.0),
            surplus_per_cycle=Currency(1000.0),
            turnover_time_days=182,
        )

        # Annual rate should be ~2.0 (200%)
        assert abs(result.annual_rate_of_surplus_value - (365.0 / 182.0)) < 0.01
        # Annual surplus = 1000 * 365/182 = 2005.49
        expected_surplus = 1000.0 * (365.0 / 182.0)
        assert abs(result.annual_surplus_value - expected_surplus) < 1.0

    def test_different_rate_of_surplus(self) -> None:
        """Non-100% rate of surplus value.

        v=1000, s=500 (s/v=50%), turnover=73 days
        turnovers = 365/73 = 5.0
        annual_rate = 0.5 * 5.0 = 2.5
        annual_surplus = 500 * 5.0 = 2500
        """
        result = compute_annual_surplus_value(
            variable_capital=Currency(1000.0),
            surplus_per_cycle=Currency(500.0),
            turnover_time_days=73,
        )

        assert abs(result.annual_rate_of_surplus_value - 2.5) < 0.01
        assert abs(result.annual_surplus_value - 2500.0) < 1.0

    def test_output_contains_fips_and_year(self) -> None:
        """AnnualSurplusValue contains fips_code and year."""
        result = compute_annual_surplus_value(
            variable_capital=Currency(100.0),
            surplus_per_cycle=Currency(50.0),
            turnover_time_days=30,
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
        )

        assert result.fips_code == WAYNE_COUNTY_FIPS
        assert result.year == TEST_YEAR

    def test_rate_of_surplus_value_per_cycle(self) -> None:
        """Single-cycle rate matches s/v."""
        result = compute_annual_surplus_value(
            variable_capital=Currency(200.0),
            surplus_per_cycle=Currency(100.0),
            turnover_time_days=30,
        )

        assert abs(result.rate_of_surplus_value - 0.5) < 0.001

    def test_turnovers_per_year(self) -> None:
        """turnovers_per_year = 365 / turnover_time_days."""
        result = compute_annual_surplus_value(
            variable_capital=Currency(100.0),
            surplus_per_cycle=Currency(100.0),
            turnover_time_days=73,
        )

        assert abs(result.turnovers_per_year - 5.0) < 0.001

    def test_yearly_turnover(self) -> None:
        """365-day turnover gives exactly 1 turnover per year."""
        result = compute_annual_surplus_value(
            variable_capital=Currency(1000.0),
            surplus_per_cycle=Currency(500.0),
            turnover_time_days=365,
        )

        assert abs(result.turnovers_per_year - 1.0) < 0.001
        assert abs(result.annual_surplus_value - 500.0) < 0.01
        assert abs(result.annual_rate_of_surplus_value - 0.5) < 0.001


# =============================================================================
# T032: compare_turnover_advantage tests
# =============================================================================


class TestCompareTurnoverAdvantage:
    """Tests for fast/slow turnover comparison ratio."""

    def test_fast_vs_slow_ratio(self) -> None:
        """Fast turnover produces more annual surplus than slow.

        Fast: 60-day, s/v=100% -> annual = 1000 * 365/60 = 6083.33
        Slow: 182-day, s/v=100% -> annual = 1000 * 365/182 = 2005.49
        Ratio = 6083.33 / 2005.49 = 3.033...
        """
        fast = compute_annual_surplus_value(
            variable_capital=Currency(1000.0),
            surplus_per_cycle=Currency(1000.0),
            turnover_time_days=60,
        )
        slow = compute_annual_surplus_value(
            variable_capital=Currency(1000.0),
            surplus_per_cycle=Currency(1000.0),
            turnover_time_days=182,
        )

        ratio = compare_turnover_advantage(fast=fast, slow=slow)

        # 182/60 = 3.033 (ratio of turnovers equals ratio of surplus)
        expected = 182.0 / 60.0
        assert abs(ratio - expected) < 0.01

    def test_equal_turnover_ratio_is_one(self) -> None:
        """Identical turnover times yield ratio of 1.0."""
        a = compute_annual_surplus_value(
            variable_capital=Currency(500.0),
            surplus_per_cycle=Currency(250.0),
            turnover_time_days=90,
        )
        b = compute_annual_surplus_value(
            variable_capital=Currency(500.0),
            surplus_per_cycle=Currency(250.0),
            turnover_time_days=90,
        )

        ratio = compare_turnover_advantage(fast=a, slow=b)
        assert abs(ratio - 1.0) < 0.001

    def test_ratio_with_different_surplus_rates(self) -> None:
        """Ratio reflects both turnover speed and surplus rate differences.

        Fast: v=1000, s=500, 30-day -> annual = 500 * 365/30 = 6083.33
        Slow: v=1000, s=200, 90-day -> annual = 200 * 365/90 = 811.11
        Ratio = 6083.33 / 811.11 = 7.5
        """
        fast = compute_annual_surplus_value(
            variable_capital=Currency(1000.0),
            surplus_per_cycle=Currency(500.0),
            turnover_time_days=30,
        )
        slow = compute_annual_surplus_value(
            variable_capital=Currency(1000.0),
            surplus_per_cycle=Currency(200.0),
            turnover_time_days=90,
        )

        ratio = compare_turnover_advantage(fast=fast, slow=slow)
        expected = (500.0 * (365.0 / 30.0)) / (200.0 * (365.0 / 90.0))
        assert abs(ratio - expected) < 0.01


# =============================================================================
# T033: DefaultTurnoverProfileSource tests
# =============================================================================


class TestDefaultTurnoverProfileSource:
    """Tests for default turnover profile resolution by NAICS code."""

    def test_exact_match_by_sector(self) -> None:
        """Exact 2-digit NAICS code returns the matching profile."""
        source = DefaultTurnoverProfileSource()
        profile = source.get_turnover_profile("31")

        assert profile is not None
        assert profile.naics_code == "31"
        assert profile.working_period_days == 30

    def test_prefix_match_longer_naics(self) -> None:
        """6-digit NAICS code falls back to 2-digit sector prefix.

        "311210" (Flour Milling) -> prefix "31" -> Manufacturing profile.
        """
        source = DefaultTurnoverProfileSource()
        profile = source.get_turnover_profile("311210")

        assert profile is not None
        assert profile.naics_code == "31"

    def test_unknown_naics_returns_fallback(self) -> None:
        """Unknown NAICS code returns the fallback profile."""
        source = DefaultTurnoverProfileSource()
        profile = source.get_turnover_profile("99")

        assert profile is not None
        assert profile == FALLBACK_PROFILE

    def test_agriculture_profile(self) -> None:
        """Agriculture (NAICS 11) has long working period and non-working time."""
        source = DefaultTurnoverProfileSource()
        profile = source.get_turnover_profile("11")

        assert profile is not None
        assert profile.working_period_days == 90
        assert profile.non_working_production_days == 60
        assert profile.fixed_capital_ratio == 0.6

    def test_retail_profile(self) -> None:
        """Retail (NAICS 44) has very short turnover."""
        source = DefaultTurnoverProfileSource()
        profile = source.get_turnover_profile("44")

        assert profile is not None
        assert profile.working_period_days == 3
        assert profile.sale_time_days == 10

    def test_finance_profile(self) -> None:
        """Finance (NAICS 52) has short turnover and low fixed ratio."""
        source = DefaultTurnoverProfileSource()
        profile = source.get_turnover_profile("52")

        assert profile is not None
        assert profile.working_period_days == 5
        assert profile.fixed_capital_ratio == 0.3

    def test_all_default_profiles_valid(self) -> None:
        """Every profile in DEFAULT_TURNOVER_PROFILES is a valid TurnoverProfile."""
        for naics_code, profile in DEFAULT_TURNOVER_PROFILES.items():
            assert isinstance(profile, TurnoverProfile), (
                f"Profile for {naics_code} is not TurnoverProfile"
            )
            assert profile.naics_code == naics_code
            assert profile.turnover_time > 0

    def test_fallback_profile_has_moderate_values(self) -> None:
        """Fallback profile has moderate/average turnover parameters."""
        assert isinstance(FALLBACK_PROFILE, TurnoverProfile)
        assert FALLBACK_PROFILE.turnover_time > 0
        assert 0.3 <= FALLBACK_PROFILE.fixed_capital_ratio <= 0.7


# =============================================================================
# T034: get_weighted_turnover_profile tests
# =============================================================================


class TestGetWeightedTurnoverProfile:
    """Tests for employment-weighted turnover profile aggregation."""

    def test_single_industry_returns_that_profile(self) -> None:
        """Single industry with 100% weight returns its exact profile."""
        source = DefaultTurnoverProfileSource()
        weights = {"31": 1.0}

        result = get_weighted_turnover_profile(
            industry_weights=weights,
            source=source,
        )

        assert result is not None
        mfg = source.get_turnover_profile("31")
        assert mfg is not None
        assert result.working_period_days == mfg.working_period_days
        assert result.sale_time_days == mfg.sale_time_days

    def test_two_industry_weighted_average(self) -> None:
        """Two industries produce weighted average of all parameters.

        Manufacturing (31): working=30, non_working=10, purchase=10, sale=20, fixed=0.6
        Retail (44):       working= 3, non_working= 0, purchase= 7, sale=10, fixed=0.4

        50/50 weights:
        working = (30+3)/2 = 16.5 -> round to 16 or 17
        """
        source = DefaultTurnoverProfileSource()
        weights = {"31": 0.5, "44": 0.5}

        result = get_weighted_turnover_profile(
            industry_weights=weights,
            source=source,
        )

        assert result is not None
        # Weighted working period: 0.5*30 + 0.5*3 = 16.5
        # Should be rounded to nearest int
        assert abs(result.working_period_days - 17) <= 1
        # Weighted fixed_capital_ratio: 0.5*0.6 + 0.5*0.4 = 0.5
        assert abs(result.fixed_capital_ratio - 0.5) < 0.01

    def test_empty_weights_returns_none(self) -> None:
        """Empty industry weights returns None."""
        source = DefaultTurnoverProfileSource()
        result = get_weighted_turnover_profile(
            industry_weights={},
            source=source,
        )

        assert result is None

    def test_all_unknown_industries_returns_none(self) -> None:
        """If no profiles found for any industry, returns None.

        But wait - DefaultTurnoverProfileSource returns fallback for unknown.
        So this test uses a custom source that returns None for unknowns.
        """

        class StrictSource:
            """Source that returns None for any code."""

            def get_turnover_profile(self, naics_code: str) -> TurnoverProfile | None:
                """Return None for all codes."""
                return None

        result = get_weighted_turnover_profile(
            industry_weights={"ZZ": 0.5, "XX": 0.5},
            source=StrictSource(),
        )

        assert result is None

    def test_partial_unknown_uses_known_only(self) -> None:
        """Unknown industries are skipped; weights renormalized to known only.

        If one of two industries is unknown, the known one gets full weight.
        """

        class PartialSource:
            """Source that only knows manufacturing."""

            def get_turnover_profile(self, naics_code: str) -> TurnoverProfile | None:
                """Return profile only for code '31'."""
                if naics_code == "31":
                    return DEFAULT_TURNOVER_PROFILES["31"]
                return None

        weights = {"31": 0.5, "ZZ": 0.5}
        result = get_weighted_turnover_profile(
            industry_weights=weights,
            source=PartialSource(),
        )

        assert result is not None
        mfg = DEFAULT_TURNOVER_PROFILES["31"]
        # With only manufacturing known, should match manufacturing exactly
        assert result.working_period_days == mfg.working_period_days

    def test_weighted_profile_has_synthetic_naics(self) -> None:
        """Weighted profile gets a synthetic NAICS code ('WEIGHTED')."""
        source = DefaultTurnoverProfileSource()
        weights = {"31": 0.7, "44": 0.3}

        result = get_weighted_turnover_profile(
            industry_weights=weights,
            source=source,
        )

        assert result is not None
        assert result.naics_code == "WEIGHTED"

    def test_heavily_skewed_weights(self) -> None:
        """90/10 weighting produces result close to dominant industry."""
        source = DefaultTurnoverProfileSource()
        weights = {"31": 0.9, "44": 0.1}

        result = get_weighted_turnover_profile(
            industry_weights=weights,
            source=source,
        )

        assert result is not None
        mfg = source.get_turnover_profile("31")
        assert mfg is not None
        # Working period should be close to manufacturing (30)
        # 0.9*30 + 0.1*3 = 27.3 -> 27
        assert abs(result.working_period_days - 27) <= 1
