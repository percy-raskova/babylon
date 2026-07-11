"""Mathematical formulas for the Babylon simulation.

This module contains the pure mathematical functions that drive
the dialectical mechanics of the simulation. These are deterministic
functions with no side effects - the same inputs always produce
the same outputs.

Key Formulas:
1. Fundamental Theorem of MLM-TW:
   - Imperial Rent: Phi(Wp, Psip) = alpha * Wp * (1 - Psip)
   - Labor Aristocracy: Wc/Vc > 1
   - Consciousness Drift: dPsic/dt = k(1 - Wc/Vc) - lambda*Psic

2. Survival Calculus:
   - Acquiescence: P(S|A) = 1 / (1 + e^(-k(x - x_critical)))
   - Revolution: P(S|R) = Cohesion / (Repression + epsilon)
   - Loss Aversion: lambda = 2.25

3. Unequal Exchange:
   - Exchange Ratio: epsilon = (Lp/Lc) * (Wc/Wp)
   - Prebisch-Singer Effect
"""

from babylon.config.defines import GameDefines as _GameDefines

# Re-export Balkanization formulas (Spec 070)
from babylon.formulas.balkanization import (
    calculate_metabolic_impact,
    contiguous_influence_majority_subregion,
    derive_default_multipliers_from_stance,
    derive_extraction_policy_from_stance,
    detect_red_settler_trap,
    extrapolate_habitability,
    winning_faction_for_territory,
)

# Re-export Class Dynamics formulas (FRED DFA-derived)
from babylon.formulas.class_dynamics import (
    ClassDynamicsParams,
    SecondOrderParams,
    calculate_class_dynamics_derivative,
    calculate_equilibrium_deviation,
    calculate_full_dynamics,
    calculate_wealth_acceleration,
    calculate_wealth_flow,
    invert_wealth_to_population,
)

# Re-export Community Layer formulas (Feature 022)
from babylon.formulas.community import (
    calculate_infrastructure_decay,
    calculate_solidarity_amplification,
    calculate_solidarity_potential,
    calculate_threat_score,
    compute_community_cost_modifier,
)

# Re-export Consciousness Computation (Feature 034)
from babylon.formulas.consciousness import compute_ternary_consciousness

# Re-export Consciousness Routing (Spec 043 - Value Transparency)
from babylon.formulas.consciousness_routing import (
    compute_agitation_delta,
    compute_exploitation_visibility,
    compute_reification_buffer,
    normalize_to_simplex,
    route_agitation_to_ternary,
)

# Re-export Contradiction formulas (Feature 002 + Lawverian Phase C)
from babylon.formulas.contradiction import (
    calculate_contradiction_intensity,
    calculate_wealth_asymmetry_balance,
    calculate_wealth_asymmetry_gap,
)

# Re-export Curvature formulas (Feature 002 - Dialectical Field Topology)
from babylon.formulas.curvature import compute_ollivier_ricci

# Re-export Dynamic Balance formulas
from babylon.formulas.dynamic_balance import (
    BourgeoisieDecision,
    calculate_bourgeoisie_decision,
)

# Re-export Fundamental Theorem formulas
from babylon.formulas.fundamental_theorem import (
    calculate_consciousness_drift,
    calculate_labor_aristocracy_ratio,
    is_labor_aristocracy,
)

# Re-export D-P-D' Lifecycle Circuit formulas (Feature 030)
from babylon.formulas.lifecycle import (
    compute_dependency_ratio,
    compute_ideology_transmission,
    compute_legitimation_index,
    compute_pareto_gini,
    compute_population_flow,
    compute_shadow_subsidy,
)

# Re-export Metabolic Rift formulas
from babylon.formulas.metabolic_rift import (
    calculate_biocapacity_delta,
    calculate_overshoot_ratio,
)

# Re-export Reactionary Subject formulas (spec-071)
from babylon.formulas.reactionary import (
    calculate_defection_probability,
    calculate_entitlement_effective,
    calculate_fascist_pull,
    calculate_spontaneous_riot_risk,
)

# Re-export Solidarity Transmission formula
from babylon.formulas.solidarity import calculate_solidarity_transmission

