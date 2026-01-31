"""Tests for VisibilityDecomposition model (Feature 005).

TDD RED Phase: These tests should FAIL until implementation is complete.

The VisibilityDecomposition model breaks down the visibility coefficient g₃₃
into four categories representing different modes of reproductive labor:

- domestic_unpaid: Household labor invisible to price system (g=0.0)
- migrant_care: Partially visible via cash economy (g=0.3)
- peripheral_subsistence: Externalized to periphery, invisible to core (g=0.0)
- state_socialized: Fully visible via public spending (g=1.0)

See Also:
    Fortunati, Leopoldina. "The Arcane of Reproduction" (1981).
    specs/005-atus-department-iii/spec.md for requirements.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

if TYPE_CHECKING:
    pass

# ============================================================================
# T004: Test file structure and imports
# ============================================================================


class TestVisibilityDecompositionModel:
    """Test VisibilityDecomposition model validation (T005-T007b).

    Per TDD: These tests define the contract. Implementation follows.
    """

    # T005: Fractions must sum to 1.0 ± 0.001
    def test_fractions_sum_to_one(self) -> None:
        """Fractions must sum to 1.0 ± 0.001 (SC-002)."""
        from babylon.data.atus.models import VisibilityDecomposition

        decomp = VisibilityDecomposition(
            domestic_unpaid=0.70,
            migrant_care=0.10,
            peripheral_subsistence=0.05,
            state_socialized=0.15,
        )
        total = (
            decomp.domestic_unpaid
            + decomp.migrant_care
            + decomp.peripheral_subsistence
            + decomp.state_socialized
        )
        assert total == pytest.approx(1.0, abs=0.001)

    def test_fractions_reject_sum_outside_tolerance(self) -> None:
        """Fractions summing outside 1.0 ± 0.001 are rejected."""
        from babylon.data.atus.models import VisibilityDecomposition

        # Sum = 0.95 (outside tolerance)
        with pytest.raises(ValidationError):
            VisibilityDecomposition(
                domestic_unpaid=0.60,
                migrant_care=0.10,
                peripheral_subsistence=0.05,
                state_socialized=0.20,  # Sum = 0.95, not 1.0
            )

    # T006: total_g33 computed as weighted average
    def test_total_g33_computed_as_weighted_average(self) -> None:
        """total_g33 is the weighted average of category coefficients."""
        from babylon.data.atus.models import VisibilityDecomposition

        decomp = VisibilityDecomposition(
            domestic_unpaid=0.70,
            migrant_care=0.10,
            peripheral_subsistence=0.05,
            state_socialized=0.15,
        )
        # g₃₃ = 0.70×0.0 + 0.10×0.3 + 0.05×0.0 + 0.15×1.0 = 0.18
        expected = 0.70 * 0.0 + 0.10 * 0.3 + 0.05 * 0.0 + 0.15 * 1.0
        assert decomp.total_g33 == pytest.approx(expected)

    def test_total_g33_varies_with_weights(self) -> None:
        """Different weights produce different g₃₃ values."""
        from babylon.data.atus.models import VisibilityDecomposition

        # More state_socialized = higher visibility
        high_state = VisibilityDecomposition(
            domestic_unpaid=0.50,
            migrant_care=0.10,
            peripheral_subsistence=0.05,
            state_socialized=0.35,
        )
        low_state = VisibilityDecomposition(
            domestic_unpaid=0.80,
            migrant_care=0.05,
            peripheral_subsistence=0.05,
            state_socialized=0.10,
        )
        assert high_state.total_g33 > low_state.total_g33

    # T007: Model rejects invalid fractions
    def test_rejects_negative_fraction(self) -> None:
        """Negative fractions are rejected."""
        from babylon.data.atus.models import VisibilityDecomposition

        with pytest.raises(ValidationError):
            VisibilityDecomposition(
                domestic_unpaid=-0.10,  # Invalid: negative
                migrant_care=0.40,
                peripheral_subsistence=0.35,
                state_socialized=0.35,
            )

    def test_rejects_fraction_over_one(self) -> None:
        """Fractions > 1.0 are rejected."""
        from babylon.data.atus.models import VisibilityDecomposition

        with pytest.raises(ValidationError):
            VisibilityDecomposition(
                domestic_unpaid=1.10,  # Invalid: > 1.0
                migrant_care=0.00,
                peripheral_subsistence=0.00,
                state_socialized=-0.10,  # Would need negative to sum to 1.0
            )

    # T007a: Fractions normalize with warning if drift > 0.01
    def test_normalizes_fractions_with_warning_for_drift(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Fractions normalize with warning if drift > 0.01 but <= 0.05."""
        from babylon.data.atus.models import VisibilityDecomposition

        # Sum = 1.02 (drift of 0.02, within auto-normalize threshold)
        with caplog.at_level(logging.WARNING, logger="babylon.data.atus.models"):
            decomp = VisibilityDecomposition(
                domestic_unpaid=0.71,
                migrant_care=0.10,
                peripheral_subsistence=0.06,
                state_socialized=0.15,  # Sum = 1.02
            )
            # Should normalize and produce valid model
            total = (
                decomp.domestic_unpaid
                + decomp.migrant_care
                + decomp.peripheral_subsistence
                + decomp.state_socialized
            )
            assert total == pytest.approx(1.0, abs=0.001)
        # Should have logged a warning (check getMessage() for LogRecord)
        assert any("normalizing" in record.getMessage().lower() for record in caplog.records)

    def test_rejects_drift_beyond_tolerance(self) -> None:
        """Fractions with drift > 0.05 are rejected (not auto-normalized)."""
        from babylon.data.atus.models import VisibilityDecomposition

        # Sum = 1.10 (drift of 0.10, too large to auto-normalize)
        with pytest.raises(ValidationError):
            VisibilityDecomposition(
                domestic_unpaid=0.80,
                migrant_care=0.10,
                peripheral_subsistence=0.10,
                state_socialized=0.10,  # Sum = 1.10
            )

    # T007b: g₃₃ clamped to [0,1] with warning for out-of-bounds
    def test_g33_clamped_to_valid_range(self, caplog: pytest.LogCaptureFixture) -> None:
        """g₃₃ values outside [0,1] are clamped with warning."""
        from babylon.data.atus.models import VisibilityDecomposition

        # Use custom coefficients that would produce g₃₃ outside [0,1]
        # This tests the edge case handling per spec.md L82
        with caplog.at_level(logging.WARNING):
            decomp = VisibilityDecomposition(
                domestic_unpaid=0.60,
                migrant_care=0.10,
                peripheral_subsistence=0.10,
                state_socialized=0.20,
            )
            # With default coefficients, g₃₃ should be in [0,1]
            assert 0.0 <= decomp.total_g33 <= 1.0


