"""Phase-typed state for engine tick ordering (Spec 040 Discipline 4).

The Phase enum enforces system ordering at the type level.
Each system declares which Phase it operates in, and the engine
validates that systems only run during their declared phase.

The four phases correspond to the Marxian circuit of capital:

1. PRODUCTION:     Value creation (labor × nature)
2. DISTRIBUTION:   Value extraction and transfer (imperial rent)
3. CONSCIOUSNESS:  Ideological drift and solidarity
4. STRUGGLE:       Agency, contradiction, and rupture
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Phase(IntEnum):
    """Tick phase for system ordering.

    Systems declare their phase. The engine runs systems in phase order.
    IntEnum enables natural ordering comparisons.

    Values:
        PRODUCTION: Value creation from labor applied to nature (0)
        DISTRIBUTION: Value extraction, wages, imperial rent (1)
        CONSCIOUSNESS: Ideology drift, solidarity transmission (2)
        STRUGGLE: Agency, contradiction resolution, rupture (3)
    """

    PRODUCTION = 0
    DISTRIBUTION = 1
    CONSCIOUSNESS = 2
    STRUGGLE = 3


@dataclass(frozen=True)
class PhaseTransition:
    """Record of a phase advancement.

    Attributes:
        from_phase: The phase being left.
        to_phase: The phase being entered.
    """

    from_phase: Phase
    to_phase: Phase


def advance_phase(current: Phase) -> Phase:
    """Advance to the next phase, wrapping from STRUGGLE to PRODUCTION.

    Args:
        current: The current phase.

    Returns:
        The next phase in the cycle.
    """
    phases = list(Phase)
    idx = phases.index(current)
    return phases[(idx + 1) % len(phases)]
