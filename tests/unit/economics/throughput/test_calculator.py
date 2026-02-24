"""Unit tests for ThroughputCalculator.

Feature: 014-throughput-position
TDD Phase: Red/Green

Tests for τ_through and π computation following FR-001, FR-002, FR-006, FR-007.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from babylon.economics.tensor import NoDataSentinel
from babylon.economics.throughput.calculator import (
    HOURS_PER_YEAR,
    MINIMUM_EMPLOYMENT_THRESHOLD,
    DefaultThroughputCalculator,
)
from babylon.economics.throughput.types import ThroughputMetrics

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_gdp_source() -> MagicMock:
    """Create a mock BEA GDP source."""
    source = MagicMock()
    source.get_county_gdp.return_value = None  # Default: no data
    return source


@pytest.fixture
def mock_qcew_source() -> MagicMock:
    """Create a mock QCEW source."""
    source = MagicMock()
    source.get_county_total_employment.return_value = None  # Default: no data
    source.get_county_employment_by_naics.return_value = {}  # Default: empty
    return source


@pytest.fixture
def mock_supply_chain() -> MagicMock:
    """Create a mock SupplyChainAnalyzer."""
    analyzer = MagicMock()
    analyzer.compute_depth.return_value = 3.0  # Default depth
    # Default: 10 sectors, 8 mapped, 100k employment (80% coverage = high quality)
    analyzer.get_sector_coverage.return_value = (10, 8, 100000)
    return analyzer


@pytest.fixture
def mock_melt_calculator() -> MagicMock:
    """Create a mock MELTCalculator."""
    calc = MagicMock()
    calc.get_melt.return_value = 65.0  # National MELT ~$65/hour
    return calc


@pytest.fixture
def calculator(
    mock_gdp_source: MagicMock,
    mock_qcew_source: MagicMock,
    mock_supply_chain: MagicMock,
    mock_melt_calculator: MagicMock,
) -> DefaultThroughputCalculator:
    """Create a calculator with mock dependencies."""
    return DefaultThroughputCalculator(
        gdp_source=mock_gdp_source,
        qcew_source=mock_qcew_source,
        supply_chain_analyzer=mock_supply_chain,
        melt_calculator=mock_melt_calculator,
    )


@pytest.fixture
def calculator_no_melt(
    mock_gdp_source: MagicMock,
    mock_qcew_source: MagicMock,
    mock_supply_chain: MagicMock,
) -> DefaultThroughputCalculator:
    """Create a calculator without MELT (for testing FR-006 degradation)."""
    return DefaultThroughputCalculator(
        gdp_source=mock_gdp_source,
        qcew_source=mock_qcew_source,
        supply_chain_analyzer=mock_supply_chain,
        melt_calculator=None,
    )


# =============================================================================
# TEST: τ_through COMPUTATION (FR-001)
# =============================================================================


class TestThroughputIntensity:
    """Tests for τ_through = GDP / (employment × 2080)."""

    def test_basic_computation(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
    ) -> None:
        """Test basic τ_through formula with known values."""
        # Wayne County: GDP = $95B, Employment = 800,000
        mock_gdp_source.get_county_gdp.return_value = 95_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 800_000

        result = calculator.compute_throughput_intensity("26163", 2022)

        # Expected: $95B / (800,000 × 2080) = $95B / 1,664,000,000 = $57.09
        expected = 95_000_000_000.0 / (800_000 * HOURS_PER_YEAR)
        assert isinstance(result, float)
        assert result == pytest.approx(expected, rel=1e-6)
        assert result == pytest.approx(57.09, rel=0.01)

    def test_no_data_when_gdp_unavailable(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
    ) -> None:
        """τ_through returns NoDataSentinel when GDP is unavailable."""
        mock_gdp_source.get_county_gdp.return_value = None
        mock_qcew_source.get_county_total_employment.return_value = 100_000

        result = calculator.compute_throughput_intensity("99999", 2022)

        assert isinstance(result, NoDataSentinel)
        assert "GDP unavailable" in result.reason
        assert result.fips == "99999"
        assert result.year == 2022

    def test_no_data_when_employment_unavailable(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
    ) -> None:
        """τ_through returns NoDataSentinel when employment is unavailable."""
        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = None

        result = calculator.compute_throughput_intensity("99999", 2022)

        assert isinstance(result, NoDataSentinel)
        assert "Employment unavailable" in result.reason

    def test_insufficient_employment_threshold(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
    ) -> None:
        """Small counties below 1,000 employment return INSUFFICIENT_DATA."""
        mock_gdp_source.get_county_gdp.return_value = 100_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 500  # Below threshold

        result = calculator.compute_throughput_intensity("12345", 2022)

        assert isinstance(result, NoDataSentinel)
        assert "INSUFFICIENT_DATA" in result.reason
        assert str(MINIMUM_EMPLOYMENT_THRESHOLD) in result.reason

    def test_exactly_at_threshold_passes(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
    ) -> None:
        """Counties at exactly 1,000 employment should pass threshold."""
        mock_gdp_source.get_county_gdp.return_value = 100_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 1000  # At threshold

        result = calculator.compute_throughput_intensity("12345", 2022)

        assert isinstance(result, float)
        # $100M / (1000 × 2080) = $48.08
        assert result == pytest.approx(48.08, rel=0.01)


# =============================================================================
# TEST: π COMPUTATION (FR-002, FR-006)
# =============================================================================


class TestThroughputPosition:
    """Tests for π = τ_through / τ_national."""

    def test_basic_computation(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_melt_calculator: MagicMock,
    ) -> None:
        """Test basic π formula with known values."""
        # Setup: τ_through = $57.09, τ_national = $65
        mock_gdp_source.get_county_gdp.return_value = 95_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 800_000
        mock_melt_calculator.get_melt.return_value = 65.0

        result = calculator.compute_throughput_position("26163", 2022)

        # Expected: π = 57.09 / 65.0 = 0.878
        assert isinstance(result, float)
        assert result == pytest.approx(0.878, rel=0.01)

    def test_high_throughput_position(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_melt_calculator: MagicMock,
    ) -> None:
        """Manhattan should have π > 1.0 (coordination chokepoint)."""
        # Manhattan: GDP = $700B, Employment = 2,500,000 → τ = $134.62
        mock_gdp_source.get_county_gdp.return_value = 700_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 2_500_000
        mock_melt_calculator.get_melt.return_value = 65.0

        result = calculator.compute_throughput_position("36061", 2022)

        # Expected: π = 134.62 / 65.0 = 2.07
        assert isinstance(result, float)
        assert result > 1.0  # Coordination chokepoint

    def test_no_data_when_melt_unavailable(
        self,
        calculator_no_melt: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
    ) -> None:
        """π returns NoDataSentinel when MELT calculator not provided (FR-006)."""
        mock_gdp_source.get_county_gdp.return_value = 95_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 800_000

        result = calculator_no_melt.compute_throughput_position("26163", 2022)

        assert isinstance(result, NoDataSentinel)
        assert "MELT unavailable" in result.reason

    def test_tau_through_still_computed_without_melt(
        self,
        calculator_no_melt: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
    ) -> None:
        """τ_through should still be computed even without MELT (FR-006)."""
        mock_gdp_source.get_county_gdp.return_value = 95_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 800_000

        result = calculator_no_melt.compute_throughput_intensity("26163", 2022)

        assert isinstance(result, float)
        assert result == pytest.approx(57.09, rel=0.01)

    def test_no_data_propagates_from_tau_through(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
    ) -> None:
        """π propagates NoDataSentinel from τ_through computation."""
        mock_gdp_source.get_county_gdp.return_value = None

        result = calculator.compute_throughput_position("99999", 2022)

        assert isinstance(result, NoDataSentinel)
        assert "GDP unavailable" in result.reason


# =============================================================================
# TEST: FULL METRICS COMPUTATION
# =============================================================================


class TestComputeMetrics:
    """Tests for compute_metrics() returning ThroughputMetrics."""

    def test_returns_throughput_metrics(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
        mock_melt_calculator: MagicMock,
    ) -> None:
        """compute_metrics returns ThroughputMetrics container."""
        mock_gdp_source.get_county_gdp.return_value = 95_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 800_000
        mock_supply_chain.compute_depth.return_value = 2.5
        mock_melt_calculator.get_melt.return_value = 65.0

        result = calculator.compute_metrics("26163", 2022)

        assert isinstance(result, ThroughputMetrics)
        assert result.fips == "26163"
        assert result.year == 2022
        assert result.tau_through == pytest.approx(57.09, rel=0.01)
        assert result.pi == pytest.approx(0.878, rel=0.01)
        assert result.supply_chain_depth == 2.5

    def test_pi_none_when_melt_unavailable(
        self,
        calculator_no_melt: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """compute_metrics returns pi=None when MELT unavailable (FR-006)."""
        mock_gdp_source.get_county_gdp.return_value = 95_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 800_000
        mock_supply_chain.compute_depth.return_value = 2.5

        result = calculator_no_melt.compute_metrics("26163", 2022)

        assert isinstance(result, ThroughputMetrics)
        assert result.tau_through == pytest.approx(57.09, rel=0.01)
        assert result.pi is None  # Not available without MELT
        assert result.supply_chain_depth == 2.5

    def test_no_data_sentinel_when_gdp_unavailable(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
    ) -> None:
        """compute_metrics returns NoDataSentinel when GDP unavailable."""
        mock_gdp_source.get_county_gdp.return_value = None

        result = calculator.compute_metrics("99999", 2022)

        assert isinstance(result, NoDataSentinel)

    def test_no_data_sentinel_when_depth_unavailable(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """compute_metrics returns NoDataSentinel when supply chain depth unavailable."""
        mock_gdp_source.get_county_gdp.return_value = 95_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 800_000
        mock_supply_chain.compute_depth.return_value = NoDataSentinel(
            "26163", 2022, "No NAICS data"
        )

        result = calculator.compute_metrics("26163", 2022)

        assert isinstance(result, NoDataSentinel)


# =============================================================================
# TEST: VALIDATION (FR-008)
# =============================================================================


class TestValidation:
    """Tests for sanity range validation per FR-008."""

    def test_valid_throughput_no_warning(self, calculator: DefaultThroughputCalculator) -> None:
        """Normal τ_through values pass without warning."""
        is_valid, warning = calculator.validate_throughput(65.0)
        assert is_valid is True
        assert warning is None

    def test_warning_below_expected_minimum(self, calculator: DefaultThroughputCalculator) -> None:
        """τ_through below $20 triggers warning."""
        is_valid, warning = calculator.validate_throughput(15.0)
        assert is_valid is True
        assert warning is not None
        assert "below expected minimum" in warning

    def test_warning_above_expected_maximum(self, calculator: DefaultThroughputCalculator) -> None:
        """τ_through above $200 triggers warning."""
        is_valid, warning = calculator.validate_throughput(250.0)
        assert is_valid is True
        assert warning is not None
        assert "above expected maximum" in warning

    def test_fail_below_warning_minimum(self, calculator: DefaultThroughputCalculator) -> None:
        """τ_through below $10 fails validation."""
        is_valid, warning = calculator.validate_throughput(5.0)
        assert is_valid is False
        assert "below minimum" in warning

    def test_fail_above_warning_maximum(self, calculator: DefaultThroughputCalculator) -> None:
        """τ_through above $500 fails validation."""
        is_valid, warning = calculator.validate_throughput(600.0)
        assert is_valid is False
        assert "above maximum" in warning


# =============================================================================
# TARGETED MUTATION SURVIVOR TESTS: compute_metrics data quality
# =============================================================================


class TestComputeMetricsDataQuality:
    """Targeted tests to kill mutation survivors in compute_metrics.

    Focuses on data quality classification (sector coverage → low/medium/high),
    is_estimated flag, sentinel propagation, and pi-optional behavior.
    """

    def test_data_quality_low_when_coverage_below_50pct(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """Data quality = 'low' when sector coverage ratio < 0.5."""
        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 200_000
        mock_supply_chain.compute_depth.return_value = 3.0
        # 10 sectors with data, 3 mapped (30% coverage)
        mock_supply_chain.get_sector_coverage.return_value = (10, 3, 100000)

        result = calculator.compute_metrics("26163", 2022)

        assert isinstance(result, ThroughputMetrics)
        assert result.data_quality == "low"
        assert result.is_estimated is True

    def test_data_quality_medium_when_coverage_50_to_80pct(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """Data quality = 'medium' when 0.5 <= coverage ratio < 0.8."""
        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 200_000
        mock_supply_chain.compute_depth.return_value = 3.0
        # 10 sectors with data, 6 mapped (60% coverage)
        mock_supply_chain.get_sector_coverage.return_value = (10, 6, 100000)

        result = calculator.compute_metrics("26163", 2022)

        assert isinstance(result, ThroughputMetrics)
        assert result.data_quality == "medium"
        assert result.is_estimated is True

    def test_data_quality_high_when_coverage_above_80pct(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """Data quality = 'high' when coverage ratio >= 0.8."""
        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 200_000
        mock_supply_chain.compute_depth.return_value = 3.0
        # 10 sectors with data, 9 mapped (90% coverage)
        mock_supply_chain.get_sector_coverage.return_value = (10, 9, 100000)

        result = calculator.compute_metrics("26163", 2022)

        assert isinstance(result, ThroughputMetrics)
        assert result.data_quality == "high"
        assert result.is_estimated is False

    def test_data_quality_at_exact_50pct_boundary(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """At exactly 50% coverage, data quality should be 'medium' (not 'low')."""
        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 200_000
        mock_supply_chain.compute_depth.return_value = 3.0
        # 10 sectors, 5 mapped (exactly 50%)
        mock_supply_chain.get_sector_coverage.return_value = (10, 5, 100000)

        result = calculator.compute_metrics("26163", 2022)

        assert isinstance(result, ThroughputMetrics)
        assert result.data_quality == "medium"
        assert result.is_estimated is True

    def test_data_quality_at_exact_80pct_boundary(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """At exactly 80% coverage, data quality should be 'high' (not 'medium')."""
        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 200_000
        mock_supply_chain.compute_depth.return_value = 3.0
        # 10 sectors, 8 mapped (exactly 80%)
        mock_supply_chain.get_sector_coverage.return_value = (10, 8, 100000)

        result = calculator.compute_metrics("26163", 2022)

        assert isinstance(result, ThroughputMetrics)
        assert result.data_quality == "high"
        assert result.is_estimated is False

    def test_is_estimated_true_when_not_full_coverage(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """is_estimated should be True when coverage < 80% (low or medium)."""
        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 200_000
        mock_supply_chain.compute_depth.return_value = 3.0
        # 70% coverage → medium quality, estimated
        mock_supply_chain.get_sector_coverage.return_value = (10, 7, 100000)

        result = calculator.compute_metrics("26163", 2022)

        assert isinstance(result, ThroughputMetrics)
        assert result.is_estimated is True

    def test_returns_sentinel_when_tau_unavailable(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
    ) -> None:
        """compute_metrics propagates NoDataSentinel from τ_through failure."""
        mock_gdp_source.get_county_gdp.return_value = None

        result = calculator.compute_metrics("99999", 2022)

        assert isinstance(result, NoDataSentinel)
        assert "GDP unavailable" in result.reason

    def test_returns_sentinel_when_depth_unavailable(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """compute_metrics propagates NoDataSentinel from depth failure."""
        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 200_000
        mock_supply_chain.compute_depth.return_value = NoDataSentinel(
            "26163", 2022, "No NAICS data"
        )

        result = calculator.compute_metrics("26163", 2022)

        assert isinstance(result, NoDataSentinel)

    def test_pi_optional_when_no_melt(
        self,
        calculator_no_melt: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """compute_metrics returns valid ThroughputMetrics with pi=None when no MELT."""
        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 200_000
        mock_supply_chain.compute_depth.return_value = 3.0

        result = calculator_no_melt.compute_metrics("26163", 2022)

        assert isinstance(result, ThroughputMetrics)
        assert result.pi is None
        assert result.tau_through > 0
        assert result.supply_chain_depth == 3.0

    def test_result_contains_valid_tau_and_depth(
        self,
        calculator: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """Valid compute_metrics result should have non-sentinel τ and depth."""
        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 200_000
        mock_supply_chain.compute_depth.return_value = 2.5

        result = calculator.compute_metrics("26163", 2022)

        assert isinstance(result, ThroughputMetrics)
        # τ_through = 50B / (200k × 2080) = $120.19
        expected_tau = 50_000_000_000.0 / (200_000 * 2080)
        assert result.tau_through == pytest.approx(expected_tau, rel=1e-6)
        assert result.supply_chain_depth == 2.5


# =============================================================================
# MUTATION-KILLING TESTS: compute_all_counties, commuter methods
# =============================================================================


class TestComputeAllCountiesMutationKillers:
    """Mutation-killing tests for compute_all_counties."""

    def test_returns_metrics_for_each_county(
        self,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
        mock_melt_calculator: MagicMock,
    ) -> None:
        """compute_all_counties returns metrics for each county with GDP data."""
        mock_gdp_source.get_all_counties.return_value = ["26163", "26125"]
        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 200_000
        mock_supply_chain.compute_depth.return_value = 3.0

        calc = DefaultThroughputCalculator(
            gdp_source=mock_gdp_source,
            qcew_source=mock_qcew_source,
            supply_chain_analyzer=mock_supply_chain,
            melt_calculator=mock_melt_calculator,
        )
        results = calc.compute_all_counties(2022)

        assert len(results) == 2
        assert "26163" in results
        assert "26125" in results
        assert isinstance(results["26163"], ThroughputMetrics)

    def test_empty_county_list_returns_empty_dict(
        self,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """No counties with GDP data → empty dict."""
        mock_gdp_source.get_all_counties.return_value = []

        calc = DefaultThroughputCalculator(
            gdp_source=mock_gdp_source,
            qcew_source=mock_qcew_source,
            supply_chain_analyzer=mock_supply_chain,
        )
        results = calc.compute_all_counties(2022)

        assert results == {}

    def test_none_county_list_returns_empty_dict(
        self,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """None from get_all_counties → empty dict."""
        mock_gdp_source.get_all_counties.return_value = None

        calc = DefaultThroughputCalculator(
            gdp_source=mock_gdp_source,
            qcew_source=mock_qcew_source,
            supply_chain_analyzer=mock_supply_chain,
        )
        results = calc.compute_all_counties(2022)

        assert results == {}

    def test_mixed_success_and_failure(
        self,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """Some counties succeed, some return NoDataSentinel."""
        mock_gdp_source.get_all_counties.return_value = ["26163", "99999"]

        def gdp_side_effect(fips: str, year: int) -> float | None:
            if fips == "26163":
                return 50_000_000_000.0
            return None

        mock_gdp_source.get_county_gdp.side_effect = gdp_side_effect
        mock_qcew_source.get_county_total_employment.return_value = 200_000
        mock_supply_chain.compute_depth.return_value = 3.0

        calc = DefaultThroughputCalculator(
            gdp_source=mock_gdp_source,
            qcew_source=mock_qcew_source,
            supply_chain_analyzer=mock_supply_chain,
        )
        results = calc.compute_all_counties(2022)

        assert len(results) == 2
        assert isinstance(results["26163"], ThroughputMetrics)
        assert isinstance(results["99999"], NoDataSentinel)


class TestResidenceThroughputMutationKillers:
    """Mutation-killing tests for compute_residence_throughput."""

    def test_no_commuter_source_returns_sentinel(
        self,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """No commuter source → NoDataSentinel."""
        calc = DefaultThroughputCalculator(
            gdp_source=mock_gdp_source,
            qcew_source=mock_qcew_source,
            supply_chain_analyzer=mock_supply_chain,
            commuter_source=None,
        )
        result = calc.compute_residence_throughput("26163", 2022)
        assert isinstance(result, NoDataSentinel)
        assert "Commuter source unavailable" in result.reason

    def test_no_gdp_returns_sentinel(
        self,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """No GDP data → NoDataSentinel."""
        mock_commuter = MagicMock()
        mock_gdp_source.get_county_gdp.return_value = None

        calc = DefaultThroughputCalculator(
            gdp_source=mock_gdp_source,
            qcew_source=mock_qcew_source,
            supply_chain_analyzer=mock_supply_chain,
            commuter_source=mock_commuter,
        )
        result = calc.compute_residence_throughput("26163", 2022)
        assert isinstance(result, NoDataSentinel)
        assert "GDP unavailable" in result.reason

    def test_no_residence_employment_returns_sentinel(
        self,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """No residence employment → NoDataSentinel."""
        mock_commuter = MagicMock()
        mock_commuter.get_residence_employment.return_value = None
        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0

        calc = DefaultThroughputCalculator(
            gdp_source=mock_gdp_source,
            qcew_source=mock_qcew_source,
            supply_chain_analyzer=mock_supply_chain,
            commuter_source=mock_commuter,
        )
        result = calc.compute_residence_throughput("26163", 2022)
        assert isinstance(result, NoDataSentinel)
        assert "residence employment unavailable" in result.reason

    def test_insufficient_residence_employment_returns_sentinel(
        self,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """Residence employment below threshold → INSUFFICIENT_DATA."""
        mock_commuter = MagicMock()
        mock_commuter.get_residence_employment.return_value = 500
        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0

        calc = DefaultThroughputCalculator(
            gdp_source=mock_gdp_source,
            qcew_source=mock_qcew_source,
            supply_chain_analyzer=mock_supply_chain,
            commuter_source=mock_commuter,
        )
        result = calc.compute_residence_throughput("26163", 2022)
        assert isinstance(result, NoDataSentinel)
        assert "INSUFFICIENT_DATA" in result.reason

    def test_valid_residence_throughput_computed(
        self,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """Valid data → τ_residence = GDP / (residence_emp × 2080)."""
        mock_commuter = MagicMock()
        mock_commuter.get_residence_employment.return_value = 150_000
        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0

        calc = DefaultThroughputCalculator(
            gdp_source=mock_gdp_source,
            qcew_source=mock_qcew_source,
            supply_chain_analyzer=mock_supply_chain,
            commuter_source=mock_commuter,
        )
        result = calc.compute_residence_throughput("26163", 2022)

        assert isinstance(result, float)
        expected = 50_000_000_000.0 / (150_000 * HOURS_PER_YEAR)
        assert result == pytest.approx(expected, rel=1e-6)

    def test_at_threshold_passes(
        self,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """Residence employment at exactly threshold → computes successfully."""
        mock_commuter = MagicMock()
        mock_commuter.get_residence_employment.return_value = MINIMUM_EMPLOYMENT_THRESHOLD
        mock_gdp_source.get_county_gdp.return_value = 10_000_000_000.0

        calc = DefaultThroughputCalculator(
            gdp_source=mock_gdp_source,
            qcew_source=mock_qcew_source,
            supply_chain_analyzer=mock_supply_chain,
            commuter_source=mock_commuter,
        )
        result = calc.compute_residence_throughput("26163", 2022)
        assert isinstance(result, float)


class TestCommuterAdjustedMetricsMutationKillers:
    """Mutation-killing tests for compute_commuter_adjusted_metrics."""

    def test_no_commuter_source_returns_defaults(
        self,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
        mock_melt_calculator: MagicMock,
    ) -> None:
        """Without commuter source, returns workplace metrics + commuter defaults."""
        from babylon.economics.throughput.types import CommuterAdjustedMetrics

        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 200_000

        calc = DefaultThroughputCalculator(
            gdp_source=mock_gdp_source,
            qcew_source=mock_qcew_source,
            supply_chain_analyzer=mock_supply_chain,
            melt_calculator=mock_melt_calculator,
            commuter_source=None,
        )
        result = calc.compute_commuter_adjusted_metrics("26163", 2022)

        assert isinstance(result, CommuterAdjustedMetrics)
        assert result.tau_through_workplace > 0
        assert result.has_commuter_data is False
        assert result.tau_through_residence is None
        assert result.net_commuter_balance == 0

    def test_tau_workplace_sentinel_propagates(
        self,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """NoDataSentinel from τ_workplace propagates."""
        mock_gdp_source.get_county_gdp.return_value = None

        calc = DefaultThroughputCalculator(
            gdp_source=mock_gdp_source,
            qcew_source=mock_qcew_source,
            supply_chain_analyzer=mock_supply_chain,
        )
        result = calc.compute_commuter_adjusted_metrics("26163", 2022)
        assert isinstance(result, NoDataSentinel)

    def test_with_commuter_data_job_importer(
        self,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
        mock_melt_calculator: MagicMock,
    ) -> None:
        """Positive net balance → is_job_importer=True."""
        from babylon.economics.throughput.types import CommuterAdjustedMetrics

        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 200_000

        mock_commuter = MagicMock()
        mock_commuter.get_net_commuter_balance.return_value = 50000  # Positive: job importer
        mock_commuter.get_residence_employment.return_value = 150_000

        calc = DefaultThroughputCalculator(
            gdp_source=mock_gdp_source,
            qcew_source=mock_qcew_source,
            supply_chain_analyzer=mock_supply_chain,
            melt_calculator=mock_melt_calculator,
            commuter_source=mock_commuter,
        )
        result = calc.compute_commuter_adjusted_metrics("26163", 2022)

        assert isinstance(result, CommuterAdjustedMetrics)
        assert result.has_commuter_data is True
        assert result.is_job_importer is True
        assert result.net_commuter_balance == 50000

    def test_with_commuter_data_job_exporter(
        self,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
        mock_melt_calculator: MagicMock,
    ) -> None:
        """Negative net balance → is_job_importer=False."""
        from babylon.economics.throughput.types import CommuterAdjustedMetrics

        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 200_000

        mock_commuter = MagicMock()
        mock_commuter.get_net_commuter_balance.return_value = -30000  # Negative: bedroom community
        mock_commuter.get_residence_employment.return_value = 250_000

        calc = DefaultThroughputCalculator(
            gdp_source=mock_gdp_source,
            qcew_source=mock_qcew_source,
            supply_chain_analyzer=mock_supply_chain,
            melt_calculator=mock_melt_calculator,
            commuter_source=mock_commuter,
        )
        result = calc.compute_commuter_adjusted_metrics("26163", 2022)

        assert isinstance(result, CommuterAdjustedMetrics)
        assert result.is_job_importer is False
        assert result.net_commuter_balance == -30000

    def test_commuter_ratio_computed(
        self,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """commuter_ratio = residence_emp / workplace_emp."""
        from babylon.economics.throughput.types import CommuterAdjustedMetrics

        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 200_000

        mock_commuter = MagicMock()
        mock_commuter.get_net_commuter_balance.return_value = 0
        mock_commuter.get_residence_employment.return_value = 300_000

        calc = DefaultThroughputCalculator(
            gdp_source=mock_gdp_source,
            qcew_source=mock_qcew_source,
            supply_chain_analyzer=mock_supply_chain,
            commuter_source=mock_commuter,
        )
        result = calc.compute_commuter_adjusted_metrics("26163", 2022)

        assert isinstance(result, CommuterAdjustedMetrics)
        # 300000 / 200000 = 1.5
        assert result.commuter_ratio == pytest.approx(1.5, rel=1e-6)

    def test_balance_none_means_no_commuter_data(
        self,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_supply_chain: MagicMock,
    ) -> None:
        """None balance from commuter source → has_commuter_data=False."""
        from babylon.economics.throughput.types import CommuterAdjustedMetrics

        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 200_000

        mock_commuter = MagicMock()
        mock_commuter.get_net_commuter_balance.return_value = None

        calc = DefaultThroughputCalculator(
            gdp_source=mock_gdp_source,
            qcew_source=mock_qcew_source,
            supply_chain_analyzer=mock_supply_chain,
            commuter_source=mock_commuter,
        )
        result = calc.compute_commuter_adjusted_metrics("26163", 2022)

        assert isinstance(result, CommuterAdjustedMetrics)
        assert result.has_commuter_data is False
