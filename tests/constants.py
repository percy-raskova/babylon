"""Centralized test constants for Babylon formula tests.

This module provides a single source of truth for magic numbers used across
the test suite. Constants are organized by theoretical domain and documented
with their sources.

YAML-First Architecture:
    Shared constants are imported from GameDefines, which loads from defines.yaml.
    This ensures test constants stay in sync with production configuration.

Design Principles:
    1. Shared constants: Import from GameDefines (single source of truth)
    2. Test-only constants: Defined here (scenarios, edge cases, theoretical validation)
    3. Computed values (e.g., 20-year horizon = 52 ticks/year * 20 = 1040)

Canonical Source:
    - src/babylon/data/defines.yaml (YAML configuration)
    - src/babylon/config/defines.py (GameDefines Pydantic model)
    - src/babylon/formulas/formulas/constants.py (EPSILON, LOSS_AVERSION_COEFFICIENT)

Example:
    from tests.constants import TestConstants, MarxCapitalExamples

    # Use behavioral economics constant (from GameDefines)
    assert loss == TestConstants.Behavioral.LOSS_AVERSION * principal

    # Parametrized test with Marx's examples
    @pytest.mark.parametrize("example", MarxCapitalExamples.all())
    def test_rate_of_profit(example):
        rate = calculate_rate_of_profit(
            surplus_value=example.s,
            constant_capital=example.c,
            variable_capital=example.v,
        )
        assert rate == pytest.approx(example.expected_profit_rate, abs=0.001)
"""

from dataclasses import dataclass
from typing import Final

from babylon.config.defines import GameDefines

# =============================================================================
# GAMEDEFINES INSTANCE (Single Source of Truth)
# =============================================================================
# All shared constants reference this instance, which loads from defines.yaml.
# This ensures test values stay in sync with production configuration.
_DEFINES: Final[GameDefines] = GameDefines.load_default()

# =============================================================================
# CANONICAL CONSTANTS (Single Source of Truth)
# =============================================================================


@dataclass(frozen=True)
class CanonicalThresholds:
    """Universal threshold values used across multiple test domains.

    These are the canonical "source of truth" for commonly-used values.
    Domain-specific dataclasses should reference these rather than
    redefining the same values.

    Source: GameDefines (loads from src/babylon/data/defines.yaml).
    """

    # -------------------------------------------------------------------------
    # Pool Ratio Thresholds (from GameDefines.economy.pool_*_threshold)
    # Used for bourgeoisie decision heuristics in Dynamic Balance
    # -------------------------------------------------------------------------
    POOL_HIGH: float = _DEFINES.economy.pool_high_threshold
    POOL_LOW: float = _DEFINES.economy.pool_low_threshold
    POOL_CRITICAL: float = _DEFINES.economy.pool_critical_threshold

    # -------------------------------------------------------------------------
    # Economic Baselines (from GameDefines)
    # -------------------------------------------------------------------------
    INITIAL_RENT_POOL: float = _DEFINES.economy.initial_rent_pool
    DEFAULT_REPRESSION: float = _DEFINES.survival.default_repression
    DEFAULT_EXTRACTION: float = _DEFINES.economy.extraction_efficiency

    # -------------------------------------------------------------------------
    # Probability Bands [0.0, 1.0]
    # Universal threshold levels for probability-based fields
    # -------------------------------------------------------------------------
    P_ZERO: float = 0.0  # Minimum probability / none
    P_LOW: float = 0.1  # Low threshold
    P_MODERATE: float = 0.3  # Moderate-low threshold
    P_MIDPOINT: float = 0.5  # Middle value / default
    P_ELEVATED: float = 0.6  # Elevated threshold
    P_HIGH: float = 0.7  # High threshold
    P_VERY_HIGH: float = 0.8  # Very high threshold
    P_EXTREME: float = 0.9  # Near-maximum
    P_FULL: float = 1.0  # Maximum probability

    # -------------------------------------------------------------------------
    # Tick Counts (standard simulation durations)
    # -------------------------------------------------------------------------
    TICKS_SHORT: int = 5  # Quick comparison tests
    TICKS_FEEDBACK: int = 10  # Feedback loop tests
    TICKS_MEDIUM: int = 50  # Economic flow tests
    TICKS_STANDARD: int = 100  # Standard success criteria
    TICKS_CROSSOVER: int = 200  # P(S|R) > P(S|A) detection
    TICKS_LONG: int = 1000  # Long-run stability


# Shorthand alias for referencing canonical values
Canon = CanonicalThresholds


# =============================================================================
# DETROIT METRO TEST CASE (Constitution IV)
# =============================================================================
# The Detroit metro area serves as the foundational validation case for
# deindustrialization signal detection (Feature 003).


@dataclass(frozen=True)
class DetroitMetro:
    """Detroit metro county FIPS codes for temporal validation tests.

    Detroit serves as the canonical test case for deindustrialization:
    - Wayne County (Detroit core): Manufacturing decline, population loss
    - Oakland County (affluent suburb): Professional services growth
    - Macomb County (working-class suburb): Mixed manufacturing/services

    Reference: Constitution Section IV, spec-003-hydrator-temporal-validation
    """

    WAYNE_FIPS: str = "26163"
    """Wayne County - Detroit core (deindustrialized manufacturing center)."""

    OAKLAND_FIPS: str = "26125"
    """Oakland County - Affluent northern suburb (professional services)."""

    MACOMB_FIPS: str = "26099"
    """Macomb County - Working-class eastern suburb."""

    @classmethod
    def all_fips(cls) -> list[str]:
        """Return all Detroit metro FIPS codes."""
        return [cls.WAYNE_FIPS, cls.OAKLAND_FIPS, cls.MACOMB_FIPS]


# =============================================================================
# DOMAIN-SPECIFIC CONSTANTS
# =============================================================================


@dataclass(frozen=True)
class BehavioralConstants:
    """Behavioral economics constants (Kahneman-Tversky prospect theory).

    Source: Kahneman & Tversky (1979), "Prospect Theory: An Analysis of
    Decision under Risk", Econometrica 47(2): 263-292.
    Loaded from: GameDefines.behavioral.loss_aversion_lambda
    """

    # Losses are perceived as 2.25x more impactful than equivalent gains
    LOSS_AVERSION: float = _DEFINES.behavioral.loss_aversion_lambda


@dataclass(frozen=True)
class SolidarityConstants:
    """Solidarity transmission constants (MLM-TW theory).

    The activation threshold encodes the theoretical requirement that
    consciousness must exceed a minimum level before it can transmit
    through solidarity networks.
    Loaded from: GameDefines.solidarity.*
    """

    # Minimum source consciousness for transmission
    ACTIVATION_THRESHOLD: float = _DEFINES.solidarity.activation_threshold

    # Consciousness level for MASS_AWAKENING event
    MASS_AWAKENING_THRESHOLD: float = _DEFINES.solidarity.mass_awakening_threshold


@dataclass(frozen=True)
class BourgeoisieDecisionConstants:
    """Pool threshold and policy delta constants for bourgeoisie decision system.

    These encode the decision matrix for Dynamic Balance (Sprint 3.4.4):
    - pool_ratio >= HIGH -> BRIBERY (if low tension)
    - pool_ratio < LOW -> AUSTERITY/IRON_FIST
    - pool_ratio < CRITICAL -> CRISIS

    Loaded from: GameDefines.economy.*
    """

    # Pool ratio thresholds (reference canonical values)
    POOL_HIGH_THRESHOLD: float = Canon.POOL_HIGH
    POOL_LOW_THRESHOLD: float = Canon.POOL_LOW
    POOL_CRITICAL_THRESHOLD: float = Canon.POOL_CRITICAL

    # Tension thresholds for decision branching
    BRIBERY_TENSION_THRESHOLD: float = _DEFINES.economy.bribery_tension_threshold
    IRON_FIST_TENSION_THRESHOLD: float = _DEFINES.economy.iron_fist_tension_threshold
    TENSION_THRESHOLD: float = _DEFINES.economy.iron_fist_tension_threshold  # Legacy alias

    # Policy deltas (wage and repression changes per decision)
    BRIBERY_WAGE_DELTA: float = _DEFINES.economy.bribery_wage_delta
    AUSTERITY_WAGE_DELTA: float = _DEFINES.economy.austerity_wage_delta
    IRON_FIST_REPRESSION_DELTA: float = _DEFINES.economy.iron_fist_repression_delta
    CRISIS_WAGE_DELTA: float = _DEFINES.economy.crisis_wage_delta
    CRISIS_REPRESSION_DELTA: float = _DEFINES.economy.crisis_repression_delta