# Re-export Survival Calculus formulas
from babylon.formulas.survival_calculus import (
    apply_loss_aversion,
    calculate_acquiescence_probability,
    calculate_crossover_threshold,
    calculate_revolution_probability,
)

# Re-export TRPF formulas (Marx, Capital Vol. 3)
from babylon.formulas.trpf import (
    calculate_rent_pool_decay,
    calculate_trpf_multiplier,
)

# Re-export Unequal Exchange formulas
from babylon.formulas.unequal_exchange import (
    calculate_exchange_ratio,
    calculate_unequal_exchange_rate,
    calculate_value_transfer,
    prebisch_singer_effect,
)

# Re-export Vitality formulas (Mass Line Refactor)
from babylon.formulas.vitality import calculate_mortality_rate

# Canonical constant re-exports from GameDefines
_DEFINES = _GameDefines()
EPSILON = _DEFINES.precision.epsilon
LOSS_AVERSION_COEFFICIENT = _DEFINES.behavioral.loss_aversion_lambda

__all__ = [
    # Constants
    "LOSS_AVERSION_COEFFICIENT",
    "EPSILON",
    # Fundamental Theorem
    "calculate_labor_aristocracy_ratio",
    "is_labor_aristocracy",
    "calculate_consciousness_drift",
    # Survival Calculus
    "calculate_acquiescence_probability",
    "calculate_revolution_probability",
    "calculate_crossover_threshold",
    "apply_loss_aversion",
    # Unequal Exchange
    "calculate_exchange_ratio",
    "calculate_unequal_exchange_rate",
    "calculate_value_transfer",
    "prebisch_singer_effect",
    # Solidarity Transmission
    "calculate_solidarity_transmission",
    # Consciousness Routing (Spec 043)
    "compute_agitation_delta",
    "compute_exploitation_visibility",
    "compute_reification_buffer",
    "route_agitation_to_ternary",
    "normalize_to_simplex",
    # Dynamic Balance
    "BourgeoisieDecision",
    "calculate_bourgeoisie_decision",
    # Metabolic Rift
    "calculate_biocapacity_delta",
    "calculate_overshoot_ratio",
    # TRPF (Marx, Capital Vol. 3)
    "calculate_rent_pool_decay",
    "calculate_trpf_multiplier",
    # Vitality (Mass Line Refactor)
    "calculate_mortality_rate",
    # Class Dynamics (FRED DFA-derived)
    "ClassDynamicsParams",
    "SecondOrderParams",
    "calculate_class_dynamics_derivative",
    "calculate_equilibrium_deviation",
    "calculate_full_dynamics",
    "calculate_wealth_acceleration",
    "calculate_wealth_flow",
    "invert_wealth_to_population",
    # Curvature & Contradictions (Dialectical Field Topology)
    "compute_ollivier_ricci",
    "calculate_contradiction_intensity",
    "calculate_wealth_asymmetry_balance",
    "calculate_wealth_asymmetry_gap",
    # Consciousness Computation (Feature 034)
    "compute_ternary_consciousness",
    # Community Layer (Feature 022)
    "calculate_solidarity_potential",
    "calculate_threat_score",
    "calculate_infrastructure_decay",
    "calculate_solidarity_amplification",
    "compute_community_cost_modifier",
    # D-P-D' Lifecycle Circuit (Feature 030)
    "compute_population_flow",
    "compute_dependency_ratio",
    "compute_legitimation_index",
    "compute_pareto_gini",
    "compute_ideology_transmission",
    "compute_shadow_subsidy",
    # Reactionary Subject (Spec 071)
    "calculate_defection_probability",
    "calculate_entitlement_effective",
    "calculate_fascist_pull",
    "calculate_spontaneous_riot_risk",
    # Balkanization (Spec 070)
    "calculate_metabolic_impact",
    "contiguous_influence_majority_subregion",
    "derive_default_multipliers_from_stance",
    "derive_extraction_policy_from_stance",
    "detect_red_settler_trap",
    "extrapolate_habitability",
    "winning_faction_for_territory",
]
