"""Tests for _convert_bus_event_to_pydantic() function.

Sprint 3.1+: Event conversion from EventBus Events to typed Pydantic models.

Tests verify:
- Each EventType is correctly converted to its corresponding Pydantic class
- Payload fields are correctly extracted
- Unsupported event types return None (graceful degradation)
- String event types are normalized to EventType enum
"""

from datetime import datetime

from babylon.engine.simulation_engine import _convert_bus_event_to_pydantic
from babylon.kernel.event_bus import Event
from babylon.models.entity_registry import (
    COMPRADOR_ID,
    CORE_BOURGEOISIE_ID,
    LABOR_ARISTOCRACY_ID,
    PERIPHERY_WORKER_ID,
)
from babylon.models.enums import EventType
from babylon.models.events import (
    CrisisEvent,
    ExtractionEvent,
    MassAwakeningEvent,
    RuptureEvent,
    SolidaritySpikeEvent,
    SparkEvent,
    SubsidyEvent,
    TransmissionEvent,
    UprisingEvent,
)
from babylon.models.events.balkanization_payloads import (
    CivilWarDeclaredPayload,
    DualPowerActivePayload,
    FactionVictoryPayload,
    RedSettlerTrapDetectedPayload,
    SovereignCollapsePayload,
    TerritoryTransitionPayload,
)
from babylon.models.events.field_payloads import PrincipalContradictionShiftEvent
from babylon.models.events.institution_payloads import (
    InstitutionBonapartistModeEvent,
    InstitutionFactionShiftEvent,
)
from babylon.models.events.lifecycle_payloads import (
    InheritanceTransferEvent,
    LegitimationCrisisEvent,
    LegitimationRecoveryEvent,
    LifecycleTransitionEvent,
)
from babylon.models.events.ooda_payloads import (
    OrganizationalActionEvent,
    StateRepressionEvent,
    StateSurveillanceEvent,
)
from babylon.models.events.reactionary_payloads import (
    FascistDriftEvent,
    FascistRecruitmentEvent,
    OrganizationalFractureEvent,
    RedBrownCoupEvent,
)


