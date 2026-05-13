"""Geometric weekly depreciation and equalization helpers.

Spec 062 — FR-014 / FR-015 / FR-029a. The simulation runs at a one-week tick
cadence, but federal-statistics depreciation and equalization rates are
specified annually. This module derives the per-tick rates so that 52 weekly
applications compound back to the annual rate exactly.

For an annual rate ``r`` and one-week step:

.. math::

    r_\\text{weekly} = 1 - (1 - r)^{1/52}

Compounding 52 such steps reproduces ``r``:

.. math::

    (1 - r_\\text{weekly})^{52} = 1 - r

The same form applies to both capital depreciation (delta) and capital
equalization (alpha).

See Also:
    ``specs/062-cross-scale-integration/spec.md`` FR-014/FR-015/FR-029a.
    :mod:`babylon.config.defines.economy_basic`: ``alpha_annual``,
        ``EconomyDefines.alpha_weekly`` property.
"""

from __future__ import annotations


def delta_weekly(delta_annual: float) -> float:
    """Convert an annual depreciation rate to its weekly equivalent.

    Implements FR-014/FR-015: ``delta_weekly = 1 - (1 - delta_annual)^(1/52)``.

    Args:
        delta_annual: Annual depreciation rate. Must satisfy
            ``0 <= delta_annual < 1``. The bound is strict at the upper end
            because ``delta_annual == 1`` is total depreciation in one year,
            an edge case that breaks the geometric inverse identity.

    Returns:
        Per-week depreciation rate in ``[0, 1 - eps)``.

    Raises:
        ValueError: If ``delta_annual`` is outside ``[0, 1)``.

    Example:
        >>> round(delta_weekly(0.07), 6)
        0.001397
        >>> abs((1 - delta_weekly(0.07)) ** 52 - (1 - 0.07)) < 1e-12
        True
    """
    if not 0.0 <= delta_annual < 1.0:
        raise ValueError(f"delta_annual must be in [0, 1); got {delta_annual!r}")
    return float(1.0 - (1.0 - delta_annual) ** (1.0 / 52.0))


def alpha_weekly(alpha_annual: float) -> float:
    """Convert an annual equalization rate to its weekly equivalent.

    Same geometric form as :func:`delta_weekly`. Required by FR-029a
    startup invariant ``alpha_weekly < 1/52``.

    Args:
        alpha_annual: Annual equalization rate. Must satisfy
            ``0 <= alpha_annual < 1``.

    Returns:
        Per-week equalization rate.

    Raises:
        ValueError: If ``alpha_annual`` is outside ``[0, 1)``.

    Example:
        >>> round(alpha_weekly(0.01), 7)
        0.0001932
        >>> alpha_weekly(0.01) < 1 / 52
        True
    """
    if not 0.0 <= alpha_annual < 1.0:
        raise ValueError(f"alpha_annual must be in [0, 1); got {alpha_annual!r}")
    return float(1.0 - (1.0 - alpha_annual) ** (1.0 / 52.0))


__all__ = ["delta_weekly", "alpha_weekly"]
