"""Tests for WorldState graph round-trip serialization.

Sprint 1.X Deliverable 2: High-Fidelity State.
Pain Point #7: WorldState.to_graph() -> WorldState.from_graph() is lossy.

These tests verify that ALL WorldState fields survive the round-trip
through NetworkX graph serialization and deserialization.
"""

from __future__ import annotations

import pytest

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
from babylon.models.events import (
    EVENT_CLASS_MAP,
    ExtractionEvent,
    SimulationEvent,
    UprisingEvent,
)
from babylon.models.world_state import WorldState
from babylon.topology.graph import BabylonGraph

# EventType members with no TickEvent leaf class (no ``kind`` literal in the
# discriminated union). Sorted for deterministic parametrize ids.
NON_UNION_TYPES = sorted(set(EventType) - set(EVENT_CLASS_MAP), key=str)


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


class TestNonUnionEventRoundTrip:
    """Design B: EventType members outside the 19-leaf TickEvent union must
    replay as bare SimulationEvent instead of crashing (union_tag_invalid)."""

    def test_non_union_type_count_pin(self) -> None:
        """Sanity-pin: exactly 19 EventType values are union-dispatchable."""
        assert len(NON_UNION_TYPES) == len(EventType) - 19

    @pytest.mark.parametrize("event_type", NON_UNION_TYPES, ids=str)
    def test_non_union_event_types_survive_round_trip(self, event_type: EventType) -> None:
        state = WorldState(tick=0, events=[SimulationEvent(event_type=event_type, tick=0)])

        restored = WorldState.from_graph(state.to_graph(), tick=0)

        assert len(restored.events) == 1
        assert restored.events[0].event_type is event_type


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


class TestEdgeCollisionPreScan:
    """Design B: to_graph must fail loud on same-pair edge_type collisions.

    BabylonGraph stores ONE edge per (source, target) pair (rustworkx core
    is multigraph=False; add_edge merges payloads), so two Relationships on
    the same pair with different edge_types would silently collapse
    last-writer-wins during the round-trip.
    """

    @staticmethod
    def _state_with_two_entities() -> WorldState:
        from babylon.engine.factories import create_bourgeoisie, create_proletariat

        return WorldState(
            tick=0,
            entities={
                "C000": create_proletariat(id="C000"),
                "C001": create_bourgeoisie(id="C001"),
            },
        )

    def test_to_graph_raises_on_same_pair_edge_type_collision(self) -> None:
        state = self._state_with_two_entities()
        state = state.model_copy(
            update={
                "relationships": [
                    Relationship(
                        source_id="C000", target_id="C001", edge_type=EdgeType.EXPLOITATION
                    ),
                    Relationship(source_id="C000", target_id="C001", edge_type=EdgeType.SOLIDARITY),
                ]
            }
        )

        with pytest.raises(ValueError, match="edge collision"):
            state.to_graph()

    def test_same_pair_same_type_duplicates_still_merge(self) -> None:
        """Residual contract (documented, unchanged): same-pair SAME-type
        duplicates merge silently — the pre-scan only rejects differing
        edge_types."""
        state = self._state_with_two_entities()
        state = state.model_copy(
            update={
                "relationships": [
                    Relationship(
                        source_id="C000",
                        target_id="C001",
                        edge_type=EdgeType.EXPLOITATION,
                        value_flow=1.0,
                    ),
                    Relationship(
                        source_id="C000",
                        target_id="C001",
                        edge_type=EdgeType.EXPLOITATION,
                        value_flow=2.0,
                    ),
                ]
            }
        )

        graph = state.to_graph()  # must not raise

        restored = WorldState.from_graph(graph, tick=0)
        assert len(restored.relationships) == 1


class TestInstitutionRelationsRoundTrip:
    """Feature 040: institution_relations must survive to_graph/from_graph."""

    def test_institution_relations_survive_round_trip(self) -> None:
        """Relations are richer than the HOUSES edges to_graph derives from
        housed_org_ids — they must round-trip via graph metadata (today:
        restored.institution_relations silently resets to [])."""
        from babylon.models.entities.institution import InstitutionOrgRelation

        relation = InstitutionOrgRelation(
            institution_id="INST_001",
            organization_id="ORG_001",
            resource_provision=0.4,
            legal_cover=True,
            legitimacy_transfer=0.6,
        )
        state = WorldState(tick=0, institution_relations=[relation])

        graph = state.to_graph()
        restored = WorldState.from_graph(graph, tick=0)

        assert len(restored.institution_relations) == 1
        assert restored.institution_relations[0].model_dump() == relation.model_dump()


