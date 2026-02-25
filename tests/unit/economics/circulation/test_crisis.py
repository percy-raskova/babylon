"""Tests for Capital Volume II integrated crisis detection.

Feature: 023-capital-volume-ii
User Story: US7 - Integrated Crisis Detection (FR-021, FR-022)
Tasks: T065-T070

Tests cover:
    - Realization crisis flagged when commodity overhang > 0.3
    - Turnover crisis flagged when liquidity < 0.1 and circulation > production
    - Reproduction crisis flagged when balance not met
    - All three crises active simultaneously
    - No crises active (all normal)
    - Each crisis in isolation
    - Vulnerability string correctness
"""

from __future__ import annotations

from babylon.economics.circulation.crisis import assess_circulation_crisis
from babylon.economics.circulation.types import (
    CircuitState,
    CirculationCrisisAssessment,
    InventoryState,
    ReproductionAnalysis,
    ReproductionBalance,
    TurnoverProfile,
)
from babylon.models.types import Currency

# =============================================================================
# Test Constants
# =============================================================================

WAYNE_COUNTY_FIPS = "26163"
TEST_YEAR = 2022


# =============================================================================
# Helpers: Create test fixtures with specific conditions
# =============================================================================


def _normal_circuit() -> CircuitState:
    """Circuit state with no crisis conditions.

    Commodity overhang = 200/1000 = 0.2 (below 0.3 threshold).
    Liquidity ratio = 400/1000 = 0.4 (above 0.1 threshold).
    """
    return CircuitState(
        fips_code=WAYNE_COUNTY_FIPS,
        year=TEST_YEAR,
        money_capital=Currency(400.0),
        productive_capital=Currency(400.0),
        commodity_capital=Currency(200.0),
        fixed_capital=Currency(300.0),
        circulating_capital=Currency(100.0),
    )


def _high_overhang_circuit() -> CircuitState:
    """Circuit state with commodity overhang > 0.3.

    Commodity overhang = 400/1000 = 0.4 (above 0.3 threshold).
    Liquidity ratio = 300/1000 = 0.3 (above 0.1 threshold).
    """
    return CircuitState(
        fips_code=WAYNE_COUNTY_FIPS,
        year=TEST_YEAR,
        money_capital=Currency(300.0),
        productive_capital=Currency(300.0),
        commodity_capital=Currency(400.0),
        fixed_capital=Currency(200.0),
        circulating_capital=Currency(100.0),
    )


def _low_liquidity_circuit() -> CircuitState:
    """Circuit state with liquidity ratio < 0.1.

    Liquidity ratio = 50/1000 = 0.05 (below 0.1 threshold).
    Commodity overhang = 200/1000 = 0.2 (below 0.3 threshold).
    """
    return CircuitState(
        fips_code=WAYNE_COUNTY_FIPS,
        year=TEST_YEAR,
        money_capital=Currency(50.0),
        productive_capital=Currency(750.0),
        commodity_capital=Currency(200.0),
        fixed_capital=Currency(500.0),
        circulating_capital=Currency(250.0),
    )


def _crisis_all_circuit() -> CircuitState:
    """Circuit state with BOTH overhang > 0.3 AND liquidity < 0.1.

    Commodity overhang = 500/1000 = 0.5 (above 0.3).
    Liquidity ratio = 50/1000 = 0.05 (below 0.1).
    """
    return CircuitState(
        fips_code=WAYNE_COUNTY_FIPS,
        year=TEST_YEAR,
        money_capital=Currency(50.0),
        productive_capital=Currency(450.0),
        commodity_capital=Currency(500.0),
        fixed_capital=Currency(300.0),
        circulating_capital=Currency(150.0),
    )


def _normal_turnover() -> TurnoverProfile:
    """Turnover profile where production_time > circulation_time."""
    return TurnoverProfile(
        naics_code="31",
        working_period_days=20,
        non_working_production_days=5,
        purchase_time_days=3,
        sale_time_days=7,
        fixed_capital_ratio=0.6,
    )


def _slow_turnover() -> TurnoverProfile:
    """Turnover profile where circulation_time > production_time."""
    return TurnoverProfile(
        naics_code="31",
        working_period_days=5,
        non_working_production_days=2,
        purchase_time_days=10,
        sale_time_days=20,
        fixed_capital_ratio=0.6,
    )


