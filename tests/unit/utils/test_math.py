"""Tests for babylon.utils.math - Quantization utilities.

TDD Red Phase: These tests define the contract for the quantize() function
that will provide 10^-5 precision quantization for all economic calculations.

Epoch 0 Physics Hardening:
- All floating-point values in the simulation snap to a 10^-5 grid
- This prevents drift accumulation over long simulations
- Quantization uses ROUND_HALF_UP (banker's rounding variant: away from zero)

The quantize() function will be used by:
- Pydantic AfterValidators on constrained types (Probability, Currency, etc.)
- Formula outputs before storage
- Edge weight calculations

Kent Beck says: "Make the tests pass with the simplest code possible."
"""

from __future__ import annotations

import pytest

# =============================================================================
# RED PHASE: Import module that doesn't exist yet
# =============================================================================

# Use pytest.importorskip to gracefully handle missing module during RED phase
_math_module = pytest.importorskip(
    "babylon.utils.math",
    reason="babylon.utils.math not yet implemented (RED phase)",
)

# Extract functions from module after successful import
quantize = _math_module.quantize
set_precision = _math_module.set_precision


# =============================================================================
# QUANTIZE FUNCTION TESTS
# =============================================================================


@pytest.mark.math
class TestQuantize:
    """Tests for the quantize() function.

    The quantize function snaps floating-point values to a fixed grid
    (default 10^-5 = 0.00001) to prevent drift accumulation.

    Rounding mode: ROUND_HALF_UP (ties round away from zero)
    - 0.000005 -> 0.00001 (positive, round up)
    - -0.000005 -> -0.00001 (negative, round away from zero = down)
    """

    def test_quantize_rounds_to_5_decimals(self) -> None:
        """quantize(0.123456789) -> 0.12346 with default precision=5.

        The sixth digit (7) causes round-up of the fifth digit (5 -> 6).
        """
        result = quantize(0.123456789)

        assert result == 0.12346

    def test_quantize_zero_returns_zero(self) -> None:
        """quantize(0.0) -> 0.0 (no floating point drift).

        Zero is a fixed point of quantization.
        """
        result = quantize(0.0)

        assert result == 0.0
        # Verify it's actually zero, not a tiny epsilon
        assert result == pytest.approx(0.0, abs=1e-10)

    def test_quantize_none_returns_zero(self) -> None:
        """quantize(None) -> 0.0 (graceful handling).

        None is treated as zero for defensive programming.
        This prevents crashes when edge cases pass None to formulas.
        """
        result = quantize(None)  # type: ignore[arg-type]

        assert result == 0.0

    def test_quantize_negative_values(self) -> None:
        """quantize(-0.123456789) -> -0.12346.

        Negative values are quantized symmetrically to positive values.
        """
        result = quantize(-0.123456789)

        assert result == -0.12346

    def test_quantize_rounds_half_up(self) -> None:
        """quantize(0.000005) -> 0.00001 (round half away from zero).

        When exactly at the midpoint (5 in the next digit position),
        we round AWAY from zero (up for positive numbers).
        """
        result = quantize(0.000005)

        assert result == 0.00001

    def test_quantize_rounds_half_down_for_negative(self) -> None:
        """quantize(-0.000005) -> -0.00001 (round half away from zero).

        For negative numbers, "away from zero" means rounding down
        (more negative).
        """
        result = quantize(-0.000005)

        assert result == -0.00001

    def test_quantize_preserves_exact_grid_values(self) -> None:
        """quantize(0.12345) -> 0.12345 (already on grid).

        Values that are already on the grid are preserved exactly.
        """
        result = quantize(0.12345)

        assert result == 0.12345

    def test_quantize_very_small_values(self) -> None:
        """quantize(0.000001) -> 0.0 (below grid resolution).

        Values smaller than half the grid step round to zero.
        Grid step is 0.00001, so 0.000001 < 0.000005 -> rounds to 0.
        """
        result = quantize(0.000001)

        assert result == 0.0

    def test_quantize_very_large_values(self) -> None:
        """quantize(1234567.89) -> 1234567.89 (large values work).

        Quantization works on large values too - the decimal places
        are still snapped to the grid.
        """
        result = quantize(1234567.89)

        assert result == 1234567.89

    def test_set_precision_changes_grid(self) -> None:
        """set_precision(3) makes quantize use 10^-3 grid.

        The precision is configurable for different simulation needs.
        After calling set_precision(3), quantize uses 0.001 grid.
        """
        # Store original to restore later
        original = _math_module.get_precision()

        try:
            set_precision(3)

            result = quantize(0.1234)

            assert result == 0.123
        finally:
            # Restore original precision
            set_precision(original)

    def test_quantize_idempotent(self) -> None:
        """quantize(quantize(x)) == quantize(x).

        Applying quantize twice gives the same result as once.
        This is a critical property for numerical stability.
        """
        original = 0.123456789

        once = quantize(original)
        twice = quantize(once)

        assert once == twice

    def test_quantize_edge_case_0_999995(self) -> None:
        """quantize(0.999995) -> 1.0 (rounds up to boundary).

        Values near 1.0 that round up should reach exactly 1.0.
        This is important for Probability type which has max=1.0.
        """
        result = quantize(0.999995)

        assert result == 1.0


# =============================================================================
# PRECISION CONFIGURATION TESTS
# =============================================================================


@pytest.mark.math
class TestPrecisionConfiguration:
    """Tests for precision configuration functions.

    The precision can be changed globally via set_precision().
    get_precision() returns the current precision setting.
    """

    def test_get_precision_returns_default_5(self) -> None:
        """get_precision() returns 5 by default.

        The default precision is 5 decimal places (10^-5 grid).
        """
        get_precision = _math_module.get_precision

        result = get_precision()

        assert result == 5

    def test_set_precision_accepts_valid_range(self) -> None:
        """set_precision accepts values 1-10.

        Precision must be a positive integer in a reasonable range.
        """
        get_precision = _math_module.get_precision
        original = get_precision()

        try:
            for precision in range(1, 11):
                set_precision(precision)
                assert get_precision() == precision
        finally:
            set_precision(original)

    def test_set_precision_rejects_zero(self) -> None:
        """set_precision(0) raises ValueError.

        Zero precision means no decimal places, which doesn't make sense
        for financial/economic calculations.
        """
        with pytest.raises(ValueError, match="[Pp]recision"):
            set_precision(0)

    def test_set_precision_rejects_negative(self) -> None:
        """set_precision(-1) raises ValueError.

        Negative precision is meaningless.
        """
        with pytest.raises(ValueError, match="[Pp]recision"):
            set_precision(-1)
