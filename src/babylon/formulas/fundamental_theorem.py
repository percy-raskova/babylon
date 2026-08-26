"""Fundamental Theorem of MLM-TW.

Core formulas:

- Imperial Rent (extraction flow): Phi = alpha * Wp * (1 - Psi_p)
- Imperial Rent Gap (absolute, U2): Phi = Wc - Vc
- Labor Aristocracy: Wc/Vc > 1
"""


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


def calculate_imperial_rent_gap(core_wages: float, value_produced: float) -> float:
    """Phi = Wc - Vc, the Fundamental Theorem's absolute (dollar) gap.

    The subtraction-form companion to :func:`calculate_labor_aristocracy_ratio`
    (a ratio): matches the reference calibration surface
    ``view_imperial_rent.imperial_rent_millions`` exactly
    (``wages_core_millions - value_produced_millions``, ``data-catalog.yaml``
    over ``fact_productivity_annual``) — see
    ``tests/unit/reference/test_marxian_views.py`` for the cross-check
    against that view's real BLS-derived numbers (Constitution III.12
    redundant verification). Unlike the ratio/boolean/drift formulas in this
    module, subtraction has no singularity at ``value_produced == 0``, so
    no guard/raise is needed.

    Args:
        core_wages: Wages received (Wc).
        value_produced: Value produced (Vc).

    Returns:
        Phi = core_wages - value_produced. Positive: the imperial bribe
        (paid more than produced). Negative: super-exploitation (produced
        more than paid).

    Examples:
        >>> calculate_imperial_rent_gap(120.0, 100.0)
        20.0
        >>> calculate_imperial_rent_gap(60.0, 100.0)
        -40.0
    """
    return core_wages - value_produced


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
