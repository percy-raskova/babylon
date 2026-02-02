"""Unit tests for ClassPositionClassifier (User Story 2).

Feature: 013-melt-basket-visibility
Date: 2026-02-01

TDD Red Phase: These tests define the expected behavior for class position
classification.
"""

from __future__ import annotations

import pytest

from babylon.economics.melt import ClassPosition, DefaultClassPositionClassifier, NationalParameters


class TestClassPositionEnum:
    """Tests for ClassPosition enum definition."""

    def test_enum_has_exactly_three_values(self) -> None:
        """Test that ClassPosition enum has exactly 3 values."""
        assert len(ClassPosition) == 3

    def test_enum_values_exist(self) -> None:
        """Test that all expected enum values exist."""
        assert ClassPosition.LABOR_ARISTOCRACY is not None
        assert ClassPosition.PROLETARIAT is not None
        assert ClassPosition.SUBPROLETARIAT is not None


class TestClassPositionClassification:
    """Tests for wage-based class position classification."""

    def test_wage_above_tau_effective_is_labor_aristocracy(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that wage > τ_effective results in LABOR_ARISTOCRACY."""
        classifier = DefaultClassPositionClassifier()

        # τ_effective = 44.2, so $50/hr should be LA
        position = classifier.classify(50.0, sample_national_params)
        assert position == ClassPosition.LABOR_ARISTOCRACY

    def test_wage_between_thresholds_is_proletariat(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that V_reproduction < wage ≤ τ_effective results in PROLETARIAT."""
        classifier = DefaultClassPositionClassifier()

        # τ_effective = 44.2, V_reproduction = 12.0
        # $25/hr should be Proletariat
        position = classifier.classify(25.0, sample_national_params)
        assert position == ClassPosition.PROLETARIAT

    def test_wage_at_or_below_v_reproduction_is_subproletariat(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that wage ≤ V_reproduction results in SUBPROLETARIAT."""
        classifier = DefaultClassPositionClassifier()

        # V_reproduction = 12.0, so $8/hr should be Subproletariat
        position = classifier.classify(8.0, sample_national_params)
        assert position == ClassPosition.SUBPROLETARIAT

    def test_wage_equal_to_tau_effective_is_proletariat(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that wage == τ_effective results in PROLETARIAT (not LA).

        The classification rule is W > τ_effective for LA, so W == τ_effective
        falls into Proletariat.
        """
        classifier = DefaultClassPositionClassifier()

        # Exactly at threshold
        position = classifier.classify(44.2, sample_national_params)
        assert position == ClassPosition.PROLETARIAT

    def test_wage_equal_to_v_reproduction_is_subproletariat(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that wage == V_reproduction results in SUBPROLETARIAT.

        The classification rule is W > V_reproduction for Proletariat, so
        W == V_reproduction falls into Subproletariat.
        """
        classifier = DefaultClassPositionClassifier()

        # Exactly at V_reproduction threshold
        position = classifier.classify(12.0, sample_national_params)
        assert position == ClassPosition.SUBPROLETARIAT


class TestClassifyDistribution:
    """Tests for classify_distribution method."""

    def test_returns_all_three_class_positions(
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

    def test_distribution_calculation(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that distribution shares are calculated correctly."""
        classifier = DefaultClassPositionClassifier()

        # 2 LA, 2 Proletariat, 1 Subproletariat
        wages = [50.0, 50.0, 25.0, 25.0, 8.0]
        shares = classifier.classify_distribution(wages, sample_national_params)

        assert abs(shares[ClassPosition.LABOR_ARISTOCRACY] - 0.4) < 1e-10
        assert abs(shares[ClassPosition.PROLETARIAT] - 0.4) < 1e-10
        assert abs(shares[ClassPosition.SUBPROLETARIAT] - 0.2) < 1e-10

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
        assert abs(shares[ClassPosition.SUBPROLETARIAT] - 0.0) < 1e-10

    def test_weighted_distribution(
        self,
        sample_national_params: NationalParameters,
    ) -> None:
        """Test that weights are applied correctly to distribution."""
        classifier = DefaultClassPositionClassifier()

        # 2 wages with different weights
        wages = [50.0, 8.0]  # LA and Subproletariat
        weights = [3.0, 1.0]  # 3:1 ratio

        shares = classifier.classify_distribution(wages, sample_national_params, weights)

        # Total weight = 4, LA weight = 3, Sub weight = 1
        assert abs(shares[ClassPosition.LABOR_ARISTOCRACY] - 0.75) < 1e-10
        assert abs(shares[ClassPosition.PROLETARIAT] - 0.0) < 1e-10
        assert abs(shares[ClassPosition.SUBPROLETARIAT] - 0.25) < 1e-10

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
