"""Integration tests for Gamma Visibility Tensor feature.

Feature: 015-gamma-visibility-tensor
Date: 2026-02-05

Tests full pipeline: ATUS -> gamma_III -> Phi_III; ERDI -> gamma_import -> gamma_basket -> Phi_imperial.
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.gamma import (
    DefaultGammaBasketCalculator,
    DefaultGammaIIICalculator,
    DefaultGammaImportCalculator,
    DefaultShadowSubsidyCalculator,
    GammaBasket,
    GammaIII,
    GammaImport,
    ShadowSubsidy,
)


class TestFullGammaPipeline:
    """Integration test for complete gamma tensor computation."""

    def test_full_pipeline_produces_valid_results(self) -> None:
        """Test complete pipeline from data sources to shadow subsidies."""
        # Step 1: Compute gamma_III
        from tests.unit.economics.gamma.conftest import (
            MockPaidCareHoursSource,
            MockUnpaidCareHoursSource,
        )

        gamma_iii_calc = DefaultGammaIIICalculator(
            MockUnpaidCareHoursSource(),
            MockPaidCareHoursSource(),
        )
        gamma_iii_result = gamma_iii_calc.compute(2022)
        assert isinstance(gamma_iii_result, GammaIII)
        assert 0.20 <= gamma_iii_result.gamma_iii <= 0.40

        # Step 2: Compute gamma_import
        gamma_import_calc = DefaultGammaImportCalculator()
        gamma_import_result = gamma_import_calc.compute(2022)
        assert isinstance(gamma_import_result, GammaImport)
        assert 0.40 <= gamma_import_result.gamma_import <= 0.70

        # Step 3: Compute gamma_basket
        gamma_basket_calc = DefaultGammaBasketCalculator()
        gamma_basket_result = gamma_basket_calc.compute(
            2022,
            alpha=0.35,
            gamma_import=gamma_import_result.gamma_import,
        )
        assert isinstance(gamma_basket_result, GammaBasket)
        assert 0.60 <= gamma_basket_result.gamma_basket <= 0.95

        # Step 4: Compute shadow subsidies
        shadow_calc = DefaultShadowSubsidyCalculator()

        # Phi_III with MELT
        phi_iii = shadow_calc.compute_phi_iii(gamma_iii_result, melt=65.0)
        assert isinstance(phi_iii, ShadowSubsidy)
        assert phi_iii.melt_available is True
        assert phi_iii.phi_iii_dollars is not None
        assert phi_iii.phi_iii_dollars > 0

        # Phi_imperial
        phi_imperial = shadow_calc.compute_phi_imperial(gamma_basket_result, consumption=15e12)
        assert phi_imperial > 0

        # Total shadow
        total = shadow_calc.compute_total_shadow(phi_iii, phi_imperial)
        assert isinstance(total, ShadowSubsidy)
        assert total.total_shadow_dollars is not None
        assert total.total_shadow_dollars > phi_iii.phi_iii_dollars
        assert total.total_shadow_dollars > phi_imperial


@pytest.mark.integration
class TestDetroitMetroValidation:
    """Detroit Metro validation scenario for magnitude checks."""

    def test_detroit_metro_magnitudes(self) -> None:
        """Validate gamma values produce reasonable Detroit Metro results.

        Uses national aggregate values as proxy (Detroit is within national).
        """
        from tests.unit.economics.gamma.conftest import (
            MockPaidCareHoursSource,
            MockUnpaidCareHoursSource,
        )

        # National gamma_III
        gamma_iii_calc = DefaultGammaIIICalculator(
            MockUnpaidCareHoursSource(),
            MockPaidCareHoursSource(),
        )
        gamma_iii = gamma_iii_calc.compute(2022)
        assert isinstance(gamma_iii, GammaIII)

        # National gamma_import
        gamma_import_calc = DefaultGammaImportCalculator()
        gamma_import = gamma_import_calc.compute(2022)
        assert isinstance(gamma_import, GammaImport)

        # National gamma_basket
        gamma_basket_calc = DefaultGammaBasketCalculator()
        gamma_basket = gamma_basket_calc.compute(
            2022, alpha=0.35, gamma_import=gamma_import.gamma_import
        )
        assert isinstance(gamma_basket, GammaBasket)

        # Shadow subsidies
        shadow_calc = DefaultShadowSubsidyCalculator()
        phi_iii = shadow_calc.compute_phi_iii(gamma_iii, melt=65.0)
        phi_imperial = shadow_calc.compute_phi_imperial(gamma_basket, consumption=15e12)
        total = shadow_calc.compute_total_shadow(phi_iii, phi_imperial)

        # Validate magnitudes
        assert total.phi_iii_dollars is not None
        assert total.total_shadow_dollars is not None
        # Phi_III should be in reasonable range (depends on mock data)
        assert total.phi_iii_dollars > 0
        # Phi_imperial should be in $1-4T range
        assert 1.0e12 <= phi_imperial <= 4.0e12
        # Total should be substantial (both subsidies combined)
        assert total.total_shadow_dollars > 1.0e12


@pytest.mark.integration
class TestDirectionalSC002:
    """SC-002: Verify gamma_III increases when paid_care_hours increases."""

    def test_more_paid_care_increases_gamma_iii(self) -> None:
        """Directional test: increasing paid care hours raises gamma_III."""
        from tests.unit.economics.gamma.conftest import (
            MockPaidCareHoursSource,
            MockUnpaidCareHoursSource,
        )

        unpaid_source = MockUnpaidCareHoursSource({2022: 33.0})

        # Scenario A: Lower paid care hours
        paid_source_low = MockPaidCareHoursSource({2022: 10.0})
        calc_low = DefaultGammaIIICalculator(unpaid_source, paid_source_low)
        result_low = calc_low.compute(2022)

        # Scenario B: Higher paid care hours
        paid_source_high = MockPaidCareHoursSource({2022: 25.0})
        calc_high = DefaultGammaIIICalculator(unpaid_source, paid_source_high)
        result_high = calc_high.compute(2022)

        assert isinstance(result_low, GammaIII)
        assert isinstance(result_high, GammaIII)
        assert result_high.gamma_iii > result_low.gamma_iii

    def test_more_unpaid_care_decreases_gamma_iii(self) -> None:
        """Directional test: increasing unpaid care hours lowers gamma_III."""
        from tests.unit.economics.gamma.conftest import (
            MockPaidCareHoursSource,
            MockUnpaidCareHoursSource,
        )

        paid_source = MockPaidCareHoursSource({2022: 16.5})

        # Scenario A: Lower unpaid care hours
        unpaid_source_low = MockUnpaidCareHoursSource({2022: 20.0})
        calc_low = DefaultGammaIIICalculator(unpaid_source_low, paid_source)
        result_low = calc_low.compute(2022)

        # Scenario B: Higher unpaid care hours
        unpaid_source_high = MockUnpaidCareHoursSource({2022: 50.0})
        calc_high = DefaultGammaIIICalculator(unpaid_source_high, paid_source)
        result_high = calc_high.compute(2022)

        assert isinstance(result_low, GammaIII)
        assert isinstance(result_high, GammaIII)
        assert result_low.gamma_iii > result_high.gamma_iii
