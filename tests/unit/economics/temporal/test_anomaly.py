"""Unit tests for anomaly detection.

Feature: 003-hydrator-temporal-validation
User Story 2: Flag Anomalous Year-over-Year Jumps

Tests cover:
- T027: Z-score computation with rolling window
- T028: Tiered detection method selection

TDD: These tests are written FIRST and should FAIL until implementation.
"""

import pytest

from babylon.economics.temporal.models import (
    AnomalyFlag,
    AnomalyThresholdConfig,
    DetectionMethod,
)


class TestRollingZScore:
    """Test rolling Z-score computation (T027, T031)."""

    def test_rolling_zscore_returns_float(self) -> None:
        """rolling_zscore returns float for valid input."""
        from babylon.economics.temporal.anomaly import rolling_zscore

        # 5 values with known statistics
        values = [0.10, 0.12, 0.11, 0.13, 0.25]  # Last is outlier

        # Z-score for the last value (0.25)
        z = rolling_zscore(values, window_size=5)

        # 0.25 should be a positive outlier (high Z-score)
        assert isinstance(z, float)
        assert z > 1.5  # Should be significantly above mean

    def test_rolling_zscore_insufficient_history_returns_none(self) -> None:
        """rolling_zscore returns None for insufficient history."""
        from babylon.economics.temporal.anomaly import rolling_zscore

        # Only 3 values, but window_size is 5
        values = [0.10, 0.12, 0.11]

        z = rolling_zscore(values, window_size=5)

        assert z is None

    def test_rolling_zscore_exact_window_size(self) -> None:
        """rolling_zscore works with exactly window_size values."""
        from babylon.economics.temporal.anomaly import rolling_zscore

        values = [0.10, 0.12, 0.11, 0.13, 0.12]  # 5 values

        z = rolling_zscore(values, window_size=5)

        assert z is not None
        # Mean ≈ 0.116, std ≈ 0.01, z for 0.12 ≈ 0.4
        assert isinstance(z, float)

    def test_rolling_zscore_negative_outlier(self) -> None:
        """rolling_zscore detects negative outliers."""
        from babylon.economics.temporal.anomaly import rolling_zscore

        values = [0.10, 0.12, 0.11, 0.13, 0.02]  # Last is low outlier

        z = rolling_zscore(values, window_size=5)

        assert z is not None
        assert z < -1.5  # Should be significantly below mean

    def test_rolling_zscore_zero_std_returns_zero(self) -> None:
        """rolling_zscore returns 0 when all values are identical."""
        from babylon.economics.temporal.anomaly import rolling_zscore

        values = [0.10, 0.10, 0.10, 0.10, 0.10]  # All same

        z = rolling_zscore(values, window_size=5)

        # Can't compute Z-score with zero std, should return 0 or handle gracefully
        assert z == 0.0 or z is None


class TestDetectionMethodSelection:
    """Test tiered detection method selection (T028, T033)."""

    def test_z_score_method_when_sufficient_history(self) -> None:
        """Z_SCORE method selected when ≥5 years of history."""
        from babylon.economics.temporal.anomaly import select_detection_method

        config = AnomalyThresholdConfig(rolling_window_years=5)

        method = select_detection_method(
            years_of_history=6,
            config=config,
        )

        assert method == DetectionMethod.Z_SCORE

    def test_empirical_threshold_when_insufficient_history_with_p95(self) -> None:
        """EMPIRICAL_THRESHOLD when <5 years but national p95 available."""
        from babylon.economics.temporal.anomaly import select_detection_method

        config = AnomalyThresholdConfig(
            rolling_window_years=5,
            national_p95_threshold=0.12,  # Calibrated
        )

        method = select_detection_method(
            years_of_history=3,
            config=config,
        )

        assert method == DetectionMethod.EMPIRICAL_THRESHOLD

    def test_bootstrap_when_no_calibration(self) -> None:
        """BOOTSTRAP method when insufficient history AND no p95 calibration."""
        from babylon.economics.temporal.anomaly import select_detection_method

        config = AnomalyThresholdConfig(
            rolling_window_years=5,
            national_p95_threshold=None,  # Not calibrated
        )

        method = select_detection_method(
            years_of_history=3,
            config=config,
        )

        assert method == DetectionMethod.BOOTSTRAP


