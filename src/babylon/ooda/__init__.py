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

from babylon.ooda.action_eligibility import ELIGIBILITY_MAP, check_eligibility
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
]
