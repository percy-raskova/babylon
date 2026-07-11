"""Tests for Capital Volume II circulation costs and labor classification.

Feature: 023-capital-volume-ii
User Story: US6 - Circulation Costs (FR-018, FR-019, FR-020)
Tasks: T059-T064

Tests cover:
    - PureCirculationCosts total and burden calculations
    - TransportationValue value-adding computation
    - classify_labor productive/unproductive classification
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.circulation.costs import (
    LaborClassification,
    classify_labor,
)
from babylon.domain.economics.circulation.types import (
    PureCirculationCosts,
    TransportationValue,
)
from babylon.models.types import Currency

# =============================================================================
# Test Constants
# =============================================================================

WAYNE_COUNTY_FIPS = "26163"
TEST_YEAR = 2022


# =============================================================================
# T059: PureCirculationCosts - Total and Burden
# =============================================================================


class TestPureCirculationCosts:
    """Tests for PureCirculationCosts model calculations."""

    def test_total_equals_sum_of_six_fields(self) -> None:
        """Total pure circulation costs = sum of all 6 components.

        Components: 10M + 5M + 3M + 2M + 4M + 1M = 25M
        """
        costs = PureCirculationCosts(
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
            sales_labor=Currency(10_000_000.0),
            accounting_labor=Currency(5_000_000.0),
            marketing_labor=Currency(3_000_000.0),
            sales_facilities=Currency(2_000_000.0),
            advertising_materials=Currency(4_000_000.0),
            transaction_costs=Currency(1_000_000.0),
        )
        assert costs.total_pure_circulation == pytest.approx(25_000_000.0, rel=1e-5)

    def test_circulation_burden_ratio(self) -> None:
        """Circulation burden = total costs / revenue = 25M / 250M = 0.1."""
        costs = PureCirculationCosts(
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
            sales_labor=Currency(10_000_000.0),
            accounting_labor=Currency(5_000_000.0),
            marketing_labor=Currency(3_000_000.0),
            sales_facilities=Currency(2_000_000.0),
            advertising_materials=Currency(4_000_000.0),
            transaction_costs=Currency(1_000_000.0),
        )
        burden = costs.circulation_burden(Currency(250_000_000.0))
        assert burden == pytest.approx(0.1, rel=1e-5)

    def test_circulation_burden_zero_revenue(self) -> None:
        """Circulation burden with zero revenue returns 0.0."""
        costs = PureCirculationCosts(
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
            sales_labor=Currency(10_000_000.0),
            accounting_labor=Currency(5_000_000.0),
            marketing_labor=Currency(3_000_000.0),
            sales_facilities=Currency(2_000_000.0),
            advertising_materials=Currency(4_000_000.0),
            transaction_costs=Currency(1_000_000.0),
        )
        burden = costs.circulation_burden(Currency(0.0))
        assert burden == 0.0


# =============================================================================
# T060: TransportationValue - Value-Adding Industry
# =============================================================================


class TestTransportationValue:
    """Tests for TransportationValue model calculations."""

    def test_value_added_equals_c_plus_v_plus_s(self) -> None:
        """Value added by transport = c + v + s."""
        tv = TransportationValue(
            origin_value=Currency(10_000.0),
            transport_c=Currency(200.0),
            transport_v=Currency(300.0),
            transport_s=Currency(150.0),
        )
        assert tv.value_added == pytest.approx(650.0, rel=1e-5)

    def test_destination_equals_origin_plus_value_added(self) -> None:
        """Destination value = origin + value added by transport."""
        tv = TransportationValue(
            origin_value=Currency(10_000.0),
            transport_c=Currency(200.0),
            transport_v=Currency(300.0),
            transport_s=Currency(150.0),
        )
        assert tv.destination_value == pytest.approx(10_650.0, rel=1e-5)

    def test_transport_value_ratio(self) -> None:
        """Transport value ratio = value_added / destination_value."""
        tv = TransportationValue(
            origin_value=Currency(10_000.0),
            transport_c=Currency(200.0),
            transport_v=Currency(300.0),
            transport_s=Currency(150.0),
        )
        expected_ratio = 650.0 / 10_650.0
        assert tv.transport_value_ratio == pytest.approx(expected_ratio, rel=1e-5)


# =============================================================================
# T061-T064: classify_labor - Productive/Unproductive Classification
# =============================================================================


class TestClassifyLabor:
    """Tests for classify_labor function.

    Marx distinguishes between productive labor (creates use-value or
    transforms material) and unproductive labor (merely facilitates
    exchange without creating value).
    """

    def test_production_worker_is_productive(self) -> None:
        """Production workers transform materials -> productive."""
        result = classify_labor("51-0000", "Production workers")
        assert isinstance(result, LaborClassification)
        assert result.is_productive is True
        assert result.occupation_code == "51-0000"

    def test_truck_driver_is_productive(self) -> None:
        """Truck drivers change commodity location -> productive.

        Per Marx Capital II Ch. 6, transportation adds value because
        changing location is a real use-value transformation.
        """
        result = classify_labor("53-3032", "Truck drivers, heavy and tractor-trailer")
        assert result.is_productive is True

    def test_transport_worker_is_productive(self) -> None:
        """Transport workers change commodity location -> productive."""
        result = classify_labor("53-0000", "Transportation workers")
        assert result.is_productive is True

    def test_warehouse_worker_is_productive(self) -> None:
        """Warehouse workers preserve use-value -> productive."""
        result = classify_labor("53-7062", "Warehouse workers and laborers")
        assert result.is_productive is True

    def test_cashier_is_unproductive(self) -> None:
        """Cashiers facilitate exchange only -> unproductive."""
        result = classify_labor("41-2011", "Cashiers")
        assert result.is_productive is False

    def test_sales_worker_is_unproductive(self) -> None:
        """Sales workers facilitate exchange -> unproductive."""
        result = classify_labor("41-0000", "Sales representatives")
        assert result.is_productive is False

    def test_advertising_is_unproductive(self) -> None:
        """Advertising workers create no use-value -> unproductive."""
        result = classify_labor("11-2011", "Advertising and marketing managers")
        assert result.is_productive is False

    def test_accountant_is_unproductive(self) -> None:
        """Accountants facilitate exchange bookkeeping -> unproductive."""
        result = classify_labor("13-2011", "Accountants and auditors")
        assert result.is_productive is False

    def test_bookkeeper_is_unproductive(self) -> None:
        """Bookkeepers facilitate exchange bookkeeping -> unproductive."""
        result = classify_labor("43-3031", "Bookkeeping and accounting clerks")
        assert result.is_productive is False

    def test_security_guard_is_unproductive(self) -> None:
        """Security guards protect property relations -> unproductive."""
        result = classify_labor("33-9032", "Security guards and gaming surveillance")
        assert result.is_productive is False

    def test_classification_has_rationale(self) -> None:
        """Every classification includes a rationale string."""
        result = classify_labor("51-0000", "Production workers")
        assert len(result.rationale) > 0

    def test_classification_has_description(self) -> None:
        """Classification preserves the input description."""
        result = classify_labor("51-0000", "Production workers")
        assert result.description == "Production workers"

    def test_marketing_is_unproductive(self) -> None:
        """Marketing workers create no use-value -> unproductive."""
        result = classify_labor("13-1161", "Marketing specialists")
        assert result.is_productive is False
