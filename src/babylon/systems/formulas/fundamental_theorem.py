"""Fundamental Theorem of MLM-TW.

Core formulas:

- Imperial Rent: Phi = alpha * Wp * (1 - Psi_p)
- Labor Aristocracy: Wc/Vc > 1
- Consciousness Drift: dPsi/dt = k(1 - Wc/Vc) - lambda*Psi + bifurcation
"""

from babylon.systems.formulas.constants import LOSS_AVERSION_COEFFICIENT


def calculate_imperial_rent(
    alpha: float,
    periphery_wages: float,
    periphery_consciousness: float,
) -> float:
    """Phi = alpha * Wp * (1 - Psi_p). Value extracted from periphery.

    Args:
        alpha: Extraction efficiency [0, 1].
        periphery_wages: Periphery wage share [0, 1].
        periphery_consciousness: Resistance level (1 = full resistance).

    Returns:
        Imperial rent value (>= 0).

    Examples:
        >>> calculate_imperial_rent(0.5, 0.3, 0.2)
        0.12
        >>> calculate_imperial_rent(0.8, 0.6, 1.0)  # Full consciousness
        0.0
    """
    return max(0.0, alpha * periphery_wages * (1 - periphery_consciousness))


def calculate_labor_aristocracy_ratio(
    core_wages: float,
    value_produced: float,
) -> float:
    """Wc/Vc ratio. When > 1, worker receives more than produced.

    Args:
        core_wages: Wages received.
        value_produced: Value produced.

    Returns:
        Labor aristocracy ratio.

    Raises:
        ValueError: If value_produced <= 0.

    Examples:
        >>> calculate_labor_aristocracy_ratio(120.0, 100.0)
        1.2
    """
    if value_produced <= 0:
        raise ValueError("value_produced must be > 0")
    return core_wages / value_produced


def is_labor_aristocracy(core_wages: float, value_produced: float) -> bool:
    """True if Wc/Vc > 1 (receives more than produces).

    Args:
        core_wages: Wages received.
        value_produced: Value produced.

    Returns:
        True if labor aristocracy.

    Raises:
        ValueError: If value_produced <= 0.

    Examples:
        >>> is_labor_aristocracy(120.0, 100.0)
        True
        >>> is_labor_aristocracy(80.0, 100.0)
        False
    """
    if value_produced <= 0:
        raise ValueError("value_produced must be > 0")
    return core_wages > value_produced


def _apply_bifurcation(
    base_drift: float,
    wage_change: float,
    solidarity_pressure: float,
) -> float:
    """Apply Fascist Bifurcation when wages fall."""
    if wage_change >= 0:
        return base_drift

    agitation = abs(wage_change) * LOSS_AVERSION_COEFFICIENT
    if solidarity_pressure > 0:
        return base_drift + agitation * min(1.0, solidarity_pressure)
    return base_drift - agitation


def calculate_consciousness_drift(
    core_wages: float,
    value_produced: float,
    current_consciousness: float,
    sensitivity_k: float,
    decay_lambda: float,
    solidarity_pressure: float = 0.0,
    wage_change: float = 0.0,
) -> float:
    """dPsi/dt = k(1 - Wc/Vc) - lambda*Psi + bifurcation.

    Args:
        core_wages: Wages received.
        value_produced: Value produced.
        current_consciousness: Current level [0, 1].
        sensitivity_k: Material conditions sensitivity.
        decay_lambda: Consciousness decay rate.
        solidarity_pressure: Incoming SOLIDARITY strength.
        wage_change: Wage delta (negative = crisis).

    Returns:
        Consciousness drift rate (positive = revolutionary).

    Raises:
        ValueError: If value_produced <= 0.
    """
    if value_produced <= 0:
        raise ValueError("value_produced must be > 0")

    wage_ratio = core_wages / value_produced
    base_drift = sensitivity_k * (1 - wage_ratio) - decay_lambda * current_consciousness

    return _apply_bifurcation(base_drift, wage_change, solidarity_pressure)
