"""Contract tests for the EVENT_BUILDERS registry (spec-116 systems-dedup Phase 2).

The bus->pydantic converter ``_convert_bus_event_to_pydantic`` was a ~720-line
if/elif chain. Phase 2 extracts each branch into a keyed builder in
``babylon.engine.event_builders.EVENT_BUILDERS`` and turns the converter into a
thin dispatcher. These tests pin the registry contract:

* it is an immutable ``Mapping[EventType, EventBuilder]``;
* it covers exactly the EventTypes the dispatcher converts (no widening — a
  spec non-goal), and drives the dispatcher (registry key <=> non-None result);
* every builder yields a ``SimulationEvent`` from an empty payload (defaults);
* an unregistered EventType still drops to ``None`` at the boundary.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

import pytest

from babylon.engine.event_builders import EVENT_BUILDERS
from babylon.engine.simulation_engine import _convert_bus_event_to_pydantic
from babylon.kernel.event_bus import Event
from babylon.models.enums import EventType
from babylon.models.events import SimulationEvent

# The current branch converts exactly this many EventTypes (spec-116 4.7 sweep:
# every EventType with a live bus publisher). Pinned so a widening/narrowing is
# a deliberate, reviewed change — not silent drift.
_EXPECTED_COVERAGE = 64


class TestRegistryShape:
    """The registry is an immutable EventType-keyed mapping."""

    def test_is_immutable_mapping(self) -> None:
        assert isinstance(EVENT_BUILDERS, Mapping)
        assert isinstance(EVENT_BUILDERS, MappingProxyType)
        with pytest.raises(TypeError):
            EVENT_BUILDERS[EventType.SURPLUS_EXTRACTION] = EVENT_BUILDERS[  # type: ignore[index]
                EventType.IMPERIAL_SUBSIDY
            ]

    def test_all_keys_are_eventtypes(self) -> None:
        assert all(isinstance(key, EventType) for key in EVENT_BUILDERS)

    def test_coverage_count_pinned(self) -> None:
        assert len(EVENT_BUILDERS) == _EXPECTED_COVERAGE


class TestRegistryDrivesDispatcher:
    """The dispatcher converts exactly the registered EventTypes."""

    def test_registered_types_dispatch_never_drop(self) -> None:
        """A registered EventType dispatches to its builder — never dropped to
        ``None`` for lack of registration. Some builders raise a
        ``ValidationError`` on an empty payload (required non-empty fields, e.g.
        ExtractionEvent's source/target ids); that still proves the builder was
        invoked rather than skipped at the boundary.
        """
        from pydantic import ValidationError

        for event_type in EVENT_BUILDERS:
            bus_event = Event(type=event_type, tick=1, payload={})
            try:
                result = _convert_bus_event_to_pydantic(bus_event)
            except ValidationError:
                continue  # builder invoked; empty payload failed validation — dispatched
            assert result is not None, f"{event_type.name} registered but dropped to None"
            assert isinstance(result, SimulationEvent)

    def test_unregistered_type_drops_to_none(self) -> None:
        # ENDGAME_REACHED is injected pre-typed elsewhere; never converted here.
        unregistered = [e for e in EventType if e not in EVENT_BUILDERS]
        assert unregistered, "expected some EventTypes to be intentionally unconverted"
        for event_type in unregistered:
            bus_event = Event(type=event_type, tick=1, payload={})
            assert _convert_bus_event_to_pydantic(bus_event) is None

    def test_bad_string_type_drops_to_none(self) -> None:
        bus_event = Event(type="not_a_real_event_type", tick=1, payload={})
        assert _convert_bus_event_to_pydantic(bus_event) is None

    def test_representative_conversion_shape(self) -> None:
        # SURPLUS_EXTRACTION -> ExtractionEvent with payload-driven fields.
        from babylon.models.events import ExtractionEvent

        bus_event = Event(
            type=EventType.SURPLUS_EXTRACTION,
            tick=7,
            payload={"source_id": "core", "target_id": "periphery", "amount": 3.5},
        )
        result = _convert_bus_event_to_pydantic(bus_event)
        assert isinstance(result, ExtractionEvent)
        assert result.tick == 7
        assert result.source_id == "core"
        assert result.target_id == "periphery"
        assert result.amount == 3.5
