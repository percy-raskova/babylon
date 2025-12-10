"""Simulation configuration for the Babylon engine.

SimulationConfig holds all global coefficients and parameters used by
the formulas in babylon.systems.formulas. This model provides:
- Type-safe validation of all parameters
- Sensible defaults matching ai-docs/game-loop-architecture.yaml
- Immutability during simulation runs
- JSON serialization for save/load

Sprint 3: Phase 2 game loop configuration.
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.types import Coefficient, Currency, Probability

# Positive float constraint for steepness and lambda parameters
PositiveFloat = Annotated[
    float,
    Field(gt=0.0, description="Positive float value (> 0)"),
]


class SimulationConfig(BaseModel):
    """Global configuration for the simulation engine.

    All formula coefficients and world parameters are stored here.
    The config is immutable (frozen) to ensure determinism during
    simulation runs.

    Attributes:
        extraction_efficiency: Alpha (α) in imperial rent formula.
            Controls how efficiently the core extracts value from periphery.
            Range: [0, 1], Default: 0.8

        consciousness_sensitivity: k in consciousness drift formula.
            Controls how quickly consciousness responds to material conditions.
            Range: [0, 1], Default: 0.5

        subsistence_threshold: Poverty line for acquiescence calculation.
            Below this wealth level, survival through compliance becomes impossible.
            Range: [0, inf), Default: 0.3

        survival_steepness: Controls sigmoid sharpness in acquiescence probability.
            Higher values mean sharper transition around subsistence threshold.
            Range: (0, inf), Default: 10.0

        repression_level: State capacity for violence.
            Reduces revolution probability in P(S|R) = cohesion / repression.
            Range: [0, 1], Default: 0.5

        initial_worker_wealth: Starting wealth for periphery worker entities.
            Range: [0, inf), Default: 0.5

        initial_owner_wealth: Starting wealth for core owner entities.
            Range: [0, inf), Default: 0.5

        loss_aversion_lambda: Kahneman-Tversky loss aversion coefficient.
            Humans feel losses ~2.25x more strongly than equivalent gains.
            Range: (0, inf), Default: 2.25
    """

    model_config = ConfigDict(frozen=True)

    # Imperial rent parameters
    extraction_efficiency: Coefficient = Field(
        default=0.8,
        description="Alpha (α) - extraction efficiency in imperial rent formula",
    )

    # Consciousness drift parameters
    consciousness_sensitivity: Coefficient = Field(
        default=0.5,
        description="k - how quickly consciousness responds to material conditions",
    )

    consciousness_decay_lambda: PositiveFloat = Field(
        default=0.1,
        description="lambda - decay rate for consciousness without material basis",
    )

    # Survival calculus parameters
    subsistence_threshold: Currency = Field(
        default=0.3,
        description="Minimum wealth for survival through compliance",
    )

    survival_steepness: PositiveFloat = Field(
        default=10.0,
        description="Sigmoid sharpness in acquiescence probability",
    )

    repression_level: Probability = Field(
        default=0.5,
        description="State capacity for violence (reduces P(S|R))",
    )

    # Initial conditions
    initial_worker_wealth: Currency = Field(
        default=0.5,
        description="Starting wealth for periphery worker",
    )

    initial_owner_wealth: Currency = Field(
        default=0.5,
        description="Starting wealth for core owner",
    )

    # Behavioral economics
    loss_aversion_lambda: PositiveFloat = Field(
        default=2.25,
        description="Kahneman-Tversky loss aversion coefficient (λ)",
    )

    # Tension dynamics
    tension_accumulation_rate: Coefficient = Field(
        default=0.05,
        description="Rate at which tension accumulates from wealth gaps",
    )

    # Imperial Circuit parameters (Sprint 3.4.1)
    comprador_cut: Coefficient = Field(
        default=0.15,
        description="Fraction of tribute kept by comprador class (15%)",
    )

    super_wage_rate: Coefficient = Field(
        default=0.20,
        description="Fraction of core bourgeoisie wealth paid as super-wages (20%)",
    )

    subsidy_conversion_rate: Coefficient = Field(
        default=0.1,
        description="Rate at which wealth converts to suppression capacity (10%)",
    )

    subsidy_trigger_threshold: Coefficient = Field(
        default=0.8,
        description="P(S|R) / P(S|A) ratio threshold for subsidy trigger (80%)",
    )

    # Solidarity transmission parameters (Sprint 3.4.2)
    solidarity_activation_threshold: Coefficient = Field(
        default=0.3,
        description="Minimum source consciousness for solidarity transmission (30%)",
    )

    mass_awakening_threshold: Coefficient = Field(
        default=0.6,
        description="Target consciousness threshold for MASS_AWAKENING event (60%)",
    )

    # Territory dynamics parameters (Sprint 3.5.4)
    heat_decay_rate: Coefficient = Field(
        default=0.1,
        description="Rate at which heat decays for LOW_PROFILE territories (10%)",
    )

    high_profile_heat_gain: Coefficient = Field(
        default=0.15,
        description="Heat gain per tick for HIGH_PROFILE territories (15%)",
    )

    eviction_heat_threshold: Coefficient = Field(
        default=0.8,
        description="Heat threshold for triggering eviction pipeline (80%)",
    )

    rent_spike_multiplier: PositiveFloat = Field(
        default=1.5,
        description="Rent multiplier during eviction (1.5x)",
    )

    displacement_rate: Coefficient = Field(
        default=0.1,
        description="Population displacement rate during eviction (10%)",
    )

    heat_spillover_rate: Coefficient = Field(
        default=0.05,
        description="Rate of heat spillover via ADJACENCY edges (5%)",
    )

    clarity_profile_coefficient: Coefficient = Field(
        default=0.3,
        description="Clarity bonus for HIGH_PROFILE territories (30%)",
    )

    # Dynamic Balance parameters (Sprint 3.4.4)
    initial_rent_pool: Currency = Field(
        default=100.0,
        description="Starting imperial rent pool for GlobalEconomy",
    )

    pool_high_threshold: Coefficient = Field(
        default=0.7,
        description="Pool ratio above which bourgeoisie considers prosperity (70%)",
    )

    pool_low_threshold: Coefficient = Field(
        default=0.3,
        description="Pool ratio below which bourgeoisie enters austerity (30%)",
    )

    pool_critical_threshold: Coefficient = Field(
        default=0.1,
        description="Pool ratio below which ECONOMIC_CRISIS fires (10%)",
    )

    min_wage_rate: Coefficient = Field(
        default=0.05,
        description="Minimum super-wage rate during crisis (5%)",
    )

    max_wage_rate: Coefficient = Field(
        default=0.35,
        description="Maximum super-wage rate during prosperity (35%)",
    )

    # Purchasing Power Parity parameters (PPP Model - Superwage Distribution)
    superwage_multiplier: float = Field(
        default=1.0,
        ge=0.0,
        description="PPP multiplier for labor aristocracy purchasing power from imperial discount",
    )

    superwage_ppp_impact: Coefficient = Field(
        default=0.5,
        description="How much imperial extraction translates to PPP bonus (50%)",
    )
