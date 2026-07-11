"""Unit tests for report generation and computed properties.

Feature: 003-hydrator-temporal-validation
Phase 6: Report Generation & Calibration

Tests cover:
- T044: TemporalValidationReport computed properties
- Report generation aggregation

TDD: These tests are written FIRST and should FAIL until implementation.
"""

from datetime import datetime

import pytest

from babylon.domain.economics.temporal.models import (
    AnomalyFlag,
    AnomalyThresholdConfig,
    DeindustrializationSignal,
    DetectionMethod,
    SmoothedCoefficientSeries,
    TemporalTransition,
    TemporalValidationReport,
)


class TestTemporalValidationReportComputedProperties:
    """Test TemporalValidationReport computed properties (T044)."""

    def test_anomalous_transitions_filters_correctly(self) -> None:
        """anomalous_transitions returns only transitions with flags."""
        # Create mix of anomalous and non-anomalous transitions
        anomalous = TemporalTransition(
            fips_code="26163",
            year_from=2019,
            year_to=2020,
            delta_total_v=0.25,
            delta_profit_rate=0.05,
            detection_method=DetectionMethod.Z_SCORE,
            flags_raised=[
                AnomalyFlag(component="total_v", value=0.25, threshold=2.5, z_score=3.0),
            ],
        )

        non_anomalous = TemporalTransition(
            fips_code="26163",
            year_from=2020,
            year_to=2021,
            delta_total_v=0.05,
            delta_profit_rate=0.02,
            detection_method=DetectionMethod.Z_SCORE,
            flags_raised=[],
        )

        report = TemporalValidationReport(
            fips_codes=["26163"],
            year_range=(2019, 2021),
            generated_at=datetime.now(),
            transitions=[anomalous, non_anomalous],
            threshold_config=AnomalyThresholdConfig(),
        )

        assert len(report.anomalous_transitions) == 1
        assert report.anomalous_transitions[0] == anomalous

    def test_flags_by_year_groups_correctly(self) -> None:
        """flags_by_year groups flags by year_to."""
        flag_2020 = AnomalyFlag(component="total_v", value=0.25, threshold=2.5, z_score=3.0)
        flag_2021_a = AnomalyFlag(component="profit_rate", value=0.30, threshold=2.5, z_score=3.5)
        flag_2021_b = AnomalyFlag(component="dept_I", value=0.20, threshold=2.5, z_score=2.8)

        trans_2020 = TemporalTransition(
            fips_code="26163",
            year_from=2019,
            year_to=2020,
            delta_total_v=0.25,
            delta_profit_rate=0.05,
            detection_method=DetectionMethod.Z_SCORE,
            flags_raised=[flag_2020],
        )

        trans_2021 = TemporalTransition(
            fips_code="26163",
            year_from=2020,
            year_to=2021,
            delta_total_v=0.30,
            delta_profit_rate=0.30,
            detection_method=DetectionMethod.Z_SCORE,
            flags_raised=[flag_2021_a, flag_2021_b],
        )

        report = TemporalValidationReport(
            fips_codes=["26163"],
            year_range=(2019, 2021),
            generated_at=datetime.now(),
            transitions=[trans_2020, trans_2021],
            threshold_config=AnomalyThresholdConfig(),
        )

        flags_by_year = report.flags_by_year

        assert 2020 in flags_by_year
        assert 2021 in flags_by_year
        assert len(flags_by_year[2020]) == 1
        assert len(flags_by_year[2021]) == 2

    def test_systemic_shock_years_detects_multiple_county_flags(self) -> None:
        """systemic_shock_years returns years where 2+ counties flagged."""
        # 2020: Both Wayne and Oakland flagged (systemic - COVID)
        wayne_2020 = TemporalTransition(
            fips_code="26163",
            year_from=2019,
            year_to=2020,
            delta_total_v=0.25,
            delta_profit_rate=0.05,
            detection_method=DetectionMethod.Z_SCORE,
            flags_raised=[
                AnomalyFlag(component="total_v", value=0.25, threshold=2.5, z_score=3.0),
            ],
        )

        oakland_2020 = TemporalTransition(
            fips_code="26125",
            year_from=2019,
            year_to=2020,
            delta_total_v=0.22,
            delta_profit_rate=0.04,
            detection_method=DetectionMethod.Z_SCORE,
            flags_raised=[
                AnomalyFlag(component="total_v", value=0.22, threshold=2.5, z_score=2.8),
            ],
        )

        # 2021: Only Wayne flagged (county-specific)
        wayne_2021 = TemporalTransition(
            fips_code="26163",
            year_from=2020,
            year_to=2021,
            delta_total_v=0.18,
            delta_profit_rate=0.03,
            detection_method=DetectionMethod.Z_SCORE,
            flags_raised=[
                AnomalyFlag(component="total_v", value=0.18, threshold=2.5, z_score=2.6),
            ],
        )

        oakland_2021 = TemporalTransition(
            fips_code="26125",
            year_from=2020,
            year_to=2021,
            delta_total_v=0.05,
            delta_profit_rate=0.02,
            detection_method=DetectionMethod.Z_SCORE,
            flags_raised=[],  # No flags
        )

        report = TemporalValidationReport(
            fips_codes=["26163", "26125"],
            year_range=(2019, 2021),
            generated_at=datetime.now(),
            transitions=[wayne_2020, oakland_2020, wayne_2021, oakland_2021],
            threshold_config=AnomalyThresholdConfig(),
        )

        systemic_years = report.systemic_shock_years

        assert 2020 in systemic_years  # Both counties flagged
        assert 2021 not in systemic_years  # Only one county flagged

    def test_empty_report_handles_gracefully(self) -> None:
        """Report with no transitions handles computed properties."""
        report = TemporalValidationReport(
            fips_codes=["26163"],
            year_range=(2019, 2020),
            generated_at=datetime.now(),
            transitions=[],
            threshold_config=AnomalyThresholdConfig(),
        )

        assert report.anomalous_transitions == []
        assert report.flags_by_year == {}
        assert report.systemic_shock_years == []