@dataclass(frozen=True)
class TRPFConstants:
    """Tendency of the Rate of Profit to Fall constants.

    Source: Marx, Capital Volume 3, Chapters 13-15.
    The TRPF surrogate models profit rate decline as time-dependent decay.
    Loaded from: GameDefines.economy.trpf_*
    """

    # TRPF decay coefficient per tick
    TRPF_COEFFICIENT: float = _DEFINES.economy.trpf_coefficient

    # Rent pool background evaporation rate
    RENT_POOL_DECAY: float = _DEFINES.economy.rent_pool_decay

    # Minimum extraction efficiency (floor for TRPF multiplier)
    EFFICIENCY_FLOOR: float = _DEFINES.economy.trpf_efficiency_floor


@dataclass(frozen=True)
class TimescaleConstants:
    """Simulation timescale constants.

    1 tick = 1 week, 52 weeks = 1 year.
    Loaded from: GameDefines.timescale.*
    """

    TICKS_PER_YEAR: int = _DEFINES.timescale.weeks_per_year
    DAYS_PER_TICK: int = _DEFINES.timescale.tick_duration_days

    # Derived: 20-year simulation horizon (Epoch 1 standard)
    TWENTY_YEAR_HORIZON: int = _DEFINES.timescale.weeks_per_year * 20  # 1040 ticks


@dataclass(frozen=True)
class MetabolicRiftConstants:
    """Ecological limits constants (Metabolic Rift).

    The metabolic rift encodes thermodynamic inefficiency in extraction
    and the cap for overshoot ratio when biocapacity is depleted.
    Loaded from: GameDefines.metabolism.*
    """

    # Extraction costs more than it yields (thermodynamic waste)
    ENTROPY_FACTOR: float = _DEFINES.metabolism.entropy_factor

    # Cap for overshoot ratio when biocapacity is zero/negative
    MAX_OVERSHOOT_RATIO: float = _DEFINES.metabolism.max_overshoot_ratio

    # Breakeven intensity where regeneration equals extraction
    # Formula: regeneration_rate / entropy_factor = 0.02 / 1.2 = 0.0167
    # When intensity > 0.0167, biocapacity depletes
    # When intensity < 0.0167, biocapacity regenerates
    BREAKEVEN_INTENSITY: float = 0.0167  # Test-specific computed value


# =============================================================================
# MODEL TEST CONSTANTS (Value-Type Organization)
# =============================================================================


@dataclass(frozen=True)
class WealthDefaults:
    """Default wealth values for test entities.

    Source: SocialClass model defaults and Phase 1 blueprint scenarios.
    Currency type represents imperial rent pool and entity wealth.
    """

    # SocialClass model default
    DEFAULT_WEALTH: float = 10.0

    # DomainFactory defaults
    WORKER_BASELINE: float = 0.5  # create_worker() default
    OWNER_BASELINE: float = 10.0  # create_owner() default

    # Phase 1 blueprint values
    PERIPHERY_WORKER: float = 20.0  # Periphery proletariat
    CORE_OWNER: float = 1000.0  # Core bourgeoisie

    # Safe wealth for integration tests (survives per-capita survival mechanics)
    # 5× default_subsistence (0.3) = 1.5, but we use 5.0 for extra margin
    SAFE_WEALTH: float = 5.0

    # Common test ranges
    DESTITUTE: float = 0.0
    MODEST: float = 50.0
    SIGNIFICANT: float = 100.0
    SUBSTANTIAL: float = 200.0  # Component test scenarios
    HIGH: float = 500.0
    LARGE: float = 1_000_000.0  # Large value validation
    EXTREME: float = 1_000_000_000.0  # Edge case testing


@dataclass(frozen=True)
class ProbabilityDefaults:
    """Probability values [0.0, 1.0] for tests.

    Source: Probability constrained type bounds and common test scenarios.
    Used for: organization, repression, p_acquiescence, p_revolution, tension.
    """

    # Boundaries
    ZERO: float = 0.0
    FULL: float = 1.0
    MIDPOINT: float = 0.5

    # Common thresholds
    LOW: float = 0.1  # Low organization (DomainFactory worker)
    MODERATE: float = 0.3  # Subsistence threshold default
    BELOW_MIDPOINT: float = 0.4  # Between moderate and midpoint
    ELEVATED: float = 0.6  # P_acquiescence test scenarios
    HIGH: float = 0.7  # High organization (DomainFactory owner)
    VERY_HIGH: float = 0.8  # Eviction threshold, high tension
    EXTREME: float = 0.9  # Near-maximum values

    # Edge case testing
    EPSILON_ABOVE_ZERO: float = 0.001
    EPSILON_BELOW_ONE: float = 0.999


@dataclass(frozen=True)
class IdeologyDefaults:
    """Ideology values [-1.0, +1.0] for tests.

    Source: Ideology constrained type bounds (bipolar spectrum).
    -1.0 = fully revolutionary (class conscious)
    +1.0 = fully reactionary (nationalist)
     0.0 = neutral/undecided
    """

    FULL_REVOLUTIONARY: float = -1.0
    LEANING_REVOLUTIONARY: float = -0.5
    SLIGHT_REVOLUTIONARY: float = -0.3
    NEUTRAL: float = 0.0
    SLIGHT_REACTIONARY: float = 0.3
    LEANING_REACTIONARY: float = 0.5
    STRONG_REACTIONARY: float = 0.7
    FULL_REACTIONARY: float = 1.0


@dataclass(frozen=True)
class ConsciousnessDefaults:
    """Consciousness values [0.0, 1.0] for George Jackson model.

    Source: IdeologicalProfile model (Sprint 3.4.3 George Jackson Refactor).
    class_consciousness + national_identity represent dual consciousness.
    """

    FALSE_CONSCIOUSNESS: float = 0.0  # No class awareness
    LOW: float = 0.1  # Minimal awareness
    NEUTRAL_IDENTITY: float = 0.5  # Balanced consciousness
    AWAKENING: float = 0.7  # Beginning to see class interests
    CLASS_CONSCIOUS: float = 0.8  # Strong class awareness
    REVOLUTIONARY: float = 0.9  # Near-complete class consciousness
    FULL: float = 1.0  # Maximum consciousness


@dataclass(frozen=True)
class TerritoryDefaults:
    """Territory values for spatial tests.

    Source: Territory model defaults and carceral geography system.
    Heat represents state attention, rent_level represents extraction.
    """

    # Heat dynamics (carceral geography)
    NO_HEAT: float = 0.0
    MODERATE_HEAT: float = 0.5
    EVICTION_THRESHOLD: float = 0.8  # Matches GameDefines.territory.eviction_threshold
    MAX_HEAT: float = 1.0

    # Rent levels
    BASELINE_RENT: float = 1.0
    ELEVATED_RENT: float = 2.0

    # Population
    EMPTY: int = 0
    SMALL_POPULATION: int = 1000
    LARGE_POPULATION: int = 1_000_000

    # Biocapacity (metabolic rift)
    FULL_BIOCAPACITY: float = 100.0
    DEFAULT_REGENERATION: float = 0.02


@dataclass(frozen=True)
class EconomicFlowDefaults:
    """Economic flow values for relationship tests.

    Source: Relationship model and GlobalEconomy defaults.
    value_flow represents imperial rent extracted via EXPLOITATION edges.
    """

    NO_FLOW: float = Canon.P_ZERO
    PHASE1_EXTRACTION: float = 80.0  # Phi = 100 - 20 (Phase 1 blueprint)
    INITIAL_RENT_POOL: float = Canon.INITIAL_RENT_POOL  # Reference canonical

    # Tension values (reference canonical probability bands)
    NO_TENSION: float = Canon.P_ZERO
    LOW_TENSION: float = Canon.P_MODERATE
    MODERATE_TENSION: float = Canon.P_MIDPOINT
    HIGH_TENSION: float = Canon.P_HIGH
    CRITICAL_TENSION: float = Canon.P_EXTREME

    # Solidarity strength (from topology tests)
    WEAK_SOLIDARITY: float = 0.05
    POTENTIAL_SOLIDARITY: float = Canon.P_MODERATE  # > 0.1 to count as potential
    ACTUAL_SOLIDARITY: float = Canon.P_MIDPOINT  # > 0.5 to count as actual
    STRONG_SOLIDARITY: float = Canon.P_VERY_HIGH


