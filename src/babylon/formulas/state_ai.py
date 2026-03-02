"""State AI formulas (Feature 039).

Provides the faction shift calculation that adjusts FactionBalance weights
based on player heat and events. Heat drives Security-State weight upward;
dropping heat allows reversion toward Finance-Capital dominance.

See Also:
    ``specs/039-state-apparatus-ai/contracts/faction-balance.md``: F-01 through F-05.
    :class:`babylon.config.defines.StateApparatusAIDefines`: Shift limits.
"""

from __future__ import annotations

from babylon.config.defines import StateApparatusAIDefines
from babylon.models.entities.state_apparatus_ai import FactionBalance


def calculate_faction_shift(
    heat: float,
    current_balance: FactionBalance,
    defines: StateApparatusAIDefines,
) -> FactionBalance:
    """Calculate faction balance shift driven by player heat.

    Higher heat increases Security-State weight at the expense of
    Finance-Capital and Settler-Populist. The shift per tick is
    clamped to ``defines.max_faction_shift_per_tick``.

    When heat is low (< 0.3), a gradual reversion toward the default
    equilibrium occurs.

    Args:
        heat: Player threat level [0.0, 1.0].
        current_balance: Current FactionBalance.
        defines: State AI configuration with shift limits.

    Returns:
        New FactionBalance with shifted weights.
    """
    max_shift = defines.max_faction_shift_per_tick
    fc = current_balance.finance_capital
    ss = current_balance.security_state
    sp = current_balance.settler_populist

    if heat > 0.5:
        # High heat: Security-State gains at expense of others
        shift_amount = min(max_shift, (heat - 0.5) * 0.2)
        ss_new = min(1.0, ss + shift_amount)
        # Distribute loss proportionally between FC and SP
        loss = ss_new - ss
        fc_share = fc / (fc + sp) if (fc + sp) > 0 else 0.5
        fc_new = max(0.0, fc - loss * fc_share)
        sp_new = max(0.0, sp - loss * (1.0 - fc_share))
    elif heat < 0.3:
        # Low heat: gradual reversion toward equilibrium
        shift_amount = min(max_shift, (0.3 - heat) * 0.1)
        ss_new = max(0.0, ss - shift_amount * 0.5)
        gain = ss - ss_new
        fc_new = fc + gain * 0.6  # FC recovers faster
        sp_new = sp + gain * 0.4
    else:
        # Moderate heat: no shift
        return current_balance

    # Normalize to sum to 1.0
    total = fc_new + ss_new + sp_new
    if total > 0:
        fc_new /= total
        ss_new /= total
        sp_new /= total
    else:
        fc_new = 1.0 / 3.0
        ss_new = 1.0 / 3.0
        sp_new = 1.0 / 3.0

    return FactionBalance(
        finance_capital=round(fc_new, 6),
        security_state=round(ss_new, 6),
        settler_populist=round(sp_new, 6),
        stability=current_balance.stability,
        legitimacy=current_balance.legitimacy,
    )


__all__ = ["calculate_faction_shift"]