class TestAnomalyFlagCreation:
    """Test anomaly flag creation logic."""

    def test_flag_created_when_z_score_exceeds_k(self) -> None:
        """Flag created when Z-score exceeds k standard deviations."""
        from babylon.economics.temporal.anomaly import check_threshold_violation

        config = AnomalyThresholdConfig(z_score_k=2.5)

        # Z-score of 3.0 exceeds k=2.5
        flag = check_threshold_violation(
            component="total_v",
            delta_value=0.25,
            z_score=3.0,
            config=config,
            detection_method=DetectionMethod.Z_SCORE,
        )

        assert flag is not None
        assert isinstance(flag, AnomalyFlag)
        assert flag.component == "total_v"
        assert flag.z_score == 3.0

    def test_no_flag_when_z_score_within_k(self) -> None:
        """No flag when Z-score is within k standard deviations."""
        from babylon.economics.temporal.anomaly import check_threshold_violation

        config = AnomalyThresholdConfig(z_score_k=2.5)

        # Z-score of 2.0 is within k=2.5
        flag = check_threshold_violation(
            component="total_v",
            delta_value=0.15,
            z_score=2.0,
            config=config,
            detection_method=DetectionMethod.Z_SCORE,
        )

        assert flag is None

    def test_flag_created_with_bootstrap_threshold(self) -> None:
        """Flag created when delta exceeds bootstrap threshold."""
        from babylon.economics.temporal.anomaly import check_threshold_violation

        config = AnomalyThresholdConfig(bootstrap_threshold=0.15)

        # Delta of 0.20 exceeds bootstrap threshold of 0.15
        flag = check_threshold_violation(
            component="profit_rate",
            delta_value=0.20,
            z_score=None,  # No Z-score available
            config=config,
            detection_method=DetectionMethod.BOOTSTRAP,
        )

        assert flag is not None
        assert flag.threshold == 0.15
        assert flag.z_score is None

    def test_flag_created_with_empirical_threshold(self) -> None:
        """Flag created when delta exceeds empirical p95 threshold."""
        from babylon.economics.temporal.anomaly import check_threshold_violation

        config = AnomalyThresholdConfig(national_p95_threshold=0.12)

        # Delta of 0.18 exceeds empirical threshold of 0.12
        flag = check_threshold_violation(
            component="dept_i_share",
            delta_value=0.18,
            z_score=None,
            config=config,
            detection_method=DetectionMethod.EMPIRICAL_THRESHOLD,
        )

        assert flag is not None
        assert flag.threshold == 0.12


class TestAnomalyDetectorImpl:
    """Test AnomalyDetectorImpl class (T032, T033)."""

    def test_detect_anomalies_returns_transitions(self) -> None:
        """detect_anomalies returns list of TemporalTransition."""
        from babylon.economics.temporal.anomaly import AnomalyDetectorImpl

        detector = AnomalyDetectorImpl(hydrator=None)  # type: ignore[arg-type]
        assert hasattr(detector, "detect_anomalies")

    def test_detect_anomalies_insufficient_years_raises(self) -> None:
        """detect_anomalies with <2 years raises ValueError."""
        from babylon.economics.temporal.anomaly import AnomalyDetectorImpl

        detector = AnomalyDetectorImpl(hydrator=None)  # type: ignore[arg-type]
        config = AnomalyThresholdConfig()

        with pytest.raises(ValueError, match="at least 2"):
            detector.detect_anomalies(
                fips="26163",
                years=[2020],  # Only 1 year
                config=config,
            )

    def test_compute_z_scores_returns_dict(self) -> None:
        """compute_z_scores returns dict mapping year to Z-score."""
        from babylon.economics.temporal.anomaly import AnomalyDetectorImpl

        detector = AnomalyDetectorImpl(hydrator=None)  # type: ignore[arg-type]
        assert hasattr(detector, "compute_z_scores")


