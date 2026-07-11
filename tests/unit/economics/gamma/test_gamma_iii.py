"""Unit tests for GammaIIICalculator (User Story 1).

Feature: 015-gamma-visibility-tensor
Date: 2026-02-05

TDD Red Phase: These tests define the expected behavior for gamma_III computation.
Tests should FAIL before implementation and PASS after.
"""

from __future__ import annotations

import math

from babylon.domain.economics.gamma.gamma_iii import (
    MAX_YEAR,
    MIN_YEAR,
    DefaultGammaIIICalculator,
)
from babylon.domain.economics.gamma.types import GammaIII
from babylon.domain.economics.tensor import NoDataSentinel

from .conftest import MockPaidCareHoursSource, MockUnpaidCareHoursSource


class TestGammaIIIComputation:
    """Tests for gamma_III = L_paid / (L_paid + L_unpaid) computation."""

    def test_compute_2022_typical(
        self,
        mock_unpaid_source: MockUnpaidCareHoursSource,
        mock_paid_source: MockPaidCareHoursSource,
    ) -> None:
        """Test gamma_III computation with 2022 data.

        Expected: gamma_III = 16.5 / (16.5 + 33.0) = 0.333
        """
        calculator = DefaultGammaIIICalculator(mock_unpaid_source, mock_paid_source)
        result = calculator.compute(2022)

        assert isinstance(result, GammaIII)
        assert result.year == 2022
        # gamma_III should be in expected range [0.20, 0.40]
        assert 0.20 <= result.gamma_iii <= 0.40
        # Specific value: 16.5 / (16.5 + 33.0) = 0.333...
        assert abs(result.gamma_iii - 1.0 / 3.0) < 0.01

    def test_compute_formula_verification(self) -> None:
        """Verify gamma_III formula with known values.

        gamma_III = paid / (paid + unpaid) = 10 / (10 + 30) = 0.25
        """
        unpaid_source = MockUnpaidCareHoursSource({2022: 30.0})
        paid_source = MockPaidCareHoursSource({2022: 10.0})

        calculator = DefaultGammaIIICalculator(unpaid_source, paid_source)
        result = calculator.compute(2022)

        assert isinstance(result, GammaIII)
        expected = 10.0 / (10.0 + 30.0)
        assert abs(result.gamma_iii - expected) < 1e-10
        assert result.paid_care_hours == 10.0
        assert result.unpaid_care_hours == 30.0

    def test_compute_in_expected_range(
        self,
        mock_unpaid_source: MockUnpaidCareHoursSource,
        mock_paid_source: MockPaidCareHoursSource,
    ) -> None:
        """SC-001: Verify gamma_III is in [0.20, 0.40] range."""
        calculator = DefaultGammaIIICalculator(mock_unpaid_source, mock_paid_source)
        result = calculator.compute(2022)

        assert isinstance(result, GammaIII)
        assert 0.20 <= result.gamma_iii <= 0.40


class TestGetPaidCareHours:
    """Tests for paid care hours retrieval from QCEW data."""

    def test_returns_hours_when_available(
        self,
        mock_unpaid_source: MockUnpaidCareHoursSource,
        mock_paid_source: MockPaidCareHoursSource,
    ) -> None:
        """Test that paid care hours are returned when data exists."""
        calculator = DefaultGammaIIICalculator(mock_unpaid_source, mock_paid_source)
        result = calculator.get_paid_care_hours(2022)

        assert isinstance(result, float)
        assert result == 16.5

    def test_returns_sentinel_when_unavailable(
        self,
        mock_unpaid_source: MockUnpaidCareHoursSource,
    ) -> None:
        """Test NoDataSentinel when QCEW data is missing."""
        paid_source = MockPaidCareHoursSource({})
        calculator = DefaultGammaIIICalculator(mock_unpaid_source, paid_source)
        result = calculator.get_paid_care_hours(2022)

        assert isinstance(result, NoDataSentinel)
        assert "QCEW" in result.reason
        assert "2022" in result.reason


class TestGetUnpaidCareHours:
    """Tests for unpaid care hours retrieval from ATUS data."""

    def test_returns_hours_when_available(
        self,
        mock_unpaid_source: MockUnpaidCareHoursSource,
        mock_paid_source: MockPaidCareHoursSource,
    ) -> None:
        """Test that unpaid care hours are returned when data exists."""
        calculator = DefaultGammaIIICalculator(mock_unpaid_source, mock_paid_source)
        result = calculator.get_unpaid_care_hours(2022)

        assert isinstance(result, float)
        assert result == 33.0

    def test_returns_sentinel_when_unavailable(
        self,
        mock_paid_source: MockPaidCareHoursSource,
    ) -> None:
        """Test NoDataSentinel when ATUS data is missing."""
        unpaid_source = MockUnpaidCareHoursSource({})
        calculator = DefaultGammaIIICalculator(unpaid_source, mock_paid_source)
        result = calculator.get_unpaid_care_hours(2022)

        assert isinstance(result, NoDataSentinel)
        assert "ATUS" in result.reason
        assert "2022" in result.reason


