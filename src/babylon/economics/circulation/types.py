"""Type definitions for Capital Volume II: Circulation of Capital.

Feature: 023-capital-volume-ii
Date: 2026-02-25

Frozen Pydantic models for the circuit of capital (M-C-P-C'-M'),
turnover time decomposition, fixed/circulating capital, depreciation
fund dynamics, reproduction schema balance, inventory tracking,
realization/disproportionality crises, circulation costs, and
integrated crisis state.

Models:
    - CircuitState: Three-form capital composition (M, P, C)
    - TurnoverProfile: Sectoral turnover time decomposition
    - AnnualSurplusValue: Turnover-adjusted surplus value (Capital II Ch. 16)
    - FixedCapitalItem: Individual fixed capital asset with depreciation
    - DepreciationFundState: Aggregate depreciation fund adequacy
    - MoralDepreciation: Technological obsolescence factor
    - InventoryState: Raw/WIP/finished goods inventory tracking
    - ReproductionBalance: Simple reproduction balance condition
    - ReproductionAnalysis: Labor power reproduction capacity
    - RealizationCrisis: Commodity realization gap assessment
    - DisproportionalityCrisis: Dept I/II output imbalance
    - PureCirculationCosts: Faux frais de production (Marx)
    - TransportationValue: Transport as value-adding industry
    - CirculationCrisisAssessment: Multi-dimensional crisis flags
    - CirculationCrisisState: Composite per-county circulation state

Enums:
    - CapitalForm: Money, productive, commodity capital
    - ReplacementCyclePosition: Investment lifecycle phase
    - InventoryDiagnosis: Inventory health classification
    - CrisisSeverity: Realization crisis severity level

See Also:
    :mod:`babylon.economics.tensor`: ValueTensor4x3 (Volume I production)
    :mod:`babylon.economics.tick`: TickDynamicsSystem pipeline integration
    :mod:`babylon.economics.crisis`: TRPF crisis mechanics (Feature 018)
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, computed_field

from babylon.models.types import Currency

# =============================================================================
# THRESHOLD CONSTANTS (Module-Level)
# =============================================================================

OVERPRODUCTION_DAYS_THRESHOLD: Final[float] = 60.0
"""Finished goods inventory days threshold for overproduction diagnosis.

Traceability: Census M3 inventory-to-shipments ratio. When finished goods
exceed ~60 days of inventory, the economy is producing beyond effective
demand. Derived from historical M3 survey data where ratios above 1.5
(~45 shipping days) signal slowdown; 60 days provides conservative buffer.
"""

SUPPLY_CRISIS_DAYS_THRESHOLD: Final[float] = 7.0
"""Raw materials inventory days threshold for supply crisis diagnosis.

Traceability: Standard JIT minimum buffer. Modern JIT manufacturing
targets 3-7 days of raw materials. Below 7 days, production continuity
is at risk. Derived from Toyota Production System benchmarks and
post-2021 supply chain disruption analyses.
"""

COMMODITY_OVERHANG_CRISIS: Final[float] = 0.3
"""Commodity capital share threshold triggering circulation crisis.

Traceability: Marx Capital II Ch. 16-17. When commodity capital exceeds
30% of total circuit value, the M-C-P-C'-M' circuit is stalling in the
C'-M' phase (realization). This indicates systemic inability to convert
produced commodities back into money capital.
"""

LIQUIDITY_CRISIS_RATIO: Final[float] = 0.1
"""Money capital share threshold below which liquidity crisis occurs.

Traceability: Marx Capital II Ch. 15. When money capital falls below
10% of total circuit value, the capitalist lacks sufficient liquidity
to purchase labor power and means of production for the next production
cycle. The M-C phase of the circuit is blocked.
"""

REALIZATION_RATE_NORMAL: Final[float] = 0.95
"""Realization rate above which no crisis is diagnosed.

Traceability: NBER recession classification. During normal economic
periods, 95%+ of produced commodity value is successfully realized
through sale. Below this threshold indicates emerging demand deficiency.
"""

REALIZATION_RATE_SLOWDOWN: Final[float] = 0.85
"""Realization rate threshold for mild slowdown classification.

Traceability: NBER recession classification. Realization rates between
85-95% correspond to mild demand contraction observable in retail sales
and industrial production indices during early recession phases.
"""

REALIZATION_RATE_RECESSION: Final[float] = 0.70
"""Realization rate threshold for recession classification.

Traceability: NBER recession classification. Realization rates between
70-85% correspond to significant demand destruction observed during
major recessions (2008-09 levels). Below 70% constitutes full crisis.
"""

REPLACEMENT_BOOM_RATIO: Final[float] = 1.5
"""Depreciation fund ratio threshold for investment boom classification.

Traceability: BEA Fixed Asset Tables. When accumulated depreciation
exceeds 1.5x annual depreciation flow, excess funds drive replacement
investment beyond maintenance needs, creating investment boom dynamics.
"""

REPLACEMENT_EXPANSION_RATIO: Final[float] = 1.0
"""Depreciation fund ratio threshold for expansion classification.

Traceability: BEA Fixed Asset Tables. Fund adequacy above 1.0 means
the depreciation fund covers at least one full year of depreciation,
enabling timely replacement and modest expansion of fixed capital stock.
"""

REPLACEMENT_MAINTENANCE_RATIO: Final[float] = 0.7
"""Depreciation fund ratio threshold for maintenance classification.

