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
) -> float:
    """Calculate consciousness drift: dΨc/dt = k(1 - Wc/Vc) - λΨc.

    Core consciousness drifts based on the material relationship
    between wages and value produced.

    Args:
        core_wages: Wages received by core worker
        value_produced: Value produced by core worker
        current_consciousness: Current consciousness level (0 to 1)
        sensitivity_k: Sensitivity coefficient for material conditions
        decay_lambda: Decay coefficient (consciousness fades without basis)

    Returns:
        Rate of change of consciousness (positive = revolutionary drift)

    Raises:
        ValueError: If value_produced is zero or negative
    """
    if value_produced <= 0:
        raise ValueError("value_produced must be > 0")

    wage_ratio = core_wages / value_produced
    material_term = sensitivity_k * (1 - wage_ratio)
    decay_term = decay_lambda * current_consciousness

    return material_term - decay_term


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