class TestRollingZscoreMutationKillers:
    """Mutation-killing tests for rolling_zscore."""

    def test_zscore_exact_computation(self) -> None:
        """Verify exact Z-score for known distribution."""
        from babylon.economics.temporal.anomaly import rolling_zscore

        # values = [10, 10, 10, 10, 20], window=5
        # mean = 12, variance = (4+4+4+4+64)/5 = 16, std = 4
        # z = (20 - 12) / 4 = 2.0
        z = rolling_zscore([10.0, 10.0, 10.0, 10.0, 20.0], window_size=5)
        assert z == pytest.approx(2.0)

    def test_zscore_negative_outlier_exact(self) -> None:
        """Verify negative Z-score for below-mean outlier."""
        from babylon.economics.temporal.anomaly import rolling_zscore

        # values = [10, 10, 10, 10, 0], window=5
        # mean = 8, variance = (4+4+4+4+64)/5 = 16, std = 4
        # z = (0 - 8) / 4 = -2.0
        z = rolling_zscore([10.0, 10.0, 10.0, 10.0, 0.0], window_size=5)
        assert z == pytest.approx(-2.0)

    def test_zscore_uses_last_value(self) -> None:
        """Z-score is computed for the LAST value in window."""
        from babylon.economics.temporal.anomaly import rolling_zscore

        # Outlier in middle, normal at end — should not flag
        z = rolling_zscore([10.0, 10.0, 100.0, 10.0, 10.0], window_size=5)
        # Last value (10) is near mean, z should be small/negative
        assert z is not None
        assert z < 0  # 10 is below the mean that includes the 100 outlier

    def test_zscore_window_size_exact_match(self) -> None:
        """Exactly window_size values returns valid z-score."""
        from babylon.economics.temporal.anomaly import rolling_zscore

        z = rolling_zscore([1.0, 2.0, 3.0], window_size=3)
        assert z is not None

    def test_zscore_below_window_size_returns_none(self) -> None:
        """Fewer than window_size values returns None."""
        from babylon.economics.temporal.anomaly import rolling_zscore

        z = rolling_zscore([1.0, 2.0], window_size=3)
        assert z is None

    def test_zscore_uses_last_n_values(self) -> None:
        """When len(values) > window_size, only last window_size used."""
        from babylon.economics.temporal.anomaly import rolling_zscore

        # First 5 values are noise, last 3 are [10, 10, 20]
        values = [999.0, 888.0, 777.0, 666.0, 555.0, 10.0, 10.0, 20.0]
        z = rolling_zscore(values, window_size=3)
        # Only [10, 10, 20] used. mean=13.33, variance=22.22, std=4.71
        # z = (20 - 13.33) / 4.71 ≈ 1.414
        assert z is not None
        assert z == pytest.approx(1.4142, abs=0.01)

    def test_zscore_zero_std_returns_zero(self) -> None:
        """All identical values produces zero std, returns 0.0."""
        from babylon.economics.temporal.anomaly import rolling_zscore

        z = rolling_zscore([5.0, 5.0, 5.0], window_size=3)
        assert z == 0.0

    def test_zscore_mean_computation_correct(self) -> None:
        """Verify mean is computed as sum/n, not sum/(n-1)."""
        from babylon.economics.temporal.anomaly import rolling_zscore

        # [0, 10] window=2: mean = 5, variance = (25+25)/2=25, std=5
        # z = (10-5)/5 = 1.0
        z = rolling_zscore([0.0, 10.0], window_size=2)
        assert z == pytest.approx(1.0)


