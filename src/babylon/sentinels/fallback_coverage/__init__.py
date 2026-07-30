"""Fallback-coverage sentinel — the two verdict-surface gates (ADR176 r.25).

Closes the family's next declared-but-unheard blind spot: ``reachability``
catches *the gate reads what nobody writes*; **this catches *the event fires
and the player never hears it*** — dropped at the bus->pydantic boundary
(no ``EVENT_BUILDERS`` entry), or rendered as the generic field-list line
(no bespoke chronicle summary). Every gap carries a cited disposition row;
coverage arriving for a ledgered member reds the gate until the row retires.

Registry: :mod:`babylon.sentinels.fallback_coverage.registry` · checks:
:mod:`babylon.sentinels.fallback_coverage.checks` · run:
``uv run python tools/sentinel_check.py fallback-coverage --check`` /
``mise run check:fallback-coverage``.
"""

from babylon.sentinels.fallback_coverage.checks import main
from babylon.sentinels.fallback_coverage.registry import (
    BUS_BOUNDARY_LEDGER,
    CHRONICLE_LEDGER,
    EventCoverageRow,
    Governance,
)

__all__ = [
    "BUS_BOUNDARY_LEDGER",
    "CHRONICLE_LEDGER",
    "EventCoverageRow",
    "Governance",
    "main",
]
