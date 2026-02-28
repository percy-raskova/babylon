"""Test fixtures and factory helpers for OODA unit tests (Feature 032)."""

from __future__ import annotations

from typing import Any

from babylon.models.enums import ActionType, DecisionMode, OrgType
from babylon.ooda.types import Action, OODAProfile


def make_ooda_profile(**overrides: Any) -> OODAProfile:
    """Create an OODAProfile with sensible defaults, applying overrides.

    Args:
        **overrides: Fields to override on the default OODAProfile.

    Returns:
        Frozen OODAProfile instance.
    """
    defaults: dict[str, Any] = {
        "sensor_latency": 1,
        "ideological_coherence": 0.5,
        "analytical_capacity": 0.5,
        "decision_mode": DecisionMode.DEMOCRATIC,
        "bureaucratic_depth": 0.3,
        "action_points": 3,
        "coordination_range": 1,
        "autonomy": 0.5,
    }
    defaults.update(overrides)
    return OODAProfile(**defaults)


def make_action(
    org_id: str = "org_1",
    action_type: ActionType = ActionType.EDUCATE,
    target_id: str = "community_1",
    **overrides: Any,
) -> Action:
    """Create an Action with sensible defaults, applying overrides.

    Args:
        org_id: Acting organization ID.
        action_type: Action type to perform.
        target_id: Target ID.
        **overrides: Additional field overrides.

    Returns:
        Frozen Action instance.
    """
    defaults: dict[str, Any] = {
        "org_id": org_id,
        "action_type": action_type,
        "target_id": target_id,
    }
    defaults.update(overrides)
    return Action(**defaults)


def make_org_node(
    org_id: str = "org_1",
    org_type: OrgType = OrgType.POLITICAL_FACTION,
    **attrs: Any,
) -> dict[str, Any]:
    """Create a dict representing an organization graph node.

    Args:
        org_id: Node ID.
        org_type: Organization type.
        **attrs: Additional node attributes.

    Returns:
        Dict with standard org node attributes.
    """
    node: dict[str, Any] = {
        "_node_type": "organization",
        "id": org_id,
        "org_type": org_type.value,
        "cohesion": 0.7,
        "cadre_level": 0.5,
        "consciousness_tendency": "revolutionary",
        "budget": 100.0,
        "heat": 0.0,
    }
    node.update(attrs)
    return node


def make_community_node(
    community_id: str = "community_1",
    **attrs: Any,
) -> dict[str, Any]:
    """Create a dict representing a community graph node.

    Args:
        community_id: Node ID.
        **attrs: Additional node attributes.

    Returns:
        Dict with standard community node attributes.
    """
    node: dict[str, Any] = {
        "_node_type": "community",
        "id": community_id,
        "community_type": "new_afrikan",
        "collective_identity": 0.3,
        "dominant_tendency": "revolutionary",
        "ideological_contestation": 0.2,
        "infrastructure": 0.5,
    }
    node.update(attrs)
    return node