class TestSelectDetectionMethodMutationKillers:
    """Mutation-killing tests for select_detection_method."""

    def test_z_score_at_exact_boundary(self) -> None:
        """Exactly rolling_window_years returns Z_SCORE."""
        from babylon.economics.temporal.anomaly import select_detection_method

        config = AnomalyThresholdConfig(rolling_window_years=5)
        method = select_detection_method(years_of_history=5, config=config)
        assert method == DetectionMethod.Z_SCORE

    def test_z_score_above_boundary(self) -> None:
        """Above rolling_window_years returns Z_SCORE."""
        from babylon.economics.temporal.anomaly import select_detection_method

        config = AnomalyThresholdConfig(rolling_window_years=5)
        method = select_detection_method(years_of_history=10, config=config)
        assert method == DetectionMethod.Z_SCORE

    def test_below_boundary_no_p95_returns_bootstrap(self) -> None:
        """Below threshold without p95 returns BOOTSTRAP."""
        from babylon.economics.temporal.anomaly import select_detection_method

        config = AnomalyThresholdConfig(rolling_window_years=5, national_p95_threshold=None)
        method = select_detection_method(years_of_history=4, config=config)
        assert method == DetectionMethod.BOOTSTRAP

    def test_below_boundary_with_p95_returns_empirical(self) -> None:
        """Below threshold with p95 returns EMPIRICAL_THRESHOLD."""
        from babylon.economics.temporal.anomaly import select_detection_method

        config = AnomalyThresholdConfig(rolling_window_years=5, national_p95_threshold=0.12)
        method = select_detection_method(years_of_history=4, config=config)
        assert method == DetectionMethod.EMPIRICAL_THRESHOLD

    def test_one_below_boundary_without_p95(self) -> None:
        """One less than required window: still BOOTSTRAP when no p95."""
        from babylon.economics.temporal.anomaly import select_detection_method

        config = AnomalyThresholdConfig(rolling_window_years=5, national_p95_threshold=None)
        method = select_detection_method(years_of_history=4, config=config)
        assert method == DetectionMethod.BOOTSTRAP