def _normal_inventory() -> InventoryState:
    """Normal inventory state."""
    return InventoryState(
        fips_code=WAYNE_COUNTY_FIPS,
        year=TEST_YEAR,
        raw_materials=Currency(50_000.0),
        work_in_progress=Currency(30_000.0),
        finished_goods=Currency(80_000.0),
        days_inventory_raw=15.0,
        days_inventory_finished=30.0,
    )


def _supply_crisis_inventory() -> InventoryState:
    """Inventory with supply crisis (raw materials < 7 days)."""
    return InventoryState(
        fips_code=WAYNE_COUNTY_FIPS,
        year=TEST_YEAR,
        raw_materials=Currency(5_000.0),
        work_in_progress=Currency(30_000.0),
        finished_goods=Currency(80_000.0),
        days_inventory_raw=3.0,
        days_inventory_finished=30.0,
    )


def _balanced_reproduction() -> ReproductionBalance:
    """Reproduction balance condition met."""
    return ReproductionBalance(
        condition_met=True,
        gap=0.0,
        interpretation="Simple reproduction balance holds.",
    )


def _unbalanced_reproduction() -> ReproductionBalance:
    """Reproduction balance condition NOT met."""
    return ReproductionBalance(
        condition_met=False,
        gap=-50.0,
        interpretation="Department II deficit: insufficient consumption goods.",
    )


def _sustainable_analysis() -> ReproductionAnalysis:
    """Sustainable labor reproduction."""
    return ReproductionAnalysis(
        labor_power_demand=1000.0,
        reproduction_capacity=1200.0,
        gap=200.0,
        sustainability=True,
    )


def _unsustainable_analysis() -> ReproductionAnalysis:
    """Unsustainable labor reproduction."""
    return ReproductionAnalysis(
        labor_power_demand=1000.0,
        reproduction_capacity=800.0,
        gap=-200.0,
        sustainability=False,
    )


# =============================================================================
# T065: Realization Crisis Detection
# =============================================================================


class TestRealizationCrisis:
    """Tests for realization crisis flag in assess_circulation_crisis."""

    def test_realization_crisis_flagged_when_overhang_exceeds_threshold(self) -> None:
        """Realization crisis = True when commodity_overhang > 0.3."""
        result = assess_circulation_crisis(
            circuit_state=_high_overhang_circuit(),
            turnover=_normal_turnover(),
            inventory=_normal_inventory(),
            reproduction_balance=_balanced_reproduction(),
            reproduction_analysis=_sustainable_analysis(),
        )
        assert isinstance(result, CirculationCrisisAssessment)
        assert result.realization_crisis is True

    def test_no_realization_crisis_when_overhang_normal(self) -> None:
        """Realization crisis = False when commodity_overhang <= 0.3."""
        result = assess_circulation_crisis(
            circuit_state=_normal_circuit(),
            turnover=_normal_turnover(),
            inventory=_normal_inventory(),
            reproduction_balance=_balanced_reproduction(),
            reproduction_analysis=_sustainable_analysis(),
        )
        assert result.realization_crisis is False


# =============================================================================
# T066: Turnover Crisis Detection
# =============================================================================


class TestTurnoverCrisis:
    """Tests for turnover crisis flag in assess_circulation_crisis."""

    def test_turnover_crisis_when_low_liquidity_and_slow_circulation(self) -> None:
        """Turnover crisis = True when liquidity < 0.1 AND circulation > production."""
        result = assess_circulation_crisis(
            circuit_state=_low_liquidity_circuit(),
            turnover=_slow_turnover(),
            inventory=_normal_inventory(),
            reproduction_balance=_balanced_reproduction(),
            reproduction_analysis=_sustainable_analysis(),
        )
        assert result.turnover_crisis is True

    def test_no_turnover_crisis_when_liquidity_adequate(self) -> None:
        """Turnover crisis = False when liquidity ratio is adequate."""
        result = assess_circulation_crisis(
            circuit_state=_normal_circuit(),
            turnover=_slow_turnover(),
            inventory=_normal_inventory(),
            reproduction_balance=_balanced_reproduction(),
            reproduction_analysis=_sustainable_analysis(),
        )
        assert result.turnover_crisis is False

    def test_no_turnover_crisis_when_circulation_not_slow(self) -> None:
        """Turnover crisis = False when circulation_time <= production_time."""
        result = assess_circulation_crisis(
            circuit_state=_low_liquidity_circuit(),
            turnover=_normal_turnover(),
            inventory=_normal_inventory(),
            reproduction_balance=_balanced_reproduction(),
            reproduction_analysis=_sustainable_analysis(),
        )
        assert result.turnover_crisis is False