class TestGammaIIINoData:
    """Tests for NoDataSentinel returns with distinct error messages."""

    def test_missing_atus_returns_sentinel_with_atus_reason(self) -> None:
        """Test that missing ATUS data returns NoDataSentinel with ATUS-specific message."""
        unpaid_source = MockUnpaidCareHoursSource({})
        paid_source = MockPaidCareHoursSource({2022: 16.5})

        calculator = DefaultGammaIIICalculator(unpaid_source, paid_source)
        result = calculator.compute(2022)

        assert isinstance(result, NoDataSentinel)
        assert "ATUS" in result.reason

    def test_missing_qcew_returns_sentinel_with_qcew_reason(self) -> None:
        """Test that missing QCEW data returns NoDataSentinel with QCEW-specific message."""
        unpaid_source = MockUnpaidCareHoursSource({2022: 33.0})
        paid_source = MockPaidCareHoursSource({})

        calculator = DefaultGammaIIICalculator(unpaid_source, paid_source)
        result = calculator.compute(2022)

        assert isinstance(result, NoDataSentinel)
        assert "QCEW" in result.reason

    def test_atus_and_qcew_error_messages_are_distinct(self) -> None:
        """Test that ATUS and QCEW error messages are distinguishable."""
        # Test missing ATUS
        calc_atus_missing = DefaultGammaIIICalculator(
            MockUnpaidCareHoursSource({}),
            MockPaidCareHoursSource({2022: 16.5}),
        )
        atus_result = calc_atus_missing.compute(2022)

        # Test missing QCEW
        calc_qcew_missing = DefaultGammaIIICalculator(
            MockUnpaidCareHoursSource({2022: 33.0}),
            MockPaidCareHoursSource({}),
        )
        qcew_result = calc_qcew_missing.compute(2022)

        assert isinstance(atus_result, NoDataSentinel)
        assert isinstance(qcew_result, NoDataSentinel)
        assert atus_result.reason != qcew_result.reason

    def test_year_outside_range_returns_sentinel(self) -> None:
        """Test that year outside ATUS range returns NoDataSentinel."""
        calculator = DefaultGammaIIICalculator(
            MockUnpaidCareHoursSource(),
            MockPaidCareHoursSource(),
        )
        result = calculator.compute(2000)

        assert isinstance(result, NoDataSentinel)
        assert "2000" in result.reason
        assert "range" in result.reason.lower()


class TestFortunatExploitation:
    """Tests for Fortunati exploitation rate computation."""

    def test_fortunati_exploitation_typical(self) -> None:
        """SC-008: Verify Fortunati exploitation rate.

        Given gamma_III = 1/3, Fortunati = (1 - 1/3) / (1/3) = 2.0
        """
        unpaid_source = MockUnpaidCareHoursSource({2022: 33.0})
        paid_source = MockPaidCareHoursSource({2022: 16.5})

        calculator = DefaultGammaIIICalculator(unpaid_source, paid_source)
        result = calculator.compute(2022)

        assert isinstance(result, GammaIII)
        # (1 - gamma) / gamma ≈ 2.0
        assert abs(result.fortunati_exploitation - 2.0) < 0.1

    def test_fortunati_exploitation_high_visibility(self) -> None:
        """Test Fortunati rate when gamma_III is high (most care is paid)."""
        unpaid_source = MockUnpaidCareHoursSource({2022: 10.0})
        paid_source = MockPaidCareHoursSource({2022: 40.0})

        calculator = DefaultGammaIIICalculator(unpaid_source, paid_source)
        result = calculator.compute(2022)

        assert isinstance(result, GammaIII)
        # gamma = 40/50 = 0.8, Fortunati = 0.2/0.8 = 0.25
        assert result.fortunati_exploitation < 1.0

    def test_fortunati_exploitation_low_visibility(self) -> None:
        """Test Fortunati rate when gamma_III is low (most care is unpaid)."""
        unpaid_source = MockUnpaidCareHoursSource({2022: 45.0})
        paid_source = MockPaidCareHoursSource({2022: 5.0})

        calculator = DefaultGammaIIICalculator(unpaid_source, paid_source)
        result = calculator.compute(2022)

        assert isinstance(result, GammaIII)
        # gamma = 5/50 = 0.1, Fortunati = 0.9/0.1 = 9.0
        assert result.fortunati_exploitation > 5.0


