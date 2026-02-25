"""Tests for Capital Volume II inventory and realization crisis detection.

Feature: 023-capital-volume-ii
User Story: US5 - Inventory & Realization (FR-015, FR-016, FR-017)
Tasks: T055-T058

Tests cover:
    - compute_realization_metrics at 4 severity thresholds
    - Boundary test at 95% realization rate
    - detect_realization_crisis trend analysis
"""

from __future__ import annotations

import pytest

from babylon.economics.circulation.inventory import (
    compute_realization_metrics,
    detect_realization_crisis,
)
from babylon.economics.circulation.types import (
    CrisisSeverity,
    InventoryState,
)
from babylon.models.types import Currency

# =============================================================================
# Test Constants
# =============================================================================

WAYNE_COUNTY_FIPS = "26163"
TEST_YEAR = 2022


# =============================================================================
# Helper: Create InventoryState with specific finished_goods
# =============================================================================


def _make_inventory(
    finished_goods: float,
    *,
    fips: str = WAYNE_COUNTY_FIPS,
    year: int = TEST_YEAR,
    raw_materials: float = 50_000.0,
    work_in_progress: float = 30_000.0,
    days_inventory_raw: float = 15.0,
    days_inventory_finished: float = 30.0,
) -> InventoryState:
    """Create an InventoryState with customizable finished_goods."""
    return InventoryState(
        fips_code=fips,
        year=year,
        raw_materials=Currency(raw_materials),
        work_in_progress=Currency(work_in_progress),
        finished_goods=Currency(finished_goods),
        days_inventory_raw=days_inventory_raw,
        days_inventory_finished=days_inventory_finished,
    )


# =============================================================================
# T055: compute_realization_metrics - Severity Thresholds
# =============================================================================


class TestComputeRealizationMetrics:
    """Tests for compute_realization_metrics function."""

    def test_normal_severity_at_98_percent(self) -> None:
        """98% realization rate -> NORMAL severity."""
        result = compute_realization_metrics(
            value_produced=Currency(1_000_000.0),
            value_realized=Currency(980_000.0),
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
        )
        assert result.crisis_severity == CrisisSeverity.NORMAL

    def test_mild_slowdown_at_90_percent(self) -> None:
        """90% realization rate -> MILD_SLOWDOWN severity."""
        result = compute_realization_metrics(
            value_produced=Currency(1_000_000.0),
            value_realized=Currency(900_000.0),
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
        )
        assert result.crisis_severity == CrisisSeverity.MILD_SLOWDOWN

    def test_recession_at_75_percent(self) -> None:
        """75% realization rate -> RECESSION severity."""
        result = compute_realization_metrics(
            value_produced=Currency(1_000_000.0),
            value_realized=Currency(750_000.0),
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
        )
        assert result.crisis_severity == CrisisSeverity.RECESSION

    def test_crisis_at_60_percent(self) -> None:
        """60% realization rate -> CRISIS severity."""
        result = compute_realization_metrics(
            value_produced=Currency(1_000_000.0),
            value_realized=Currency(600_000.0),
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
        )
        assert result.crisis_severity == CrisisSeverity.CRISIS

    def test_boundary_95_percent_is_mild_slowdown(self) -> None:
        """95% realization rate -> MILD_SLOWDOWN (not NORMAL).

        The threshold is > 0.95 for NORMAL, so exactly 0.95 falls into
        MILD_SLOWDOWN territory.
        """
        result = compute_realization_metrics(
            value_produced=Currency(1_000_000.0),
            value_realized=Currency(950_000.0),
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
        )
        assert result.crisis_severity == CrisisSeverity.MILD_SLOWDOWN

    def test_realization_gap_computed(self) -> None:
        """Realization gap equals produced minus realized."""
        result = compute_realization_metrics(
            value_produced=Currency(1_000_000.0),
            value_realized=Currency(900_000.0),
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
        )
        assert result.realization_gap == pytest.approx(100_000.0, rel=1e-3)

    def test_realization_rate_computed(self) -> None:
        """Realization rate equals realized / produced."""
        result = compute_realization_metrics(
            value_produced=Currency(1_000_000.0),
            value_realized=Currency(900_000.0),
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
        )
        assert result.realization_rate == pytest.approx(0.9, rel=1e-5)

    def test_fips_and_year_passthrough(self) -> None:
        """FIPS code and year are passed through to the model."""
        result = compute_realization_metrics(
            value_produced=Currency(1_000_000.0),
            value_realized=Currency(980_000.0),
            fips_code="06037",
            year=2023,
        )
        assert result.fips_code == "06037"
        assert result.year == 2023


# =============================================================================
# T056-T058: detect_realization_crisis - Trend Analysis
# =============================================================================


class TestDetectRealizationCrisis:
    """Tests for detect_realization_crisis function."""

    def test_rising_inventory_falling_production_is_crisis(self) -> None:
        """Rising finished goods + falling production -> True."""
        inventory_trend = [
            _make_inventory(80_000.0),
            _make_inventory(120_000.0),
        ]
        production_trend = [
            Currency(500_000.0),
            Currency(450_000.0),
        ]
        result = detect_realization_crisis(inventory_trend, production_trend)
        assert result is True

    def test_rising_inventory_rising_production_not_crisis(self) -> None:
        """Rising finished goods + rising production -> False.

        If production is also rising, the inventory buildup may be
        intentional (e.g., seasonal stockpiling), not a realization problem.
        """
        inventory_trend = [
            _make_inventory(80_000.0),
            _make_inventory(120_000.0),
        ]
        production_trend = [
            Currency(500_000.0),
            Currency(600_000.0),
        ]
        result = detect_realization_crisis(inventory_trend, production_trend)
        assert result is False

    def test_flat_inventory_not_crisis(self) -> None:
        """Flat finished goods inventory -> False."""
        inventory_trend = [
            _make_inventory(100_000.0),
            _make_inventory(100_000.0),
        ]
        production_trend = [
            Currency(500_000.0),
            Currency(450_000.0),
        ]
        result = detect_realization_crisis(inventory_trend, production_trend)
        assert result is False

    def test_single_element_list_returns_false(self) -> None:
        """Single-element trend list -> False (insufficient data)."""
        inventory_trend = [_make_inventory(100_000.0)]
        production_trend = [Currency(500_000.0)]
        result = detect_realization_crisis(inventory_trend, production_trend)
        assert result is False

    def test_empty_list_returns_false(self) -> None:
        """Empty trend lists -> False (no data)."""
        result = detect_realization_crisis([], [])
        assert result is False

    def test_rising_inventory_flat_production_is_crisis(self) -> None:
        """Rising finished goods + flat production -> True.

        Flat production with rising inventory means goods are not
        being absorbed by the market.
        """
        inventory_trend = [
            _make_inventory(80_000.0),
            _make_inventory(120_000.0),
        ]
        production_trend = [
            Currency(500_000.0),
            Currency(500_000.0),
        ]
        result = detect_realization_crisis(inventory_trend, production_trend)
        assert result is True