Traceability: BEA Fixed Asset Tables. Fund adequacy between 0.7 and
1.0 indicates the depreciation fund can cover replacement needs but
without surplus for expansion. Below 0.7 signals disinvestment risk.
"""


# =============================================================================
# ENUMS
# =============================================================================


class CapitalForm(StrEnum):
    """Form of capital within the circuit M-C-P-C'-M'.

    Capital exists in three functional forms as it circulates through
    the production and realization process. At any moment, a portion
    of total capital is frozen in each form.

    Values:
        MONEY: Liquid capital available for purchase (M and M').
        PRODUCTIVE: Capital engaged in production (means of production + labor power).
        COMMODITY: Produced goods awaiting sale (C').

    See Also:
        :class:`CircuitState`: Quantitative decomposition by form.
    """

    MONEY = "money"
    PRODUCTIVE = "productive"
    COMMODITY = "commodity"


class ReplacementCyclePosition(StrEnum):
    """Position within the fixed capital replacement cycle.

    Fixed capital creates a replacement fund through annual depreciation
    charges. The adequacy of this fund relative to depreciation flow
    determines the investment phase of the economy.

    Values:
        INVESTMENT_BOOM: Fund ratio > 1.5 (excess funds drive replacement wave).
        EXPANSION: Fund ratio > 1.0 (adequate for timely replacement).
        MAINTENANCE: Fund ratio > 0.7 (covers basics, no expansion).
        DISINVESTMENT: Fund ratio <= 0.7 (capital stock deteriorating).

    See Also:
        :class:`DepreciationFundState`: Computes replacement cycle position.
    """

    INVESTMENT_BOOM = "investment_boom"
    EXPANSION = "expansion"
    MAINTENANCE = "maintenance"
    DISINVESTMENT = "disinvestment"


class InventoryDiagnosis(StrEnum):
    """Diagnosis of inventory health for a territory.

    Classifies the inventory situation based on days-of-inventory
    thresholds for raw materials and finished goods.

    Values:
        NORMAL: Inventory levels within acceptable bounds.
        OVERPRODUCTION: Finished goods exceed demand absorption capacity.
        SUPPLY_CRISIS: Raw materials below minimum production buffer.

    See Also:
        :class:`InventoryState`: Produces this diagnosis from inventory data.
    """

    NORMAL = "normal"
    OVERPRODUCTION = "overproduction"
    SUPPLY_CRISIS = "supply_crisis"


class CrisisSeverity(StrEnum):
    """Severity classification for realization crisis.

    Based on the gap between commodity value produced and commodity
    value successfully realized (sold). Maps to NBER recession
    classification methodology.

    Values:
        NORMAL: Realization rate >= 95% (healthy demand).
        MILD_SLOWDOWN: Realization rate 85-95% (emerging demand deficiency).
        RECESSION: Realization rate 70-85% (significant demand destruction).
        CRISIS: Realization rate < 70% (systemic realization failure).

    See Also:
        :class:`RealizationCrisis`: Computes severity from realization data.
    """

    NORMAL = "normal"
    MILD_SLOWDOWN = "mild_slowdown"
    RECESSION = "recession"
    CRISIS = "crisis"


# =============================================================================
# FROZEN MODELS
# =============================================================================


class CircuitState(BaseModel):
    """Capital composition across the three forms of the circuit M-C-P-C'-M'.

    Tracks how total capital is distributed among money, productive, and
    commodity forms at a given point in time for a county. Also decomposes
    productive capital into fixed and circulating components.

    Args:
        fips_code: 5-digit county FIPS code.
        year: Calendar year of the snapshot.
        money_capital: Liquid capital available for purchase (M).
        productive_capital: Capital engaged in production (P).
        commodity_capital: Produced goods awaiting sale (C').
        fixed_capital: Durable means of production (buildings, machinery).
        circulating_capital: Consumed-per-cycle inputs (raw materials, labor power).

    Example:
        >>> state = CircuitState(
        ...     fips_code="26163", year=2015,
        ...     money_capital=100.0, productive_capital=300.0,
        ...     commodity_capital=200.0,
        ...     fixed_capital=250.0, circulating_capital=50.0,
        ... )
        >>> state.total_capital
        600.0
    """

    model_config = ConfigDict(frozen=True)

    fips_code: str = Field(..., min_length=5, max_length=5, description="5-digit county FIPS code")
    year: int = Field(..., ge=2010, description="Calendar year of the snapshot")
    money_capital: Currency = Field(..., description="Liquid capital available for purchase (M)")
    productive_capital: Currency = Field(..., description="Capital engaged in production (P)")
    commodity_capital: Currency = Field(..., description="Produced goods awaiting sale (C')")
    fixed_capital: Currency = Field(
        ..., description="Durable means of production (buildings, machinery)"
    )
    circulating_capital: Currency = Field(
        ..., description="Consumed-per-cycle inputs (raw materials, labor power)"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_capital(self) -> Currency:
        """Total capital across all three circuit forms (M + P + C).

        Returns:
            Sum of money, productive, and commodity capital.
        """
        return Currency(self.money_capital + self.productive_capital + self.commodity_capital)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def liquidity_ratio(self) -> float:
        """Share of total capital held as money (M / total).

        A low liquidity ratio indicates capital is locked in production
        or unsold commodities, reducing ability to begin new circuits.

        Returns:
            Money capital as fraction of total, 0.0 if total is zero.
        """
        total = self.money_capital + self.productive_capital + self.commodity_capital
        if total == 0.0:
            return 0.0
        return self.money_capital / total

    @computed_field  # type: ignore[prop-decorator]
    @property
    def commodity_overhang(self) -> float:
        """Share of total capital stuck as unsold commodities (C / total).

        High commodity overhang signals realization difficulties: the
        economy is producing more than effective demand can absorb.

        Returns:
            Commodity capital as fraction of total, 0.0 if total is zero.
        """
        total = self.money_capital + self.productive_capital + self.commodity_capital
        if total == 0.0:
            return 0.0
        return self.commodity_capital / total


class TurnoverProfile(BaseModel):
    """Sectoral turnover time decomposition per NAICS code.

    Decomposes the total turnover time into production time and
    circulation time components, following Marx's Capital Volume II
    Ch. 12-14 analysis.

    Args:
        naics_code: NAICS industry code.
        working_period_days: Days of active production per cycle.
        non_working_production_days: Days in production but not actively worked
            (e.g., aging, drying, chemical processes).
        purchase_time_days: Days to acquire means of production.
        sale_time_days: Days to sell finished commodities.
        fixed_capital_ratio: Fraction of productive capital that is fixed
            (durable, multi-cycle) vs circulating (consumed per cycle).

    Example:
        >>> profile = TurnoverProfile(
        ...     naics_code="31", working_period_days=20,
        ...     non_working_production_days=5, purchase_time_days=3,
        ...     sale_time_days=7, fixed_capital_ratio=0.6,
        ... )
        >>> profile.turnover_time
        35
    """

    model_config = ConfigDict(frozen=True)

    naics_code: str = Field(..., description="NAICS industry code")
    working_period_days: int = Field(..., gt=0, description="Days of active production per cycle")
    non_working_production_days: int = Field(
        ..., ge=0, description="Days in production but not actively worked"
    )
    purchase_time_days: int = Field(..., ge=0, description="Days to acquire means of production")
    sale_time_days: int = Field(..., ge=0, description="Days to sell finished commodities")
    fixed_capital_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of productive capital that is fixed (durable)",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def production_time(self) -> int:
        """Total production time (working period + non-working production).

        Returns:
            Sum of working and non-working production days.
        """
        return self.working_period_days + self.non_working_production_days

    @computed_field  # type: ignore[prop-decorator]
    @property
    def circulation_time(self) -> int:
        """Total circulation time (purchase + sale time).

        Returns:
            Sum of purchase and sale time days.
        """
        return self.purchase_time_days + self.sale_time_days

    @computed_field  # type: ignore[prop-decorator]
    @property
    def turnover_time(self) -> int:
        """Total turnover time for one complete circuit (production + circulation).

        Returns:
            Sum of production time and circulation time in days.
        """
        return (
            self.working_period_days
            + self.non_working_production_days
            + self.purchase_time_days
            + self.sale_time_days
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def turnovers_per_year(self) -> float:
        """Number of complete circuits per year (365 / turnover_time).

        Returns:
            Annual turnover count, 0.0 if turnover time is zero.
        """
        total = (
            self.working_period_days
            + self.non_working_production_days
            + self.purchase_time_days
            + self.sale_time_days
        )
        if total == 0:
            return 0.0
        return 365.0 / total

    @computed_field  # type: ignore[prop-decorator]
    @property
    def production_ratio(self) -> float:
        """Fraction of turnover time spent in production vs circulation.

        A high production ratio means capital spends most of its time
        productively employed rather than idle in circulation.

        Returns:
            Production time as fraction of turnover time, 0.0 if turnover is zero.
        """
        total = (
            self.working_period_days
            + self.non_working_production_days
            + self.purchase_time_days
            + self.sale_time_days
        )
        if total == 0:
            return 0.0
        production = self.working_period_days + self.non_working_production_days
        return production / total


class AnnualSurplusValue(BaseModel):
    """Turnover-adjusted annual surplus value per Marx Capital II Ch. 16.

    The annual rate of surplus value differs from the simple rate because
    faster turnover allows the same variable capital to be advanced
    multiple times per year, extracting surplus value each cycle.

    Args:
        fips_code: 5-digit county FIPS code.
        year: Calendar year.
        variable_capital_advanced: Variable capital (v) advanced per cycle.
        surplus_value_per_cycle: Surplus value (s) extracted per cycle.
        turnover_time_days: Days for one complete circuit.

    Example:
        >>> asv = AnnualSurplusValue(
        ...     fips_code="26163", year=2015,
        ...     variable_capital_advanced=1000.0,
        ...     surplus_value_per_cycle=500.0,
        ...     turnover_time_days=73,
        ... )
        >>> asv.annual_rate_of_surplus_value
        2.5
    """

    model_config = ConfigDict(frozen=True)

    fips_code: str = Field(..., min_length=5, max_length=5, description="5-digit county FIPS code")
    year: int = Field(..., description="Calendar year")
    variable_capital_advanced: Currency = Field(
        ..., gt=0, description="Variable capital (v) advanced per cycle"
    )
    surplus_value_per_cycle: Currency = Field(
        ..., description="Surplus value (s) extracted per cycle"
    )
    turnover_time_days: int = Field(..., gt=0, description="Days for one complete circuit")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def rate_of_surplus_value(self) -> float:
        """Simple rate of surplus value per cycle (s / v).

        Returns:
            Surplus value divided by variable capital for a single cycle.
        """
        return self.surplus_value_per_cycle / self.variable_capital_advanced

    @computed_field  # type: ignore[prop-decorator]
    @property
    def turnovers_per_year(self) -> float:
        """Number of complete turnover cycles per year (365 / days).

        Returns:
            Annual turnover count.
        """
        return 365.0 / self.turnover_time_days

    @computed_field  # type: ignore[prop-decorator]
    @property
    def annual_surplus_value(self) -> Currency:
        """Total surplus value extracted over one year (s * turnovers).

        Returns:
            Annualized surplus value accounting for turnover frequency.
        """
        turnovers = 365.0 / self.turnover_time_days
        return Currency(self.surplus_value_per_cycle * turnovers)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def annual_rate_of_surplus_value(self) -> float:
        """Annual rate of surplus value ((s/v) * turnovers per year).

        This is the key insight of Capital II Ch. 16: the annual rate
        of surplus value can far exceed the simple rate because variable
        capital turns over multiple times per year.

        Returns:
            Turnover-adjusted annual exploitation rate.
        """
        turnovers = 365.0 / self.turnover_time_days
        rate = self.surplus_value_per_cycle / self.variable_capital_advanced
        return rate * turnovers


class FixedCapitalItem(BaseModel):
    """Individual fixed capital asset with straight-line depreciation.

    Models a single durable means of production (building, machine, etc.)
    that transfers its value to the product gradually over its service life.

    Args:
        item_id: Unique identifier for this asset.
        category: Asset category (e.g., 'machinery', 'building', 'vehicle').
        initial_value: Original purchase value of the asset.
        service_life_years: Expected useful life in years.
        current_age_years: Current age of the asset in years.

    Example:
        >>> item = FixedCapitalItem(
        ...     item_id="PRESS-001", category="machinery",
        ...     initial_value=100000.0, service_life_years=10.0,
        ...     current_age_years=3.0,
        ... )
        >>> item.annual_depreciation
        10000.0
        >>> item.remaining_value
        70000.0
    """

    model_config = ConfigDict(frozen=True)

    item_id: str = Field(..., description="Unique identifier for this asset")
    category: str = Field(
        ..., description="Asset category (e.g., 'machinery', 'building', 'vehicle')"
    )
    initial_value: Currency = Field(..., gt=0, description="Original purchase value of the asset")
    service_life_years: float = Field(..., gt=0, description="Expected useful life in years")
    current_age_years: float = Field(..., ge=0, description="Current age of the asset in years")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def annual_depreciation(self) -> Currency:
        """Annual straight-line depreciation (initial_value / service_life).

        Returns:
            Annual depreciation charge.
        """
        return Currency(self.initial_value / self.service_life_years)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def remaining_value(self) -> Currency:
        """Remaining undepreciated value of the asset.

        Computed as initial_value minus accumulated depreciation, floored
        at zero (an asset cannot have negative remaining value).

        Returns:
            max(0, initial_value - annual_depreciation * current_age).
        """
        depreciation_charge = self.initial_value / self.service_life_years
        accumulated = depreciation_charge * self.current_age_years
        return Currency(max(0.0, self.initial_value - accumulated))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def depreciation_fund_required(self) -> Currency:
        """Depreciation fund that should have been accumulated by current age.

        Equals initial_value minus remaining_value: the total value already
        transferred from fixed capital to the product.

        Returns:
            Accumulated depreciation amount (initial - remaining).
        """
        depreciation_charge = self.initial_value / self.service_life_years
        accumulated = depreciation_charge * self.current_age_years
        remaining = max(0.0, self.initial_value - accumulated)
        return Currency(self.initial_value - remaining)


class DepreciationFundState(BaseModel):
    """Aggregate depreciation fund adequacy for a county-year.

    Tracks the relationship between accumulated depreciation reserves
    and annual depreciation flow to determine the replacement cycle
    position of the local economy.

    Args:
        fips_code: 5-digit county FIPS code.
        year: Calendar year.
        total_fixed_capital: Total fixed capital stock value.
        accumulated_depreciation: Depreciation reserves accumulated to date.
        annual_depreciation_flow: Annual depreciation charge across all fixed capital.
        replacement_expenditure: Actual replacement investment this year.

    Example:
        >>> fund = DepreciationFundState(
        ...     fips_code="26163", year=2015,
        ...     total_fixed_capital=1000000.0,
        ...     accumulated_depreciation=150000.0,
        ...     annual_depreciation_flow=100000.0,
        ...     replacement_expenditure=80000.0,
        ... )
        >>> fund.fund_adequacy
        1.5
        >>> fund.replacement_cycle_position
        <ReplacementCyclePosition.INVESTMENT_BOOM: 'investment_boom'>
    """

    model_config = ConfigDict(frozen=True)

    fips_code: str = Field(..., min_length=5, max_length=5, description="5-digit county FIPS code")
    year: int = Field(..., description="Calendar year")
    total_fixed_capital: Currency = Field(..., description="Total fixed capital stock value")
    accumulated_depreciation: Currency = Field(
        ..., description="Depreciation reserves accumulated to date"
    )
    annual_depreciation_flow: Currency = Field(
        ..., gt=0, description="Annual depreciation charge across all fixed capital"
    )
    replacement_expenditure: Currency = Field(
        ..., description="Actual replacement investment this year"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def fund_adequacy(self) -> float:
        """Ratio of accumulated depreciation to annual depreciation flow.

        Measures how many years of depreciation the fund can cover.
        A ratio of 1.0 means exactly one year of coverage.

        Returns:
            Accumulated depreciation divided by annual flow.
        """
        return self.accumulated_depreciation / self.annual_depreciation_flow

    @computed_field  # type: ignore[prop-decorator]
    @property
    def replacement_cycle_position(self) -> ReplacementCyclePosition:
        """Classify the replacement cycle based on fund adequacy ratio.

        Thresholds (from BEA Fixed Asset Tables):
            - > 1.5: INVESTMENT_BOOM (excess funds drive replacement wave)
            - > 1.0: EXPANSION (adequate for timely replacement)
            - > 0.7: MAINTENANCE (covers basics, no expansion)
            - <= 0.7: DISINVESTMENT (capital stock deteriorating)

        Returns:
            ReplacementCyclePosition enum value.
        """
        ratio = self.accumulated_depreciation / self.annual_depreciation_flow
        if ratio > REPLACEMENT_BOOM_RATIO:
            return ReplacementCyclePosition.INVESTMENT_BOOM
        if ratio > REPLACEMENT_EXPANSION_RATIO:
            return ReplacementCyclePosition.EXPANSION
        if ratio > REPLACEMENT_MAINTENANCE_RATIO:
            return ReplacementCyclePosition.MAINTENANCE
        return ReplacementCyclePosition.DISINVESTMENT


class MoralDepreciation(BaseModel):
    """Technological obsolescence factor for fixed capital.

    Marx's concept of 'moral depreciation': fixed capital loses value
    not through physical wear but through technological supersession.
    The economic life can be shorter than the physical life.

    Args:
        naics_code: NAICS industry code.
        physical_remaining_life: Years of physical service remaining.
        economic_remaining_life: Years of economic viability remaining.

    Example:
        >>> md = MoralDepreciation(
        ...     naics_code="334", physical_remaining_life=10.0,
        ...     economic_remaining_life=3.0,
        ... )
        >>> md.obsolescence_factor
        0.3
    """

    model_config = ConfigDict(frozen=True)

    naics_code: str = Field(..., description="NAICS industry code")
    physical_remaining_life: float = Field(
        ..., ge=0, description="Years of physical service remaining"
    )
    economic_remaining_life: float = Field(
        ..., ge=0, description="Years of economic viability remaining"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def obsolescence_factor(self) -> float:
        """Ratio of economic to physical remaining life.

        A factor of 1.0 means no moral depreciation (economic life equals
        physical life). A factor below 1.0 indicates technological
        obsolescence is shortening the asset's useful life.

        Returns:
            economic_remaining_life / physical_remaining_life,
            1.0 if physical_remaining_life <= 0.
        """
        if self.physical_remaining_life <= 0.0:
            return 1.0
        return self.economic_remaining_life / self.physical_remaining_life


class InventoryState(BaseModel):
    """Inventory levels and health diagnosis for a county-year.

    Tracks three categories of inventory (raw materials, work-in-progress,
    finished goods) along with days-of-inventory metrics to diagnose
    overproduction or supply crisis conditions.

    Args:
        fips_code: 5-digit county FIPS code.
        year: Calendar year.
        raw_materials: Value of raw materials inventory.
        work_in_progress: Value of work-in-progress inventory.
        finished_goods: Value of finished goods inventory.
        days_inventory_raw: Days of raw materials at current usage rate.
        days_inventory_finished: Days of finished goods at current sales rate.

    Example:
        >>> inv = InventoryState(
        ...     fips_code="26163", year=2015,
        ...     raw_materials=50000.0, work_in_progress=30000.0,
        ...     finished_goods=80000.0,
        ...     days_inventory_raw=15.0, days_inventory_finished=45.0,
        ... )
        >>> inv.total_inventory
        160000.0
        >>> inv.inventory_problem
        <InventoryDiagnosis.NORMAL: 'normal'>
    """

    model_config = ConfigDict(frozen=True)

    fips_code: str = Field(..., min_length=5, max_length=5, description="5-digit county FIPS code")
    year: int = Field(..., description="Calendar year")
    raw_materials: Currency = Field(..., description="Value of raw materials inventory")
    work_in_progress: Currency = Field(..., description="Value of work-in-progress inventory")
    finished_goods: Currency = Field(..., description="Value of finished goods inventory")
    days_inventory_raw: float = Field(
        ..., ge=0, description="Days of raw materials at current usage rate"
    )
    days_inventory_finished: float = Field(
        ..., ge=0, description="Days of finished goods at current sales rate"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_inventory(self) -> Currency:
        """Total inventory value across all categories.

        Returns:
            Sum of raw materials, work-in-progress, and finished goods.
        """
        return Currency(self.raw_materials + self.work_in_progress + self.finished_goods)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def inventory_problem(self) -> InventoryDiagnosis:
        """Diagnose inventory health based on days-of-inventory thresholds.

        Priority: supply crisis (raw < 7 days) takes precedence over
        overproduction (finished > 60 days), since inability to produce
        is more immediately disruptive than inability to sell.

        Returns:
            InventoryDiagnosis classification.
        """
        if self.days_inventory_raw < SUPPLY_CRISIS_DAYS_THRESHOLD:
            return InventoryDiagnosis.SUPPLY_CRISIS
        if self.days_inventory_finished > OVERPRODUCTION_DAYS_THRESHOLD:
            return InventoryDiagnosis.OVERPRODUCTION
        return InventoryDiagnosis.NORMAL


class ReproductionBalance(BaseModel):
    """Simple reproduction balance condition result.

    Records whether the balance condition between departments is met,
    the quantitative gap, and a human-readable interpretation.

    Args:
        condition_met: True if the reproduction balance holds.
        gap: Quantitative gap between supply and demand
            (positive = excess, negative = deficit).
        interpretation: Human-readable explanation of the balance state.

    Example:
        >>> balance = ReproductionBalance(
        ...     condition_met=True, gap=0.0,
        ...     interpretation="Simple reproduction balance holds.",
        ... )
    """

    model_config = ConfigDict(frozen=True)

    condition_met: bool = Field(..., description="True if the reproduction balance holds")
    gap: float = Field(..., description="Quantitative gap (positive=excess, negative=deficit)")
    interpretation: str = Field(..., description="Human-readable explanation of the balance state")


class ReproductionAnalysis(BaseModel):
    """Labor power reproduction capacity analysis.

    Assesses whether the economy produces sufficient means of subsistence
    to reproduce the labor power it employs, following Marx's reproduction
    schema analysis.

    Args:
        labor_power_demand: Total labor power demanded by capital.
        reproduction_capacity: Total reproduction capacity of Dept II output.
        gap: Difference (capacity - demand), negative = reproduction deficit.
        sustainability: True if reproduction capacity meets or exceeds demand.

    Example:
        >>> analysis = ReproductionAnalysis(
        ...     labor_power_demand=1000.0, reproduction_capacity=950.0,
        ...     gap=-50.0, sustainability=False,
        ... )
    """

    model_config = ConfigDict(frozen=True)

    labor_power_demand: float = Field(
        ..., ge=0, description="Total labor power demanded by capital"
    )
    reproduction_capacity: float = Field(
        ..., ge=0, description="Total reproduction capacity of Dept II output"
    )
    gap: float = Field(..., description="Capacity minus demand (negative = reproduction deficit)")
    sustainability: bool = Field(
        ..., description="True if reproduction capacity meets or exceeds demand"
    )


class RealizationCrisis(BaseModel):
    """Commodity realization gap assessment for a county-year.

    Measures the gap between commodity value produced and commodity value
    successfully realized (sold). A growing gap indicates effective demand
    is insufficient to absorb production.

    Args:
        fips_code: 5-digit county FIPS code.
        year: Calendar year.
        commodity_value_produced: Total value of commodities produced.
        commodity_value_realized: Total value actually sold/realized.

    Example:
        >>> crisis = RealizationCrisis(
        ...     fips_code="26163", year=2015,
        ...     commodity_value_produced=1000000.0,
        ...     commodity_value_realized=850000.0,
        ... )
        >>> crisis.realization_rate
        0.85
        >>> crisis.crisis_severity
        <CrisisSeverity.MILD_SLOWDOWN: 'mild_slowdown'>
    """

    model_config = ConfigDict(frozen=True)

    fips_code: str = Field(..., min_length=5, max_length=5, description="5-digit county FIPS code")
    year: int = Field(..., description="Calendar year")
    commodity_value_produced: Currency = Field(
        ..., gt=0, description="Total value of commodities produced"
    )
    commodity_value_realized: Currency = Field(
        ..., description="Total value actually sold/realized"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def realization_gap(self) -> Currency:
        """Absolute gap between produced and realized value.

        Returns:
            Produced minus realized (positive = unrealized surplus).
        """
        gap = self.commodity_value_produced - self.commodity_value_realized
        return Currency(max(0.0, gap))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def realization_rate(self) -> float:
        """Fraction of produced value successfully realized (sold).

        Returns:
            Realized / produced ratio.
        """
        return self.commodity_value_realized / self.commodity_value_produced

    @computed_field  # type: ignore[prop-decorator]
    @property
    def crisis_severity(self) -> CrisisSeverity:
        """Classify realization crisis severity based on realization rate.

        Thresholds (from NBER recession classification):
            - >= 0.95: NORMAL (healthy demand)
            - >= 0.85: MILD_SLOWDOWN (emerging demand deficiency)
            - >= 0.70: RECESSION (significant demand destruction)
            - < 0.70: CRISIS (systemic realization failure)

        Returns:
            CrisisSeverity enum value.
        """
        rate = self.commodity_value_realized / self.commodity_value_produced
        if rate >= REALIZATION_RATE_NORMAL:
            return CrisisSeverity.NORMAL
        if rate >= REALIZATION_RATE_SLOWDOWN:
            return CrisisSeverity.MILD_SLOWDOWN
        if rate >= REALIZATION_RATE_RECESSION:
            return CrisisSeverity.RECESSION
        return CrisisSeverity.CRISIS


class DisproportionalityCrisis(BaseModel):
    """Department I/II output imbalance assessment.

    Tracks the proportional balance between means-of-production output
    (Dept I) and means-of-consumption output (Dept II). Imbalance between
    departments creates crisis tendencies per Marx's reproduction schemas.

    Args:
        year: Calendar year.
        dept_i_output: Total output of Department I (means of production).
        dept_ii_output: Total output of Department II (means of consumption).
        dept_i_share_required: Theoretically required Dept I share for balanced
            reproduction.

    Example:
        >>> crisis = DisproportionalityCrisis(
        ...     year=2015, dept_i_output=600000.0, dept_ii_output=400000.0,
        ...     dept_i_share_required=0.55,
        ... )
        >>> crisis.actual_i_share
        0.6
        >>> crisis.imbalance_direction
        'over-industrialized'
    """

    model_config = ConfigDict(frozen=True)

    year: int = Field(..., description="Calendar year")
    dept_i_output: Currency = Field(
        ..., description="Total output of Department I (means of production)"
    )
    dept_ii_output: Currency = Field(
        ..., description="Total output of Department II (means of consumption)"
    )
    dept_i_share_required: float = Field(
        ...,
        ge=0,
        le=1,
        description="Required Dept I share for balanced reproduction",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def actual_i_share(self) -> float:
        """Actual Department I share of total output.

        Returns:
            Dept I output / (Dept I + Dept II), 0.0 if total is zero.
        """
        total = self.dept_i_output + self.dept_ii_output
        if total == 0.0:
            return 0.0
        return self.dept_i_output / total

    @computed_field  # type: ignore[prop-decorator]
    @property
    def imbalance(self) -> float:
        """Signed difference between actual and required Dept I share.

        Positive means Dept I is over-represented (over-industrialized).
        Negative means Dept I is under-represented (under-industrialized).

        Returns:
            actual_i_share - dept_i_share_required.
        """
        total = self.dept_i_output + self.dept_ii_output
        actual = 0.0 if total == 0.0 else self.dept_i_output / total
        return actual - self.dept_i_share_required

    @computed_field  # type: ignore[prop-decorator]
    @property
    def imbalance_direction(self) -> str:
        """Human-readable description of the imbalance direction.

        Returns:
            'over-industrialized', 'under-industrialized', or 'balanced'.
        """
        total = self.dept_i_output + self.dept_ii_output
        actual = 0.0 if total == 0.0 else self.dept_i_output / total
        diff = actual - self.dept_i_share_required
        if diff > 0.0:
            return "over-industrialized"
        if diff < 0.0:
            return "under-industrialized"
        return "balanced"


class PureCirculationCosts(BaseModel):
    """Faux frais de production: pure circulation costs that add no value.

    Marx distinguishes between costs that add value (transport, storage
    of use-values) and pure circulation costs that merely facilitate
    the change of ownership. These are unproductive from the standpoint
    of value creation but necessary for capital circulation.

    Args:
        fips_code: 5-digit county FIPS code.
        year: Calendar year.
        sales_labor: Wages of sales workers.
        accounting_labor: Wages of bookkeeping/accounting workers.
        marketing_labor: Wages of marketing/advertising workers.
        sales_facilities: Cost of retail/wholesale facilities.
        advertising_materials: Cost of advertising materials and media.
        transaction_costs: Financial transaction costs (banking, insurance overhead).

    Example:
        >>> costs = PureCirculationCosts(
        ...     fips_code="26163", year=2015,
        ...     sales_labor=50000.0, accounting_labor=40000.0,
        ...     marketing_labor=30000.0, sales_facilities=20000.0,
        ...     advertising_materials=15000.0, transaction_costs=10000.0,
        ... )
        >>> costs.total_pure_circulation
        165000.0
    """

    model_config = ConfigDict(frozen=True)

    fips_code: str = Field(..., min_length=5, max_length=5, description="5-digit county FIPS code")
    year: int = Field(..., description="Calendar year")
    sales_labor: Currency = Field(..., description="Wages of sales workers")
    accounting_labor: Currency = Field(..., description="Wages of bookkeeping/accounting workers")
    marketing_labor: Currency = Field(..., description="Wages of marketing/advertising workers")
    sales_facilities: Currency = Field(..., description="Cost of retail/wholesale facilities")
    advertising_materials: Currency = Field(
        ..., description="Cost of advertising materials and media"
    )
    transaction_costs: Currency = Field(
        ..., description="Financial transaction costs (banking, insurance overhead)"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_pure_circulation(self) -> Currency:
        """Total pure circulation costs (sum of all cost components).

        Returns:
            Sum of all six pure circulation cost categories.
        """
        return Currency(
            self.sales_labor
            + self.accounting_labor
            + self.marketing_labor
            + self.sales_facilities
            + self.advertising_materials
            + self.transaction_costs
        )

    def circulation_burden(self, total_revenue: Currency) -> float:
        """Compute circulation costs as a fraction of total revenue.

        Args:
            total_revenue: Total revenue to compare against.

        Returns:
            Pure circulation costs / total_revenue, 0.0 if revenue is zero.
        """
        if total_revenue == 0.0:
            return 0.0
        total_costs = (
            self.sales_labor
            + self.accounting_labor
            + self.marketing_labor
            + self.sales_facilities
            + self.advertising_materials
            + self.transaction_costs
        )
        return total_costs / total_revenue


class TransportationValue(BaseModel):
    """Transport as a value-adding industry per Marx Capital II Ch. 6.

    Unlike pure circulation costs, transportation adds real value to
    commodities by changing their spatial location (a real use-value).
    The transport industry has its own c, v, s decomposition.

    Args:
        origin_value: Value of the commodity at point of origin.
        transport_c: Constant capital consumed in transport (fuel, vehicle wear).
        transport_v: Variable capital in transport (transport workers' wages).
        transport_s: Surplus value generated in transport.

    Example:
        >>> tv = TransportationValue(
        ...     origin_value=10000.0, transport_c=200.0,
        ...     transport_v=300.0, transport_s=150.0,
        ... )
        >>> tv.destination_value
        10650.0
    """

    model_config = ConfigDict(frozen=True)

    origin_value: Currency = Field(..., description="Value of the commodity at point of origin")
    transport_c: Currency = Field(
        ..., description="Constant capital consumed in transport (fuel, vehicle wear)"
    )
    transport_v: Currency = Field(
        ..., description="Variable capital in transport (transport workers' wages)"
    )
    transport_s: Currency = Field(..., description="Surplus value generated in transport")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def value_added(self) -> Currency:
        """Value added by transportation (c + v + s).

        Returns:
            Sum of transport constant capital, variable capital, and surplus value.
        """
        return Currency(self.transport_c + self.transport_v + self.transport_s)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def destination_value(self) -> Currency:
        """Total value of commodity at destination (origin + value added).

        Returns:
            Origin value plus transport value added.
        """
        added = self.transport_c + self.transport_v + self.transport_s
        return Currency(self.origin_value + added)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def transport_value_ratio(self) -> float:
        """Transport value added as fraction of destination value.

        Returns:
            Value added / destination value, 0.0 if destination value is zero.
        """
        added = self.transport_c + self.transport_v + self.transport_s
        destination = self.origin_value + added
        if destination == 0.0:
            return 0.0
        return added / destination


class CirculationCrisisAssessment(BaseModel):
    """Multi-dimensional crisis flag assessment for a county-year.

    Aggregates boolean flags for different types of circulation crises
    and a list of specific vulnerability descriptions.

    Args:
        fips_code: 5-digit county FIPS code.
        year: Calendar year.
        realization_crisis: True if realization gap exceeds threshold.
        turnover_crisis: True if turnover time is critically extended.
        reproduction_crisis: True if reproduction balance is violated.
        vulnerabilities: List of specific vulnerability descriptions.

    Example:
        >>> assessment = CirculationCrisisAssessment(
        ...     fips_code="26163", year=2015,
        ...     realization_crisis=True, turnover_crisis=False,
        ...     reproduction_crisis=False,
        ...     vulnerabilities=["Realization rate below 85%"],
        ... )
    """

    model_config = ConfigDict(frozen=True)

    fips_code: str = Field(..., min_length=5, max_length=5, description="5-digit county FIPS code")
    year: int = Field(..., description="Calendar year")
    realization_crisis: bool = Field(
        default=False, description="True if realization gap exceeds threshold"
    )
    turnover_crisis: bool = Field(
        default=False, description="True if turnover time is critically extended"
    )
    reproduction_crisis: bool = Field(
        default=False, description="True if reproduction balance is violated"
    )
    vulnerabilities: list[str] = Field(
        default_factory=list, description="List of specific vulnerability descriptions"
    )


class CirculationCrisisState(BaseModel):
    """Composite per-county circulation state for the simulation pipeline.

    Bundles the core circuit state, inventory state, depreciation fund,
    and latest crisis assessment into a single object for the tick
    dynamics system to consume.

    Args:
        circuit_state: Capital composition across the three circuit forms.
        inventory_state: Inventory levels and health diagnosis.
        depreciation_fund: Depreciation fund adequacy and replacement cycle.
        latest_assessment: Most recent crisis assessment (None if not yet evaluated).

    Example:
        >>> state = CirculationCrisisState.initial("26163", 2015)
        >>> state.circuit_state.total_capital
        0.0
    """

    model_config = ConfigDict(frozen=True)

    circuit_state: CircuitState = Field(
        ..., description="Capital composition across the three circuit forms"
    )
    inventory_state: InventoryState = Field(
        ..., description="Inventory levels and health diagnosis"
    )
    depreciation_fund: DepreciationFundState = Field(
        ..., description="Depreciation fund adequacy and replacement cycle"
    )
    latest_assessment: CirculationCrisisAssessment | None = Field(
        default=None, description="Most recent crisis assessment"
    )

    @classmethod
    def initial(cls, fips: str, year: int) -> CirculationCrisisState:
        """Factory for a zeroed initial state.

        Creates a CirculationCrisisState with all monetary values at zero
        and neutral diagnostics. Suitable for initializing a new county
        before census data is loaded.

        Args:
            fips: 5-digit county FIPS code.
            year: Calendar year.

        Returns:
            CirculationCrisisState with zeroed sub-models.
        """
        circuit = CircuitState(
            fips_code=fips,
            year=year,
            money_capital=0.0,
            productive_capital=0.0,
            commodity_capital=0.0,
            fixed_capital=0.0,
            circulating_capital=0.0,
        )
        inventory = InventoryState(
            fips_code=fips,
            year=year,
            raw_materials=0.0,
            work_in_progress=0.0,
            finished_goods=0.0,
            days_inventory_raw=30.0,
            days_inventory_finished=30.0,
        )
        depreciation = DepreciationFundState(
            fips_code=fips,
            year=year,
            total_fixed_capital=0.0,
            accumulated_depreciation=1.0,
            annual_depreciation_flow=1.0,
            replacement_expenditure=0.0,
        )
        return cls(
            circuit_state=circuit,
            inventory_state=inventory,
            depreciation_fund=depreciation,
            latest_assessment=None,
        )


__all__ = [
    "AnnualSurplusValue",
    "CapitalForm",
    "CircuitState",
    "CirculationCrisisAssessment",
    "CirculationCrisisState",
    "COMMODITY_OVERHANG_CRISIS",
    "CrisisSeverity",
    "DepreciationFundState",
    "DisproportionalityCrisis",
    "FixedCapitalItem",
    "InventoryDiagnosis",
    "InventoryState",
    "LIQUIDITY_CRISIS_RATIO",
    "MoralDepreciation",
    "OVERPRODUCTION_DAYS_THRESHOLD",
    "PureCirculationCosts",
    "REALIZATION_RATE_NORMAL",
    "REALIZATION_RATE_RECESSION",
    "REALIZATION_RATE_SLOWDOWN",
    "RealizationCrisis",
    "REPLACEMENT_BOOM_RATIO",
    "REPLACEMENT_EXPANSION_RATIO",
    "REPLACEMENT_MAINTENANCE_RATIO",
    "ReplacementCyclePosition",
    "ReproductionAnalysis",
    "ReproductionBalance",
    "SUPPLY_CRISIS_DAYS_THRESHOLD",
    "TransportationValue",
    "TurnoverProfile",
]