@dataclass(frozen=True)
class QuantizationDefaults:
    """Precision values for type tests (Epoch 0 Physics: 10^-6 grid).

    Loaded from: GameDefines.precision.*
    All constrained types quantize to 6 decimal places for determinism.
    Increased from 5 to support 100-year Carceral Equilibrium simulations.
    """

    DECIMAL_PLACES: int = _DEFINES.precision.decimal_places
    GRID_PRECISION: float = 10 ** (-_DEFINES.precision.decimal_places)

    # Division-by-zero guard (from GameDefines.precision.epsilon)
    EPSILON: float = _DEFINES.precision.epsilon

    # Comparison epsilon for floating-point tests (more lenient than grid)
    # Used in property-based tests where tiny differences don't matter
    COMPARISON_EPSILON: float = 10 ** (-(_DEFINES.precision.decimal_places + 4))

    # Test values for quantization validation
    UNQUANTIZED_PROBABILITY: float = 0.123456789
    QUANTIZED_PROBABILITY: float = 0.123457  # Rounded to 6 decimals
    UNQUANTIZED_CURRENCY: float = 1234.567891
    QUANTIZED_CURRENCY: float = 1234.567891  # Rounded to 6 decimals
    UNQUANTIZED_RATIO: float = 2.718281828
    QUANTIZED_RATIO: float = 2.718282  # Rounded to 6 decimals


@dataclass(frozen=True)
class StateFinanceDefaults:
    """StateFinance model default values.

    Source: StateFinance model (Epoch 1 Political Economy of Liquidity).
    Represents sovereign fiscal capacity: treasury, budgets, taxation, debt.
    """

    # Treasury (liquid funds)
    DEFAULT_TREASURY: float = 100.0  # Starting liquidity
    MODERATE_TREASURY: float = 200.0  # Custom creation tests
    HEALTHY_TREASURY: float = 500.0  # Well-funded state

    # Budgets (spending per tick)
    DEFAULT_POLICE_BUDGET: float = 10.0  # Repression cost
    DEFAULT_WELFARE_BUDGET: float = 15.0  # Social reproduction cost
    ELEVATED_POLICE_BUDGET: float = 20.0  # Increased repression
    ELEVATED_WELFARE_BUDGET: float = 25.0  # Increased welfare
    HIGH_POLICE_BUDGET: float = 30.0  # Austerity reversal
    HIGH_WELFARE_BUDGET: float = 30.0  # Strong welfare state

    # Tax rates (Coefficient [0, 1])
    DEFAULT_TAX_RATE: float = 0.3  # 30% extraction from bourgeoisie
    ELEVATED_TAX_RATE: float = 0.4  # Higher extraction
    CONFISCATORY_TAX_RATE: float = 0.5  # 50% extraction

    # Debt
    DEFAULT_DEBT_CEILING: float = 500.0  # Max sustainable debt
    HIGH_DEBT_CEILING: float = 1000.0  # Extended borrowing


@dataclass(frozen=True)
class GlobalEconomyDefaults:
    """GlobalEconomy model default values.

    Source: GlobalEconomy model (Sprint 3.4.4: Dynamic Balance).
    The "Gas Tank" that forces scarcity and agency into the simulation.
    """

    # Super-wage rates (Coefficient [0, 1])
    DEFAULT_WAGE_RATE: float = 0.20  # 20% of extraction as super-wages
    LOW_WAGE_RATE: float = 0.15  # Austerity level
    MODERATE_WAGE_RATE: float = 0.25  # Moderate bribery
    ELEVATED_WAGE_RATE: float = 0.30  # Increased bribery
    HIGH_WAGE_RATE: float = 0.35  # High bribery level

    # Pool thresholds for decision heuristics (reference canonical values)
    PROSPERITY_THRESHOLD: float = Canon.POOL_HIGH
    AUSTERITY_THRESHOLD: float = Canon.POOL_LOW
    CRISIS_THRESHOLD: float = Canon.POOL_CRITICAL

    # Pool values for test scenarios (relative to Canon.INITIAL_RENT_POOL)
    CRISIS_POOL: float = 5.0  # 5% of initial (crisis scenario)
    AUSTERITY_POOL: float = 25.0  # 25% of initial (below austerity)
    HALF_POOL: float = 50.0  # 50% of initial
    PROSPERITY_POOL: float = 70.0  # 70% of initial (at prosperity threshold)
    MODERATE_POOL: float = 150.0  # 150% - serialization test
    ELEVATED_POOL: float = 175.0  # 175% - JSON round trip test
    DOUBLED_POOL: float = 200.0  # 200% - full custom creation
    HEALTHY_POOL: float = 500.0  # Large pool


@dataclass(frozen=True)
class PrecarityDefaults:
    """PrecarityState model default values for test scenarios.

    Source: PrecarityState model (Epoch 1 Political Economy of Liquidity).
    Tracks economic precarity: wages, PPP, inflation, subsistence, organization.
    """

    # Nominal wage values
    DEFAULT_WAGE: float = 10.0  # Model default
    PERIPHERY_WAGE: float = 20.0  # Periphery proletariat
    CUSTOM_WAGE: float = 25.0  # Serialization tests
    HIGH_WAGE: float = 30.0  # JSON round-trip tests
    ARISTOCRACY_WAGE: float = 50.0  # Core labor aristocracy
    HYPERINFLATION_WAGE: float = 1000.0  # Hyperinflation scenario
    ATOMIZED_WAGE: float = 20.0  # Atomized petty bourgeoisie
    BELOW_SUBSISTENCE_WAGE: float = 3.0  # Below subsistence wage
    MINIMAL_WAGE: float = 1.0  # Maximum precarity
    VERY_HIGH_WAGE: float = 100.0  # Very high wage
    EXTREME_WAGE: float = 100_000.0  # Boundary testing

    # PPP factor values [0, 1]
    PERIPHERY_PPP: float = 0.3  # Low purchasing power
    LOW_PPP: float = 0.5  # Half purchasing power
    DECLINING_PPP: float = 0.7  # Stagflation scenario
    MODERATE_PPP: float = 0.8  # Moderate PPP

    # Inflation index values [1, inf)
    MODERATE_INFLATION: float = 1.4  # Stagflation
    ELEVATED_INFLATION: float = 1.5  # Serialization tests
    DOUBLE_INFLATION: float = 2.0  # 2x price level
    HIGH_INFLATION: float = 1.8  # JSON round-trip
    HYPERINFLATION: float = 100.0  # Hyperinflation

    # Subsistence threshold values
    DEFAULT_SUBSISTENCE: float = 5.0  # Model default
    ELEVATED_SUBSISTENCE: float = 6.0  # JSON round-trip
    HIGH_SUBSISTENCE: float = 7.0  # Serialization tests
    CUSTOM_SUBSISTENCE: float = 8.0  # Custom creation


@dataclass(frozen=True)
class VitalityDefaults:
    """VitalityComponent model default values.

    Source: VitalityComponent model (Material Reality Refactor).
    Represents population size and subsistence requirements.
    """

    # Default population for test entities
    # MUST match GameDefines.initial.default_population to avoid magic numbers
    # pop=1 ensures per-capita survival mechanics are tested without large denominators
    DEFAULT_POPULATION: int = 1

    # Base subsistence needs
    DEFAULT_SUBSISTENCE: float = 5.0

    # Population scales (for scenario tests with multi-actor dynamics)
    FRACTIONAL: float = 0.5  # Fractional population
    SMALL: int = 1000  # Small population
    MEDIUM: int = 500  # Medium population
    LARGE: int = 1_000_000  # Large population

    # Subsistence scales
    LOW_SUBSISTENCE: float = 2.5  # Low needs
    ELEVATED_SUBSISTENCE: float = 8.0  # Elevated needs
    HIGH_SUBSISTENCE: float = 10.0  # High needs
    DOUBLED_SUBSISTENCE: float = 20.0  # Doubled needs


