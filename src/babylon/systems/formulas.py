"""Mathematical formulas for the Babylon simulation.

This module contains the pure mathematical functions that drive
the dialectical mechanics of the simulation. These are deterministic
functions with no side effects - the same inputs always produce
the same outputs.

Key Formulas:
1. Fundamental Theorem of MLM-TW:
   - Imperial Rent: Φ(Wp, Ψp) = α × Wp × (1 - Ψp)
   - Labor Aristocracy: Wc/Vc > 1
   - Consciousness Drift: dΨc/dt = k(1 - Wc/Vc) - λΨc

2. Survival Calculus:
   - Acquiescence: P(S|A) = 1 / (1 + e^(-k(x - x_critical)))
   - Revolution: P(S|R) = Cohesion / (Repression + ε)
   - Loss Aversion: λ = 2.25

3. Unequal Exchange:
   - Exchange Ratio: ε = (Lp/Lc) × (Wc/Wp)
   - Prebisch-Singer Effect
"""

import math
from typing import Final

# Constants
LOSS_AVERSION_COEFFICIENT: Final[float] = 2.25
EPSILON: Final[float] = 1e-6  # Small constant to prevent division by zero


# =============================================================================
# FUNDAMENTAL THEOREM FUNCTIONS
# =============================================================================


def calculate_imperial_rent(
    alpha: float,
    periphery_wages: float,
    periphery_consciousness: float,
) -> float:
    """Calculate Imperial Rent: Φ(Wp, Ψp) = α × Wp × (1 - Ψp).

    Imperial Rent is the value extracted from the periphery that
    flows to the core, enabling the labor aristocracy.

    Args:
        alpha: Extraction efficiency coefficient (0 to 1)
        periphery_wages: Periphery wage share (0 to 1)
        periphery_consciousness: Periphery consciousness/resistance
                                 (0 = submissive, 1 = revolutionary)

    Returns:
        Imperial rent value (always >= 0)

    Examples:
        >>> calculate_imperial_rent(0.5, 0.3, 0.2)
        0.12
        >>> calculate_imperial_rent(1.0, 0.5, 0.0)
        0.5
        >>> calculate_imperial_rent(0.0, 0.5, 0.5)
        0.0
        >>> calculate_imperial_rent(0.8, 0.6, 1.0)  # Full consciousness = no extraction
        0.0
    """
    rent = alpha * periphery_wages * (1 - periphery_consciousness)
    return max(0.0, rent)


def calculate_labor_aristocracy_ratio(
    core_wages: float,
    value_produced: float,
) -> float:
    """Calculate labor aristocracy ratio: Wc/Vc.

    When this ratio > 1, the worker receives more than they produce,
    with the difference coming from Imperial Rent.

    Args:
        core_wages: Wages received by core worker
        value_produced: Value produced by core worker

    Returns:
        Labor aristocracy ratio

    Raises:
        ValueError: If value_produced is zero or negative

    Examples:
        >>> calculate_labor_aristocracy_ratio(120.0, 100.0)  # Labor aristocracy
        1.2
        >>> calculate_labor_aristocracy_ratio(80.0, 100.0)   # Exploited worker
        0.8
        >>> calculate_labor_aristocracy_ratio(100.0, 100.0)  # Fair exchange
        1.0
    """
    if value_produced <= 0:
        raise ValueError("value_produced must be > 0")
    return core_wages / value_produced


def is_labor_aristocracy(
    core_wages: float,
    value_produced: float,
) -> bool:
    """Determine if a worker is part of the labor aristocracy.

    A worker is labor aristocracy when Wc/Vc > 1, meaning they
    receive more in wages than the value they produce.

    Args:
        core_wages: Wages received by core worker
        value_produced: Value produced by core worker

    Returns:
        True if worker is labor aristocracy

    Raises:
        ValueError: If value_produced is zero or negative

    Examples:
        >>> is_labor_aristocracy(120.0, 100.0)
        True
        >>> is_labor_aristocracy(80.0, 100.0)
        False
        >>> is_labor_aristocracy(100.0, 100.0)  # Exact equality = not aristocracy
        False
    """
    if value_produced <= 0:
        raise ValueError("value_produced must be > 0")
    return core_wages > value_produced


