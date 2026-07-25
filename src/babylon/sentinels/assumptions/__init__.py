"""The declared-assumptions ledger (T1.2 keel, unit K5).

Babylon's economics layer carries a small set of intentional, disclosed
simplifications standing in for data/modeling work not yet done (a flat
employment default, a national series applied uniformly per county, a proxy
formula standing in for an absent dataset). This sentinel makes them a
**declared, machine-checked registry** (:data:`~babylon.sentinels.assumptions.
registry.DECLARED_ASSUMPTIONS`) instead of tribal knowledge scattered across
recon docs and code comments — printed by ``babylon doctor``
(:func:`~babylon.sentinels.assumptions.registry.ledger_lines`) so a player or
reviewer can query "what is this run assuming?" without spelunking.

**Scope — STATIC existence only.** The check here
(:func:`~babylon.sentinels.assumptions.checks.check_code_refs_exist`) proves,
via the filesystem (no import, no execution of ``babylon.domain``/``web``),
that every declared row's cited file still exists. It does not re-verify the
claimed behavior is still accurate — that is for human review when the cited
file changes.
"""

from babylon.sentinels.assumptions.checks import check_code_refs_exist
from babylon.sentinels.assumptions.registry import (
    DECLARED_ASSUMPTIONS,
    Assumption,
    ledger_lines,
)

__all__ = [
    "DECLARED_ASSUMPTIONS",
    "Assumption",
    "check_code_refs_exist",
    "ledger_lines",
]