@dataclass(frozen=True)
class AttritionDefaults:
    """Grinding Attrition formula constants (Mass Line Refactor Phase 3).

    Source: Coverage ratio threshold model for demographic mortality.
    The formula ensures high inequality requires more wealth to prevent deaths.

    Formula: threshold = 1 + inequality
             deficit = max(0, threshold - coverage_ratio)
             attrition_rate = clamp(deficit × (0.5 + inequality), 0, 1)
    """

    # Inequality values (Gini coefficient [0, 1])
    ZERO_INEQUALITY: float = 0.0  # Perfect equality
    LOW_INEQUALITY: float = 0.2  # Low inequality
    MODERATE_INEQUALITY: float = 0.5  # Moderate inequality
    HIGH_INEQUALITY: float = 0.8  # High inequality (requires 1.8× coverage)
    EXTREME_INEQUALITY: float = 0.95  # Near-maximum inequality

    # Coverage thresholds (1 + inequality)
    THRESHOLD_ZERO_INEQUALITY: float = 1.0  # 1 + 0.0
    THRESHOLD_HIGH_INEQUALITY: float = 1.8  # 1 + 0.8

    # Test scenario values
    POP_100: int = 100  # Standard test population
    WEALTH_100: float = 100.0  # Standard test wealth
    NEEDS_1: float = 1.0  # Unit subsistence needs

    # Attrition rate multipliers
    MULTIPLIER_ZERO_INEQUALITY: float = 0.5  # 0.5 + 0.0
    MULTIPLIER_HIGH_INEQUALITY: float = 1.3  # 0.5 + 0.8


@dataclass(frozen=True)
class OrganizationDefaults:
    """OrganizationComponent and Organization entity default values.

    Source: OrganizationComponent model + Feature 031 Organization entities.
    Represents organizational capacity, consciousness, and structure.
    """

    # Legacy OrganizationComponent defaults
    DEFAULT_COHESION: float = 0.1  # Low cohesion
    DEFAULT_CADRE: float = 0.0  # No cadre leadership

    # Organization entity defaults (Feature 031)
    DEFAULT_BUDGET: float = 0.0
    DEFAULT_HEAT: float = 0.0
    DEFAULT_LEGITIMACY: float = 0.5  # CivilSocietyOrg default

    # Subtype-specific test values
    DETROIT_PD_VIOLENCE_CAPACITY: float = 0.6
    DETROIT_PD_SURVEILLANCE_CAPACITY: float = 0.4
    FORD_EMPLOYMENT_COUNT: int = 5000
    FORD_SURPLUS_EXTRACTION: float = 0.3
    FORD_REVENUE: float = 1000.0
    RWP_CADRE_LEVEL: float = 0.7
    RWP_COHESION: float = 0.6
    CHURCH_CADRE_LEVEL: float = 0.3
    CHURCH_COHESION: float = 0.8
    CHURCH_LEGITIMACY: float = 0.7

    # IntelMethodology presets (Sparrow calibration)
    CEILING_LOCAL_PD: float = 0.2
    CEILING_FUSION: float = 0.5
    CEILING_FBI: float = 0.4

    # Consciousness formula expected values (Detroit worked example)
    RWP_CI_DELTA: float = 0.0315  # 0.15 × 0.7 × 0.6 × 0.5
    CHURCH_CI_DELTA: float = -0.0084  # -0.05 × 0.3 × 0.8 × 0.7
    FORD_CI_DELTA: float = -0.000675  # -0.05 × 0.1 × 0.9 × 0.15
    DETROIT_TOTAL_CI_DELTA: float = 0.022425  # sum of above

    # OrganizationDefines values
    ELDER_CAPACITY_FACTOR: float = 0.2
    TENDENCY_MOD_REVOLUTIONARY: float = 0.15
    TENDENCY_MOD_LIBERAL: float = -0.05
    TENDENCY_MOD_FASCIST: float = 0.10
    COHESION_LOSS_PER_KF: float = 0.2
    MIN_COHESION_THRESHOLD: float = 0.05
    CREDIBILITY_DEFAULT_FACTION: float = 0.5
    CREDIBILITY_SOVEREIGN: float = 0.8
    CREDIBILITY_CHARTERED: float = 0.6


@dataclass(frozen=True)
class SpatialDefaults:
    """SpatialComponent model default values.

    Source: SpatialComponent model.
    Represents location and mobility.
    """

    # Default values
    DEFAULT_MOBILITY: float = 0.5  # Average mobility
    LOW_MOBILITY: float = 0.2  # Low mobility (rooted)
    HIGH_MOBILITY: float = 0.8  # High mobility (nomadic)


@dataclass(frozen=True)
class AgitationDefaults:
    """Agitation values [0, inf) for George Jackson model.

    Source: IdeologicalComponent model (Sprint 3.4.3 George Jackson Refactor).
    Agitation represents raw political energy that accumulates during wage crises.
    Unlike class_consciousness/national_identity, agitation has NO upper bound.
    """

    ZERO: float = 0.0  # No crisis energy
    MIDPOINT: float = 0.5  # Low agitation
    FULL: float = 1.0  # Unit agitation (for immutability tests)
    MODERATE: float = 1.5  # Moderate crisis energy
    ELEVATED: float = 2.5  # Elevated crisis energy
    HIGH: float = 3.0  # High agitation (fascist profile test)
    CRISIS: float = 5.0  # Crisis conditions
    EXTREME: float = 100.0  # Extreme accumulation
    MAXIMUM_TEST: float = 1000.0  # Validation test (very high)


@dataclass(frozen=True)
class EventDefaults:
    """Event model default values for test scenarios.

    Source: Event models (Sprint 3.1+ event hierarchy).
    Includes tick values, deltas, and event-specific parameters.
    """

    # Tick values for event tests
    TICK_ZERO: int = 0  # Start/initial tick
    TICK_EARLY: int = 3  # Early simulation
    TICK_MID: int = 5  # Mid simulation
    TICK_SIX: int = 6  # Mid-late simulation
    TICK_SEVEN: int = 7  # Mid-late simulation
    TICK_EIGHT: int = 8  # Later simulation
    TICK_LATE: int = 10  # Later simulation
    TICK_ENDGAME: int = 12  # Late-game events

    # Consciousness deltas (transmission events)
    SMALL_DELTA: float = 0.05  # Small consciousness transmission
    MODERATE_DELTA: float = 0.1  # Moderate transmission
    LARGE_DELTA: float = 0.2  # Large transmission

    # Wage deltas (crisis events)
    WAGE_CUT_SMALL: float = -0.02  # Small wage reduction
    WAGE_CUT_MODERATE: float = -0.05  # Moderate wage reduction
    WAGE_NO_CHANGE: float = 0.0  # No wage change

    # Repression boost (subsidy events)
    REPRESSION_BOOST_LOW: float = 0.1  # Low repression boost
    REPRESSION_BOOST_MODERATE: float = 0.25  # Moderate boost
    REPRESSION_BOOST_HIGH: float = 0.5  # High boost

    # Spark probability (struggle events)
    SPARK_LOW: float = 0.25  # Low spark probability
    SPARK_MODERATE: float = 0.4  # Moderate spark probability

    # Extraction amounts (economic events)
    EXTRACTION_SMALL: float = 10.0  # Small extraction
    EXTRACTION_MODERATE: float = 15.5  # Moderate extraction
    EXTRACTION_LARGE: float = 50.0  # Large extraction
    SUBSIDY_LARGE: float = 100.0  # Large imperial subsidy

    # Solidarity spike values
    SOLIDARITY_GAIN_SMALL: float = 0.1  # Small solidarity gain
    SOLIDARITY_GAIN_MODERATE: float = 0.2  # Moderate solidarity gain
    SOLIDARITY_GAIN_LARGE: float = 0.3  # Large solidarity gain
    EDGES_AFFECTED_ONE: int = 1  # Single edge affected
    EDGES_AFFECTED_FEW: int = 2  # Few edges affected


