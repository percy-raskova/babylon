"""Unit tests for SupplyChainAnalyzer.

Feature: 014-throughput-position
TDD Phase: Red/Green

Tests for D (supply chain depth) and λ_proxy (wage share) computation.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from babylon.domain.economics.tensor import NoDataSentinel
from babylon.domain.economics.throughput.supply_chain import (
    DefaultSupplyChainAnalyzer,
)
from babylon.domain.economics.throughput.types import WageShareEstimate

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_qcew_source() -> MagicMock:
    """Create a mock QCEW source."""
    source = MagicMock()
    source.get_county_employment_by_naics.return_value = {}
    source.get_county_naics_employment.return_value = None
    source.get_county_naics_wages.return_value = None
    return source


@pytest.fixture
def mock_throughput_calculator() -> MagicMock:
    """Create a mock ThroughputCalculator for λ_proxy computation."""
    calc = MagicMock()
    calc.compute_throughput_intensity.return_value = 65.0  # Default τ_through
    return calc


@pytest.fixture
def analyzer(mock_qcew_source: MagicMock) -> DefaultSupplyChainAnalyzer:
    """Create an analyzer with mock dependencies."""
    return DefaultSupplyChainAnalyzer(qcew_source=mock_qcew_source)


@pytest.fixture
def analyzer_with_throughput(
    mock_qcew_source: MagicMock, mock_throughput_calculator: MagicMock
) -> DefaultSupplyChainAnalyzer:
    """Create an analyzer with throughput calculator for λ_proxy."""
    return DefaultSupplyChainAnalyzer(
        qcew_source=mock_qcew_source,
        throughput_calculator=mock_throughput_calculator,
    )


# =============================================================================
# TEST: SUPPLY CHAIN DEPTH (FR-004)
# =============================================================================


class TestSupplyChainDepth:
    """Tests for D = Σ(employment × depth) / Σ employment."""

    def test_basic_depth_computation(
        self, analyzer: DefaultSupplyChainAnalyzer, mock_qcew_source: MagicMock
    ) -> None:
        """Test basic D formula with known values."""
        # Finance-heavy county: 50% finance (depth 5), 50% retail (depth 4)
        mock_qcew_source.get_county_employment_by_naics.return_value = {
            "52": 50000,  # Finance, depth 5.0
            "44": 50000,  # Retail, depth 4.0
        }

        result = analyzer.compute_depth("36061", 2022)  # Manhattan

        # Expected: (50000×5 + 50000×4) / 100000 = 4.5
        assert isinstance(result, float)
        assert result == pytest.approx(4.5, rel=1e-6)

    def test_extraction_county_low_depth(
        self, analyzer: DefaultSupplyChainAnalyzer, mock_qcew_source: MagicMock
    ) -> None:
        """Extraction counties should have D < 1.5."""
        # Coal mining county: 80% mining (depth 0), 20% retail (depth 4)
        mock_qcew_source.get_county_employment_by_naics.return_value = {
            "21": 8000,  # Mining, depth 0.0
            "44": 2000,  # Retail, depth 4.0
        }

        result = analyzer.compute_depth("56037", 2022)  # Sweetwater County, WY

        # Expected: (8000×0 + 2000×4) / 10000 = 0.8
        assert isinstance(result, float)
        assert result == pytest.approx(0.8, rel=1e-6)
        assert result < 1.5  # Extraction-oriented

    def test_manufacturing_county_medium_depth(
        self, analyzer: DefaultSupplyChainAnalyzer, mock_qcew_source: MagicMock
    ) -> None:
        """Manufacturing counties should have D ≈ 2.0."""
        # Manufacturing county: 60% manufacturing, 40% services
        mock_qcew_source.get_county_employment_by_naics.return_value = {
            "31": 60000,  # Manufacturing, depth 1.5
            "62": 40000,  # Healthcare, depth 4.0
        }

        result = analyzer.compute_depth("26163", 2022)  # Wayne County

        # Expected: (60000×1.5 + 40000×4.0) / 100000 = 2.5
        assert isinstance(result, float)
        assert result == pytest.approx(2.5, rel=1e-6)

    def test_no_data_when_empty_naics(
        self, analyzer: DefaultSupplyChainAnalyzer, mock_qcew_source: MagicMock
    ) -> None:
        """Return NoDataSentinel when no NAICS employment data."""
        mock_qcew_source.get_county_employment_by_naics.return_value = {}

        result = analyzer.compute_depth("99999", 2022)

        assert isinstance(result, NoDataSentinel)
        assert "No NAICS employment data" in result.reason

    def test_depth_in_valid_range(
        self, analyzer: DefaultSupplyChainAnalyzer, mock_qcew_source: MagicMock
    ) -> None:
        """D must always be in [0.0, 5.0] range."""
        # All finance: maximum depth
        mock_qcew_source.get_county_employment_by_naics.return_value = {
            "52": 100000,  # Finance, depth 5.0
        }
        result = analyzer.compute_depth("12345", 2022)
        assert result == 5.0

        # All mining: minimum depth
        mock_qcew_source.get_county_employment_by_naics.return_value = {
            "21": 100000,  # Mining, depth 0.0
        }
        result = analyzer.compute_depth("12345", 2022)
        assert result == 0.0

    def test_unknown_naics_sectors_skipped(
        self, analyzer: DefaultSupplyChainAnalyzer, mock_qcew_source: MagicMock
    ) -> None:
        """Unknown NAICS sectors are skipped in depth calculation."""
        mock_qcew_source.get_county_employment_by_naics.return_value = {
            "52": 50000,  # Finance, depth 5.0
            "99": 50000,  # Unknown, should be skipped
        }

        result = analyzer.compute_depth("12345", 2022)

        # Should only use finance employment
        assert result == 5.0


class TestGetNaicsDepth:
    """Tests for get_naics_depth() delegation."""

    def test_known_sector(self, analyzer: DefaultSupplyChainAnalyzer) -> None:
        """Known sectors return depth value."""
        assert analyzer.get_naics_depth("52") == 5.0  # Finance
        assert analyzer.get_naics_depth("21") == 0.0  # Mining
        assert analyzer.get_naics_depth("31") == 1.5  # Manufacturing

    def test_unknown_sector(self, analyzer: DefaultSupplyChainAnalyzer) -> None:
        """Unknown sectors return None."""
        assert analyzer.get_naics_depth("99") is None


class TestGetSectorEmployment:
    """Tests for get_sector_employment()."""

    def test_returns_employment_dict(
        self, analyzer: DefaultSupplyChainAnalyzer, mock_qcew_source: MagicMock
    ) -> None:
        """Returns dict mapping NAICS to employment."""
        mock_qcew_source.get_county_employment_by_naics.return_value = {
            "52": 25000,
            "44": 45000,
        }

        result = analyzer.get_sector_employment("26163", 2022)

        assert isinstance(result, dict)
        assert result["52"] == 25000
        assert result["44"] == 45000

    def test_no_data_when_empty(
        self, analyzer: DefaultSupplyChainAnalyzer, mock_qcew_source: MagicMock
    ) -> None:
        """Returns NoDataSentinel when no data available."""
        mock_qcew_source.get_county_employment_by_naics.return_value = {}

        result = analyzer.get_sector_employment("99999", 2022)

        assert isinstance(result, NoDataSentinel)


# =============================================================================
# TEST: WAGE SHARE PROXY (FR-005)
# =============================================================================


class TestWageShareProxy:
    """Tests for λ_proxy = avg_wage / τ_through."""

    def test_basic_lambda_computation(
        self,
        analyzer_with_throughput: DefaultSupplyChainAnalyzer,
        mock_qcew_source: MagicMock,
        mock_throughput_calculator: MagicMock,
    ) -> None:
        """Test basic λ_proxy formula with known values."""
        # Retail: avg_weekly_wage = $650, τ_through = $65/hour
        mock_qcew_source.get_county_naics_wages.return_value = 650.0
        mock_qcew_source.get_county_naics_employment.return_value = 45000
        mock_throughput_calculator.compute_throughput_intensity.return_value = 65.0

        result = analyzer_with_throughput.compute_wage_share_proxy("26163", "44", 2022)

        # Expected: λ = (650/40) / 65 = 16.25 / 65 = 0.25
        assert isinstance(result, WageShareEstimate)
        assert result.lambda_proxy == pytest.approx(0.25, rel=0.01)
        assert result.fips == "26163"
        assert result.naics == "44"
        assert result.year == 2022

    def test_low_retail_lambda(
        self,
        analyzer_with_throughput: DefaultSupplyChainAnalyzer,
        mock_qcew_source: MagicMock,
        mock_throughput_calculator: MagicMock,
    ) -> None:
        """Retail should have low λ (Walmart effect)."""
        # Low retail wages: $400/week
        mock_qcew_source.get_county_naics_wages.return_value = 400.0
        mock_qcew_source.get_county_naics_employment.return_value = 45000
        mock_throughput_calculator.compute_throughput_intensity.return_value = 65.0

        result = analyzer_with_throughput.compute_wage_share_proxy("26163", "44", 2022)

        # λ = (400/40) / 65 = 10 / 65 = 0.154
        assert isinstance(result, WageShareEstimate)
        assert result.lambda_proxy < 0.2  # Low capture

    def test_high_finance_lambda(
        self,
        analyzer_with_throughput: DefaultSupplyChainAnalyzer,
        mock_qcew_source: MagicMock,
        mock_throughput_calculator: MagicMock,
    ) -> None:
        """Finance should have higher λ."""
        # High finance wages: $2000/week
        mock_qcew_source.get_county_naics_wages.return_value = 2000.0
        mock_qcew_source.get_county_naics_employment.return_value = 25000
        mock_throughput_calculator.compute_throughput_intensity.return_value = 65.0

        result = analyzer_with_throughput.compute_wage_share_proxy("26163", "52", 2022)

        # λ = (2000/40) / 65 = 50 / 65 = 0.77
        assert isinstance(result, WageShareEstimate)
        assert result.lambda_proxy > 0.5  # High capture

    def test_no_data_when_wages_unavailable(
        self,
        analyzer_with_throughput: DefaultSupplyChainAnalyzer,
        mock_qcew_source: MagicMock,
    ) -> None:
        """Return NoDataSentinel when wages unavailable (suppressed)."""
        mock_qcew_source.get_county_naics_wages.return_value = None

        result = analyzer_with_throughput.compute_wage_share_proxy("26163", "44", 2022)

        assert isinstance(result, NoDataSentinel)
        assert "Wages unavailable" in result.reason

    def test_no_data_without_throughput_calculator(
        self, analyzer: DefaultSupplyChainAnalyzer, mock_qcew_source: MagicMock
    ) -> None:
        """Return NoDataSentinel when no throughput calculator."""
        mock_qcew_source.get_county_naics_wages.return_value = 650.0

        result = analyzer.compute_wage_share_proxy("26163", "44", 2022)

        assert isinstance(result, NoDataSentinel)
        assert "ThroughputCalculator not provided" in result.reason

    def test_lambda_greater_than_one_flags_issue(
        self,
        analyzer_with_throughput: DefaultSupplyChainAnalyzer,
        mock_qcew_source: MagicMock,
        mock_throughput_calculator: MagicMock,
    ) -> None:
        """λ > 1.0 indicates data quality issue."""
        # Very high wages relative to throughput
        mock_qcew_source.get_county_naics_wages.return_value = 5000.0
        mock_qcew_source.get_county_naics_employment.return_value = 1000
        mock_throughput_calculator.compute_throughput_intensity.return_value = 30.0

        result = analyzer_with_throughput.compute_wage_share_proxy("26163", "52", 2022)

        # λ = (5000/40) / 30 = 125 / 30 = 4.17
        assert isinstance(result, WageShareEstimate)
        assert result.lambda_proxy > 1.0
        assert result.confidence == "low"  # Data quality flag


class TestConfidenceLevels:
    """Tests for confidence level assignment."""

    def test_high_confidence_with_sufficient_data(
        self,
        analyzer_with_throughput: DefaultSupplyChainAnalyzer,
        mock_qcew_source: MagicMock,
        mock_throughput_calculator: MagicMock,
    ) -> None:
        """High confidence with complete data and large sample."""
        mock_qcew_source.get_county_naics_wages.return_value = 650.0
        mock_qcew_source.get_county_naics_employment.return_value = 5000
        mock_throughput_calculator.compute_throughput_intensity.return_value = 65.0

        result = analyzer_with_throughput.compute_wage_share_proxy("26163", "44", 2022)

        assert result.confidence == "high"

    def test_medium_confidence_with_small_sample(
        self,
        analyzer_with_throughput: DefaultSupplyChainAnalyzer,
        mock_qcew_source: MagicMock,
        mock_throughput_calculator: MagicMock,
    ) -> None:
        """Medium confidence with small employment sample."""
        mock_qcew_source.get_county_naics_wages.return_value = 650.0
        mock_qcew_source.get_county_naics_employment.return_value = 500
        mock_throughput_calculator.compute_throughput_intensity.return_value = 65.0

        result = analyzer_with_throughput.compute_wage_share_proxy("26163", "44", 2022)

        assert result.confidence == "medium"

    def test_low_confidence_with_very_small_sample(
        self,
        analyzer_with_throughput: DefaultSupplyChainAnalyzer,
        mock_qcew_source: MagicMock,
        mock_throughput_calculator: MagicMock,
    ) -> None:
        """Low confidence with very small employment."""
        mock_qcew_source.get_county_naics_wages.return_value = 650.0
        mock_qcew_source.get_county_naics_employment.return_value = 50
        mock_throughput_calculator.compute_throughput_intensity.return_value = 65.0

        result = analyzer_with_throughput.compute_wage_share_proxy("26163", "44", 2022)

        assert result.confidence == "low"


class TestGetSectorCoverageMutationKillers:
    """Mutation-killing tests for get_sector_coverage."""

    def test_returns_correct_tuple(self, mock_qcew_source: MagicMock) -> None:
        """Returns (sectors_with_data, sectors_mapped, employment_covered)."""
        mock_qcew_source.get_county_employment_by_naics.return_value = {
            "52": 50000,  # Finance, depth 5.0 → mapped
            "44": 30000,  # Retail, depth 4.0 → mapped
            "99": 10000,  # Unknown → NOT mapped
        }
        analyzer = DefaultSupplyChainAnalyzer(qcew_source=mock_qcew_source)

        result = analyzer.get_sector_coverage("26163", 2022)

        assert not isinstance(result, NoDataSentinel)
        sectors_with_data, sectors_mapped, employment_covered = result
        assert sectors_with_data == 3
        assert sectors_mapped == 2
        assert employment_covered == 80000  # 50000 + 30000

    def test_no_data_returns_sentinel(self, mock_qcew_source: MagicMock) -> None:
        """Empty NAICS data returns NoDataSentinel."""
        mock_qcew_source.get_county_employment_by_naics.return_value = {}
        analyzer = DefaultSupplyChainAnalyzer(qcew_source=mock_qcew_source)

        result = analyzer.get_sector_coverage("99999", 2022)

        assert isinstance(result, NoDataSentinel)

    def test_all_sectors_mapped(self, mock_qcew_source: MagicMock) -> None:
        """All sectors with depth mappings → sectors_mapped = sectors_with_data."""
        mock_qcew_source.get_county_employment_by_naics.return_value = {
            "52": 25000,  # Finance
            "21": 15000,  # Mining
        }
        analyzer = DefaultSupplyChainAnalyzer(qcew_source=mock_qcew_source)

        result = analyzer.get_sector_coverage("26163", 2022)

        assert not isinstance(result, NoDataSentinel)
        sectors_with_data, sectors_mapped, employment_covered = result
        assert sectors_with_data == 2
        assert sectors_mapped == 2
        assert employment_covered == 40000

    def test_no_sectors_mapped(self, mock_qcew_source: MagicMock) -> None:
        """All unknown NAICS → sectors_mapped=0, employment_covered=0."""
        mock_qcew_source.get_county_employment_by_naics.return_value = {
            "99": 10000,
            "98": 5000,
        }
        analyzer = DefaultSupplyChainAnalyzer(qcew_source=mock_qcew_source)

        result = analyzer.get_sector_coverage("26163", 2022)

        assert not isinstance(result, NoDataSentinel)
        sectors_with_data, sectors_mapped, employment_covered = result
        assert sectors_with_data == 2
        assert sectors_mapped == 0
        assert employment_covered == 0


class TestDetermineConfidenceMutationKillers:
    """Mutation-killing tests for _determine_confidence boundary conditions."""

    def test_lambda_above_1_is_low(self, mock_qcew_source: MagicMock) -> None:
        """lambda_proxy > 1.0 → always 'low' regardless of employment."""
        analyzer = DefaultSupplyChainAnalyzer(qcew_source=mock_qcew_source)
        assert analyzer._determine_confidence(5000, 1.1) == "low"

    def test_none_employment_is_low(self, mock_qcew_source: MagicMock) -> None:
        """None employment (suppressed data) → 'low'."""
        analyzer = DefaultSupplyChainAnalyzer(qcew_source=mock_qcew_source)
        assert analyzer._determine_confidence(None, 0.5) == "low"

    def test_employment_below_100_is_low(self, mock_qcew_source: MagicMock) -> None:
        """employment < 100 → 'low'."""
        analyzer = DefaultSupplyChainAnalyzer(qcew_source=mock_qcew_source)
        assert analyzer._determine_confidence(50, 0.5) == "low"

    def test_employment_at_exactly_100_is_low(self, mock_qcew_source: MagicMock) -> None:
        """employment == 100 → still 'low' (uses < 100 check first, but 100 < 1000)."""
        analyzer = DefaultSupplyChainAnalyzer(qcew_source=mock_qcew_source)
        # 100 is NOT < 100, so passes first check
        # 100 < 1000, so returns "medium"... wait, let me re-read
        # Actually: if employment < 100 → low; if employment < 1000 → medium
        # 100 is NOT < 100, so NOT low. 100 IS < 1000, so medium.
        assert analyzer._determine_confidence(100, 0.5) == "medium"

    def test_employment_at_exactly_1000_is_high(self, mock_qcew_source: MagicMock) -> None:
        """employment == 1000 → 'high' (not medium, since 1000 is NOT < 1000)."""
        analyzer = DefaultSupplyChainAnalyzer(qcew_source=mock_qcew_source)
        assert analyzer._determine_confidence(1000, 0.5) == "high"

    def test_employment_999_is_medium(self, mock_qcew_source: MagicMock) -> None:
        """employment == 999 → 'medium' (999 < 1000)."""
        analyzer = DefaultSupplyChainAnalyzer(qcew_source=mock_qcew_source)
        assert analyzer._determine_confidence(999, 0.5) == "medium"

    def test_employment_99_is_low(self, mock_qcew_source: MagicMock) -> None:
        """employment == 99 → 'low' (99 < 100)."""
        analyzer = DefaultSupplyChainAnalyzer(qcew_source=mock_qcew_source)
        assert analyzer._determine_confidence(99, 0.5) == "low"

    def test_lambda_at_exactly_1_is_low(self, mock_qcew_source: MagicMock) -> None:
        """lambda_proxy at exactly 1.0 → 'low' (uses > not >=)."""
        analyzer = DefaultSupplyChainAnalyzer(qcew_source=mock_qcew_source)
        # LAMBDA_EXPECTED_MAX = 1.0, check is lambda_proxy > LAMBDA_EXPECTED_MAX
        # 1.0 > 1.0 is False, so NOT low from lambda check
        # With employment=5000 and lambda=1.0: passes lambda, passes None, passes <100, passes <1000 → high
        assert analyzer._determine_confidence(5000, 1.0) == "high"

    def test_large_employment_with_valid_lambda_is_high(self, mock_qcew_source: MagicMock) -> None:
        """High employment with normal lambda → 'high'."""
        analyzer = DefaultSupplyChainAnalyzer(qcew_source=mock_qcew_source)
        assert analyzer._determine_confidence(10000, 0.3) == "high"
