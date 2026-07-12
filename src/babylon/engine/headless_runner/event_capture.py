"""Engine event capture for the headless runner.

Spec: 065-engine-bridging (T003 / T070).

The :class:`EventCapture` subscribes to the engine's ``EventBus`` and
buffers every ``EventType`` fired during the tick loop. At end of run
the buffer is drained and emitted into ``summary.json.events`` in
deterministic emission order (FR-018).

This is the narrative spine of the run: every ``SuperwageCrisis``,
``ClassDecomposition``, ``ControlRatioCrisis``, ``TerminalDecision``,
``ExcessiveForce``, ``Uprising``, etc. fires through here.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["EngineEvent", "EventCapture"]


class EngineEvent(BaseModel):
    """One fired engine event, awaiting serialization into summary.events."""

    model_config = ConfigDict(frozen=True)

    tick: int = Field(ge=0)
    event_type: str
    entity_ids: tuple[str, ...] = Field(default_factory=tuple)
    severity: Literal["info", "warning", "error", "critical"] = "info"
    details: dict[str, Any] = Field(default_factory=dict)


# Common engine-event payload attribute names we probe for entity ids.
# Engine systems vary; this is the union of observed conventions.
_ENTITY_ID_ATTRS: tuple[str, ...] = (
    "affected_entity_ids",
    "affected_class_id",
    "county_fips",
    "fips",
    "entity_id",
    "node_id",
)


class EventCapture:
    """EventBus subscriber that collects engine events for summary.json."""

    def __init__(self) -> None:
        self._buffer: list[EngineEvent] = []
        self._current_tick: int = 0

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)

    def set_tick(self, tick: int) -> None:
        """Tag subsequent ``on_event`` calls with this tick number.

        Called by the runner at the start of each tick BEFORE
        ``engine.run_tick(...)``.
        """
        if tick < 0:
            raise ValueError(f"tick must be non-negative, got {tick}")
        self._current_tick = tick

    def on_event(self, event: Any) -> None:
        """``EventBus`` subscriber callback. Preserves emission order."""
        event_type = self._extract_event_type(event)
        entity_ids = self._extract_entity_ids(event)
        severity = self._extract_severity(event)
        details = self._extract_details(event)

        self._buffer.append(
            EngineEvent(
                tick=self._current_tick,
                event_type=event_type,
                entity_ids=entity_ids,
                severity=severity,  # type: ignore[arg-type]
                details=details,
            )
        )

    def drain(self) -> tuple[EngineEvent, ...]:
        """Return captured events (in emission order); buffer is preserved.

        Idempotent calls return the same tuple (the buffer is not
        cleared on read — callers can re-drain for summary writing
        plus per-tick debug introspection).
        """
        return tuple(self._buffer)

    @staticmethod
    def _extract_event_type(event: Any) -> str:
        # Typed domain events expose ``event_type``; kernel ``event_bus.Event``
        # dataclasses expose ``type`` (an EventType). Check BOTH — otherwise
        # every bus-published event (e.g. TERMINAL_DECISION, SUPERWAGE_CRISIS)
        # collapses to the class name "Event", which silently starved the
        # Carceral phase-milestone detection on the headless backend
        # (Constitution III.11 — a plausible-but-wrong default).
        for attr in ("event_type", "type"):
            if hasattr(event, attr):
                t = getattr(event, attr)
                return str(t.value) if hasattr(t, "value") else str(t)
        return str(event.__class__.__name__)

    @staticmethod
    def _extract_entity_ids(event: Any) -> tuple[str, ...]:
        for attr in _ENTITY_ID_ATTRS:
            if hasattr(event, attr):
                val = getattr(event, attr)
                if val is None:
                    continue
                if isinstance(val, str):
                    return (val,)
                try:
                    return tuple(str(x) for x in val)
                except TypeError:
                    return (str(val),)
        return ()

    @staticmethod
    def _extract_severity(event: Any) -> str:
        sev = getattr(event, "severity", "info")
        if hasattr(sev, "value"):
            sev = sev.value
        sev = str(sev).lower()
        if sev not in {"info", "warning", "error", "critical"}:
            return "info"
        return sev

    @staticmethod
    def _extract_details(event: Any) -> dict[str, Any]:
        # Pydantic models expose model_dump; fall back to __dict__.
        if hasattr(event, "model_dump"):
            try:
                full = event.model_dump(mode="json")
            except Exception:
                full = {}
        elif hasattr(event, "__dict__"):
            full = {k: v for k, v in event.__dict__.items() if not k.startswith("_")}
        else:
            full = {}
        # Strip the fields we already promoted to top-level entries.
        return {
            k: v
            for k, v in full.items()
            if k not in {"event_type", "severity", "tick", *_ENTITY_ID_ATTRS}
        }
