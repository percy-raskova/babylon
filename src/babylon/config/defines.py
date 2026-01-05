"""Game defines for centralized coefficient configuration.

This module provides the GameDefines model which extracts hardcoded values
from systems into a single, configurable location. This enables:
1. Easier calibration of game balance
2. Scenario-specific coefficient overrides
3. Clear documentation of magic numbers

Sprint: Paradox Refactor Phase 1
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class EconomyDefines(BaseModel):
    """Economic system coefficients."""

    model_config = ConfigDict(frozen=True)

    # Imperial rent extraction
    extraction_efficiency: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Alpha - how efficiently core extracts value from periphery",
    )
    comprador_cut: float = Field(
        default=0.90,
        ge=0.0,
        le=1.0,
        description="Fraction of wealth kept by comprador class (prevents Comprador Liquidation)",
    )

    # Production (Material Reality Refactor)
    base_labor_power: float = Field(
        default=1.0,
        ge=0.0,
        description="Base value produced per tick by worker with full biocapacity",
    )

    # Super-wages (PPP Model)
    super_wage_rate: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Fraction of tribute paid as super-wages",
    )
    superwage_multiplier: float = Field(
        default=1.0,
        ge=0.0,
        description="PPP multiplier for labor aristocracy purchasing power",
    )
    superwage_ppp_impact: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How much extraction translates to PPP bonus",
    )

    # Imperial rent pool (Dynamic Balance)
    initial_rent_pool: float = Field(
        default=100.0,
        ge=0.0,
        description="Starting imperial rent pool",
    )
    pool_high_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Pool ratio for prosperity mode",
    )
    pool_low_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Pool ratio for austerity mode",
    )
    pool_critical_threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Pool ratio for ECONOMIC_CRISIS",
    )

    # Wage bounds
    min_wage_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Minimum super-wage rate during crisis",
    )
    max_wage_rate: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Maximum super-wage rate during prosperity",
    )

    # Client state subsidy (The Iron Lung)
    subsidy_conversion_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Rate at which wealth converts to repression",
    )
    subsidy_trigger_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="P(S|R)/P(S|A) ratio threshold for subsidy",
    )

    # Negligible value thresholds (noise filtering)
    negligible_rent: float = Field(
        default=0.01,
        ge=0.0,
        description="Rent below this threshold skips event emission",
    )
    negligible_subsidy: float = Field(
        default=0.01,
        ge=0.0,
        description="Subsidy below this threshold skips processing",
    )

    # Entity operational costs (The Calorie Check - must be > 0 to prevent Eden Mode)
    # LINEAR burn: cost = base_subsistence * class_multiplier (not percentage!)
    # Calibrated for 20-year (1040 tick) Hump Shape dynamics:
    #   At 0.0005: C_b burns 0.01/tick, allowing growth phase before metabolic collapse
    base_subsistence: float = Field(
        default=0.0005,
        ge=0.0,
        le=0.5,
        description="Biological floor: fixed cost per tick (LINEAR), scaled by class multiplier",
    )

    # Zombie prevention (Sprint 1.X D2: High-Fidelity State)
    death_threshold: float = Field(
        default=0.001,
        ge=0.0,
        description="Wealth threshold below which entities die (zombie prevention failsafe)",
    )

    # TRPF Surrogate - Tendency of the Rate of Profit to Fall (Marx, Capital Vol. 3)
    # See ai-docs/epoch2-trpf.yaml for full OCC implementation planned for Epoch 2
    trpf_coefficient: float = Field(
        default=0.0005,
        ge=0.0,
        le=0.01,
        description="Rate at which extraction efficiency declines per tick (TRPF surrogate)",
    )
    rent_pool_decay: float = Field(
        default=0.002,
        ge=0.0,
        le=0.01,
        description="Background evaporation rate of imperial rent pool per tick",
    )

    # Bourgeoisie decision policy deltas (Dynamic Balance - Sprint 3.4.4)
    bribery_wage_delta: float = Field(
        default=0.05,
        ge=-1.0,
        le=1.0,
        description="Wage increase during prosperity (BRIBERY policy)",
    )
    austerity_wage_delta: float = Field(
        default=-0.05,
        ge=-1.0,
        le=1.0,
        description="Wage cut during low pool (AUSTERITY policy)",
    )
    iron_fist_repression_delta: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Repression increase during high tension (IRON_FIST policy)",
    )
    crisis_wage_delta: float = Field(
        default=-0.15,
        ge=-1.0,
        le=1.0,
        description="Emergency wage cut during crisis",
    )
    crisis_repression_delta: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Emergency repression spike during crisis",
    )

    # Tension thresholds for bourgeoisie decisions
    bribery_tension_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Maximum aggregate tension for bribery policy",
    )
    iron_fist_tension_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum aggregate tension for iron fist policy",
    )

    # TRPF efficiency floor
    trpf_efficiency_floor: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Minimum extraction efficiency after TRPF decay",
    )


class SurvivalDefines(BaseModel):
    """Survival calculus coefficients."""

    model_config = ConfigDict(frozen=True)

    # Acquiescence probability P(S|A)
    steepness_k: float = Field(
        default=10.0,
        gt=0.0,
        description="Sigmoid sharpness in acquiescence probability",
    )
    default_subsistence: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum wealth for survival through compliance",
    )

    # Revolution probability P(S|R)
    default_organization: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Fallback organization value",
    )
    default_repression: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Fallback repression value",
    )
    revolution_threshold: float = Field(
        default=1.0,
        gt=0.0,
        description="Tipping point for P(S|R) formula",
    )
    repression_base: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Base resistance to revolution in denominator",
    )


class VitalityDefines(BaseModel):
    """Mortality coefficients for Mass Line population dynamics.

    The Grinding Attrition Formula models probabilistic mortality based on
    intra-class inequality:
    - Even with sufficient average wealth, high inequality kills marginal workers
    - Deaths reduce population → per-capita wealth increases → equilibrium

    Formula:
        effective_wealth_per_capita = wealth / population
        marginal_wealth = effective_wealth_per_capita × (1 - inequality × inequality_impact)
        mortality_rate = max(0, (consumption_needs - marginal_wealth) / consumption_needs)
        deaths = floor(population × mortality_rate × base_mortality_factor)

    Malthusian Correction: Population decline increases per-capita wealth,
    reducing future mortality rates and creating equilibrium dynamics.
    """

    model_config = ConfigDict(frozen=True)

    base_mortality_factor: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="Fraction of at-risk population that dies per tick",
    )
    inequality_impact: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="How strongly inequality affects marginal wealth (1.0=full effect)",
    )


class SolidarityDefines(BaseModel):
    """Solidarity and consciousness transmission coefficients."""

    model_config = ConfigDict(frozen=True)

    scaling_factor: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="Multiplier for graph edge weights affecting organization",
    )
    activation_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum source consciousness for transmission",
    )
    mass_awakening_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Target consciousness for MASS_AWAKENING event",
    )
    negligible_transmission: float = Field(
        default=0.01,
        ge=0.0,
        description="Threshold below which transmissions are skipped",
    )
    superwage_impact: float = Field(
        default=1.0,
        ge=0.0,
        description="How much imperial extraction affects Core wealth",
    )


class BehavioralDefines(BaseModel):
    """Behavioral economics coefficients."""

    model_config = ConfigDict(frozen=True)

    loss_aversion_lambda: float = Field(
        default=2.25,
        gt=0.0,
        description="Kahneman-Tversky loss aversion coefficient",
    )


class TensionDefines(BaseModel):
    """Tension dynamics coefficients."""

    model_config = ConfigDict(frozen=True)

    accumulation_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Rate at which tension accumulates from wealth gaps",
    )


class ConsciousnessDefines(BaseModel):
    """Consciousness drift coefficients."""

    model_config = ConfigDict(frozen=True)

    sensitivity: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How quickly consciousness responds to material conditions",
    )
    decay_lambda: float = Field(
        default=0.1,
        gt=0.0,
        description="Decay rate for consciousness without material basis",
    )


class TerritoryDefines(BaseModel):
    """Territory dynamics coefficients."""

    model_config = ConfigDict(frozen=True)

    heat_decay_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Heat decay for LOW_PROFILE territories",
    )
    high_profile_heat_gain: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Heat gain for HIGH_PROFILE territories",
    )
    eviction_heat_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Heat threshold for eviction pipeline",
    )
    rent_spike_multiplier: float = Field(
        default=1.5,
        gt=0.0,
        description="Rent multiplier during eviction",
    )
    displacement_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Population displacement during eviction",
    )
    heat_spillover_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Heat spillover via ADJACENCY edges",
    )
    clarity_profile_coefficient: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Clarity bonus for HIGH_PROFILE territories",
    )


class TopologyDefines(BaseModel):
    """Phase transition coefficients for solidarity network analysis.

    The topology system tracks phase transitions in class solidarity:
    - Gaseous: Atomized, no collective action capacity
    - Transitional: Solidarity building, weak ties forming
    - Liquid: Mass movement (percolation but low cadre density)
    - Solid: Vanguard party (percolation with high cadre density)
    """

    model_config = ConfigDict(frozen=True)

    gaseous_threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Percolation ratio below this = atomized (no collective action)",
    )
    condensation_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Percolation ratio for phase transition (gaseous→liquid/solid)",
    )
    vanguard_density_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Cadre density threshold for vanguard party (liquid→solid)",
    )


class MetabolismDefines(BaseModel):
    """Metabolic rift coefficients (Slice 1.4 - Ecological Limits).

    The Metabolism System tracks the widening rift between extraction and regeneration:
    - Biocapacity regeneration and depletion
    - ECOLOGICAL_OVERSHOOT event when consumption exceeds biocapacity
    """

    model_config = ConfigDict(frozen=True)

    entropy_factor: float = Field(
        default=1.2,
        gt=1.0,
        le=3.0,
        description="Extraction costs more than it yields (thermodynamic inefficiency)",
    )
    overshoot_threshold: float = Field(
        default=1.0,
        gt=0.0,
        le=2.0,
        description="Consumption/biocapacity ratio triggering ECOLOGICAL_OVERSHOOT",
    )
    max_overshoot_ratio: float = Field(
        default=999.0,
        gt=0.0,
        description="Cap for overshoot ratio when biocapacity depleted",
    )


class StruggleDefines(BaseModel):
    """Struggle dynamics coefficients (Agency Layer - "George Floyd" Dynamic).

    The Struggle System gives political agency to oppressed classes by modeling:
    - The Spark: State violence (EXCESSIVE_FORCE) triggers insurrection
    - The Combustion: Spark + High Agitation + Low P(S|A) = UPRISING
    - The Result: Uprisings destroy wealth but build solidarity infrastructure

    George Jackson Bifurcation (Power Vacuum):
    When the Comprador becomes insolvent, a power vacuum occurs. The outcome
    depends on the Periphery Proletariat's revolutionary capacity:
    - capacity >= jackson_threshold: Revolutionary Offensive
    - capacity < jackson_threshold: Fascist Revanchism
    """

    model_config = ConfigDict(frozen=True)

    spark_probability_scale: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Base 10% chance scaled by repression_faced for EXCESSIVE_FORCE",
    )
    resistance_threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Minimum agitation level for uprising to trigger",
    )
    wealth_destruction_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Fraction of wealth destroyed during uprising (riot damage)",
    )
    solidarity_gain_per_uprising: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Solidarity strength increase on edges per uprising",
    )

    # George Jackson Bifurcation parameters
    jackson_threshold: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Revolutionary capacity threshold (org * consciousness) for organized response",
    )
    revolutionary_agitation_boost: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="Agitation boost for periphery proletariat during revolutionary offensive",
    )
    fascist_identity_boost: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="National identity boost for core workers during fascist turn",
    )
    fascist_acquiescence_boost: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Acquiescence boost for core workers during fascist turn",
    )


class CarceralDefines(BaseModel):
    """Carceral equilibrium coefficients (Terminal Crisis Dynamics).

    The carceral system models the transition from wage suppression to
    outright incarceration as the imperial rent pool exhausts:

    1. SUPERWAGE_CRISIS: Rent pool can't sustain LA wages
    2. CLASS_DECOMPOSITION: LA splits into enforcers + prisoners
    3. CONTROL_RATIO_CRISIS: Prisoners exceed control capacity
    4. TERMINAL_DECISION: Revolution vs genocide based on organization

    Real-world staffing ratios (sources: BJS, Marshall Project 2024):
    - 1:1 = Maximum control (Massachusetts, best-staffed)
    - 4:1 = US national jail average (2022)
    - 15:1 = Federal DOJ theoretical baseline
    - 200:1 = Crisis/collapse (Georgia, 2024)

    With 70/30 decomposition, prisoner/enforcer = 2.33:1, so:
    - control_capacity <= 2: Crisis triggers immediately
    - control_capacity >= 3: No crisis (stable carceral state)
    """

    model_config = ConfigDict(frozen=True)

    control_capacity: int = Field(
        default=4,
        ge=1,
        le=20,
        description="Prisoners one enforcer can control (1:N). US average ~4, crisis >15.",
    )
    enforcer_fraction: float = Field(
        default=0.15,
        ge=0.05,
        le=0.50,
        description="After SUPERWAGE_CRISIS: % of former LA who BECOME guards/cops",
    )
    proletariat_fraction: float = Field(
        default=0.85,
        ge=0.50,
        le=0.95,
        description="After SUPERWAGE_CRISIS: % of former LA who BECOME prisoners",
    )
    revolution_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Average prisoner organization threshold for revolution (vs genocide)",
    )

    # Phase staggering delays (ticks) - ensures temporal separation between phases
    decomposition_delay: int = Field(
        default=52,
        ge=0,
        le=520,
        description="Ticks to wait after SUPERWAGE_CRISIS before CLASS_DECOMPOSITION (1 year default)",
    )
    control_ratio_delay: int = Field(
        default=52,
        ge=0,
        le=520,
        description="Ticks to wait after CLASS_DECOMPOSITION before checking control ratio (1 year default)",
    )
    terminal_decision_delay: int = Field(
        default=1,
        ge=0,
        le=52,
        description="Ticks to wait after CONTROL_RATIO_CRISIS before TERMINAL_DECISION",
    )


class EndgameDefines(BaseModel):
    """Configuration for endgame detection thresholds (Slice 1.6).

    The EndgameDetector monitors WorldState for three possible game endings:

    1. REVOLUTIONARY_VICTORY: percolation >= threshold AND consciousness > threshold
       The masses have achieved critical organization AND ideological clarity.

    2. ECOLOGICAL_COLLAPSE: overshoot_ratio > threshold for N consecutive ticks
       Sustained ecological overshoot leads to irreversible collapse.

    3. FASCIST_CONSOLIDATION: national_identity > class_consciousness for M+ nodes
       Fascist ideology has captured the majority of the population.

    Attributes:
        revolutionary_percolation_threshold: Minimum percolation ratio (0.7 = 70%
            of nodes in giant solidarity component) for revolutionary victory.
        revolutionary_consciousness_threshold: Minimum average class consciousness
            (0.8 = 80% ideological clarity) for revolutionary victory.
        ecological_overshoot_threshold: Consumption/biocapacity ratio above which
            ecological damage accumulates (2.0 = consuming 2x biocapacity).
        ecological_sustained_ticks: Number of consecutive ticks overshoot must
            persist before triggering ECOLOGICAL_COLLAPSE (5 ticks).
        fascist_majority_threshold: Minimum number of nodes where national_identity
            exceeds class_consciousness for FASCIST_CONSOLIDATION (3 nodes).
    """

    model_config = ConfigDict(frozen=True)

    revolutionary_percolation_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Percolation ratio threshold for revolutionary victory (70%)",
    )
    revolutionary_consciousness_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Average consciousness threshold for revolutionary victory (80%)",
    )
    ecological_overshoot_threshold: float = Field(
        default=2.0,
        gt=0.0,
        description="Overshoot ratio threshold for ecological collapse tracking",
    )
    ecological_sustained_ticks: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Consecutive ticks of overshoot before collapse triggers",
    )
    fascist_majority_threshold: int = Field(
        default=3,
        ge=1,
        le=100,
        description="Minimum nodes with national_identity > class_consciousness",
    )


class InitialDefines(BaseModel):
    """Initial condition coefficients."""

    model_config = ConfigDict(frozen=True)

    worker_wealth: float = Field(
        default=0.5,
        ge=0.0,
        description="Starting wealth for periphery worker",
    )
    owner_wealth: float = Field(
        default=0.5,
        ge=0.0,
        description="Starting wealth for core owner",
    )
    default_population: int = Field(
        default=1,
        ge=1,
        description="Default population for test entities. pop=1 ensures per-capita survival mechanics are tested without large denominators masking issues.",
    )


class PrecisionDefines(BaseModel):
    """Numerical precision configuration for deterministic simulation.

    Epoch 0 Physics Hardening:
    - All floating-point values snap to a 10^-n grid (default n=6)
    - This prevents drift accumulation over long simulations (100+ years)
    - ROUND_HALF_UP ensures deterministic cross-platform behavior

    The Gatekeeper Pattern: Quantization is applied at TYPE level
    (Pydantic AfterValidator), NOT inside formulas.

    Note: Increased from 5 to 6 decimal places for 100-year (5200 tick)
    Carceral Equilibrium simulations to reduce cumulative rounding errors.
    """

    model_config = ConfigDict(frozen=True)

    decimal_places: int = Field(
        default=6,
        ge=1,
        le=10,
        description="Quantization precision (10^-n). Default 6 = 0.000001",
    )
    rounding_mode: str = Field(
        default="ROUND_HALF_UP",
        description="Rounding mode for quantization.",
    )
    epsilon: float = Field(
        default=1e-6,
        gt=0.0,
        le=1e-3,
        description="Division-by-zero guard for formulas. Default 1e-6 matches quantization.",
    )


class TimescaleDefines(BaseModel):
    """Simulation timescale configuration for weekly ticks.

    Epoch 0 Physics Hardening:
    - 1 tick = 7 days (weekly resolution)
    - 52 weeks = 1 year (for annual rate conversions)

    This is critical for:
    - Economic flow rates (annual -> per-tick conversion)
    - Historical pacing (events per game year)
    - UI display (showing dates/weeks)

    All annual rates (wage_rate, extraction_efficiency) are divided by
    weeks_per_year to get per-tick rates.
    """

    model_config = ConfigDict(frozen=True)

    tick_duration_days: int = Field(
        default=7,
        ge=1,
        le=365,
        description="Real-world days per tick. Default 7 = weekly.",
    )
    weeks_per_year: int = Field(
        default=52,
        ge=1,
        description="Weeks per year for flow conversion.",
    )

    @property
    def ticks_per_year(self) -> int:
        """Number of ticks per simulation year.

        Since 1 tick = 1 week, this equals weeks_per_year.
        """
        return self.weeks_per_year

    @property
    def days_per_year(self) -> int:
        """Days per simulation year (ticks * days_per_tick).

        With defaults: 7 * 52 = 364 days (close to actual 365-366).
        """
        return self.tick_duration_days * self.weeks_per_year


class GameDefines(BaseModel):
    """Centralized game coefficients extracted from hardcoded values.

    GameDefines collects numerical constants that were previously scattered
    across system implementations. By centralizing them here, we can:
    - Document their purpose and valid ranges
    - Override them per-scenario for calibration
    - Test the sensitivity of outcomes to coefficient changes

    The model is frozen (immutable) to ensure defines remain constant
    throughout a simulation run.

    Structure follows the YAML file organization:
    - economy: Imperial rent extraction and value flow
    - survival: P(S|A) and P(S|R) survival calculus
    - solidarity: Consciousness transmission
    - behavioral: Behavioral economics (loss aversion)
    - tension: Tension dynamics
    - consciousness: Consciousness drift
    - territory: Territory dynamics
    - topology: Phase transition thresholds (gaseous/liquid/solid)
    - metabolism: Metabolic rift (ecological limits)
    - struggle: Struggle dynamics (Agency Layer)
    - carceral: Carceral equilibrium (Terminal Crisis Dynamics)
    - endgame: Endgame detection thresholds
    - initial: Initial conditions
    """

    model_config = ConfigDict(frozen=True)

    economy: EconomyDefines = Field(default_factory=EconomyDefines)
    survival: SurvivalDefines = Field(default_factory=SurvivalDefines)
    vitality: VitalityDefines = Field(default_factory=VitalityDefines)
    solidarity: SolidarityDefines = Field(default_factory=SolidarityDefines)
    behavioral: BehavioralDefines = Field(default_factory=BehavioralDefines)
    tension: TensionDefines = Field(default_factory=TensionDefines)
    consciousness: ConsciousnessDefines = Field(default_factory=ConsciousnessDefines)
    territory: TerritoryDefines = Field(default_factory=TerritoryDefines)
    topology: TopologyDefines = Field(default_factory=TopologyDefines)
    metabolism: MetabolismDefines = Field(default_factory=MetabolismDefines)
    struggle: StruggleDefines = Field(default_factory=StruggleDefines)
    carceral: CarceralDefines = Field(default_factory=CarceralDefines)
    endgame: EndgameDefines = Field(default_factory=EndgameDefines)
    initial: InitialDefines = Field(default_factory=InitialDefines)
    precision: PrecisionDefines = Field(default_factory=PrecisionDefines)
    timescale: TimescaleDefines = Field(default_factory=TimescaleDefines)

    # Legacy flat attributes for backward compatibility
    # These delegate to the nested structure

    @property
    def SUPERWAGE_IMPACT(self) -> float:
        """How much 1 unit of imperial extraction increases Core wealth."""
        return self.solidarity.superwage_impact

    @property
    def SOLIDARITY_SCALING(self) -> float:
        """Multiplier for graph edge weights affecting Organization."""
        return self.solidarity.scaling_factor

    @property
    def REPRESSION_BASE(self) -> float:
        """Base resistance to revolution in P(S|R) denominator."""
        return self.survival.repression_base

    @property
    def REVOLUTION_THRESHOLD(self) -> float:
        """The tipping point for P(S|R) formula."""
        return self.survival.revolution_threshold

    @property
    def DEFAULT_ORGANIZATION(self) -> float:
        """Fallback organization value when not specified on entity."""
        return self.survival.default_organization

    @property
    def DEFAULT_REPRESSION_FACED(self) -> float:
        """Fallback repression value when not specified on entity."""
        return self.survival.default_repression

    @property
    def DEFAULT_SUBSISTENCE(self) -> float:
        """Fallback subsistence threshold when not specified on entity."""
        return self.survival.default_subsistence

    @property
    def NEGLIGIBLE_TRANSMISSION(self) -> float:
        """Threshold below which transmissions are skipped as noise."""
        return self.solidarity.negligible_transmission

    @classmethod
    def load_from_yaml(cls, path: str | Path) -> GameDefines:
        """Load GameDefines from a YAML file.

        Args:
            path: Path to the YAML file (absolute or relative)

        Returns:
            GameDefines instance populated from YAML

        Raises:
            FileNotFoundError: If the YAML file doesn't exist
            yaml.YAMLError: If the YAML is malformed
            pydantic.ValidationError: If values fail validation
        """
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return cls._from_yaml_dict(data)

    @classmethod
    def _from_yaml_dict(cls, data: dict[str, Any]) -> GameDefines:
        """Create GameDefines from parsed YAML dictionary.

        Args:
            data: Parsed YAML data

        Returns:
            GameDefines instance
        """
        if data is None:
            data = {}

        return cls(
            economy=EconomyDefines(**data.get("economy", {})),
            survival=SurvivalDefines(**data.get("survival", {})),
            vitality=VitalityDefines(**data.get("vitality", {})),
            solidarity=SolidarityDefines(**data.get("solidarity", {})),
            behavioral=BehavioralDefines(**data.get("behavioral", {})),
            tension=TensionDefines(**data.get("tension", {})),
            consciousness=ConsciousnessDefines(**data.get("consciousness", {})),
            territory=TerritoryDefines(**data.get("territory", {})),
            topology=TopologyDefines(**data.get("topology", {})),
            metabolism=MetabolismDefines(**data.get("metabolism", {})),
            struggle=StruggleDefines(**data.get("struggle", {})),
            carceral=CarceralDefines(**data.get("carceral", {})),
            endgame=EndgameDefines(**data.get("endgame", {})),
            initial=InitialDefines(**data.get("initial", {})),
            precision=PrecisionDefines(**data.get("precision", {})),
            timescale=TimescaleDefines(**data.get("timescale", {})),
        )

    @classmethod
    def default_yaml_path(cls) -> Path:
        """Return the default path to defines.yaml.

        Returns:
            Path to src/babylon/data/defines.yaml
        """
        return Path(__file__).parent.parent / "data" / "defines.yaml"

    @classmethod
    def load_default(cls) -> GameDefines:
        """Load GameDefines from the default YAML location.

        Falls back to default values if file doesn't exist.

        Returns:
            GameDefines instance
        """
        default_path = cls.default_yaml_path()
        if default_path.exists():
            return cls.load_from_yaml(default_path)
        return cls()