@dataclass(frozen=True)
class Phase2GameLoopDefaults:
    """Phase 2 Game Loop integration test defaults.

    Source: Phase 2 integration tests (Sprint 6).
    Tests verify feedback loops work correctly over multiple ticks.

    Sprint 1.5: Added constants to eliminate magic numbers.
    Consolidated: Now references CanonicalThresholds where applicable.
    """

    # Entity wealth values (reference canonical midpoint)
    WORKER_BASELINE: float = Canon.P_MIDPOINT  # Default worker wealth
    OWNER_BASELINE: float = Canon.P_MIDPOINT  # Default owner wealth
    CUSTOM_WORKER_WEALTH: float = Canon.P_MODERATE  # Custom parameter test
    CUSTOM_OWNER_WEALTH: float = Canon.P_HIGH  # Custom parameter test
    LABOR_ARISTOCRACY_WEALTH: float = Canon.P_HIGH  # Wealthy worker scenario

    # Extraction efficiency (reference canonical values)
    CUSTOM_EXTRACTION: float = Canon.P_ELEVATED  # Custom parameter test
    LOW_EXTRACTION: float = Canon.P_MODERATE  # Low extraction for comparison
    HIGH_EXTRACTION: float = Canon.P_EXTREME  # High extraction for comparison
    DEFAULT_EXTRACTION: float = Canon.DEFAULT_EXTRACTION  # Reference canonical

    # Repression levels (reference canonical probability bands)
    LOW_REPRESSION: float = Canon.P_LOW  # Allows high P(S|R)
    MODERATE_REPRESSION: float = 0.2  # Moderate repression (between LOW and MODERATE)
    DEFAULT_REPRESSION: float = Canon.DEFAULT_REPRESSION  # Reference canonical
    HIGH_REPRESSION: float = Canon.P_VERY_HIGH  # Delays crossover
    VERY_HIGH_REPRESSION: float = Canon.P_EXTREME  # Keeps P(S|R) low

    # Organization levels (reference canonical probability bands)
    LOW_ORGANIZATION: float = Canon.P_MODERATE  # Low organization
    MODERATE_ORGANIZATION: float = Canon.P_MIDPOINT  # Better organized

    # P(S|R) thresholds (reference canonical probability bands)
    LOW_P_REVOLUTION: float = Canon.P_MODERATE  # Low revolution probability
    HIGH_P_REVOLUTION: float = Canon.P_MIDPOINT  # High revolution probability

    # Tension thresholds (reference canonical probability bands)
    MIN_TENSION_INCREASE: float = Canon.P_LOW  # Minimum tension for wealth gap test
    HIGH_TENSION_START: float = Canon.P_HIGH  # High tension scenario start
    NEAR_RUPTURE_TENSION: float = Canon.P_EXTREME  # Near rupture threshold
    RUPTURE_TENSION: float = Canon.P_FULL  # Rupture threshold

    # Ideology values (bipolar scale [-1, 1]) - unique to Phase2, keep as-is
    REVOLUTIONARY_IDEOLOGY: float = -0.9  # Near full revolutionary
    REACTIONARY_IDEOLOGY: float = 0.9  # Near full reactionary

    # Growth cap for stability test
    MAX_GROWTH_MULTIPLIER: float = Canon.INITIAL_RENT_POOL  # 100x growth cap

    # Tick counts (reference canonical tick values)
    SHORT_FEEDBACK_TICKS: int = Canon.TICKS_SHORT
    FEEDBACK_TICKS: int = Canon.TICKS_FEEDBACK
    MEDIUM_FEEDBACK_TICKS: int = Canon.TICKS_MEDIUM
    CROSSOVER_DETECTION_TICKS: int = Canon.TICKS_CROSSOVER
    LONG_RUN_TICKS: int = Canon.TICKS_LONG
    RUPTURE_TICKS: int = Canon.TICKS_STANDARD
    SUCCESS_CRITERIA_TICKS: int = Canon.TICKS_STANDARD


@dataclass(frozen=True)
class DynamicBalanceDefaults:
    """Dynamic Balance scenario defaults (pool drain/growth tests).

    Source: Dynamic Balance integration tests (Sprint 3.4.4).
    Tests verify the "Gas Tank" behavior: finite imperial rent pools
    force bourgeoisie agency and eventually trigger economic crisis.

    Sprint 1.5: Tolerances relaxed to account for subsistence entropy.
    """

    # Initial pool (reference canonical value)
    INITIAL_POOL: float = Canon.INITIAL_RENT_POOL

    # Entity wealth (for drain scenarios)
    P_W_WEALTH: float = 50.0  # Extraction source
    P_C_WEALTH: float = Canon.P_ZERO  # Start empty
    C_B_WEALTH: float = 50.0  # Bourgeoisie baseline
    C_W_WEALTH: float = Canon.P_ZERO  # Start empty

    # Extraction parameters for drain scenario
    EXTRACTION_EFFICIENCY_DRAIN: float = Canon.P_MODERATE  # Low extraction = less inflow
    EXTRACTION_EFFICIENCY_GROWTH: float = Canon.P_MIDPOINT  # Above decay breakeven (~0.41)
    EXTRACTION_EFFICIENCY_CRISIS: float = Canon.P_LOW  # Very low (crisis scenario)

    # Wage rates
    DRAIN_WAGE_RATE: float = 0.40  # High wages = faster drain (above max_wage_rate)
    MAX_WAGE_RATE: float = 0.35  # Maximum wage rate (GameDefines default)
    MODERATE_WAGE_RATE: float = 0.25  # Moderate wage level
    LOW_WAGE_RATE: float = 0.20  # Low wage level

    # Pool levels for crisis/policy tests
    CRISIS_POOL: float = 5.0  # Below 10% critical threshold
    AUSTERITY_POOL: float = 20.0  # Below 30% low threshold
    PROSPERITY_POOL: float = 80.0  # Above 70% high threshold
    EMPTY_POOL: float = Canon.P_ZERO  # Empty pool (extreme crisis)
    MODERATE_POOL: float = 75.0  # For serialization tests

    # Repression levels
    LOW_REPRESSION: float = 0.4  # Below default
    DEFAULT_REPRESSION: float = Canon.DEFAULT_REPRESSION  # Reference canonical

    # Tension values for policy tests
    VERY_LOW_TENSION: float = 0.2  # For bribery trigger
    HIGH_TENSION: float = Canon.P_HIGH  # For iron fist trigger

    # Tolerance constants for entropy (VitalitySystem subsistence burn)
    # Pool may shrink slightly due to rent_pool_decay and outflows
    ENTROPY_TOLERANCE_TIGHT: float = 0.95  # 5% tolerance
    ENTROPY_TOLERANCE_LOOSE: float = 0.90  # 10% tolerance

    # Assertion tolerances
    APPROX_REL_TOLERANCE: float = 0.01  # 1% relative tolerance for approx


@dataclass(frozen=True)
class ImperialCircuitDefaults:
    """Imperial Circuit scenario defaults (4-node extraction model).

    Source: Imperial Circuit integration tests (Sprint 3.4.1).
    Models the 5-phase extraction loop:
    - Phase 1: EXPLOITATION (P_w -> P_c)
    - Phase 2: TRIBUTE (P_c -> C_b, comprador keeps cut)
    - Phase 3: WAGES (C_b -> C_w, super-wages)
    - Phase 4: SUBSIDY (C_b -> P_c, client state stabilization)
    - Phase 5: DECISION (adjust wages/repression)

    Sprint 1.5: Wealth values increased to 100.0 to survive subsistence burn.
    """

    # Entity initial wealth (increased from 5.0/50.0 to survive subsistence burn)
    # All classes now start with SIGNIFICANT wealth buffer
    P_W_WEALTH: float = 100.0  # Periphery Worker (PERIPHERY_PROLETARIAT)
    P_C_WEALTH: float = 100.0  # Periphery Comprador (COMPRADOR_BOURGEOISIE, 10x burn)
    C_B_WEALTH: float = 100.0  # Core Bourgeoisie (CORE_BOURGEOISIE, 20x burn)
    C_W_WEALTH: float = 100.0  # Core Worker (LABOR_ARISTOCRACY, 5x burn)

    # Extraction parameters (from GameDefines.economy)
    EXTRACTION_EFFICIENCY: float = 0.8  # Alpha: annual extraction rate
    COMPRADOR_CUT: float = 0.15  # 15% tribute retained by comprador
    TRIBUTE_RATIO: float = 0.85  # 85% forwarded to C_b (1 - COMPRADOR_CUT)

    # Repression levels
    REPRESSION_LOW: float = 0.3  # Default P_c repression
    REPRESSION_HIGH: float = 0.9  # Stable client state (no subsidy trigger)

    # Subsidy parameters
    SUBSIDY_TRIGGER_THRESHOLD: float = 0.8  # P(S|R) >= 0.8 * P(S|A) triggers subsidy
    SUBSIDY_CONVERSION_RATE: float = 0.1  # Wealth-to-repression conversion
    SUBSIDY_CAP: float = 10.0  # Maximum subsidy per tick

    # Biocapacity (territory)
    TERRITORY_BIOCAPACITY: float = 100.0


