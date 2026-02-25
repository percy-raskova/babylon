"""Integrated circulation crisis detection per Marx Capital II.

Feature: 023-capital-volume-ii
User Story: US7 - Integrated Crisis Detection (FR-021, FR-022)

Detects three independent crisis types from Volume II:
    1. **Realization crisis**: Commodity overhang exceeds threshold (C'-M' stall)
    2. **Turnover crisis**: Low liquidity combined with slow circulation
    3. **Reproduction crisis**: Departmental balance violated or unsustainable

Each crisis type is assessed independently; multiple crises can be active
simultaneously. Vulnerability strings provide specific diagnostic labels
for downstream systems.

See Also:
    :class:`babylon.economics.circulation.types.CirculationCrisisAssessment`: Result model
    :mod:`babylon.economics.circulation.inventory`: Realization metrics
"""

from __future__ import annotations

from babylon.economics.circulation.types import (
    COMMODITY_OVERHANG_CRISIS,
    LIQUIDITY_CRISIS_RATIO,
    CircuitState,
    CirculationCrisisAssessment,
    InventoryDiagnosis,
    InventoryState,
    ReproductionAnalysis,
    ReproductionBalance,
    TurnoverProfile,
)

# =============================================================================
# Vulnerability label constants
# =============================================================================

_VULN_REALIZATION_CRISIS = "REALIZATION_CRISIS"
_VULN_SUPPLY_CHAIN_CRISIS = "SUPPLY_CHAIN_CRISIS"
_VULN_LABOR_SHORTAGE = "LABOR_SHORTAGE"
_VULN_MONETARY_CRISIS = "MONETARY_CRISIS"


def assess_circulation_crisis(
    circuit_state: CircuitState,
    turnover: TurnoverProfile,
    inventory: InventoryState,
    reproduction_balance: ReproductionBalance,
    reproduction_analysis: ReproductionAnalysis,
) -> CirculationCrisisAssessment:
    """Detect all Volume II crisis types independently.

    Evaluates three crisis dimensions from the circulation of capital:

    1. **Realization crisis**: commodity_overhang > 0.3 means the C'-M'
       phase is stalling (commodities cannot be converted back to money).
    2. **Turnover crisis**: liquidity_ratio < 0.1 AND circulation_time >
       production_time means capital is stuck AND turning slowly.
    3. **Reproduction crisis**: departmental balance not met OR labor
       reproduction unsustainable.

    Each crisis is assessed independently. Vulnerability strings are
    generated for specific conditions that may not map 1:1 to the
    three boolean flags.

    Args:
        circuit_state: Capital composition across the three circuit forms.
        turnover: Sectoral turnover time decomposition.
        inventory: Inventory levels and health diagnosis.
        reproduction_balance: Simple reproduction balance condition.
        reproduction_analysis: Labor power reproduction capacity.

    Returns:
        CirculationCrisisAssessment with boolean flags and vulnerability list.
    """
    # --- Realization crisis ---
    realization_crisis = circuit_state.commodity_overhang > COMMODITY_OVERHANG_CRISIS

    # --- Turnover crisis ---
    low_liquidity = circuit_state.liquidity_ratio < LIQUIDITY_CRISIS_RATIO
    slow_circulation = turnover.circulation_time > turnover.production_time
    turnover_crisis = low_liquidity and slow_circulation

    # --- Reproduction crisis ---
    reproduction_crisis = (
        not reproduction_balance.condition_met or not reproduction_analysis.sustainability
    )

    # --- Vulnerability strings ---
    vulnerabilities: list[str] = []

    if circuit_state.commodity_overhang > COMMODITY_OVERHANG_CRISIS:
        vulnerabilities.append(_VULN_REALIZATION_CRISIS)

    if inventory.inventory_problem == InventoryDiagnosis.SUPPLY_CRISIS:
        vulnerabilities.append(_VULN_SUPPLY_CHAIN_CRISIS)

    if not reproduction_analysis.sustainability:
        vulnerabilities.append(_VULN_LABOR_SHORTAGE)

    if circuit_state.liquidity_ratio < LIQUIDITY_CRISIS_RATIO:
        vulnerabilities.append(_VULN_MONETARY_CRISIS)

    return CirculationCrisisAssessment(
        fips_code=circuit_state.fips_code,
        year=circuit_state.year,
        realization_crisis=realization_crisis,
        turnover_crisis=turnover_crisis,
        reproduction_crisis=reproduction_crisis,
        vulnerabilities=vulnerabilities,
    )


__all__ = [
    "assess_circulation_crisis",
]
