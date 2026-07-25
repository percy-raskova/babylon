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
    :class:`babylon.domain.economics.circulation.types.CirculationCrisisAssessment`: Result model
    :mod:`babylon.domain.economics.circulation.inventory`: Realization metrics
"""

from __future__ import annotations

from babylon.domain.economics.circulation.types import (
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
    reproduction_balance: ReproductionBalance | None,
    reproduction_analysis: ReproductionAnalysis | None,
    commodity_overhang_threshold: float = 0.3,
    liquidity_crisis_ratio: float = 0.1,
) -> CirculationCrisisAssessment:
    """Detect all Volume II crisis types independently.

    Evaluates three crisis dimensions from the circulation of capital:

    1. **Realization crisis**: commodity_overhang > commodity_overhang_threshold
       means the C'-M' phase is stalling (commodities cannot be converted
       back to money).
    2. **Turnover crisis**: liquidity_ratio < liquidity_crisis_ratio AND
       circulation_time > production_time means capital is stuck AND
       turning slowly.
    3. **Reproduction crisis**: departmental balance not met OR labor
       reproduction unsustainable — ``None`` (unknown), never a fabricated
       ``False``, when the underlying department data is absent for this
       county-year (Constitution III.11; U3 code-review fix). Realization
       and turnover crisis detection are independent of reproduction data
       and are still computed even when reproduction inputs are ``None``.

    Each crisis is assessed independently. Vulnerability strings are
    generated for specific conditions that may not map 1:1 to the
    three boolean flags.

    Args:
        circuit_state: Capital composition across the three circuit forms.
        turnover: Sectoral turnover time decomposition.
        inventory: Inventory levels and health diagnosis.
        reproduction_balance: Simple reproduction balance condition, or
            ``None`` when no department data is available this county-year.
        reproduction_analysis: Labor power reproduction capacity, or
            ``None`` when no department data is available this county-year.
        commodity_overhang_threshold: Commodity-capital share above which
            the realization phase is diagnosed as stalling (default 0.3,
            matching the original hardcoded threshold; production callers
            should pass ``defines.capital_vol2.commodity_overhang_threshold``
            — U7 defines sweep, 2026-07-21 vol2-circulation-engine program).
        liquidity_crisis_ratio: Money-capital share below which a
            liquidity crisis is diagnosed (default 0.1, matching the
            original hardcoded threshold; production callers should pass
            ``defines.capital_vol2.liquidity_crisis_ratio`` — U7 defines
            sweep).

    Returns:
        CirculationCrisisAssessment with boolean (or, for
        ``reproduction_crisis``, optional-boolean) flags and a
        vulnerability list.
    """
    # --- Realization crisis ---
    realization_crisis = circuit_state.commodity_overhang > commodity_overhang_threshold

    # --- Turnover crisis ---
    low_liquidity = circuit_state.liquidity_ratio < liquidity_crisis_ratio
    slow_circulation = turnover.circulation_time > turnover.production_time
    turnover_crisis = low_liquidity and slow_circulation

    # --- Reproduction crisis ---
    # None (unknown) rather than a fabricated False when either input is
    # absent — mirrors the sibling DisproportionalityCrisis | None field on
    # CirculationCrisisState (U3 code-review fix: a positive
    # ReproductionBalance/Analysis placeholder here used to silently
    # suppress this flag instead of leaving it honestly unknown).
    reproduction_crisis: bool | None
    if reproduction_balance is None or reproduction_analysis is None:
        reproduction_crisis = None
    else:
        reproduction_crisis = (
            not reproduction_balance.condition_met or not reproduction_analysis.sustainability
        )

    # --- Vulnerability strings ---
    vulnerabilities: list[str] = []

    if circuit_state.commodity_overhang > commodity_overhang_threshold:
        vulnerabilities.append(_VULN_REALIZATION_CRISIS)

    if inventory.inventory_problem == InventoryDiagnosis.SUPPLY_CRISIS:
        vulnerabilities.append(_VULN_SUPPLY_CHAIN_CRISIS)

    if reproduction_analysis is not None and not reproduction_analysis.sustainability:
        vulnerabilities.append(_VULN_LABOR_SHORTAGE)

    if circuit_state.liquidity_ratio < liquidity_crisis_ratio:
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
