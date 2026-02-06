"""Integration tests for MELT and Basket Visibility module (Feature 013).

Feature: 013-melt-basket-visibility
Date: 2026-02-01

These tests verify the full pipeline integration:
MELT → γ_basket → NationalParameters → ClassPosition → Φ_hour

This file addresses:
- T033: Full pipeline integration tests
- T034: Detroit Metro validation case
"""

from __future__ import annotations

import pytest

from babylon.economics.melt import (
    ClassPosition,
    DefaultBasketVisibilityCalculator,
    DefaultClassPositionClassifier,
    DefaultImperialRentCalculator,
    DefaultMELTCalculator,
    NationalParameters,
)
from babylon.economics.tensor import NoDataSentinel

# Import mock sources from unit test conftest
from tests.unit.economics.melt.conftest import MockBEADataSource, MockQCEWDataSource


@pytest.mark.integration
class TestFullPipelineIntegration:
    """Test complete MELT → γ_basket → NationalParameters → ClassPosition → Φ_hour pipeline."""

    def test_full_pipeline_with_mock_data(self) -> None:
        """Test full pipeline from MELT computation through imperial rent.

        Pipeline:
        1. MELTCalculator computes τ from GDP/employment
        2. BasketVisibilityCalculator computes γ_basket
        3. NationalParameters bundles τ, γ_basket, τ_effective
        4. ClassPositionClassifier classifies wages
        5. ImperialRentCalculator computes Φ_hour
        """
        # Step 1: Compute MELT (τ)
        bea_source = MockBEADataSource()
        qcew_source = MockQCEWDataSource()
        melt_calc = DefaultMELTCalculator(bea_source, qcew_source)

        tau_result = melt_calc.get_melt(2022)
        assert not isinstance(tau_result, NoDataSentinel)
        tau = tau_result

        # Validate τ is reasonable
        valid, msg = melt_calc.validate_melt(tau)
        assert valid, f"τ validation failed: {msg}"

        # Step 2: Compute basket visibility (γ_basket)
        basket_calc = DefaultBasketVisibilityCalculator()
        gamma_basket, estimated = basket_calc.get_gamma_basket(2022)

        # Validate γ_basket is reasonable
        valid, msg = basket_calc.validate_gamma_basket(gamma_basket)
        assert valid, f"γ_basket validation failed: {msg}"

        # Step 3: Construct NationalParameters
        tau_effective = tau * gamma_basket
        params = NationalParameters(
            year=2022,
            tau=tau,
            alpha=basket_calc.mvp_alpha,
            gamma_import=basket_calc.mvp_gamma_import,
            gamma_basket=gamma_basket,
            tau_effective=tau_effective,
            v_reproduction=12.0,  # Fixed for MVP
            estimated=estimated,
        )

        # Verify theoretical consistency
        warnings = params.validate_theoretical_consistency()
        # We expect no warnings with properly computed values
        if warnings:
            pytest.fail(f"NationalParameters consistency warnings: {warnings}")

        # Step 4: Classify wages using parameters
        class_calc = DefaultClassPositionClassifier()

        # Test classification at different wage levels
        test_wages = [8.0, 25.0, tau_effective, 65.0, 100.0]
        for wage in test_wages:
            position = class_calc.classify(wage, params)
            assert isinstance(position, ClassPosition)

        # Step 5: Compute imperial rent
        rent_calc = DefaultImperialRentCalculator()

        # Break-even verification
        phi_at_threshold = rent_calc.compute_phi_hour(tau_effective, params)
        assert abs(phi_at_threshold) < 0.01, f"Break-even failed: Φ_hour={phi_at_threshold}"

        # LA verification: wage > τ_effective should have Φ > 0
        phi_la = rent_calc.compute_phi_hour(65.0, params)
        assert phi_la > 0, f"LA should extract labor: Φ_hour={phi_la}"

        # Proletariat verification: wage < τ_effective should have Φ < 0
        phi_prolet = rent_calc.compute_phi_hour(25.0, params)
        assert phi_prolet < 0, f"Proletariat should be exploited: Φ_hour={phi_prolet}"

    def test_national_parameters_construction_from_calculators(self) -> None:
        """Test constructing NationalParameters from calculator outputs."""
        # Get τ from MELT calculator
        bea_source = MockBEADataSource()
        qcew_source = MockQCEWDataSource()
        melt_calc = DefaultMELTCalculator(bea_source, qcew_source)
        tau = melt_calc.get_melt(2022)
        assert isinstance(tau, float)

        # Get γ_basket from basket calculator
        basket_calc = DefaultBasketVisibilityCalculator()
        gamma_basket, estimated = basket_calc.get_gamma_basket(2022)

        # Construct parameters
        params = NationalParameters(
            year=2022,
            tau=tau,
            alpha=basket_calc.mvp_alpha,
            gamma_import=basket_calc.mvp_gamma_import,
            gamma_basket=gamma_basket,
            tau_effective=tau * gamma_basket,
            v_reproduction=12.0,
            estimated=estimated,
        )

        # Verify parameters are usable by classifiers
        class_calc = DefaultClassPositionClassifier()
        rent_calc = DefaultImperialRentCalculator()

        position = class_calc.classify(50.0, params)
        phi = rent_calc.compute_phi_hour(50.0, params)

        # Both should work without error
        assert isinstance(position, ClassPosition)
        assert isinstance(phi, float)


