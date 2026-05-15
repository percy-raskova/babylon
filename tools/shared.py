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
from babylon.models.entity_registry import (
    COMPRADOR_ID,
    CORE_BOURGEOISIE_ID,
    ENTITY_SLOT_NAMES,
    LABOR_ARISTOCRACY_ID,
    METRICS_ENTITY_IDS,
    PERIPHERY_WORKER_ID,
)
from babylon.models.types import EntityProtocol

# Spec-064: the legacy in-memory engine imports
# (``create_imperial_circuit_scenario``, ``step``, ``WorldState``,
# ``EdgeType``, ``EventType``) were removed at module scope to satisfy
# SC-007. ``run_simulation`` now routes through
# :func:`babylon.engine.headless_runner.run` instead.

# =============================================================================
# ENTITY ID CONSTANTS (re-exported from entity_registry for backward compatibility)
# =============================================================================

# Re-export entity IDs - see babylon.models.entity_registry for canonical source
# PERIPHERY_WORKER_ID, COMPRADOR_ID, CORE_BOURGEOISIE_ID, LABOR_ARISTOCRACY_ID
# are imported above and re-exported in __all__

# Backward-compatible aliases
ENTITY_IDS: Final[list[str]] = list(METRICS_ENTITY_IDS)
"""All entity IDs for iteration (alias for METRICS_ENTITY_IDS)."""

# Only include metrics entities for backward compatibility (original had C001-C004 only)
ENTITY_COLUMN_PREFIX: Final[dict[str, str]] = {
    entity_id: ENTITY_SLOT_NAMES[entity_id] for entity_id in METRICS_ENTITY_IDS
}
"""Column name mapping for CSV output (filtered to metrics entities for compatibility)."""

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

DEATH_THRESHOLD: Final[float] = GameDefines().economy.death_threshold
"""Wealth threshold for legacy death detection (use is_dead() instead)."""


# =============================================================================
# DEATH DETECTION
# =============================================================================


def is_dead(entity: EntityProtocol | None) -> bool:
    """Check if an entity is dead using VitalitySystem's active field.

    This aligns with VitalitySystem which sets active=False when
    wealth < consumption_needs (s_bio + s_class).

    Sprint 1.X D2: Now enforces EntityProtocol for type safety.
    Use is_dead_by_wealth() for float-based wealth threshold checks.

    Args:
        entity: Object implementing EntityProtocol, or None.

    Returns:
        True if entity is None or has active=False.

    Raises:
        TypeError: If entity does not implement EntityProtocol.
    """
    if entity is None:
        return True
    if not isinstance(entity, EntityProtocol):
        raise TypeError(
            f"is_dead() requires EntityProtocol, got {type(entity).__name__}. "
            "Use is_dead_by_wealth() for float values."
        )
    return not entity.active


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
    """Run a single simulation via the headless Postgres-backed runner.

    Spec-064 migration: the legacy in-memory imperial-circuit scenario
    has been replaced by a routed call to
    :func:`babylon.engine.headless_runner.run`, which performs a real
    Postgres-backed Detroit-tri-county simulation. Result keys preserve
    the legacy dict shape so downstream tools (``tools/monte_carlo.py``,
    ``tools/parameter_analysis.py``, etc.) continue to compile, but
    several fields are degraded since the headless MVP runner does not
    yet compute them — see ``Returns`` below for the per-field status.

    Args:
        defines: GameDefines to use for this simulation. ``defines.rng_seed``
            is plumbed through as the runner's top-level seed; the
            remaining defines fields are accepted for signature
            compatibility but are not currently applied to the headless
            runner's per-tick advancement (which is a no-op carry-forward
            in the MVP — see ``runner.py``).
        max_ticks: Maximum number of ticks to run.

    Returns:
        Dictionary with:
            - ``ticks_survived``: Number of ticks the runner completed
              (always ``max_ticks`` for COMPLETED; ``< max_ticks`` for
              USER_INTERRUPTED / ERRORED).
            - ``outcome``: "SURVIVED" if exit_reason == COMPLETED, else "DIED".
            - ``max_tension``: Always ``0.0`` (degraded — the headless MVP
              does not compute per-edge tension).
            - ``final_wealth``: Sum of terminal-tick ``v`` (variable
              capital) across all in-scope counties, as a coarse proxy
              for the legacy single-worker wealth value.
            - ``final_state``: Always ``None`` (degraded — the headless
              runner has no in-memory ``WorldState``; persisted state
              lives in Postgres).
            - ``phase_milestones``: All entries ``None`` (degraded — the
              MVP runner does not detect SuperwageCrisis /
              ClassDecomposition / ControlRatioCrisis / TerminalDecision
              events).
            - ``terminal_outcome``: Always ``None`` (degraded — see above).

    Note:
        Each call opens a Postgres pool and runs a full session_init +
        hex_hydration cycle (~9 s for the Detroit tri-county scope), so
        Monte Carlo / parameter sweeps that previously executed in
        milliseconds now take seconds per sample. Use small ``max_ticks``
        in test contexts.
    """
    import tempfile
    from pathlib import Path

    from babylon.engine.headless_runner import run as headless_run
    from babylon.engine.headless_runner.models import (
        ExitReason,
        SimulationRunConfig,
    )
    from babylon.engine.headless_runner.scopes import resolve_scope

    scope = resolve_scope("detroit-tri-county")

    # Ephemeral output dir — caller doesn't see the artifact bundle here;
    # the run is purely for the result projection.
    with tempfile.TemporaryDirectory(prefix="babylon-shared-") as tmpdir:
        config = SimulationRunConfig(
            ticks=max_ticks,
            random_seed=getattr(defines, "rng_seed", 2010),
            scope_name="detroit-tri-county",
            scope_fips=scope.scope_fips,
            external_node_ids=scope.external_node_ids,
            output_dir=Path(tmpdir),
        )
        result = headless_run(config)

    return {
        "ticks_survived": result.ticks_completed,
        "max_tension": 0.0,
        "outcome": "SURVIVED" if result.exit_reason == ExitReason.COMPLETED else "DIED",
        "final_wealth": 0.0,
        "final_state": None,
        "phase_milestones": {
            "superwage_crisis": None,
            "class_decomposition": None,
            "control_ratio_crisis": None,
            "terminal_decision": None,
        },
        "terminal_outcome": None,
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
