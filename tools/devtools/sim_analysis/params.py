"""GameDefines injection and introspection for development-only analysis.

The Pydantic introspection and ``Field`` bounds extraction that power Monte
Carlo, sensitivity analysis, and parameter sweeps route through the functions
in this module.

See Also:
    :doc:`/ai/decisions.yaml` ADR038 for the introspection rationale.
"""

from __future__ import annotations

import math
from typing import Any

from babylon.config.defines import GameDefines

ParameterValue = int | float
ParameterBounds = tuple[ParameterValue, ParameterValue]

_RawBound = tuple[ParameterValue, bool]

# =============================================================================
# PARAMETER INJECTION
# =============================================================================


def _normalize_parameter_value(field_info: Any, value: ParameterValue) -> ParameterValue:
    """Preserve schema-native numeric types before strict model validation."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"Parameter value must be finite, got: {value!r}")
        if field_info.annotation is int and value.is_integer():
            return int(value)
    return value


def inject_parameter(
    base_defines: GameDefines,
    param_path: str,
    value: ParameterValue,
) -> GameDefines:
    """Create a new GameDefines with a nested parameter overridden.

    Revalidates the complete candidate through Pydantic in strict mode. This
    preserves the frozen model while refusing type coercion (for example, an
    integer tick count cannot be supplied as ``7.5``).

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
    return inject_parameters(base_defines, {param_path: value})


def inject_parameters(
    base_defines: GameDefines,
    params: dict[str, ParameterValue],
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
    candidate = base_defines.model_dump(mode="python")
    for param_path, value in params.items():
        parts = param_path.split(".")
        if len(parts) != 2:
            raise ValueError(f"param_path must be 'category.field', got: {param_path}")

        category, field = parts
        if category not in GameDefines.model_fields:
            raise ValueError(f"Unknown category: {category}")

        category_model = GameDefines.model_fields[category].annotation
        if category_model is None or not hasattr(category_model, "model_fields"):
            raise ValueError(f"Category {category} is not a Pydantic model")
        if field not in category_model.model_fields:
            raise ValueError(f"Unknown field '{field}' in category '{category}'")

        category_values = candidate[category]
        if not isinstance(category_values, dict):
            raise TypeError(f"Expected dumped category {category!r} to be a mapping")
        field_info = category_model.model_fields[field]
        category_values[field] = _normalize_parameter_value(field_info, value)

    return GameDefines.model_validate(candidate, strict=True)


# =============================================================================
# PARAMETER ENUMERATION (Pydantic Introspection - ADR038)
# =============================================================================


def _extract_bounds(field_info: Any) -> tuple[_RawBound | None, _RawBound | None]:
    """Extract min/max bounds from Pydantic ``FieldInfo`` metadata.

    Searches for ``Ge``, ``Gt`` (lower bounds) and ``Le``, ``Lt`` (upper
    bounds) in metadata.

    :param field_info: Pydantic ``FieldInfo`` object.
    :returns: Tuple of ``(lower_bound, upper_bound)``. A present bound is a
        ``(value, inclusive)`` pair; either side may be ``None``.
    """
    lower: _RawBound | None = None
    upper: _RawBound | None = None

    for constraint in field_info.metadata:
        constraint_name = type(constraint).__name__
        if constraint_name == "Ge" and hasattr(constraint, "ge"):
            lower = (constraint.ge, True)
        elif constraint_name == "Gt" and hasattr(constraint, "gt"):
            lower = (constraint.gt, False)
        elif constraint_name == "Le" and hasattr(constraint, "le"):
            upper = (constraint.le, True)
        elif constraint_name == "Lt" and hasattr(constraint, "lt"):
            upper = (constraint.lt, False)

    return lower, upper


def _sampleable_bound(
    raw_bound: _RawBound,
    *,
    parameter_type: type[int] | type[float],
    lower: bool,
) -> ParameterValue:
    """Convert one schema constraint to an endpoint safe to sample.

    Integer bounds use the nearest valid integer. Float bounds use the
    adjacent representable float for strict ``gt``/``lt`` constraints, so a
    sampler that includes both endpoints still cannot emit the forbidden
    schema boundary.
    """
    value, inclusive = raw_bound
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"Non-finite parameter bound: {value!r}")

    if parameter_type is int:
        if lower:
            return math.ceil(numeric) if inclusive else math.floor(numeric) + 1
        return math.floor(numeric) if inclusive else math.ceil(numeric) - 1

    if inclusive:
        return numeric
    direction = math.inf if lower else -math.inf
    return math.nextafter(numeric, direction)


def get_tunable_parameters(
    categories: list[str] | None = None,
) -> dict[str, ParameterBounds]:
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
    result: dict[str, ParameterBounds] = {}

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
            parameter_type = int if annotation is int else float

            # Extract bounds from metadata
            raw_lower, raw_upper = _extract_bounds(field_info)
            default = field_info.default

            # Apply fallback bounds
            if raw_lower is None:
                raw_lower = (0 if parameter_type is int else 0.0, True)
            if raw_upper is None:
                # Use 10x default as upper bound if no explicit constraint
                fallback = default * 10 if default > 0 else 10
                raw_upper = (fallback, True)

            lower = _sampleable_bound(raw_lower, parameter_type=parameter_type, lower=True)
            upper = _sampleable_bound(raw_upper, parameter_type=parameter_type, lower=False)

            param_path = f"{category_name}.{field_name}"
            if lower > upper:
                raise ValueError(
                    f"No sampleable values for {param_path}: lower={lower!r}, upper={upper!r}"
                )
            result[param_path] = (lower, upper)

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
    "ParameterBounds",
    "ParameterValue",
    "inject_parameter",
    "inject_parameters",
    "get_tunable_parameters",
    "get_parameter_type",
]
