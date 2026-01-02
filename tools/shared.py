#!/usr/bin/env python3
"""Shared utilities for simulation tooling (ADR036).

This module is the single source of truth for common functions used across
the tools/ directory. All simulation utilities should be imported from here,
never duplicated.

Usage:
    from shared import (
        inject_parameter,
        inject_parameters,
        is_dead,
        run_simulation,
        PERIPHERY_WORKER_ID,
        DEFAULT_MAX_TICKS,
    )

See Also:
    :doc:`/ai-docs/tooling.yaml` for full documentation
    :doc:`/ai-docs/decisions.yaml` ADR036 for rationale
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Final

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from babylon.config.defines import GameDefines
from babylon.engine.scenarios import create_imperial_circuit_scenario
from babylon.engine.simulation_engine import step
from babylon.models.enums import EdgeType, EventType

# =============================================================================
# ENTITY ID CONSTANTS
# =============================================================================

PERIPHERY_WORKER_ID: Final[str] = "C001"
"""Periphery Worker (P_w) - exploited proletariat in the global South."""

COMPRADOR_ID: Final[str] = "C002"
"""Comprador (P_c) - local bourgeoisie collaborating with imperialism."""

CORE_BOURGEOISIE_ID: Final[str] = "C003"
"""Core Bourgeoisie (C_b) - metropolitan capitalist class."""

LABOR_ARISTOCRACY_ID: Final[str] = "C004"
"""Labor Aristocracy (C_w) - privileged workers in the imperial core."""

# All entity IDs for iteration
ENTITY_IDS: Final[list[str]] = [
    PERIPHERY_WORKER_ID,
    COMPRADOR_ID,
    CORE_BOURGEOISIE_ID,
    LABOR_ARISTOCRACY_ID,
]

# Column name mapping for CSV output (semantic names)
ENTITY_COLUMN_PREFIX: Final[dict[str, str]] = {
    "C001": "p_w",  # Periphery Worker
    "C002": "p_c",  # Comprador
    "C003": "c_b",  # Core Bourgeoisie
    "C004": "c_w",  # Labor Aristocracy (Core Worker)
}

# =============================================================================
# SIMULATION CONSTANTS
# =============================================================================

DEFAULT_MAX_TICKS: Final[int] = 5200
"""Default simulation length: 5200 ticks = 100 years (1 tick = 1 week).