@pytest.mark.integration
class TestDetroitMetroValidation:
    """Integration tests for Detroit Metro validation case.

    This test validates that the system correctly identifies
    Oakland County (suburbs) as having higher Labor Aristocracy
    share than Wayne County (Detroit proper), consistent with
    the economic geography of the Detroit Metro area.

    FIPS Codes:
    - Wayne County (Detroit proper): 26163
    - Oakland County (suburbs): 26125
    """

    def test_detroit_metro_validation_full_pipeline(self) -> None:
        """Test Detroit Metro validation through full pipeline.

        This is an integration test that uses the full calculator
        chain to validate the class composition difference between
        Wayne and Oakland counties.
        """
        # Set up calculators
        bea_source = MockBEADataSource()
        qcew_source = MockQCEWDataSource()
        melt_calc = DefaultMELTCalculator(bea_source, qcew_source)
        basket_calc = DefaultBasketVisibilityCalculator()
        class_calc = DefaultClassPositionClassifier()

        # Get national parameters
        tau = melt_calc.get_melt(2022)
        assert isinstance(tau, float)

        gamma_basket, estimated = basket_calc.get_gamma_basket(2022)

        params = NationalParameters(
            year=2022,
            tau=tau,
            alpha=basket_calc.mvp_alpha,
            gamma_import=basket_calc.mvp_gamma_import,
            gamma_basket=gamma_basket,
            tau_effective=tau * gamma_basket,
            v_reproduction=12.0,
            estimated=estimated,
        )

        # Mock wage distributions representing Detroit Metro counties
        # Wayne: more manufacturing, service (lower wages)
        wayne_wages = [
            15.0,
            15.0,
            18.0,
            20.0,
            22.0,  # Lower wages
            25.0,
            28.0,
            30.0,
            32.0,
            35.0,  # Middle wages
            40.0,
            42.0,
            45.0,
            50.0,
            55.0,  # Upper wages
        ]

        # Oakland: more tech, finance, management (higher wages)
        oakland_wages = [
            18.0,
            22.0,
            25.0,
            28.0,
            30.0,  # Lower wages
            35.0,
            40.0,
            45.0,
            50.0,
            55.0,  # Middle wages
            60.0,
            65.0,
            70.0,
            80.0,
            95.0,  # Upper wages (more LA)
        ]

        # Classify county distributions
        wayne_shares = class_calc.classify_distribution(wayne_wages, params)
        oakland_shares = class_calc.classify_distribution(oakland_wages, params)

        # Oakland should have higher LA share
        assert (
            oakland_shares[ClassPosition.LABOR_ARISTOCRACY]
            > wayne_shares[ClassPosition.LABOR_ARISTOCRACY]
        ), (
            f"Oakland LA share ({oakland_shares[ClassPosition.LABOR_ARISTOCRACY]:.2%}) "
            f"should exceed Wayne ({wayne_shares[ClassPosition.LABOR_ARISTOCRACY]:.2%})"
        )


