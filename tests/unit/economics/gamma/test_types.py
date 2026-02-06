"""Unit tests for Gamma Visibility Tensor type definitions.

Feature: 015-gamma-visibility-tensor
Date: 2026-02-05

Tests for Pydantic models: GammaIII, GammaImport, GammaBasket, ShadowSubsidy,
ERDIData, and the weighted_average_gamma utility function.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.economics.gamma.types import (
    CORE_DEFAULT_ERDI,
    MVP_ERDI_VALUES,
    PERIPHERY_DEFAULT_ERDI,
    ERDIData,
    GammaBasket,
    GammaIII,
    GammaImport,
    ShadowSubsidy,
    weighted_average_gamma,
)


class TestGammaIIIModel:
    """Tests for GammaIII Pydantic model."""

    def test_valid_construction(self) -> None:
        """Test GammaIII with typical values."""
        result = GammaIII(
            year=2022,
            paid_care_hours=16.5,
            unpaid_care_hours=33.0,
            gamma_iii=0.333,
            fortunati_exploitation=2.003,
        )
        assert result.year == 2022
        assert result.paid_care_hours == 16.5
        assert result.unpaid_care_hours == 33.0
        assert result.gamma_iii == 0.333
        assert result.fortunati_exploitation == 2.003
        assert result.is_estimated is False

    def test_frozen_immutability(self) -> None:
        """Test that GammaIII is immutable (frozen=True)."""
        result = GammaIII(
            year=2022,
            paid_care_hours=16.5,
            unpaid_care_hours=33.0,
            gamma_iii=0.333,
            fortunati_exploitation=2.0,
        )
        with pytest.raises(ValidationError):
            result.gamma_iii = 0.5  # type: ignore[misc]

    def test_year_below_minimum_rejected(self) -> None:
        """Test that year below 2003 (ATUS start) is rejected."""
        with pytest.raises(ValidationError, match="greater than or equal to 2003"):
            GammaIII(
                year=2002,
                paid_care_hours=16.5,
                unpaid_care_hours=33.0,
                gamma_iii=0.333,
                fortunati_exploitation=2.0,
            )

    def test_gamma_iii_below_zero_rejected(self) -> None:
        """Test that gamma_iii < 0 is rejected."""
        with pytest.raises(ValidationError):
            GammaIII(
                year=2022,
                paid_care_hours=16.5,
                unpaid_care_hours=33.0,
                gamma_iii=-0.1,
                fortunati_exploitation=2.0,
            )

    def test_gamma_iii_above_one_rejected(self) -> None:
        """Test that gamma_iii > 1 is rejected."""
        with pytest.raises(ValidationError):
            GammaIII(
                year=2022,
                paid_care_hours=16.5,
                unpaid_care_hours=33.0,
                gamma_iii=1.1,
                fortunati_exploitation=2.0,
            )

    def test_boundary_gamma_iii_zero(self) -> None:
        """Test gamma_iii = 0.0 is valid (fully invisible)."""
        result = GammaIII(
            year=2022,
            paid_care_hours=0.0,
            unpaid_care_hours=33.0,
            gamma_iii=0.0,
            fortunati_exploitation=float("inf"),
        )
        assert result.gamma_iii == 0.0

    def test_boundary_gamma_iii_one(self) -> None:
        """Test gamma_iii = 1.0 is valid (fully visible)."""
        result = GammaIII(
            year=2022,
            paid_care_hours=33.0,
            unpaid_care_hours=0.0,
            gamma_iii=1.0,
            fortunati_exploitation=0.0,
        )
        assert result.gamma_iii == 1.0

    def test_is_estimated_flag(self) -> None:
        """Test is_estimated flag defaults to False."""
        result = GammaIII(
            year=2022,
            paid_care_hours=16.5,
            unpaid_care_hours=33.0,
            gamma_iii=0.333,
            fortunati_exploitation=2.0,
            is_estimated=True,
        )
        assert result.is_estimated is True


class TestGammaImportModel:
    """Tests for GammaImport Pydantic model."""

    def test_valid_construction(self) -> None:
        """Test GammaImport with typical values."""
        result = GammaImport(
            year=2022,
            import_shares={"CHN": 0.18, "MEX": 0.14},
            erdi_values={"CHN": 1.80, "MEX": 1.50},
            gamma_import=0.65,
        )
        assert result.year == 2022
        assert result.gamma_import == 0.65
        assert result.is_mvp is True

    def test_frozen_immutability(self) -> None:
        """Test that GammaImport is immutable."""
        result = GammaImport(
            year=2022,
            import_shares={"CHN": 0.50},
            erdi_values={"CHN": 1.80},
            gamma_import=0.65,
        )
        with pytest.raises(ValidationError):
            result.gamma_import = 0.7  # type: ignore[misc]

    def test_gamma_import_zero_rejected(self) -> None:
        """Test that gamma_import = 0 is rejected (gt=0.0)."""
        with pytest.raises(ValidationError):
            GammaImport(
                year=2022,
                import_shares={"CHN": 1.0},
                erdi_values={"CHN": 1.80},
                gamma_import=0.0,
            )

    def test_gamma_import_above_one_rejected(self) -> None:
        """Test that gamma_import > 1 is rejected."""
        with pytest.raises(ValidationError):
            GammaImport(
                year=2022,
                import_shares={"CHN": 1.0},
                erdi_values={"CHN": 1.80},
                gamma_import=1.1,
            )


class TestGammaBasketModel:
    """Tests for GammaBasket Pydantic model."""

    def test_valid_construction(self) -> None:
        """Test GammaBasket with typical values."""
        result = GammaBasket(
            year=2022,
            alpha=0.35,
            gamma_import=0.65,
            gamma_basket=0.74,
        )
        assert result.year == 2022
        assert result.alpha == 0.35
        assert result.gamma_import == 0.65
        assert result.gamma_basket == 0.74

    def test_frozen_immutability(self) -> None:
        """Test that GammaBasket is immutable."""
        result = GammaBasket(
            year=2022,
            alpha=0.35,
            gamma_import=0.65,
            gamma_basket=0.74,
        )
        with pytest.raises(ValidationError):
            result.gamma_basket = 0.8  # type: ignore[misc]

    def test_alpha_boundary_zero(self) -> None:
        """Test alpha=0 (no imports) is valid."""
        result = GammaBasket(
            year=2022,
            alpha=0.0,
            gamma_import=0.65,
            gamma_basket=1.0,
        )
        assert result.alpha == 0.0

    def test_alpha_boundary_one(self) -> None:
        """Test alpha=1 (all imports) is valid."""
        result = GammaBasket(
            year=2022,
            alpha=1.0,
            gamma_import=0.65,
            gamma_basket=0.65,
        )
        assert result.alpha == 1.0


class TestShadowSubsidyModel:
    """Tests for ShadowSubsidy Pydantic model."""

    def test_valid_construction_with_melt(self) -> None:
        """Test ShadowSubsidy with MELT available."""
        result = ShadowSubsidy(
            year=2022,
            phi_iii_dollars=2.2e12,
            phi_iii_labor_hours=33.0,
            phi_imperial=3.9e12,
            total_shadow_dollars=6.1e12,
            melt_available=True,
        )
        assert result.phi_iii_dollars == 2.2e12
        assert result.phi_iii_labor_hours == 33.0
        assert result.phi_imperial == 3.9e12
        assert result.total_shadow_dollars == 6.1e12
        assert result.melt_available is True

    def test_valid_construction_without_melt(self) -> None:
        """Test ShadowSubsidy without MELT (labor-hours only)."""
        result = ShadowSubsidy(
            year=2022,
            phi_iii_labor_hours=33.0,
        )
        assert result.phi_iii_dollars is None
        assert result.phi_iii_labor_hours == 33.0
        assert result.phi_imperial == 0.0
        assert result.total_shadow_dollars is None
        assert result.melt_available is False

    def test_frozen_immutability(self) -> None:
        """Test that ShadowSubsidy is immutable."""
        result = ShadowSubsidy(
            year=2022,
            phi_iii_labor_hours=33.0,
        )
        with pytest.raises(ValidationError):
            result.phi_iii_labor_hours = 40.0  # type: ignore[misc]


class TestERDIDataModel:
    """Tests for ERDIData Pydantic model."""

    def test_valid_construction(self) -> None:
        """Test ERDIData with typical values."""
        result = ERDIData(
            country_code="CHN",
            country_name="China",
            erdi=1.80,
            reference_year=2019,
        )
        assert result.country_code == "CHN"
        assert result.erdi == 1.80
        assert result.source == "Penn World Tables 10.01"

    def test_erdi_zero_rejected(self) -> None:
        """Test that ERDI = 0 is rejected."""
        with pytest.raises(ValidationError):
            ERDIData(
                country_code="TST",
                country_name="Test",
                erdi=0.0,
                reference_year=2019,
            )

    def test_country_code_too_short_rejected(self) -> None:
        """Test that single-char country code is rejected."""
        with pytest.raises(ValidationError):
            ERDIData(
                country_code="X",
                country_name="Test",
                erdi=1.0,
                reference_year=2019,
            )


class TestMVPConstants:
    """Tests for MVP constant definitions."""

    def test_mvp_erdi_values_populated(self) -> None:
        """Test that MVP ERDI values contain expected countries."""
        assert "CHN" in MVP_ERDI_VALUES
        assert "MEX" in MVP_ERDI_VALUES
        assert "CAN" in MVP_ERDI_VALUES
        assert len(MVP_ERDI_VALUES) == 9

    def test_mvp_erdi_values_types(self) -> None:
        """Test that MVP ERDI values are ERDIData instances."""
        for country_code, erdi_data in MVP_ERDI_VALUES.items():
            assert isinstance(erdi_data, ERDIData)
            assert erdi_data.country_code == country_code
            assert erdi_data.erdi > 0.0

    def test_core_and_periphery_defaults(self) -> None:
        """Test fallback ERDI constants."""
        assert CORE_DEFAULT_ERDI == 1.0
        assert PERIPHERY_DEFAULT_ERDI == 2.0


class TestWeightedAverageGamma:
    """Tests for weighted_average_gamma utility function (T012b)."""

    def test_uniform_weights(self) -> None:
        """Test that uniform weights produce simple average."""
        result = weighted_average_gamma([0.30, 0.40], [1.0, 1.0])
        assert abs(result - 0.35) < 1e-10

    def test_intensive_aggregation(self) -> None:
        """Test that result is intensive (not extensive).

        Doubling all weights should NOT change the result.
        This verifies sum(w*g)/sum(w), not sum(w*g).
        """
        result_1x = weighted_average_gamma([0.30, 0.35], [100.0, 200.0])
        result_2x = weighted_average_gamma([0.30, 0.35], [200.0, 400.0])
        assert abs(result_1x - result_2x) < 1e-10

    def test_single_value(self) -> None:
        """Test single value returns itself regardless of weight."""
        result = weighted_average_gamma([0.42], [999.0])
        assert abs(result - 0.42) < 1e-10

    def test_weighted_result(self) -> None:
        """Test weighted average with asymmetric weights."""
        # 0.30 * 100 + 0.35 * 200 = 30 + 70 = 100 / 300 = 0.333...
        result = weighted_average_gamma([0.30, 0.35], [100.0, 200.0])
        expected = (0.30 * 100.0 + 0.35 * 200.0) / 300.0
        assert abs(result - expected) < 1e-10

    def test_mismatched_lengths_raises_error(self) -> None:
        """Test that mismatched list lengths raise ValueError."""
        with pytest.raises(ValueError, match="same length"):
            weighted_average_gamma([0.30, 0.35], [100.0])

    def test_zero_total_weight_raises_error(self) -> None:
        """Test that zero total weight raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            weighted_average_gamma([0.30, 0.35], [0.0, 0.0])

    def test_empty_lists_raises_error(self) -> None:
        """Test that empty lists raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            weighted_average_gamma([], [])
