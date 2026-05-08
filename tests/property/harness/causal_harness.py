"""Shared event dataclasses + import surface for spec-056 causal invariants.

Per data-model.md §2.1 (revised post-/speckit.analyze C1 finding):
the original `CausalInvariantHarness` runner class was dropped per
YAGNI — every test in spec-056 Phases 3–6 invokes the spy / context-
manager primitives directly without going through a wrapper, matching
Spec 055's `TopologyInvariantHarness` light-touch usage.

This module:
  - Defines the three frozen event dataclasses (`SystemCallEvent`,
    `OrganizationActionEvent`, `TickTrace`).
  - Re-exports the spy classes + DB-I/O context manager from their
    sibling modules so test files import from one canonical place.
  - At import time, machine-asserts spec-056 SC-006: every System
    that carries a `bypasses_causal_invariant` ClassVar marker has
    non-empty justification strings.
"""

from __future__ import annotations

from dataclasses import dataclass

from tests.property.harness.no_db_io_during_tick import (
    DBIONotPermittedError,
    no_db_io_during_tick,
)
from tests.property.harness.org_action_spy import OrganizationActionSpy
from tests.property.harness.system_call_spy import SystemCallSpy
from tests.property.harness.system_registry import all_systems

__all__ = [
    "DBIONotPermittedError",
    "OrganizationActionEvent",
    "OrganizationActionSpy",
    "SystemCallEvent",
    "SystemCallSpy",
    "TickTrace",
    "no_db_io_during_tick",
]


@dataclass(frozen=True)
class SystemCallEvent:
    """One System.step() invocation observed by SystemCallSpy.

    Attributes:
        system_class_name: ``type(system).__name__`` at invocation time.
        call_index: Zero-based invocation index within this tick (0 for
            the first System called, monotonic across the tick).
        monotonic_timestamp_ns: ``time.monotonic_ns()`` at the moment
            the spy intercepted the call. Used for cross-spy ordering
            comparisons (US2 needs Consequence-System timestamps to
            postdate per-organization action timestamps).
    """

    system_class_name: str
    call_index: int
    monotonic_timestamp_ns: int


@dataclass(frozen=True)
class OrganizationActionEvent:
    """One per-organization action resolution observed by
    OrganizationActionSpy.

    Attributes:
        organization_id: Org node ID whose ``_resolve_for_organization``
            invocation produced this event.
        action_resolution_index: Zero-based per-tick action-resolution
            index (0 for the first org resolved this tick).
        monotonic_timestamp_ns: ``time.monotonic_ns()`` at the moment
            the spy intercepted the per-org call. Shares the clock
            domain with ``SystemCallEvent.monotonic_timestamp_ns``.
    """

    organization_id: str
    action_resolution_index: int
    monotonic_timestamp_ns: int


@dataclass(frozen=True)
class TickTrace:
    """Frozen aggregator pairing system-call and per-organization-action
    event lists from a single tick.

    Per data-model.md §2.4 (post-C2): tests iterate ``system_calls``
    and ``org_actions`` directly with comprehensions; no helper methods
    on this dataclass. The shape is purely to bundle the two event
    sequences together for one-tick-at-a-time test loops.
    """

    system_calls: tuple[SystemCallEvent, ...]
    org_actions: tuple[OrganizationActionEvent, ...]


# Import-time spec-056 SC-006 enforcement: every System with a
# `bypasses_causal_invariant` ClassVar must declare non-empty
# justification strings. Default-deny — most Systems carry no marker;
# those that do must explain why.
_BYPASS_MARKER = "bypasses_causal_invariant"


def _validate_bypass_markers() -> None:
    """Walk every System in the registry; assert any
    `bypasses_causal_invariant` ClassVar contains only non-empty values."""
    for cls in all_systems():
        marker = getattr(cls, _BYPASS_MARKER, None)
        if marker is None:
            continue
        if not isinstance(marker, dict):
            raise AssertionError(
                f"{cls.__name__}.{_BYPASS_MARKER} must be a dict[str, str]; "
                f"got {type(marker).__name__}"
            )
        for predicate_name, justification in marker.items():
            if not isinstance(justification, str) or not justification.strip():
                raise AssertionError(
                    f"{cls.__name__}.{_BYPASS_MARKER}[{predicate_name!r}] "
                    f"must be a non-empty justification string (spec-056 SC-006); "
                    f"got {justification!r}"
                )


_validate_bypass_markers()
