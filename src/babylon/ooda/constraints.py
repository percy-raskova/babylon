"""OODA profile constraints for action validation (Feature 032).

Enforces action points budget, coordination range limits, and
the autonomy-effectiveness tradeoff.

See Also:
    ``specs/032-ooda-loop-system/contracts/action-resolution-contract.md``
"""

from __future__ import annotations

from babylon.config.defines import OODADefines
from babylon.ooda.types import Action, ActionResult, OODAProfile

_MAX_ACTIONS_PER_ORG = 20  # Upper bound for loop safety


def enforce_action_points(
    actions: list[Action],
    profile: OODAProfile,
) -> tuple[list[Action], list[ActionResult]]:
    """Greedily accept actions until AP budget is exhausted.

    Actions are processed in order. Each accepted action deducts its
    cost from remaining AP. Actions exceeding budget are rejected.

    Args:
        actions: Ordered list of proposed actions.
        profile: OODAProfile with action_points budget.

    Returns:
        Tuple of (accepted actions, rejected ActionResults).
    """
    remaining_ap = profile.action_points
    accepted: list[Action] = []
    rejected: list[ActionResult] = []

    for action in actions[:_MAX_ACTIONS_PER_ORG]:
        if action.action_point_cost <= remaining_ap:
            accepted.append(action)
            remaining_ap -= action.action_point_cost
        else:
            rejected.append(
                ActionResult(
                    action=action,
                    success=False,
                    failure_reason=f"Insufficient AP: need {action.action_point_cost}, have {remaining_ap}",
                )
            )

    return accepted, rejected


def enforce_coordination_range(
    actions: list[Action],
    profile: OODAProfile,
) -> tuple[list[Action], list[ActionResult]]:
    """Reject actions targeting more distinct territories than coordination_range.

    Args:
        actions: List of proposed actions.
        profile: OODAProfile with coordination_range limit.

    Returns:
        Tuple of (accepted actions, rejected ActionResults).
    """
    seen_targets: set[str] = set()
    accepted: list[Action] = []
    rejected: list[ActionResult] = []

    for action in actions[:_MAX_ACTIONS_PER_ORG]:
        target = action.target_id
        if target in seen_targets or len(seen_targets) < profile.coordination_range:
            if target not in seen_targets:
                seen_targets.add(target)
            accepted.append(action)
        else:
            rejected.append(
                ActionResult(
                    action=action,
                    success=False,
                    failure_reason=(
                        f"Coordination range exceeded: limit {profile.coordination_range}, "
                        f"already targeting {len(seen_targets)} distinct locations"
                    ),
                )
            )

    return accepted, rejected


def apply_autonomy_modifier(
    num_distinct_targets: int,
    autonomy: float,
    defines: OODADefines,
) -> float:
    """Compute effectiveness modifier from the autonomy-breadth tradeoff.

    Higher autonomy allows targeting more locations but reduces per-target
    effectiveness. The floor is 0.1 (never fully ineffective).

    Args:
        num_distinct_targets: Number of distinct target locations.
        autonomy: Organization's autonomy value [0, 1].
        defines: OODADefines with autonomy_effectiveness_scale.

    Returns:
        Effectiveness modifier in [0.1, 1.0].
    """
    if num_distinct_targets <= 1:
        return 1.0

    raw = 1.0 - autonomy * defines.autonomy_effectiveness_scale * (
        (num_distinct_targets - 1) / num_distinct_targets
    )
    return max(raw, 0.1)


__all__ = [
    "apply_autonomy_modifier",
    "enforce_action_points",
    "enforce_coordination_range",
]
