"""Unit tests for shadow labor visibility calculations.

This module tests the Shadow Labor Sprint implementation, which adds the
visibility dimension (g_33) to distinguish monetized care work from shadow
labor subsidy in Department III (Social Reproduction).

**Theoretical Foundation:**

The visibility coefficient g_33 represents the fraction of reproductive labor
that enters the formal commodity circuit (monetized). The complement (1 - g_33)
represents shadow labor that subsidizes capital accumulation without direct
compensation.

**Formulas:**

    v_market = T_3,v × w_shadow × g_33
    v_shadow = T_3,v × w_shadow × (1 - g_33)

Where:
    - T_3,v = Total reproductive labor hours (from ATUS)
    - w_shadow = Shadow wage (replacement cost basis, $15.43/hour)
    - g_33 = Visibility coefficient ∈ [0, 1]

**Boundary Conditions:**
    - g_33 = 1.0 → All care work monetized (daycare, nursing homes) → v_shadow = 0
    - g_33 = 0.0 → All care work unpaid (full-time homemaker) → v_market = 0

See Also:
    :mod:`babylon.economics.shadow_labor`: Shadow labor implementation.
    :mod:`babylon.data.atus`: ATUS data loading infrastructure.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.economics.atus_compat import (
    ATUSActivityRecord,
    ATUSHouseholdSummary,
    MockReproductionLoader,
)
from babylon.economics.shadow_labor import (
    ReproductionLoaderProtocol,
    ShadowLaborConfig,
    ShadowLaborResult,
    ShadowLaborService,
)
from tests.constants import TestConstants

TC = TestConstants


# =============================================================================
# Model Tests: ShadowLaborConfig
# =============================================================================


class TestShadowLaborConfig:
    """Tests for ShadowLaborConfig validation."""

    def test_default_g_33(self) -> None:
        """Default visibility coefficient is 0.3.

        ATUS 2022 shows approximately 30% of care work is formally compensated.
        """
        config = ShadowLaborConfig()
        assert config.g_33 == pytest.approx(0.3)

    def test_default_shadow_wage(self) -> None:
        """Default shadow wage is $15.43/hour (BLS home health aide median)."""
        config = ShadowLaborConfig()
        assert config.shadow_wage_hourly == pytest.approx(15.43)

    def test_g_33_lower_bound(self) -> None:
        """g_33 must be >= 0.0."""
        with pytest.raises(ValidationError):
            ShadowLaborConfig(g_33=-0.1)

    def test_g_33_upper_bound(self) -> None:
        """g_33 must be <= 1.0."""
        with pytest.raises(ValidationError):
            ShadowLaborConfig(g_33=1.1)

    def test_g_33_at_boundaries(self) -> None:
        """g_33 can be exactly 0.0 or 1.0."""
        config_zero = ShadowLaborConfig(g_33=0.0)
        config_one = ShadowLaborConfig(g_33=1.0)

        assert config_zero.g_33 == 0.0
        assert config_one.g_33 == 1.0

    def test_shadow_wage_non_negative(self) -> None:
        """Shadow wage must be >= 0."""
        with pytest.raises(ValidationError):
            ShadowLaborConfig(shadow_wage_hourly=-1.0)

    def test_config_immutable(self) -> None:
        """Config is frozen (immutable)."""
        config = ShadowLaborConfig()
        with pytest.raises(ValidationError):
            config.g_33 = 0.5  # type: ignore[misc]

    def test_custom_config(self) -> None:
        """Custom config values are accepted."""
        config = ShadowLaborConfig(g_33=0.5, shadow_wage_hourly=20.0)
        assert config.g_33 == pytest.approx(0.5)
        assert config.shadow_wage_hourly == pytest.approx(20.0)


# =============================================================================
# Model Tests: ShadowLaborResult
# =============================================================================


class TestShadowLaborResult:
    """Tests for ShadowLaborResult computed fields."""

    def test_total_value_computation(self) -> None:
        """Total value = hours * wage."""
        result = ShadowLaborResult(
            fips_code="06001",
            year=2022,
            total_hours_annual=1000.0,
            shadow_wage=15.43,
            g_33=0.5,
        )
        assert result.total_value == pytest.approx(15430.0)

    def test_v_market_computation(self) -> None:
        """v_market = total_value * g_33."""
        result = ShadowLaborResult(
            fips_code="06001",
            year=2022,
            total_hours_annual=1000.0,
            shadow_wage=15.43,
            g_33=0.3,
        )
        # 15430.0 * 0.3 = 4629.0
        assert result.v_market == pytest.approx(4629.0)

    def test_v_shadow_computation(self) -> None:
        """v_shadow = total_value * (1 - g_33)."""
        result = ShadowLaborResult(
            fips_code="06001",
            year=2022,
            total_hours_annual=1000.0,
            shadow_wage=15.43,
            g_33=0.3,
        )
        # 15430.0 * 0.7 = 10801.0
        assert result.v_shadow == pytest.approx(10801.0)

    def test_shadow_subsidy_ratio(self) -> None:
        """shadow_subsidy_ratio = 1 - g_33."""
        result = ShadowLaborResult(
            fips_code="06001",
            year=2022,
            total_hours_annual=1000.0,
            shadow_wage=15.43,
            g_33=0.3,
        )
        assert result.shadow_subsidy_ratio == pytest.approx(0.7)

    def test_result_immutable(self) -> None:
        """Result is frozen (immutable)."""
        result = ShadowLaborResult(
            fips_code="06001",
            year=2022,
            total_hours_annual=1000.0,
            shadow_wage=15.43,
            g_33=0.3,
        )
        with pytest.raises(ValidationError):
            result.g_33 = 0.5  # type: ignore[misc]

    def test_fips_code_stored(self) -> None:
        """FIPS code is stored correctly."""
        result = ShadowLaborResult(
            fips_code="06001",
            year=2022,
            total_hours_annual=1000.0,
            shadow_wage=15.43,
            g_33=0.3,
        )
        assert result.fips_code == "06001"
        assert result.year == 2022


# =============================================================================
# Model Tests: ATUSActivityRecord
# =============================================================================


class TestATUSActivityRecord:
    """Tests for ATUS activity record model."""

    def test_default_values(self) -> None:
        """Default values for optional fields."""
        record = ATUSActivityRecord(
            respondent_id="R001",
            activity_code="030101",
            duration_minutes=60,
        )
        assert record.is_reproductive is False
        assert record.is_paid is False

    def test_duration_bounds(self) -> None:
        """Duration must be 0-1440 minutes (24 hours)."""
        # Valid at boundaries
        record_zero = ATUSActivityRecord(
            respondent_id="R001",
            activity_code="030101",
            duration_minutes=0,
        )
        record_max = ATUSActivityRecord(
            respondent_id="R001",
            activity_code="030101",
            duration_minutes=1440,
        )
        assert record_zero.duration_minutes == 0
        assert record_max.duration_minutes == 1440

        # Invalid below zero
        with pytest.raises(ValidationError):
            ATUSActivityRecord(
                respondent_id="R001",
                activity_code="030101",
                duration_minutes=-1,
            )

        # Invalid above 24 hours
        with pytest.raises(ValidationError):
            ATUSActivityRecord(
                respondent_id="R001",
                activity_code="030101",
                duration_minutes=1441,
            )


# =============================================================================
# Model Tests: ATUSHouseholdSummary
# =============================================================================


class TestATUSHouseholdSummary:
    """Tests for ATUS household summary model."""

    def test_fips_code_format(self) -> None:
        """FIPS code must be 5 digits."""
        # Valid 5-digit FIPS
        summary = ATUSHouseholdSummary(
            fips_code="06001",
            year=2022,
            total_reproductive_hours_weekly=21.0,
            unpaid_care_hours_weekly=15.0,
            paid_care_hours_weekly=6.0,
        )
        assert summary.fips_code == "06001"

        # Invalid: 4 digits
        with pytest.raises(ValidationError):
            ATUSHouseholdSummary(
                fips_code="6001",
                year=2022,
                total_reproductive_hours_weekly=21.0,
                unpaid_care_hours_weekly=15.0,
                paid_care_hours_weekly=6.0,
            )

    def test_year_minimum(self) -> None:
        """Year must be >= 2003 (ATUS start year)."""
        # Valid: 2003
        summary = ATUSHouseholdSummary(
            fips_code="06001",
            year=2003,
            total_reproductive_hours_weekly=21.0,
            unpaid_care_hours_weekly=15.0,
            paid_care_hours_weekly=6.0,
        )
        assert summary.year == 2003

        # Invalid: 2002
        with pytest.raises(ValidationError):
            ATUSHouseholdSummary(
                fips_code="06001",
                year=2002,
                total_reproductive_hours_weekly=21.0,
                unpaid_care_hours_weekly=15.0,
                paid_care_hours_weekly=6.0,
            )

    def test_hours_non_negative(self) -> None:
        """Hours fields must be >= 0."""
        with pytest.raises(ValidationError):
            ATUSHouseholdSummary(
                fips_code="06001",
                year=2022,
                total_reproductive_hours_weekly=-1.0,
                unpaid_care_hours_weekly=15.0,
                paid_care_hours_weekly=6.0,
            )

    def test_default_weight(self) -> None:
        """Default household weight is 1.0."""
        summary = ATUSHouseholdSummary(
            fips_code="06001",
            year=2022,
            total_reproductive_hours_weekly=21.0,
            unpaid_care_hours_weekly=15.0,
            paid_care_hours_weekly=6.0,
        )
        assert summary.household_weight == pytest.approx(1.0)


# =============================================================================
# Mock Loader Tests
# =============================================================================


class TestMockReproductionLoader:
    """Tests for MockReproductionLoader implementation."""

    def test_implements_protocol(self) -> None:
        """MockReproductionLoader implements ReproductionLoaderProtocol."""
        loader = MockReproductionLoader()
        assert isinstance(loader, ReproductionLoaderProtocol)

    def test_default_weekly_hours(self) -> None:
        """Default uses national average of 21 hours/week."""
        loader = MockReproductionLoader()
        summary = loader.load_county_summary("06001", 2022)
        assert summary.unpaid_care_hours_weekly == pytest.approx(21.0)

    def test_default_shadow_wage(self) -> None:
        """Default shadow wage is $15.43/hour."""
        loader = MockReproductionLoader()
        wage = loader.get_shadow_wage("06001", 2022)
        assert wage == pytest.approx(15.43)

    def test_custom_weekly_hours(self) -> None:
        """Custom weekly hours are applied."""
        loader = MockReproductionLoader(default_weekly_hours=30.0)
        summary = loader.load_county_summary("06001", 2022)
        assert summary.unpaid_care_hours_weekly == pytest.approx(30.0)

    def test_custom_shadow_wage(self) -> None:
        """Custom shadow wage is applied."""
        loader = MockReproductionLoader(shadow_wage_hourly=20.0)
        wage = loader.get_shadow_wage("06001", 2022)
        assert wage == pytest.approx(20.0)

    def test_fips_code_passthrough(self) -> None:
        """FIPS code is passed through to summary."""
        loader = MockReproductionLoader()
        summary = loader.load_county_summary("26163", 2022)
        assert summary.fips_code == "26163"

    def test_year_passthrough(self) -> None:
        """Year is passed through to summary."""
        loader = MockReproductionLoader()
        summary = loader.load_county_summary("06001", 2020)
        assert summary.year == 2020


# =============================================================================
# Core Test Suite: Shadow Subsidy Calculation
# =============================================================================


class TestShadowSubsidyCalculation:
    """Core test suite for shadow subsidy calculation.

    Scenario: A county with 1000 hours of annual care work.
    Shadow wage: $15.43/hour (BLS home health aide median).
    Total value: $15,430.
    """

    @pytest.fixture
    def mock_loader(self) -> MockReproductionLoader:
        """Loader configured for 1000 annual hours.

        1000 annual hours = 19.23 weekly hours (1000/52).
        """
        return MockReproductionLoader(
            default_weekly_hours=1000.0 / 52,
            shadow_wage_hourly=15.43,
        )

    @pytest.fixture
    def shadow_service(self, mock_loader: MockReproductionLoader) -> ShadowLaborService:
        """Service with mock loader."""
        return ShadowLaborService(loader=mock_loader)

    def test_full_monetization_zero_subsidy(self, shadow_service: ShadowLaborService) -> None:
        """When g_33 = 1.0, all care work is monetized, subsidy = 0.

        Interpretation: All reproductive labor enters formal commodity
        circuit (paid daycare, nursing homes, domestic workers).
        """
        result = shadow_service.calculate_shadow_decomposition(
            fips_code="06001",
            year=2022,
            g_33_override=1.0,
        )

        assert result.v_market == pytest.approx(15430.0, rel=0.01)
        assert result.v_shadow == pytest.approx(0.0, abs=0.01)
        assert result.shadow_subsidy_ratio == pytest.approx(0.0)

    def test_full_shadow_maximum_subsidy(self, shadow_service: ShadowLaborService) -> None:
        """When g_33 = 0.0, all care work is shadow labor, subsidy = $15,430.

        Interpretation: All reproductive labor is unpaid household work
        (full-time homemaker scenario). This represents maximum subsidy
        to capital accumulation.
        """
        result = shadow_service.calculate_shadow_decomposition(
            fips_code="06001",
            year=2022,
            g_33_override=0.0,
        )

        assert result.v_market == pytest.approx(0.0, abs=0.01)
        assert result.v_shadow == pytest.approx(15430.0, rel=0.01)
        assert result.shadow_subsidy_ratio == pytest.approx(1.0)

    def test_partial_visibility_default(self, shadow_service: ShadowLaborService) -> None:
        """Default g_33 = 0.3 reflects ATUS 2022 national average.

        ~30% of care work is formally compensated.
        ~70% remains unpaid household labor (shadow subsidy).
        """
        result = shadow_service.calculate_shadow_decomposition(
            fips_code="06001",
            year=2022,
            # Uses default g_33 = 0.3
        )

        assert result.g_33 == pytest.approx(0.3)
        # 0.3 * 15430 = 4629
        assert result.v_market == pytest.approx(4629.0, rel=0.01)
        # 0.7 * 15430 = 10801
        assert result.v_shadow == pytest.approx(10801.0, rel=0.01)

    def test_invariant_total_value_preserved(self, shadow_service: ShadowLaborService) -> None:
        """v_market + v_shadow = total_value for any g_33.

        The visibility lens redistributes but does not create/destroy value.
        """
        for g_33 in [0.0, 0.25, 0.5, 0.75, 1.0]:
            result = shadow_service.calculate_shadow_decomposition(
                fips_code="06001",
                year=2022,
                g_33_override=g_33,
            )

            assert result.v_market + result.v_shadow == pytest.approx(result.total_value), (
                f"Value conservation violated at g_33={g_33}"
            )

    def test_g_33_override_takes_precedence(self, shadow_service: ShadowLaborService) -> None:
        """g_33_override takes precedence over config default."""
        result = shadow_service.calculate_shadow_decomposition(
            fips_code="06001",
            year=2022,
            g_33_override=0.6,
        )

        assert result.g_33 == pytest.approx(0.6)

    def test_service_with_custom_config(self, mock_loader: MockReproductionLoader) -> None:
        """Service accepts custom config."""
        config = ShadowLaborConfig(g_33=0.5, shadow_wage_hourly=20.0)
        service = ShadowLaborService(loader=mock_loader, config=config)

        result = service.calculate_shadow_decomposition(
            fips_code="06001",
            year=2022,
        )

        assert result.g_33 == pytest.approx(0.5)


# =============================================================================
# Integration Tests: Existing Infrastructure Unaffected
# =============================================================================


class TestExistingInfrastructureUnaffected:
    """Verify shadow labor lens does not break existing tensor/hydrator."""

    def test_shadow_service_independent(self) -> None:
        """Shadow service operates alongside tensor, not inside it."""
        # Shadow service can be instantiated independently
        loader = MockReproductionLoader()
        service = ShadowLaborService(loader=loader)

        # Can calculate decomposition without any tensor
        result = service.calculate_shadow_decomposition(
            fips_code="06001",
            year=2022,
        )

        # Result is valid
        assert result.total_value > 0
        assert result.v_market >= 0
        assert result.v_shadow >= 0


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Edge case tests for shadow labor calculations."""

    def test_zero_hours_zero_value(self) -> None:
        """Zero hours produces zero value."""
        loader = MockReproductionLoader(default_weekly_hours=0.0)
        service = ShadowLaborService(loader=loader)

        result = service.calculate_shadow_decomposition(
            fips_code="06001",
            year=2022,
        )

        assert result.total_value == pytest.approx(0.0)
        assert result.v_market == pytest.approx(0.0)
        assert result.v_shadow == pytest.approx(0.0)

    def test_zero_wage_zero_value(self) -> None:
        """Zero wage produces zero value."""
        loader = MockReproductionLoader(
            default_weekly_hours=21.0,
            shadow_wage_hourly=0.0,
        )
        service = ShadowLaborService(loader=loader)

        result = service.calculate_shadow_decomposition(
            fips_code="06001",
            year=2022,
        )

        assert result.total_value == pytest.approx(0.0)
        assert result.v_market == pytest.approx(0.0)
        assert result.v_shadow == pytest.approx(0.0)

    def test_high_hours_high_value(self) -> None:
        """High hours (40/week) produces correct value."""
        loader = MockReproductionLoader(default_weekly_hours=40.0)
        service = ShadowLaborService(loader=loader)

        result = service.calculate_shadow_decomposition(
            fips_code="06001",
            year=2022,
        )

        # 40 * 52 = 2080 annual hours
        # 2080 * 15.43 = 32,094.40
        assert result.total_hours_annual == pytest.approx(2080.0)
        assert result.total_value == pytest.approx(32094.4, rel=0.01)
