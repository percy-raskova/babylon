"""Productivity-shock helper — spec 060 US5 / FR-007.

Halves SNLT-per-unit (constant + variable capital per unit output) in a
designated sector, leaving all other entities untouched. The
metamorphic pair (baseline_world, shocked_world) feeds the value-vs-
price decoupling test.

Implementation
--------------
Productivity in the Marxian sense is the inverse of SNLT per unit
output. In the engine, the c/v fields on ``HexEconomicState`` and
``ValueTensor4x3.DepartmentRow`` carry the labor-time aggregate
(``LaborHours``). "Doubling productivity" means halving the labor-time
per unit output for the sector. The helper directly halves the entity's
c and v in the target sector.

The helper does not attempt sector-specific filtering beyond a simple
ID match because the engine does not yet expose a canonical sector
classifier. The first matching entity (by ``id`` or by hex key) is
shocked. Tests that need finer control can pass a custom matcher.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel


def halve_snlt_in_sector(
    world: BaseModel,
    sector_id: str,
    *,
    matcher: Callable[[str, Any], bool] | None = None,
) -> BaseModel:
    """Return a new world with SNLT (c, v) halved for the target sector.

    Args:
        world: Source state (Pydantic BaseModel; typically ``WorldState``).
        sector_id: Identifier of the sector to shock. By default
            matches against entity ``id`` field or dict keys.
        matcher: Optional ``(candidate_id, candidate_obj) -> bool``
            predicate. Used when the default ID match is insufficient.

    Returns:
        A new world with the target sector's ``constant_capital`` and
        ``variable_capital`` halved (in labor-time terms). All other
        fields unchanged.

    Raises:
        ValueError: If no sector matches ``sector_id``.
    """
    if matcher is None:

        def matcher(cid: str, _obj: Any) -> bool:  # type: ignore[misc]
            return cid == sector_id

    updates: dict[str, Any] = {}
    matched = False

    for field_name in type(world).model_fields:
        value = getattr(world, field_name)
        if not isinstance(value, dict):
            continue
        new_dict: dict[Any, Any] = dict(value)
        local_changed = False
        for key, entity in list(value.items()):
            cid = str(key)
            if matcher(cid, entity):
                halved = _halve_cv(entity)
                if halved is not entity:
                    new_dict[key] = halved
                    local_changed = True
                    matched = True
        if local_changed:
            updates[field_name] = new_dict

    if not matched:
        raise ValueError(f"No sector matched id={sector_id!r}")

    return world.model_copy(update=updates)


def _halve_cv(entity: Any) -> Any:
    """If entity has c/v fields, return a copy with each halved."""
    if not isinstance(entity, BaseModel):
        return entity
    halve_updates: dict[str, Any] = {}
    for fname in ("constant_capital", "variable_capital", "c", "v"):
        if fname in type(entity).model_fields:
            current = getattr(entity, fname)
            if isinstance(current, (int, float)) and not isinstance(current, bool):
                halve_updates[fname] = float(current) / 2.0
    if not halve_updates:
        return entity
    return entity.model_copy(update=halve_updates)


__all__ = ["halve_snlt_in_sector"]
