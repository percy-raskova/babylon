"""Unit tests for deindustrialization signal detection.

Feature: 003-hydrator-temporal-validation
User Story 1: Detect Deindustrialization Signal

Tests cover:
- T019: Linear trend computation
- T020: Signal detection criteria (core ≤ 0, core < suburb)

TDD: These tests are written FIRST and should FAIL until implementation.
"""

import pytest

from babylon.economics.temporal.models import DeindustrializationSignal


class TestComputeTrend:
    """Test linear trend computation (T019)."""

    def test_compute_trend_positive_slope(self) -> None:
        """Positive trend returns positive slope."""
        # Import will fail until implementation exists
        from babylon.economics.temporal.signals import compute_trend

        # Years: 2018, 2019, 2020, 2021, 2022
        # Values: 0.10, 0.12, 0.14, 0.16, 0.18 (increasing by 0.02/year)
        years = [2018, 2019, 2020, 2021, 2022]
        values = [0.10, 0.12, 0.14, 0.16, 0.18]

        slope = compute_trend(years, values)

        # Slope should be approximately 0.02 per year
        assert slope == pytest.approx(0.02, abs=0.001)

    def test_compute_trend_negative_slope(self) -> None:
        """Negative trend returns negative slope."""
        from babylon.economics.temporal.signals import compute_trend

        # Declining values
        years = [2018, 2019, 2020, 2021, 2022]
        values = [0.20, 0.18, 0.16, 0.14, 0.12]

        slope = compute_trend(years, values)

        assert slope == pytest.approx(-0.02, abs=0.001)

    def test_compute_trend_flat(self) -> None:
        """Flat trend returns near-zero slope."""
        from babylon.economics.temporal.signals import compute_trend

        years = [2018, 2019, 2020, 2021, 2022]
        values = [0.15, 0.15, 0.15, 0.15, 0.15]

        slope = compute_trend(years, values)

        assert slope == pytest.approx(0.0, abs=0.0001)

    def test_compute_trend_minimum_points(self) -> None:
        """Trend computation works with minimum 2 points."""
        from babylon.economics.temporal.signals import compute_trend

        years = [2020, 2021]
        values = [0.10, 0.15]

        slope = compute_trend(years, values)

        assert slope == pytest.approx(0.05, abs=0.001)

    def test_compute_trend_single_point_raises(self) -> None:
        """Single point raises ValueError."""
        from babylon.economics.temporal.signals import compute_trend

        with pytest.raises(ValueError, match="at least 2"):
            compute_trend([2020], [0.10])

    def test_compute_trend_mismatched_lengths_raises(self) -> None:
        """Mismatched years/values lengths raises ValueError."""
        from babylon.economics.temporal.signals import compute_trend

        with pytest.raises(ValueError, match="length"):
            compute_trend([2020, 2021, 2022], [0.10, 0.15])


class TestSignalDetectionCriteria:
    """Test signal detection criteria (T020)."""

    def test_signal_detected_when_core_declining_and_worse_than_suburb(self) -> None:
        """Signal detected: core declining AND core trend < suburb trend."""
        # Core is declining (-0.005), suburb is growing (0.002)
        signal = DeindustrializationSignal(
            core_county="26163",
            suburb_county="26125",
            year_range=(2010, 2022),
            core_dept_i_trend=-0.005,
            suburb_dept_i_trend=0.002,
            signal_detected=True,
            signal_strength=0.007,  # suburb - core = 0.002 - (-0.005)
        )

        assert signal.signal_detected is True
        assert signal.core_declining is True
        assert signal.signal_strength == pytest.approx(0.007)

    def test_signal_detected_when_core_stagnating_and_suburb_growing(self) -> None:
        """Signal detected: core stagnating AND suburb growing."""
        # Core is flat (0.0001), suburb is growing (0.003)
        signal = DeindustrializationSignal(
            core_county="26163",
            suburb_county="26125",
            year_range=(2010, 2022),
            core_dept_i_trend=0.0001,
            suburb_dept_i_trend=0.003,
            signal_detected=True,
            signal_strength=0.0029,
        )

        assert signal.signal_detected is True
        assert signal.core_stagnating is True

    def test_no_signal_when_core_growing_faster(self) -> None:
        """No signal: core growing faster than suburb."""
        # Core is growing (0.005), suburb is growing less (0.002)
        signal = DeindustrializationSignal(
            core_county="26163",
            suburb_county="26125",
            year_range=(2010, 2022),
            core_dept_i_trend=0.005,
            suburb_dept_i_trend=0.002,
            signal_detected=False,
            signal_strength=-0.003,  # suburb - core = negative
        )

        assert signal.signal_detected is False
        assert signal.core_declining is False


class TestDeindustrializationDetectorImpl:
    """Test DeindustrializationDetectorImpl (T023)."""

    def test_detect_deindustrialization_returns_signal(self) -> None:
        """detect_deindustrialization returns DeindustrializationSignal."""
        from babylon.economics.temporal.signals import DeindustrializationDetectorImpl

        # This test will fail until implementation exists
        # We'll need to mock the hydrator or use test fixtures
        detector = DeindustrializationDetectorImpl(hydrator=None)  # type: ignore[arg-type]

        # Placeholder - actual test needs hydrator mock
        assert hasattr(detector, "detect_deindustrialization")

    def test_detect_deindustrialization_insufficient_years_raises(self) -> None:
        """detect_deindustrialization with <2 years raises ValueError."""
        from babylon.economics.temporal.signals import DeindustrializationDetectorImpl

        detector = DeindustrializationDetectorImpl(hydrator=None)  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="at least 2"):
            detector.detect_deindustrialization(
                core_fips="26163",
                suburb_fips="26125",
                years=[2020],  # Only 1 year
            )
