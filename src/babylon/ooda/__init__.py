"""OODA Loop System for organizational action resolution (Feature 032).

Each tick, organizations Observe their environment, Orient to conditions,
Decide on actions, and Act — constrained by their OODA profile. This module
implements the three-layer turn resolution:

- **Layer 0**: Automatic metabolism (Business self-sustaining activity)
- **Action Phase**: Initiative-ordered organizational actions
- **Layer 3**: Consequence propagation (consciousness, heat, edges, infrastructure)

See Also:
    :mod:`babylon.engine.systems.ooda`: OODASystem orchestrator.
    ``specs/032-ooda-loop-system/spec.md``: Full specification.
"""

from babylon.ooda.action_costs import compute_action_cost
from babylon.ooda.action_eligibility import ELIGIBILITY_MAP, check_eligibility
from babylon.ooda.cycle_time import compute_cycle_time
from babylon.ooda.initiative import (
    compute_community_embeddedness,
    compute_initiative_score,
    resolve_action_order,
    update_momentum,
)
from babylon.ooda.layer0 import process_layer0
from babylon.ooda.lifecycle_capacity import compute_lifecycle_modifier, elder_legitimacy_bonus
from babylon.ooda.npc_stub import select_npc_actions
from babylon.ooda.types import (
    Action,
    ActionCostModifier,
    ActionResult,
    InitiativeScore,
    OODAProfile,
    TurnResolution,
)

__all__ = [
    "Action",
    "ActionCostModifier",
    "ActionResult",
    "ELIGIBILITY_MAP",
    "InitiativeScore",
    "OODAProfile",
    "TurnResolution",
    "check_eligibility",
    "compute_action_cost",
    "compute_lifecycle_modifier",
    "compute_community_embeddedness",
    "compute_cycle_time",
    "compute_initiative_score",
    "elder_legitimacy_bonus",
    "process_layer0",
    "resolve_action_order",
    "select_npc_actions",
    "update_momentum",
]
