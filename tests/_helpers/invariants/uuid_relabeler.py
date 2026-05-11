"""UUID relabeler — spec 060 US6(a) / FR-013.

Builds an alias mapping for every entity ID in a ``WorldState`` and
returns a new state with all IDs replaced, plus the mapping used.
Numeric fields, structural relationships, and edge mode types are
untouched.

Contract: ``specs/060-value-form-invariants/contracts/uuid_relabeler.md``.
Field inventory: ``specs/060-value-form-invariants/research.md`` R5.

Algorithm
---------
1. Collect canonical IDs from all top-level ``WorldState`` dict-key
   namespaces.
2. Sort them lexicographically for determinism.
3. Build a bijective mapping ``orig -> alias`` via ``alias_fn``.
4. Dump the world via ``model_dump()``, recursively rewrite every dict
   key and every string value that matches the mapping.
5. Reconstitute the world via ``WorldState.model_validate(dump)``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

# Top-level WorldState dict-key namespaces (research.md R5).
# Keys that are NOT entity IDs (e.g., dialectic kind labels) must not
# appear here. The "industries" and "institution_relations" fields are
# included opportunistically; if absent on a given WorldState they are
# skipped.
_TOP_LEVEL_KEY_FIELDS: tuple[str, ...] = (
    "entities",
    "territories",
    "state_finances",
    "contradiction_frames",
    "organizations",
    "key_figures",
    "institutions",
    "industries",
)


def _default_alias_fn(index: int, original: str) -> str:
    """Deterministic alias function: ``alias_{i:06d}``."""
    return f"alias_{index:06d}"


def _collect_canonical_ids(world: BaseModel) -> set[str]:
    """Walk top-level dict-key fields on the world and return their union."""
    ids: set[str] = set()
    for field_name in _TOP_LEVEL_KEY_FIELDS:
        value = getattr(world, field_name, None)
        if isinstance(value, dict):
            ids.update(k for k in value if isinstance(k, str))
    return ids


def _rewrite_in_place(obj: Any, mapping: dict[str, str]) -> Any:
    """Recursive walker: rewrite dict keys and string values per mapping."""
    if isinstance(obj, dict):
        # Rewrite keys
        rekeyed: dict[Any, Any] = {}
        for key, val in obj.items():
            new_key = mapping[key] if isinstance(key, str) and key in mapping else key
            rekeyed[new_key] = _rewrite_in_place(val, mapping)
        return rekeyed
    if isinstance(obj, list):
        return [_rewrite_in_place(v, mapping) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_rewrite_in_place(v, mapping) for v in obj)
    if isinstance(obj, str):
        return mapping.get(obj, obj)
    return obj


def relabel_uuids(
    world: BaseModel,
    alias_fn: Callable[[int, str], str] | None = None,
) -> tuple[BaseModel, dict[str, str]]:
    """Return a world with every canonical ID relabeled, plus the mapping.

    Args:
        world: Source state (any Pydantic ``BaseModel``; typically
            ``WorldState``).
        alias_fn: ``(index, original_id) -> new_id``. Defaults to a
            deterministic ``f"alias_{i:06d}"`` function. Must produce
            unique outputs.

    Returns:
        ``(relabeled_world, {original_id: alias})``. The mapping is
        bijective. ``relabeled_world`` is structurally identical to
        ``world`` except for IDs (numerics preserved bit-identically).

    Raises:
        TypeError: If ``world`` is not a Pydantic ``BaseModel``.
        ValueError: If the supplied ``alias_fn`` produces a collision.
    """
    if not isinstance(world, BaseModel):
        raise TypeError(f"Expected pydantic BaseModel, got {type(world).__name__}")

    fn = alias_fn or _default_alias_fn
    sorted_ids = sorted(_collect_canonical_ids(world))
    mapping: dict[str, str] = {orig: fn(i, orig) for i, orig in enumerate(sorted_ids)}

    if len(set(mapping.values())) != len(mapping):
        raise ValueError("alias_fn produced collisions; aliases must be unique")

    if not mapping:
        return world, mapping

    dump = world.model_dump()
    rewritten = _rewrite_in_place(dump, mapping)
    relabeled = world.__class__.model_validate(rewritten)
    return relabeled, mapping


__all__ = ["relabel_uuids"]
