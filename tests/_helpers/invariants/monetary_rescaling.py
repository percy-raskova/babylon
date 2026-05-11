"""Monetary rescaling helper — spec 060 US1 / FR-001 / FR-002.

Walks a ``WorldState`` and produces a new state with all ``Currency``-typed
fields scaled by ``k``. Leaves all ``LaborHours``, structural, enum, and
ID fields untouched. Used by ``tests/property/invariants/
test_numeraire_invariance.py`` to assert that dimensionless ratios are
invariant under monetary numéraire choice.

Contract: ``specs/060-value-form-invariants/contracts/monetary_rescaling.md``.

Currency / LaborHours detection
-------------------------------
``Currency`` and ``LaborHours`` are ``typing.Annotated[float, ...]``
aliases at ``babylon.models.types``. We detect Currency-shaped fields by
identity comparison against the imported alias, with support for
``Optional[Currency]`` and homogeneous containers. The annotation walk
recurses into nested ``BaseModel`` instances.
"""

from __future__ import annotations

import math
import typing
from typing import Any, get_args, get_origin

from pydantic import BaseModel

from babylon.models.types import Currency

# Allowed monetary scale band per FR-001 / contracts/monetary_rescaling.md.
_K_MIN_SAFE: float = 1e-9
_K_MAX_SAFE: float = 1e9


def _is_currency_annotation(annot: Any) -> bool:
    """True iff the annotation is ``Currency`` (or ``Optional[Currency]``,
    ``list[Currency]``, ``dict[K, Currency]``)."""
    if annot is Currency:
        return True
    origin = get_origin(annot)
    args = get_args(annot)
    if origin is typing.Union or (origin is not None and type(None) in args):
        return any(_is_currency_annotation(a) for a in args if a is not type(None))
    if origin in (list, tuple, set, frozenset):
        return any(_is_currency_annotation(a) for a in args)
    if origin is dict:
        return _is_currency_annotation(args[-1]) if args else False
    return False


def _scale_value(value: Any, k: float, is_currency: bool) -> Any:
    """Scale a single value by ``k`` iff its annotation is Currency-shaped."""
    if value is None:
        return None
    if isinstance(value, BaseModel):
        return _rescale_model(value, k)
    if isinstance(value, dict):
        return {key: _scale_value(v, k, is_currency) for key, v in value.items()}
    if isinstance(value, list):
        return [_scale_value(v, k, is_currency) for v in value]
    if isinstance(value, tuple):
        return tuple(_scale_value(v, k, is_currency) for v in value)
    if is_currency and isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value) * k
    return value


def _rescale_model(model: BaseModel, k: float) -> BaseModel:
    """Return a new model instance with Currency-typed fields scaled by k."""
    updates: dict[str, Any] = {}
    for name, field in type(model).model_fields.items():
        current = getattr(model, name)
        is_cur = _is_currency_annotation(field.annotation)
        new_val = _scale_value(current, k, is_cur)
        if new_val is not current:
            updates[name] = new_val
    if not updates:
        return model
    try:
        return model.model_copy(update=updates)
    except Exception:
        # Fallback: re-validate from dict for non-frozen edge cases
        dump = model.model_dump()
        dump.update(updates)
        return model.__class__.model_validate(dump)


def rescale_currency_fields(world: BaseModel, k: float) -> BaseModel:
    """Return a new ``world`` with all Currency-typed fields scaled by ``k``.

    Pure; reversible by passing ``1/k``; idempotent on labor-time fields.

    Args:
        world: A Pydantic ``BaseModel`` (typically a ``WorldState``).
        k: Positive finite scale factor. Practical range: ``[1e-9, 1e9]``.

    Returns:
        A new ``BaseModel`` of the same type as ``world`` with all
        ``Currency``-annotated leaves multiplied by ``k``. All other
        fields are preserved by reference (immutable Pydantic semantics).

    Raises:
        ValueError: If ``k <= 0`` or ``k`` is non-finite.
        TypeError: If ``world`` is not a Pydantic ``BaseModel``.
    """
    if not isinstance(world, BaseModel):
        raise TypeError(f"Expected pydantic BaseModel, got {type(world).__name__}")
    if not isinstance(k, (int, float)) or isinstance(k, bool):
        raise ValueError(f"Scale factor must be a real number, got {type(k).__name__}")
    if not math.isfinite(k):
        raise ValueError(f"Scale factor must be finite, got {k}")
    if k <= 0:
        raise ValueError(f"Scale factor must be positive, got {k}")
    if k < _K_MIN_SAFE or k > _K_MAX_SAFE:
        # Outside the practical band — caller should use [1e-9, 1e9]
        # but we don't fail; we let the test report drift if it occurs.
        pass
    return _rescale_model(world, k)


__all__ = ["rescale_currency_fields"]
