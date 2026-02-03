"""Unit tests for commuter-adjusted throughput calculations.

Feature: 014-throughput-position (T036)
TDD Phase: Green

Tests verify:
- compute_residence_throughput() calculates τ_residence correctly
- compute_commuter_adjusted_metrics() combines workplace and residence metrics
- CommuterAdjustedMetrics type validates correctly
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from babylon.economics.tensor import NoDataSentinel
from babylon.economics.throughput.calculator import (
    HOURS_PER_YEAR,
    DefaultThroughputCalculator,
)
from babylon.economics.throughput.types import CommuterAdjustedMetrics

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_gdp_source() -> MagicMock:
    """Create a mock BEA GDP source."""
    source = MagicMock()
    source.get_county_gdp.return_value = None
    return source


@pytest.fixture
def mock_qcew_source() -> MagicMock:
    """Create a mock QCEW source."""
    source = MagicMock()
    source.get_county_total_employment.return_value = None
    source.get_county_employment_by_naics.return_value = {}
    return source


@pytest.fixture
def mock_supply_chain() -> MagicMock:
    """Create a mock SupplyChainAnalyzer."""
    analyzer = MagicMock()
    analyzer.compute_depth.return_value = 3.0
    analyzer.get_sector_coverage.return_value = (10, 8, 100000)
    return analyzer


@pytest.fixture
def mock_melt_calculator() -> MagicMock:
    """Create a mock MELTCalculator."""
    calc = MagicMock()
    calc.get_melt.return_value = 65.0  # National MELT ~$65/hour
    return calc


@pytest.fixture
def mock_commuter_source() -> MagicMock:
    """Create a mock LODESCommuterFlowSource."""
    source = MagicMock()
    source.get_inbound_commuters.return_value = None
    source.get_outbound_commuters.return_value = None
    source.get_internal_workers.return_value = None
    source.get_net_commuter_balance.return_value = None
    source.get_residence_employment.return_value = None
    source.get_commuter_flows.return_value = None
    return source


@pytest.fixture
def calculator_with_commuter(
    mock_gdp_source: MagicMock,
    mock_qcew_source: MagicMock,
    mock_supply_chain: MagicMock,
    mock_melt_calculator: MagicMock,
    mock_commuter_source: MagicMock,
) -> DefaultThroughputCalculator:
    """Create a calculator with all sources including commuter."""
    return DefaultThroughputCalculator(
        gdp_source=mock_gdp_source,
        qcew_source=mock_qcew_source,
        supply_chain_analyzer=mock_supply_chain,
        melt_calculator=mock_melt_calculator,
        commuter_source=mock_commuter_source,
    )


@pytest.fixture
def calculator_no_commuter(
    mock_gdp_source: MagicMock,
    mock_qcew_source: MagicMock,
    mock_supply_chain: MagicMock,
    mock_melt_calculator: MagicMock,
) -> DefaultThroughputCalculator:
    """Create a calculator without commuter source."""
    return DefaultThroughputCalculator(
        gdp_source=mock_gdp_source,
        qcew_source=mock_qcew_source,
        supply_chain_analyzer=mock_supply_chain,
        melt_calculator=mock_melt_calculator,
        commuter_source=None,
    )


# =============================================================================
# TEST: CommuterAdjustedMetrics TYPE
# =============================================================================


class TestCommuterAdjustedMetricsType:
    """Tests for CommuterAdjustedMetrics pydantic model."""

    def test_basic_construction(self) -> None:
        """Can construct with required fields."""
        metrics = CommuterAdjustedMetrics(
            fips="26163",
            year=2022,
            tau_through_workplace=58.5,
        )
        assert metrics.fips == "26163"
        assert metrics.year == 2022
        assert metrics.tau_through_workplace == 58.5

    def test_all_fields(self) -> None:
        """Can construct with all optional fields."""
        metrics = CommuterAdjustedMetrics(
            fips="26125",
            year=2022,
            tau_through_workplace=45.0,
            pi_workplace=0.70,
            tau_through_residence=62.0,
            pi_residence=0.95,
            net_commuter_balance=-150000,
            commuter_ratio=1.35,
            is_job_importer=False,
            has_commuter_data=True,
        )
        assert metrics.pi_workplace == 0.70
        assert metrics.tau_through_residence == 62.0
        assert metrics.pi_residence == 0.95
        assert metrics.net_commuter_balance == -150000
        assert metrics.commuter_ratio == 1.35
        assert metrics.is_job_importer is False
        assert metrics.has_commuter_data is True

    def test_fips_validation(self) -> None:
        """FIPS must be exactly 5 digits."""
        with pytest.raises(ValueError):
            CommuterAdjustedMetrics(
                fips="1234",  # Too short
                year=2022,
                tau_through_workplace=50.0,
            )

    def test_frozen(self) -> None:
        """Model is immutable (frozen)."""
        metrics = CommuterAdjustedMetrics(
            fips="26163",
            year=2022,
            tau_through_workplace=58.5,
        )
        with pytest.raises(TypeError):  # Pydantic frozen model raises TypeError
            metrics.tau_through_workplace = 60.0  # type: ignore[misc]


# =============================================================================
# TEST: compute_residence_throughput
# =============================================================================


class TestResidenceThroughput:
    """Tests for compute_residence_throughput method."""

    def test_basic_computation(
        self,
        calculator_with_commuter: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_commuter_source: MagicMock,
    ) -> None:
        """τ_residence = GDP / (residence_employment × 2080)."""
        # Oakland County: GDP = $80B, Residence Employment = 600,000
        mock_gdp_source.get_county_gdp.return_value = 80_000_000_000.0
        mock_commuter_source.get_residence_employment.return_value = 600_000

        result = calculator_with_commuter.compute_residence_throughput("26125", 2022)

        expected = 80_000_000_000.0 / (600_000 * HOURS_PER_YEAR)
        assert isinstance(result, float)
        assert result == pytest.approx(expected, rel=1e-6)
        # ~$64.10/hour

    def test_no_commuter_source_returns_sentinel(
        self,
        calculator_no_commuter: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
    ) -> None:
        """Returns NoDataSentinel when commuter source not provided."""
        mock_gdp_source.get_county_gdp.return_value = 80_000_000_000.0

        result = calculator_no_commuter.compute_residence_throughput("26125", 2022)

        assert isinstance(result, NoDataSentinel)
        assert "Commuter source unavailable" in result.reason

    def test_no_gdp_returns_sentinel(
        self,
        calculator_with_commuter: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_commuter_source: MagicMock,
    ) -> None:
        """Returns NoDataSentinel when GDP unavailable."""
        mock_gdp_source.get_county_gdp.return_value = None
        mock_commuter_source.get_residence_employment.return_value = 600_000

        result = calculator_with_commuter.compute_residence_throughput("99999", 2022)

        assert isinstance(result, NoDataSentinel)
        assert "GDP unavailable" in result.reason

    def test_no_residence_employment_returns_sentinel(
        self,
        calculator_with_commuter: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_commuter_source: MagicMock,
    ) -> None:
        """Returns NoDataSentinel when residence employment unavailable."""
        mock_gdp_source.get_county_gdp.return_value = 80_000_000_000.0
        mock_commuter_source.get_residence_employment.return_value = None

        result = calculator_with_commuter.compute_residence_throughput("26125", 2022)

        assert isinstance(result, NoDataSentinel)
        assert "residence employment unavailable" in result.reason

    def test_insufficient_employment_returns_sentinel(
        self,
        calculator_with_commuter: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_commuter_source: MagicMock,
    ) -> None:
        """Returns NoDataSentinel when employment below threshold."""
        mock_gdp_source.get_county_gdp.return_value = 500_000_000.0
        mock_commuter_source.get_residence_employment.return_value = 500  # Below 1000

        result = calculator_with_commuter.compute_residence_throughput("99999", 2022)

        assert isinstance(result, NoDataSentinel)
        assert "INSUFFICIENT_DATA" in result.reason


# =============================================================================
# TEST: compute_commuter_adjusted_metrics
# =============================================================================


class TestCommuterAdjustedMetrics:
    """Tests for compute_commuter_adjusted_metrics method."""

    def test_full_computation(
        self,
        calculator_with_commuter: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_commuter_source: MagicMock,
        mock_melt_calculator: MagicMock,
    ) -> None:
        """Computes all metrics when data is available."""
        # Oakland County
        mock_gdp_source.get_county_gdp.return_value = 80_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 500_000  # Workplace
        mock_commuter_source.get_residence_employment.return_value = 650_000  # Residence
        mock_commuter_source.get_net_commuter_balance.return_value = -150_000  # Exporter
        mock_melt_calculator.get_melt.return_value = 65.0

        result = calculator_with_commuter.compute_commuter_adjusted_metrics("26125", 2022)

        assert isinstance(result, CommuterAdjustedMetrics)
        assert result.fips == "26125"
        assert result.year == 2022
        assert result.has_commuter_data is True
        assert result.is_job_importer is False  # Negative balance
        assert result.net_commuter_balance == -150_000

        # τ_workplace = 80B / (500k × 2080) = ~$76.92
        expected_tau_workplace = 80_000_000_000.0 / (500_000 * HOURS_PER_YEAR)
        assert result.tau_through_workplace == pytest.approx(expected_tau_workplace, rel=1e-6)

        # τ_residence = 80B / (650k × 2080) = ~$59.17
        expected_tau_residence = 80_000_000_000.0 / (650_000 * HOURS_PER_YEAR)
        assert result.tau_through_residence is not None
        assert result.tau_through_residence == pytest.approx(expected_tau_residence, rel=1e-6)

        # π = τ / τ_national
        assert result.pi_workplace is not None
        assert result.pi_residence is not None
        assert result.pi_workplace == pytest.approx(expected_tau_workplace / 65.0, rel=1e-6)
        assert result.pi_residence == pytest.approx(expected_tau_residence / 65.0, rel=1e-6)

        # Commuter ratio = residence / workplace = 650k / 500k = 1.3
        assert result.commuter_ratio is not None
        assert result.commuter_ratio == pytest.approx(1.3, rel=1e-6)

    def test_without_commuter_data(
        self,
        calculator_with_commuter: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_commuter_source: MagicMock,
    ) -> None:
        """Returns metrics with has_commuter_data=False when LODES unavailable."""
        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 400_000
        mock_commuter_source.get_net_commuter_balance.return_value = None  # No data

        result = calculator_with_commuter.compute_commuter_adjusted_metrics("99999", 2022)

        assert isinstance(result, CommuterAdjustedMetrics)
        assert result.has_commuter_data is False
        assert result.tau_through_residence is None
        assert result.pi_residence is None
        assert result.net_commuter_balance == 0
        assert result.is_job_importer is False

    def test_without_gdp_returns_sentinel(
        self,
        calculator_with_commuter: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
    ) -> None:
        """Returns NoDataSentinel when GDP unavailable (can't compute workplace τ)."""
        mock_gdp_source.get_county_gdp.return_value = None
        mock_qcew_source.get_county_total_employment.return_value = 400_000

        result = calculator_with_commuter.compute_commuter_adjusted_metrics("99999", 2022)

        assert isinstance(result, NoDataSentinel)
        assert "GDP unavailable" in result.reason

    def test_without_commuter_source(
        self,
        calculator_no_commuter: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
    ) -> None:
        """Returns metrics without commuter data when source not provided."""
        mock_gdp_source.get_county_gdp.return_value = 50_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 400_000

        result = calculator_no_commuter.compute_commuter_adjusted_metrics("26163", 2022)

        assert isinstance(result, CommuterAdjustedMetrics)
        assert result.has_commuter_data is False
        assert result.tau_through_workplace > 0  # Workplace metrics work
        assert result.tau_through_residence is None


# =============================================================================
# DETROIT METRO VALIDATION SCENARIO
# =============================================================================


class TestDetroitMetroValidation:
    """Validate commuter-adjusted metrics for Detroit metro scenario.

    Expected patterns:
    - Oakland County (26125): Bedroom community
      - is_job_importer=False (negative balance)
      - pi_residence should be closer to Wayne's pi_workplace
      - commuter_ratio > 1.0 (more residents than local jobs)

    - Wayne County (26163): Job center
      - is_job_importer=True (positive balance)
      - commuter_ratio < 1.0 (more local jobs than residents)
    """

    def test_oakland_county_bedroom_community(
        self,
        calculator_with_commuter: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_commuter_source: MagicMock,
        mock_melt_calculator: MagicMock,
    ) -> None:
        """Oakland County should show bedroom community characteristics."""
        # Realistic data for Oakland County
        mock_gdp_source.get_county_gdp.return_value = 80_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 500_000
        mock_commuter_source.get_residence_employment.return_value = 650_000
        mock_commuter_source.get_net_commuter_balance.return_value = -150_000
        mock_melt_calculator.get_melt.return_value = 65.0

        result = calculator_with_commuter.compute_commuter_adjusted_metrics("26125", 2022)

        assert isinstance(result, CommuterAdjustedMetrics)
        assert result.is_job_importer is False  # Bedroom community exports workers
        assert result.net_commuter_balance < 0
        assert result.commuter_ratio is not None
        assert result.commuter_ratio > 1.0  # More residents than local jobs

    def test_wayne_county_job_center(
        self,
        calculator_with_commuter: DefaultThroughputCalculator,
        mock_gdp_source: MagicMock,
        mock_qcew_source: MagicMock,
        mock_commuter_source: MagicMock,
        mock_melt_calculator: MagicMock,
    ) -> None:
        """Wayne County should show job center characteristics."""
        # Realistic data for Wayne County (Detroit)
        mock_gdp_source.get_county_gdp.return_value = 115_000_000_000.0
        mock_qcew_source.get_county_total_employment.return_value = 750_000
        mock_commuter_source.get_residence_employment.return_value = 680_000
        mock_commuter_source.get_net_commuter_balance.return_value = 70_000
        mock_melt_calculator.get_melt.return_value = 65.0

        result = calculator_with_commuter.compute_commuter_adjusted_metrics("26163", 2022)

        assert isinstance(result, CommuterAdjustedMetrics)
        assert result.is_job_importer is True  # Job center imports workers
        assert result.net_commuter_balance > 0
        assert result.commuter_ratio is not None
        assert result.commuter_ratio < 1.0  # More local jobs than residents
