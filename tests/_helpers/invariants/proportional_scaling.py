"""Proportional (c, v) scaling at constant s/v — spec 060 US7(a) / FR-017.

Scales constant capital ``c`` and variable capital ``v`` by ``k`` while
holding the rate of surplus value ``s/v`` constant. This means ``s``
also scales by ``k`` (since v scales by k and s/v is invariant). The
expected outcome: total value ``c+v+s`` scales by exactly ``k``; profit
rate, OCC, and exploitation rate are unchanged.

This helper sweeps the same ``BaseModel`` fields as the productivity-
shock helper but multiplies (rather than halving) and treats all
matching entities uniformly.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

_CV_FIELDS = ("constant_capital", "variable_capital", "c", "v")
_S_FIELDS = ("surplus_value", "s")


def scale_c_v_preserving_s_over_v(world: BaseModel, k: float) -> BaseModel:
    """Return a new world with c, v, s all scaled by ``k``.

    Since ``s/v`` is held constant and ``v`` scales by ``k``, ``s`` also
    scales by ``k``. The end result: ``c, v, s`` all multiply by ``k``;
    ratios (profit rate, OCC, exploitation rate) are unchanged; total
    value scales by ``k``.

    Args:
        world: Source state.
        k: Positive scale factor. ``k == 1.0`` is a no-op.

    Returns:
        A new world with scaled value-tensor fields.

    Raises:
        ValueError: If ``k <= 0``.
    """
    if not isinstance(k, (int, float)) or isinstance(k, bool):
        raise ValueError(f"k must be a real number, got {type(k).__name__}")
    if k <= 0:
        raise ValueError(f"k must be positive, got {k}")

    updates: dict[str, Any] = {}
    for field_name in type(world).model_fields:
        value = getattr(world, field_name)
        if not isinstance(value, dict):
            continue
        new_dict: dict[Any, Any] = dict(value)
        changed = False
        for key, entity in value.items():
            scaled = _scale_cvs(entity, k)
            if scaled is not entity:
                new_dict[key] = scaled
                changed = True
        if changed:
            updates[field_name] = new_dict

    if not updates:
        return world
    return world.model_copy(update=updates)


def _scale_cvs(entity: Any, k: float) -> Any:
    """Scale c, v, s on an entity by k; return original if no fields match."""
    if not isinstance(entity, BaseModel):
        return entity
    sub_updates: dict[str, Any] = {}
    for fname in _CV_FIELDS + _S_FIELDS:
        if fname in type(entity).model_fields:
            current = getattr(entity, fname)
            if isinstance(current, (int, float)) and not isinstance(current, bool):
                sub_updates[fname] = float(current) * k
    if not sub_updates:
        # Recurse one level into nested models (e.g. ValueTensor4x3
        # carrying DepartmentRow instances).
        nested_updates: dict[str, Any] = {}
        for fname in type(entity).model_fields:
            child = getattr(entity, fname)
            if isinstance(child, BaseModel):
                scaled = _scale_cvs(child, k)
                if scaled is not child:
                    nested_updates[fname] = scaled
        if nested_updates:
            return entity.model_copy(update=nested_updates)
        return entity
    return entity.model_copy(update=sub_updates)


__all__ = ["scale_c_v_preserving_s_over_v"]
