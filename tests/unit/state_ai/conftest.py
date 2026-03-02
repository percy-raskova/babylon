"""Test fixtures and factory helpers for state AI unit tests (Feature 039)."""

from __future__ import annotations

from typing import Any

from babylon.models.entities.attention_thread import AttentionThread, SparrowAnalysis
from babylon.models.entities.state_apparatus_ai import (
    FactionBalance,
    LegalFramework,
    StateAction,
    StateBudget,
)
from babylon.models.enums import (
    OrgType,
    StateActionType,
    StateFaction,
    SurveillanceMethod,
    ThreadPhase,
)


def make_faction_balance(**overrides: Any) -> FactionBalance:
    """Create a FactionBalance with Detroit 2010 defaults.

    Args:
        **overrides: Fields to override on the default FactionBalance.

    Returns:
        Frozen FactionBalance instance.
    """
    defaults: dict[str, Any] = {
        "finance_capital": 0.45,
        "security_state": 0.30,
        "settler_populist": 0.25,
        "stability": 0.6,
        "legitimacy": 0.5,
    }
    defaults.update(overrides)
    return FactionBalance(**defaults)


def make_state_budget(**overrides: Any) -> StateBudget:
    """Create a StateBudget with sensible defaults.

    Args:
        **overrides: Fields to override on the default StateBudget.

    Returns:
        Frozen StateBudget instance.
    """
    defaults: dict[str, Any] = {
        "revenue": 100.0,
        "available": 100.0,
        "allocated": {
            StateActionType.ADMINISTER: 20.0,
            StateActionType.DEVELOP: 25.0,
            StateActionType.RESEARCH: 5.0,
            StateActionType.CO_OPT: 20.0,
            StateActionType.REPRESS: 25.0,
            StateActionType.WITHDRAW: 5.0,
        },
        "imperial_rent_pool": 50.0,
    }
    defaults.update(overrides)
    return StateBudget(**defaults)


def make_state_action(**overrides: Any) -> StateAction:
    """Create a StateAction with sensible defaults.

    Args:
        **overrides: Fields to override on the default StateAction.

    Returns:
        Frozen StateAction instance.
    """
    defaults: dict[str, Any] = {
        "verb": StateActionType.REPRESS,
        "sub_verb": StateActionType.SURVEIL,
        "target_id": "org_player_1",
        "budget_cost": 5.0,
        "thread_cost": 1,
        "legitimacy_cost": -0.01,
        "faction_alignment": StateFaction.SECURITY_STATE,
    }
    defaults.update(overrides)
    return StateAction(**defaults)


def make_attention_thread(**overrides: Any) -> AttentionThread:
    """Create an AttentionThread with sensible defaults.

    Args:
        **overrides: Fields to override on the default AttentionThread.

    Returns:
        Frozen AttentionThread instance.
    """
    defaults: dict[str, Any] = {
        "thread_id": "thread_001",
        "target_type": "organization",
        "target_id": "org_player_1",
        "phase": ThreadPhase.MONITORING,
        "intensity": 0.3,
        "intel_completeness": 0.15,
        "surveillance_methods": [SurveillanceMethod.SIGNALS],
        "stickiness": 0.2,
        "ticks_active": 3,
        "owning_apparatus_id": "apparatus_detroit_pd",
    }
    defaults.update(overrides)
    return AttentionThread(**defaults)


def make_sparrow_analysis(**overrides: Any) -> SparrowAnalysis:
    """Create a SparrowAnalysis with sensible defaults.

    Args:
        **overrides: Fields to override on the default SparrowAnalysis.

    Returns:
        Frozen SparrowAnalysis instance.
    """
    defaults: dict[str, Any] = {
        "thread_id": "thread_001",
        "tick": 5,
        "centrality_rankings": {
            "node_a": {"degree": 0.8, "betweenness": 0.6},
            "node_b": {"degree": 0.3, "betweenness": 0.1},
        },
        "equivalence_classes": [frozenset({"node_a"}), frozenset({"node_b"})],
        "identified_singletons": frozenset({"node_a", "node_b"}),
        "known_cutsets": [frozenset({"node_a"})],
        "confidence": 0.4,
    }
    defaults.update(overrides)
    return SparrowAnalysis(**defaults)


def make_legal_framework(**overrides: Any) -> LegalFramework:
    """Create a LegalFramework with sensible defaults.

    Args:
        **overrides: Fields to override on the default LegalFramework.

    Returns:
        Frozen LegalFramework instance.
    """
    defaults: dict[str, Any] = {
        "framework_id": "law_001",
        "law_type": "SURVEILLANCE_EXPANSION",
        "scope": "municipal",
        "severity": 0.5,
        "effects": {"surveillance_multiplier": 1.5},
        "created_tick": 0,
        "creating_apparatus_id": "apparatus_detroit_pd",
    }
    defaults.update(overrides)
    return LegalFramework(**defaults)


def make_state_apparatus_node(
    org_id: str = "apparatus_detroit_pd",
    **attrs: Any,
) -> dict[str, Any]:
    """Create a dict representing a StateApparatus graph node.

    Args:
        org_id: Node ID.
        **attrs: Additional node attributes.

    Returns:
        Dict with standard state apparatus node attributes.
    """
    node: dict[str, Any] = {
        "_node_type": "organization",
        "id": org_id,
        "org_type": OrgType.STATE_APPARATUS.value,
        "class_character": "bourgeois",
        "cohesion": 0.8,
        "cadre_level": 0.6,
        "consciousness_tendency": "liberal",
        "budget": 1000.0,
        "heat": 0.0,
        "jurisdiction": "municipal",
        "violence_capacity": 0.7,
        "surveillance_capacity": 0.5,
        "factional_alignment": StateFaction.SECURITY_STATE.value,
    }
    node.update(attrs)
    return node
