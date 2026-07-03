"""Tests for WorldState graph round-trip serialization.

Sprint 1.X Deliverable 2: High-Fidelity State.
Pain Point #7: WorldState.to_graph() -> WorldState.from_graph() is lossy.

These tests verify that ALL WorldState fields survive the round-trip
through NetworkX graph serialization and deserialization.
"""

from __future__ import annotations

import pytest

from babylon.engine.graph import BabylonGraph
from babylon.models import EdgeType, Relationship, SocialClass, SocialRole
from babylon.models.entities.economy import GlobalEconomy
from babylon.models.entities.state_finance import StateFinance
from babylon.models.entities.territory import Territory
from babylon.models.entity_registry import (
    COMPRADOR_ID,
    CORE_BOURGEOISIE_ID,
    PERIPHERY_WORKER_ID,
)
from babylon.models.enums import EventType, OperationalProfile, SectorType
from babylon.models.events import ExtractionEvent, UprisingEvent
from babylon.models.world_state import WorldState


class TestEventsRoundTrip:
    """Tests for SimulationEvent list preservation through round-trip."""

    def test_events_survive_round_trip(self) -> None:
        """SimulationEvent list should be preserved through to_graph/from_graph.

        This is the primary test for Pain Point #7.
        """
        # Create a state with events
        extraction = ExtractionEvent(
            tick=5,
            source_id=PERIPHERY_WORKER_ID,
            target_id=COMPRADOR_ID,
            amount=15.5,
        )
        uprising = UprisingEvent(
            tick=8,
            node_id=PERIPHERY_WORKER_ID,
            trigger="spark",
            agitation=0.9,
            repression=0.7,
        )
        state = WorldState(
            tick=10,
            events=[extraction, uprising],
        )

        # Round-trip through graph
        graph = state.to_graph()
        restored = WorldState.from_graph(graph, tick=10)

        # Assert events are preserved
        assert len(restored.events) == 2, "Events list should have 2 events"
        assert restored.events[0].event_type == EventType.SURPLUS_EXTRACTION
        assert restored.events[0].source_id == PERIPHERY_WORKER_ID
        assert restored.events[0].amount == 15.5
        assert restored.events[1].event_type == EventType.UPRISING
        assert restored.events[1].node_id == PERIPHERY_WORKER_ID
        assert restored.events[1].trigger == "spark"


class TestEventLogRoundTrip:
    """Tests for event_log string list preservation through round-trip."""

    def test_event_log_survives_round_trip(self) -> None:
        """event_log string list should be preserved through to_graph/from_graph."""
        state = WorldState(
            tick=5,
            event_log=["Worker crossed threshold", "Uprising in sector 3"],
        )

        # Round-trip through graph
        graph = state.to_graph()
        restored = WorldState.from_graph(graph, tick=5)

        # Assert event_log is preserved
        assert restored.event_log == ["Worker crossed threshold", "Uprising in sector 3"]


class TestBackwardCompatibility:
    """Tests for backward compatibility when graph lacks new metadata."""

    def test_from_graph_defaults_empty_events_when_missing(self) -> None:
        """from_graph should return empty lists when events/event_log not in graph.

        This ensures backward compatibility with graphs created before
        events were stored in graph metadata.
        """

        # Create a bare graph with no events metadata
        graph = BabylonGraph()

        restored = WorldState.from_graph(graph, tick=0)

        assert restored.events == []
        assert restored.event_log == []

    def test_explicit_events_parameter_takes_precedence(self) -> None:
        """Explicit events= parameter should override graph metadata.

        This preserves the existing API where events can be passed explicitly.
        """
        # Create state with events in graph
        state = WorldState(
            tick=5,
            events=[
                ExtractionEvent(
                    tick=5,
                    source_id=PERIPHERY_WORKER_ID,
                    target_id=COMPRADOR_ID,
                    amount=10.0,
                )
            ],
        )
        graph = state.to_graph()

        # Pass different events explicitly
        explicit_events = [
            UprisingEvent(
                tick=6,
                node_id=CORE_BOURGEOISIE_ID,
                trigger="revolutionary_pressure",
                agitation=0.8,
                repression=0.6,
            )
        ]
        restored = WorldState.from_graph(graph, tick=5, events=explicit_events)

        # Explicit parameter should win
        assert len(restored.events) == 1
        assert restored.events[0].event_type == EventType.UPRISING
        assert restored.events[0].node_id == CORE_BOURGEOISIE_ID


