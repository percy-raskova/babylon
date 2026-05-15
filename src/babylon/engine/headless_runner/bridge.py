"""WorldState ↔ Postgres bridge for the headless runner.

Spec: 065-engine-bridging (T002 / T040 / T041).

The bridge adapts the in-memory ``WorldState`` Pydantic model to the
per-tick Postgres subsystem tables (spec-062 schema + spec-065
additions in migrations 0020-0023). Lifecycle within one run:

  1. :meth:`WorldStateBridge.hydrate_initial` — one-shot at session
     init. Builds the initial ``WorldState`` from the tick-0
     ``view_runtime_trace_emission`` + boundary nodes, and subscribes
     :class:`EventCapture` to the engine's ``EventBus``.
  2. Each tick the runner mutates the ``WorldState`` in-place via
     ``engine.run_tick(graph, services, context)``.
  3. :meth:`WorldStateBridge.persist_tick` — serializes the delta
     into a :class:`PerTickTransactionEnvelope` and writes via
     ``runtime.persist_tick_atomic``.

The bridge owns no engine logic; it is purely a serialization adapter
(Constitution II.6: State is Data, Engine is Transformation).
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from babylon.config.defines import GameDefines
    from babylon.engine.headless_runner.event_capture import EngineEvent, EventCapture

__all__ = ["WorldStateBridge"]


class WorldStateBridge:
    """Adapter between in-memory ``WorldState`` and per-tick Postgres state.

    See ``specs/065-engine-bridging/contracts/engine_bridge_protocol.yaml``
    for the canonical contract.
    """

    def __init__(self, runtime: Any, defines: GameDefines) -> None:
        self._runtime = runtime
        self._defines = defines
        self._session_id: UUID | None = None
        self._scope_fips: frozenset[str] | None = None
        self._hydrated = False
        self._event_capture: EventCapture | None = None
        self._endgame_detector: Any = None

    @property
    def runtime(self) -> Any:
        return self._runtime

    @property
    def event_capture(self) -> EventCapture | None:
        return self._event_capture

    def hydrate_initial(
        self,
        session_id: UUID,
        scope_fips: frozenset[str],
        event_capture: EventCapture | None = None,
    ) -> Any:
        """Build the initial ``WorldState`` from tick-0 Postgres state.

        Phase-2 stub. Full implementation lands in T040.
        """
        if self._hydrated:
            raise RuntimeError(
                "WorldStateBridge.hydrate_initial called twice on the same "
                "instance; one bridge per session"
            )
        self._session_id = session_id
        self._scope_fips = scope_fips
        self._event_capture = event_capture
        self._hydrated = True
        raise NotImplementedError("WorldStateBridge.hydrate_initial — T040")

    def persist_tick(
        self,
        world: Any,
        tick: int,
        determinism_hash: str,
    ) -> None:
        """Serialize WorldState delta into the spec-062 envelope + persist.

        Phase-2 stub. Full implementation lands in T041.
        """
        raise NotImplementedError("WorldStateBridge.persist_tick — T041")

    def refresh_event_log(self) -> tuple[EngineEvent, ...]:
        """Drain accumulated engine events for ``summary.json.events``."""
        if self._event_capture is None:
            return ()
        return self._event_capture.drain()

    def set_endgame_detector(self, dotted_path: str) -> None:
        """Resolve a dotted import path to an ``EndgameDetector`` instance.

        Phase-2 stub. Full implementation lands in T063.
        """
        module_path, _, attr = dotted_path.rpartition(".")
        if not module_path:
            raise ImportError(f"--endgame-detector value {dotted_path!r} is not a dotted path")
        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:
            raise ImportError(
                f"--endgame-detector module {module_path!r} could not be imported: {exc}"
            ) from exc
        detector_cls = getattr(module, attr, None)
        if detector_cls is None:
            raise ImportError(
                f"--endgame-detector path {dotted_path!r}: "
                f"module {module_path!r} has no attribute {attr!r}"
            )
        self._endgame_detector = detector_cls() if callable(detector_cls) else detector_cls

    def poll_endgame(self, world: Any, tick: int) -> Any:
        """Invoke the configured endgame detector. None if none configured."""
        if self._endgame_detector is None:
            return None
        return self._endgame_detector.check(world, tick)
