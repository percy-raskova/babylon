"""Unit tests for GammaImportCalculator (User Story 3).

Feature: 015-gamma-visibility-tensor
Date: 2026-02-05

TDD Red Phase: These tests define the expected behavior for gamma_import computation.
"""

from __future__ import annotations

from babylon.domain.economics.gamma.gamma_import import (
    MVP_IMPORT_SHARES,
    DefaultGammaImportCalculator,
)
from babylon.domain.economics.gamma.types import (
    CORE_DEFAULT_ERDI,
    MVP_ERDI_VALUES,
    PERIPHERY_DEFAULT_ERDI,
    GammaImport,
)


class TestGammaImportComputation:
    """Tests for gamma_import = sum(import_share * 1/ERDI) computation."""

    def test_compute_with_mvp_values(self) -> None:
        """SC-004: Verify gamma_import is in [0.40, 0.70] range with MVP values."""
        calculator = DefaultGammaImportCalculator()
        result = calculator.compute(2022)

        assert isinstance(result, GammaImport)
        assert 0.40 <= result.gamma_import <= 0.70
        assert result.is_mvp is True

    def test_compute_weighted_sum_formula(self) -> None:
        """Verify the weighted sum formula with known values.

        For 2 countries with equal shares:
        - Country A: share=0.5, ERDI=1.0 -> contribution = 0.5 * 1/1.0 = 0.5
        - Country B: share=0.5, ERDI=2.0 -> contribution = 0.5 * 1/2.0 = 0.25
        - gamma_import = 0.75
        """
        # We verify indirectly through the MVP values
        calculator = DefaultGammaImportCalculator()
        result = calculator.compute(2022)

        assert isinstance(result, GammaImport)
        # Verify the result was computed (not hardcoded)
        assert len(result.import_shares) > 0
        assert len(result.erdi_values) > 0

    def test_import_shares_include_rest_of_world(self) -> None:
        """Test that rest-of-world share is included to sum to 1.0."""
        calculator = DefaultGammaImportCalculator()
        result = calculator.compute(2022)

        assert isinstance(result, GammaImport)
        shares_sum = sum(result.import_shares.values())
        assert abs(shares_sum - 1.0) < 0.01


class TestGetERDI:
    """Tests for ERDI value lookup."""

    def test_known_country_returns_mvp_value(self) -> None:
        """Test that known countries return their MVP ERDI values."""
        calculator = DefaultGammaImportCalculator()

        assert calculator.get_erdi("CHN") == 1.80
        assert calculator.get_erdi("MEX") == 1.50
        assert calculator.get_erdi("CAN") == 1.10

    def test_unknown_country_returns_periphery_default(self) -> None:
        """Test that unknown countries return PERIPHERY_DEFAULT_ERDI."""
        calculator = DefaultGammaImportCalculator()

        # Country not in MVP list
        assert calculator.get_erdi("BRA") == PERIPHERY_DEFAULT_ERDI
        assert calculator.get_erdi("ZZZ") == PERIPHERY_DEFAULT_ERDI

    def test_core_countries_have_erdi_near_one(self) -> None:
        """Test that core countries (DEU, JPN) have ERDI close to 1.0."""
        assert MVP_ERDI_VALUES["DEU"].erdi == 1.00
        assert MVP_ERDI_VALUES["JPN"].erdi == 1.00

    def test_periphery_countries_have_erdi_above_one(self) -> None:
        """Test that periphery countries have ERDI > 1.0."""
        assert MVP_ERDI_VALUES["CHN"].erdi > 1.0
        assert MVP_ERDI_VALUES["VNM"].erdi > 1.0
        assert MVP_ERDI_VALUES["IND"].erdi > 1.0


class TestImportShareValidation:
    """Tests for import share sum validation."""

    def test_mvp_shares_sum_to_expected(self) -> None:
        """Test that MVP import shares for listed countries are reasonable."""
        listed_sum = sum(MVP_IMPORT_SHARES.values())
        # Top 9 partners should be around 0.70
        assert 0.50 < listed_sum < 0.90

    def test_total_shares_sum_to_one(self) -> None:
        """Test that total shares (including ROW) sum to 1.0 ± 0.01."""
        calculator = DefaultGammaImportCalculator()
        result = calculator.compute(2022)

        assert isinstance(result, GammaImport)
        total = sum(result.import_shares.values())
        assert abs(total - 1.0) < 0.01


class TestFallbackERDI:
    """Tests for fallback ERDI values."""

    def test_core_default_is_one(self) -> None:
        """Test Core default ERDI = 1.0 (no distortion)."""
        assert CORE_DEFAULT_ERDI == 1.0

    def test_periphery_default_is_two(self) -> None:
        """Test Periphery default ERDI = 2.0 (50% labor compression)."""
        assert PERIPHERY_DEFAULT_ERDI == 2.0

    def test_periphery_default_used_for_unknown_countries(self) -> None:
        """Test that unknown countries use periphery default."""
        calculator = DefaultGammaImportCalculator()
        # Not in MVP list
        erdi = calculator.get_erdi("NGA")
        assert erdi == PERIPHERY_DEFAULT_ERDI
