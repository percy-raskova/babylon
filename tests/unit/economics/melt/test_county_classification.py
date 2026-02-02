"""Unit tests for County Workforce Classification (User Story 4).

Feature: 013-melt-basket-visibility
Date: 2026-02-01

TDD Red Phase: These tests define the expected behavior for aggregating
individual wage classifications to county-level class distributions.

Note: The core classify_distribution functionality is tested in
test_class_position.py. This file provides additional county-specific
tests including weighted aggregation and Detroit Metro validation case.
"""

from __future__ import annotations

import pytest

from babylon.economics.melt import ClassPosition, DefaultClassPositionClassifier, NationalParameters


class TestCountyDistributionAggregation:
    """Tests for county-level class distribution aggregation."""

    def test_classify_distribution_returns_all_class_positions(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that result dict contains all 3 ClassPosition keys."""
        classifier = DefaultClassPositionClassifier()

        wages = [50.0, 25.0, 8.0]
        shares = classifier.classify_distribution(wages, sample_national_params)

        assert ClassPosition.LABOR_ARISTOCRACY in shares
        assert ClassPosition.PROLETARIAT in shares
        assert ClassPosition.SUBPROLETARIAT in shares

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

    def test_empty_wage_list_returns_equal_shares(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that empty wage list returns equal shares (1/3 each)."""
        classifier = DefaultClassPositionClassifier()

        shares = classifier.classify_distribution([], sample_national_params)

        expected_share = 1.0 / 3.0
        for position in ClassPosition:
            assert abs(shares[position] - expected_share) < 1e-10

    def test_single_wage_returns_100_percent_in_appropriate_class(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that single wage returns 100% in appropriate class."""
        classifier = DefaultClassPositionClassifier()

        # Single LA wage
        shares = classifier.classify_distribution([50.0], sample_national_params)

        assert abs(shares[ClassPosition.LABOR_ARISTOCRACY] - 1.0) < 1e-10
        assert abs(shares[ClassPosition.PROLETARIAT] - 0.0) < 1e-10
        assert abs(shares[ClassPosition.SUBPROLETARIAT] - 0.0) < 1e-10


class TestEmploymentWeightedAggregation:
    """Tests for employment-weighted county classification."""

    def test_weighted_distribution_calculation(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that weights are applied correctly to distribution.

        With 2 wages (LA and Subproletariat) and weights 3:1,
        LA share should be 0.75, Subproletariat 0.25.
        """
        classifier = DefaultClassPositionClassifier()

        wages = [50.0, 8.0]  # LA and Subproletariat
        weights = [3.0, 1.0]  # 3:1 ratio

        shares = classifier.classify_distribution(wages, sample_national_params, weights)

        # Total weight = 4, LA weight = 3, Sub weight = 1
        assert abs(shares[ClassPosition.LABOR_ARISTOCRACY] - 0.75) < 1e-10
        assert abs(shares[ClassPosition.PROLETARIAT] - 0.0) < 1e-10
        assert abs(shares[ClassPosition.SUBPROLETARIAT] - 0.25) < 1e-10

    def test_equal_weights_same_as_unweighted(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that equal weights produce same result as unweighted."""
        classifier = DefaultClassPositionClassifier()

        wages = [50.0, 25.0, 8.0]

        unweighted = classifier.classify_distribution(wages, sample_national_params)
        weighted = classifier.classify_distribution(wages, sample_national_params, [1.0, 1.0, 1.0])

        for position in ClassPosition:
            assert abs(unweighted[position] - weighted[position]) < 1e-10

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


class TestDetroitMetroValidationCase:
    """Tests for Detroit Metro validation case (FR-011).

    FIPS Codes:
    - Wayne County (Detroit proper): 26163
    - Oakland County (suburbs): 26125

    Expected: Oakland LA share > Wayne LA share due to suburban wealth
    concentration in knowledge economy jobs.

    This test uses mock wage distributions representative of the
    Detroit Metro area class structure per QCEW data patterns.
    """

    def test_oakland_la_share_exceeds_wayne(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that Oakland (suburbs) has higher LA share than Wayne (urban).

        Mock data represents:
        - Wayne County: More manufacturing, service sector (lower wages)
        - Oakland County: Tech, finance, healthcare management (higher wages)
        """
        classifier = DefaultClassPositionClassifier()

        # Wayne County (Detroit) - representative wage distribution
        # More workers below τ_effective = $44.2
        wayne_wages = [
            15.0,
            15.0,
            18.0,
            20.0,
            22.0,  # 5 Subproletariat/low-Prolet
            25.0,
            28.0,
            30.0,
            32.0,
            35.0,  # 5 Proletariat
            40.0,
            42.0,
            45.0,
            50.0,
            55.0,  # 5 mixed (some LA)
        ]

        # Oakland County (suburbs) - representative wage distribution
        # More knowledge economy, management jobs
        oakland_wages = [
            18.0,
            22.0,
            25.0,
            28.0,
            30.0,  # 5 lower wage
            35.0,
            40.0,
            45.0,
            50.0,
            55.0,  # 5 middle-upper
            60.0,
            65.0,
            70.0,
            80.0,
            95.0,  # 5 high wage (mostly LA)
        ]

        wayne_shares = classifier.classify_distribution(wayne_wages, sample_national_params)
        oakland_shares = classifier.classify_distribution(oakland_wages, sample_national_params)

        # Oakland should have higher Labor Aristocracy share
        assert (
            oakland_shares[ClassPosition.LABOR_ARISTOCRACY]
            > wayne_shares[ClassPosition.LABOR_ARISTOCRACY]
        )

        # Wayne should have higher Subproletariat share
        assert (
            wayne_shares[ClassPosition.SUBPROLETARIAT]
            >= oakland_shares[ClassPosition.SUBPROLETARIAT]
        )

    def test_fips_code_documentation(self) -> None:
        """Document FIPS codes for Detroit Metro counties.

        This test serves as documentation reference for the validation case.
        FIPS codes are used for BLS QCEW data queries.
        """
        # FIPS codes for Detroit Metro validation case
        wayne_county_fips = "26163"  # Detroit proper
        oakland_county_fips = "26125"  # Northern suburbs

        # Verify format (5-digit state+county FIPS)
        assert len(wayne_county_fips) == 5
        assert len(oakland_county_fips) == 5
        assert wayne_county_fips[:2] == "26"  # Michigan state code
        assert oakland_county_fips[:2] == "26"  # Michigan state code


class TestCountyLevelScenarios:
    """Tests for various county-level classification scenarios."""

    def test_uniform_wage_county(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test county where all workers earn same wage."""
        classifier = DefaultClassPositionClassifier()

        # All workers earn $30/hour (Proletariat)
        wages = [30.0] * 100
        shares = classifier.classify_distribution(wages, sample_national_params)

        assert shares[ClassPosition.LABOR_ARISTOCRACY] == 0.0
        assert shares[ClassPosition.PROLETARIAT] == 1.0
        assert shares[ClassPosition.SUBPROLETARIAT] == 0.0

    def test_bimodal_wage_distribution(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test county with bimodal wage distribution (service + professional).

        Common pattern in university towns, state capitals, etc.

        With V_reproduction = $12 and τ_effective = $44.2:
        - Service wages $8-11: Subproletariat (≤$12)
        - Service wages $13-20: Proletariat (>$12, ≤$44.2)
        - Professional $50-80: Labor Aristocracy (>$44.2)
        """
        classifier = DefaultClassPositionClassifier()

        # Service sector: $8-11/hour (50 workers) - Subproletariat
        service_wages = [8.0, 9.0, 10.0, 11.0, 11.5] * 10

        # Professional sector: $50-80/hour (50 workers) - Labor Aristocracy
        professional_wages = [50.0, 55.0, 60.0, 70.0, 80.0] * 10

        wages = service_wages + professional_wages
        shares = classifier.classify_distribution(wages, sample_national_params)

        # Should have minimal Proletariat, mostly LA and Subproletariat
        assert shares[ClassPosition.LABOR_ARISTOCRACY] == 0.5
        assert shares[ClassPosition.SUBPROLETARIAT] == 0.5
        assert shares[ClassPosition.PROLETARIAT] == 0.0
