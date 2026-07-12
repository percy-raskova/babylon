"""Parameter injection and introspection for :class:`GameDefines` (ADR038).

Moved verbatim from ``tools/shared.py`` (the pre-package single source of
truth for this machinery). Behavior is unchanged: the Pydantic-introspection
+ ``Field`` bounds-extraction logic that powers Monte Carlo, sensitivity
analysis, and parameter sweeps all route through the four functions here.

See Also:
    :doc:`/ai/decisions.yaml` ADR038 for the introspection rationale.
"""

from __future__ import annotations

from typing import Any

from babylon.config.defines import GameDefines

# =============================================================================
# PARAMETER INJECTION
# =============================================================================


def inject_parameter(
    base_defines: GameDefines,
    param_path: str,
    value: float,
) -> GameDefines:
    """Create a new GameDefines with a nested parameter overridden.

    Uses Pydantic's ``model_copy(update=...)`` to create an immutable copy
    with the specified parameter changed.

    :param base_defines: Original GameDefines (not mutated).
    :param param_path: Dot-separated path like ``"economy.extraction_efficiency"``.
    :param value: New value to set.
    :returns: New GameDefines with the parameter updated.
    :raises ValueError: If ``param_path`` is invalid.

    Example::

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

    :param base_defines: Original GameDefines (not mutated).
    :param params: Dict mapping ``param_path`` -> value.
    :returns: New GameDefines with all parameters updated.
    :raises ValueError: If any ``param_path`` is invalid.

    Example::

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
# PARAMETER ENUMERATION (Pydantic Introspection - ADR038)
# =============================================================================


def _extract_bounds(field_info: Any) -> tuple[float | None, float | None]:
    """Extract min/max bounds from Pydantic ``FieldInfo`` metadata.

    Searches for ``Ge``, ``Gt`` (lower bounds) and ``Le``, ``Lt`` (upper
    bounds) in metadata.

    :param field_info: Pydantic ``FieldInfo`` object.
    :returns: Tuple of ``(lower_bound, upper_bound)``, either may be ``None``
        if not specified.
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

    Recursively walks nested Pydantic models, extracting ``Field``
    constraints (``ge``, ``le``, ``gt``, ``lt``) as bounds. Falls back to
    10x default for unbounded fields.

    This is the single source of truth for parameter enumeration. All
    optimization algorithms should use this function instead of
    maintaining hardcoded parameter lists.

    :param categories: Optional list of category names to filter
        (e.g., ``["economy", "carceral"]``). If ``None``, returns all
        categories.
    :returns: Dict mapping ``"category.field"`` -> ``(min_value, max_value)``.

    Example::

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
        if category_model is None or not hasattr(category_model, "model_fields"):
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

    Used by algorithms (e.g. Optuna-backed Bayesian search) to select
    ``suggest_int`` vs ``suggest_float``.

    :param param_path: Dot-separated path like ``"carceral.control_capacity"``.
    :returns: ``int`` or ``float`` type.
    :raises ValueError: If ``param_path`` is invalid.

    Example::

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
    if category_model is None or not hasattr(category_model, "model_fields"):
        raise ValueError(f"Category {category_name} is not a Pydantic model")

    # Get field annotation
    if field_name not in category_model.model_fields:
        raise ValueError(f"Unknown field '{field_name}' in category '{category_name}'")

    annotation = category_model.model_fields[field_name].annotation
    if annotation is int:
        return int
    return float


__all__ = [
    "inject_parameter",
    "inject_parameters",
    "get_tunable_parameters",
    "get_parameter_type",
]