@dataclass(frozen=True)
class RevolutionaryFinanceDefaults:
    """RevolutionaryFinance model default values.

    Source: RevolutionaryFinance model (Epoch 1 - Political Economy of Liquidity).
    Represents the fiscal capacity of revolutionary organizations:
    - war_chest: liquid funds for revolutionary activity
    - operational_burn: minimum cost per tick
    - Income streams: dues, expropriation, donors
    - Strategic concerns: heat, reformist_drift
    """

    # Default values from model
    DEFAULT_WAR_CHEST: float = 5.0  # Minimal starting funds
    DEFAULT_OPERATIONAL_BURN: float = 2.0  # Minimum spend per tick
    DEFAULT_DUES_INCOME: float = 1.0  # Member contributions
    DEFAULT_EXPROPRIATION: float = 0.0  # No direct action
    DEFAULT_DONOR_INCOME: float = 0.0  # No liberal funding
    DEFAULT_HEAT: float = 0.0  # No state attention
    DEFAULT_REFORMIST_DRIFT: float = 0.0  # Ideologically neutral

    # War chest test scenarios
    BANKRUPTCY: float = 10.0  # War chest for bankruptcy test
    MODEST_WAR_CHEST: float = 25.0  # Dict round-trip test
    MODERATE_WAR_CHEST: float = 50.0  # Full custom creation
    ELEVATED_WAR_CHEST: float = 75.0  # JSON round trip
    SIGNIFICANT_WAR_CHEST: float = 100.0  # Custom creation test
    LARGE_WAR_CHEST: float = 1_000_000.0  # Large validation test

    # Income stream test values
    DUES_LOW: float = 0.5  # NGO-style dues
    DUES_MODERATE: float = 2.0  # Balanced org
    DUES_INCOME: float = 3.0  # Full custom creation
    DUES_HIGH: float = 4.0  # JSON round trip
    DUES_MASS_ORG: float = 5.0  # Mass organization

    OPERATIONAL_BURN: float = 5.0  # Full custom / computed tests
    BURN_ELEVATED: float = 8.0  # Elevated burn rate

    DONOR_LOW: float = 1.0  # Mixed funding
    DONOR_MODERATE: float = 2.0  # JSON round trip
    DONOR_STANDARD: float = 5.0  # Full custom creation
    DONOR_HEAVY: float = 10.0  # NGO-style org

    EXPROPRIATION_LOW: float = 2.0  # Mixed funding
    EXPROPRIATION_MODERATE: float = 4.0  # Computed tests
    EXPROPRIATION_STANDARD: float = 10.0  # Full custom creation
    EXPROPRIATION_ELEVATED: float = 15.0  # JSON round trip
    EXPROPRIATION_MILITANT: float = 20.0  # Action-heavy org

    # Computed values for test scenarios
    TOTAL_INCOME_FULL: float = 18.0  # 3 + 10 + 5
    NET_FLOW_POSITIVE: float = 2.0  # 7 - 5
    BALANCED_TOTAL: float = 5.0  # 2 + 1 + 2

    # Reformist drift test values (Ideology [-1, 1])
    DRIFT_SLIGHT: float = 0.1  # Slight reformist tendency
    DRIFT_MILD: float = 0.2  # Mild reformist drift (JSON round trip)
    DRIFT_MODERATE: float = 0.3  # Moderate drift (custom creation)
    DRIFT_HIGH: float = 0.6  # High drift (NGO-style org)


# =============================================================================
# MARXIAN REPRODUCTION SCHEMA EXAMPLES (Capital Volume 2)
# =============================================================================


@dataclass(frozen=True)
class ShadowLaborDefaults:
    """Shadow labor test constants (Department III visibility).

    Source: Shadow Labor Sprint implementation.
    The visibility coefficient g_33 determines what fraction of reproductive
    labor is monetized vs. shadow (unpaid household work).

    Based on:
    - ATUS 2022 national averages (~21 hours/week care work)
    - BLS OES May 2023 (SOC 31-1120 home health aide median: $15.43/hour)
    """

    # Mock ATUS values (national averages)
    WEEKLY_HOURS: float = 21.0  # ATUS 2022 national average
    ANNUAL_HOURS: float = 1092.0  # 21 * 52 weeks

    # Shadow wage (BLS replacement cost)
    SHADOW_WAGE_HOURLY: float = _DEFINES.economy.shadow_wage_hourly  # $15.43

    # Visibility coefficients
    G_33_FULL_MONETIZED: float = 1.0  # All care work paid → no shadow
    G_33_FULL_SHADOW: float = 0.0  # All care work unpaid → max shadow
    G_33_DEFAULT: float = 0.3  # ATUS 2022 ~30% monetized

    # Test scenario: 1000 annual hours at $15.43/hour
    TEST_HOURS: float = 1000.0
    TEST_TOTAL_VALUE: float = 15430.0  # 1000 * 15.43
    TEST_SHADOW_FULL: float = 15430.0  # g_33 = 0.0 → 100% shadow
    TEST_SHADOW_NONE: float = 0.0  # g_33 = 1.0 → 0% shadow
    TEST_MARKET_DEFAULT: float = 4629.0  # g_33 = 0.3 → 30% market (15430 * 0.3)
    TEST_SHADOW_DEFAULT: float = 10801.0  # g_33 = 0.3 → 70% shadow (15430 * 0.7)


@dataclass(frozen=True)
class TensorDefaults:
    """Tensor primitive test constants (Spec 011).

    Source: Fundamental Tensor Primitive specification.
    Used for testing ValueTensor4x3, TensorRegistry, and SNLT conversion.
    """

    # -------------------------------------------------------------------------
    # Year Boundaries (data availability range)
    # -------------------------------------------------------------------------
    MIN_YEAR: int = 2010  # Earliest year with complete data
    MAX_YEAR: int = 2025  # Latest year with complete data

    # Test years within valid range
    YEAR_BASELINE: int = 2020  # Default test year
    YEAR_EARLY: int = 2015  # Early in range
    YEAR_LATE: int = 2023  # Late in range

    # Invalid years (should return NoDataSentinel)
    YEAR_TOO_EARLY: int = 1975  # Before data range
    YEAR_TOO_LATE: int = 2030  # After data range

    # -------------------------------------------------------------------------
    # SNLT Conversion Factors
    # -------------------------------------------------------------------------
    SNLT_DEFAULT: float = 1.0  # No conversion (wage-proportional proxy)
    SNLT_HIGH_PRODUCTIVITY: float = 0.90  # 10% productivity increase
    SNLT_LOW_PRODUCTIVITY: float = 1.10  # 10% productivity decrease

    # -------------------------------------------------------------------------
    # LaborHours Values (for tensor cell tests)
    # -------------------------------------------------------------------------
    LABOR_ZERO: float = 0.0  # Valid zero value
    LABOR_SMALL: float = 100.0  # Small labor allocation
    LABOR_MODERATE: float = 1000.0  # Moderate labor allocation
    LABOR_LARGE: float = 10000.0  # Large labor allocation
    LABOR_HUGE: float = 1_000_000.0  # County-scale labor

    # -------------------------------------------------------------------------
    # Department Values (Marx Capital Vol 2 aligned)
    # -------------------------------------------------------------------------
    # Simple reproduction schema (4:1 OCC, 100% exploitation)
    DEPT_I_C: float = 4000.0
    DEPT_I_V: float = 1000.0
    DEPT_I_S: float = 1000.0

    DEPT_IIA_C: float = 1600.0
    DEPT_IIA_V: float = 400.0
    DEPT_IIA_S: float = 400.0

    DEPT_IIB_C: float = 400.0
    DEPT_IIB_V: float = 100.0
    DEPT_IIB_S: float = 100.0

    DEPT_III_C: float = 500.0
    DEPT_III_V: float = 200.0
    DEPT_III_S: float = 150.0

    # -------------------------------------------------------------------------
    # Aggregation Tolerance
    # -------------------------------------------------------------------------
    AGGREGATION_TOLERANCE_REL: float = 0.0001  # 0.01% relative tolerance
    FLOAT_COMPARISON_TOLERANCE: float = 1e-9  # SC-008 floating-point comparison

    # -------------------------------------------------------------------------
    # Performance Thresholds (SC-005, SC-009, SC-010)
    # -------------------------------------------------------------------------
    GET_LATENCY_P95_MS: float = 1.0  # < 1ms for cache hit
    GET_AGGREGATE_COLD_P95_MS: float = 100.0  # < 100ms cold cache
    GET_AGGREGATE_WARM_P95_MS: float = 1.0  # < 1ms warm cache
    LOAD_100X10_SECONDS: float = 5.0  # 100 counties × 10 years

    # Memory limit (SC-006)
    MEMORY_LIMIT_MB: int = 500  # Peak RSS limit

    # -------------------------------------------------------------------------
    # Cache Configuration
    # -------------------------------------------------------------------------
    LRU_MAXSIZE_DEFAULT: int = 10_000  # Default LRU cache size
    LRU_MAXSIZE_TEST: int = 100  # Small cache for eviction tests

    # -------------------------------------------------------------------------
    # BEA Interpolation
    # -------------------------------------------------------------------------
    MAX_DELTA_YEARS: int = 5  # Maximum interpolation distance


