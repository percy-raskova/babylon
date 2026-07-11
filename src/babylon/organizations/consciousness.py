"""Consciousness tendency modifier (Feature 031 survivor).

The Feature-031 five-factor trio (``derive_credibility``,
``consciousness_effect``, ``aggregate_consciousness_effects``) was retired
by the fork-reconciliation ledger (F7, owner-ratified 2026-07-10): the live
Feature-032 path ``babylon.ooda.action_effects`` is its strict superset
(membership-overlap credibility, action-type multipliers, per-tick clamp).
``tendency_modifier`` remains — it is imported live by the 032 path.
"""

from __future__ import annotations

from babylon.config.defines import OrganizationDefines
from babylon.models.enums import ConsciousnessTendency


def tendency_modifier(
    tendency: ConsciousnessTendency,
    defines: OrganizationDefines,
) -> float:
    """Resolve tendency modifier from defines."""
    modifier_map = {
        ConsciousnessTendency.REVOLUTIONARY: defines.tendency_modifier_revolutionary,
        ConsciousnessTendency.LIBERAL: defines.tendency_modifier_liberal,
        ConsciousnessTendency.FASCIST: defines.tendency_modifier_fascist,
    }
    return modifier_map[tendency]