Extended from 70-year trajectory to allow full parameter exploration.
See ai-docs/carceral-equilibrium.md for the phase transition sequence:
- Years 0-20:  Imperial Extraction
- Years 15-25: Peripheral Revolt
- Years 20-30: Superwage Crisis
- Years 25-40: Carceral Turn
- Years 35-50: Control Ratio Crisis
- Years 45-65: Genocide Phase
- Years 60-70: Stable Necropolis
"""

DEATH_THRESHOLD: Final[float] = 0.001
"""Wealth threshold for legacy death detection (use is_dead() instead)."""


# =============================================================================
# DEATH DETECTION
# =============================================================================


def is_dead(entity: Any) -> bool:
    """Check if an entity is dead using VitalitySystem's active field.

    This aligns with VitalitySystem which sets active=False when
    wealth < consumption_needs (s_bio + s_class).

    Args:
        entity: SocialClass entity or None

    Returns:
        True if entity is None or has active=False
    """
    if entity is None:
        return True
    return not getattr(entity, "active", True)


def is_dead_by_wealth(wealth: float) -> bool:
    """Check if wealth level indicates death (legacy method).

    Prefer is_dead() for alignment with VitalitySystem. This function
    exists for compatibility with older code paths.

    Args:
        wealth: Current wealth value

    Returns:
        True if wealth <= DEATH_THRESHOLD
    """
    return wealth <= DEATH_THRESHOLD


# =============================================================================
# PARAMETER INJECTION
# =============================================================================


def inject_parameter(
    base_defines: GameDefines,
    param_path: str,
    value: float,
) -> GameDefines:
    """Create a new GameDefines with a nested parameter overridden.

    Uses Pydantic's model_copy(update=...) to create an immutable copy
    with the specified parameter changed.

    Args:
        base_defines: Original GameDefines (not mutated)
        param_path: Dot-separated path like "economy.extraction_efficiency"
        value: New value to set

    Returns:
        New GameDefines with the parameter updated

    Raises:
        ValueError: If param_path is invalid

    Example:
        >>> defines = inject_parameter(GameDefines(), "economy.extraction_efficiency", 0.5)
        >>> defines.economy.extraction_efficiency
        0.5
    """
    parts = param_path.split(".")
    if len(parts) != 2:
        raise ValueError(f"param_path must be 'category.field', got: {param_path}")

    category, field = parts

    # Get the current category model
    category_model = getattr(base_defines, category, None)
    if category_model is None:
        raise ValueError(f"Unknown category: {category}")

    # Verify the field exists
    if not hasattr(category_model, field):
        raise ValueError(f"Unknown field '{field}' in category '{category}'")

    # Create new category model with updated field
    new_category = category_model.model_copy(update={field: value})

    # Create new GameDefines with updated category
    return base_defines.model_copy(update={category: new_category})


def inject_parameters(
    base_defines: GameDefines,
    params: dict[str, float],
) -> GameDefines:
    """Create a new GameDefines with multiple parameters overridden.

    Convenience function for batch parameter injection, useful for
    Monte Carlo and sensitivity analysis where multiple parameters
    are varied simultaneously.

    Args:
        base_defines: Original GameDefines (not mutated)
        params: Dict mapping param_path -> value

    Returns:
        New GameDefines with all parameters updated

    Raises:
        ValueError: If any param_path is invalid

    Example:
        >>> params = {
        ...     "economy.extraction_efficiency": 0.5,
        ...     "economy.comprador_cut": 0.8,
        ... }
        >>> defines = inject_parameters(GameDefines(), params)
    """
    result = base_defines
    for param_path, value in params.items():
        result = inject_parameter(result, param_path, value)
    return result


# =============================================================================
# SIMULATION EXECUTION
# =============================================================================


def run_simulation(
    defines: GameDefines,
    max_ticks: int = DEFAULT_MAX_TICKS,
) -> dict[str, Any]:
    """Run a single simulation with the given GameDefines.

    Args:
        defines: GameDefines to use for this simulation
        max_ticks: Maximum number of ticks to run

    Returns:
        Dictionary with:
            - ticks_survived: Number of ticks before death (or max_ticks)
            - max_tension: Maximum tension observed on any edge
            - outcome: "SURVIVED" or "DIED"
            - final_wealth: Final wealth of periphery worker
            - final_state: Final WorldState object
            - phase_milestones: Dict mapping phase name -> tick (or None)
            - terminal_outcome: "revolution", "genocide", or None
    """
    # Create scenario with default parameters
    state, config, _scenario_defines = create_imperial_circuit_scenario()

    # We use our injected defines instead of scenario_defines
    persistent_context: dict[str, Any] = {}
    max_tension: float = 0.0
    ticks_survived: int = 0
    final_wealth: float = 0.0

    # Phase milestone tracking for Carceral Equilibrium scoring
    phase_milestones: dict[str, int | None] = {
        "superwage_crisis": None,
        "class_decomposition": None,
        "control_ratio_crisis": None,
        "terminal_decision": None,
    }
    terminal_outcome: str | None = None

    for tick in range(max_ticks):
        state = step(state, config, persistent_context, defines)

        # Track phase transition events
        for event in state.events:
            if event.event_type == EventType.SUPERWAGE_CRISIS:
                if phase_milestones["superwage_crisis"] is None:
                    phase_milestones["superwage_crisis"] = tick
            elif event.event_type == EventType.CLASS_DECOMPOSITION:
                if phase_milestones["class_decomposition"] is None:
                    phase_milestones["class_decomposition"] = tick
            elif event.event_type == EventType.CONTROL_RATIO_CRISIS:
                if phase_milestones["control_ratio_crisis"] is None:
                    phase_milestones["control_ratio_crisis"] = tick
            elif (
                event.event_type == EventType.TERMINAL_DECISION
                and phase_milestones["terminal_decision"] is None
            ):
                phase_milestones["terminal_decision"] = tick
                # TerminalDecisionEvent has outcome as a direct attribute
                terminal_outcome = getattr(event, "outcome", None)

        # Get periphery worker wealth
        worker = state.entities.get(PERIPHERY_WORKER_ID)
        if worker is None:
            # Unexpected state - worker entity missing
            break

        final_wealth = float(worker.wealth)

        # Track maximum tension across all edges
        for rel in state.relationships:
            if rel.edge_type == EdgeType.EXPLOITATION:
                max_tension = max(max_tension, rel.tension)

        # Check for death (uses VitalitySystem's active field)
        if is_dead(worker):
            ticks_survived = tick + 1
            return {
                "ticks_survived": ticks_survived,
                "max_tension": max_tension,
                "outcome": "DIED",
                "final_wealth": final_wealth,
                "final_state": state,
                "phase_milestones": phase_milestones,
                "terminal_outcome": terminal_outcome,
            }

        ticks_survived = tick + 1

    return {
        "ticks_survived": ticks_survived,
        "max_tension": max_tension,
        "outcome": "SURVIVED",
        "final_wealth": final_wealth,
        "final_state": state,
        "phase_milestones": phase_milestones,
        "terminal_outcome": terminal_outcome,
    }


# =============================================================================
# PARAMETER ENUMERATION (Pydantic Introspection - ADR038)
# =============================================================================


def _extract_bounds(field_info: Any) -> tuple[float | None, float | None]:
    """Extract min/max bounds from Pydantic FieldInfo metadata.

    Searches for Ge, Gt (lower bounds) and Le, Lt (upper bounds) in metadata.

    Args:
        field_info: Pydantic FieldInfo object

    Returns:
        Tuple of (lower_bound, upper_bound), either may be None if not specified
    """
    lower: float | None = None
    upper: float | None = None

    for constraint in field_info.metadata:
        constraint_name = type(constraint).__name__
        if constraint_name == "Ge" and hasattr(constraint, "ge"):
            lower = constraint.ge
        elif constraint_name == "Gt" and hasattr(constraint, "gt"):
            # For strict greater-than, use the value as lower bound
            lower = constraint.gt
        elif constraint_name == "Le" and hasattr(constraint, "le"):
            upper = constraint.le
        elif constraint_name == "Lt" and hasattr(constraint, "lt"):
            # For strict less-than, use the value as upper bound
            upper = constraint.lt

    return lower, upper


def get_tunable_parameters(
    categories: list[str] | None = None,
) -> dict[str, tuple[float, float]]:
    """Introspect GameDefines for all tunable float/int fields.

    Recursively walks nested Pydantic models, extracting Field constraints
    (ge, le, gt, lt) as bounds. Falls back to 10x default for unbounded fields.

    This is the single source of truth for parameter enumeration. All tools
    should use this function instead of maintaining hardcoded parameter lists.

    Args:
        categories: Optional list of category names to filter
            (e.g., ["economy", "carceral"]). If None, returns all categories.

    Returns:
        Dict mapping "category.field" -> (min_value, max_value)

    Example:
        >>> params = get_tunable_parameters()
        >>> len(params) >= 70
        True
        >>> params = get_tunable_parameters(categories=["economy"])
        >>> all(k.startswith("economy.") for k in params)
        True
    """
    result: dict[str, tuple[float, float]] = {}

    # Iterate over GameDefines categories (economy, consciousness, etc.)
    for category_name, category_field in GameDefines.model_fields.items():
        # Skip if filtering and category not in list
        if categories is not None and category_name not in categories:
            continue

        # Get the nested model class
        category_model = category_field.annotation
        if not hasattr(category_model, "model_fields"):
            continue  # Skip if not a Pydantic model

        # Iterate over fields in the category
        for field_name, field_info in category_model.model_fields.items():
            # Only include numeric types (int, float)
            annotation = field_info.annotation
            if annotation not in (int, float):
                continue

            # Extract bounds from metadata
            lower, upper = _extract_bounds(field_info)
            default = field_info.default

            # Apply fallback bounds
            if lower is None:
                lower = 0.0
            if upper is None:
                # Use 10x default as upper bound if no explicit constraint
                upper = default * 10.0 if default > 0 else 10.0

            param_path = f"{category_name}.{field_name}"
            result[param_path] = (float(lower), float(upper))

    return result


def get_parameter_type(param_path: str) -> type[int] | type[float]:
    """Return whether a parameter is int or float.

    Used by Optuna to select suggest_int vs suggest_float.

    Args:
        param_path: Dot-separated path like "carceral.control_capacity"

    Returns:
        int or float type

    Raises:
        ValueError: If param_path is invalid

    Example:
        >>> get_parameter_type("carceral.control_capacity")
        <class 'int'>
        >>> get_parameter_type("economy.extraction_efficiency")
        <class 'float'>
    """
    parts = param_path.split(".")
    if len(parts) != 2:
        raise ValueError(f"param_path must be 'category.field', got: {param_path}")

    category_name, field_name = parts

    # Get category model
    if category_name not in GameDefines.model_fields:
        raise ValueError(f"Unknown category: {category_name}")

    category_model = GameDefines.model_fields[category_name].annotation
    if not hasattr(category_model, "model_fields"):
        raise ValueError(f"Category {category_name} is not a Pydantic model")

    # Get field annotation
    if field_name not in category_model.model_fields:
        raise ValueError(f"Unknown field '{field_name}' in category '{category_name}'")

    annotation = category_model.model_fields[field_name].annotation
    if annotation is int:
        return int
    return float


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Entity IDs
    "PERIPHERY_WORKER_ID",
    "COMPRADOR_ID",
    "CORE_BOURGEOISIE_ID",
    "LABOR_ARISTOCRACY_ID",
    "ENTITY_IDS",
    "ENTITY_COLUMN_PREFIX",
    # Constants
    "DEFAULT_MAX_TICKS",
    "DEATH_THRESHOLD",
    # Death detection
    "is_dead",
    "is_dead_by_wealth",
    # Parameter injection
    "inject_parameter",
    "inject_parameters",
    # Simulation
    "run_simulation",
    # Parameter enumeration
    "get_tunable_parameters",
    "get_parameter_type",
]