class TestSovereignRoundTrip:
    """Spec-070: Sovereign nodes must survive to_graph/from_graph."""

    def test_sovereign_survives_round_trip(self) -> None:
        """A WorldState-carried Sovereign round-trips losslessly."""
        from babylon.models.entities.sovereign import Sovereign
        from babylon.models.enums import ExtractionPolicy, SovereigntyType

        sovereign = Sovereign(
            id="SOV_TEST",
            name="Test Sovereign",
            sovereignty_type=SovereigntyType.RECOGNIZED_STATE,
            legitimacy=0.8,
            color_hex="#112233",
            ruling_faction_id=None,
            extraction_policy=ExtractionPolicy.CONTINUE,
            founded_tick=0,
        )
        state = WorldState(tick=0, sovereigns={"SOV_TEST": sovereign})

        graph = state.to_graph()
        assert graph.nodes["SOV_TEST"]["_node_type"] == "sovereign"

        restored = WorldState.from_graph(graph, tick=0)
        assert restored.sovereigns["SOV_TEST"].model_dump() == sovereign.model_dump()

    def test_sovereign_node_without_id_attr_reconstructs(self) -> None:
        """A node written the way CollapseTransitionSystem historically wrote
        it (no ``id`` attr) reconstructs with ``id == node_id`` instead of
        crashing (today: ValidationError from SocialClass extra="forbid")."""
        graph = BabylonGraph()
        graph.add_node(
            "SOV_TEST",
            _node_type="sovereign",
            name="Successor of SOV_USA_FED",
            sovereignty_type="provisional",
            legitimacy=0.5,
            color_hex="#7f7f7f",
            ruling_faction_id=None,
            extraction_policy="continue",
            founded_tick=0,
        )

        restored = WorldState.from_graph(graph, tick=0)

        assert restored.sovereigns["SOV_TEST"].id == "SOV_TEST"
        assert restored.sovereigns["SOV_TEST"].name == "Successor of SOV_USA_FED"


