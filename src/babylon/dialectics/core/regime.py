r"""Fixed-point regimes: one Picard operator, three outcomes (§9.4).

Percy's "unification": a tick is one iteration of a self-consistency search
``W_{n+1} = T(W_n)``. Its convergence behaviour classifies the social form's
regime — and rupture is the THIRD REGIME of the SAME operator, not a separate
mechanism:

- **reproduction**: the principal opposition's ``|rate| <= rate_epsilon`` — the
  search converged; the form reproduces (Marx's simple reproduction).
- **crisis**: the principal gap is DEVELOPING (``rate > rate_epsilon``) and the
  field is NOT resolved at the next level — the contradiction diverges WITHIN
  its level. The existing RUPTURE gate (gap over threshold AND rising) is this
  regime's boiling point, unchanged.
- **sublation**: the gap is developing AND the level lattice's Aufhebung of the
  principal's level returns a resolving level — the contradiction has MOVED UP:
  resolved-at-a-higher-level while diverging below (quality from quantity).

This module ships only the CLASSIFIER over one tick's opposition trajectory —
no engine loop change, no convergence iteration inside a tick (the dormant
package never had one).

See Also:
    :class:`babylon.dialectics.core.level.LevelLattice`: supplies ``aufhebung_of``.
    :class:`babylon.dialectics.core.opposition.OppositionState`: the trajectory.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from babylon.dialectics.core.level import LevelLattice
    from babylon.dialectics.core.opposition import OppositionState

__all__ = ["Regime", "classify_regime"]

Regime = Literal["reproduction", "crisis", "sublation"]


def classify_regime(
    states: Sequence[OppositionState],
    lattice: LevelLattice[Mapping[str, float]] | None,
    field: Mapping[str, float],
    level_index: int,
    *,
    rate_epsilon: float,
) -> Regime:
    """Classify one tick's regime from the principal opposition's trajectory.

    Args:
        states: This tick's opposition states, exactly one marked principal.
        lattice: The level lattice for the principal's chain (None disables the
            sublation test — a rising gap can then only be crisis).
        field: The principal's per-entity gaps (e.g. county fips → capital_labor
            tension), the probe handed to ``aufhebung_of``.
        level_index: The principal's declared level index in ``lattice``.
        rate_epsilon: ``|rate|`` at or below this is CONVERGED (reproduction).

    Returns:
        ``"reproduction"``, ``"crisis"``, or ``"sublation"``.

    Notes:
        Branch ORDER is load-bearing: the reproduction gate is checked BEFORE the
        Aufhebung probe, so a converged principal whose field happens to resolve
        upward is reproduction, NOT sublation (a still contradiction has not
        moved anywhere). A fast-FALLING gap (``rate < -rate_epsilon``) is the
        contradiction being contained — the form reproduces.
    """
    principal = next((state for state in states if state.is_principal), None)
    if principal is None:
        return "reproduction"

    rate = principal.rate
    if abs(rate) <= rate_epsilon:
        return "reproduction"
    if rate < 0.0:  # |rate| > epsilon but falling: the gap is being contained
        return "reproduction"

    # rate > rate_epsilon: the principal gap is rising. Sublation (the
    # contradiction moved up a level) takes precedence over crisis (it diverges
    # within its level). aufhebung_of is only consulted here — never before the
    # reproduction gate (see Notes; §9.1 mutation probe (b) guards this order).
    if lattice is not None and lattice.aufhebung_of(level_index, [field]) is not None:
        return "sublation"
    return "crisis"
