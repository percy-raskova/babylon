"""Tendency of the Rate of Profit to Fall (TRPF) formulas.

Marx's TRPF from Capital Volume 3 describes capitalism's central contradiction:
as organic composition of capital (c/v) rises, the rate of profit falls.

Epoch 1 Implementation:
    TRPF Surrogate - time-based decay of extraction efficiency.
    Models effect without full OCC tracking.

Epoch 2 Implementation (Planned):
    Full OCC tracking with constant_capital/variable_capital on entities.
    See ai-docs/epoch2-trpf.yaml for specification.

See Also:
    :doc:`/reference/trpf` for full theoretical background
    ai-docs/theory.md for Marx's original formulation
"""

from __future__ import annotations


def calculate_trpf_multiplier(
    tick: int,
    trpf_coefficient: float,
    floor: float = 0.1,
) -> float:
    """Calculate TRPF efficiency multiplier (Epoch 1 Surrogate).

    Models Marx's Tendency of the Rate of Profit to Fall as a
    time-dependent decay of extraction efficiency. This is a
    surrogate for proper organic composition tracking.

    The multiplier declines linearly from 1.0 at tick 0, representing
    how rising organic composition of capital reduces profit rates
    over time under capitalist accumulation.

    Args:
        tick: Current simulation tick (0-indexed)
        trpf_coefficient: Decay rate per tick (default 0.0005)
        floor: Minimum multiplier (default 0.1 = 10% efficiency floor)

    Returns:
        Multiplier in range [floor, 1.0]

    Example:
        >>> calculate_trpf_multiplier(0, 0.0005)
        1.0
        >>> calculate_trpf_multiplier(1000, 0.0005)
        0.5
        >>> calculate_trpf_multiplier(2000, 0.0005)
        0.1

    Note:
        At default coefficient 0.0005:
        - tick 0: 100% efficiency
        - tick 520 (10 years): 74% efficiency
        - tick 1040 (20 years): 48% efficiency
        - tick 1800+: floors at 10% efficiency

        Full OCC-based TRPF calculation planned for Epoch 2.
        See ai-docs/epoch2-trpf.yaml for specification.

    Theoretical Basis:
        Marx, Capital Vol. 3, Chapters 13-15:
        Rate of Profit p' = s / (c + v)
        As OCC (c/v) rises, p' falls even with constant exploitation rate (s/v).
    """
    raw_multiplier = 1.0 - (trpf_coefficient * tick)
    return max(floor, raw_multiplier)


def calculate_rent_pool_decay(
    current_pool: float,
    decay_rate: float,
) -> float:
    """Apply TRPF rent pool decay (background evaporation).

    Models the tendency of accumulated surplus to erode over time,
    representing the contradiction between the tendency to accumulate
    and the tendency of profit rates to fall.

    Args:
        current_pool: Current imperial rent pool value
        decay_rate: Per-tick decay rate (default 0.002 = 0.2%)

    Returns:
        Decayed pool value (always >= 0)

    Example:
        >>> calculate_rent_pool_decay(100.0, 0.002)
        99.8
        >>> calculate_rent_pool_decay(100.0, 0.0)
        100.0

    Note:
        At default decay 0.002:
        - After 52 ticks (1 year): ~90% remaining
        - After 520 ticks (10 years): ~35% remaining
        - After 1040 ticks (20 years): ~12% remaining
    """
    if decay_rate <= 0:
        return current_pool
    return max(0.0, current_pool * (1.0 - decay_rate))


# Epoch 2 placeholder - will be implemented with OCC tracking
def calculate_rate_of_profit(
    surplus_value: float,
    constant_capital: float,
    variable_capital: float,
) -> float:
    """Calculate Marx's rate of profit: p' = s / (c + v).

    This is the Epoch 2 formula for proper OCC-based TRPF calculation.
    Currently a placeholder - full implementation in Epoch 2.

    Args:
        surplus_value: Value extracted beyond wages (s)
        constant_capital: Investment in machinery, materials (c)
        variable_capital: Wages paid to labor (v)

    Returns:
        Rate of profit as decimal (0.0 to 1.0+)

    Example:
        >>> calculate_rate_of_profit(100, 50, 100)  # Marx's first example
        0.6666666666666666
        >>> calculate_rate_of_profit(100, 400, 100)  # Marx's third example
        0.2

    Note:
        Full implementation requires:
        - constant_capital/variable_capital fields on Bourgeoisie entities
        - surplus_extracted tracking per tick
        - OCC dynamics (automation investments shifting c/v ratio)

        See ai-docs/epoch2-trpf.yaml for specification.
    """
    total_capital = constant_capital + variable_capital
    if total_capital <= 0:
        return 0.0
    return surplus_value / total_capital


def calculate_organic_composition(
    constant_capital: float,
    variable_capital: float,
) -> float:
    """Calculate organic composition of capital: OCC = c / v.

    The organic composition represents the ratio of "dead labor"
    (machinery, materials) to "living labor" (wages). As capitalism
    develops, OCC tends to rise.

    This is the Epoch 2 formula. Currently a placeholder.

    Args:
        constant_capital: Investment in machinery, materials (c)
        variable_capital: Wages paid to labor (v)

    Returns:
        Organic composition ratio (0.0 to infinity)

    Example:
        >>> calculate_organic_composition(50, 100)
        0.5
        >>> calculate_organic_composition(400, 100)
        4.0

    Note:
        Higher OCC means more capital-intensive production.
        In Marx's examples:
        - OCC = 0.5: Early capitalism (labor-intensive)
        - OCC = 4.0: Advanced capitalism (capital-intensive)
    """
    if variable_capital <= 0:
        return 0.0
    return constant_capital / variable_capital
