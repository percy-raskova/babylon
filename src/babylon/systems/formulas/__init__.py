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

# Re-export constants
from babylon.systems.formulas.constants import (
    EPSILON,
    LOSS_AVERSION_COEFFICIENT,
)

# Re-export Dynamic Balance formulas
from babylon.systems.formulas.dynamic_balance import (
    BourgeoisieDecision,
    calculate_bourgeoisie_decision,
)

# Re-export Fundamental Theorem formulas
from babylon.systems.formulas.fundamental_theorem import (
    calculate_consciousness_drift,
    calculate_imperial_rent,
    calculate_labor_aristocracy_ratio,
    is_labor_aristocracy,
)

# Re-export Ideological Routing formula
from babylon.systems.formulas.ideological_routing import calculate_ideological_routing

# Re-export Metabolic Rift formulas
from babylon.systems.formulas.metabolic_rift import (
    calculate_biocapacity_delta,
    calculate_overshoot_ratio,
)

# Re-export Solidarity Transmission formula
from babylon.systems.formulas.solidarity import calculate_solidarity_transmission

# Re-export Survival Calculus formulas
from babylon.systems.formulas.survival_calculus import (
    apply_loss_aversion,
    calculate_acquiescence_probability,
    calculate_crossover_threshold,
    calculate_revolution_probability,
)

# Re-export TRPF formulas (Marx, Capital Vol. 3)
from babylon.systems.formulas.trpf import (
    calculate_organic_composition,
    calculate_rate_of_profit,
    calculate_rent_pool_decay,
    calculate_trpf_multiplier,
)

# Re-export Unequal Exchange formulas
from babylon.systems.formulas.unequal_exchange import (
    calculate_exchange_ratio,
    calculate_exploitation_rate,
    calculate_value_transfer,
    prebisch_singer_effect,
)

__all__ = [
    # Constants
    "LOSS_AVERSION_COEFFICIENT",
    "EPSILON",
    # Fundamental Theorem
    "calculate_imperial_rent",
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
    "calculate_exploitation_rate",
    "calculate_value_transfer",
    "prebisch_singer_effect",
    # Solidarity Transmission
    "calculate_solidarity_transmission",
    # Ideological Routing
    "calculate_ideological_routing",
    # Dynamic Balance
    "BourgeoisieDecision",
    "calculate_bourgeoisie_decision",
    # Metabolic Rift
    "calculate_biocapacity_delta",
    "calculate_overshoot_ratio",
    # TRPF (Marx, Capital Vol. 3)
    "calculate_organic_composition",
    "calculate_rate_of_profit",
    "calculate_rent_pool_decay",
    "calculate_trpf_multiplier",
]
