"""Bus->pydantic event builders (spec-116 systems-dedup Phase 2).

Extracted from ``_convert_bus_event_to_pydantic``'s ~720-line if/elif chain into
a single keyed registry. Each :data:`EVENT_BUILDERS` entry maps an
:class:`~babylon.models.enums.EventType` to a builder that turns an EventBus
event's ``(tick, timestamp, payload)`` into a typed
:class:`~babylon.models.events.SimulationEvent`. The converter is now a thin
dispatcher over this table; EventTypes absent from the table intentionally drop
to ``None`` at the bus->pydantic boundary (dead enum values or events injected
pre-typed elsewhere). Coverage is asserted by
``tests/unit/engine/test_event_builders.py`` and surfaced by the seam sentinel
``check_event_coverage``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from types import MappingProxyType
from typing import Any, Final

from babylon.models.enums import EventType
from babylon.models.events import (
    AxiomViolationEvent,
    ClassDecompositionEvent,
    ControlRatioCrisisEvent,
    CrisisEvent,
    DoctrinePurgeFailedEvent,
    DoctrineTrapEscapedEvent,
    DoctrineTrapSprungEvent,
    ExtractionEvent,
    MassAwakeningEvent,
    PhaseTransitionEvent,
    PhiHourOutlierEvent,
    QcewCarryForwardEvent,
    RuptureEvent,
    SimulationEvent,
    SolidaritySpikeEvent,
    SparkEvent,
    SubsidyEvent,
    SuperwageCrisisEvent,
    TerminalDecisionEvent,
    TransmissionEvent,
    UprisingEvent,
)
from babylon.models.events.balkanization_payloads import (
    CivilWarDeclaredPayload,
    DualPowerActivePayload,
    FactionVictoryPayload,
    RedSettlerTrapDetectedPayload,
    SecessionDeclaredPayload,
    SovereignCollapsePayload,
    TerritoryTransitionPayload,
)
from babylon.models.events.dispossession_payloads import (
    DispossessionCascadeEvent,
    DispossessionEvent,
    EcologicalOvershootEvent,
    ReserveArmyPressureEvent,
    ValueTransferEvent,
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
    LockoutEvent,
    OrganizationalFractureEvent,
    PogromEvent,
    RedBrownCoupEvent,
    VigilantismEvent,
)
from babylon.models.events.spine_payloads import (
    AspectReversalEvent,
    BifurcationThresholdEvent,
    CoOptiveBreakdownEvent,
    CrisisPhaseTransitionEvent,
    EdgeModeTransitionEvent,
    EntityDeathEvent,
    LatentContradictionReleaseEvent,
    LevelTransitionEvent,
    MarketCorrectionEvent,
    PopulationAttritionEvent,
)
from babylon.models.events.struggle_payloads import (
    FascistRevanchismEvent,
    PeripheralRevoltEvent,
    PowerVacuumEvent,
    RevolutionaryOffensiveEvent,
    SpontaneousRiotEvent,
)

#: A builder turns an EventBus event's (tick, timestamp, payload) into a typed
#: SimulationEvent. Signature mirrors the fields read off ``Event``.
EventBuilder = Callable[[int, datetime, dict[str, Any]], SimulationEvent]

_BUILDERS: dict[EventType, EventBuilder] = {
    EventType.SURPLUS_EXTRACTION: lambda tick, timestamp, payload: ExtractionEvent(
        tick=tick,
        timestamp=timestamp,
        source_id=payload.get("source_id", ""),
        target_id=payload.get("target_id", ""),
        amount=payload.get("amount", 0.0),
        mechanism=payload.get("mechanism", "imperial_rent"),
    ),
    EventType.IMPERIAL_SUBSIDY: lambda tick, timestamp, payload: SubsidyEvent(
        tick=tick,
        timestamp=timestamp,
        source_id=payload.get("source_id", ""),
        target_id=payload.get("target_id", ""),
        amount=payload.get("amount", 0.0),
        repression_boost=payload.get("repression_boost", 0.0),
    ),
    EventType.ECONOMIC_CRISIS: lambda tick, timestamp, payload: CrisisEvent(
        tick=tick,
        timestamp=timestamp,
        pool_ratio=payload.get("pool_ratio", 0.0),
        aggregate_tension=payload.get("aggregate_tension", 0.0),
        decision=payload.get("decision", "UNKNOWN"),
        wage_delta=payload.get("wage_delta", 0.0),
    ),
    EventType.CONSCIOUSNESS_TRANSMISSION: lambda tick, timestamp, payload: TransmissionEvent(
        tick=tick,
        timestamp=timestamp,
        source_id=payload.get("source_id", ""),
        target_id=payload.get("target_id", ""),
        delta=payload.get("delta", 0.0),
        solidarity_strength=payload.get("solidarity_strength", 0.0),
    ),
    EventType.MASS_AWAKENING: lambda tick, timestamp, payload: MassAwakeningEvent(
        tick=tick,
        timestamp=timestamp,
        target_id=payload.get("target_id", ""),
        old_consciousness=payload.get("old_consciousness", 0.0),
        new_consciousness=payload.get("new_consciousness", 0.0),
        triggering_source=payload.get("triggering_source", ""),
    ),
    EventType.EXCESSIVE_FORCE: lambda tick, timestamp, payload: SparkEvent(
        tick=tick,
        timestamp=timestamp,
        node_id=payload.get("node_id", ""),
        repression=payload.get("repression", 0.0),
        spark_probability=payload.get("spark_probability", 0.0),
    ),
    EventType.UPRISING: lambda tick, timestamp, payload: UprisingEvent(
        tick=tick,
        timestamp=timestamp,
        node_id=payload.get("node_id", ""),
        trigger=payload.get("trigger", "unknown"),
        agitation=payload.get("agitation", 0.0),
        repression=payload.get("repression", 0.0),
    ),
    EventType.SOLIDARITY_SPIKE: lambda tick, timestamp, payload: SolidaritySpikeEvent(
        tick=tick,
        timestamp=timestamp,
        node_id=payload.get("node_id", ""),
        solidarity_gained=payload.get("solidarity_gained", 0.0),
        edges_affected=payload.get("edges_affected", 0),
        triggered_by=payload.get("triggered_by", "unknown"),
    ),
    EventType.RUPTURE: lambda tick, timestamp, payload: RuptureEvent(
        tick=tick,
        timestamp=timestamp,
        edge=payload.get("edge", ""),
        opposition=payload.get("opposition", ""),
        gap=payload.get("gap", 0.0),
        rate=payload.get("rate", 0.0),
    ),
    EventType.PHASE_TRANSITION: lambda tick, timestamp, payload: PhaseTransitionEvent(
        tick=tick,
        timestamp=timestamp,
        previous_state=payload.get("previous_state", ""),
        new_state=payload.get("new_state", ""),
        percolation_ratio=payload.get("percolation_ratio", 0.0),
        num_components=payload.get("num_components", 0),
        largest_component_size=payload.get("largest_component_size", 0),
        cadre_density=payload.get("cadre_density", 0.0),
        is_resilient=payload.get("is_resilient"),
    ),
    EventType.SUPERWAGE_CRISIS: lambda tick, timestamp, payload: SuperwageCrisisEvent(
        tick=tick,
        timestamp=timestamp,
        payer_id=payload.get("payer_id", ""),
        receiver_id=payload.get("receiver_id", ""),
        desired_wages=payload.get("desired_wages", 0.0),
        available_pool=payload.get("available_pool", 0.0),
    ),
    EventType.CLASS_DECOMPOSITION: lambda tick, timestamp, payload: ClassDecompositionEvent(
        tick=tick,
        timestamp=timestamp,
        original_id=payload.get("source_class", ""),
        enforcer_fraction=payload.get("enforcer_fraction", 0.3),
        proletariat_fraction=payload.get("proletariat_fraction", 0.7),
    ),
    EventType.CONTROL_RATIO_CRISIS: lambda tick, timestamp, payload: ControlRatioCrisisEvent(
        tick=tick,
        timestamp=timestamp,
        prisoner_population=payload.get("prisoner_population", 0),
        enforcer_population=payload.get("enforcer_population", 0),
        control_ratio=payload.get("control_ratio", 0.0),
        capacity_threshold=payload.get("capacity_threshold", 0.0),
    ),
    EventType.TERMINAL_DECISION: lambda tick, timestamp, payload: TerminalDecisionEvent(
        tick=tick,
        timestamp=timestamp,
        outcome=payload.get("outcome", "genocide"),
        avg_organization=payload.get("avg_organization", 0.0),
        revolution_threshold=payload.get("revolution_threshold", 0.0),
    ),
    EventType.SOVEREIGN_COLLAPSE: lambda tick, timestamp, payload: SovereignCollapsePayload(
        tick=tick,
        timestamp=timestamp,
        sovereign_id=payload.get("sovereign_id", ""),
        trigger=payload.get("trigger", "legitimacy_zero"),
        claimed_territories_count=payload.get("claimed_territories_count", 0),
    ),
    EventType.TERRITORY_TRANSITION: lambda tick, timestamp, payload: TerritoryTransitionPayload(
        tick=tick,
        timestamp=timestamp,
        territory_id=payload.get("territory_id", ""),
        from_sovereign_id=payload.get("from_sovereign_id"),
        to_sovereign_id=payload.get("to_sovereign_id"),
        from_winning_faction_id=payload.get("from_winning_faction_id"),
        to_winning_faction_id=payload.get("to_winning_faction_id"),
        reason=payload.get("reason", "influence_flip"),
    ),
    EventType.FACTION_VICTORY: lambda tick, timestamp, payload: FactionVictoryPayload(
        tick=tick,
        timestamp=timestamp,
        faction_id=payload.get("faction_id", ""),
        aggregate_influence_share=payload.get("aggregate_influence_share", 0.0),
    ),
    EventType.CIVIL_WAR_DECLARED: lambda tick, timestamp, payload: CivilWarDeclaredPayload(
        tick=tick,
        timestamp=timestamp,
        parent_sovereign_id=payload.get("parent_sovereign_id", ""),
        secessionist_faction_id=payload.get("secessionist_faction_id", ""),
        contested_territory_count=payload.get("contested_territory_count", 0),
    ),
    EventType.RED_SETTLER_TRAP_DETECTED: lambda tick, timestamp, payload: (
        RedSettlerTrapDetectedPayload(
            tick=tick,
            timestamp=timestamp,
            faction_id=payload.get("faction_id", ""),
            class_reduction=payload.get("class_reduction", 0.0),
            colonial_stance=payload.get("colonial_stance", "uphold"),
        )
    ),
    EventType.DUAL_POWER_ACTIVE: lambda tick, timestamp, payload: DualPowerActivePayload(
        tick=tick,
        timestamp=timestamp,
        territory_id=payload.get("territory_id", ""),
        competing_sovereign_ids=tuple(payload.get("competing_sovereign_ids", ())),
        control_level_sum=payload.get("control_level_sum", 0.0),
    ),
    EventType.FASCIST_DRIFT: lambda tick, timestamp, payload: FascistDriftEvent(
        tick=tick,
        timestamp=timestamp,
        node_id=payload.get("node_id", ""),
        fascist_pull=payload.get("fascist_pull", 0.0),
        fascist_alignment=payload.get("fascist_alignment", 0.0),
        entitlement=payload.get("entitlement", 0.0),
        solidarity=payload.get("solidarity", 0.0),
        regime=payload.get("regime"),
    ),
    EventType.FASCIST_RECRUITMENT: lambda tick, timestamp, payload: FascistRecruitmentEvent(
        tick=tick,
        timestamp=timestamp,
        node_id=payload.get("node_id", ""),
        faction_id=payload.get("faction_id", ""),
        fascist_alignment=payload.get("fascist_alignment", 0.0),
    ),
    EventType.ORGANIZATIONAL_FRACTURE: lambda tick, timestamp, payload: OrganizationalFractureEvent(
        tick=tick,
        timestamp=timestamp,
        org_id=payload.get("org_id", ""),
        member_id=payload.get("member_id", ""),
        chauvinism=payload.get("chauvinism", 0.0),
        defection_probability=payload.get("defection_probability", 0.0),
    ),
    EventType.RED_BROWN_COUP: lambda tick, timestamp, payload: RedBrownCoupEvent(
        tick=tick,
        timestamp=timestamp,
        org_id=payload.get("org_id", ""),
        defections=payload.get("defections", 0),
        member_count=payload.get("member_count", 0),
    ),
    EventType.POGROM: lambda tick, timestamp, payload: PogromEvent(
        tick=tick,
        timestamp=timestamp,
        org_id=payload.get("org_id", ""),
        target_id=payload.get("target_id", ""),
        repression_increment=payload.get("repression_increment", 0.0),
        wealth_destroyed=payload.get("wealth_destroyed", 0.0),
    ),
    EventType.LOCKOUT: lambda tick, timestamp, payload: LockoutEvent(
        tick=tick,
        timestamp=timestamp,
        org_id=payload.get("org_id", ""),
        target_id=payload.get("target_id", ""),
        wage_attenuation=payload.get("wage_attenuation", 0.0),
    ),
    EventType.VIGILANTISM: lambda tick, timestamp, payload: VigilantismEvent(
        tick=tick,
        timestamp=timestamp,
        org_id=payload.get("org_id", ""),
        target_id=payload.get("target_id", ""),
        repression_increment=payload.get("repression_increment", 0.0),
    ),
    EventType.LIFECYCLE_TRANSITION: lambda tick, timestamp, payload: LifecycleTransitionEvent(
        tick=tick,
        timestamp=timestamp,
        territory_id=payload.get("territory_id", ""),
        pop_d=payload.get("pop_d", 0.0),
        pop_p=payload.get("pop_p", 0.0),
        pop_d_prime=payload.get("pop_d_prime", 0.0),
        dependency_ratio=payload.get("dependency_ratio", 0.0),
    ),
    EventType.LEGITIMATION_CRISIS: lambda tick, timestamp, payload: LegitimationCrisisEvent(
        tick=tick,
        timestamp=timestamp,
        territory_id=payload.get("territory_id", ""),
        legitimation_index=payload.get("legitimation_index", 0.0),
    ),
    EventType.LEGITIMATION_RECOVERY: lambda tick, timestamp, payload: LegitimationRecoveryEvent(
        tick=tick,
        timestamp=timestamp,
        territory_id=payload.get("territory_id", ""),
        legitimation_index=payload.get("legitimation_index", 0.0),
    ),
    EventType.INHERITANCE_TRANSFER: lambda tick, timestamp, payload: InheritanceTransferEvent(
        tick=tick,
        timestamp=timestamp,
        territory_id=payload.get("territory_id", ""),
        total_transferred=payload.get("total_transferred", 0.0),
        care_consumed=payload.get("care_consumed", 0.0),
        net_inheritance=payload.get("net_inheritance", 0.0),
        inheritance_gini=payload.get("inheritance_gini", 0.0),
    ),
    EventType.INSTITUTION_FACTION_SHIFT: lambda tick, timestamp, payload: (
        InstitutionFactionShiftEvent(
            tick=tick,
            timestamp=timestamp,
            institution_id=payload.get("institution_id", ""),
            old_fraction=payload.get("old_fraction", ""),
            new_fraction=payload.get("new_fraction", ""),
            weights=payload.get("weights", {}),
        )
    ),
    EventType.INSTITUTION_BONAPARTIST_MODE: lambda tick, timestamp, payload: (
        InstitutionBonapartistModeEvent(
            tick=tick,
            timestamp=timestamp,
            institution_id=payload.get("institution_id", ""),
            bonapartist_weight=payload.get("bonapartist_weight", 0.0),
        )
    ),
    EventType.PRINCIPAL_CONTRADICTION_SHIFT: lambda tick, timestamp, payload: (
        PrincipalContradictionShiftEvent(
            tick=tick,
            timestamp=timestamp,
            previous_field=payload.get("previous_field"),
            new_field=payload.get("new_field", ""),
            max_abs_df_dt=payload.get("max_abs_df_dt", 0.0),
        )
    ),
    EventType.ORGANIZATIONAL_ACTION: lambda tick, timestamp, payload: OrganizationalActionEvent(
        tick=tick,
        timestamp=timestamp,
        layer0_count=payload.get("layer0_count", 0),
        action_count=payload.get("action_count", 0),
        org_count=payload.get("org_count", 0),
    ),
    EventType.STATE_REPRESSION: lambda tick, timestamp, payload: StateRepressionEvent(
        tick=tick,
        timestamp=timestamp,
        org_id=payload.get("org_id", ""),
        target_id=payload.get("target_id", ""),
        backfire_delta=payload.get("backfire_delta", 0.0),
    ),
    EventType.STATE_SURVEILLANCE: lambda tick, timestamp, payload: StateSurveillanceEvent(
        tick=tick,
        timestamp=timestamp,
        org_id=payload.get("org_id", ""),
        target_id=payload.get("target_id", ""),
        backfire_delta=payload.get("backfire_delta", 0.0),
    ),
    EventType.POWER_VACUUM: lambda tick, timestamp, payload: PowerVacuumEvent(
        tick=tick,
        timestamp=timestamp,
        comprador_id=payload.get("comprador_id", ""),
        comprador_wealth=payload.get("comprador_wealth", 0.0),
        subsistence_threshold=payload.get("subsistence_threshold", 0.0),
        revolutionary_capacity=payload.get("revolutionary_capacity", 0.0),
        jackson_threshold=payload.get("jackson_threshold", 0.0),
    ),
    EventType.REVOLUTIONARY_OFFENSIVE: lambda tick, timestamp, payload: RevolutionaryOffensiveEvent(
        tick=tick,
        timestamp=timestamp,
        periphery_id=payload.get("periphery_id", ""),
        revolutionary_capacity=payload.get("revolutionary_capacity", 0.0),
        agitation_boost=payload.get("agitation_boost", 0.0),
        narrative_hint=payload.get("narrative_hint", ""),
    ),
    EventType.FASCIST_REVANCHISM: lambda tick, timestamp, payload: FascistRevanchismEvent(
        tick=tick,
        timestamp=timestamp,
        core_worker_id=payload.get("core_worker_id"),
        revolutionary_capacity=payload.get("revolutionary_capacity", 0.0),
        identity_boost=payload.get("identity_boost", 0.0),
        acquiescence_boost=payload.get("acquiescence_boost", 0.0),
        narrative_hint=payload.get("narrative_hint", ""),
    ),
    EventType.SPONTANEOUS_RIOT: lambda tick, timestamp, payload: SpontaneousRiotEvent(
        tick=tick,
        timestamp=timestamp,
        node_id=payload.get("node_id", ""),
        volatility=payload.get("volatility", 0.0),
        organizational_discipline=payload.get("organizational_discipline", 0.0),
        riot_risk=payload.get("riot_risk", 0.0),
        wealth_before=payload.get("wealth_before", 0.0),
        wealth_after=payload.get("wealth_after", 0.0),
        narrative_hint=payload.get("narrative_hint", ""),
    ),
    EventType.PERIPHERAL_REVOLT: lambda tick, timestamp, payload: PeripheralRevoltEvent(
        tick=tick,
        timestamp=timestamp,
        node_id=payload.get("node_id", ""),
        edges_severed=payload.get("edges_severed", 0),
        p_acquiescence=payload.get("p_acquiescence", 0.0),
        p_revolution=payload.get("p_revolution", 0.0),
        capital_labor_gap=payload.get("capital_labor_gap", 0.0),
        narrative_hint=payload.get("narrative_hint", ""),
    ),
    EventType.DISPOSSESSION_EVENT: lambda tick, timestamp, payload: DispossessionEvent(
        tick=tick,
        timestamp=timestamp,
        territory=payload.get("territory", ""),
        intensity=payload.get("intensity", 0.0),
        foreclosure_rate=payload.get("foreclosure_rate", 0.0),
        eviction_rate=payload.get("eviction_rate", 0.0),
        displacement_rate=payload.get("displacement_rate", 0.0),
    ),
    EventType.VALUE_TRANSFER: lambda tick, timestamp, payload: ValueTransferEvent(
        tick=tick,
        timestamp=timestamp,
        territory=payload.get("territory", ""),
        total_transferred=payload.get("total_transferred", 0.0),
        net_received=payload.get("net_received", 0.0),
        deadweight_loss=payload.get("deadweight_loss", 0.0),
    ),
    EventType.RESERVE_ARMY_PRESSURE: lambda tick, timestamp, payload: ReserveArmyPressureEvent(
        tick=tick,
        timestamp=timestamp,
        territory=payload.get("territory", ""),
        reserve_ratio=payload.get("reserve_ratio", 0.0),
        wage_pressure=payload.get("wage_pressure", 0.0),
        median_wage=payload.get("median_wage", 0.0),
    ),
    EventType.DISPOSSESSION_CASCADE: lambda tick, timestamp, payload: DispossessionCascadeEvent(
        tick=tick,
        timestamp=timestamp,
        fips=payload.get("fips", ""),
        cumulative_la_decline=payload.get("cumulative_la_decline", 0.0),
        milestone_crossed=payload.get("milestone_crossed", 0.0),
        current_la_share=payload.get("current_la_share", 0.0),
        baseline_la_share=payload.get("baseline_la_share", 0.0),
    ),
    EventType.ECOLOGICAL_OVERSHOOT: lambda tick, timestamp, payload: EcologicalOvershootEvent(
        tick=tick,
        timestamp=timestamp,
        overshoot_ratio=payload.get("overshoot_ratio", 0.0),
        total_consumption=payload.get("total_consumption", 0.0),
        total_biocapacity=payload.get("total_biocapacity", 0.0),
    ),
    EventType.DOCTRINE_TRAP_SPRUNG: lambda tick, timestamp, payload: DoctrineTrapSprungEvent(
        tick=tick,
        timestamp=timestamp,
        org_id=payload.get("org_id", ""),
        node_id=payload.get("node_id", ""),
    ),
    EventType.DOCTRINE_TRAP_ESCAPED: lambda tick, timestamp, payload: DoctrineTrapEscapedEvent(
        tick=tick,
        timestamp=timestamp,
        org_id=payload.get("org_id", ""),
        node_id=payload.get("node_id", ""),
    ),
    EventType.DOCTRINE_PURGE_FAILED: lambda tick, timestamp, payload: DoctrinePurgeFailedEvent(
        tick=tick,
        timestamp=timestamp,
        org_id=payload.get("org_id", ""),
        node_id=payload.get("node_id", ""),
    ),
    EventType.MARKET_CORRECTION: lambda tick, timestamp, payload: MarketCorrectionEvent(
        tick=tick,
        timestamp=timestamp,
        overhang=payload.get("overhang", 0.0),
        serviceable=payload.get("serviceable", 0.0),
        profit_rate=payload.get("profit_rate"),
        fictitious_log_before=payload.get("fictitious_log_before", 0.0),
        fictitious_log_after=payload.get("fictitious_log_after", 0.0),
        price_log_before=payload.get("price_log_before", 0.0),
        price_log_after=payload.get("price_log_after", 0.0),
    ),
    EventType.ENTITY_DEATH: lambda tick, timestamp, payload: EntityDeathEvent(
        tick=tick,
        timestamp=timestamp,
        entity_id=payload.get("entity_id", ""),
        wealth=payload.get("wealth", 0.0),
        consumption_needs=payload.get("consumption_needs", 0.0),
        s_bio=payload.get("s_bio", 0.0),
        s_class=payload.get("s_class", 0.0),
        cause=payload.get("cause", "unknown"),
    ),
    EventType.POPULATION_ATTRITION: lambda tick, timestamp, payload: PopulationAttritionEvent(
        tick=tick,
        timestamp=timestamp,
        entity_id=payload.get("entity_id", ""),
        deaths=payload.get("deaths", 0),
        remaining_population=payload.get("remaining_population", 0),
        attrition_rate=payload.get("attrition_rate", 0.0),
    ),
    EventType.CRISIS_PHASE_TRANSITION: lambda tick, timestamp, payload: CrisisPhaseTransitionEvent(
        tick=tick,
        timestamp=timestamp,
        fips=payload.get("fips", ""),
        previous_phase=payload.get("previous_phase", ""),
        new_phase=payload.get("new_phase", ""),
        profit_rate=payload.get("profit_rate"),
        crisis_duration=payload.get("crisis_duration", 0),
    ),
    EventType.BIFURCATION_THRESHOLD: lambda tick, timestamp, payload: BifurcationThresholdEvent(
        tick=tick,
        timestamp=timestamp,
        fips=payload.get("fips", ""),
        score=payload.get("score", 0.0),
        direction=payload.get("direction", ""),
        solidarity_density=payload.get("solidarity_density", 0.0),
        legitimation=payload.get("legitimation", 0.0),
        class_burden_ratio=payload.get("class_burden_ratio", 0.0),
        threshold=payload.get("threshold", 0.0),
    ),
    EventType.EDGE_MODE_TRANSITION: lambda tick, timestamp, payload: EdgeModeTransitionEvent(
        tick=tick,
        timestamp=timestamp,
        source_id=payload.get("source_id", ""),
        target_id=payload.get("target_id", ""),
        from_mode=str(payload.get("from_mode", "")),
        to_mode=str(payload.get("to_mode", "")),
        predicate=payload.get("predicate", ""),
        description=payload.get("description", ""),
    ),
    EventType.CO_OPTIVE_BREAKDOWN: lambda tick, timestamp, payload: CoOptiveBreakdownEvent(
        tick=tick,
        timestamp=timestamp,
        source_id=payload.get("source_id", ""),
        target_id=payload.get("target_id", ""),
        latent_released=dict(payload.get("latent_released", {})),
        multiplier=payload.get("multiplier", 0.0),
    ),
    EventType.LATENT_CONTRADICTION_RELEASE: lambda tick, timestamp, payload: (
        LatentContradictionReleaseEvent(
            tick=tick,
            timestamp=timestamp,
            node_id=payload.get("node_id", ""),
            released_fields=dict(payload.get("released_fields", {})),
        )
    ),
    EventType.ASPECT_REVERSAL: lambda tick, timestamp, payload: AspectReversalEvent(
        tick=tick,
        timestamp=timestamp,
        source_id=payload.get("source_id", ""),
        target_id=payload.get("target_id", ""),
        previous_dominant=payload.get("previous_dominant", ""),
        new_dominant=payload.get("new_dominant", ""),
    ),
    EventType.LEVEL_TRANSITION: lambda tick, timestamp, payload: LevelTransitionEvent(
        tick=tick,
        timestamp=timestamp,
        opposition=payload.get("opposition", ""),
        from_level=payload.get("from_level", ""),
        to_level=payload.get("to_level", ""),
        gap=payload.get("gap", 0.0),
        rate=payload.get("rate", 0.0),
    ),
    EventType.SECESSION_DECLARED: lambda tick, timestamp, payload: SecessionDeclaredPayload(
        tick=tick,
        timestamp=timestamp,
        secessionist_faction_id=payload.get("secessionist_faction_id", ""),
        parent_sovereign_id=payload.get("parent_sovereign_id", ""),
        contiguous_territory_ids=tuple(payload.get("contiguous_territory_ids", ())),
        observer_triggered=payload.get("observer_triggered", False),
    ),
    EventType.CALIBRATION_AXIOM_VIOLATION: lambda tick, timestamp, payload: AxiomViolationEvent(
        tick=tick,
        timestamp=timestamp,
        industry=payload.get("industry", ""),
        year=payload.get("year", 0),
        ratio=payload.get("ratio", 0.0),
        threshold=payload.get("threshold", 1.0),
    ),
    EventType.CALIBRATION_QCEW_CARRY_FORWARD: lambda tick, timestamp, payload: (
        QcewCarryForwardEvent(
            tick=tick,
            timestamp=timestamp,
            county_fips=payload.get("county_fips", ""),
            year=payload.get("year", 0),
            look_back_year=payload.get("look_back_year", 0),
            look_back_distance=payload.get("look_back_distance", 0),
        )
    ),
    EventType.CALIBRATION_PHI_HOUR_OUTLIER: lambda tick, timestamp, payload: PhiHourOutlierEvent(
        tick=tick,
        timestamp=timestamp,
        county_fips=payload.get("county_fips", ""),
        phi_hour=payload.get("phi_hour", 0.0),
        threshold_low=payload.get("threshold_low", -1000.0),
        threshold_high=payload.get("threshold_high", 1000.0),
    ),
}

#: Immutable bus->pydantic builder registry. Keyed by EventType; the converter
#: dispatches through ``.get(event_type)`` and returns ``None`` for misses.
EVENT_BUILDERS: Final[Mapping[EventType, EventBuilder]] = MappingProxyType(_BUILDERS)
