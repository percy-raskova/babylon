"""Centralized test constants for Babylon formula tests.

This module provides a single source of truth for magic numbers used across
the test suite. Constants are organized by theoretical domain and documented
with their sources.

Design Principles:
    1. Test-specific constants that appear in 2+ test files
    2. Theoretical validation data (Marx's Capital, Kahneman-Tversky)
    3. Computed values (e.g., 20-year horizon = 52 ticks/year * 20 = 1040)

For production constants, see:
    - src/babylon/systems/formulas/constants.py (LOSS_AVERSION_COEFFICIENT, EPSILON)
    - src/babylon/config/defines.py (GameDefines with all tunable coefficients)

Example:
    from tests.constants import TestConstants, MarxCapitalExamples

    # Use behavioral economics constant
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

# =============================================================================
# DOMAIN-SPECIFIC CONSTANTS
# =============================================================================


@dataclass(frozen=True)
class BehavioralConstants:
    """Behavioral economics constants (Kahneman-Tversky prospect theory).

    Source: Kahneman & Tversky (1979), "Prospect Theory: An Analysis of
    Decision under Risk", Econometrica 47(2): 263-292.
    """

    # Losses are perceived as 2.25x more impactful than equivalent gains
    # This matches src/babylon/systems/formulas/constants.py:LOSS_AVERSION_COEFFICIENT
    LOSS_AVERSION: float = 2.25


@dataclass(frozen=True)
class SolidarityConstants:
    """Solidarity transmission constants (MLM-TW theory).

    The activation threshold encodes the theoretical requirement that
    consciousness must exceed a minimum level before it can transmit
    through solidarity networks.
    """

    # Minimum source consciousness for transmission
    # Matches GameDefines.solidarity.activation_threshold
    ACTIVATION_THRESHOLD: float = 0.3

    # Consciousness level for MASS_AWAKENING event
    # Matches GameDefines.solidarity.mass_awakening_threshold
    MASS_AWAKENING_THRESHOLD: float = 0.6


@dataclass(frozen=True)
class BourgeoisieDecisionConstants:
    """Pool threshold and policy delta constants for bourgeoisie decision system.

    These encode the decision matrix for Dynamic Balance (Sprint 3.4.4):
    - pool_ratio >= HIGH -> BRIBERY (if low tension)
    - pool_ratio < LOW -> AUSTERITY/IRON_FIST
    - pool_ratio < CRITICAL -> CRISIS

    All thresholds match GameDefines.economy.pool_*_threshold
    Policy deltas match GameDefines.economy.*_delta
    """

    # Pool ratio thresholds
    POOL_HIGH_THRESHOLD: float = 0.7
    POOL_LOW_THRESHOLD: float = 0.3
    POOL_CRITICAL_THRESHOLD: float = 0.1

    # Tension thresholds for decision branching
    BRIBERY_TENSION_THRESHOLD: float = 0.3  # Max tension for bribery
    IRON_FIST_TENSION_THRESHOLD: float = 0.5  # Min tension for iron fist
    TENSION_THRESHOLD: float = 0.5  # Legacy alias for iron_fist threshold

    # Policy deltas (wage and repression changes per decision)
    BRIBERY_WAGE_DELTA: float = 0.05  # Wage increase during prosperity
    AUSTERITY_WAGE_DELTA: float = -0.05  # Wage cut during low pool
    IRON_FIST_REPRESSION_DELTA: float = 0.10  # Repression boost during high tension
    CRISIS_WAGE_DELTA: float = -0.15  # Emergency wage slash
    CRISIS_REPRESSION_DELTA: float = 0.20  # Emergency repression spike


@dataclass(frozen=True)
class TRPFConstants:
    """Tendency of the Rate of Profit to Fall constants.

    Source: Marx, Capital Volume 3, Chapters 13-15.
    The TRPF surrogate models profit rate decline as time-dependent decay.
    """

    # TRPF decay coefficient per tick
    # Matches GameDefines.economy.trpf_coefficient
    TRPF_COEFFICIENT: float = 0.0005

    # Rent pool background evaporation rate
    # Matches GameDefines.economy.rent_pool_decay
    RENT_POOL_DECAY: float = 0.002

    # Minimum extraction efficiency (floor for TRPF multiplier)
    EFFICIENCY_FLOOR: float = 0.1


@dataclass(frozen=True)
class TimescaleConstants:
    """Simulation timescale constants.

    1 tick = 1 week, 52 weeks = 1 year.
    These match GameDefines.timescale.
    """

    TICKS_PER_YEAR: int = 52
    DAYS_PER_TICK: int = 7

    # Derived: 20-year simulation horizon (Epoch 1 standard)
    TWENTY_YEAR_HORIZON: int = 52 * 20  # 1040 ticks


@dataclass(frozen=True)
class MetabolicRiftConstants:
    """Ecological limits constants (Metabolic Rift).

    The metabolic rift encodes thermodynamic inefficiency in extraction
    and the cap for overshoot ratio when biocapacity is depleted.
    """

    # Extraction costs more than it yields (thermodynamic waste)
    # Matches GameDefines.metabolism.entropy_factor
    ENTROPY_FACTOR: float = 1.2

    # Cap for overshoot ratio when biocapacity is zero/negative
    # Matches GameDefines.metabolism.max_overshoot_ratio
    MAX_OVERSHOOT_RATIO: float = 999.0

    # Breakeven intensity where regeneration equals extraction
    # Formula: regeneration_rate / entropy_factor = 0.02 / 1.2 = 0.0167
    # When intensity > 0.0167, biocapacity depletes
    # When intensity < 0.0167, biocapacity regenerates
    BREAKEVEN_INTENSITY: float = 0.0167


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

    NO_FLOW: float = 0.0
    PHASE1_EXTRACTION: float = 80.0  # Phi = 100 - 20 (Phase 1 blueprint)
    INITIAL_RENT_POOL: float = 100.0  # GlobalEconomy default

    # Tension values
    NO_TENSION: float = 0.0
    LOW_TENSION: float = 0.3
    MODERATE_TENSION: float = 0.5
    HIGH_TENSION: float = 0.7
    CRITICAL_TENSION: float = 0.9

    # Solidarity strength (from topology tests)
    WEAK_SOLIDARITY: float = 0.05
    POTENTIAL_SOLIDARITY: float = 0.3  # > 0.1 to count as potential
    ACTUAL_SOLIDARITY: float = 0.5  # > 0.5 to count as actual
    STRONG_SOLIDARITY: float = 0.8


@dataclass(frozen=True)
class QuantizationDefaults:
    """Precision values for type tests (Epoch 0 Physics: 10^-6 grid).

    Source: src/babylon/systems/formulas/math.py quantization system.
    All constrained types quantize to 6 decimal places for determinism.
    Increased from 5 to support 100-year Carceral Equilibrium simulations.
    """

    GRID_PRECISION: float = 0.000001  # 10^-6
    DECIMAL_PLACES: int = 6

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

    # Pool thresholds for decision heuristics (match GameDefines)
    PROSPERITY_THRESHOLD: float = 0.7  # Pool ratio >= 0.7 = prosperity
    AUSTERITY_THRESHOLD: float = 0.3  # Pool ratio < 0.3 = austerity
    CRISIS_THRESHOLD: float = 0.1  # Pool ratio < 0.1 = crisis

    # Pool values for test scenarios (relative to INITIAL_RENT_POOL=100)
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

    # Default values
    DEFAULT_POPULATION: float = 1.0  # Single entity
    DEFAULT_SUBSISTENCE: float = 5.0  # Base subsistence needs

    # Population scales
    FRACTIONAL: float = 0.5  # Fractional population
    SMALL: float = 1000.0  # Small population
    MEDIUM: float = 500.0  # Medium population
    LARGE: float = 1_000_000.0  # Large population

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
    """OrganizationComponent model default values.

    Source: OrganizationComponent model.
    Represents organizational capacity: cohesion and cadre quality.
    """

    # Default values
    DEFAULT_COHESION: float = 0.1  # Low cohesion
    DEFAULT_CADRE: float = 0.0  # No cadre leadership


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