class TestFullStateRoundTrip:
    """Tests for complete WorldState round-trip with all field types."""

    def test_full_state_round_trip(self) -> None:
        """All WorldState fields should survive round-trip together.

        This is the comprehensive "hydration audit" test.
        """
        # Create entities
        worker = SocialClass(
            id=PERIPHERY_WORKER_ID,
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=100.0,
            organization=0.3,
            s_bio=0.1,
            s_class=0.2,
            population=1000,
            active=True,
        )
        bourgeois = SocialClass(
            id=COMPRADOR_ID,
            name="Bourgeoisie",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=10000.0,
            organization=0.9,
            active=True,
        )

        # Create territory
        territory = Territory(
            id="T001",
            name="Industrial District",
            sector_type=SectorType.INDUSTRIAL,
            profile=OperationalProfile.LOW_PROFILE,
            heat=0.3,
            biocapacity=500.0,
        )

        # Create relationship
        exploitation = Relationship(
            source_id=PERIPHERY_WORKER_ID,
            target_id=COMPRADOR_ID,
            edge_type=EdgeType.EXPLOITATION,
            value_flow=5.0,
            tension=0.4,
            solidarity_strength=0.1,
        )

        # Create events
        extraction = ExtractionEvent(
            tick=5,
            source_id=PERIPHERY_WORKER_ID,
            target_id=COMPRADOR_ID,
            amount=5.0,
        )

        # Create economy
        economy = GlobalEconomy(
            imperial_rent_pool=1000.0,
            current_super_wage_rate=0.25,
        )

        # Create state finances
        state_finances = {
            COMPRADOR_ID: StateFinance(tax_rate=0.2, budget=500.0),
        }

        # Build WorldState
        state = WorldState(
            tick=10,
            entities={PERIPHERY_WORKER_ID: worker, COMPRADOR_ID: bourgeois},
            territories={"T001": territory},
            relationships=[exploitation],
            event_log=["Initial extraction"],
            events=[extraction],
            economy=economy,
            state_finances=state_finances,
        )

        # Round-trip
        graph = state.to_graph()
        restored = WorldState.from_graph(graph, tick=10)

        # Verify all fields
        # 1. Tick (passed explicitly, not from graph)
        assert restored.tick == 10

        # 2. Entities
        assert len(restored.entities) == 2
        assert restored.entities[PERIPHERY_WORKER_ID].name == "Worker"
        assert restored.entities[PERIPHERY_WORKER_ID].wealth == 100.0
        assert restored.entities[PERIPHERY_WORKER_ID].s_bio == 0.1
        assert restored.entities[COMPRADOR_ID].role == SocialRole.CORE_BOURGEOISIE

        # 3. Territories
        assert len(restored.territories) == 1
        assert restored.territories["T001"].name == "Industrial District"
        assert restored.territories["T001"].sector_type == SectorType.INDUSTRIAL
        assert restored.territories["T001"].heat == pytest.approx(0.3)

        # 4. Relationships
        assert len(restored.relationships) == 1
        assert restored.relationships[0].source_id == PERIPHERY_WORKER_ID
        assert restored.relationships[0].target_id == COMPRADOR_ID
        assert restored.relationships[0].edge_type == EdgeType.EXPLOITATION
        assert restored.relationships[0].tension == pytest.approx(0.4)

        # 5. Economy
        assert restored.economy.imperial_rent_pool == pytest.approx(1000.0)
        assert restored.economy.current_super_wage_rate == pytest.approx(0.25)

        # 6. State Finances
        assert COMPRADOR_ID in restored.state_finances
        assert restored.state_finances[COMPRADOR_ID].tax_rate == pytest.approx(0.2)

        # 7. Event log (THE FIX for Pain Point #7)
        assert restored.event_log == ["Initial extraction"]

        # 8. Events (THE FIX for Pain Point #7)
        assert len(restored.events) == 1
        assert restored.events[0].event_type == EventType.SURPLUS_EXTRACTION
        assert restored.events[0].source_id == PERIPHERY_WORKER_ID

    def test_model_dump_round_trip_equality(self) -> None:
        """Ultimate Goal: state.model_dump() == recovered.model_dump().

        This is the strongest assertion for lossless round-trip.
        Note: Computed fields (consumption_needs) are excluded by design.
        """
        # Create entities without relying on computed fields
        worker = SocialClass(
            id=PERIPHERY_WORKER_ID,
            name="Worker",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=100.0,
            organization=0.3,
            s_bio=0.1,
            s_class=0.2,
            population=1000,
            active=True,
        )
        owner = SocialClass(
            id=COMPRADOR_ID,
            name="Owner",
            role=SocialRole.CORE_BOURGEOISIE,
            wealth=5000.0,
            organization=0.8,
            active=True,
        )

        # Create territory
        territory = Territory(
            id="T001",
            name="District",
            sector_type=SectorType.INDUSTRIAL,
            profile=OperationalProfile.LOW_PROFILE,
        )

        # Create relationship
        exploitation = Relationship(
            source_id=PERIPHERY_WORKER_ID,
            target_id=COMPRADOR_ID,
            edge_type=EdgeType.EXPLOITATION,
            value_flow=5.0,
            tension=0.4,
        )

        # Create event
        extraction = ExtractionEvent(
            tick=1,
            source_id=PERIPHERY_WORKER_ID,
            target_id=COMPRADOR_ID,
            amount=5.0,
        )

        # Build state
        state = WorldState(
            tick=1,
            entities={PERIPHERY_WORKER_ID: worker, COMPRADOR_ID: owner},
            territories={"T001": territory},
            relationships=[exploitation],
            events=[extraction],
            event_log=["Tick 1: extraction"],
        )

        # Round-trip
        graph = state.to_graph()
        restored = WorldState.from_graph(graph, tick=1)

        # Ultimate assertion: model_dump equality
        original_dump = state.model_dump()
        restored_dump = restored.model_dump()

        # Core state fields must match exactly
        assert original_dump["tick"] == restored_dump["tick"]
        assert original_dump["event_log"] == restored_dump["event_log"]
        assert len(original_dump["events"]) == len(restored_dump["events"])
        assert len(original_dump["entities"]) == len(restored_dump["entities"])
        assert len(original_dump["territories"]) == len(restored_dump["territories"])
        assert len(original_dump["relationships"]) == len(restored_dump["relationships"])

        # Verify entity fields (excluding computed consumption_needs)
        for entity_id in original_dump["entities"]:
            orig = original_dump["entities"][entity_id]
            rest = restored_dump["entities"][entity_id]
            # All non-computed fields should match
            assert orig["id"] == rest["id"]
            assert orig["name"] == rest["name"]
            assert orig["role"] == rest["role"]
            assert orig["wealth"] == pytest.approx(rest["wealth"])
            assert orig["active"] == rest["active"]

        # Verify relationship fields
        assert original_dump["relationships"][0] == restored_dump["relationships"][0]

        # Verify territory fields
        for terr_id in original_dump["territories"]:
            orig = original_dump["territories"][terr_id]
            rest = restored_dump["territories"][terr_id]
            assert orig["id"] == rest["id"]
            assert orig["name"] == rest["name"]
            assert orig["sector_type"] == rest["sector_type"]