@dataclass(frozen=True)
class MarxReproductionExamples:
    """Numerical examples from Marx's Capital Volume 2, Chapters 20-21.

    These examples validate our 4x3 Marxian reproduction schema against
    Marx's original formulations in Capital Volume 2.

    Sources:
        - Chapter 20: Simple Reproduction
        - Chapter 21: Expanded Reproduction
        - Marx's IIa/IIb subdivision for luxury vs. necessary consumption

    Note: Marx assumed uniform c/v ratio of 4:1 and s/v ratio of 1:1 (100%).
    Our implementation extends this with variable ratios per department.
    """

    # -------------------------------------------------------------------------
    # Simple Reproduction (Capital Vol. 2, Chapter 20)
    # -------------------------------------------------------------------------
    # Department I: Means of Production
    SIMPLE_I_C: float = 4000.0
    SIMPLE_I_V: float = 1000.0
    SIMPLE_I_S: float = 1000.0
    SIMPLE_I_TOTAL: float = 6000.0

    # Department II: Means of Consumption (IIa + IIb combined)
    SIMPLE_II_C: float = 2000.0
    SIMPLE_II_V: float = 500.0
    SIMPLE_II_S: float = 500.0
    SIMPLE_II_TOTAL: float = 3000.0

    # -------------------------------------------------------------------------
    # IIa/IIb Subdivision (Capital Vol. 2, Chapter 20)
    # -------------------------------------------------------------------------
    # Department IIa: Necessary Consumption (wage goods)
    SIMPLE_IIA_C: float = 1600.0
    SIMPLE_IIA_V: float = 400.0
    SIMPLE_IIA_S: float = 400.0
    SIMPLE_IIA_TOTAL: float = 2400.0

    # Department IIb: Luxury Consumption (bourgeois goods)
    SIMPLE_IIB_C: float = 400.0
    SIMPLE_IIB_V: float = 100.0
    SIMPLE_IIB_S: float = 100.0
    SIMPLE_IIB_TOTAL: float = 600.0

    # -------------------------------------------------------------------------
    # Expanded Reproduction (Capital Vol. 2, Chapter 21)
    # -------------------------------------------------------------------------
    # Department I: Means of Production (accumulating capital)
    EXPAND_I_C: float = 5000.0
    EXPAND_I_V: float = 1000.0
    EXPAND_I_S: float = 1000.0
    EXPAND_I_TOTAL: float = 7000.0

    # Department II: Means of Consumption
    EXPAND_II_C: float = 1430.0
    EXPAND_II_V: float = 285.0
    EXPAND_II_S: float = 285.0
    EXPAND_II_TOTAL: float = 2000.0

    # -------------------------------------------------------------------------
    # Marx's Theoretical Ratios (uniform in his examples)
    # -------------------------------------------------------------------------
    MARX_OCC: float = 4.0  # c/v ratio in all Marx's examples
    MARX_EXPLOITATION_RATE: float = 1.0  # s/v = 100% (s equals v)

    # -------------------------------------------------------------------------
    # Derived Ratios
    # -------------------------------------------------------------------------
    # IIb to total II ratio: 600/3000 = 20% luxury consumption
    IIB_TO_II_RATIO: float = 0.20

    # Simple reproduction equilibrium: I(v+s) = IIc
    # 1000 + 1000 = 2000 ✓
    SIMPLE_EQUILIBRIUM_LHS: float = 2000.0  # I(v+s)
    SIMPLE_EQUILIBRIUM_RHS: float = 2000.0  # IIc

    # Total economy value in simple reproduction
    SIMPLE_TOTAL_VALUE: float = 9000.0


@dataclass(frozen=True)
class Thresholds:
    __test__ = False  # Prevent pytest collection
    """Namespace for all test constants.

    Named 'Thresholds' to avoid pytest collection (classes starting with 'Test'
    are auto-collected even without test methods).

    Usage:
        from tests.constants import TestConstants
        TC = TestConstants

        # Domain-specific constants
        assert drift == TC.Behavioral.LOSS_AVERSION * base_loss
        assert consciousness > TC.Solidarity.ACTIVATION_THRESHOLD

        # Model test constants
        assert worker.wealth == TC.Wealth.DEFAULT_WEALTH
        assert tension == TC.EconomicFlow.MODERATE_TENSION

    Attributes:
        Canonical Thresholds (Source of Truth):
            Canon: Universal threshold values (pool ratios, probability bands, tick counts)

        Domain-Specific Constants:
            Behavioral: Kahneman-Tversky prospect theory constants
            Solidarity: MLM-TW solidarity transmission constants
            BourgeoisieDecision: Dynamic Balance decision thresholds
            TRPF: Tendency of the Rate of Profit to Fall constants
            Timescale: Simulation time unit constants
            MetabolicRift: Ecological limits constants

        Model Test Constants (Value-Type Organization):
            Wealth: Currency/wealth values for entity tests
            Probability: [0.0, 1.0] values for probability-based fields
            Ideology: [-1.0, +1.0] values for ideology spectrum
            Consciousness: George Jackson dual consciousness values
            Territory: Spatial/carceral geography values
            EconomicFlow: Relationship value_flow and tension values
            Quantization: Epoch 0 Physics precision values
            StateFinance: State fiscal capacity values
            GlobalEconomy: Dynamic Balance super-wage and pool values
            Precarity: PrecarityState model test values
            Vitality: VitalityComponent population and subsistence values
            Organization: OrganizationComponent cohesion and cadre values
            Spatial: SpatialComponent mobility values
            Agitation: George Jackson model agitation values [0, inf)
            Event: Event model test values (ticks, deltas, amounts)
            RevolutionaryFinance: Revolutionary organization fiscal capacity values
    """

    # Canonical thresholds (source of truth for commonly-used values)
    Canon: type[CanonicalThresholds] = CanonicalThresholds

    # Domain-specific constants (existing)
    Behavioral: type[BehavioralConstants] = BehavioralConstants
    Solidarity: type[SolidarityConstants] = SolidarityConstants
    BourgeoisieDecision: type[BourgeoisieDecisionConstants] = BourgeoisieDecisionConstants
    TRPF: type[TRPFConstants] = TRPFConstants
    Timescale: type[TimescaleConstants] = TimescaleConstants
    MetabolicRift: type[MetabolicRiftConstants] = MetabolicRiftConstants

    # Model test constants (new - value-type organization)
    Wealth: type[WealthDefaults] = WealthDefaults
    Probability: type[ProbabilityDefaults] = ProbabilityDefaults
    Ideology: type[IdeologyDefaults] = IdeologyDefaults
    Consciousness: type[ConsciousnessDefaults] = ConsciousnessDefaults
    Territory: type[TerritoryDefaults] = TerritoryDefaults
    EconomicFlow: type[EconomicFlowDefaults] = EconomicFlowDefaults
    Quantization: type[QuantizationDefaults] = QuantizationDefaults
    StateFinance: type[StateFinanceDefaults] = StateFinanceDefaults
    GlobalEconomy: type[GlobalEconomyDefaults] = GlobalEconomyDefaults
    Precarity: type[PrecarityDefaults] = PrecarityDefaults
    Vitality: type[VitalityDefaults] = VitalityDefaults
    Organization: type[OrganizationDefaults] = OrganizationDefaults
    Spatial: type[SpatialDefaults] = SpatialDefaults
    Agitation: type[AgitationDefaults] = AgitationDefaults
    Event: type[EventDefaults] = EventDefaults
    RevolutionaryFinance: type[RevolutionaryFinanceDefaults] = RevolutionaryFinanceDefaults
    Attrition: type[AttritionDefaults] = AttritionDefaults
    DynamicBalance: type[DynamicBalanceDefaults] = DynamicBalanceDefaults
    ImperialCircuit: type[ImperialCircuitDefaults] = ImperialCircuitDefaults
    Phase2: type[Phase2GameLoopDefaults] = Phase2GameLoopDefaults
    ShadowLabor: type[ShadowLaborDefaults] = ShadowLaborDefaults

    # Tensor primitive test constants (Spec 011)
    Tensor: type[TensorDefaults] = TensorDefaults

    # Marxian theory validation constants (Capital Volume 2)
    MarxReproduction: type[MarxReproductionExamples] = MarxReproductionExamples


