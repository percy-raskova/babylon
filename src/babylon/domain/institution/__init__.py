"""Institution module for the Babylon simulation (Feature 040).

Provides pure functions for institution-level mechanics:
- structural_selectivity: Action cost modifiers based on apparatus type
- update_internal_balance: Factional balance dynamics
- hegemonic_fraction_effect: OODA orientation modulation
- community_embeddedness: Graph query for territory overlap

All functions are stateless — they take data in and return data out.
No EventBus dependency; events are returned as data for caller to emit.
"""

from babylon.domain.institution.balance import update_internal_balance
from babylon.domain.institution.ooda_effects import hegemonic_fraction_effect
from babylon.domain.institution.queries import community_embeddedness
from babylon.domain.institution.selectivity import structural_selectivity

__all__ = [
    "community_embeddedness",
    "hegemonic_fraction_effect",
    "structural_selectivity",
    "update_internal_balance",
]
