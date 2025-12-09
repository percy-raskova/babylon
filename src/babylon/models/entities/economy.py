"""GlobalEconomy entity model for Sprint 3.4.4: Dynamic Balance.

GlobalEconomy tracks the system-wide economic state that enables
dynamic bourgeois decision-making. This is the "Gas Tank" that
forces scarcity and agency into the simulation.

Key insight: Without finite resources, the bourgeoisie can pay
infinite super-wages and the simulation stalls at equilibrium.
The imperial rent pool depletes as wages and subsidies are paid,
forcing strategic decisions.

Components:
- imperial_rent_pool: Accumulated rent from TRIBUTE edges (the Gas Tank)
- current_super_wage_rate: Dynamic wage rate [min_wage_rate, max_wage_rate]
- current_repression_level: System-wide repression modifier

Design decisions (Sprint 3.4.4):
- Pool fed by post-tribute (what Core Bourgeoisie receives after comprador cut)
- Aggressive thresholds: high=0.7, low=0.3, critical=0.1
- Repression as separate modifier (systems blend with per-class values)
"""

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.types import Coefficient, Currency, Probability


class GlobalEconomy(BaseModel):
    """System-wide economic state for dynamic balance mechanics.

    The GlobalEconomy model tracks the "Gas Tank" (imperial rent pool)
    and the "Driver" parameters (wage rate, repression level) that
    the bourgeoisie can adjust based on pool levels and tension.

    Attributes:
        imperial_rent_pool: Accumulated imperial rent available for
            redistribution. Fed by TRIBUTE inflows, depleted by
            WAGES and CLIENT_STATE outflows. Default: 100.0 Currency.

        current_super_wage_rate: Dynamic wage rate for WAGES edges.
            Adjusts based on pool level and tension via decision
            heuristics. Range: [0.05, 0.35]. Default: 0.20 (20%).

        current_repression_level: System-wide repression modifier.
            Blended with per-class repression_faced values.
            Increases during austerity/crisis periods.
            Range: [0.0, 1.0]. Default: 0.5.

    Pool Flow Logic:
        inflow = sum(tribute reaching Core Bourgeoisie after comprador cut)
        outflow = wages_paid + subsidy_paid
        delta = inflow - outflow
        new_pool = old_pool + delta

    Decision Thresholds (Aggressive):
        pool_ratio >= 0.7: PROSPERITY (can increase wages)
        pool_ratio < 0.3: AUSTERITY (cut wages or increase repression)
        pool_ratio < 0.1: CRISIS (emergency measures, emit event)
    """

    model_config = ConfigDict(frozen=True)

    imperial_rent_pool: Currency = Field(
        default=100.0,
        description="Accumulated imperial rent available for redistribution (the Gas Tank)",
    )

    current_super_wage_rate: Coefficient = Field(
        default=0.20,
        description="Dynamic wage rate for WAGES edges (20% default)",
    )

    current_repression_level: Probability = Field(
        default=0.5,
        description="System-wide repression modifier (blended with per-class values)",
    )
