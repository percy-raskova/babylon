"""Contract definitions for Capital Volume II circulation formulas.

These are the function signatures and type contracts that the implementation
must satisfy. Each function maps to one or more functional requirements (FR-xxx).

Not executable code — serves as the API contract between spec and implementation.
"""

from __future__ import annotations

from typing import Protocol

# --- Types referenced (from existing codebase + new) ---
# Currency: from babylon.models.types (existing)
# LaborHours: from babylon.models.types (existing)
# DepartmentRow: from babylon.economics.tensor (existing)
# CircuitState: from babylon.economics.circulation.types (new)
# TurnoverProfile: from babylon.economics.circulation.types (new)
# InventoryState: from babylon.economics.circulation.types (new)
# DepreciationFundState: from babylon.economics.circulation.types (new)
# ReproductionBalance: from babylon.economics.circulation.types (new)
# ReproductionAnalysis: from babylon.economics.circulation.types (new)
# RealizationCrisis: from babylon.economics.circulation.types (new)
# DisproportionalityCrisis: from babylon.economics.circulation.types (new)
# CirculationCrisisAssessment: from babylon.economics.circulation.types (new)
# AnnualSurplusValue: from babylon.economics.circulation.types (new)
# PureCirculationCosts: from babylon.economics.circulation.types (new)
# TransportationValue: from babylon.economics.circulation.types (new)
# MoralDepreciation: from babylon.economics.circulation.types (new)


# ============================================================
# FR-001 to FR-003: Circuit State & Form Transitions
# ============================================================

# FR-002: Circuit state transition (pure function)
# def advance_circuit(
#     state: CircuitState,
#     turnover: TurnoverProfile,
#     surplus_value: Currency,
#     elapsed_days: int,
# ) -> CircuitState:
#     """Advance capital through circuit phases based on elapsed time."""
#     ...

# FR-003: Diagnostic ratios (computed fields on CircuitState)
# CircuitState.liquidity_ratio -> float  (M / total, 0.0 if total=0)
# CircuitState.commodity_overhang -> float  (C / total, 0.0 if total=0)


# ============================================================
# FR-004 to FR-007: Turnover Time & Annual Surplus Value
# ============================================================

# FR-004, FR-005: Turnover decomposition (computed fields on TurnoverProfile)
# TurnoverProfile.production_time -> int
# TurnoverProfile.circulation_time -> int
# TurnoverProfile.turnover_time -> int
# TurnoverProfile.turnovers_per_year -> float  (0.0 if turnover_time=0)

# FR-006: Annual surplus value computation (pure function)
# def compute_annual_surplus_value(
#     variable_capital: Currency,
#     surplus_per_cycle: Currency,
#     turnover_time_days: int,
# ) -> AnnualSurplusValue:
#     """Compute annual surplus value amplified by turnover speed."""
#     ...

# FR-007: Industry-level turnover profile resolution
# class TurnoverProfileSource(Protocol):
#     def get_turnover_profile(self, naics_code: str) -> TurnoverProfile | None:
#         """Resolve turnover profile for a given industry."""
#         ...


# ============================================================
# FR-008 to FR-011: Fixed vs Circulating Capital
# ============================================================

# FR-008: Decompose c into fixed and circulating
# def decompose_constant_capital(
#     total_c: Currency,
#     fixed_capital_ratio: float,
# ) -> tuple[Currency, Currency]:
#     """Split constant capital into (fixed, circulating) portions."""
#     ...

# FR-009: Straight-line depreciation (computed field on FixedCapitalItem)
# annual_depreciation = initial_value / service_life_years

# FR-010: Depreciation fund tracking
# def update_depreciation_fund(
#     previous: DepreciationFundState,
#     annual_depreciation: Currency,
#     replacement_expenditure: Currency,
# ) -> DepreciationFundState:
#     """Update depreciation fund state for one period."""
#     ...

# FR-011: Moral depreciation
# MoralDepreciation.obsolescence_factor -> float


# ============================================================
# FR-012 to FR-014: Reproduction Schemata
# ============================================================

# FR-012: Simple reproduction condition
# def check_simple_reproduction(
#     dept_i: DepartmentRow,
#     dept_ii: DepartmentRow,  # Combined IIa + IIb
#     tolerance: float = 0.01,
# ) -> ReproductionBalance:
#     """Check I(v+s) = IIc condition."""
#     ...

# FR-013: Extended reproduction with Dept III
# def check_extended_reproduction(
#     dept_i: DepartmentRow,
#     dept_ii: DepartmentRow,
#     dept_iii: DepartmentRow,
# ) -> ReproductionAnalysis:
#     """Check if Dept III can reproduce all departments' labor power."""
#     ...

# FR-014: Disproportionality metrics
# def compute_disproportionality(
#     dept_i_output: Currency,
#     dept_ii_output: Currency,
#     dept_i_share_required: float,
# ) -> DisproportionalityCrisis:
#     """Compute department output imbalance metrics."""
#     ...


# ============================================================
# FR-015 to FR-017: Inventory & Realization
# ============================================================

# FR-015: Inventory diagnosis (computed field on InventoryState)
# InventoryState.inventory_problem -> str

# FR-016: Realization metrics
# def compute_realization_metrics(
#     value_produced: Currency,
#     value_realized: Currency,
#     fips_code: str,
#     year: int,
# ) -> RealizationCrisis:
#     """Compute realization gap, rate, and severity."""
#     ...

# FR-017: Realization crisis detection from time series
# def detect_realization_crisis(
#     inventory_trend: list[InventoryState],
#     production_trend: list[Currency],
# ) -> bool:
#     """Rising inventory + flat/falling production = realization crisis."""
#     ...


# ============================================================
# FR-018 to FR-020: Circulation Costs
# ============================================================

# FR-018, FR-019: Pure circulation costs (computed fields on PureCirculationCosts)
# PureCirculationCosts.total_pure_circulation -> Currency
# PureCirculationCosts.circulation_burden(revenue) -> float

# FR-020: Transportation value (computed fields on TransportationValue)
# TransportationValue.value_added -> Currency
# TransportationValue.destination_value -> Currency
# TransportationValue.transport_value_ratio -> float


# ============================================================
# FR-021, FR-022: Integrated Crisis Detection
# ============================================================

# FR-021: Integrated assessment
# def assess_circulation_crisis(
#     circuit_state: CircuitState,
#     turnover: TurnoverProfile,
#     inventory: InventoryState,
#     reproduction_balance: ReproductionBalance,
#     reproduction_analysis: ReproductionAnalysis,
# ) -> CirculationCrisisAssessment:
#     """Detect all Volume II crisis types independently.
#
#     Vulnerability derivation:
#       - REALIZATION_CRISIS: circuit_state.commodity_overhang > 0.3
#       - SUPPLY_CHAIN_CRISIS: inventory.inventory_problem == SUPPLY_CRISIS
#       - LABOR_SHORTAGE: reproduction_analysis.sustainability == False
#       - MONETARY_CRISIS: circuit_state.liquidity_ratio < 0.1
#     """
#     ...

# FR-022: Complementary to TRPF (architectural constraint, not a function)
# CirculationCrisisAssessment stored alongside CrisisState (TRPF)
# in CountyEconomicState. Both run independently.