class TestReportGeneratorImpl:
    """Test ReportGeneratorImpl class (T047)."""

    def test_report_generator_impl_exists(self) -> None:
        """ReportGeneratorImpl can be imported and instantiated."""
        from babylon.domain.economics.temporal.reports import ReportGeneratorImpl

        generator = ReportGeneratorImpl(hydrator=None)  # type: ignore[arg-type]
        assert hasattr(generator, "generate_report")

    def test_generate_report_returns_validation_report(self) -> None:
        """generate_report returns TemporalValidationReport."""
        from babylon.domain.economics.temporal.reports import ReportGeneratorImpl

        generator = ReportGeneratorImpl(hydrator=None)  # type: ignore[arg-type]
        assert callable(generator.generate_report)

    def test_generate_report_requires_minimum_years(self) -> None:
        """generate_report with <2 years raises ValueError."""
        from babylon.domain.economics.temporal.reports import ReportGeneratorImpl

        generator = ReportGeneratorImpl(hydrator=None)  # type: ignore[arg-type]
        config = AnomalyThresholdConfig()

        with pytest.raises(ValueError, match="at least 2"):
            generator.generate_report(
                fips="26163",
                years=[2020],  # Only 1 year
                config=config,
            )


class TestReportWithSmoothedSeries:
    """Test report includes smoothed series."""

    def test_report_includes_smoothed_series(self) -> None:
        """Report can contain smoothed coefficient series."""
        series = SmoothedCoefficientSeries(
            fips_code="26163",
            coefficient_name="profit_rate",
            alpha=0.3,
            years=[2018, 2019, 2020],
            raw_values=[0.04, 0.06, 0.05],
            smoothed_values=[0.04, 0.046, 0.0472],
        )

        report = TemporalValidationReport(
            fips_codes=["26163"],
            year_range=(2018, 2020),
            generated_at=datetime.now(),
            transitions=[],
            smoothed_series={"profit_rate": series},
            threshold_config=AnomalyThresholdConfig(),
        )

        assert "profit_rate" in report.smoothed_series
        assert report.smoothed_series["profit_rate"].alpha == 0.3


class TestReportWithSignals:
    """Test report includes deindustrialization signals."""

    def test_report_includes_signals(self) -> None:
        """Report can contain deindustrialization signals."""
        signal = DeindustrializationSignal(
            core_county="26163",
            suburb_county="26125",
            year_range=(2015, 2022),
            core_dept_i_trend=-0.005,
            suburb_dept_i_trend=0.002,
            signal_detected=True,
            signal_strength=0.007,
        )

        report = TemporalValidationReport(
            fips_codes=["26163", "26125"],
            year_range=(2015, 2022),
            generated_at=datetime.now(),
            transitions=[],
            signals=[signal],
            threshold_config=AnomalyThresholdConfig(),
        )

        assert len(report.signals) == 1
        assert report.signals[0].signal_detected is True


class TestReportWithAnnotations:
    """Test report includes annotations."""

    def test_report_includes_annotations(self) -> None:
        """Report can contain analyst annotations."""
        from babylon.domain.economics.temporal.models import TransitionAnnotation

        annotation = TransitionAnnotation(
            transition_key="26163_2019_2020",
            annotation_type="documented_shock",
            description="COVID-19 pandemic impact",
            annotated_by="analyst@example.com",
            annotated_at=datetime.now(),
        )

        report = TemporalValidationReport(
            fips_codes=["26163"],
            year_range=(2019, 2020),
            generated_at=datetime.now(),
            transitions=[],
            annotations=[annotation],
            threshold_config=AnomalyThresholdConfig(),
        )

        assert len(report.annotations) == 1
        assert report.annotations[0].annotation_type == "documented_shock"