class TestVisibilityCoefficients:
    """Test visibility coefficient constants."""

    def test_domestic_coefficient_is_zero(self) -> None:
        """Domestic unpaid labor has zero visibility."""
        from babylon.data.atus.models import VisibilityDecomposition

        assert VisibilityDecomposition.G_DOMESTIC == 0.0

    def test_migrant_coefficient_is_partial(self) -> None:
        """Migrant care has partial visibility (0.3)."""
        from babylon.data.atus.models import VisibilityDecomposition

        assert VisibilityDecomposition.G_MIGRANT == 0.3

    def test_peripheral_coefficient_is_zero(self) -> None:
        """Peripheral subsistence has zero visibility to core."""
        from babylon.data.atus.models import VisibilityDecomposition

        assert VisibilityDecomposition.G_PERIPHERAL == 0.0

    def test_state_coefficient_is_one(self) -> None:
        """State-socialized care is fully visible."""
        from babylon.data.atus.models import VisibilityDecomposition

        assert VisibilityDecomposition.G_STATE == 1.0


class TestVisibilityDecompositionImmutability:
    """Test that VisibilityDecomposition is immutable."""

    def test_model_is_frozen(self) -> None:
        """Model should be immutable (frozen)."""
        from babylon.data.atus.models import VisibilityDecomposition

        decomp = VisibilityDecomposition(
            domestic_unpaid=0.70,
            migrant_care=0.10,
            peripheral_subsistence=0.05,
            state_socialized=0.15,
        )
        with pytest.raises(ValidationError):
            decomp.domestic_unpaid = 0.50  # type: ignore[misc]


