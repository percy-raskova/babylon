"""The Veil of Money — theoretical disclosure tier thresholds (D7, spec-117 §5d).

Commodity fetishism as a mechanic: the player sees only prices until theory
lets them see through the money-form. Conceptual visibility is a pure
function of the org's existing doctrine state (the ADR073 accumulator — no
Unit 6 dependency), evaluated at serialization (:mod:`game.veil`).

**Gate on MONOTONIC quantities.** Both thresholds below name a doctrine node
id; the veil tier is a membership test against
``Organization.acquired_doctrine_ids`` (append-only, dedup-checked —
:func:`babylon.domain.doctrine.mechanics.acquire`), never against the
decaying ``doctrine_tags`` accumulator (0.55%/tick decay, and several tree
nodes carry NEGATIVE tag deltas) or the spendable ``theoretical_labor``
balance (drops to 0 the moment a node is bought). Either of those would let
an already-unlocked tier flicker or regress — a real bug this design avoids
by construction. See :mod:`game.veil` for the full reachability arithmetic
(I-15 calibration) and the one caveat this module's field bounds cannot
enforce (the configured node must not be a trap — Party Congress can strip a
purged trap back out of ``acquired_doctrine_ids``; pinned against the real
tree in ``tests/unit/web/test_veil.py`` since ``config.defines`` sits below
``domain`` in the Program-14 layering and may not import it here).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class VeilDefines(BaseModel):
    """Doctrine-node-id thresholds gating the Veil of Money's 3 tiers.

    Tier 0 (below ``tier1_doctrine_node_id``): the money-form only — dollar
    prices, wages, profit. Tier 1 (``tier1_doctrine_node_id`` acquired): the
    wage/imperial oppositions become legible (value_produced,
    exploitation_rate). Tier 2 (``tier2_doctrine_node_id`` acquired): the
    scissors — price/value divergence instruments, the Fundamental Theorem
    meter's full form.
    """

    model_config = ConfigDict(frozen=True)

    tier1_doctrine_node_id: str = Field(
        default="class_consciousness",
        min_length=1,
        description=(
            "Ruling D7: acquiring this doctrine node unlocks veil Tier 1 "
            "(exploitation visible — wage vs value-produced axes). Default "
            "is the free tree root (cost_tl=0), reachable the first "
            "DoctrineSystem tick for any organization regardless of "
            "cadre_level (bootstrap fires once theoretical_labor >= 0)."
        ),
    )
    tier2_doctrine_node_id: str = Field(
        default="trade_unionism",
        min_length=1,
        description=(
            "Ruling D7: acquiring this doctrine node unlocks veil Tier 2 "
            "(the scissors — price/value divergence instruments, the "
            "Fundamental Theorem meter's full form). Default costs 25 TL; "
            "at cadre_level=0.25 (the nationwide Cadre Council seed) and "
            "study_allocation=0.20 that is 25 / (0.25*0.20) = 500 ticks — "
            "reachable inside a 520-tick campaign, but earned near its end."
        ),
    )


__all__ = ["VeilDefines"]