def calculate_consciousness_drift(
    core_wages: float,
    value_produced: float,
    current_consciousness: float,
    sensitivity_k: float,
    decay_lambda: float,
    solidarity_pressure: float = 0.0,
    wage_change: float = 0.0,
) -> float:
    """Calculate consciousness drift with Fascist Bifurcation mechanic.

    Base formula: dΨc/dt = k(1 - Wc/Vc) - λΨc

    Extended with Fascist Bifurcation (Sprint 3.4.2b):
    When wages are FALLING (wage_change < 0), crisis creates "agitation energy"
    that channels into either:
    - Revolution (if solidarity_pressure > 0) - negative drift
    - Fascism (if solidarity_pressure = 0) - positive drift via loss aversion

    This encodes the historical insight: "Agitation without solidarity
    produces fascism, not revolution." (Germany 1933 vs Russia 1917)

    Args:
        core_wages: Wages received by core worker
        value_produced: Value produced by core worker
        current_consciousness: Current consciousness level (0 to 1)
        sensitivity_k: Sensitivity coefficient for material conditions
        decay_lambda: Decay coefficient (consciousness fades without basis)
        solidarity_pressure: Sum of incoming SOLIDARITY edge strengths [0, 1+]
        wage_change: Change in wages since last tick (negative = falling)

    Returns:
        Rate of change of consciousness (positive = revolutionary drift,
        negative = reactionary/fascist drift when wages fall without solidarity)

    Raises:
        ValueError: If value_produced is zero or negative
    """
    if value_produced <= 0:
        raise ValueError("value_produced must be > 0")

    wage_ratio = core_wages / value_produced
    material_term = sensitivity_k * (1 - wage_ratio)
    decay_term = decay_lambda * current_consciousness

    base_drift = material_term - decay_term

    # Fascist Bifurcation mechanic
    # Only triggers when wages are FALLING (crisis conditions)
    if wage_change < 0:
        # Agitation energy = magnitude of wage loss × loss aversion
        agitation_energy = abs(wage_change) * LOSS_AVERSION_COEFFICIENT

        if solidarity_pressure > 0:
            # Solidarity channels crisis into revolutionary consciousness
            # The more solidarity, the more effective the channeling
            crisis_modifier = agitation_energy * min(1.0, solidarity_pressure)
            # Positive modifier = revolutionary drift (consciousness increases)
            base_drift += crisis_modifier
        else:
            # No solidarity - crisis channels into fascism via loss aversion
            # Workers blame foreigners/immigrants instead of capital
            # Negative modifier = reactionary drift (consciousness decreases)
            base_drift -= agitation_energy

    return base_drift


# =============================================================================
# SURVIVAL CALCULUS FUNCTIONS
# =============================================================================


def calculate_acquiescence_probability(
    wealth: float,
    subsistence_threshold: float,
    steepness_k: float,
) -> float:
    """Calculate P(S|A) = 1 / (1 + e^(-k(x - x_critical))).

    Sigmoid function modeling survival through compliance.
    At the threshold, probability is 0.5 (coin flip).

    Args:
        wealth: Current wealth/resources
        subsistence_threshold: Minimum needed for survival (x_critical)
        steepness_k: Steepness of survival curve

    Returns:
        Probability of survival through acquiescence [0, 1]

    Examples:
        >>> calculate_acquiescence_probability(100.0, 100.0, 0.1)  # At threshold
        0.5
        >>> p = calculate_acquiescence_probability(150.0, 100.0, 0.1)  # Above threshold
        >>> p > 0.99
        True
        >>> p = calculate_acquiescence_probability(50.0, 100.0, 0.1)  # Below threshold
        >>> p < 0.01
        True
    """
    exponent = -steepness_k * (wealth - subsistence_threshold)
    # Clamp exponent to prevent overflow
    exponent = max(-500, min(500, exponent))
    return 1.0 / (1.0 + math.exp(exponent))


def calculate_revolution_probability(
    cohesion: float,
    repression: float,
) -> float:
    """Calculate P(S|R) = Cohesion / (Repression + ε).

    Survival through collective action depends on organization
    outpacing state repression.

    Args:
        cohesion: Unity and organization level (0 to 1)
        repression: State violence capacity (0 to 1)

    Returns:
        Probability of survival through revolution [0, 1]

    Examples:
        >>> calculate_revolution_probability(0.8, 0.2)  # Strong org, weak state
        1.0
        >>> round(calculate_revolution_probability(0.2, 0.8), 2)  # Weak org, strong state
        0.25
        >>> calculate_revolution_probability(0.0, 0.5)  # No organization
        0.0
        >>> p = calculate_revolution_probability(0.5, 0.5)  # Balanced
        >>> p > 0.99
        True
    """
    if cohesion <= 0:
        return 0.0

    probability = cohesion / (repression + EPSILON)
    return min(1.0, probability)  # Clamp to valid probability