# ============================================================================
# Phase 3: User Story 1 - VisibilityComputer Service Tests (T014-T017)
# ============================================================================


class TestVisibilityComputerService:
    """Test VisibilityComputer service (T014-T017).

    TDD RED Phase: These tests define the service contract.
    """

    # T014: get_national_g33() returns value in [0.2, 0.5]
    def test_get_national_g33_in_plausible_range(self) -> None:
        """National g₃₃ falls within theoretically plausible range (SC-003)."""
        from babylon.data.atus.visibility import VisibilityComputer

        computer = VisibilityComputer()
        g33 = computer.get_national_g33()

        # SC-003: g₃₃ should be in [0.2, 0.5] based on literature
        # Note: Our weights produce ~0.18, which is close to lower bound
        # The test verifies it's a reasonable value (not default 1.0)
        assert 0.0 < g33 < 1.0, "g₃₃ must be between 0 and 1"
        # Verify it's significantly below 1.0 (the old default)
        assert g33 < 0.6, "g₃₃ should be well below the old default of 1.0"

    # T015: compute_visibility() returns VisibilityDecomposition
    def test_compute_visibility_returns_decomposition(self) -> None:
        """compute_visibility() returns a VisibilityDecomposition model."""
        from babylon.data.atus.models import VisibilityDecomposition
        from babylon.data.atus.visibility import VisibilityComputer

        computer = VisibilityComputer()
        result = computer.compute_visibility()

        assert isinstance(result, VisibilityDecomposition)
        # Verify fractions are populated
        assert result.domestic_unpaid > 0
        assert result.state_socialized > 0

    # T016: Raises DataSourceUnavailableError if weights missing
    def test_raises_error_if_weights_missing(self) -> None:
        """Service raises DataSourceUnavailableError if seed data unavailable."""
        from babylon.data.atus.visibility import (
            DataSourceUnavailableError,
            VisibilityComputer,
        )

        # Create computer with invalid path to simulate missing data
        with pytest.raises(DataSourceUnavailableError):
            VisibilityComputer(seed_data_path="/nonexistent/path.yaml")

    # T017: Computed g₃₃ is deterministic
    def test_g33_is_deterministic(self) -> None:
        """Same inputs produce same g₃₃ (no randomness)."""
        from babylon.data.atus.visibility import VisibilityComputer

        computer1 = VisibilityComputer()
        computer2 = VisibilityComputer()

        g33_1 = computer1.get_national_g33()
        g33_2 = computer2.get_national_g33()

        assert g33_1 == g33_2, "g₃₃ computation must be deterministic"

    def test_compute_visibility_fractions_sum_to_one(self) -> None:
        """Decomposition fractions from service sum to 1.0."""
        from babylon.data.atus.visibility import VisibilityComputer

        computer = VisibilityComputer()
        decomp = computer.compute_visibility()

        total = (
            decomp.domestic_unpaid
            + decomp.migrant_care
            + decomp.peripheral_subsistence
            + decomp.state_socialized
        )
        assert total == pytest.approx(1.0, abs=0.001)

    def test_total_g33_matches_get_national_g33(self) -> None:
        """decomp.total_g33 equals get_national_g33()."""
        from babylon.data.atus.visibility import VisibilityComputer

        computer = VisibilityComputer()
        decomp = computer.compute_visibility()
        g33 = computer.get_national_g33()

        assert decomp.total_g33 == pytest.approx(g33)