@pytest.mark.integration
class TestQuickstartExamples:
    """Test that quickstart.md examples work correctly."""

    def test_basic_melt_computation(self) -> None:
        """Test basic MELT computation example from quickstart."""
        from babylon.economics.melt import DefaultMELTCalculator
        from tests.unit.economics.melt.conftest import (
            MockBEADataSource,
            MockQCEWDataSource,
        )

        # Create calculator with mock data
        calculator = DefaultMELTCalculator(MockBEADataSource(), MockQCEWDataSource())

        # Compute MELT
        tau = calculator.get_melt(2022)

        # Should return a float, not sentinel
        assert isinstance(tau, float)
        # Should be in reasonable range
        assert 50.0 < tau < 150.0

    def test_class_position_classification(self) -> None:
        """Test class position classification example from quickstart."""
        from babylon.economics.melt import (
            ClassPosition,
            DefaultClassPositionClassifier,
            NationalParameters,
        )

        # Create parameters (MVP mode)
        params = NationalParameters(
            year=2022,
            tau=65.0,
            alpha=0.25,
            gamma_import=0.35,
            gamma_basket=0.68,
            tau_effective=44.2,
            v_reproduction=12.0,
            estimated=True,
        )

        # Classify wages
        classifier = DefaultClassPositionClassifier()

        assert classifier.classify(50.0, params) == ClassPosition.LABOR_ARISTOCRACY
        assert classifier.classify(25.0, params) == ClassPosition.PROLETARIAT
        assert classifier.classify(8.0, params) == ClassPosition.LUMPENPROLETARIAT

    def test_imperial_rent_computation(self) -> None:
        """Test imperial rent computation example from quickstart."""
        from babylon.economics.melt import (
            DefaultImperialRentCalculator,
            NationalParameters,
        )

        params = NationalParameters(
            year=2022,
            tau=65.0,
            alpha=0.25,
            gamma_import=0.35,
            gamma_basket=0.68,
            tau_effective=44.2,
            v_reproduction=12.0,
            estimated=True,
        )

        calculator = DefaultImperialRentCalculator()

        # LA wage: should have positive Φ
        phi_la = calculator.compute_phi_hour(65.0, params)
        assert phi_la > 0

        # Break-even at τ_effective
        phi_threshold = calculator.compute_phi_hour(44.2, params)
        assert abs(phi_threshold) < 0.01

    def test_basket_visibility_mvp_mode(self) -> None:
        """Test basket visibility MVP mode example from quickstart."""
        from babylon.economics.melt import DefaultBasketVisibilityCalculator

        calculator = DefaultBasketVisibilityCalculator()

        # MVP mode: no parameters provided
        gamma, estimated = calculator.get_gamma_basket(2022)

        assert gamma == 0.68
        assert estimated is True

        # With explicit parameters
        gamma_explicit, estimated_explicit = calculator.get_gamma_basket(
            2022, alpha=0.25, gamma_import=0.35
        )

        assert estimated_explicit is False
        assert 0.65 < gamma_explicit < 0.70  # Should be ~0.683


@pytest.mark.integration
class TestModuleImportIntegration:
    """Test that module imports work correctly from various entry points."""

    def test_import_from_economics_package(self) -> None:
        """Test imports from babylon.economics package."""
        from babylon.economics import (
            ClassPosition,
            NationalParameters,
        )

        assert ClassPosition.LABOR_ARISTOCRACY is not None
        assert NationalParameters is not None

    def test_import_from_melt_module(self) -> None:
        """Test imports from babylon.economics.melt module."""
        from babylon.economics.melt import (
            ClassPosition,
            DefaultBasketVisibilityCalculator,
            DefaultClassPositionClassifier,
            DefaultImperialRentCalculator,
            DefaultMELTCalculator,
            NationalParameters,
        )

        # All imports should work
        assert ClassPosition is not None
        assert NationalParameters is not None
        assert DefaultMELTCalculator is not None
        assert DefaultBasketVisibilityCalculator is not None
        assert DefaultClassPositionClassifier is not None
        assert DefaultImperialRentCalculator is not None

    def test_nodata_sentinel_integration(self) -> None:
        """Test that NoDataSentinel from tensor module integrates correctly."""
        from babylon.economics.melt import DefaultMELTCalculator
        from babylon.economics.tensor import NoDataSentinel
        from tests.unit.economics.melt.conftest import (
            MockBEADataSource,
            MockQCEWDataSource,
        )

        # Create calculator with no data for 2025
        calculator = DefaultMELTCalculator(
            MockBEADataSource({2022: 25_000_000_000_000.0}),
            MockQCEWDataSource({2022: 150_000_000}),
        )

        # Should return NoDataSentinel for year outside data range
        result = calculator.get_melt(2025)

        assert isinstance(result, NoDataSentinel)
        assert "2025" in result.reason