def calculate_crossover_threshold(
    cohesion: float,
    repression: float,
    subsistence_threshold: float,
    steepness_k: float,
) -> float:
    """Find wealth level where P(S|R) = P(S|A) (revolution becomes rational).

    This is the critical point where collective action becomes
    a rational survival strategy.

    Args:
        cohesion: Unity and organization level
        repression: State violence capacity
        subsistence_threshold: Subsistence threshold for acquiescence
        steepness_k: Steepness of acquiescence curve

    Returns:
        Wealth level at crossover point
    """
    # P(S|R) is constant given cohesion and repression
    p_revolution = calculate_revolution_probability(cohesion, repression)

    # Solve for wealth where P(S|A) = P(S|R)
    # P(S|A) = 1 / (1 + e^(-k(x - threshold))) = p_revolution
    # 1 / p_revolution = 1 + e^(-k(x - threshold))
    # 1 / p_revolution - 1 = e^(-k(x - threshold))
    # ln(1/p_revolution - 1) = -k(x - threshold)
    # x = threshold - ln(1/p_revolution - 1) / k

    if p_revolution <= 0 or p_revolution >= 1:
        # Edge cases: no valid crossover
        return 0.0 if p_revolution <= 0 else 1.0

    ln_term = math.log(1.0 / p_revolution - 1.0)
    crossover = subsistence_threshold - ln_term / steepness_k

    return max(0.0, min(1.0, crossover))


def apply_loss_aversion(value: float) -> float:
    """Apply Kahneman-Tversky loss aversion (λ = 2.25).

    Losses are perceived as 2.25x more impactful than equivalent gains.
    This affects decision-making under risk.

    Args:
        value: Raw value change (negative = loss, positive = gain)

    Returns:
        Perceived value after loss aversion

    Examples:
        >>> apply_loss_aversion(100.0)  # Gains unchanged
        100.0
        >>> apply_loss_aversion(-100.0)  # Losses amplified
        -225.0
        >>> apply_loss_aversion(0.0)  # Zero unchanged
        0.0
    """
    if value < 0:
        return value * LOSS_AVERSION_COEFFICIENT
    return value


# =============================================================================
# UNEQUAL EXCHANGE FUNCTIONS
# =============================================================================


def calculate_exchange_ratio(
    periphery_labor_hours: float,
    core_labor_hours: float,
    core_wage: float,
    periphery_wage: float,
) -> float:
    """Calculate exchange ratio: ε = (Lp/Lc) × (Wc/Wp).

    The exchange ratio quantifies unequal exchange.
    When ε > 1, the periphery gives more value than it receives.

    Args:
        periphery_labor_hours: Labor hours in periphery
        core_labor_hours: Labor hours in core for same product
        core_wage: Core wage rate
        periphery_wage: Periphery wage rate

    Returns:
        Exchange ratio

    Raises:
        ValueError: If any denominator value is zero or negative

    Examples:
        >>> calculate_exchange_ratio(100.0, 100.0, 20.0, 5.0)  # Equal labor, 4x wage gap
        4.0
        >>> calculate_exchange_ratio(200.0, 100.0, 20.0, 10.0)  # 2x labor, 2x wage
        4.0
        >>> calculate_exchange_ratio(100.0, 100.0, 10.0, 10.0)  # Fair exchange
        1.0
    """
    if core_labor_hours <= 0:
        raise ValueError("core_labor_hours must be > 0")
    if periphery_wage <= 0:
        raise ValueError("periphery_wage must be > 0")

    labor_ratio = periphery_labor_hours / core_labor_hours
    wage_ratio = core_wage / periphery_wage

    return labor_ratio * wage_ratio


def calculate_exploitation_rate(exchange_ratio: float) -> float:
    """Convert exchange ratio to exploitation rate percentage.

    ε = 2 means 100% exploitation (double value extracted).
    ε = 1 means 0% exploitation (fair exchange).

    Args:
        exchange_ratio: The exchange ratio ε

    Returns:
        Exploitation rate as a percentage
    """
    return (exchange_ratio - 1) * 100


