"""Unit tests for MELTCalculator (User Story 1).

Feature: 013-melt-basket-visibility
Date: 2026-02-01

TDD Red Phase: These tests define the expected behavior for MELT computation.
Tests should FAIL before implementation and PASS after.

CHK030: Tests verify distinct error messages for GDP vs employment data.
"""

from __future__ import annotations

from babylon.domain.economics.melt import DefaultMELTCalculator
from babylon.domain.economics.tensor import NoDataSentinel

from .conftest import MockBEADataSource, MockQCEWDataSource


class TestMELTCalculatorComputation:
    """Tests for τ = GDP / (employment × 2080) computation."""

    def test_melt_computation_2022(
        self,
        mock_bea_source: MockBEADataSource,
        mock_qcew_source: MockQCEWDataSource,
    ) -> None:
        """Test MELT computation with 2022 data.

        Expected: τ = 25,462,700,000,000 / (152,900,000 × 2080) ≈ $80/hour
        """
        calculator = DefaultMELTCalculator(mock_bea_source, mock_qcew_source)
        tau = calculator.get_melt(2022)

        # Should return a float, not NoDataSentinel
        assert isinstance(tau, float)
        # τ should be in expected range ($55-75 typical, up to ~$80 for 2022)
        assert 60.0 <= tau <= 100.0

    def test_melt_computation_formula_verification(self) -> None:
        """Verify MELT formula: τ = GDP / (employment × 2080).

        Use known values to verify computation.
        """
        # Known values for easy verification
        gdp = 100_000_000_000.0  # $100 billion
        employment = 1_000_000  # 1 million workers

        bea_source = MockBEADataSource({2022: gdp})
        qcew_source = MockQCEWDataSource({2022: employment})

        calculator = DefaultMELTCalculator(bea_source, qcew_source)
        tau = calculator.get_melt(2022)

        # τ = 100,000,000,000 / (1,000,000 × 2080)
        # τ = 100,000,000,000 / 2,080,000,000
        # τ ≈ 48.08
        expected_tau = gdp / (employment * 2080)
        assert isinstance(tau, float)
        assert abs(tau - expected_tau) < 0.01


class TestMELTCalculatorNoData:
    """Tests for NoDataSentinel returns with distinct error messages (CHK030)."""

    def test_missing_gdp_returns_sentinel_with_gdp_reason(self) -> None:
        """Test that missing GDP returns NoDataSentinel with GDP-specific message.

        CHK030: Error message should specifically mention "GDP data unavailable".
        """
        # BEA source returns None for 2022
        bea_source = MockBEADataSource({})
        qcew_source = MockQCEWDataSource({2022: 150_000_000})

        calculator = DefaultMELTCalculator(bea_source, qcew_source)
        result = calculator.get_melt(2022)

        # Should return NoDataSentinel
        assert isinstance(result, NoDataSentinel)
        # Reason should specifically mention GDP
        assert "GDP" in result.reason
        assert "2022" in result.reason

    def test_missing_employment_returns_sentinel_with_employment_reason(self) -> None:
        """Test that missing employment returns NoDataSentinel with employment-specific message.

        CHK030: Error message should specifically mention "Employment data unavailable".
        """
        # QCEW source returns None for 2022
        bea_source = MockBEADataSource({2022: 25_000_000_000_000.0})
        qcew_source = MockQCEWDataSource({})

        calculator = DefaultMELTCalculator(bea_source, qcew_source)
        result = calculator.get_melt(2022)

        # Should return NoDataSentinel
        assert isinstance(result, NoDataSentinel)
        # Reason should specifically mention employment
        assert "Employment" in result.reason or "employment" in result.reason
        assert "2022" in result.reason

    def test_gdp_and_employment_error_messages_are_distinct(self) -> None:
        """Test that GDP and employment error messages are distinguishable.

        CHK030: Users must be able to tell which data source is missing.
        """
        # Test missing GDP
        bea_source_empty = MockBEADataSource({})
        qcew_source_full = MockQCEWDataSource({2022: 150_000_000})
        calc_gdp_missing = DefaultMELTCalculator(bea_source_empty, qcew_source_full)
        gdp_result = calc_gdp_missing.get_melt(2022)

        # Test missing employment
        bea_source_full = MockBEADataSource({2022: 25_000_000_000_000.0})
        qcew_source_empty = MockQCEWDataSource({})
        calc_emp_missing = DefaultMELTCalculator(bea_source_full, qcew_source_empty)
        emp_result = calc_emp_missing.get_melt(2022)

        # Both should be NoDataSentinel
        assert isinstance(gdp_result, NoDataSentinel)
        assert isinstance(emp_result, NoDataSentinel)

        # Messages should be different
        assert gdp_result.reason != emp_result.reason