# Alias for backwards compatibility and shorter imports
TestConstants = Thresholds


# =============================================================================
# THEORETICAL VALIDATION DATA
# =============================================================================


@dataclass(frozen=True)
class MarxCapitalExample:
    """A single example from Marx's Capital Volume 3.

    These examples demonstrate the Tendency of the Rate of Profit to Fall:
    as organic composition of capital (c/v) rises, rate of profit falls.

    Attributes:
        c: Constant capital (dead labor - machinery, raw materials)
        v: Variable capital (living labor - wages)
        s: Surplus value (unpaid labor extracted from workers)
        expected_occ: Expected organic composition = c / v
        expected_profit_rate: Expected rate of profit = s / (c + v)
        description: Human-readable description of the example
    """

    c: float
    v: float
    s: float
    expected_occ: float
    expected_profit_rate: float
    description: str


class MarxCapitalExamples:
    """Examples from Marx's Capital Volume 3, Chapter 13.

    These demonstrate TRPF: as OCC rises (more machinery per worker),
    the rate of profit falls.

    Usage in parametrized tests::

        @pytest.mark.parametrize("example", MarxCapitalExamples.all())
        def test_rate_of_profit_falls_with_occ(example):
            rate = calculate_rate_of_profit(
                surplus_value=example.s,
                constant_capital=example.c,
                variable_capital=example.v,
            )
            assert rate == pytest.approx(example.expected_profit_rate, abs=0.001)
    """

    # Early capitalism: labor-intensive production (OCC = 0.5)
    EARLY_CAPITALISM: Final[MarxCapitalExample] = MarxCapitalExample(
        c=50.0,
        v=100.0,
        s=100.0,
        expected_occ=0.5,
        expected_profit_rate=100.0 / 150.0,  # 66.67%
        description="Early capitalism (OCC=0.5, labor-intensive)",
    )

    # Balanced composition: equal dead and living labor (OCC = 1.0)
    BALANCED: Final[MarxCapitalExample] = MarxCapitalExample(
        c=100.0,
        v=100.0,
        s=100.0,
        expected_occ=1.0,
        expected_profit_rate=100.0 / 200.0,  # 50%
        description="Balanced composition (OCC=1.0)",
    )

    # Advanced capitalism: capital-intensive production (OCC = 4.0)
    ADVANCED_CAPITALISM: Final[MarxCapitalExample] = MarxCapitalExample(
        c=400.0,
        v=100.0,
        s=100.0,
        expected_occ=4.0,
        expected_profit_rate=100.0 / 500.0,  # 20%
        description="Advanced capitalism (OCC=4.0, capital-intensive)",
    )

    @classmethod
    def all(cls) -> list[MarxCapitalExample]:
        """Return all Marx examples for parametrized testing."""
        return [cls.EARLY_CAPITALISM, cls.BALANCED, cls.ADVANCED_CAPITALISM]

    @classmethod
    def all_ids(cls) -> list[str]:
        """Return pytest IDs for parametrized tests."""
        return ["occ_0.5", "occ_1.0", "occ_4.0"]


# =============================================================================
# UNIFIED CLASS SYSTEM (Feature 038)
# =============================================================================


@dataclass(frozen=True)
class ClassSystemDefaults:
    """Unified Class System test constants (Feature 038).

    Source: specs/038-unified-class-system/spec.md
    Provides wealth percentiles, precarity values, community memberships,
    and rent differential test values for the unified class system.
    """

    # -------------------------------------------------------------------------
    # Wealth Percentiles (from spec acceptance scenarios)
    # -------------------------------------------------------------------------
    WEALTH_LA: float = 75.0  # -> LABOR_ARISTOCRACY (50th-90th)
    WEALTH_PROLETARIAT: float = 25.0  # -> PROLETARIAT (< 50th, STABLE)
    WEALTH_LUMPEN: float = 10.0  # -> LUMPENPROLETARIAT (< 50th, EXCLUDED)
    WEALTH_PB: float = 95.0  # -> PETIT_BOURGEOISIE (90th-99th)
    WEALTH_BOURGEOISIE: float = 99.5  # -> BOURGEOISIE (>= 99th)
    WEALTH_LA_EXCLUDED: float = 55.0  # -> LA even with EXCLUDED precarity
    WEALTH_FIRST_NATIONS: float = 60.0  # -> filtered by trust_land_discount
    WEALTH_INCARCERATED: float = 45.0  # -> filtered to LUMPEN
    WEALTH_UNDOCUMENTED: float = 55.0  # -> filtered by doc_exclusion_factor
    WEALTH_DISABLED: float = 65.0  # -> filtered by reproduction_cost_modifier

    # -------------------------------------------------------------------------
    # Filtration Parameters (from ClassSystemDefines defaults)
    # -------------------------------------------------------------------------
    TRUST_LAND_DISCOUNT: float = 0.5
    DOCUMENTATION_EXCLUSION_FACTOR: float = 0.6
    EQUITY_FACTOR: float = 0.6
    REPRODUCTION_COST_MODIFIER: float = 1.3  # DISABLED community state

    # -------------------------------------------------------------------------
    # Solidarity Matrix Reference Values (from data-model.md)
    # -------------------------------------------------------------------------
    SOLIDARITY_PROL_PROL: float = 0.80
    SOLIDARITY_BOURG_PROL: float = 0.00
    SOLIDARITY_BOURG_BOURG: float = 0.70
    SOLIDARITY_LA_PROL: float = 0.30
    SOLIDARITY_PB_LA: float = 0.40

    # -------------------------------------------------------------------------
    # Rent Differential Test Values
    # -------------------------------------------------------------------------
    WAYNE_FIPS: str = "26163"
    OAKLAND_FIPS: str = "26125"
    MACOMB_FIPS: str = "26099"
    RENT_YEAR: int = 2022
    NAICS_MANUFACTURING: str = "31-33"
    NAICS_RETAIL: str = "44-45"

    # -------------------------------------------------------------------------
    # Dual Criteria Test Values
    # -------------------------------------------------------------------------
    V_PRODUCED_HIGH: float = 50000.0  # Above reproduction -> bourgeois relation
    V_REPRODUCTION: float = 35000.0  # Baseline reproduction cost
    V_PRODUCED_LOW: float = 20000.0  # Below reproduction -> lumpen relation
    MAGNITUDE_ZERO: float = 0.0  # Agreement magnitude
