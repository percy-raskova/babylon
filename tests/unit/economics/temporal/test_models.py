"""Unit tests for temporal validation Pydantic models.

Feature: 003-hydrator-temporal-validation

Tests cover:
- T005: DetectionMethod enum
- T006: AnomalyFlag model
- T007: TemporalTransition model
- T008: AnomalyThresholdConfig model
- T009: SmoothedCoefficientSeries model
- T010: DeindustrializationSignal model
- T011: TransitionAnnotation model
- T012: TemporalValidationReport model
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from babylon.economics.temporal.models import (
    AnomalyFlag,
    AnomalyThresholdConfig,
    DeindustrializationSignal,
    DetectionMethod,
    SmoothedCoefficientSeries,
    TemporalTransition,
    TemporalValidationReport,
    TransitionAnnotation,
)


class TestDetectionMethod:
    """Test DetectionMethod enum (T005)."""

    def test_z_score_value(self) -> None:
        """Z_SCORE has correct string value."""
        assert DetectionMethod.Z_SCORE.value == "z_score"

    def test_empirical_threshold_value(self) -> None:
        """EMPIRICAL_THRESHOLD has correct string value."""
        assert DetectionMethod.EMPIRICAL_THRESHOLD.value == "empirical_threshold"

    def test_bootstrap_value(self) -> None:
        """BOOTSTRAP has correct string value."""
        assert DetectionMethod.BOOTSTRAP.value == "bootstrap"

    def test_enum_members_count(self) -> None:
        """Enum has exactly 3 members."""
        assert len(DetectionMethod) == 3


class TestAnomalyFlag:
    """Test AnomalyFlag model (T006)."""

    def test_create_minimal_flag(self) -> None:
        """Create flag with required fields only."""
        flag = AnomalyFlag(
            component="total_v",
            value=0.25,
            threshold=0.15,
        )
        assert flag.component == "total_v"
        assert flag.value == 0.25
        assert flag.threshold == 0.15
        assert flag.z_score is None
        assert flag.year_context is None

    def test_create_full_flag(self) -> None:
        """Create flag with all fields."""
        flag = AnomalyFlag(
            component="profit_rate",
            value=-0.35,
            threshold=0.20,
            z_score=3.5,
            year_context="COVID-2020",
        )
        assert flag.z_score == 3.5
        assert flag.year_context == "COVID-2020"

    def test_flag_is_frozen(self) -> None:
        """Flag model is immutable."""
        flag = AnomalyFlag(component="total_v", value=0.25, threshold=0.15)
        with pytest.raises(ValidationError):
            flag.value = 0.30  # type: ignore[misc]


class TestTemporalTransition:
    """Test TemporalTransition model (T007)."""

    def test_create_valid_transition(self) -> None:
        """Create transition with valid consecutive years."""
        transition = TemporalTransition(
            fips_code="26163",
            year_from=2020,
            year_to=2021,
            delta_total_v=0.05,
            delta_profit_rate=-0.02,
            detection_method=DetectionMethod.Z_SCORE,
        )
        assert transition.fips_code == "26163"
        assert transition.year_from == 2020
        assert transition.year_to == 2021
        assert transition.is_anomalous is False

    def test_transition_with_flags_is_anomalous(self) -> None:
        """Transition with flags returns is_anomalous=True."""
        flag = AnomalyFlag(component="total_v", value=0.25, threshold=0.15)
        transition = TemporalTransition(
            fips_code="26163",
            year_from=2020,
            year_to=2021,
            delta_total_v=0.25,
            delta_profit_rate=-0.02,
            flags_raised=[flag],
            detection_method=DetectionMethod.Z_SCORE,
        )
        assert transition.is_anomalous is True

    def test_invalid_year_sequence_raises(self) -> None:
        """year_to must equal year_from + 1."""
        with pytest.raises(ValidationError, match="year_to"):
            TemporalTransition(
                fips_code="26163",
                year_from=2020,
                year_to=2022,  # Invalid: should be 2021
                delta_total_v=0.05,
                delta_profit_rate=-0.02,
                detection_method=DetectionMethod.Z_SCORE,
            )

    def test_fips_code_length_validation(self) -> None:
        """FIPS code must be exactly 5 characters."""
        with pytest.raises(ValidationError, match="fips_code"):
            TemporalTransition(
                fips_code="123",  # Too short
                year_from=2020,
                year_to=2021,
                delta_total_v=0.05,
                delta_profit_rate=-0.02,
                detection_method=DetectionMethod.Z_SCORE,
            )

    def test_transition_is_frozen(self) -> None:
        """Transition model is immutable."""
        transition = TemporalTransition(
            fips_code="26163",
            year_from=2020,
            year_to=2021,
            delta_total_v=0.05,
            delta_profit_rate=-0.02,
            detection_method=DetectionMethod.Z_SCORE,
        )
        with pytest.raises(ValidationError):
            transition.delta_total_v = 0.10  # type: ignore[misc]


class TestAnomalyThresholdConfig:
    """Test AnomalyThresholdConfig model (T008)."""

    def test_default_values(self) -> None:
        """Config has correct default values."""
        config = AnomalyThresholdConfig()
        assert config.z_score_k == 2.5
        assert config.rolling_window_years == 5
        assert config.empirical_percentile == 95
        assert config.bootstrap_threshold == 0.15
        assert config.national_p95_threshold is None

    def test_fallback_threshold_uses_bootstrap(self) -> None:
        """fallback_threshold returns bootstrap when no p95."""
        config = AnomalyThresholdConfig()
        assert config.fallback_threshold == 0.15

    def test_fallback_threshold_uses_p95(self) -> None:
        """fallback_threshold returns p95 when calibrated."""
        config = AnomalyThresholdConfig(national_p95_threshold=0.12)
        assert config.fallback_threshold == 0.12

    def test_rolling_window_minimum(self) -> None:
        """rolling_window_years must be >= 2."""
        with pytest.raises(ValidationError, match="rolling_window_years"):
            AnomalyThresholdConfig(rolling_window_years=1)

    def test_empirical_percentile_range(self) -> None:
        """empirical_percentile must be in [1, 99]."""
        with pytest.raises(ValidationError, match="empirical_percentile"):
            AnomalyThresholdConfig(empirical_percentile=100)

    def test_config_is_frozen(self) -> None:
        """Config model is immutable."""
        config = AnomalyThresholdConfig()
        with pytest.raises(ValidationError):
            config.z_score_k = 3.0  # type: ignore[misc]


class TestSmoothedCoefficientSeries:
    """Test SmoothedCoefficientSeries model (T009)."""

    def test_create_valid_series(self) -> None:
        """Create series with matching list lengths."""
        series = SmoothedCoefficientSeries(
            fips_code="26163",
            coefficient_name="profit_rate",
            alpha=0.3,
            years=[2018, 2019, 2020, 2021, 2022],
            raw_values=[0.04, 0.06, 0.05, 0.04, 0.05],
            smoothed_values=[0.04, 0.046, 0.048, 0.046, 0.047],
        )
        assert series.coefficient_name == "profit_rate"
        assert series.alpha == 0.3
        assert len(series.years) == 5

    def test_mismatched_list_lengths_raises(self) -> None:
        """Lists must have equal length."""
        with pytest.raises(ValidationError, match="List lengths"):
            SmoothedCoefficientSeries(
                fips_code="26163",
                coefficient_name="profit_rate",
                alpha=0.3,
                years=[2018, 2019, 2020],
                raw_values=[0.04, 0.06],  # Wrong length
                smoothed_values=[0.04, 0.046, 0.048],
            )

    def test_alpha_boundary_zero(self) -> None:
        """Alpha can be 0.0 (full smoothing)."""
        series = SmoothedCoefficientSeries(
            fips_code="26163",
            coefficient_name="profit_rate",
            alpha=0.0,
            years=[2020],
            raw_values=[0.04],
            smoothed_values=[0.04],
        )
        assert series.alpha == 0.0

    def test_alpha_boundary_one(self) -> None:
        """Alpha can be 1.0 (no smoothing)."""
        series = SmoothedCoefficientSeries(
            fips_code="26163",
            coefficient_name="profit_rate",
            alpha=1.0,
            years=[2020],
            raw_values=[0.04],
            smoothed_values=[0.04],
        )
        assert series.alpha == 1.0

    def test_alpha_out_of_range_raises(self) -> None:
        """Alpha must be in [0, 1]."""
        with pytest.raises(ValidationError, match="alpha"):
            SmoothedCoefficientSeries(
                fips_code="26163",
                coefficient_name="profit_rate",
                alpha=1.5,  # Invalid
                years=[2020],
                raw_values=[0.04],
                smoothed_values=[0.04],
            )

    def test_variance_reduction_calculation(self) -> None:
        """variance_reduction computes ratio correctly."""
        # Raw values have high variance, smoothed have lower
        series = SmoothedCoefficientSeries(
            fips_code="26163",
            coefficient_name="profit_rate",
            alpha=0.3,
            years=[2018, 2019, 2020, 2021, 2022],
            raw_values=[0.02, 0.08, 0.03, 0.07, 0.04],  # High variance
            smoothed_values=[0.02, 0.038, 0.036, 0.046, 0.044],  # Lower variance
        )
        # Smoothed variance should be less than raw
        assert series.variance_reduction < 1.0

    def test_variance_reduction_single_value(self) -> None:
        """variance_reduction returns 1.0 for insufficient data."""
        series = SmoothedCoefficientSeries(
            fips_code="26163",
            coefficient_name="profit_rate",
            alpha=0.3,
            years=[2020],
            raw_values=[0.04],
            smoothed_values=[0.04],
        )
        assert series.variance_reduction == 1.0

    def test_series_is_frozen(self) -> None:
        """Series model is immutable."""
        series = SmoothedCoefficientSeries(
            fips_code="26163",
            coefficient_name="profit_rate",
            alpha=0.3,
            years=[2020],
            raw_values=[0.04],
            smoothed_values=[0.04],
        )
        with pytest.raises(ValidationError):
            series.alpha = 0.5  # type: ignore[misc]


class TestDeindustrializationSignal:
    """Test DeindustrializationSignal model (T010)."""

    def test_create_valid_signal(self) -> None:
        """Create signal with valid year range."""
        signal = DeindustrializationSignal(
            core_county="26163",  # Wayne (Detroit)
            suburb_county="26125",  # Oakland
            year_range=(2010, 2022),
            core_dept_i_trend=-0.005,  # Declining
            suburb_dept_i_trend=0.002,  # Growing
            signal_detected=True,
            signal_strength=0.007,
        )
        assert signal.core_county == "26163"
        assert signal.suburb_county == "26125"
        assert signal.signal_detected is True

    def test_core_declining_property(self) -> None:
        """core_declining returns True for negative trend."""
        signal = DeindustrializationSignal(
            core_county="26163",
            suburb_county="26125",
            year_range=(2010, 2022),
            core_dept_i_trend=-0.005,
            suburb_dept_i_trend=0.002,
            signal_detected=True,
            signal_strength=0.007,
        )
        assert signal.core_declining is True

    def test_core_stagnating_property(self) -> None:
        """core_stagnating returns True for near-zero trend."""
        signal = DeindustrializationSignal(
            core_county="26163",
            suburb_county="26125",
            year_range=(2010, 2022),
            core_dept_i_trend=0.0005,  # Near zero
            suburb_dept_i_trend=0.002,
            signal_detected=True,
            signal_strength=0.0015,
        )
        assert signal.core_stagnating is True

    def test_invalid_year_range_raises(self) -> None:
        """year_range start must be less than end."""
        with pytest.raises(ValidationError, match="year_range"):
            DeindustrializationSignal(
                core_county="26163",
                suburb_county="26125",
                year_range=(2022, 2010),  # Invalid: reversed
                core_dept_i_trend=-0.005,
                suburb_dept_i_trend=0.002,
                signal_detected=True,
                signal_strength=0.007,
            )

    def test_signal_is_frozen(self) -> None:
        """Signal model is immutable."""
        signal = DeindustrializationSignal(
            core_county="26163",
            suburb_county="26125",
            year_range=(2010, 2022),
            core_dept_i_trend=-0.005,
            suburb_dept_i_trend=0.002,
            signal_detected=True,
            signal_strength=0.007,
        )
        with pytest.raises(ValidationError):
            signal.signal_detected = False  # type: ignore[misc]


class TestTransitionAnnotation:
    """Test TransitionAnnotation model (T011)."""

    def test_create_valid_annotation(self) -> None:
        """Create annotation with all required fields."""
        annotation = TransitionAnnotation(
            transition_key="26163_2019_2020",
            annotation_type="documented_shock",
            description="COVID-19 pandemic impact on manufacturing",
            annotated_by="analyst_jdoe",
            annotated_at=datetime(2026, 1, 31, 12, 0, 0),
        )
        assert annotation.transition_key == "26163_2019_2020"
        assert annotation.annotation_type == "documented_shock"

    def test_annotation_type_validation(self) -> None:
        """annotation_type must be one of the allowed literals."""
        # Valid types
        for valid_type in [
            "documented_shock",
            "data_quality_issue",
            "structural_shift",
            "other",
        ]:
            annotation = TransitionAnnotation(
                transition_key="26163_2019_2020",
                annotation_type=valid_type,  # type: ignore[arg-type]
                description="Test annotation",
                annotated_by="analyst",
                annotated_at=datetime.now(),
            )
            assert annotation.annotation_type == valid_type

    def test_invalid_annotation_type_raises(self) -> None:
        """Invalid annotation_type raises ValidationError."""
        with pytest.raises(ValidationError, match="annotation_type"):
            TransitionAnnotation(
                transition_key="26163_2019_2020",
                annotation_type="invalid_type",  # type: ignore[arg-type]
                description="Test annotation",
                annotated_by="analyst",
                annotated_at=datetime.now(),
            )

    def test_empty_description_raises(self) -> None:
        """description cannot be empty."""
        with pytest.raises(ValidationError, match="description"):
            TransitionAnnotation(
                transition_key="26163_2019_2020",
                annotation_type="documented_shock",
                description="",  # Empty
                annotated_by="analyst",
                annotated_at=datetime.now(),
            )

    def test_annotation_is_frozen(self) -> None:
        """Annotation model is immutable."""
        annotation = TransitionAnnotation(
            transition_key="26163_2019_2020",
            annotation_type="documented_shock",
            description="Test",
            annotated_by="analyst",
            annotated_at=datetime.now(),
        )
        with pytest.raises(ValidationError):
            annotation.description = "Updated"  # type: ignore[misc]


class TestTemporalValidationReport:
    """Test TemporalValidationReport model (T012)."""

    @pytest.fixture
    def sample_config(self) -> AnomalyThresholdConfig:
        """Create sample threshold config."""
        return AnomalyThresholdConfig()

    @pytest.fixture
    def sample_transition(self) -> TemporalTransition:
        """Create sample transition."""
        return TemporalTransition(
            fips_code="26163",
            year_from=2020,
            year_to=2021,
            delta_total_v=0.05,
            delta_profit_rate=-0.02,
            detection_method=DetectionMethod.Z_SCORE,
        )

    @pytest.fixture
    def anomalous_transition(self) -> TemporalTransition:
        """Create sample anomalous transition."""
        flag = AnomalyFlag(component="total_v", value=0.25, threshold=0.15)
        return TemporalTransition(
            fips_code="26163",
            year_from=2019,
            year_to=2020,
            delta_total_v=0.25,
            delta_profit_rate=-0.10,
            flags_raised=[flag],
            detection_method=DetectionMethod.Z_SCORE,
        )

    def test_create_valid_report(
        self, sample_config: AnomalyThresholdConfig, sample_transition: TemporalTransition
    ) -> None:
        """Create report with required fields."""
        report = TemporalValidationReport(
            fips_codes=["26163"],
            year_range=(2020, 2022),
            generated_at=datetime.now(),
            transitions=[sample_transition],
            threshold_config=sample_config,
        )
        assert report.fips_codes == ["26163"]
        assert len(report.transitions) == 1

    def test_anomalous_transitions_property(
        self,
        sample_config: AnomalyThresholdConfig,
        sample_transition: TemporalTransition,
        anomalous_transition: TemporalTransition,
    ) -> None:
        """anomalous_transitions filters correctly."""
        report = TemporalValidationReport(
            fips_codes=["26163"],
            year_range=(2019, 2022),
            generated_at=datetime.now(),
            transitions=[sample_transition, anomalous_transition],
            threshold_config=sample_config,
        )
        anomalous = report.anomalous_transitions
        assert len(anomalous) == 1
        assert anomalous[0].year_from == 2019

    def test_flags_by_year_property(
        self, sample_config: AnomalyThresholdConfig, anomalous_transition: TemporalTransition
    ) -> None:
        """flags_by_year groups flags correctly."""
        report = TemporalValidationReport(
            fips_codes=["26163"],
            year_range=(2019, 2022),
            generated_at=datetime.now(),
            transitions=[anomalous_transition],
            threshold_config=sample_config,
        )
        flags_by_year = report.flags_by_year
        assert 2020 in flags_by_year
        assert len(flags_by_year[2020]) == 1

    def test_systemic_shock_years_property(self, sample_config: AnomalyThresholdConfig) -> None:
        """systemic_shock_years detects multi-county flags."""
        flag1 = AnomalyFlag(component="total_v", value=0.25, threshold=0.15)
        flag2 = AnomalyFlag(component="profit_rate", value=-0.30, threshold=0.15)

        t1 = TemporalTransition(
            fips_code="26163",
            year_from=2019,
            year_to=2020,
            delta_total_v=0.25,
            delta_profit_rate=-0.02,
            flags_raised=[flag1],
            detection_method=DetectionMethod.Z_SCORE,
        )
        t2 = TemporalTransition(
            fips_code="26125",
            year_from=2019,
            year_to=2020,
            delta_total_v=0.10,
            delta_profit_rate=-0.30,
            flags_raised=[flag2],
            detection_method=DetectionMethod.Z_SCORE,
        )

        report = TemporalValidationReport(
            fips_codes=["26163", "26125"],
            year_range=(2019, 2022),
            generated_at=datetime.now(),
            transitions=[t1, t2],
            threshold_config=sample_config,
        )
        shock_years = report.systemic_shock_years
        assert 2020 in shock_years

    def test_invalid_year_range_raises(
        self, sample_config: AnomalyThresholdConfig, sample_transition: TemporalTransition
    ) -> None:
        """year_range start must be less than end."""
        with pytest.raises(ValidationError, match="year_range"):
            TemporalValidationReport(
                fips_codes=["26163"],
                year_range=(2022, 2020),  # Invalid: reversed
                generated_at=datetime.now(),
                transitions=[sample_transition],
                threshold_config=sample_config,
            )

    def test_empty_fips_codes_raises(
        self, sample_config: AnomalyThresholdConfig, sample_transition: TemporalTransition
    ) -> None:
        """fips_codes must have at least one element."""
        with pytest.raises(ValidationError, match="fips_codes"):
            TemporalValidationReport(
                fips_codes=[],  # Empty
                year_range=(2020, 2022),
                generated_at=datetime.now(),
                transitions=[sample_transition],
                threshold_config=sample_config,
            )

    def test_report_is_frozen(
        self, sample_config: AnomalyThresholdConfig, sample_transition: TemporalTransition
    ) -> None:
        """Report model is immutable."""
        report = TemporalValidationReport(
            fips_codes=["26163"],
            year_range=(2020, 2022),
            generated_at=datetime.now(),
            transitions=[sample_transition],
            threshold_config=sample_config,
        )
        with pytest.raises(ValidationError):
            report.fips_codes = ["26125"]  # type: ignore[misc]
