"""Class Wealth Dynamics ODE System.

Empirically derived from FRED Distributional Financial Accounts (DFA)
data (2015-2025). Models wealth flows between four Marxian classes:

- Core Bourgeoisie (Top 1%)
- Petty Bourgeoisie (90-99%)
- Labor Aristocracy (50-90%)
- Internal Proletariat (Bottom 50%)

Key Finding: Wealth distribution is remarkably stable:
- Top 1% maintains ~30% homeostasis (self-reinforcing)
- 90-99% slowly loses ground (-0.3%/year)
- Bottom classes gain slightly through redistribution

First-Order System:
    dW₁/dt = α₄₁W₄ + α₃₁W₃ + α₂₁W₂ - δ₁W₁
    dW₂/dt = α₃₂W₃ + α₄₂W₄ - α₂₁W₂ - δ₂W₂
    dW₃/dt = α₄₃W₄ + γ₃ - α₃₁W₃ - α₃₂W₃ - δ₃W₃
    dW₄/dt = -(dW₁ + dW₂ + dW₃)  [constraint: ΣWᵢ = 1]

Second-Order Terms:
    d²Wᵢ/dt² = βᵢ(dWᵢ/dt) - ωᵢ²(Wᵢ - Wᵢ*)

See Also:
    tools/analyze_wealth_distribution.py for data derivation
    FRED DFA: https://www.federalreserve.gov/releases/z1/dataviz/dfa/
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ClassDynamicsParams:
    """Parameters for class wealth dynamics ODE system.

    All rates are per-tick (convert from quarterly by dividing by ticks_per_quarter).

    Attributes:
        alpha_41: Extraction rate from proletariat to bourgeoisie.
        alpha_31: Extraction rate from labor aristocracy to bourgeoisie.
        alpha_21: Extraction rate from petty bourgeoisie to bourgeoisie.
        alpha_32: Rent-seeking from labor aristocracy to petty bourgeoisie.
        alpha_42: Extraction from proletariat to petty bourgeoisie.
        alpha_43: Extraction from proletariat to labor aristocracy.
        delta_1: Redistribution rate from bourgeoisie (taxation).
        delta_2: Redistribution rate from petty bourgeoisie.
        delta_3: Redistribution rate from labor aristocracy.
        gamma_3: Imperial rent formation rate (superwages).

    Examples:
        >>> params = ClassDynamicsParams()
        >>> params.gamma_3
        0.0057
    """

    # Extraction rates (per quarter, fitted from FRED 2015-2025)
    alpha_41: float = 0.0000  # proletariat → bourgeoisie
    alpha_31: float = 0.0000  # labor aristocracy → bourgeoisie
    alpha_21: float = 0.0006  # petty bourgeoisie → bourgeoisie
    alpha_32: float = 0.0000  # labor aristocracy → petty bourgeoisie
    alpha_42: float = 0.0000  # proletariat → petty bourgeoisie
    alpha_43: float = 0.0000  # proletariat → labor aristocracy

    # Redistribution rates (progressive taxation, inheritance)
    delta_1: float = 0.0010  # from bourgeoisie
    delta_2: float = 0.0020  # from petty bourgeoisie
    delta_3: float = 0.0010  # from labor aristocracy

    # Imperial rent formation (superwages to core workers)
    gamma_3: float = 0.0057  # quarterly injection rate


@dataclass(frozen=True)
class SecondOrderParams:
    """Second-order dynamics parameters for momentum effects.

    Attributes:
        beta: Damping coefficients (negative = mean-reverting).
        omega: Natural frequencies of oscillation.
        equilibrium: Attractor wealth shares (W*).

    Examples:
        >>> params = SecondOrderParams()
        >>> params.equilibrium
        (0.305, 0.382, 0.294, 0.02)
    """

    beta: tuple[float, float, float, float] = (-0.10, -0.15, -0.10, -0.05)
    omega: tuple[float, float, float, float] = (0.05, 0.08, 0.05, 0.03)
    equilibrium: tuple[float, float, float, float] = (0.305, 0.382, 0.294, 0.020)


def calculate_wealth_flow(
    source_share: float,
    extraction_rate: float,
    resistance: float = 0.0,
) -> float:
    """Calculate per-tick wealth flow from source class.

    Args:
        source_share: Source class wealth share [0, 1].
        extraction_rate: Base extraction coefficient.
        resistance: Class consciousness resistance [0, 1].

    Returns:
        Wealth delta flowing out of source class.

    Examples:
        >>> calculate_wealth_flow(0.5, 0.01, 0.0)
        0.005
        >>> calculate_wealth_flow(0.5, 0.01, 0.5)  # 50% resistance
        0.0025
    """
    return extraction_rate * source_share * (1 - resistance)


def calculate_class_dynamics_derivative(
    wealth_shares: tuple[float, float, float, float],
    params: ClassDynamicsParams | None = None,
    resistances: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
) -> tuple[float, float, float, float]:
    """Compute dW/dt for all four classes (first-order system).

    Implements:
        dW₁/dt = α₄₁W₄ + α₃₁W₃ + α₂₁W₂ - δ₁W₁
        dW₂/dt = α₃₂W₃ + α₄₂W₄ - α₂₁W₂ - δ₂W₂
        dW₃/dt = α₄₃W₄ + γ₃ - α₃₁W₃ - α₃₂W₃ - δ₃W₃
        dW₄/dt = -(dW₁ + dW₂ + dW₃)

    Args:
        wealth_shares: (W₁, W₂, W₃, W₄) current wealth shares summing to 1.
        params: ODE system parameters (uses defaults if None).
        resistances: (r₁, r₂, r₃, r₄) class consciousness levels [0, 1].

    Returns:
        (dW₁/dt, dW₂/dt, dW₃/dt, dW₄/dt) derivatives.

    Examples:
        >>> shares = (0.30, 0.36, 0.30, 0.04)
        >>> dW = calculate_class_dynamics_derivative(shares)
        >>> abs(sum(dW)) < 1e-10  # Sum constraint
        True
    """
    if params is None:
        params = ClassDynamicsParams()

    w1, w2, w3, w4 = wealth_shares
    r1, r2, r3, r4 = resistances

    # Flows into W1 (bourgeoisie)
    dw1 = (
        params.alpha_41 * w4 * (1 - r4)
        + params.alpha_31 * w3 * (1 - r3)
        + params.alpha_21 * w2 * (1 - r2)
        - params.delta_1 * w1
    )

    # Flows into W2 (petty bourgeoisie)
    dw2 = (
        params.alpha_32 * w3 * (1 - r3)
        + params.alpha_42 * w4 * (1 - r4)
        - params.alpha_21 * w2 * (1 - r2)
        - params.delta_2 * w2
    )

    # Flows into W3 (labor aristocracy)
    dw3 = (
        params.alpha_43 * w4 * (1 - r4)
        + params.gamma_3  # Imperial rent injection
        - params.alpha_31 * w3 * (1 - r3)
        - params.alpha_32 * w3 * (1 - r3)
        - params.delta_3 * w3
    )

    # W4 determined by constraint (sum to zero)
    dw4 = -dw1 - dw2 - dw3

    return (dw1, dw2, dw3, dw4)


def calculate_wealth_acceleration(
    wealth_share: float,
    velocity: float,
    equilibrium: float,
    damping: float = -0.1,
    frequency: float = 0.05,
) -> float:
    """Compute d²W/dt² for second-order dynamics.

    Models momentum effects and oscillation around equilibrium:
        d²W/dt² = β(dW/dt) - ω²(W - W*)

    Args:
        wealth_share: Current wealth share W.
        velocity: First derivative dW/dt.
        equilibrium: Target equilibrium wealth share W*.
        damping: Damping coefficient (negative = mean-reverting).
        frequency: Natural frequency of oscillation.

    Returns:
        Second derivative d²W/dt².

    Examples:
        >>> result = calculate_wealth_acceleration(0.32, 0.001, 0.30, -0.1, 0.05)
        >>> round(result, 10)
        -0.00015
    """
    return damping * velocity - (frequency**2) * (wealth_share - equilibrium)


def calculate_full_dynamics(
    wealth_shares: tuple[float, float, float, float],
    velocities: tuple[float, float, float, float],
    params: ClassDynamicsParams | None = None,
    second_order: SecondOrderParams | None = None,
    resistances: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
) -> tuple[tuple[float, float, float, float], tuple[float, float, float, float]]:
    """Compute both first and second order derivatives.

    Combines first-order wealth flows with second-order momentum dynamics.

    Args:
        wealth_shares: (W₁, W₂, W₃, W₄) current wealth shares.
        velocities: (dW₁/dt, dW₂/dt, dW₃/dt, dW₄/dt) current velocities.
        params: First-order ODE parameters.
        second_order: Second-order parameters.
        resistances: Class consciousness levels.

    Returns:
        Tuple of (first_derivatives, second_derivatives).

    Examples:
        >>> shares = (0.305, 0.382, 0.294, 0.020)
        >>> vels = (0.0, -0.001, 0.0006, 0.0004)
        >>> dW, d2W = calculate_full_dynamics(shares, vels)
    """
    if params is None:
        params = ClassDynamicsParams()
    if second_order is None:
        second_order = SecondOrderParams()

    # First-order derivatives
    dw = calculate_class_dynamics_derivative(wealth_shares, params, resistances)

    # Second-order derivatives
    d2w = tuple(
        calculate_wealth_acceleration(
            wealth_shares[i],
            velocities[i],
            second_order.equilibrium[i],
            second_order.beta[i],
            second_order.omega[i],
        )
        for i in range(4)
    )

    return dw, d2w  # type: ignore[return-value]


def calculate_equilibrium_deviation(
    wealth_shares: tuple[float, float, float, float],
    equilibrium: tuple[float, float, float, float] | None = None,
) -> float:
    """Calculate total deviation from equilibrium wealth distribution.

    Useful for detecting when the system is far from steady state.

    Args:
        wealth_shares: Current wealth shares.
        equilibrium: Target equilibrium (defaults to FRED-fitted values).

    Returns:
        Sum of squared deviations from equilibrium.

    Examples:
        >>> result = calculate_equilibrium_deviation((0.30, 0.38, 0.29, 0.03))
        >>> 0.0001 < result < 0.0003
        True
    """
    if equilibrium is None:
        equilibrium = SecondOrderParams().equilibrium

    return sum((w - e) ** 2 for w, e in zip(wealth_shares, equilibrium, strict=True))


def invert_wealth_to_population(
    wealth_shares: tuple[float, float, float, float],
    target_wealth_pct: float = 33.333,
) -> float:
    """Find population percentile owning target wealth percentage.

    Inverts the wealth distribution to find what fraction of the population
    owns a given fraction of total wealth. Uses linear interpolation.

    Args:
        wealth_shares: (top_1%, 90-99%, 50-90%, bottom_50%) shares.
        target_wealth_pct: Target cumulative wealth percentage.

    Returns:
        Population percentile owning up to target_wealth_pct of wealth.

    Examples:
        >>> shares = (30.7, 36.4, 30.3, 2.5)
        >>> result = invert_wealth_to_population(shares, 33.333)
        >>> 90.0 < result < 91.0
        True
    """
    # Build cumulative distribution (population, wealth)
    # From bottom to top
    cumulative = [
        (50.0, wealth_shares[3]),  # Bottom 50%
        (90.0, wealth_shares[3] + wealth_shares[2]),  # + 50-90%
        (99.0, wealth_shares[3] + wealth_shares[2] + wealth_shares[1]),  # + 90-99%
        (100.0, 100.0),  # + Top 1%
    ]

    # Handle edge cases
    if target_wealth_pct <= cumulative[0][1]:
        if cumulative[0][1] <= 0:
            return 0.0
        return cumulative[0][0] * (target_wealth_pct / cumulative[0][1])

    if target_wealth_pct >= 100.0:
        return 100.0

    # Linear interpolation
    for i in range(len(cumulative) - 1):
        pop1, wealth1 = cumulative[i]
        pop2, wealth2 = cumulative[i + 1]

        if wealth1 <= target_wealth_pct <= wealth2:
            if wealth2 == wealth1:
                return pop1
            ratio = (target_wealth_pct - wealth1) / (wealth2 - wealth1)
            return pop1 + ratio * (pop2 - pop1)

    return 100.0