# =============================================================================
# T067: Reproduction Crisis Detection
# =============================================================================


class TestReproductionCrisis:
    """Tests for reproduction crisis flag in assess_circulation_crisis."""

    def test_reproduction_crisis_when_balance_not_met(self) -> None:
        """Reproduction crisis = True when balance condition_met is False."""
        result = assess_circulation_crisis(
            circuit_state=_normal_circuit(),
            turnover=_normal_turnover(),
            inventory=_normal_inventory(),
            reproduction_balance=_unbalanced_reproduction(),
            reproduction_analysis=_sustainable_analysis(),
        )
        assert result.reproduction_crisis is True

    def test_reproduction_crisis_when_not_sustainable(self) -> None:
        """Reproduction crisis = True when sustainability is False."""
        result = assess_circulation_crisis(
            circuit_state=_normal_circuit(),
            turnover=_normal_turnover(),
            inventory=_normal_inventory(),
            reproduction_balance=_balanced_reproduction(),
            reproduction_analysis=_unsustainable_analysis(),
        )
        assert result.reproduction_crisis is True

    def test_no_reproduction_crisis_when_all_balanced(self) -> None:
        """Reproduction crisis = False when balance met AND sustainable."""
        result = assess_circulation_crisis(
            circuit_state=_normal_circuit(),
            turnover=_normal_turnover(),
            inventory=_normal_inventory(),
            reproduction_balance=_balanced_reproduction(),
            reproduction_analysis=_sustainable_analysis(),
        )
        assert result.reproduction_crisis is False


# =============================================================================
# T068: Combined Crisis States
# =============================================================================


class TestCombinedCrisisStates:
    """Tests for combined crisis detection scenarios."""

    def test_all_three_crises_active(self) -> None:
        """All three crisis types can be active simultaneously."""
        result = assess_circulation_crisis(
            circuit_state=_crisis_all_circuit(),
            turnover=_slow_turnover(),
            inventory=_normal_inventory(),
            reproduction_balance=_unbalanced_reproduction(),
            reproduction_analysis=_unsustainable_analysis(),
        )
        assert result.realization_crisis is True
        assert result.turnover_crisis is True
        assert result.reproduction_crisis is True

    def test_no_crises_active(self) -> None:
        """No crisis flags when all conditions are normal."""
        result = assess_circulation_crisis(
            circuit_state=_normal_circuit(),
            turnover=_normal_turnover(),
            inventory=_normal_inventory(),
            reproduction_balance=_balanced_reproduction(),
            reproduction_analysis=_sustainable_analysis(),
        )
        assert result.realization_crisis is False
        assert result.turnover_crisis is False
        assert result.reproduction_crisis is False
        assert len(result.vulnerabilities) == 0

    def test_only_realization_crisis(self) -> None:
        """Only realization crisis active, others normal."""
        result = assess_circulation_crisis(
            circuit_state=_high_overhang_circuit(),
            turnover=_normal_turnover(),
            inventory=_normal_inventory(),
            reproduction_balance=_balanced_reproduction(),
            reproduction_analysis=_sustainable_analysis(),
        )
        assert result.realization_crisis is True
        assert result.turnover_crisis is False
        assert result.reproduction_crisis is False

    def test_only_turnover_crisis(self) -> None:
        """Only turnover crisis active, others normal."""
        result = assess_circulation_crisis(
            circuit_state=_low_liquidity_circuit(),
            turnover=_slow_turnover(),
            inventory=_normal_inventory(),
            reproduction_balance=_balanced_reproduction(),
            reproduction_analysis=_sustainable_analysis(),
        )
        assert result.realization_crisis is False
        assert result.turnover_crisis is True
        assert result.reproduction_crisis is False

    def test_only_reproduction_crisis(self) -> None:
        """Only reproduction crisis active, others normal."""
        result = assess_circulation_crisis(
            circuit_state=_normal_circuit(),
            turnover=_normal_turnover(),
            inventory=_normal_inventory(),
            reproduction_balance=_unbalanced_reproduction(),
            reproduction_analysis=_unsustainable_analysis(),
        )
        assert result.realization_crisis is False
        assert result.turnover_crisis is False
        assert result.reproduction_crisis is True


