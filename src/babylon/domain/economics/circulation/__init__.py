"""Capital Volume II: Circulation of Capital.

Feature: 023-capital-volume-ii

Models capital as a process (M-C-P-C'-M') rather than a static snapshot.
Adds turnover time, fixed/circulating capital decomposition, reproduction
schema balance conditions, inventory/realization tracking, circulation
costs classification, and integrated crisis detection.

See Also:
    :mod:`babylon.domain.economics.tensor`: ValueTensor4x3 (Volume I production)
    :mod:`babylon.domain.economics.tick`: TickDynamicsSystem pipeline integration
    :mod:`babylon.domain.economics.crisis`: TRPF crisis mechanics (Feature 018)
"""

from babylon.domain.economics.circulation.circuit import (
    advance_circuit,
    initialize_circuit_state,
)
from babylon.domain.economics.circulation.costs import (
    LaborClassification,
    classify_labor,
)
from babylon.domain.economics.circulation.crisis import (
    assess_circulation_crisis,
)
from babylon.domain.economics.circulation.fixed_circulating import (
    compute_moral_depreciation,
    decompose_constant_capital,
    update_depreciation_fund,
)
from babylon.domain.economics.circulation.inventory import (
    compute_realization_metrics,
    detect_realization_crisis,
)
from babylon.domain.economics.circulation.reproduction import (
    check_extended_reproduction,
    check_simple_reproduction,
    combine_departments_ii,
    compute_disproportionality,
)
from babylon.domain.economics.circulation.turnover import (
    DefaultTurnoverProfileSource,
    TurnoverProfileSource,
    compare_turnover_advantage,
    compute_annual_surplus_value,
    get_weighted_turnover_profile,
)

__all__ = [
    # US1: Circuit State
    "advance_circuit",
    "initialize_circuit_state",
    # US2: Turnover & Annual Surplus
    "DefaultTurnoverProfileSource",
    "TurnoverProfileSource",
    "compare_turnover_advantage",
    "compute_annual_surplus_value",
    "get_weighted_turnover_profile",
    # US3: Fixed/Circulating Capital
    "compute_moral_depreciation",
    "decompose_constant_capital",
    "update_depreciation_fund",
    # US4: Reproduction Schema
    "check_extended_reproduction",
    "check_simple_reproduction",
    "combine_departments_ii",
    "compute_disproportionality",
    # US5: Inventory & Realization
    "compute_realization_metrics",
    "detect_realization_crisis",
    # US6: Circulation Costs
    "LaborClassification",
    "classify_labor",
    # US7: Integrated Crisis Detection
    "assess_circulation_crisis",
]