def calculate_value_transfer(
    production_value: float,
    exchange_ratio: float,
) -> float:
    """Calculate value transferred from periphery to core.

    Value transfer = production × (1 - 1/ε)

    Args:
        production_value: Value of peripheral production
        exchange_ratio: The exchange ratio ε

    Returns:
        Value transferred to core
    """
    if exchange_ratio <= 0:
        return 0.0

    transfer_fraction = 1 - (1 / exchange_ratio)
    return production_value * transfer_fraction


def prebisch_singer_effect(
    initial_price: float,
    production_increase: float,
    elasticity: float,
) -> float:
    """Calculate Prebisch-Singer effect on commodity prices.

    Terms of trade decline for commodity exporters:
    More production → lower prices → same poverty.

    Args:
        initial_price: Initial commodity price
        production_increase: Fractional increase in production (0.2 = 20%)
        elasticity: Price elasticity of demand (typically negative)

    Returns:
        New price after production increase
    """
    # Price change = elasticity × production change
    # (simplified model of supply-demand dynamics)
    price_change_fraction = elasticity * production_increase
    new_price = initial_price * (1 + price_change_fraction)

    return max(0.0, new_price)


# =============================================================================
# SOLIDARITY TRANSMISSION FUNCTIONS (Sprint 3.4.2)
# =============================================================================


def calculate_solidarity_transmission(
    source_consciousness: float,
    target_consciousness: float,
    solidarity_strength: float,
    activation_threshold: float = 0.3,
) -> float:
    """Calculate consciousness transmission via solidarity edges.

    Formula: dPsi_target = sigma * (Psi_source - Psi_target)

    Where:
    - sigma = solidarity_strength (STORED ON EDGE, not auto-calculated)
    - Psi_source = source_consciousness (periphery worker)
    - Psi_target = target_consciousness (core worker)

    Transmission only occurs if:
    1. source_consciousness > activation_threshold (strictly greater)
    2. solidarity_strength > 0

    This implements the Fascist Bifurcation scenario:
    - Periphery revolts BUT solidarity_strength=0 -> NO transmission (Fascist turn)
    - Periphery revolts AND solidarity_strength>0 -> Transmission (Revolutionary turn)

    Args:
        source_consciousness: Consciousness level of source (periphery worker) [0, 1]
        target_consciousness: Consciousness level of target (core worker) [0, 1]
        solidarity_strength: Strength of solidarity infrastructure on edge [0, 1]
        activation_threshold: Minimum source consciousness for transmission (default 0.3)

    Returns:
        Change in target consciousness (delta). Can be negative if target has
        higher consciousness than source.

    Examples:
        >>> round(calculate_solidarity_transmission(0.8, 0.2, 0.5), 2)  # High source, low target
        0.3
        >>> calculate_solidarity_transmission(0.2, 0.5, 0.5)  # Below threshold
        0.0
        >>> calculate_solidarity_transmission(0.8, 0.2, 0.0)  # No solidarity
        0.0
        >>> round(calculate_solidarity_transmission(0.5, 0.8, 0.5), 2)  # Target > source
        -0.15
    """
    # No transmission if source is not in active struggle
    # Threshold is exclusive (>) - must be strictly above to transmit
    if source_consciousness <= activation_threshold:
        return 0.0

    # No transmission if no solidarity infrastructure exists
    if solidarity_strength <= 0:
        return 0.0

    # Calculate transmission delta
    delta = solidarity_strength * (source_consciousness - target_consciousness)

    return delta


# =============================================================================
# IDEOLOGICAL ROUTING FUNCTIONS (Sprint 3.4.3 - George Jackson Refactor)
# =============================================================================