# =============================================================================
# T069-T070: Vulnerability Strings
# =============================================================================


class TestVulnerabilityStrings:
    """Tests for vulnerability string generation."""

    def test_realization_crisis_vulnerability(self) -> None:
        """REALIZATION_CRISIS vulnerability when overhang > 0.3."""
        result = assess_circulation_crisis(
            circuit_state=_high_overhang_circuit(),
            turnover=_normal_turnover(),
            inventory=_normal_inventory(),
            reproduction_balance=_balanced_reproduction(),
            reproduction_analysis=_sustainable_analysis(),
        )
        assert "REALIZATION_CRISIS" in result.vulnerabilities

    def test_supply_chain_crisis_vulnerability(self) -> None:
        """SUPPLY_CHAIN_CRISIS vulnerability when inventory has supply crisis."""
        result = assess_circulation_crisis(
            circuit_state=_normal_circuit(),
            turnover=_normal_turnover(),
            inventory=_supply_crisis_inventory(),
            reproduction_balance=_balanced_reproduction(),
            reproduction_analysis=_sustainable_analysis(),
        )
        assert "SUPPLY_CHAIN_CRISIS" in result.vulnerabilities

    def test_labor_shortage_vulnerability(self) -> None:
        """LABOR_SHORTAGE vulnerability when sustainability is False."""
        result = assess_circulation_crisis(
            circuit_state=_normal_circuit(),
            turnover=_normal_turnover(),
            inventory=_normal_inventory(),
            reproduction_balance=_balanced_reproduction(),
            reproduction_analysis=_unsustainable_analysis(),
        )
        assert "LABOR_SHORTAGE" in result.vulnerabilities

    def test_monetary_crisis_vulnerability(self) -> None:
        """MONETARY_CRISIS vulnerability when liquidity ratio < 0.1."""
        result = assess_circulation_crisis(
            circuit_state=_low_liquidity_circuit(),
            turnover=_normal_turnover(),
            inventory=_normal_inventory(),
            reproduction_balance=_balanced_reproduction(),
            reproduction_analysis=_sustainable_analysis(),
        )
        assert "MONETARY_CRISIS" in result.vulnerabilities

    def test_no_vulnerabilities_when_normal(self) -> None:
        """Empty vulnerability list when all conditions normal."""
        result = assess_circulation_crisis(
            circuit_state=_normal_circuit(),
            turnover=_normal_turnover(),
            inventory=_normal_inventory(),
            reproduction_balance=_balanced_reproduction(),
            reproduction_analysis=_sustainable_analysis(),
        )
        assert result.vulnerabilities == []

    def test_multiple_vulnerabilities_accumulate(self) -> None:
        """Multiple vulnerability conditions produce multiple strings."""
        result = assess_circulation_crisis(
            circuit_state=_crisis_all_circuit(),
            turnover=_slow_turnover(),
            inventory=_supply_crisis_inventory(),
            reproduction_balance=_unbalanced_reproduction(),
            reproduction_analysis=_unsustainable_analysis(),
        )
        assert "REALIZATION_CRISIS" in result.vulnerabilities
        assert "MONETARY_CRISIS" in result.vulnerabilities
        assert "SUPPLY_CHAIN_CRISIS" in result.vulnerabilities
        assert "LABOR_SHORTAGE" in result.vulnerabilities

    def test_assessment_has_fips_and_year(self) -> None:
        """Assessment carries FIPS code and year from circuit_state."""
        result = assess_circulation_crisis(
            circuit_state=_normal_circuit(),
            turnover=_normal_turnover(),
            inventory=_normal_inventory(),
            reproduction_balance=_balanced_reproduction(),
            reproduction_analysis=_sustainable_analysis(),
        )
        assert result.fips_code == WAYNE_COUNTY_FIPS
        assert result.year == TEST_YEAR