class TestMELTCalculatorYearRange:
    """Tests for year range validation."""

    def test_year_at_lower_boundary(
        self,
        mock_bea_source: MockBEADataSource,
        mock_qcew_source: MockQCEWDataSource,
    ) -> None:
        """Test that year 2010 (lower boundary) is accepted."""
        calculator = DefaultMELTCalculator(mock_bea_source, mock_qcew_source)
        result = calculator.get_melt(2010)

        # Should return a value (might be NoDataSentinel if no data)
        # But should NOT fail due to year range
        if isinstance(result, NoDataSentinel):
            assert "outside data range" not in result.reason

    def test_year_at_upper_boundary(
        self,
        mock_bea_source: MockBEADataSource,
        mock_qcew_source: MockQCEWDataSource,
    ) -> None:
        """Test that year 2024 (upper boundary) is accepted."""
        calculator = DefaultMELTCalculator(mock_bea_source, mock_qcew_source)
        result = calculator.get_melt(2024)

        # Should return a value (might be NoDataSentinel if no data)
        # But should NOT fail due to year range
        if isinstance(result, NoDataSentinel):
            assert "outside data range" not in result.reason

    def test_year_below_range_returns_sentinel(
        self,
        mock_bea_source: MockBEADataSource,
        mock_qcew_source: MockQCEWDataSource,
    ) -> None:
        """Test that year 2005 (below range) returns NoDataSentinel."""
        calculator = DefaultMELTCalculator(mock_bea_source, mock_qcew_source)
        result = calculator.get_melt(2005)

        assert isinstance(result, NoDataSentinel)
        assert "2005" in result.reason
        assert "range" in result.reason.lower()

    def test_year_above_range_returns_sentinel(
        self,
        mock_bea_source: MockBEADataSource,
        mock_qcew_source: MockQCEWDataSource,
    ) -> None:
        """Test that year 2030 (above range) returns NoDataSentinel."""
        calculator = DefaultMELTCalculator(mock_bea_source, mock_qcew_source)
        result = calculator.get_melt(2030)

        assert isinstance(result, NoDataSentinel)
        assert "2030" in result.reason
        assert "range" in result.reason.lower()


class TestMELTCalculatorValidation:
    """Tests for MELT sanity validation."""

    def test_validate_melt_expected_range(
        self,
        mock_bea_source: MockBEADataSource,
        mock_qcew_source: MockQCEWDataSource,
    ) -> None:
        """Test that τ in expected range ($55-75) passes without warning."""
        calculator = DefaultMELTCalculator(mock_bea_source, mock_qcew_source)

        # Test values in expected range
        for tau in [55.0, 60.0, 65.0, 70.0, 75.0]:
            valid, message = calculator.validate_melt(tau)
            assert valid is True
            assert message is None

    def test_validate_melt_warning_range(
        self,
        mock_bea_source: MockBEADataSource,
        mock_qcew_source: MockQCEWDataSource,
    ) -> None:
        """Test that τ in warning range ($40-55 or $75-100) returns warning."""
        calculator = DefaultMELTCalculator(mock_bea_source, mock_qcew_source)

        # Test values in warning range (below expected)
        valid, message = calculator.validate_melt(45.0)
        assert valid is True
        assert message is not None
        assert "WARNING" in message or "warning" in message.lower()

        # Test values in warning range (above expected)
        valid, message = calculator.validate_melt(90.0)
        assert valid is True
        assert message is not None
        assert "WARNING" in message or "warning" in message.lower()

    def test_validate_melt_fail_range(
        self,
        mock_bea_source: MockBEADataSource,
        mock_qcew_source: MockQCEWDataSource,
    ) -> None:
        """Test that τ outside valid range (<$20 or >$200) fails."""
        calculator = DefaultMELTCalculator(mock_bea_source, mock_qcew_source)

        # Test values below valid range
        valid, message = calculator.validate_melt(15.0)
        assert valid is False
        assert message is not None

        # Test values above valid range
        valid, message = calculator.validate_melt(250.0)
        assert valid is False
        assert message is not None


class TestMELTCalculatorDataRange:
    """Tests for data_range property."""

    def test_data_range_returns_tuple(
        self,
        mock_bea_source: MockBEADataSource,
        mock_qcew_source: MockQCEWDataSource,
    ) -> None:
        """Test that data_range returns (min_year, max_year) tuple."""
        calculator = DefaultMELTCalculator(mock_bea_source, mock_qcew_source)

        min_year, max_year = calculator.data_range

        assert isinstance(min_year, int)
        assert isinstance(max_year, int)
        assert min_year == 2010
        assert max_year == 2024


class TestMELTCalculatorEdgeCases:
    """Tests for edge cases."""

    def test_zero_employment_returns_sentinel(self) -> None:
        """Test that zero employment returns NoDataSentinel (avoid division by zero)."""
        bea_source = MockBEADataSource({2022: 25_000_000_000_000.0})
        qcew_source = MockQCEWDataSource({2022: 0})

        calculator = DefaultMELTCalculator(bea_source, qcew_source)
        result = calculator.get_melt(2022)

        assert isinstance(result, NoDataSentinel)
        assert "zero" in result.reason.lower() or "employment" in result.reason.lower()
