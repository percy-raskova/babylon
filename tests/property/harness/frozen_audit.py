"""``frozen_audit`` — per-tick identity-discipline check for spec-055 US3.

Two helpers paired with the static ``model_class_registry.assert_all_frozen``:

  - ``snapshot_ids(state)``: capture ``id()`` of every state-bearing model
    instance at a fixed point in time (typically pre-tick).
  - ``assert_no_in_place_mutation(pre, post, pre_ids)``: for every entity
    present in both states, raise ``AssertionError`` if
    ``id(pre) is id(post) AND pre.model_dump() != post.model_dump()``
    (the operational signature of an in-place mutation).

Reuses Spec 054's ``_iter_worldstate_collections`` from
``babylon.engine.invariants`` so the canonical entity-walker stays in
one place.
"""

from __future__ import annotations

from babylon.engine.invariants import _iter_worldstate_collections
from babylon.models.world_state import WorldState


def snapshot_ids(state: WorldState) -> dict[str, int]:
    """Return a dict mapping entity ID to Python ``id()`` for the pre-state.

    Walks every state-bearing collection enumerated by Spec 054's
    ``_iter_worldstate_collections`` helper. Must be called BEFORE any
    tick runs, otherwise the captured ids are already invalidated.

    Args:
        state: Pre-tick WorldState.

    Returns:
        Mapping of entity ID -> Python ``id(entity)``.
    """
    return {entity_id: id(entity) for entity_id, entity in _iter_worldstate_collections(state)}


def assert_no_in_place_mutation(
    pre_state: WorldState, post_state: WorldState, pre_ids: dict[str, int]
) -> None:
    """Raise AssertionError on any in-place mutation across the tick.

    For every entity ID present in both pre and post, checks that the
    illegal pattern ``same id() AND different model_dump()`` does not hold.
    Legal post-tick states are either:
      (a) field-equal AND same Python id (no mutation occurred), OR
      (b) field-different AND different Python id (a model_copy produced
          a fresh instance).

    Args:
        pre_state: WorldState before the tick.
        post_state: WorldState after the tick.
        pre_ids: Output of ``snapshot_ids(pre_state)``.

    Raises:
        AssertionError: If any entity ID matches with same Python id but
            different field values, naming the entity and the field-level
            diff.
    """
    pre_dumps: dict[str, dict] = {
        entity_id: entity.model_dump()
        for entity_id, entity in _iter_worldstate_collections(pre_state)
    }

    for entity_id, post_entity in _iter_worldstate_collections(post_state):
        pre_python_id = pre_ids.get(entity_id)
        if pre_python_id is None:
            continue  # entity new this tick — no identity to check
        post_python_id = id(post_entity)
        post_dump = post_entity.model_dump()
        pre_dump = pre_dumps.get(entity_id, {})

        same_id = post_python_id == pre_python_id
        fields_equal = post_dump == pre_dump
        if same_id and not fields_equal:
            diff = _dict_diff(pre_dump, post_dump)
            raise AssertionError(
                f"In-place mutation detected on entity {entity_id} "
                f"(class {type(post_entity).__name__}): same id() but "
                f"field-different. diff: {diff}"
            )


def _dict_diff(pre: dict, post: dict) -> dict[str, tuple[object, object]]:
    """Return per-key (pre_value, post_value) tuples for changed keys.

    Top-level diff only — nested differences are reported as the full
    nested values. Sufficient for the failure-message body.
    """
    diff: dict[str, tuple[object, object]] = {}
    keys = set(pre.keys()) | set(post.keys())
    for k in keys:
        pre_v = pre.get(k)
        post_v = post.get(k)
        if pre_v != post_v:
            diff[k] = (pre_v, post_v)
    return diff


__all__ = ["assert_no_in_place_mutation", "snapshot_ids"]
