"""``model_class_registry`` — discovers state-bearing Pydantic models for US3.

Walks ``babylon.models.entities.*`` via ``pkgutil.walk_packages`` plus the
top-level ``WorldState`` class, returning every ``BaseModel`` subclass
declared in those modules. Used by spec-055 US3 Layer 1 (static frozen
audit) per data-model.md §2.5 and research §4.

Also exposes ``assert_all_frozen(classes)`` — the centralized helper that
honors the ``bypasses_topology_invariant`` opt-out marker (with non-empty
justification per FR-011) and asserts ``model_config["frozen"] is True``
for every non-bypassed class.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from collections.abc import Sequence
from functools import lru_cache

from pydantic import BaseModel

from babylon.models import entities, world_state

_MIN_EXPECTED_MODELS = 12


@lru_cache(maxsize=1)
def discover_state_bearing_models() -> tuple[type[BaseModel], ...]:
    """Return every Pydantic model class under ``babylon.models.entities``.

    Walks every submodule of ``babylon.models.entities`` (recursively via
    ``pkgutil.walk_packages``) and yields every ``BaseModel`` subclass
    that is *declared* in one of those modules (not merely imported into
    it). Also includes the top-level ``WorldState``.

    Cached so repeated calls return the same tuple identity.

    Returns:
        Tuple of state-bearing Pydantic model classes, sorted by
        ``__qualname__`` for stable parametrization order.

    Raises:
        RuntimeError: If discovery yields fewer than ``_MIN_EXPECTED_MODELS``
            classes (defensive — empty discovery is almost certainly a bug
            in the walker, not an actual empty namespace).
    """
    seen: set[type[BaseModel]] = {world_state.WorldState}
    for _finder, name, _ispkg in pkgutil.walk_packages(entities.__path__, entities.__name__ + "."):
        try:
            module = importlib.import_module(name)
        except Exception:  # noqa: BLE001 — skip optional/broken submodules
            continue
        for _attr_name, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, BaseModel) and cls is not BaseModel and cls.__module__ == name:
                seen.add(cls)

    if len(seen) < _MIN_EXPECTED_MODELS:
        raise RuntimeError(
            f"State-bearing model discovery yielded only {len(seen)} "
            f"classes; expected at least {_MIN_EXPECTED_MODELS}. The "
            f"walker likely has a bug — check babylon.models.entities."
        )

    return tuple(sorted(seen, key=lambda c: c.__qualname__))


def assert_all_frozen(classes: Sequence[type[BaseModel]]) -> None:
    """Assert every class in ``classes`` declares ``frozen=True``.

    Honors the ``bypasses_topology_invariant: ClassVar[dict[str, str]]``
    opt-out marker — if present and contains the ``"frozen_discipline"``
    key, the class is skipped (with non-empty justification asserted per
    FR-011 / SC-006).

    Args:
        classes: Sequence of Pydantic model classes to audit. Pass a
            single-class list to keep failures isolable to one class
            during pytest parametrization.

    Raises:
        AssertionError: On the first non-frozen, non-bypassed class
            encountered.
    """
    for cls in classes:
        cfg = getattr(cls, "model_config", None)
        if cfg is None:
            continue  # not a Pydantic v2 BaseModel — skip silently

        bypass = getattr(cls, "bypasses_topology_invariant", {})
        if not isinstance(bypass, dict):
            raise AssertionError(
                f"{cls.__qualname__}.bypasses_topology_invariant must be a "
                f"dict[str, str]; got {type(bypass).__name__}"
            )
        if "frozen_discipline" in bypass:
            justification = bypass["frozen_discipline"]
            if not isinstance(justification, str) or not justification.strip():
                raise AssertionError(
                    f"{cls.__qualname__} bypass marker for "
                    f"frozen_discipline has empty justification "
                    f"(FR-011 / SC-006)"
                )
            continue  # legitimately opted out

        frozen = cfg.get("frozen") if isinstance(cfg, dict) else getattr(cfg, "frozen", None)
        if frozen is not True:
            raise AssertionError(
                f"State-bearing model {cls.__qualname__} must declare "
                f"model_config = ConfigDict(frozen=True). Got "
                f"model_config['frozen']={frozen!r}"
            )


__all__ = ["assert_all_frozen", "discover_state_bearing_models"]
