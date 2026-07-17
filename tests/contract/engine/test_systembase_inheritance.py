"""Contract test: every canonical-order System inherits from SystemBase (Spec 059 SC-005).

Derives the expected System list from
:data:`babylon.engine.simulation_engine._DEFAULT_SYSTEMS` — the engine's
canonical tick order (per project ``CLAUDE.md``, the source of truth) —
rather than a hand-maintained count. Adding, removing, or reordering a
System in ``_DEFAULT_SYSTEMS`` changes this contract's coverage
automatically; nothing here needs to be updated by hand.
"""

from __future__ import annotations

import pytest

from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS
from babylon.kernel.system_base import SystemBase
from babylon.kernel.system_protocol import System

#: Concrete classes behind the canonical tick order, deduplicated while
#: preserving first-seen order. Not a hand-maintained list — derived from
#: the running engine's own System instances.
SYSTEM_CLASSES: list[type[System]] = list(
    dict.fromkeys(type(system) for system in _DEFAULT_SYSTEMS)
)


@pytest.mark.parametrize("cls", SYSTEM_CLASSES, ids=[cls.__name__ for cls in SYSTEM_CLASSES])
def test_system_inherits_systembase(cls: type[System]) -> None:
    """SC-005: ``issubclass(cls, SystemBase)`` for every System in ``_DEFAULT_SYSTEMS``."""
    assert issubclass(cls, SystemBase), (
        f"{cls.__module__}.{cls.__name__} must inherit from SystemBase (FR-009)"
    )
