"""Unit tests for ClassPositionClassifier (User Story 2).

Feature: 013-melt-basket-visibility
Date: 2026-02-01
Revision: 2026-02-02 (wealth-based classification)

This module tests both:
1. Wealth-based classification (primary, canonical method)
2. Income-based classification (deprecated, backward compatibility)

Theoretical Background:
    Class position is determined by wealth percentile (stock), NOT income (flow).
    A proletarian can have Φ_hour > 0 while remaining proletarian - they consume
    rather than accumulate the imperial subsidy.

    LA = 40% emerges naturally from wealth distribution (50th-90th percentile).
"""

from __future__ import annotations

import warnings

import pytest

from babylon.economics.melt import (
    ClassPosition,
    DefaultClassPositionClassifier,
    NationalParameters,
    PrecarityStatus,
)
from babylon.economics.melt.wealth_proxy import DefaultWealthProxyCalculator


class TestClassPositionEnum:
    """Tests for ClassPosition enum definition."""

    def test_enum_has_exactly_five_values(self) -> None:
        """Test that ClassPosition enum has exactly 5 wealth-based values."""
        assert len(ClassPosition) == 5

    def test_enum_values_exist(self) -> None:
        """Test that all expected enum values exist."""
        assert ClassPosition.BOURGEOISIE is not None
        assert ClassPosition.PETIT_BOURGEOISIE is not None
        assert ClassPosition.LABOR_ARISTOCRACY is not None
        assert ClassPosition.PROLETARIAT is not None
        assert ClassPosition.LUMPENPROLETARIAT is not None

    def test_enum_values_have_correct_order(self) -> None:
        """Test enum values are in correct order (top to bottom of class hierarchy)."""
        # BOURGEOISIE should have lowest auto() value
        assert ClassPosition.BOURGEOISIE.value < ClassPosition.PETIT_BOURGEOISIE.value
        assert ClassPosition.PETIT_BOURGEOISIE.value < ClassPosition.LABOR_ARISTOCRACY.value
        assert ClassPosition.LABOR_ARISTOCRACY.value < ClassPosition.PROLETARIAT.value
        assert ClassPosition.PROLETARIAT.value < ClassPosition.LUMPENPROLETARIAT.value