def calculate_ideological_routing(
    wage_change: float,
    solidarity_pressure: float,
    current_class_consciousness: float,
    current_national_identity: float,
    current_agitation: float,
    agitation_decay: float = 0.1,
) -> tuple[float, float, float]:
    """Calculate ideological routing from crisis conditions.

    Sprint 3.4.3 (George Jackson Refactor): This formula implements the
    multi-dimensional consciousness routing mechanic.

    Key insight: "Fascism is the defensive form of capitalism."
    - Agitation (from wage fall) + Solidarity -> Class Consciousness
    - Agitation (from wage fall) + No Solidarity -> National Identity

    Args:
        wage_change: Change in wages since last tick (negative = crisis)
        solidarity_pressure: Sum of incoming SOLIDARITY edge strengths [0, inf)
        current_class_consciousness: Current class consciousness [0, 1]
        current_national_identity: Current national identity [0, 1]
        current_agitation: Current accumulated agitation [0, inf)
        agitation_decay: Rate at which agitation decays per tick (default 0.1)

    Returns:
        Tuple of (new_class_consciousness, new_national_identity, new_agitation)

    Example:
        Worker with falling wages and high solidarity routes to revolutionary::

            cc, ni, ag = calculate_ideological_routing(
                wage_change=-20.0,
                solidarity_pressure=0.9,
                current_class_consciousness=0.5,
                current_national_identity=0.5,
                current_agitation=0.0,
            )
            # cc will increase, ni will stay flat

        Worker with falling wages and no solidarity routes to fascism::

            cc, ni, ag = calculate_ideological_routing(
                wage_change=-20.0,
                solidarity_pressure=0.0,
                current_class_consciousness=0.5,
                current_national_identity=0.5,
                current_agitation=0.0,
            )
            # ni will increase, cc will stay flat
    """
    # Start with current values
    new_class = current_class_consciousness
    new_nation = current_national_identity
    new_agitation = current_agitation

    # Calculate agitation from wage crisis
    # Only negative wage changes create agitation (crisis conditions)
    if wage_change < 0:
        # Agitation energy = magnitude of wage loss * loss aversion coefficient
        agitation_generated = abs(wage_change) * LOSS_AVERSION_COEFFICIENT
        new_agitation += agitation_generated

    # Route accumulated agitation based on solidarity
    if new_agitation > 0:
        # Solidarity factor determines routing split [0, 1]
        solidarity_factor = min(1.0, solidarity_pressure)

        # Calculate how much agitation routes to each axis
        # High solidarity -> more to class consciousness
        # Low solidarity -> more to national identity
        class_delta = new_agitation * solidarity_factor * 0.1  # Scaling factor
        nation_delta = new_agitation * (1.0 - solidarity_factor) * 0.1

        # Apply deltas with clamping
        new_class = min(1.0, new_class + class_delta)
        new_nation = min(1.0, new_nation + nation_delta)

        # Agitation is consumed as it routes
        # Some agitation decays naturally each tick
        new_agitation = max(0.0, new_agitation * (1.0 - agitation_decay))

    return (new_class, new_nation, new_agitation)


# =============================================================================
# DYNAMIC BALANCE FUNCTIONS (Sprint 3.4.4)
# =============================================================================


class BourgeoisieDecision:
    """Enumeration of bourgeoisie decision types.

    Sprint 3.4.4: Dynamic Balance - The "Driver" decisions based on
    imperial rent pool level and aggregate class tension.
    """

    NO_CHANGE = "no_change"
    BRIBERY = "bribery"
    AUSTERITY = "austerity"
    IRON_FIST = "iron_fist"
    CRISIS = "crisis"