class TestGammaIIIMutationKillers:
    """Targeted tests to kill mutation survivors in DefaultGammaIIICalculator.compute.

    Targets boundary conditions, arithmetic edge cases, and sentinel propagation
    that survive mutmut operator swaps (< vs <=, + vs -, sentinel short-circuits).
    """

    def test_year_at_exact_min_boundary(self) -> None:
        """year=MIN_YEAR should return valid GammaIII, not sentinel."""
        unpaid = MockUnpaidCareHoursSource({MIN_YEAR: 30.0})
        paid = MockPaidCareHoursSource({MIN_YEAR: 10.0})
        calculator = DefaultGammaIIICalculator(unpaid, paid)

        result = calculator.compute(MIN_YEAR)

        assert isinstance(result, GammaIII)
        assert result.year == MIN_YEAR

    def test_year_one_below_min_returns_sentinel(self) -> None:
        """year=MIN_YEAR-1 should return sentinel (boundary off-by-one)."""
        unpaid = MockUnpaidCareHoursSource({MIN_YEAR - 1: 30.0})
        paid = MockPaidCareHoursSource({MIN_YEAR - 1: 10.0})
        calculator = DefaultGammaIIICalculator(unpaid, paid)

        result = calculator.compute(MIN_YEAR - 1)

        assert isinstance(result, NoDataSentinel)
        assert str(MIN_YEAR - 1) in result.reason

    def test_year_at_exact_max_boundary(self) -> None:
        """year=MAX_YEAR should return valid GammaIII, not sentinel."""
        unpaid = MockUnpaidCareHoursSource({MAX_YEAR: 30.0})
        paid = MockPaidCareHoursSource({MAX_YEAR: 10.0})
        calculator = DefaultGammaIIICalculator(unpaid, paid)

        result = calculator.compute(MAX_YEAR)

        assert isinstance(result, GammaIII)
        assert result.year == MAX_YEAR

    def test_year_one_above_max_returns_sentinel(self) -> None:
        """year=MAX_YEAR+1 should return sentinel (boundary off-by-one)."""
        unpaid = MockUnpaidCareHoursSource({MAX_YEAR + 1: 30.0})
        paid = MockPaidCareHoursSource({MAX_YEAR + 1: 10.0})
        calculator = DefaultGammaIIICalculator(unpaid, paid)

        result = calculator.compute(MAX_YEAR + 1)

        assert isinstance(result, NoDataSentinel)
        assert str(MAX_YEAR + 1) in result.reason

    def test_zero_total_care_hours_returns_sentinel(self) -> None:
        """paid=0, unpaid=0 should return sentinel (division by zero guard)."""
        unpaid = MockUnpaidCareHoursSource({2022: 0.0})
        paid = MockPaidCareHoursSource({2022: 0.0})
        calculator = DefaultGammaIIICalculator(unpaid, paid)

        result = calculator.compute(2022)

        assert isinstance(result, NoDataSentinel)
        assert "zero" in result.reason.lower()

    def test_gamma_zero_when_only_unpaid(self) -> None:
        """paid=0, unpaid=100 → gamma=0.0, fortunati=inf."""
        unpaid = MockUnpaidCareHoursSource({2022: 100.0})
        paid = MockPaidCareHoursSource({2022: 0.0})
        calculator = DefaultGammaIIICalculator(unpaid, paid)

        result = calculator.compute(2022)

        assert isinstance(result, GammaIII)
        assert result.gamma_iii == 0.0
        assert math.isinf(result.fortunati_exploitation)

    def test_gamma_one_when_only_paid(self) -> None:
        """paid=100, unpaid=0 → gamma=1.0, fortunati=0.0."""
        unpaid = MockUnpaidCareHoursSource({2022: 0.0})
        paid = MockPaidCareHoursSource({2022: 100.0})
        calculator = DefaultGammaIIICalculator(unpaid, paid)

        result = calculator.compute(2022)

        assert isinstance(result, GammaIII)
        assert result.gamma_iii == 1.0
        assert result.fortunati_exploitation == 0.0

    def test_fortunati_formula_exact_value(self) -> None:
        """gamma=0.4 → fortunati=(1-0.4)/0.4=1.5 exactly."""
        # paid/(paid+unpaid) = 0.4 → paid=40, unpaid=60
        unpaid = MockUnpaidCareHoursSource({2022: 60.0})
        paid = MockPaidCareHoursSource({2022: 40.0})
        calculator = DefaultGammaIIICalculator(unpaid, paid)

        result = calculator.compute(2022)

        assert isinstance(result, GammaIII)
        assert abs(result.gamma_iii - 0.4) < 1e-10
        assert abs(result.fortunati_exploitation - 1.5) < 1e-10

    def test_sentinel_from_unpaid_propagates(self) -> None:
        """When unpaid source returns None, compute returns sentinel early."""
        unpaid = MockUnpaidCareHoursSource({})  # No data → None → sentinel
        paid = MockPaidCareHoursSource({2022: 16.5})
        calculator = DefaultGammaIIICalculator(unpaid, paid)

        result = calculator.compute(2022)

        assert isinstance(result, NoDataSentinel)
        assert "ATUS" in result.reason
        assert result.year == 2022

    def test_sentinel_from_paid_propagates(self) -> None:
        """When paid source returns None, compute returns sentinel early."""
        unpaid = MockUnpaidCareHoursSource({2022: 33.0})
        paid = MockPaidCareHoursSource({})  # No data → None → sentinel
        calculator = DefaultGammaIIICalculator(unpaid, paid)

        result = calculator.compute(2022)

        assert isinstance(result, NoDataSentinel)
        assert "QCEW" in result.reason
        assert result.year == 2022
