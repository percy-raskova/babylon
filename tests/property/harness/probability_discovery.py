"""Discovery walkers for spec-054 US1 (Probability bound invariant).

Two helpers:

- :func:`discover_probability_fields` — walks every Pydantic model under
  ``babylon.models`` and yields ``(ModelClass, field_name)`` pairs whose
  annotation IS the ``Probability`` constrained type alias (identity check).

- :func:`discover_probability_formulas` — walks every public callable under
  ``babylon.formulas`` and yields each one whose declared return type is
  ``Probability`` (type-driven, no allow-list).

Per ``research.md §1`` and ``§2``: identity check via direct import is the
cleanest detection rule because ``Probability = Annotated[float, ...]`` is
hashable and identity-stable when bound to a name in the importing module.
``Coefficient`` and ``Intensity`` share the same numeric bounds but are
distinct annotation aliases — identity-by-import distinguishes them
unambiguously where metadata sniffing cannot.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from collections.abc import Callable
from functools import lru_cache
from typing import Any, get_type_hints

from pydantic import BaseModel

import babylon.formulas as formulas_pkg
import babylon.models as models_pkg
from babylon.models.types import Probability


@lru_cache(maxsize=1)
def discover_probability_fields() -> tuple[tuple[type[BaseModel], str], ...]:
    """Walk Pydantic models under ``babylon.models``; yield Probability fields.

    Returns each ``(ModelClass, field_name)`` pair whose annotation is
    identity-equal to ``babylon.models.types.Probability``.

    Detection uses ``typing.get_type_hints(cls, include_extras=True)`` rather
    than ``model_fields[name].annotation`` because Pydantic v2 unwraps the
    ``Annotated[float, ...]`` and exposes only the inner ``float`` via
    ``annotation``. ``include_extras=True`` preserves the wrapper so the
    identity check ``hint is Probability`` succeeds.

    Cached on first call.

    Returns:
        Immutable tuple of ``(cls, field_name)`` pairs. Order is the
        deterministic walk order (modules in ``pkgutil.iter_modules``
        listing, classes per ``inspect.getmembers``, fields per
        ``model_fields`` dict iteration).
    """
    pairs: list[tuple[type[BaseModel], str]] = []
    for cls in _iter_pydantic_models():
        try:
            hints = get_type_hints(cls, include_extras=True)
        except (NameError, TypeError):
            # Forward-references that fail to resolve at import time. Skip
            # rather than fail collection — these are rare and would already
            # break direct usage of the model.
            continue
        for name in cls.model_fields:
            if hints.get(name) is Probability:
                pairs.append((cls, name))
    return tuple(pairs)


@lru_cache(maxsize=1)
def discover_probability_formulas() -> tuple[Callable[..., Any], ...]:
    """Walk callables under ``babylon.formulas``; yield Probability-returning.

    Type-driven via ``typing.get_type_hints(fn).get("return") is Probability``.
    No allow-list. Adding a new probability formula and narrowing its return
    annotation to ``-> Probability`` extends coverage automatically.

    Returns:
        Immutable tuple of callables.
    """
    found: list[Callable[..., Any]] = []
    for fn in _iter_public_formulas():
        try:
            hints = get_type_hints(fn, include_extras=True)
        except (NameError, TypeError):
            # Forward-ref or otherwise unresolvable type hints; skip rather
            # than fail the entire test collection.
            continue
        if hints.get("return") is Probability:
            found.append(fn)
    return tuple(found)


# --------------------------------------------------------------------------- #
# Internal helpers                                                            #
# --------------------------------------------------------------------------- #


def _iter_pydantic_models() -> list[type[BaseModel]]:
    """Walk ``babylon.models`` recursively; return every BaseModel subclass."""
    seen: set[type[BaseModel]] = set()
    for mod in _iter_package_modules(models_pkg):
        for _name, obj in inspect.getmembers(mod, inspect.isclass):
            if not issubclass(obj, BaseModel):
                continue
            if obj is BaseModel:
                continue
            seen.add(obj)
    return sorted(seen, key=lambda c: (c.__module__, c.__qualname__))


def _iter_public_formulas() -> list[Callable[..., Any]]:
    """Walk ``babylon.formulas`` recursively; return public callables."""
    seen: set[Callable[..., Any]] = set()
    for mod in _iter_package_modules(formulas_pkg):
        for name, obj in inspect.getmembers(mod, inspect.isfunction):
            if name.startswith("_"):
                continue
            if obj.__module__ != mod.__name__:
                # Re-export from another module; will be picked up at its
                # source module's iteration to avoid double counting.
                continue
            seen.add(obj)
    return sorted(seen, key=lambda f: (f.__module__, f.__qualname__))


def _iter_package_modules(package: Any) -> list[Any]:
    """Recursively import every submodule of a package and return them."""
    modules: list[Any] = [package]
    if not hasattr(package, "__path__"):
        return modules
    for mod_info in pkgutil.walk_packages(package.__path__, prefix=f"{package.__name__}."):
        if mod_info.name.endswith(".__main__"):
            continue
        try:
            mod = importlib.import_module(mod_info.name)
        except ImportError:
            continue
        modules.append(mod)
    return modules


__all__ = ["discover_probability_fields", "discover_probability_formulas"]