class TestExtractionEventConversion:
    """Tests for SURPLUS_EXTRACTION event conversion."""

    def test_converts_surplus_extraction_event(self) -> None:
        """SURPLUS_EXTRACTION events convert to ExtractionEvent."""
        bus_event = Event(
            type=EventType.SURPLUS_EXTRACTION,
            tick=5,
            payload={
                "source_id": PERIPHERY_WORKER_ID,
                "target_id": COMPRADOR_ID,
                "amount": 15.5,
                "mechanism": "imperial_rent",
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, ExtractionEvent)
        assert result.event_type == EventType.SURPLUS_EXTRACTION
        assert result.tick == 5
        assert result.source_id == PERIPHERY_WORKER_ID
        assert result.target_id == COMPRADOR_ID
        assert result.amount == 15.5
        assert result.mechanism == "imperial_rent"

    def test_extraction_with_string_event_type(self) -> None:
        """String event types are normalized to EventType enum."""
        bus_event = Event(
            type="surplus_extraction",  # type: ignore[arg-type]
            tick=3,
            payload={
                "source_id": PERIPHERY_WORKER_ID,
                "target_id": COMPRADOR_ID,
                "amount": 10.0,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, ExtractionEvent)
        assert result.event_type == EventType.SURPLUS_EXTRACTION


class TestSubsidyEventConversion:
    """Tests for IMPERIAL_SUBSIDY event conversion."""

    def test_converts_imperial_subsidy_event(self) -> None:
        """IMPERIAL_SUBSIDY events convert to SubsidyEvent."""
        bus_event = Event(
            type=EventType.IMPERIAL_SUBSIDY,
            tick=7,
            payload={
                "source_id": COMPRADOR_ID,
                "target_id": CORE_BOURGEOISIE_ID,
                "amount": 100.0,
                "repression_boost": 0.25,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, SubsidyEvent)
        assert result.event_type == EventType.IMPERIAL_SUBSIDY
        assert result.tick == 7
        assert result.source_id == COMPRADOR_ID
        assert result.target_id == CORE_BOURGEOISIE_ID
        assert result.amount == 100.0
        assert result.repression_boost == 0.25


class TestCrisisEventConversion:
    """Tests for ECONOMIC_CRISIS event conversion."""

    def test_converts_economic_crisis_event(self) -> None:
        """ECONOMIC_CRISIS events convert to CrisisEvent."""
        bus_event = Event(
            type=EventType.ECONOMIC_CRISIS,
            tick=10,
            payload={
                "pool_ratio": 0.15,
                "aggregate_tension": 0.7,
                "decision": "CRISIS",
                "wage_delta": -0.05,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, CrisisEvent)
        assert result.event_type == EventType.ECONOMIC_CRISIS
        assert result.tick == 10
        assert result.pool_ratio == 0.15
        assert result.aggregate_tension == 0.7
        assert result.decision == "CRISIS"
        assert result.wage_delta == -0.05


class TestTransmissionEventConversion:
    """Tests for CONSCIOUSNESS_TRANSMISSION event conversion."""

    def test_converts_consciousness_transmission_event(self) -> None:
        """CONSCIOUSNESS_TRANSMISSION events convert to TransmissionEvent."""
        bus_event = Event(
            type=EventType.CONSCIOUSNESS_TRANSMISSION,
            tick=3,
            payload={
                "source_id": COMPRADOR_ID,
                "target_id": PERIPHERY_WORKER_ID,
                "delta": 0.05,
                "solidarity_strength": 0.8,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, TransmissionEvent)
        assert result.event_type == EventType.CONSCIOUSNESS_TRANSMISSION
        assert result.tick == 3
        assert result.source_id == COMPRADOR_ID
        assert result.target_id == PERIPHERY_WORKER_ID
        assert result.delta == 0.05
        assert result.solidarity_strength == 0.8


class TestMassAwakeningEventConversion:
    """Tests for MASS_AWAKENING event conversion."""

    def test_converts_mass_awakening_event(self) -> None:
        """MASS_AWAKENING events convert to MassAwakeningEvent."""
        bus_event = Event(
            type=EventType.MASS_AWAKENING,
            tick=7,
            payload={
                "target_id": PERIPHERY_WORKER_ID,
                "old_consciousness": 0.4,
                "new_consciousness": 0.7,
                "triggering_source": COMPRADOR_ID,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, MassAwakeningEvent)
        assert result.event_type == EventType.MASS_AWAKENING
        assert result.tick == 7
        assert result.target_id == PERIPHERY_WORKER_ID
        assert result.old_consciousness == 0.4
        assert result.new_consciousness == 0.7
        assert result.triggering_source == COMPRADOR_ID


class TestSparkEventConversion:
    """Tests for EXCESSIVE_FORCE event conversion."""

    def test_converts_excessive_force_event(self) -> None:
        """EXCESSIVE_FORCE events convert to SparkEvent."""
        bus_event = Event(
            type=EventType.EXCESSIVE_FORCE,
            tick=5,
            payload={
                "node_id": PERIPHERY_WORKER_ID,
                "repression": 0.8,
                "spark_probability": 0.4,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, SparkEvent)
        assert result.event_type == EventType.EXCESSIVE_FORCE
        assert result.tick == 5
        assert result.node_id == PERIPHERY_WORKER_ID
        assert result.repression == 0.8
        assert result.spark_probability == 0.4


class TestUprisingEventConversion:
    """Tests for UPRISING event conversion."""

    def test_converts_uprising_event(self) -> None:
        """UPRISING events convert to UprisingEvent."""
        bus_event = Event(
            type=EventType.UPRISING,
            tick=8,
            payload={
                "node_id": PERIPHERY_WORKER_ID,
                "trigger": "spark",
                "agitation": 0.9,
                "repression": 0.7,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, UprisingEvent)
        assert result.event_type == EventType.UPRISING
        assert result.tick == 8
        assert result.node_id == PERIPHERY_WORKER_ID
        assert result.trigger == "spark"
        assert result.agitation == 0.9
        assert result.repression == 0.7


class TestSolidaritySpikeEventConversion:
    """Tests for SOLIDARITY_SPIKE event conversion."""

    def test_converts_solidarity_spike_event(self) -> None:
        """SOLIDARITY_SPIKE events convert to SolidaritySpikeEvent."""
        bus_event = Event(
            type=EventType.SOLIDARITY_SPIKE,
            tick=6,
            payload={
                "node_id": PERIPHERY_WORKER_ID,
                "solidarity_gained": 0.3,
                "edges_affected": 2,
                "triggered_by": "uprising",
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, SolidaritySpikeEvent)
        assert result.event_type == EventType.SOLIDARITY_SPIKE
        assert result.tick == 6
        assert result.node_id == PERIPHERY_WORKER_ID
        assert result.solidarity_gained == 0.3
        assert result.edges_affected == 2
        assert result.triggered_by == "uprising"


class TestRuptureEventConversion:
    """Tests for RUPTURE event conversion."""

    def test_converts_rupture_event(self) -> None:
        """RUPTURE events convert to RuptureEvent."""
        edge_repr = f"{PERIPHERY_WORKER_ID}->{COMPRADOR_ID}"
        bus_event = Event(
            type=EventType.RUPTURE,
            tick=12,
            payload={
                "edge": edge_repr,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, RuptureEvent)
        assert result.event_type == EventType.RUPTURE
        assert result.tick == 12
        assert result.edge == edge_repr


class TestSovereignCollapseConversion:
    """Tests for SOVEREIGN_COLLAPSE event conversion."""

    def test_converts_sovereign_collapse_event(self) -> None:
        """SOVEREIGN_COLLAPSE events convert to SovereignCollapsePayload."""
        bus_event = Event(
            type=EventType.SOVEREIGN_COLLAPSE,
            tick=15,
            payload={
                "sovereign_id": "SOV_TEST",
                "trigger": "legitimacy_zero",
                "claimed_territories_count": 3,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, SovereignCollapsePayload)
        assert result.event_type == EventType.SOVEREIGN_COLLAPSE
        assert result.tick == 15
        assert result.sovereign_id == "SOV_TEST"
        assert result.trigger == "legitimacy_zero"
        assert result.claimed_territories_count == 3


class TestTerritoryTransitionConversion:
    """Tests for TERRITORY_TRANSITION event conversion."""

    def test_converts_territory_transition_event(self) -> None:
        """TERRITORY_TRANSITION events convert to TerritoryTransitionPayload."""
        bus_event = Event(
            type=EventType.TERRITORY_TRANSITION,
            tick=16,
            payload={
                "territory_id": "T001",
                "from_sovereign_id": "SOV_TEST",
                "to_sovereign_id": "SOV_OTHER",
                "from_winning_faction_id": "FAC_TEST",
                "to_winning_faction_id": "FAC_OTHER",
                "reason": "influence_flip",
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, TerritoryTransitionPayload)
        assert result.event_type == EventType.TERRITORY_TRANSITION
        assert result.tick == 16
        assert result.territory_id == "T001"
        assert result.from_sovereign_id == "SOV_TEST"
        assert result.to_sovereign_id == "SOV_OTHER"
        assert result.from_winning_faction_id == "FAC_TEST"
        assert result.to_winning_faction_id == "FAC_OTHER"
        assert result.reason == "influence_flip"


class TestFactionVictoryConversion:
    """Tests for FACTION_VICTORY event conversion."""

    def test_converts_faction_victory_event(self) -> None:
        """FACTION_VICTORY events convert to FactionVictoryPayload."""
        bus_event = Event(
            type=EventType.FACTION_VICTORY,
            tick=17,
            payload={
                "faction_id": "FAC_TEST",
                "aggregate_influence_share": 0.75,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, FactionVictoryPayload)
        assert result.event_type == EventType.FACTION_VICTORY
        assert result.tick == 17
        assert result.faction_id == "FAC_TEST"
        assert result.aggregate_influence_share == 0.75


class TestCivilWarDeclaredConversion:
    """Tests for CIVIL_WAR_DECLARED event conversion."""

    def test_converts_civil_war_declared_event(self) -> None:
        """CIVIL_WAR_DECLARED events convert to CivilWarDeclaredPayload."""
        bus_event = Event(
            type=EventType.CIVIL_WAR_DECLARED,
            tick=18,
            payload={
                "parent_sovereign_id": "SOV_TEST",
                "secessionist_faction_id": "FAC_TEST",
                "contested_territory_count": 4,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, CivilWarDeclaredPayload)
        assert result.event_type == EventType.CIVIL_WAR_DECLARED
        assert result.tick == 18
        assert result.parent_sovereign_id == "SOV_TEST"
        assert result.secessionist_faction_id == "FAC_TEST"
        assert result.contested_territory_count == 4


class TestRedSettlerTrapDetectedConversion:
    """Tests for RED_SETTLER_TRAP_DETECTED event conversion."""

    def test_converts_red_settler_trap_detected_event(self) -> None:
        """RED_SETTLER_TRAP_DETECTED events convert to RedSettlerTrapDetectedPayload."""
        bus_event = Event(
            type=EventType.RED_SETTLER_TRAP_DETECTED,
            tick=19,
            payload={
                "faction_id": "FAC_TEST",
                "class_reduction": 0.4,
                "colonial_stance": "uphold",
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, RedSettlerTrapDetectedPayload)
        assert result.event_type == EventType.RED_SETTLER_TRAP_DETECTED
        assert result.tick == 19
        assert result.faction_id == "FAC_TEST"
        assert result.class_reduction == 0.4
        assert result.colonial_stance == "uphold"


class TestDualPowerActiveConversion:
    """Tests for DUAL_POWER_ACTIVE event conversion."""

    def test_converts_dual_power_active_event(self) -> None:
        """DUAL_POWER_ACTIVE events convert to DualPowerActivePayload."""
        bus_event = Event(
            type=EventType.DUAL_POWER_ACTIVE,
            tick=20,
            payload={
                "territory_id": "T001",
                "competing_sovereign_ids": ["SOV_TEST", "SOV_OTHER"],
                "control_level_sum": 1.2,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, DualPowerActivePayload)
        assert result.event_type == EventType.DUAL_POWER_ACTIVE
        assert result.tick == 20
        assert result.territory_id == "T001"
        assert result.competing_sovereign_ids == ("SOV_TEST", "SOV_OTHER")
        assert result.control_level_sum == 1.2


class TestFascistDriftEventConversion:
    """Tests for FASCIST_DRIFT event conversion (the mandatory RED-phase test)."""

    def test_converts_fascist_drift_event(self) -> None:
        """FASCIST_DRIFT events convert to FascistDriftEvent."""
        bus_event = Event(
            type=EventType.FASCIST_DRIFT,
            tick=9,
            payload={
                "node_id": PERIPHERY_WORKER_ID,
                "fascist_pull": 0.62,
                "fascist_alignment": 0.3,
                "entitlement": 0.5,
                "solidarity": 0.1,
                "regime": "antagonistic",
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, FascistDriftEvent)
        assert result.event_type == EventType.FASCIST_DRIFT
        assert result.tick == 9
        assert result.node_id == PERIPHERY_WORKER_ID
        assert result.fascist_pull == 0.62
        assert result.fascist_alignment == 0.3
        assert result.entitlement == 0.5
        assert result.solidarity == 0.1
        assert result.regime == "antagonistic"


class TestFascistRecruitmentEventConversion:
    """Tests for FASCIST_RECRUITMENT event conversion."""

    def test_converts_fascist_recruitment_event(self) -> None:
        """FASCIST_RECRUITMENT events convert to FascistRecruitmentEvent."""
        bus_event = Event(
            type=EventType.FASCIST_RECRUITMENT,
            tick=10,
            payload={
                "node_id": PERIPHERY_WORKER_ID,
                "faction_id": "FAC_TEST",
                "fascist_alignment": 0.9,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, FascistRecruitmentEvent)
        assert result.event_type == EventType.FASCIST_RECRUITMENT
        assert result.tick == 10
        assert result.node_id == PERIPHERY_WORKER_ID
        assert result.faction_id == "FAC_TEST"
        assert result.fascist_alignment == 0.9


class TestOrganizationalFractureEventConversion:
    """Tests for ORGANIZATIONAL_FRACTURE event conversion."""

    def test_converts_organizational_fracture_event(self) -> None:
        """ORGANIZATIONAL_FRACTURE events convert to OrganizationalFractureEvent."""
        bus_event = Event(
            type=EventType.ORGANIZATIONAL_FRACTURE,
            tick=11,
            payload={
                "org_id": "ORG_TEST",
                "member_id": LABOR_ARISTOCRACY_ID,
                "chauvinism": 0.6,
                "defection_probability": 0.35,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, OrganizationalFractureEvent)
        assert result.event_type == EventType.ORGANIZATIONAL_FRACTURE
        assert result.tick == 11
        assert result.org_id == "ORG_TEST"
        assert result.member_id == LABOR_ARISTOCRACY_ID
        assert result.chauvinism == 0.6
        assert result.defection_probability == 0.35


class TestRedBrownCoupEventConversion:
    """Tests for RED_BROWN_COUP event conversion."""

    def test_converts_red_brown_coup_event(self) -> None:
        """RED_BROWN_COUP events convert to RedBrownCoupEvent."""
        bus_event = Event(
            type=EventType.RED_BROWN_COUP,
            tick=12,
            payload={
                "org_id": "ORG_TEST",
                "defections": 5,
                "member_count": 8,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, RedBrownCoupEvent)
        assert result.event_type == EventType.RED_BROWN_COUP
        assert result.tick == 12
        assert result.org_id == "ORG_TEST"
        assert result.defections == 5
        assert result.member_count == 8


class TestLifecycleTransitionEventConversion:
    """Tests for LIFECYCLE_TRANSITION event conversion."""

    def test_converts_lifecycle_transition_event(self) -> None:
        """LIFECYCLE_TRANSITION events convert to LifecycleTransitionEvent."""
        bus_event = Event(
            type=EventType.LIFECYCLE_TRANSITION,
            tick=13,
            payload={
                "territory_id": "T001",
                "pop_d": 100.0,
                "pop_p": 250.0,
                "pop_d_prime": 50.0,
                "dependency_ratio": 0.4,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, LifecycleTransitionEvent)
        assert result.event_type == EventType.LIFECYCLE_TRANSITION
        assert result.tick == 13
        assert result.territory_id == "T001"
        assert result.pop_d == 100.0
        assert result.pop_p == 250.0
        assert result.pop_d_prime == 50.0
        assert result.dependency_ratio == 0.4


class TestLegitimationCrisisEventConversion:
    """Tests for LEGITIMATION_CRISIS event conversion."""

    def test_converts_legitimation_crisis_event(self) -> None:
        """LEGITIMATION_CRISIS events convert to LegitimationCrisisEvent."""
        bus_event = Event(
            type=EventType.LEGITIMATION_CRISIS,
            tick=14,
            payload={
                "territory_id": "T001",
                "legitimation_index": 0.15,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, LegitimationCrisisEvent)
        assert result.event_type == EventType.LEGITIMATION_CRISIS
        assert result.tick == 14
        assert result.territory_id == "T001"
        assert result.legitimation_index == 0.15


class TestLegitimationRecoveryEventConversion:
    """Tests for LEGITIMATION_RECOVERY event conversion."""

    def test_converts_legitimation_recovery_event(self) -> None:
        """LEGITIMATION_RECOVERY events convert to LegitimationRecoveryEvent."""
        bus_event = Event(
            type=EventType.LEGITIMATION_RECOVERY,
            tick=21,
            payload={
                "territory_id": "T001",
                "legitimation_index": 0.65,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, LegitimationRecoveryEvent)
        assert result.event_type == EventType.LEGITIMATION_RECOVERY
        assert result.tick == 21
        assert result.territory_id == "T001"
        assert result.legitimation_index == 0.65


class TestInheritanceTransferEventConversion:
    """Tests for INHERITANCE_TRANSFER event conversion."""

    def test_converts_inheritance_transfer_event(self) -> None:
        """INHERITANCE_TRANSFER events convert to InheritanceTransferEvent."""
        bus_event = Event(
            type=EventType.INHERITANCE_TRANSFER,
            tick=22,
            payload={
                "territory_id": "T001",
                "total_transferred": 500.0,
                "care_consumed": 50.0,
                "net_inheritance": 450.0,
                "inheritance_gini": 0.3,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, InheritanceTransferEvent)
        assert result.event_type == EventType.INHERITANCE_TRANSFER
        assert result.tick == 22
        assert result.territory_id == "T001"
        assert result.total_transferred == 500.0
        assert result.care_consumed == 50.0
        assert result.net_inheritance == 450.0
        assert result.inheritance_gini == 0.3


class TestInstitutionFactionShiftEventConversion:
    """Tests for INSTITUTION_FACTION_SHIFT event conversion (dead-until-wired)."""

    def test_converts_institution_faction_shift_event(self) -> None:
        """INSTITUTION_FACTION_SHIFT events convert to InstitutionFactionShiftEvent."""
        bus_event = Event(
            type=EventType.INSTITUTION_FACTION_SHIFT,
            tick=23,
            payload={
                "institution_id": "INST_001",
                "old_fraction": "COMPRADOR",
                "new_fraction": "NATIONAL",
                "weights": {"COMPRADOR": 0.3, "NATIONAL": 0.7},
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, InstitutionFactionShiftEvent)
        assert result.event_type == EventType.INSTITUTION_FACTION_SHIFT
        assert result.tick == 23
        assert result.institution_id == "INST_001"
        assert result.old_fraction == "COMPRADOR"
        assert result.new_fraction == "NATIONAL"
        assert result.weights == {"COMPRADOR": 0.3, "NATIONAL": 0.7}


class TestInstitutionBonapartistModeEventConversion:
    """Tests for INSTITUTION_BONAPARTIST_MODE event conversion (dead-until-wired)."""

    def test_converts_institution_bonapartist_mode_event(self) -> None:
        """INSTITUTION_BONAPARTIST_MODE events convert to InstitutionBonapartistModeEvent."""
        bus_event = Event(
            type=EventType.INSTITUTION_BONAPARTIST_MODE,
            tick=24,
            payload={
                "institution_id": "INST_001",
                "bonapartist_weight": 0.8,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, InstitutionBonapartistModeEvent)
        assert result.event_type == EventType.INSTITUTION_BONAPARTIST_MODE
        assert result.tick == 24
        assert result.institution_id == "INST_001"
        assert result.bonapartist_weight == 0.8


class TestPrincipalContradictionShiftEventConversion:
    """Tests for PRINCIPAL_CONTRADICTION_SHIFT event conversion."""

    def test_converts_principal_contradiction_shift_event(self) -> None:
        """PRINCIPAL_CONTRADICTION_SHIFT events convert to PrincipalContradictionShiftEvent."""
        bus_event = Event(
            type=EventType.PRINCIPAL_CONTRADICTION_SHIFT,
            tick=25,
            payload={
                "previous_field": "capital_labor",
                "new_field": "core_periphery",
                "max_abs_df_dt": 0.42,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, PrincipalContradictionShiftEvent)
        assert result.event_type == EventType.PRINCIPAL_CONTRADICTION_SHIFT
        assert result.tick == 25
        assert result.previous_field == "capital_labor"
        assert result.new_field == "core_periphery"
        assert result.max_abs_df_dt == 0.42


class TestOrganizationalActionEventConversion:
    """Tests for ORGANIZATIONAL_ACTION event conversion (live publisher: ooda.py)."""

    def test_converts_organizational_action_event(self) -> None:
        """ORGANIZATIONAL_ACTION events convert to OrganizationalActionEvent."""
        bus_event = Event(
            type=EventType.ORGANIZATIONAL_ACTION,
            tick=26,
            payload={
                "layer0_count": 4,
                "action_count": 7,
                "org_count": 2,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, OrganizationalActionEvent)
        assert result.event_type == EventType.ORGANIZATIONAL_ACTION
        assert result.tick == 26
        assert result.layer0_count == 4
        assert result.action_count == 7
        assert result.org_count == 2


class TestStateRepressionEventConversion:
    """Tests for STATE_REPRESSION event conversion (speculative; not yet published)."""

    def test_converts_state_repression_event(self) -> None:
        """STATE_REPRESSION events convert to StateRepressionEvent."""
        bus_event = Event(
            type=EventType.STATE_REPRESSION,
            tick=27,
            payload={
                "org_id": "ORG_TEST",
                "target_id": PERIPHERY_WORKER_ID,
                "backfire_delta": 0.2,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, StateRepressionEvent)
        assert result.event_type == EventType.STATE_REPRESSION
        assert result.tick == 27
        assert result.org_id == "ORG_TEST"
        assert result.target_id == PERIPHERY_WORKER_ID
        assert result.backfire_delta == 0.2


class TestStateSurveillanceEventConversion:
    """Tests for STATE_SURVEILLANCE event conversion (speculative; not yet published)."""

    def test_converts_state_surveillance_event(self) -> None:
        """STATE_SURVEILLANCE events convert to StateSurveillanceEvent."""
        bus_event = Event(
            type=EventType.STATE_SURVEILLANCE,
            tick=28,
            payload={
                "org_id": "ORG_TEST",
                "target_id": PERIPHERY_WORKER_ID,
                "backfire_delta": 0.1,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, StateSurveillanceEvent)
        assert result.event_type == EventType.STATE_SURVEILLANCE
        assert result.tick == 28
        assert result.org_id == "ORG_TEST"
        assert result.target_id == PERIPHERY_WORKER_ID
        assert result.backfire_delta == 0.1


class TestGracefulDegradation:
    """Tests for unsupported event types and edge cases."""

    def test_unknown_string_event_type_returns_none(self) -> None:
        """Unknown string event types return None."""
        bus_event = Event(
            type="unknown_event_type",  # type: ignore[arg-type]
            tick=0,
            payload={},
        )
        result = _convert_bus_event_to_pydantic(bus_event)
        assert result is None

    def test_solidarity_awakening_returns_none_until_implemented(self) -> None:
        """SOLIDARITY_AWAKENING returns None (not yet implemented)."""
        bus_event = Event(
            type=EventType.SOLIDARITY_AWAKENING,
            tick=0,
            payload={"node_id": PERIPHERY_WORKER_ID},
        )
        result = _convert_bus_event_to_pydantic(bus_event)
        # SOLIDARITY_AWAKENING doesn't have a dedicated event class yet
        assert result is None

    def test_preserves_timestamp(self) -> None:
        """Timestamp from bus event is preserved in converted event."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        bus_event = Event(
            type=EventType.SURPLUS_EXTRACTION,
            tick=0,
            timestamp=timestamp,
            payload={
                "source_id": PERIPHERY_WORKER_ID,
                "target_id": COMPRADOR_ID,
                "amount": 10.0,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert result.timestamp == timestamp