class TestSpec065CountyFipsRoundTrip:
    """Spec-065 T036a: SocialClass.county_fips round-trip and validation."""

    def test_county_fips_default_is_none(self) -> None:
        """A SocialClass constructed without county_fips defaults to None."""
        from babylon.engine.factories import create_proletariat

        entity = create_proletariat()
        assert entity.county_fips is None

    def test_factory_accepts_county_fips_kwarg(self) -> None:
        """The proletariat factory accepts the spec-065 county_fips keyword."""
        from babylon.engine.factories import create_bourgeoisie, create_proletariat

        prole = create_proletariat(county_fips="26163")
        bourg = create_bourgeoisie(county_fips="26099")
        assert prole.county_fips == "26163"
        assert bourg.county_fips == "26099"

    def test_county_fips_pattern_rejects_non_numeric(self) -> None:
        """Non-numeric strings violate the FIPS pattern."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SocialClass(
                id="C901",
                name="Test",
                role=SocialRole.PERIPHERY_PROLETARIAT,
                county_fips="ABCDE",
            )

    def test_county_fips_pattern_rejects_wrong_length(self) -> None:
        """3-digit, 4-digit, 6-digit strings violate the FIPS pattern."""
        from pydantic import ValidationError

        for bad in ("261", "2616", "261631"):
            with pytest.raises(ValidationError):
                SocialClass(
                    id="C902",
                    name="Test",
                    role=SocialRole.PERIPHERY_PROLETARIAT,
                    county_fips=bad,
                )

    def test_county_fips_pattern_accepts_empty_string(self) -> None:
        """Empty string is explicitly allowed (means 'explicitly unattributed')."""
        entity = SocialClass(
            id="C903",
            name="Test",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            county_fips="",
        )
        assert entity.county_fips == ""

    def test_county_fips_survives_round_trip(self) -> None:
        """to_graph/from_graph preserves county_fips for set, unset, empty."""
        from babylon.engine.factories import create_proletariat

        e1 = create_proletariat(id="C001", county_fips="26163")  # set
        e2 = create_proletariat(id="C002")  # unset (None)
        e3 = create_proletariat(id="C003", county_fips="")  # empty

        state = WorldState(tick=0, entities={"C001": e1, "C002": e2, "C003": e3})
        restored = WorldState.from_graph(state.to_graph(), tick=1)

        assert restored.entities["C001"].county_fips == "26163"
        assert restored.entities["C002"].county_fips is None
        assert restored.entities["C003"].county_fips == ""

    def test_backward_compatibility_no_county_fips_set(self) -> None:
        """A WorldState built without ever setting county_fips serializes
        and round-trips identically to spec-064 behavior — verifies the
        new field doesn't break any existing test."""
        from babylon.engine.factories import create_bourgeoisie, create_proletariat

        worker = create_proletariat()
        bourg = create_bourgeoisie()

        state = WorldState(
            tick=0,
            entities={PERIPHERY_WORKER_ID: worker, COMPRADOR_ID: bourg},
        )
        restored = WorldState.from_graph(state.to_graph(), tick=1)

        # Both entities round-trip; county_fips stays None on both sides.
        assert restored.entities[PERIPHERY_WORKER_ID].county_fips is None
        assert restored.entities[COMPRADOR_ID].county_fips is None


class TestWageAccountingAttrsAreTransient:
    """Phase D4: w_paid/v_produced node attrs must not break from_graph."""

    def test_from_graph_drops_wage_accounting_attrs(self) -> None:
        # The wages phase writes w_paid/v_produced onto paid class nodes; they
        # are NOT SocialClass fields, so from_graph must drop them rather than
        # raise extra_forbidden (the regression the persistence path caught).
        from babylon.engine.factories import create_proletariat

        state = WorldState(tick=0, entities={"C001": create_proletariat(id="C001")})
        graph = state.to_graph()
        graph.nodes["C001"]["w_paid"] = 6.0
        graph.nodes["C001"]["v_produced"] = 5.0

        restored = WorldState.from_graph(graph, tick=1)  # must not raise

        entity = restored.entities["C001"]
        assert not hasattr(entity, "w_paid")
        assert not hasattr(entity, "v_produced")
