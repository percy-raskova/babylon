"""SystemCallSpy — wraps every ``System.step`` on an engine to record
invocation traces for spec-056 US1 + US2.

Per data-model.md §2.2 and research.md §3 — the spy is observably
non-interfering: forwards args/kwargs and the return value unchanged,
only side-effect is appending to ``self.events``. FR-012 verifies
non-interference via a paired test that runs the same starting state
with and without the spy and asserts post-tick model_dump-equality.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType

    from babylon.engine.simulation_engine import SimulationEngine
    from babylon.kernel.system_protocol import System
    from tests.property.harness.causal_harness import SystemCallEvent


class SystemCallSpy:
    """Context manager that wraps every System on an engine to record
    each ``step()`` invocation with ``(system_class_name, call_index,
    monotonic_timestamp_ns)``.

    Usage::

        with SystemCallSpy(engine) as spy:
            engine.run_tick(graph, services, context)
        # spy.events now holds one SystemCallEvent per System invocation
    """

    def __init__(self, engine: SimulationEngine) -> None:
        self._engine = engine
        self._originals: dict[int, object] = {}  # id(system) -> original step
        self.events: list[SystemCallEvent] = []
        self._call_index = 0

    def __enter__(self) -> SystemCallSpy:
        from tests.property.harness.causal_harness import SystemCallEvent

        # Wrap each system's bound `step` method.
        for system in self._engine._systems:  # noqa: SLF001 - test instrumentation
            original = system.step
            self._originals[id(system)] = original

            def make_wrapper(sys_obj: System, original_step: object) -> object:
                def wrapped(*args: object, **kwargs: object) -> object:
                    self.events.append(
                        SystemCallEvent(
                            system_class_name=type(sys_obj).__name__,
                            call_index=self._call_index,
                            monotonic_timestamp_ns=time.monotonic_ns(),
                        )
                    )
                    self._call_index += 1
                    return original_step(*args, **kwargs)  # type: ignore[operator]

                return wrapped

            system.step = make_wrapper(system, original)  # type: ignore[method-assign]
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        # Restore originals
        for system in self._engine._systems:  # noqa: SLF001 - test instrumentation
            original = self._originals.get(id(system))
            if original is not None:
                system.step = original  # type: ignore[method-assign]
        # Sanity: timestamps strictly monotonic
        if exc_type is None and len(self.events) >= 2:
            for prev, curr in zip(self.events, self.events[1:], strict=False):
                assert curr.monotonic_timestamp_ns >= prev.monotonic_timestamp_ns, (
                    f"SystemCallSpy timestamp non-monotonic: "
                    f"{prev.system_class_name} ({prev.monotonic_timestamp_ns}) -> "
                    f"{curr.system_class_name} ({curr.monotonic_timestamp_ns})"
                )
