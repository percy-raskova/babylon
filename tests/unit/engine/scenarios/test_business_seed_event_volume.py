"""Event-volume regression for the ADR086 QCEW business seeding.

Pins the event-flood decision (ADR086): seeding is CAPPED at a small K per
scope, and the pre-existing OODA summary-event aggregation (spec-116
FR-116-4.7) already collapses every per-Business ``layer0`` ActionResult into
ONE ``ORGANIZATIONAL_ACTION`` bus event per tick — so the "one event per
business per tick" flood the naive design would cause never materializes.

Measured on the real ``us_nationwide`` session (ADR086): 6 orgs total (1 player
+ 5 businesses), exactly 1 ORGANIZATIONAL_ACTION event/tick, constant
turn_resolution payload. The naive per-hex alternative would be
1118 territories x 5 = 5590 businesses, blowing the engine's max_orgs=1000 cap.
"""

from __future__ import annotations

import pytest

from babylon.engine.context import TickContext
from babylon.engine.scenarios import create_us_scenario
from babylon.engine.scenarios.business_seeds import build_seeded_businesses
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.ooda import OODASystem
from babylon.kernel.event_bus import Event
from babylon.models.enums import EventType, OrgType

pytestmark = pytest.mark.unit

# Hard engine cap in ooda.layer0.process_layer0 / _collect_org_nodes: beyond
# this, businesses are SILENTLY dropped. Capped seeding must stay well under it.
_MAX_ORGS = 1000


class TestBusinessSeedEventVolume:
    def test_seeding_is_capped_far_under_the_engine_cap(self) -> None:
        state, _config, _defines = create_us_scenario()
        businesses = [o for o in state.organizations.values() if o.org_type == OrgType.BUSINESS]
        assert len(businesses) == len(build_seeded_businesses("US", []))
        # Total org count must stay far under the layer0/OODA max_orgs cap so
        # nothing is silently dropped.
        assert len(state.organizations) < _MAX_ORGS

    def test_one_org_action_event_per_tick_regardless_of_business_count(self) -> None:
        """The summary-event aggregation must emit exactly ONE
        ORGANIZATIONAL_ACTION per tick, NOT one per seeded business."""
        state, _config, defines = create_us_scenario()
        n_businesses = sum(
            1 for o in state.organizations.values() if o.org_type == OrgType.BUSINESS
        )
        assert n_businesses >= 2  # a meaningful flood test needs several

        graph = state.to_graph()
        services = ServiceContainer.create(defines=defines)

        recorded: list[Event] = []
        services.event_bus.subscribe(EventType.ORGANIZATIONAL_ACTION.value, recorded.append)

        system = OODASystem()
        for tick in range(2):
            recorded.clear()
            context = TickContext(tick=tick)
            system.step(graph, services, context)

            # Exactly one summary event, never one-per-business.
            assert len(recorded) == 1
            # The summary payload reports the real layer0 business count.
            assert recorded[0].payload["layer0_count"] == n_businesses
            # And the raw per-business results ride turn_resolution (not the bus).
            layer0 = context.persistent_data["turn_resolution"]["layer0_results"]
            assert len(layer0) == n_businesses