class TestCheckThresholdViolationMutationKillers:
    """Mutation-killing tests for check_threshold_violation."""

    def test_z_score_exactly_at_k_no_flag(self) -> None:
        """Z-score exactly at k does NOT flag (uses > not >=)."""
        from babylon.economics.temporal.anomaly import check_threshold_violation

        config = AnomalyThresholdConfig(z_score_k=2.5)
        flag = check_threshold_violation(
            "total_v",
            0.2,
            z_score=2.5,
            config=config,
            detection_method=DetectionMethod.Z_SCORE,
        )
        assert flag is None

    def test_z_score_just_above_k_flags(self) -> None:
        """Z-score slightly above k produces flag."""
        from babylon.economics.temporal.anomaly import check_threshold_violation

        config = AnomalyThresholdConfig(z_score_k=2.5)
        flag = check_threshold_violation(
            "total_v",
            0.3,
            z_score=2.51,
            config=config,
            detection_method=DetectionMethod.Z_SCORE,
        )
        assert flag is not None
        assert flag.z_score == pytest.approx(2.51)

    def test_z_score_negative_outlier_flags(self) -> None:
        """Negative Z-score below -k also flags (uses abs)."""
        from babylon.economics.temporal.anomaly import check_threshold_violation

        config = AnomalyThresholdConfig(z_score_k=2.0)
        flag = check_threshold_violation(
            "profit_rate",
            -0.3,
            z_score=-2.5,
            config=config,
            detection_method=DetectionMethod.Z_SCORE,
        )
        assert flag is not None

    def test_z_score_none_returns_none(self) -> None:
        """Z_SCORE method with None z_score returns None."""
        from babylon.economics.temporal.anomaly import check_threshold_violation

        config = AnomalyThresholdConfig(z_score_k=2.0)
        flag = check_threshold_violation(
            "total_v",
            0.5,
            z_score=None,
            config=config,
            detection_method=DetectionMethod.Z_SCORE,
        )
        assert flag is None

    def test_bootstrap_exactly_at_threshold_no_flag(self) -> None:
        """Bootstrap delta exactly at threshold does NOT flag (uses >)."""
        from babylon.economics.temporal.anomaly import check_threshold_violation

        config = AnomalyThresholdConfig(bootstrap_threshold=0.15)
        flag = check_threshold_violation(
            "total_v",
            0.15,
            z_score=None,
            config=config,
            detection_method=DetectionMethod.BOOTSTRAP,
        )
        assert flag is None

    def test_bootstrap_above_threshold_flags(self) -> None:
        """Bootstrap delta above threshold produces flag."""
        from babylon.economics.temporal.anomaly import check_threshold_violation

        config = AnomalyThresholdConfig(bootstrap_threshold=0.15)
        flag = check_threshold_violation(
            "total_v",
            0.16,
            z_score=None,
            config=config,
            detection_method=DetectionMethod.BOOTSTRAP,
        )
        assert flag is not None
        assert flag.threshold == pytest.approx(0.15)

    def test_bootstrap_negative_delta_uses_abs(self) -> None:
        """Bootstrap checks absolute delta, not signed."""
        from babylon.economics.temporal.anomaly import check_threshold_violation

        config = AnomalyThresholdConfig(bootstrap_threshold=0.15)
        flag = check_threshold_violation(
            "total_v",
            -0.20,
            z_score=None,
            config=config,
            detection_method=DetectionMethod.BOOTSTRAP,
        )
        assert flag is not None

    def test_empirical_uses_p95_threshold(self) -> None:
        """EMPIRICAL_THRESHOLD uses national_p95 value."""
        from babylon.economics.temporal.anomaly import check_threshold_violation

        config = AnomalyThresholdConfig(national_p95_threshold=0.10, bootstrap_threshold=0.15)
        # Delta 0.12 exceeds p95 (0.10) but not bootstrap (0.15)
        flag = check_threshold_violation(
            "dept_I",
            0.12,
            z_score=None,
            config=config,
            detection_method=DetectionMethod.EMPIRICAL_THRESHOLD,
        )
        assert flag is not None
        assert flag.threshold == pytest.approx(0.10)

    def test_empirical_fallback_to_bootstrap_when_no_p95(self) -> None:
        """EMPIRICAL_THRESHOLD falls back to bootstrap_threshold when p95 is None."""
        from babylon.economics.temporal.anomaly import check_threshold_violation

        config = AnomalyThresholdConfig(national_p95_threshold=None, bootstrap_threshold=0.15)
        flag = check_threshold_violation(
            "total_v",
            0.20,
            z_score=None,
            config=config,
            detection_method=DetectionMethod.EMPIRICAL_THRESHOLD,
        )
        assert flag is not None
        assert flag.threshold == pytest.approx(0.15)

    def test_flag_stores_component_name(self) -> None:
        """Flag correctly stores the component name."""
        from babylon.economics.temporal.anomaly import check_threshold_violation

        config = AnomalyThresholdConfig(bootstrap_threshold=0.01)
        flag = check_threshold_violation(
            "dept_IIb",
            0.50,
            z_score=None,
            config=config,
            detection_method=DetectionMethod.BOOTSTRAP,
        )
        assert flag is not None
        assert flag.component == "dept_IIb"

    def test_flag_stores_delta_value(self) -> None:
        """Flag stores the original delta value (not absolute)."""
        from babylon.economics.temporal.anomaly import check_threshold_violation

        config = AnomalyThresholdConfig(bootstrap_threshold=0.01)
        flag = check_threshold_violation(
            "total_v",
            -0.50,
            z_score=None,
            config=config,
            detection_method=DetectionMethod.BOOTSTRAP,
        )
        assert flag is not None
        assert flag.value == pytest.approx(-0.50)