class TestWealthBasedClassification:
    """Tests for wealth-based class position classification (primary method)."""

    @pytest.fixture
    def classifier(self) -> DefaultClassPositionClassifier:
        """Provide classifier instance."""
        return DefaultClassPositionClassifier()

    def test_bourgeoisie_top_1_percent(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Test that wealth percentile >= 99 results in BOURGEOISIE."""
        assert classifier.classify_by_wealth_percentile(99.0) == ClassPosition.BOURGEOISIE
        assert classifier.classify_by_wealth_percentile(99.5) == ClassPosition.BOURGEOISIE
        assert classifier.classify_by_wealth_percentile(100.0) == ClassPosition.BOURGEOISIE

    def test_petit_bourgeoisie_90_to_99(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Test that wealth percentile 90-99 results in PETIT_BOURGEOISIE."""
        assert classifier.classify_by_wealth_percentile(90.0) == ClassPosition.PETIT_BOURGEOISIE
        assert classifier.classify_by_wealth_percentile(95.0) == ClassPosition.PETIT_BOURGEOISIE
        assert classifier.classify_by_wealth_percentile(98.9) == ClassPosition.PETIT_BOURGEOISIE

    def test_labor_aristocracy_50_to_90(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Test that wealth percentile 50-90 results in LABOR_ARISTOCRACY."""
        assert classifier.classify_by_wealth_percentile(50.0) == ClassPosition.LABOR_ARISTOCRACY
        assert classifier.classify_by_wealth_percentile(70.0) == ClassPosition.LABOR_ARISTOCRACY
        assert classifier.classify_by_wealth_percentile(89.9) == ClassPosition.LABOR_ARISTOCRACY

    def test_bottom_50_defaults_to_proletariat(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Test that wealth percentile < 50 defaults to PROLETARIAT."""
        # classify_by_wealth_percentile defaults to PROLETARIAT for bottom 50%
        # (use classify_by_wealth_and_employment for lumpen distinction)
        assert classifier.classify_by_wealth_percentile(49.9) == ClassPosition.PROLETARIAT
        assert classifier.classify_by_wealth_percentile(30.0) == ClassPosition.PROLETARIAT
        assert classifier.classify_by_wealth_percentile(0.0) == ClassPosition.PROLETARIAT

    def test_proletariat_bottom_50_employed(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Test that bottom 50% + employed = PROLETARIAT."""
        assert (
            classifier.classify_by_wealth_and_employment(30.0, employed=True)
            == ClassPosition.PROLETARIAT
        )
        assert (
            classifier.classify_by_wealth_and_employment(10.0, employed=True)
            == ClassPosition.PROLETARIAT
        )

    def test_lumpenproletariat_bottom_50_excluded(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Test that bottom 50% + excluded = LUMPENPROLETARIAT."""
        assert (
            classifier.classify_by_wealth_and_employment(30.0, employed=False)
            == ClassPosition.LUMPENPROLETARIAT
        )
        assert (
            classifier.classify_by_wealth_and_employment(10.0, employed=False)
            == ClassPosition.LUMPENPROLETARIAT
        )

    def test_employment_status_ignored_above_50th_percentile(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Test that employment status doesn't matter above 50th percentile."""
        # Above 50th percentile, wealth determines class regardless of employment
        assert (
            classifier.classify_by_wealth_and_employment(70.0, employed=True)
            == ClassPosition.LABOR_ARISTOCRACY
        )
        assert (
            classifier.classify_by_wealth_and_employment(70.0, employed=False)
            == ClassPosition.LABOR_ARISTOCRACY
        )
        assert (
            classifier.classify_by_wealth_and_employment(95.0, employed=False)
            == ClassPosition.PETIT_BOURGEOISIE
        )

    def test_la_share_is_40_percent_by_definition(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """LA = 50th-90th percentile = 40% of population by definition.

        This is a definitional fact, not a parameter to tune. The 40% emerges
        naturally from the wealth distribution (90 - 50 = 40 percentage points).
        """
        # Count LA classifications across percentile range
        percentiles = list(range(100))  # 0 to 99
        la_count = sum(
            1
            for p in percentiles
            if classifier.classify_by_wealth_percentile(float(p)) == ClassPosition.LABOR_ARISTOCRACY
        )
        # 50, 51, ..., 89 = 40 values
        assert la_count == 40


class TestIncomeBasedClassificationDeprecated:
    """Tests for income-based classification (deprecated, backward compatibility)."""

    def test_classify_emits_deprecation_warning(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that income-based classify() emits deprecation warning."""
        classifier = DefaultClassPositionClassifier()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            classifier.classify(50.0, sample_national_params)

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()

    def test_wage_above_tau_effective_is_labor_aristocracy(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test backward compat: wage > τ_effective results in LABOR_ARISTOCRACY."""
        classifier = DefaultClassPositionClassifier()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            # τ_effective = 44.2, so $50/hr should be LA
            position = classifier.classify(50.0, sample_national_params)
            assert position == ClassPosition.LABOR_ARISTOCRACY

    def test_wage_between_thresholds_is_proletariat(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test backward compat: V_reproduction < wage ≤ τ_effective = PROLETARIAT."""
        classifier = DefaultClassPositionClassifier()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            # τ_effective = 44.2, V_reproduction = 12.0
            position = classifier.classify(25.0, sample_national_params)
            assert position == ClassPosition.PROLETARIAT

    def test_wage_at_or_below_v_reproduction_is_lumpenproletariat(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test backward compat: wage ≤ V_reproduction = LUMPENPROLETARIAT.

        Note: Old SUBPROLETARIAT maps to LUMPENPROLETARIAT in new model.
        """
        classifier = DefaultClassPositionClassifier()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            # V_reproduction = 12.0
            position = classifier.classify(8.0, sample_national_params)
            assert position == ClassPosition.LUMPENPROLETARIAT

    def test_wage_equal_to_tau_effective_is_proletariat(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test backward compat: wage == τ_effective = PROLETARIAT (not LA)."""
        classifier = DefaultClassPositionClassifier()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            position = classifier.classify(44.2, sample_national_params)
            assert position == ClassPosition.PROLETARIAT

    def test_wage_equal_to_v_reproduction_is_lumpenproletariat(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test backward compat: wage == V_reproduction = LUMPENPROLETARIAT."""
        classifier = DefaultClassPositionClassifier()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            position = classifier.classify(12.0, sample_national_params)
            assert position == ClassPosition.LUMPENPROLETARIAT


class TestWealthDistribution:
    """Tests for classify_wealth_distribution method (primary method)."""

    @pytest.fixture
    def classifier(self) -> DefaultClassPositionClassifier:
        """Provide classifier instance."""
        return DefaultClassPositionClassifier()

    def test_returns_all_five_class_positions(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Test that result dict contains all 5 ClassPosition keys."""
        percentiles = [99.5, 95.0, 70.0, 30.0, 20.0]
        shares = classifier.classify_wealth_distribution(percentiles)

        assert ClassPosition.BOURGEOISIE in shares
        assert ClassPosition.PETIT_BOURGEOISIE in shares
        assert ClassPosition.LABOR_ARISTOCRACY in shares
        assert ClassPosition.PROLETARIAT in shares
        assert ClassPosition.LUMPENPROLETARIAT in shares

    def test_shares_sum_to_one(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Test that shares sum to 1.0."""
        percentiles = [99.5, 95.0, 70.0, 30.0, 20.0]
        shares = classifier.classify_wealth_distribution(percentiles)

        total = sum(shares.values())
        assert abs(total - 1.0) < 1e-10

    def test_distribution_calculation(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Test that distribution shares are calculated correctly."""
        # 1 Bourgeois, 1 PB, 2 LA, 1 Proletariat (all employed by default)
        percentiles = [99.5, 95.0, 70.0, 60.0, 30.0]
        shares = classifier.classify_wealth_distribution(percentiles)

        assert abs(shares[ClassPosition.BOURGEOISIE] - 0.2) < 1e-10
        assert abs(shares[ClassPosition.PETIT_BOURGEOISIE] - 0.2) < 1e-10
        assert abs(shares[ClassPosition.LABOR_ARISTOCRACY] - 0.4) < 1e-10
        assert abs(shares[ClassPosition.PROLETARIAT] - 0.2) < 1e-10
        assert abs(shares[ClassPosition.LUMPENPROLETARIAT] - 0.0) < 1e-10

    def test_empty_distribution_returns_typical_shares(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Test that empty distribution returns typical population shares."""
        shares = classifier.classify_wealth_distribution([])

        # Should return typical national distribution
        assert abs(shares[ClassPosition.BOURGEOISIE] - 0.01) < 1e-10
        assert abs(shares[ClassPosition.PETIT_BOURGEOISIE] - 0.09) < 1e-10
        assert abs(shares[ClassPosition.LABOR_ARISTOCRACY] - 0.40) < 1e-10
        assert abs(shares[ClassPosition.PROLETARIAT] - 0.35) < 1e-10
        assert abs(shares[ClassPosition.LUMPENPROLETARIAT] - 0.15) < 1e-10

    def test_employment_status_distinguishes_lumpen(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Test that employment status distinguishes PROLETARIAT/LUMPEN."""
        percentiles = [30.0, 30.0]  # Both bottom 50%
        employment = [True, False]  # One employed, one excluded

        shares = classifier.classify_wealth_distribution(percentiles, employment)

        assert abs(shares[ClassPosition.PROLETARIAT] - 0.5) < 1e-10
        assert abs(shares[ClassPosition.LUMPENPROLETARIAT] - 0.5) < 1e-10

    def test_weighted_wealth_distribution(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Test that weights are applied correctly."""
        percentiles = [99.5, 30.0]  # Bourgeois and Proletariat
        weights = [1.0, 9.0]  # 1:9 ratio

        shares = classifier.classify_wealth_distribution(percentiles, weights=weights)

        assert abs(shares[ClassPosition.BOURGEOISIE] - 0.1) < 1e-10
        assert abs(shares[ClassPosition.PROLETARIAT] - 0.9) < 1e-10

    def test_weights_length_mismatch_raises_error(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Test that mismatched weights length raises ValueError."""
        percentiles = [99.5, 70.0, 30.0]
        weights = [1.0, 1.0]  # Wrong length

        with pytest.raises(ValueError, match="length"):
            classifier.classify_wealth_distribution(percentiles, weights=weights)


class TestIncomeDistributionDeprecated:
    """Tests for classify_distribution (deprecated, backward compatibility)."""

    def test_returns_three_class_positions(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that result dict contains 3 ClassPosition keys."""
        classifier = DefaultClassPositionClassifier()

        wages = [50.0, 25.0, 8.0]
        shares = classifier.classify_distribution(wages, sample_national_params)

        # Uses 3-class model for backward compatibility
        assert ClassPosition.LABOR_ARISTOCRACY in shares
        assert ClassPosition.PROLETARIAT in shares
        assert ClassPosition.LUMPENPROLETARIAT in shares  # Was SUBPROLETARIAT

    def test_shares_sum_to_one(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that shares sum to 1.0 (within floating point tolerance)."""
        classifier = DefaultClassPositionClassifier()

        wages = [50.0, 50.0, 25.0, 25.0, 8.0]
        shares = classifier.classify_distribution(wages, sample_national_params)

        total = sum(shares.values())
        assert abs(total - 1.0) < 1e-10

    def test_distribution_calculation(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that distribution shares are calculated correctly."""
        classifier = DefaultClassPositionClassifier()

        # 2 LA, 2 Proletariat, 1 Lumpen (was Subproletariat)
        wages = [50.0, 50.0, 25.0, 25.0, 8.0]
        shares = classifier.classify_distribution(wages, sample_national_params)

        assert abs(shares[ClassPosition.LABOR_ARISTOCRACY] - 0.4) < 1e-10
        assert abs(shares[ClassPosition.PROLETARIAT] - 0.4) < 1e-10
        assert abs(shares[ClassPosition.LUMPENPROLETARIAT] - 0.2) < 1e-10

    def test_empty_wage_list_returns_equal_shares(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that empty wage list returns equal shares (1/3 each)."""
        classifier = DefaultClassPositionClassifier()

        shares = classifier.classify_distribution([], sample_national_params)

        expected_share = 1.0 / 3.0
        # Only check the 3 classes used by this method
        assert abs(shares[ClassPosition.LABOR_ARISTOCRACY] - expected_share) < 1e-10
        assert abs(shares[ClassPosition.PROLETARIAT] - expected_share) < 1e-10
        assert abs(shares[ClassPosition.LUMPENPROLETARIAT] - expected_share) < 1e-10

    def test_single_wage_returns_100_percent(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that single wage returns 100% in appropriate class."""
        classifier = DefaultClassPositionClassifier()

        # Single LA wage
        shares = classifier.classify_distribution([50.0], sample_national_params)
        assert abs(shares[ClassPosition.LABOR_ARISTOCRACY] - 1.0) < 1e-10
        assert abs(shares[ClassPosition.PROLETARIAT] - 0.0) < 1e-10
        assert abs(shares[ClassPosition.LUMPENPROLETARIAT] - 0.0) < 1e-10

    def test_weighted_distribution(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that weights are applied correctly to distribution."""
        classifier = DefaultClassPositionClassifier()

        # 2 wages with different weights
        wages = [50.0, 8.0]  # LA and Lumpen
        weights = [3.0, 1.0]  # 3:1 ratio

        shares = classifier.classify_distribution(wages, sample_national_params, weights)

        # Total weight = 4, LA weight = 3, Lumpen weight = 1
        assert abs(shares[ClassPosition.LABOR_ARISTOCRACY] - 0.75) < 1e-10
        assert abs(shares[ClassPosition.PROLETARIAT] - 0.0) < 1e-10
        assert abs(shares[ClassPosition.LUMPENPROLETARIAT] - 0.25) < 1e-10

    def test_weights_length_mismatch_raises_error(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that mismatched weights length raises ValueError."""
        classifier = DefaultClassPositionClassifier()

        wages = [50.0, 25.0, 8.0]
        weights = [1.0, 1.0]  # Wrong length

        with pytest.raises(ValueError, match="length"):
            classifier.classify_distribution(wages, sample_national_params, weights)


class TestNationalParametersValidation:
    """Tests for NationalParameters consistency validation."""

    def test_tau_effective_consistency(self) -> None:
        """Test that τ_effective = τ × γ_basket consistency is checked."""
        params = NationalParameters(
            year=2022,
            tau=65.0,
            alpha=0.25,
            gamma_import=0.35,
            gamma_basket=0.68,
            tau_effective=44.2,  # 65 × 0.68 = 44.2
            v_reproduction=12.0,
        )

        warnings = params.validate_theoretical_consistency()
        assert len(warnings) == 0

    def test_inconsistent_tau_effective_generates_warning(self) -> None:
        """Test that inconsistent τ_effective generates warning."""
        params = NationalParameters(
            year=2022,
            tau=65.0,
            alpha=0.25,
            gamma_import=0.35,
            gamma_basket=0.68,
            tau_effective=50.0,  # Should be 44.2
            v_reproduction=12.0,
        )

        warnings = params.validate_theoretical_consistency()
        assert len(warnings) > 0
        assert any("τ_effective" in w for w in warnings)

    def test_v_reproduction_exceeds_tau_effective_generates_warning(self) -> None:
        """Test that V_reproduction >= τ_effective generates warning."""
        params = NationalParameters(
            year=2022,
            tau=65.0,
            alpha=0.25,
            gamma_import=0.35,
            gamma_basket=0.68,
            tau_effective=10.0,  # Very low
            v_reproduction=12.0,  # Higher than τ_effective
        )

        warnings = params.validate_theoretical_consistency()
        assert len(warnings) > 0
        assert any("V_reproduction" in w for w in warnings)


class TestPrecarityStatusEnum:
    """Tests for PrecarityStatus enum definition."""

    def test_enum_has_exactly_four_values(self) -> None:
        """Test that PrecarityStatus enum has exactly 4 values."""
        assert len(PrecarityStatus) == 4

    def test_enum_values_exist(self) -> None:
        """Test that all expected enum values exist."""
        assert PrecarityStatus.STABLE is not None
        assert PrecarityStatus.PRECARIOUS is not None
        assert PrecarityStatus.MARGINALLY_ATTACHED is not None
        assert PrecarityStatus.EXCLUDED is not None

    def test_enum_values_have_correct_order(self) -> None:
        """Test enum values are in order (stable to excluded)."""
        assert PrecarityStatus.STABLE.value < PrecarityStatus.PRECARIOUS.value
        assert PrecarityStatus.PRECARIOUS.value < PrecarityStatus.MARGINALLY_ATTACHED.value
        assert PrecarityStatus.MARGINALLY_ATTACHED.value < PrecarityStatus.EXCLUDED.value


class TestPrecarityBasedClassification:
    """Tests for precarity-based proletariat/lumpen distinction."""

    @pytest.fixture
    def classifier(self) -> DefaultClassPositionClassifier:
        """Provide classifier instance."""
        return DefaultClassPositionClassifier()

    def test_stable_employment_is_proletariat(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Stable W-2 employment → Proletariat."""
        result = classifier.classify_by_wealth_and_precarity(
            wealth_percentile=30.0,
            precarity=PrecarityStatus.STABLE,
        )
        assert result == ClassPosition.PROLETARIAT

    def test_precarious_employment_is_proletariat(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Precarious (gig, PTER) employment → Proletariat (borderline)."""
        result = classifier.classify_by_wealth_and_precarity(
            wealth_percentile=30.0,
            precarity=PrecarityStatus.PRECARIOUS,
        )
        assert result == ClassPosition.PROLETARIAT

    def test_marginally_attached_is_lumpen(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Marginally attached (want work, not searching) → Lumpenproletariat."""
        result = classifier.classify_by_wealth_and_precarity(
            wealth_percentile=30.0,
            precarity=PrecarityStatus.MARGINALLY_ATTACHED,
        )
        assert result == ClassPosition.LUMPENPROLETARIAT

    def test_excluded_is_lumpen(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Excluded (discouraged, incarcerated) → Lumpenproletariat."""
        result = classifier.classify_by_wealth_and_precarity(
            wealth_percentile=30.0,
            precarity=PrecarityStatus.EXCLUDED,
        )
        assert result == ClassPosition.LUMPENPROLETARIAT

    def test_precarity_ignored_above_50th_percentile(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Precarity status is irrelevant for wealth ≥ 50th percentile."""
        for precarity in PrecarityStatus:
            result = classifier.classify_by_wealth_and_precarity(
                wealth_percentile=70.0,
                precarity=precarity,
            )
            assert result == ClassPosition.LABOR_ARISTOCRACY

    def test_precarity_ignored_for_bourgeoisie(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Precarity status is irrelevant for bourgeoisie (top 1%)."""
        for precarity in PrecarityStatus:
            result = classifier.classify_by_wealth_and_precarity(
                wealth_percentile=99.5,
                precarity=precarity,
            )
            assert result == ClassPosition.BOURGEOISIE

    def test_all_precarity_levels_at_boundary(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Test classification at 50th percentile boundary."""
        # At exactly 50th percentile, precarity should NOT matter (wealth determines class)
        for precarity in PrecarityStatus:
            result = classifier.classify_by_wealth_and_precarity(
                wealth_percentile=50.0,
                precarity=precarity,
            )
            assert result == ClassPosition.LABOR_ARISTOCRACY

    def test_just_below_la_threshold(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Test classification just below LA threshold (49.9th percentile)."""
        # Just below 50th percentile, precarity DOES matter
        stable = classifier.classify_by_wealth_and_precarity(
            wealth_percentile=49.9,
            precarity=PrecarityStatus.STABLE,
        )
        assert stable == ClassPosition.PROLETARIAT

        excluded = classifier.classify_by_wealth_and_precarity(
            wealth_percentile=49.9,
            precarity=PrecarityStatus.EXCLUDED,
        )
        assert excluded == ClassPosition.LUMPENPROLETARIAT

    def test_backward_compat_with_employment(
        self,
        classifier: DefaultClassPositionClassifier,
    ) -> None:
        """Verify backward compatibility mapping between employment and precarity."""
        # employed=True should map to STABLE behavior (Proletariat)
        employed_result = classifier.classify_by_wealth_and_employment(
            wealth_percentile=30.0,
            employed=True,
        )
        precarity_result = classifier.classify_by_wealth_and_precarity(
            wealth_percentile=30.0,
            precarity=PrecarityStatus.STABLE,
        )
        assert employed_result == precarity_result == ClassPosition.PROLETARIAT

        # employed=False should map to EXCLUDED behavior (Lumpenproletariat)
        unemployed_result = classifier.classify_by_wealth_and_employment(
            wealth_percentile=30.0,
            employed=False,
        )
        excluded_result = classifier.classify_by_wealth_and_precarity(
            wealth_percentile=30.0,
            precarity=PrecarityStatus.EXCLUDED,
        )
        assert unemployed_result == excluded_result == ClassPosition.LUMPENPROLETARIAT


class TestCountyLumpenShareEstimation:
    """Tests for county-level lumpenproletariat share estimation."""

    @pytest.fixture
    def calculator(self) -> DefaultWealthProxyCalculator:
        """Provide calculator instance."""
        return DefaultWealthProxyCalculator()

    def test_wayne_higher_lumpen_than_oakland(
        self,
        calculator: DefaultWealthProxyCalculator,
    ) -> None:
        """Wayne County (Detroit) should have higher lumpen share than Oakland.

        This validates the core-periphery distinction within Detroit metro.
        Wayne (domestic periphery) has higher unemployment, NILF, and
        incarceration rates than Oakland (domestic core).
        """
        wayne_lumpen = calculator.estimate_lumpen_share("26163", 2022)
        oakland_lumpen = calculator.estimate_lumpen_share("26125", 2022)

        assert wayne_lumpen is not None
        assert oakland_lumpen is not None
        assert wayne_lumpen > oakland_lumpen

    def test_unknown_fips_returns_none(
        self,
        calculator: DefaultWealthProxyCalculator,
    ) -> None:
        """Unknown FIPS should return None (no prescribed default)."""
        # Unknown FIPS returns None - let caller handle missing data
        lumpen = calculator.estimate_lumpen_share("99999", 2022)

        assert lumpen is None

    def test_lumpen_share_positive(
        self,
        calculator: DefaultWealthProxyCalculator,
    ) -> None:
        """Lumpen share should be positive for known FIPS codes."""
        for fips in ["26163", "26125", "06037", "48201", "17031", "36061"]:
            lumpen = calculator.estimate_lumpen_share(fips, 2022)
            assert lumpen is not None
            assert lumpen > 0

    def test_lumpen_share_capped_at_bottom_50(
        self,
        calculator: DefaultWealthProxyCalculator,
    ) -> None:
        """Lumpen share should be capped at 0.50 (bottom 50% bracket)."""
        for fips in ["26163", "26125", "06037", "48201", "17031", "36061"]:
            lumpen = calculator.estimate_lumpen_share(fips, 2022)
            assert lumpen is not None
            assert lumpen <= 0.50

    def test_full_distribution_sums_correctly(
        self,
        calculator: DefaultWealthProxyCalculator,
    ) -> None:
        """Class distribution should sum to ~1.0."""
        dist = calculator.get_class_distribution_estimate("26163", 2022)

        assert dist is not None
        total = sum(dist.values())
        assert abs(total - 1.0) < 0.05  # Allow small deviation

    def test_unknown_fips_distribution_returns_none(
        self,
        calculator: DefaultWealthProxyCalculator,
    ) -> None:
        """Unknown FIPS should return None for distribution."""
        dist = calculator.get_class_distribution_estimate("99999", 2022)

        assert dist is None

    def test_precarity_indicators_accessible(
        self,
        calculator: DefaultWealthProxyCalculator,
    ) -> None:
        """Raw precarity indicators should be accessible for known FIPS."""
        indicators = calculator.get_precarity_indicators("26163", 2022)

        assert indicators is not None
        assert "u3_rate" in indicators
        assert "u6_rate" in indicators
        assert "pter_rate" in indicators
        assert "nilf_want_work" in indicators
        assert "incarceration_rate" in indicators

    def test_la_plus_lumpen_proletariat_bottom_50(
        self,
        calculator: DefaultWealthProxyCalculator,
    ) -> None:
        """LA share + proletariat + lumpen should cover non-bourgeois population.

        The bottom 50% is split between proletariat and lumpenproletariat.
        LA is the 50th-90th percentile (40% base).
        Together these three should total ~90% (with 10% bourgeoisie/PB).
        """
        dist = calculator.get_class_distribution_estimate("26163", 2022)

        assert dist is not None
        non_bourgeois = dist["labor_aristocracy"] + dist["proletariat"] + dist["lumpenproletariat"]
        # Should be approximately 90% (100% - 1% bourgeoisie - 9% PB)
        assert abs(non_bourgeois - 0.90) < 0.10