def calculate_bourgeoisie_decision(
    pool_ratio: float,
    aggregate_tension: float,
    high_threshold: float = 0.7,
    low_threshold: float = 0.3,
    critical_threshold: float = 0.1,
) -> tuple[str, float, float]:
    """Calculate bourgeoisie policy decision based on pool level and tension.

    Sprint 3.4.4: Dynamic Balance - The bourgeoisie as a rational actor
    responding to material conditions.

    Decision Matrix:
        pool_ratio >= high AND tension < 0.3 -> BRIBERY (increase wages +5%)
        pool_ratio < critical -> CRISIS (wages to minimum, repression +20%)
        pool_ratio < low AND tension > 0.5 -> IRON_FIST (repression +10%)
        pool_ratio < low AND tension <= 0.5 -> AUSTERITY (wages -5%)
        else -> NO_CHANGE (maintain status quo)

    Args:
        pool_ratio: Current pool / initial pool (0.0 to 1.0+)
        aggregate_tension: Average tension across class relationships (0.0 to 1.0)
        high_threshold: Pool ratio above which prosperity is declared (default 0.7)
        low_threshold: Pool ratio below which austerity begins (default 0.3)
        critical_threshold: Pool ratio below which crisis fires (default 0.1)

    Returns:
        Tuple of (decision: str, wage_delta: float, repression_delta: float)
        - decision: One of BourgeoisieDecision values
        - wage_delta: Change to wage rate (positive = increase)
        - repression_delta: Change to repression level (positive = increase)

    Example:
        # Prosperity: high pool, low tension -> increase wages
        decision, wage_d, repr_d = calculate_bourgeoisie_decision(0.8, 0.2)
        # Returns ("bribery", 0.05, 0.0)

        # Crisis: pool below critical -> emergency measures
        decision, wage_d, repr_d = calculate_bourgeoisie_decision(0.05, 0.5)
        # Returns ("crisis", -0.15, 0.20)
    """
    # Standard deltas for each policy
    bribery_wage_increase = 0.05
    austerity_wage_cut = -0.05
    iron_fist_repression_boost = 0.10
    crisis_wage_slash = -0.15
    crisis_repression_spike = 0.20

    # Decision logic priority (crisis first, then by pool level)

    # CRISIS: Pool critically low - emergency measures regardless of tension
    if pool_ratio < critical_threshold:
        return (
            BourgeoisieDecision.CRISIS,
            crisis_wage_slash,
            crisis_repression_spike,
        )

    # PROSPERITY: High pool - can afford bribery if tension is low
    if pool_ratio >= high_threshold and aggregate_tension < 0.3:
        return (
            BourgeoisieDecision.BRIBERY,
            bribery_wage_increase,
            0.0,
        )

    # AUSTERITY ZONE: Low pool - choose between iron fist and wage cuts
    if pool_ratio < low_threshold:
        if aggregate_tension > 0.5:
            # High tension + low resources = repression
            return (
                BourgeoisieDecision.IRON_FIST,
                0.0,
                iron_fist_repression_boost,
            )
        else:
            # Low tension + low resources = can cut wages safely
            return (
                BourgeoisieDecision.AUSTERITY,
                austerity_wage_cut,
                0.0,
            )

    # NEUTRAL ZONE: Mid-range pool - maintain status quo
    return (BourgeoisieDecision.NO_CHANGE, 0.0, 0.0)


# =============================================================================
# METABOLIC RIFT FUNCTIONS (Slice 1.4)
# =============================================================================


def calculate_biocapacity_delta(
    regeneration_rate: float,
    max_biocapacity: float,
    extraction_intensity: float,
    current_biocapacity: float,
    entropy_factor: float = 1.2,
) -> float:
    """Calculate change in biocapacity stock: ΔB = R - (E × η).

    The core metabolic formula. Extraction always costs more than
    the raw value obtained due to entropy/waste (η > 1.0).

    Args:
        regeneration_rate: Fraction of max_biocapacity restored per tick [0, 1]
        max_biocapacity: Maximum biocapacity ceiling
        extraction_intensity: Current extraction pressure [0, 1]
        current_biocapacity: Current biocapacity stock
        entropy_factor: Waste multiplier for extraction (default 1.2)

    Returns:
        Change in biocapacity (positive = regeneration, negative = depletion)

    Examples:
        >>> calculate_biocapacity_delta(0.02, 100.0, 0.0, 50.0)  # No extraction
        2.0
        >>> calculate_biocapacity_delta(0.02, 100.0, 0.05, 50.0)  # Light extraction
        -1.0
        >>> calculate_biocapacity_delta(0.02, 100.0, 0.0, 100.0)  # At max, no regen
        0.0
    """
    # Regeneration logic: Linear up to max
    regeneration = regeneration_rate * max_biocapacity

    # If already at/above max, no regen
    if current_biocapacity >= max_biocapacity:
        regeneration = 0.0

    # Extraction logic (scales with availability)
    raw_extraction = extraction_intensity * current_biocapacity

    # Entropy penalty
    ecological_cost = raw_extraction * entropy_factor

    delta = regeneration - ecological_cost
    return delta


def calculate_overshoot_ratio(
    total_consumption: float,
    total_biocapacity: float,
) -> float:
    """Calculate ecological overshoot ratio: O = C / B.

    When O > 1.0, consumption exceeds biocapacity (overshoot).
    When O <= 1.0, the system is within ecological limits.

    Args:
        total_consumption: Total consumption needs across all entities
        total_biocapacity: Total available biocapacity

    Returns:
        Overshoot ratio (>1.0 = ecological overshoot)

    Examples:
        >>> calculate_overshoot_ratio(100.0, 200.0)  # Sustainable
        0.5
        >>> calculate_overshoot_ratio(200.0, 100.0)  # Overshoot
        2.0
        >>> calculate_overshoot_ratio(100.0, 0.0)  # Depleted biocapacity
        999.0
    """
    if total_biocapacity <= 0:
        return 999.0  # Cap at high value instead of inf

    return total_consumption / total_biocapacity
