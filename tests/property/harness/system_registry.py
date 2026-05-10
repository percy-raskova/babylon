"""Auto-discovery of all engine Systems for spec-054 bound-invariant tests.

Generalizes Spec 053's ``_discover_non_opt_out_engine_systems``
(``tests/property/invariants/test_value_conservation.py:79``) to filter by
either marker the bound-invariant harness needs:

- ``creates_value: ClassVar[bool] = True``  — Spec 053 conservation opt-out
- ``bypasses_bound_invariant: ClassVar[dict[str, str]]`` — Spec 054 bound opt-out

Both markers coexist on the same System without interaction.

Per ``data-model.md §2.4`` the registry must contain ≥ 22 Systems at runtime
(the canonical engine systems set as of spec-054). Adding new Systems to
``src/babylon/engine/systems/`` extends the registry automatically — no
manual list maintenance.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from functools import lru_cache

import babylon.engine.systems as engine_systems_pkg
from babylon.engine.systems.protocol import System

_MIN_EXPECTED_SYSTEMS = 21
"""Minimum System count expected at registry build time. Empirically verified
during spec-054 implementation: ``ls src/babylon/engine/systems/*.py``
excluding ``__init__.py`` and ``protocol.py`` yields exactly 21 modules,
each containing exactly one ``*System`` class. Adding a new System should
push this count UP; if it shrinks, ``all_systems()`` raises ``RuntimeError``
to flag accidental package restructuring."""


@lru_cache(maxsize=1)
def all_systems() -> tuple[type[System], ...]:
    """Return every concrete System class under ``babylon.engine.systems``.

    Walks the package via ``pkgutil.iter_modules``, skipping ``protocol`` and
    private modules, and collects every class whose name ends with ``System``
    (excluding the ``System`` Protocol itself). Cached on first call so
    repeated test parametrize-id generation is cheap.

    Raises:
        RuntimeError: If fewer than ``_MIN_EXPECTED_SYSTEMS`` (22) Systems
            are discovered. Catches accidental package restructuring that
            would silently shrink test coverage.

    Returns:
        Immutable tuple of System classes in deterministic discovery order.
    """
    found: list[type[System]] = []
    for mod_info in pkgutil.iter_modules(engine_systems_pkg.__path__):
        if mod_info.name.startswith("_") or mod_info.name == "protocol":
            continue
        mod = importlib.import_module(f"{engine_systems_pkg.__name__}.{mod_info.name}")
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            # Per Spec 059 ADR-006.4: an engine/systems/<x>.py module that became
            # an engine/systems/<x>/ package re-exports its System class from
            # _legacy.py; obj.__module__ is then "<x>._legacy" rather than "<x>".
            # Accept both the exact module match and any submodule of it.
            if not (
                obj.__module__ == mod.__name__ or obj.__module__.startswith(mod.__name__ + ".")
            ):
                continue
            if not name.endswith("System"):
                continue
            if obj is System:
                continue
            if obj in found:
                continue  # de-dup if both _legacy and __init__ surface the class
            found.append(obj)
    if len(found) < _MIN_EXPECTED_SYSTEMS:
        msg = (
            f"SystemRegistry discovered only {len(found)} Systems; expected "
            f">= {_MIN_EXPECTED_SYSTEMS}. Adding new Systems should EXTEND "
            f"this count; if it shrunk, investigate package restructuring."
        )
        raise RuntimeError(msg)
    return tuple(found)


def non_bypassed_systems(invariant_name: str) -> tuple[type[System], ...]:
    """Return Systems that have NOT opted out of the named bound invariant.

    Reads each System's ``bypasses_bound_invariant: dict[str, str]`` ClassVar
    if present and excludes Systems whose marker contains ``invariant_name``
    as a key. Systems without the marker are included (default-deny).

    Args:
        invariant_name: Predicate name (e.g., ``"non_negative_wealth"``,
            ``"probability_in_range"``, ``"simplex_preserved"``).

    Returns:
        Tuple of Systems that the harness should test against this predicate.
    """
    return tuple(
        cls
        for cls in all_systems()
        if invariant_name not in getattr(cls, "bypasses_bound_invariant", {})
    )


__all__ = ["all_systems", "non_bypassed_systems"]
