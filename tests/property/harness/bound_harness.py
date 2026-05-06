"""``BoundInvariantHarness`` runner for spec-054 bound-invariant property tests.

Wraps a single System invocation (or a full pipeline) and applies a list of
``Invariant`` instances to the (pre, post) pair. Honors the
``bypasses_bound_invariant: ClassVar[dict[str, str]]`` opt-out marker per
``data-model.md §2.1``.

At import time, validates SC-006: every System with a
``bypasses_bound_invariant`` marker MUST carry a non-empty justification
string for every entry. Empty justifications fail collection.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Literal

from babylon.engine.context import TickContext
from babylon.engine.invariants import Invariant, InvariantResult
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.protocol import System
from babylon.models.world_state import WorldState

from .system_registry import all_systems

# A SystemRunner is anything that can take (graph, services, ctx) and mutate
# the graph in place. The harness can wrap either a single System (instantiated
# fresh per call) or a full-pipeline runner (typically ``SimulationEngine.run_tick``).
# Loose ``Callable[..., None]`` typing avoids subscripting ``nx.DiGraph`` at
# runtime — older NetworkX releases reject ``DiGraph[str]`` outside of
# ``from __future__ import annotations`` contexts.
SystemRunner = Callable[..., None]


@dataclass(frozen=True)
class HarnessResult:
    """Outcome of a single ``BoundInvariantHarness.run`` call.

    Attributes:
        system_name: Class name of the System under test, or ``"<pipeline>"``
            for full-pipeline runs.
        outcomes: Per-invariant outcome keyed by invariant name. Either an
            ``InvariantResult`` (passed/violated) or the literal string
            ``"SKIPPED"`` indicating the System opted out via
            ``bypasses_bound_invariant``.
        skip_reasons: Predicate name -> justification string copied verbatim
            from the System's marker. Empty if no skips.
    """

    system_name: str
    outcomes: dict[str, InvariantResult | Literal["SKIPPED"]] = field(default_factory=dict)
    skip_reasons: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class BoundInvariantHarness:
    """Runs a System (or pipeline) and applies bound invariants to (pre, post).

    Args:
        system: Either a System class (instantiated fresh per call) or a
            ``SystemRunner`` callable wrapping the full pipeline.
        invariants: Sequence of ``Invariant`` instances to check after the
            System runs.
        bypass_marker_attr: Class attribute name carrying the opt-out marker.
            Defaults to ``"bypasses_bound_invariant"``.
    """

    system: type[System] | SystemRunner
    invariants: Sequence[Invariant]
    bypass_marker_attr: str = "bypasses_bound_invariant"

    def run(
        self,
        pre: WorldState,
        services: ServiceContainer,
        ctx: TickContext,
    ) -> HarnessResult:
        """Run the System once and check each invariant.

        Args:
            pre: WorldState before step.
            services: ServiceContainer providing config/formulas/event_bus.
            ctx: TickContext (or dict-compatible).

        Returns:
            ``HarnessResult`` with per-invariant outcomes.
        """
        if isinstance(self.system, type):
            system_instance = self.system()
            system_name = self.system.__name__
            marker = self._read_marker(self.system)
            runner: SystemRunner = system_instance.step
        else:
            system_name = "<pipeline>"
            marker = {}
            runner = self.system

        graph = pre.to_graph()
        runner(graph, services, ctx)
        post = WorldState.from_graph(graph, tick=pre.tick + 1)

        outcomes: dict[str, InvariantResult | Literal["SKIPPED"]] = {}
        skip_reasons: dict[str, str] = {}
        for invariant in self.invariants:
            if invariant.name in marker:
                outcomes[invariant.name] = "SKIPPED"
                skip_reasons[invariant.name] = marker[invariant.name]
                continue
            outcomes[invariant.name] = invariant.check(pre, post)

        return HarnessResult(
            system_name=system_name,
            outcomes=outcomes,
            skip_reasons=skip_reasons,
        )

    @staticmethod
    def _read_marker(system_cls: type[System]) -> dict[str, str]:
        """Read the ``bypasses_bound_invariant`` ClassVar if present."""
        marker = getattr(system_cls, "bypasses_bound_invariant", None)
        if marker is None:
            return {}
        if not isinstance(marker, dict):
            msg = (
                f"{system_cls.__name__}.bypasses_bound_invariant must be a "
                f"dict[str, str]; got {type(marker).__name__}"
            )
            raise TypeError(msg)
        return marker


def _validate_all_markers() -> None:
    """At import time, machine-enforce SC-006 across every registered System.

    For every System with a ``bypasses_bound_invariant`` marker, asserts that
    every value (justification string) is non-empty after stripping. Empty
    justifications fail collection rather than slipping through review.
    """
    for cls in all_systems():
        marker = getattr(cls, "bypasses_bound_invariant", None)
        if marker is None:
            continue
        if not isinstance(marker, dict):
            msg = (
                f"{cls.__name__}.bypasses_bound_invariant must be a "
                f"dict[str, str]; got {type(marker).__name__}"
            )
            raise TypeError(msg)
        for predicate, justification in marker.items():
            if not isinstance(justification, str) or not justification.strip():
                msg = (
                    f"{cls.__name__}.bypasses_bound_invariant[{predicate!r}] "
                    f"has empty justification; SC-006 requires every marker "
                    f"entry to carry a non-empty explanation."
                )
                raise ValueError(msg)


# Run the import-time check exactly once.
_validate_all_markers()


__all__ = [
    "BoundInvariantHarness",
    "HarnessResult",
    "SystemRunner",
]