class TestSocialClassDefensiveReconstruction:
    """Design B: from_graph fail-soft on writer-incomplete social_class nodes."""

    def test_missing_id_and_name_reconstruct_with_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A social_class node whose writer omitted ``id`` and ``name``
        reconstructs (id from node id, name fallback) and logs a WARNING
        naming the node — fail-soft + loud instead of ValidationError."""
        graph = BabylonGraph()
        graph.add_node(
            "C042",
            _node_type="social_class",
            role=SocialRole.INTERNAL_PROLETARIAT.value,
            active=False,
            population=0,
            wealth=0.0,
        )

        with caplog.at_level("WARNING", logger="babylon.models.world_state"):
            restored = WorldState.from_graph(graph, tick=1)  # must not raise

        entity = restored.entities["C042"]
        assert entity.id == "C042"
        assert entity.name == "C042"  # loud fallback, not silence
        assert any(
            "C042" in record.message and "name" in record.message
            for record in caplog.records
            if record.levelname == "WARNING"
        ), "missing-name reconstruction must log a WARNING naming the node"


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

    def test_from_graph_drops_threat_score_attr(self) -> None:
        # CommunitySystem._compute_threat_scores writes threat_score onto
        # social_class nodes (community.py); it is NOT a SocialClass field,
        # so from_graph must drop it rather than raise extra_forbidden.
        from babylon.engine.factories import create_proletariat

        state = WorldState(tick=0, entities={"C001": create_proletariat(id="C001")})
        graph = state.to_graph()
        graph.nodes["C001"]["threat_score"] = 0.7

        restored = WorldState.from_graph(graph, tick=1)  # must not raise

        assert not hasattr(restored.entities["C001"], "threat_score")

    def test_from_graph_drops_shadow_partition_attrs(self) -> None:
        # Program 19 Phase 1 (ADR070): ContradictionSystem writes the shadow
        # partition attrs onto social_class nodes each tick; they are derived
        # per-tick observations, NOT SocialClass fields, so from_graph must
        # drop them rather than raise extra_forbidden.
        from babylon.engine.factories import create_proletariat

        state = WorldState(tick=0, entities={"C001": create_proletariat(id="C001")})
        graph = state.to_graph()
        graph.nodes["C001"]["sigma_capital_labor"] = -0.5
        graph.nodes["C001"]["sigma_wage"] = -0.8
        graph.nodes["C001"]["derived_class_cell"] = "labor:exploited"

        restored = WorldState.from_graph(graph, tick=1)  # must not raise

        entity = restored.entities["C001"]
        assert not hasattr(entity, "sigma_capital_labor")
        assert not hasattr(entity, "sigma_wage")
        assert not hasattr(entity, "derived_class_cell")


class TestTerritoryTransientAttrsAreDropped:
    """Design B: system-written territory attrs must not break from_graph."""

    def test_from_graph_drops_habitability_and_dispossession_intensity(self) -> None:
        # MetabolismSystem writes sovereign-driven habitability
        # (metabolism.py) and DispossessionEventSystem writes
        # dispossession_intensity (dispossession_events.py) onto territory
        # nodes; neither is a Territory model field (extra="forbid"), so
        # from_graph must drop them rather than raise.
        territory = Territory(
            id="T001",
            name="District",
            sector_type=SectorType.INDUSTRIAL,
            profile=OperationalProfile.LOW_PROFILE,
        )
        state = WorldState(tick=0, territories={"T001": territory})
        graph = state.to_graph()
        graph.nodes["T001"]["habitability"] = 0.4
        graph.nodes["T001"]["dispossession_intensity"] = 0.2

        restored = WorldState.from_graph(graph, tick=1)  # must not raise

        restored_territory = restored.territories["T001"]
        assert not hasattr(restored_territory, "habitability")
        assert not hasattr(restored_territory, "dispossession_intensity")

    def test_from_graph_drops_epistemic_horizon_shadow_attrs(self) -> None:
        # EpistemicHorizonSystem (Epistemic Horizon Phase 1 shadow) writes
        # mass_receptivity/intel_confidence/vision_state onto territory
        # nodes; none is a Territory model field (extra="forbid"), so
        # from_graph must drop them rather than raise.
        territory = Territory(
            id="T001",
            name="District",
            sector_type=SectorType.INDUSTRIAL,
            profile=OperationalProfile.LOW_PROFILE,
        )
        state = WorldState(tick=0, territories={"T001": territory})
        graph = state.to_graph()
        graph.nodes["T001"]["mass_receptivity"] = 0.56
        graph.nodes["T001"]["intel_confidence"] = 0.66
        graph.nodes["T001"]["vision_state"] = "mud"

        restored = WorldState.from_graph(graph, tick=1)  # must not raise

        restored_territory = restored.territories["T001"]
        assert not hasattr(restored_territory, "mass_receptivity")
        assert not hasattr(restored_territory, "intel_confidence")
        assert not hasattr(restored_territory, "vision_state")


class TestFactionRoundTrip:
    """Spec-109 A6: BalkanizationFaction nodes + INFLUENCES/CLAIMS edge
    payloads must survive to_graph/from_graph (closes the faction half of
    owner-queue item 12 — previously a faction node reconstructed as a
    strict SocialClass and crashed)."""

    def _faction(self) -> object:
        from babylon.data.game.balkanization import load_seed_factions

        return load_seed_factions()[0]

    def test_faction_survives_round_trip(self) -> None:
        """A WorldState-carried faction round-trips losslessly."""
        faction = self._faction()
        state = WorldState(tick=0, factions={faction.id: faction})

        graph = state.to_graph()
        assert graph.nodes[faction.id]["_node_type"] == "faction"

        restored = WorldState.from_graph(graph, tick=0)
        assert restored.factions[faction.id].model_dump() == faction.model_dump()

    def test_influences_edge_payload_survives_round_trip(self) -> None:
        """influence_level/support_type survive a full state round-trip and
        remain queryable via BabylonGraph.query_faction_influence_by_territory."""
        faction = self._faction()
        territory = Territory(
            id="T001",
            name="Test Territory",
            sector_type=SectorType.INDUSTRIAL,
            profile=OperationalProfile.LOW_PROFILE,
        )
        rel = Relationship(
            source_id=faction.id,
            target_id="T001",
            edge_type=EdgeType.INFLUENCES,
            influence_level=0.42,
            support_type="labor",
        )
        state = WorldState(
            tick=0,
            factions={faction.id: faction},
            territories={"T001": territory},
            relationships=[rel],
        )

        graph = state.to_graph()
        rows = graph.query_faction_influence_by_territory("T001")
        assert rows == [(faction.id, 0.42, "labor")]

        restored = WorldState.from_graph(graph, tick=0)
        restored_rel = next(r for r in restored.relationships if r.edge_type == EdgeType.INFLUENCES)
        assert restored_rel.influence_level == 0.42
        assert restored_rel.support_type == "labor"

        # And the payload survives a SECOND projection (state -> graph ->
        # state -> graph), which is what every engine step does.
        rows2 = restored.to_graph().query_faction_influence_by_territory("T001")
        assert rows2 == [(faction.id, 0.42, "labor")]

    def test_plain_edges_gain_no_balkanization_keys(self) -> None:
        """Byte-identity guard: a non-balkanization edge's graph payload must
        NOT grow influence/claims keys (they are exclude_none'd away)."""
        worker = SocialClass(
            id="C001", name="Workers", role=SocialRole.PERIPHERY_PROLETARIAT, population=100
        )
        owner = SocialClass(
            id="C002", name="Owners", role=SocialRole.CORE_BOURGEOISIE, population=10
        )
        rel = Relationship(source_id="C001", target_id="C002", edge_type=EdgeType.EXPLOITATION)
        state = WorldState(tick=0, entities={"C001": worker, "C002": owner}, relationships=[rel])

        payload = state.to_graph().edges[("C001", "C002")]
        for key in ("influence_level", "support_type", "control_level", "legal_status"):
            assert key not in payload


class TestFieldStackRoundTrip:
    """Program 19/20 Wave 3 Round 1: the field_stack facade carry.

    ``field_stack``/``principal_field``/``dialectical_regime`` are graph
    attrs FieldDerivativeSystem @20 / ContradictionSystem @18 write.
    WorldState carries them across ``to_graph()``/``from_graph()`` (a
    graph-attr idiom like ``opposition_states``, but actually round-tripped
    — unlike ``opposition_states``, which is write-only by design) and
    re-stamps the per-node/edge attrs the snapshot was built from, so a
    persisted-then-reloaded graph matches what the live engine graph
    carried.
    """

    def _two_class_state_with_field_stack(self) -> WorldState:
        c001 = SocialClass(
            id="C001", name="Workers", role=SocialRole.PERIPHERY_PROLETARIAT, population=100
        )
        c002 = SocialClass(
            id="C002", name="Owners", role=SocialRole.CORE_BOURGEOISIE, population=10
        )
        rel = Relationship(source_id="C001", target_id="C002", edge_type=EdgeType.EXPLOITATION)
        field_stack = {
            "nodes": {
                "C001": {
                    "fields": {"atomization": 0.2, "exploitation": 0.8},
                    "field_derivatives": {
                        "exploitation": {"laplacian": 0.1, "df_dt": 0.02, "d2f_dt2": None},
                    },
                },
                "C002": {"fields": {"atomization": 0.2, "exploitation": 0.6}},
            },
            "edges": [
                {"source": "C001", "target": "C002", "field": "atomization", "gradient": 0.0},
                {"source": "C001", "target": "C002", "field": "exploitation", "gradient": -0.2},
            ],
        }
        principal_field = {"field_name": "exploitation", "max_abs_df_dt": 0.05, "changed": True}
        dialectical_regime = {"regime": "crisis", "opposition": "capital_labor", "rate": 0.12}
        return WorldState(
            tick=9,
            entities={"C001": c001, "C002": c002},
            relationships=[rel],
            field_stack=field_stack,
            principal_field=principal_field,
            dialectical_regime=dialectical_regime,
        )

    def test_graph_attrs_survive_round_trip_byte_equal(self) -> None:
        state = self._two_class_state_with_field_stack()

        graph = state.to_graph()
        restored = WorldState.from_graph(graph, tick=9)

        assert restored.field_stack == state.field_stack
        assert restored.principal_field == state.principal_field
        assert restored.dialectical_regime == state.dialectical_regime

    def test_to_graph_restamps_node_attrs_from_field_stack(self) -> None:
        state = self._two_class_state_with_field_stack()

        graph = state.to_graph()

        assert graph.nodes["C001"]["contradiction_fields"] == {
            "atomization": 0.2,
            "exploitation": 0.8,
        }
        assert graph.nodes["C001"]["field_derivatives"] == {
            "exploitation": {"laplacian": 0.1, "df_dt": 0.02, "d2f_dt2": None},
        }
        assert graph.nodes["C002"]["contradiction_fields"] == {
            "atomization": 0.2,
            "exploitation": 0.6,
        }
        assert "field_derivatives" not in graph.nodes["C002"]

    def test_to_graph_restamps_edge_attrs_from_field_stack(self) -> None:
        state = self._two_class_state_with_field_stack()

        graph = state.to_graph()

        gradients = graph.edges["C001", "C002"]["field_gradients"]
        assert gradients == {"atomization": 0.0, "exploitation": -0.2}

    def test_restamp_skips_missing_node_without_error(self) -> None:
        """A snapshot row naming a node no longer in entities (a
        deactivated class) must not raise — the snapshot is stale, not an
        error (Design B fail-soft)."""
        base = self._two_class_state_with_field_stack()
        state = base.model_copy(
            update={
                "entities": {
                    "C001": SocialClass(
                        id="C001",
                        name="Workers",
                        role=SocialRole.PERIPHERY_PROLETARIAT,
                        population=100,
                    )
                },
                "relationships": [],
            }
        )

        graph = state.to_graph()  # must not raise

        assert "C002" not in graph.nodes

    def test_restamp_skips_missing_edge_without_error(self) -> None:
        """A snapshot row naming an edge no longer in relationships must
        not raise."""
        base = self._two_class_state_with_field_stack()
        state = base.model_copy(update={"relationships": []})

        graph = state.to_graph()  # must not raise

        assert not graph.has_edge("C001", "C002")

    def test_absent_field_stack_stamps_no_attrs_no_error(self) -> None:
        """A default WorldState (empty field_stack/principal_field/
        dialectical_regime) writes no graph attrs and stamps nothing — the
        round trip is a pure no-op for these three fields."""
        worker = SocialClass(
            id="C001", name="Workers", role=SocialRole.PERIPHERY_PROLETARIAT, population=100
        )
        state = WorldState(tick=0, entities={"C001": worker})

        graph = state.to_graph()

        assert "field_stack" not in graph.graph
        assert "principal_field" not in graph.graph
        assert "dialectical_regime" not in graph.graph
        assert "contradiction_fields" not in graph.nodes["C001"]

        restored = WorldState.from_graph(graph, tick=0)
        assert restored.field_stack == {}
        assert restored.principal_field == {}
        assert restored.dialectical_regime == {}

    def test_field_stack_round_trip_is_idempotent(self) -> None:
        """to_graph(from_graph(g)) attrs == g attrs for the field-stack
        carry — the round trip stabilizes rather than drifting."""
        state = self._two_class_state_with_field_stack()
        graph1 = state.to_graph()

        restored = WorldState.from_graph(graph1, tick=9)
        graph2 = restored.to_graph()

        assert graph2.graph["field_stack"] == graph1.graph["field_stack"]
        assert graph2.graph["principal_field"] == graph1.graph["principal_field"]
        assert graph2.graph["dialectical_regime"] == graph1.graph["dialectical_regime"]
        assert (
            graph2.nodes["C001"]["contradiction_fields"]
            == graph1.nodes["C001"]["contradiction_fields"]
        )
        assert (
            graph2.nodes["C001"]["field_derivatives"] == graph1.nodes["C001"]["field_derivatives"]
        )
        assert (
            graph2.edges["C001", "C002"]["field_gradients"]
            == graph1.edges["C001", "C002"]["field_gradients"]
        )
