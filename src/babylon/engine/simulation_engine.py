"""Simulation engine for the Babylon game loop.

ADR032: Materialist Causality System Order

The step() function is the core of Phase 2. It takes a WorldState and
SimulationConfig and returns a new WorldState representing one tick of
simulation time.

The step function is:
- **Pure**: No side effects, no mutation of inputs
- **Deterministic**: Same inputs always produce same outputs
- **Transparent**: Order of operations encodes historical materialism

Turn Order (materialist causality - base before superstructure):
1. Vitality - Biological cost + death (dead entities don't work)
2. Territory - Land state updates (land conditions affect production)
3. Production - Value creation (value must exist before extraction)
4. Solidarity - Organization (affects bargaining power)
5. Imperial Rent - Value extraction (landlord eats after harvest)
6. Decomposition - LA decomposes on super-wage crisis (Terminal Crisis)
7. Control Ratio - Guard:prisoner ratio + terminal decision (Terminal Crisis)
8. Metabolism - Environmental degradation (ecological residue of production)
9. Survival - Risk assessment (P(S|A), P(S|R) from material state)
10. Struggle - Action/Revolt (agency responds to survival odds)
11. Consciousness - Ideological drift (ideology responds to material)
12. Contradiction - Tension aggregation (final systemic accounting)

Phase 2.1: Refactored to modular System architecture.
Phase 4a: Refactored to use ServiceContainer for dependency injection.
ADR032: Reordered systems for materialist causality.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Final
from uuid import uuid4

from babylon.config.defines import GameDefines
from babylon.domain.economics.tick.system import TickDynamicsSystem
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.collapse_transition import CollapseTransitionSystem
from babylon.engine.systems.community import CommunitySystem
from babylon.engine.systems.contradiction import ContradictionSystem
from babylon.engine.systems.contradiction_field import ContradictionFieldSystem
from babylon.engine.systems.control_ratio import ControlRatioSystem
from babylon.engine.systems.decomposition import DecompositionSystem
from babylon.engine.systems.dispossession_events import DispossessionEventSystem
from babylon.engine.systems.doctrine import DoctrineSystem
from babylon.engine.systems.economic import ImperialRentSystem
from babylon.engine.systems.edge_transition import EdgeTransitionSystem
from babylon.engine.systems.epistemic_horizon import EpistemicHorizonSystem
from babylon.engine.systems.faction_influence import FactionInfluenceSystem
from babylon.engine.systems.field_derivative import FieldDerivativeSystem
from babylon.engine.systems.ideology import ConsciousnessSystem
from babylon.engine.systems.lifecycle import LifecycleSystem
from babylon.engine.systems.metabolism import MetabolismSystem
from babylon.engine.systems.ooda import OODASystem
from babylon.engine.systems.production import ProductionSystem
from babylon.engine.systems.reactionary import FascistFactionSystem
from babylon.engine.systems.reserve_army import ReserveArmySystem
from babylon.engine.systems.solidarity import SolidaritySystem
from babylon.engine.systems.sovereignty import SovereigntySystem
from babylon.engine.systems.struggle import StruggleSystem
from babylon.engine.systems.substrate import SubstrateSystem
from babylon.engine.systems.survival import SurvivalSystem
from babylon.engine.systems.territory import TerritorySystem
from babylon.engine.systems.vitality import VitalitySystem
from babylon.engine.systems.wealth_distribution import WealthDistributionSystem
from babylon.kernel.event_bus import Event
from babylon.kernel.log import log_context_scope
from babylon.kernel.system_protocol import ContextType, System
from babylon.models.config import SimulationConfig
from babylon.models.enums import EventType
from babylon.models.events import (
    ClassDecompositionEvent,
    ControlRatioCrisisEvent,
    CrisisEvent,
    DoctrinePurgeFailedEvent,
    DoctrineTrapEscapedEvent,
    DoctrineTrapSprungEvent,
    ExtractionEvent,
    MassAwakeningEvent,
    PhaseTransitionEvent,
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
    OrganizationalFractureEvent,
    RedBrownCoupEvent,
)
from babylon.models.events.struggle_payloads import (
    FascistRevanchismEvent,
    PeripheralRevoltEvent,
    PowerVacuumEvent,
    RevolutionaryOffensiveEvent,
    SpontaneousRiotEvent,
)
from babylon.models.world_state import WorldState

if TYPE_CHECKING:
    from babylon.kernel.services import ServicesProtocol
    from babylon.topology.graph import BabylonGraph

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Modular engine that advances the simulation by iterating through Systems.

    The engine holds a list of systems and executes them in sequence.
    Order encodes materialist causality (ADR032):
    1. Vitality (death check)
    2. Territory (land state)
    3. Production (value creation)
    4. Solidarity (organization)
    5. Imperial Rent (extraction)
    6. Decomposition (LA crisis)
    7. Control Ratio (terminal decision)
    8. Metabolism (ecology)
    9. Survival (risk assessment)
    10. Struggle (agency)
    11. Consciousness (ideology)
    12. Contradiction (tension)
    13. ContradictionField (field computation) - Feature 002
    14. FieldDerivative (derivatives + principal) - Feature 002
    15. EdgeTransition (predicates + state machine) - Feature 002
    """

    def __init__(
        self,
        systems: list[System],
        *,
        auditor: Any = None,
    ) -> None:
        """Initialize the engine with a list of systems.

        Args:
            systems: Ordered list of systems to execute each tick.
                     Order matters! Economic systems must run before ideology.
            auditor: Optional Spec 062 ConservationAuditor. When provided,
                runs at end-of-tick (after all systems) and emits any
                alarm-severity audit rows onto the event bus per FR-047.
                When None, audit step is skipped — preserves backward
                compatibility with pre-spec-062 callers.
        """
        self._systems = systems
        self._auditor = auditor
        # Spec-065 T074: cumulative wallclock per system class name.
        # Populated by :meth:`run_tick` via the ``time.perf_counter()``
        # wrapper around each ``system.step(...)`` call. Empty until the
        # engine actually runs (i.e., until spec-066 wires the bridged
        # runner through ``run_tick``).
        self._per_system_ms: dict[str, float] = {}

    @property
    def systems(self) -> list[System]:
        """Read-only access to registered systems."""
        return list(self._systems)

    @property
    def per_system_ms(self) -> dict[str, float]:
        """Cumulative wallclock (ms) per system class name.

        Spec-065 T074. Reset via :meth:`reset_per_system_ms` between
        runs if the same engine instance is reused.
        """
        return dict(self._per_system_ms)

    def reset_per_system_ms(self) -> None:
        """Clear the per-system wallclock accumulator (T074)."""
        self._per_system_ms.clear()

    @property
    def auditor(self) -> Any:
        """The conservation auditor, or None if not configured."""
        return self._auditor

    def run_tick(
        self,
        graph: BabylonGraph,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        """Execute all systems in order for one tick.

        All logs emitted during this method are automatically tagged with
        tick number and a unique correlation_id (UUID) for tracing.

        Spec 062, T068: when ``self._auditor`` is set, the
        :class:`ConservationAuditor` runs after every system completes.
        Alarm-severity rows are published as ``ConservationAlarmEvent``
        instances onto the event bus.

        Args:
            graph: NetworkX graph (mutated in place by systems)
            services: ServicesProtocol with config, formulas, event_bus, database, metrics
            context: TickContext or dict passed to all systems

        Spec 008: Logs within run_tick() include tick and correlation_id.
        """
        # T025: Extract tick number from context with fallback to 0
        tick: int
        if hasattr(context, "tick"):
            tick = context.tick  # TickContext has .tick attribute
        elif isinstance(context, dict):
            tick = context.get("tick", 0)
        else:
            tick = 0

        # T026: Generate per-tick UUID correlation_id
        correlation_id = str(uuid4())

        # T027: Wrap system execution with log_context_scope
        with log_context_scope(tick=tick, correlation_id=correlation_id):
            for system in self._systems:
                # Spec-065 T074: thin per-system wallclock wrapper. Accumulates
                # elapsed milliseconds per system class name into
                # ``self._per_system_ms`` for summary.json.performance.
                system_name = type(system).__name__
                t0 = time.perf_counter()
                try:
                    system.step(graph, services, context)
                finally:
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    self._per_system_ms[system_name] = (
                        self._per_system_ms.get(system_name, 0.0) + elapsed_ms
                    )

            # Spec 062 T068: end-of-tick conservation audit.
            if self._auditor is not None:
                self._run_audit(graph, services, context, tick)

    def _run_audit(
        self,
        graph: BabylonGraph,
        services: ServicesProtocol,
        context: ContextType,
        tick: int,
    ) -> None:
        """Run the conservation auditor and emit alarm events.

        Hex rows are reconstructed from the graph for the determinism
        hash. The auditor's registered evaluators (registered by the
        engine bridge) compute the actual residuals.
        """
        _ = services  # Reserved: future evaluators may consume services.
        session_id = (
            context.session_id
            if hasattr(context, "session_id")
            else (context.get("session_id") if isinstance(context, dict) else None)
        )
        if session_id is None:
            # Without a session_id the auditor cannot tag rows; skip silently.
            return

        # Reconstruct hex rows from graph for the determinism hash. The
        # auditor is robust to empty iterables (returns empty rows list).
        hex_rows = [
            attrs for _node, attrs in graph.nodes(data=True) if attrs.get("_node_type") == "hex"
        ]
        action_list = context.get("actions") if isinstance(context, dict) else None

        rows, alarms = self._auditor.evaluate(
            session_id=session_id,
            tick=tick,
            hex_rows=hex_rows,
            post_state=graph,
            action_list=action_list,
        )

        # Stash rows on the context so the envelope builder can pick them up.
        if isinstance(context, dict):
            context.setdefault("audit_rows", []).extend(rows)

        # Emit alarms onto the event bus per FR-047 / Clarification Q3.
        # The bus expects a frozen Event(type=str, tick=int, payload=dict);
        # wrap the ConservationAlarmEvent Pydantic model accordingly so
        # `bus.subscribe("conservation_alarm", handler)` routes correctly.
        event_bus = getattr(services, "event_bus", None)
        if event_bus is None or not alarms:
            return
        for alarm in alarms:
            try:
                event_bus.publish(
                    Event(
                        type="conservation_alarm",
                        tick=alarm.tick,
                        payload=alarm.model_dump(mode="json"),
                    )
                )
            except Exception:  # noqa: BLE001 - observers must not break the tick
                logger.exception("ConservationAlarmEvent observer raised; tick continues")


# ADR032: Materialist Causality System Order
# The order encodes strict materialist causality: base before superstructure.
# Each system sees mutations from all previous systems in the sequence.
#
# Spec 056 (F6=α, 2026-05-07) reordered OODA from position 21 (last) to
# position 14 — between Material Base and Consequences — so the engine's
# actual execution order matches ADR032's documented partition. See
# `MATERIAL_BASE_SYSTEMS` / `ACTION_PHASE_SYSTEMS` / `CONSEQUENCE_SYSTEMS`
# below for the canonical partition.
#
# Material Base (biological, spatial, economic) — positions 1–13:
# 1. VitalitySystem - Dead entities don't work (The Drain + The Reaper)
# 2. TerritorySystem - Land conditions affect production (Carceral Geography)
# 3. ProductionSystem - Value creation from labor × biocapacity (The Labor)
# 4. TickDynamicsSystem - Economic State Evolution (Feature 017)
# 5. ReserveArmySystem - Reserve army wage pressure (Feature 021)
# 6. CommunitySystem - Community hypergraph layer (Feature 022)
# 7. LifecycleSystem - D-P-D' lifecycle circuit (Feature 030)
# 8. SolidaritySystem - Organization affects bargaining
# 9. ImperialRentSystem - Value extraction (The Extraction)
# 10. DispossessionEventSystem - Dispossession events (Feature 021)
# 11. DecompositionSystem - LA decomposes on super-wage crisis (Terminal Crisis)
# 12. ControlRatioSystem - Guard:prisoner ratio + terminal decision
# 13. MetabolismSystem - Ecological residue of production
#
# Action Phase (organization deliberation) — position 14:
# 14. OODASystem - Organizations observe Material Base, then act (Feature 032)
#
# Consequences (social, ideological, dialectical-field) — positions 15–21:
# 15. SurvivalSystem - Risk assessment from material state (P(S|A), P(S|R))
# 16. StruggleSystem - Agency responds to survival odds (George Floyd Dynamic)
# 17. ConsciousnessSystem - Ideology responds to material (Bifurcation)
# 17.4 FascistFactionSystem - Reactionary drift + fascist capture (Spec 071)
# 18. ContradictionSystem - Systemic tension accounting (The Reckoning)
# 19. ContradictionFieldSystem - Contradiction field computation (Feature 002)
# 20. FieldDerivativeSystem - Spatial/temporal derivatives + principal (Feature 002)
# 21. EdgeTransitionSystem - Compound predicates + edge mode transitions (Feature 002)
# 22. EpistemicHorizonSystem - Fog-of-war M_r/I_c shadow (Epistemic Horizon Phase 1);
#     runs LAST because it observes the fully-mutated tick (reads this tick's
#     p_acquiescence/class_consciousness, not last tick's stale values) and
#     writes read-only shadow attrs nothing else in the engine consumes yet.
_DEFAULT_SYSTEMS: list[System] = [
    # --- Material Base (positions 1–13, plus Substrate at 2.5) ---
    VitalitySystem(),  # 1. Biological cost + death
    TerritorySystem(),  # 2. Land state updates
    SubstrateSystem(),  # 2.5. Substrate stocks (Spec 062, US7, FR-050)
    ProductionSystem(),  # 3. Value creation
    TickDynamicsSystem(),  # 4. Tick dynamics (Feature 017)
    ReserveArmySystem(),  # 5. Reserve army wage pressure (Feature 021)
    CommunitySystem(),  # 6. Community hypergraph layer (Feature 022)
    LifecycleSystem(),  # 7. D-P-D' lifecycle circuit (Feature 030)
    SolidaritySystem(),  # 8. Organization calculation
    ImperialRentSystem(),  # 9. Value extraction
    DispossessionEventSystem(),  # 10. Dispossession events (Feature 021)
    DecompositionSystem(),  # 11. LA decomposition
    ControlRatioSystem(),  # 12. Guard:prisoner ratio
    MetabolismSystem(),  # 13. Environmental degradation
    # --- Action Phase (position 14) — Spec 056 F6=α reorder ---
    OODASystem(),  # 14. Organizations observe + act (Feature 032)
    FactionInfluenceSystem(),  # 14.5. Spec-070 FR-021 winning-Faction resolution
    DoctrineSystem(),  # 14.7. Per-org Doctrine Tree state (owner-ratified 2026-07-15);
    #        shadow: writes org doctrine state (acquire/decay/traps). Feedback into
    #        bifurcation/consciousness is wired in Unit 6. Byte-safe: the qa:regression
    #        scenarios carry no organization nodes, so this is a no-op there.
    # --- Consequences (positions 15–21) ---
    SurvivalSystem(),  # 15. Risk assessment
    StruggleSystem(),  # 16. Action/Revolt
    ConsciousnessSystem(),  # 17. Ideological drift
    FascistFactionSystem(),  # 17.4. Spec-071 reactionary drift + fascist capture + stance hook
    SovereigntySystem(),  # 17.5. Spec-070 sovereign metabolic_impact (FR-019, FR-043)
    ContradictionSystem(),  # 18. Tension aggregation
    ContradictionFieldSystem(),  # 19. Contradiction field computation (Feature 002)
    FieldDerivativeSystem(),  # 20. Spatial/temporal derivatives + principal (Feature 002)
    CollapseTransitionSystem(),  # 20.5. Spec-070 sovereign-collapse + territory partition
    EdgeTransitionSystem(),  # 21. Compound predicates + edge mode transitions (Feature 002)
    WealthDistributionSystem(),  # 21.5. National wealth-share axis (Program 21 Phase-1 shadow; writes only its own axis)
    EpistemicHorizonSystem(),  # 22. Fog-of-war M_r/I_c shadow (Epistemic Horizon Phase 1) — LAST, observes fully-mutated tick
]


# Spec 056 (FR-002): three canonical sets partitioning _DEFAULT_SYSTEMS
# into Material Base / Action Phase / Consequences. Single source of
# truth for spec-056 US1 + US2 invariants. Adding a new System to
# _DEFAULT_SYSTEMS MUST also add it to exactly one of these sets;
# the import-time assertion below catches drift.
MATERIAL_BASE_SYSTEMS: Final[frozenset[type[System]]] = frozenset(
    {
        VitalitySystem,
        TerritorySystem,
        SubstrateSystem,  # Spec 062, US7: physical substrate stocks
        ProductionSystem,
        TickDynamicsSystem,
        ReserveArmySystem,
        CommunitySystem,
        LifecycleSystem,
        SolidaritySystem,
        ImperialRentSystem,
        DispossessionEventSystem,
        DecompositionSystem,
        ControlRatioSystem,
        MetabolismSystem,
    }
)

ACTION_PHASE_SYSTEMS: Final[frozenset[type[System]]] = frozenset({OODASystem})

CONSEQUENCE_SYSTEMS: Final[frozenset[type[System]]] = frozenset(
    {
        SurvivalSystem,
        StruggleSystem,
        ConsciousnessSystem,
        FascistFactionSystem,  # Spec-071 reactionary subject (position 17.4)
        FactionInfluenceSystem,  # Spec-070 FR-042 (research.md R-003)
        SovereigntySystem,  # Spec-070 FR-042
        CollapseTransitionSystem,  # Spec-070 FR-042
        ContradictionSystem,
        ContradictionFieldSystem,
        FieldDerivativeSystem,
        EdgeTransitionSystem,
        WealthDistributionSystem,  # Program 21 Phase-1 shadow (national wealth-share axis)
        EpistemicHorizonSystem,  # Epistemic Horizon Phase 1 shadow (observes consequences)
        DoctrineSystem,  # Doctrine Tree per-org state (owner-ratified 2026-07-15)
    }
)


# T005: import-time partition integrity assertion.
# A new System added to _DEFAULT_SYSTEMS without classification raises
# AssertionError on the next test collection.
_ALL_PARTITIONED: Final[frozenset[type[System]]] = (
    MATERIAL_BASE_SYSTEMS | ACTION_PHASE_SYSTEMS | CONSEQUENCE_SYSTEMS
)
_DEFAULT_SYSTEM_TYPES: Final[frozenset[type[System]]] = frozenset(type(s) for s in _DEFAULT_SYSTEMS)
if _ALL_PARTITIONED != _DEFAULT_SYSTEM_TYPES:
    raise RuntimeError(
        f"Spec 056 partition drift: System(s) "
        f"{_DEFAULT_SYSTEM_TYPES ^ _ALL_PARTITIONED} are in _DEFAULT_SYSTEMS "
        f"but not classified into MATERIAL_BASE_SYSTEMS / ACTION_PHASE_SYSTEMS "
        f"/ CONSEQUENCE_SYSTEMS (or vice versa). Add the new System(s) to "
        f"exactly one of the three sets in simulation_engine.py."
    )
if not MATERIAL_BASE_SYSTEMS.isdisjoint(ACTION_PHASE_SYSTEMS):
    raise RuntimeError(
        "Spec 056 partition violation: MATERIAL_BASE_SYSTEMS and ACTION_PHASE_SYSTEMS overlap"
    )
if not MATERIAL_BASE_SYSTEMS.isdisjoint(CONSEQUENCE_SYSTEMS):
    raise RuntimeError(
        "Spec 056 partition violation: MATERIAL_BASE_SYSTEMS and CONSEQUENCE_SYSTEMS overlap"
    )
if not ACTION_PHASE_SYSTEMS.isdisjoint(CONSEQUENCE_SYSTEMS):
    raise RuntimeError(
        "Spec 056 partition violation: ACTION_PHASE_SYSTEMS and CONSEQUENCE_SYSTEMS overlap"
    )

_DEFAULT_ENGINE = SimulationEngine(_DEFAULT_SYSTEMS)


def _convert_bus_event_to_pydantic(event: Event) -> SimulationEvent | None:  # noqa: C901
    """Convert EventBus Event to typed Pydantic SimulationEvent.

    Args:
        event: The EventBus Event dataclass with type, tick, payload.

    Returns:
        A typed SimulationEvent subclass, or None if unsupported event type.

    Note:
        This function handles graceful degradation - unsupported event types
        return None rather than raising an error. The caller should filter
        out None values.

    Sprint 3.1+: Supports all 10 EventTypes except SOLIDARITY_AWAKENING.
    Program 17 item 1b: widened to 34 of 79 EventTypes.
    Wave 1 item W1.1: widened to 44 of 79 EventTypes.
    Unit 6a (ADR073): widened to 47 of 82 EventTypes (DOCTRINE_TRAP_SPRUNG /
    DOCTRINE_TRAP_ESCAPED / DOCTRINE_PURGE_FAILED).
    """
    # Normalize event type (may be string or EventType enum)
    event_type = event.type
    if isinstance(event_type, str):
        try:
            event_type = EventType(event_type)
        except ValueError:
            return None

    tick = event.tick
    timestamp = event.timestamp
    payload = event.payload

    # Economic Events
    if event_type == EventType.SURPLUS_EXTRACTION:
        return ExtractionEvent(
            tick=tick,
            timestamp=timestamp,
            source_id=payload.get("source_id", ""),
            target_id=payload.get("target_id", ""),
            amount=payload.get("amount", 0.0),
            mechanism=payload.get("mechanism", "imperial_rent"),
        )

    if event_type == EventType.IMPERIAL_SUBSIDY:
        return SubsidyEvent(
            tick=tick,
            timestamp=timestamp,
            source_id=payload.get("source_id", ""),
            target_id=payload.get("target_id", ""),
            amount=payload.get("amount", 0.0),
            repression_boost=payload.get("repression_boost", 0.0),
        )

    if event_type == EventType.ECONOMIC_CRISIS:
        return CrisisEvent(
            tick=tick,
            timestamp=timestamp,
            pool_ratio=payload.get("pool_ratio", 0.0),
            aggregate_tension=payload.get("aggregate_tension", 0.0),
            decision=payload.get("decision", "UNKNOWN"),
            wage_delta=payload.get("wage_delta", 0.0),
        )

    # Consciousness Events
    if event_type == EventType.CONSCIOUSNESS_TRANSMISSION:
        return TransmissionEvent(
            tick=tick,
            timestamp=timestamp,
            source_id=payload.get("source_id", ""),
            target_id=payload.get("target_id", ""),
            delta=payload.get("delta", 0.0),
            solidarity_strength=payload.get("solidarity_strength", 0.0),
        )

    if event_type == EventType.MASS_AWAKENING:
        return MassAwakeningEvent(
            tick=tick,
            timestamp=timestamp,
            target_id=payload.get("target_id", ""),
            old_consciousness=payload.get("old_consciousness", 0.0),
            new_consciousness=payload.get("new_consciousness", 0.0),
            triggering_source=payload.get("triggering_source", ""),
        )

    # Struggle Events (Agency Layer - George Floyd Dynamic)
    if event_type == EventType.EXCESSIVE_FORCE:
        return SparkEvent(
            tick=tick,
            timestamp=timestamp,
            node_id=payload.get("node_id", ""),
            repression=payload.get("repression", 0.0),
            spark_probability=payload.get("spark_probability", 0.0),
        )

    if event_type == EventType.UPRISING:
        return UprisingEvent(
            tick=tick,
            timestamp=timestamp,
            node_id=payload.get("node_id", ""),
            trigger=payload.get("trigger", "unknown"),
            agitation=payload.get("agitation", 0.0),
            repression=payload.get("repression", 0.0),
        )

    if event_type == EventType.SOLIDARITY_SPIKE:
        return SolidaritySpikeEvent(
            tick=tick,
            timestamp=timestamp,
            node_id=payload.get("node_id", ""),
            solidarity_gained=payload.get("solidarity_gained", 0.0),
            edges_affected=payload.get("edges_affected", 0),
            triggered_by=payload.get("triggered_by", "unknown"),
        )

    # Contradiction Events
    if event_type == EventType.RUPTURE:
        # Lawverian (Phase C1): frame-level payload {opposition, gap, rate};
        # ``edge`` retained (default "") for older per-edge callers.
        return RuptureEvent(
            tick=tick,
            timestamp=timestamp,
            edge=payload.get("edge", ""),
            opposition=payload.get("opposition", ""),
            gap=payload.get("gap", 0.0),
            rate=payload.get("rate", 0.0),
        )

    # Topology Events (Sprint 3.3)
    if event_type == EventType.PHASE_TRANSITION:
        return PhaseTransitionEvent(
            tick=tick,
            timestamp=timestamp,
            previous_state=payload.get("previous_state", ""),
            new_state=payload.get("new_state", ""),
            percolation_ratio=payload.get("percolation_ratio", 0.0),
            num_components=payload.get("num_components", 0),
            largest_component_size=payload.get("largest_component_size", 0),
            cadre_density=payload.get("cadre_density", 0.0),
            is_resilient=payload.get("is_resilient"),
        )

    # Carceral Equilibrium Events (Sprint 3.4+)
    if event_type == EventType.SUPERWAGE_CRISIS:
        return SuperwageCrisisEvent(
            tick=tick,
            timestamp=timestamp,
            payer_id=payload.get("payer_id", ""),
            receiver_id=payload.get("receiver_id", ""),
            desired_wages=payload.get("desired_wages", 0.0),
            available_pool=payload.get("available_pool", 0.0),
        )

    if event_type == EventType.CLASS_DECOMPOSITION:
        return ClassDecompositionEvent(
            tick=tick,
            timestamp=timestamp,
            original_id=payload.get("source_class", ""),  # Field name from decomposition.py
            enforcer_fraction=payload.get("enforcer_fraction", 0.3),
            proletariat_fraction=payload.get("proletariat_fraction", 0.7),
        )

    if event_type == EventType.CONTROL_RATIO_CRISIS:
        return ControlRatioCrisisEvent(
            tick=tick,
            timestamp=timestamp,
            prisoner_population=payload.get("prisoner_population", 0),
            enforcer_population=payload.get("enforcer_population", 0),
            control_ratio=payload.get("control_ratio", 0.0),
            capacity_threshold=payload.get("capacity_threshold", 0.0),
        )

    if event_type == EventType.TERMINAL_DECISION:
        return TerminalDecisionEvent(
            tick=tick,
            timestamp=timestamp,
            outcome=payload.get("outcome", "genocide"),
            avg_organization=payload.get("avg_organization", 0.0),
            revolution_threshold=payload.get("revolution_threshold", 0.0),
        )

    # Spec-070 Balkanization events (Program 17 item 1b)
    if event_type == EventType.SOVEREIGN_COLLAPSE:
        return SovereignCollapsePayload(
            tick=tick,
            timestamp=timestamp,
            sovereign_id=payload.get("sovereign_id", ""),
            trigger=payload.get("trigger", "legitimacy_zero"),
            claimed_territories_count=payload.get("claimed_territories_count", 0),
        )

    if event_type == EventType.TERRITORY_TRANSITION:
        return TerritoryTransitionPayload(
            tick=tick,
            timestamp=timestamp,
            territory_id=payload.get("territory_id", ""),
            from_sovereign_id=payload.get("from_sovereign_id"),
            to_sovereign_id=payload.get("to_sovereign_id"),
            from_winning_faction_id=payload.get("from_winning_faction_id"),
            to_winning_faction_id=payload.get("to_winning_faction_id"),
            reason=payload.get("reason", "influence_flip"),
        )

    if event_type == EventType.FACTION_VICTORY:
        return FactionVictoryPayload(
            tick=tick,
            timestamp=timestamp,
            faction_id=payload.get("faction_id", ""),
            aggregate_influence_share=payload.get("aggregate_influence_share", 0.0),
        )

    if event_type == EventType.CIVIL_WAR_DECLARED:
        return CivilWarDeclaredPayload(
            tick=tick,
            timestamp=timestamp,
            parent_sovereign_id=payload.get("parent_sovereign_id", ""),
            secessionist_faction_id=payload.get("secessionist_faction_id", ""),
            contested_territory_count=payload.get("contested_territory_count", 0),
        )

    if event_type == EventType.RED_SETTLER_TRAP_DETECTED:
        return RedSettlerTrapDetectedPayload(
            tick=tick,
            timestamp=timestamp,
            faction_id=payload.get("faction_id", ""),
            class_reduction=payload.get("class_reduction", 0.0),
            colonial_stance=payload.get("colonial_stance", "uphold"),
        )

    if event_type == EventType.DUAL_POWER_ACTIVE:
        return DualPowerActivePayload(
            tick=tick,
            timestamp=timestamp,
            territory_id=payload.get("territory_id", ""),
            competing_sovereign_ids=tuple(payload.get("competing_sovereign_ids", ())),
            control_level_sum=payload.get("control_level_sum", 0.0),
        )

    # Spec-071 reactionary/fascist-drift events (Program 17 item 1b)
    if event_type == EventType.FASCIST_DRIFT:
        return FascistDriftEvent(
            tick=tick,
            timestamp=timestamp,
            node_id=payload.get("node_id", ""),
            fascist_pull=payload.get("fascist_pull", 0.0),
            fascist_alignment=payload.get("fascist_alignment", 0.0),
            entitlement=payload.get("entitlement", 0.0),
            solidarity=payload.get("solidarity", 0.0),
            regime=payload.get("regime"),
        )

    if event_type == EventType.FASCIST_RECRUITMENT:
        return FascistRecruitmentEvent(
            tick=tick,
            timestamp=timestamp,
            node_id=payload.get("node_id", ""),
            faction_id=payload.get("faction_id", ""),
            fascist_alignment=payload.get("fascist_alignment", 0.0),
        )

    if event_type == EventType.ORGANIZATIONAL_FRACTURE:
        return OrganizationalFractureEvent(
            tick=tick,
            timestamp=timestamp,
            org_id=payload.get("org_id", ""),
            member_id=payload.get("member_id", ""),
            chauvinism=payload.get("chauvinism", 0.0),
            defection_probability=payload.get("defection_probability", 0.0),
        )

    if event_type == EventType.RED_BROWN_COUP:
        return RedBrownCoupEvent(
            tick=tick,
            timestamp=timestamp,
            org_id=payload.get("org_id", ""),
            defections=payload.get("defections", 0),
            member_count=payload.get("member_count", 0),
        )

    # Feature-030 lifecycle/legitimation/inheritance events (Program 17 item 1b)
    if event_type == EventType.LIFECYCLE_TRANSITION:
        return LifecycleTransitionEvent(
            tick=tick,
            timestamp=timestamp,
            territory_id=payload.get("territory_id", ""),
            pop_d=payload.get("pop_d", 0.0),
            pop_p=payload.get("pop_p", 0.0),
            pop_d_prime=payload.get("pop_d_prime", 0.0),
            dependency_ratio=payload.get("dependency_ratio", 0.0),
        )

    if event_type == EventType.LEGITIMATION_CRISIS:
        return LegitimationCrisisEvent(
            tick=tick,
            timestamp=timestamp,
            territory_id=payload.get("territory_id", ""),
            legitimation_index=payload.get("legitimation_index", 0.0),
        )

    if event_type == EventType.LEGITIMATION_RECOVERY:
        return LegitimationRecoveryEvent(
            tick=tick,
            timestamp=timestamp,
            territory_id=payload.get("territory_id", ""),
            legitimation_index=payload.get("legitimation_index", 0.0),
        )

    if event_type == EventType.INHERITANCE_TRANSFER:
        return InheritanceTransferEvent(
            tick=tick,
            timestamp=timestamp,
            territory_id=payload.get("territory_id", ""),
            total_transferred=payload.get("total_transferred", 0.0),
            care_consumed=payload.get("care_consumed", 0.0),
            net_inheritance=payload.get("net_inheritance", 0.0),
            inheritance_gini=payload.get("inheritance_gini", 0.0),
        )

    # Feature-040 institution events (Program 17 item 1b) - dead-until-wired,
    # see institution_payloads.py module docstring.
    if event_type == EventType.INSTITUTION_FACTION_SHIFT:
        return InstitutionFactionShiftEvent(
            tick=tick,
            timestamp=timestamp,
            institution_id=payload.get("institution_id", ""),
            old_fraction=payload.get("old_fraction", ""),
            new_fraction=payload.get("new_fraction", ""),
            weights=payload.get("weights", {}),
        )

    if event_type == EventType.INSTITUTION_BONAPARTIST_MODE:
        return InstitutionBonapartistModeEvent(
            tick=tick,
            timestamp=timestamp,
            institution_id=payload.get("institution_id", ""),
            bonapartist_weight=payload.get("bonapartist_weight", 0.0),
        )

    # Feature-002 contradiction-field event (Program 17 item 1b)
    if event_type == EventType.PRINCIPAL_CONTRADICTION_SHIFT:
        return PrincipalContradictionShiftEvent(
            tick=tick,
            timestamp=timestamp,
            previous_field=payload.get("previous_field"),
            new_field=payload.get("new_field", ""),
            max_abs_df_dt=payload.get("max_abs_df_dt", 0.0),
        )

    # Feature-032 OODA events (Program 17 item 1b) - STATE_REPRESSION/
    # STATE_SURVEILLANCE are speculative, see ooda_payloads.py module docstring.
    if event_type == EventType.ORGANIZATIONAL_ACTION:
        return OrganizationalActionEvent(
            tick=tick,
            timestamp=timestamp,
            layer0_count=payload.get("layer0_count", 0),
            action_count=payload.get("action_count", 0),
            org_count=payload.get("org_count", 0),
        )

    if event_type == EventType.STATE_REPRESSION:
        return StateRepressionEvent(
            tick=tick,
            timestamp=timestamp,
            org_id=payload.get("org_id", ""),
            target_id=payload.get("target_id", ""),
            backfire_delta=payload.get("backfire_delta", 0.0),
        )

    if event_type == EventType.STATE_SURVEILLANCE:
        return StateSurveillanceEvent(
            tick=tick,
            timestamp=timestamp,
            org_id=payload.get("org_id", ""),
            target_id=payload.get("target_id", ""),
            backfire_delta=payload.get("backfire_delta", 0.0),
        )

    # Wave 1 item W1.1 struggle-system events (Program 17 / struggle.py)
    if event_type == EventType.POWER_VACUUM:
        return PowerVacuumEvent(
            tick=tick,
            timestamp=timestamp,
            comprador_id=payload.get("comprador_id", ""),
            comprador_wealth=payload.get("comprador_wealth", 0.0),
            subsistence_threshold=payload.get("subsistence_threshold", 0.0),
            revolutionary_capacity=payload.get("revolutionary_capacity", 0.0),
            jackson_threshold=payload.get("jackson_threshold", 0.0),
        )

    if event_type == EventType.REVOLUTIONARY_OFFENSIVE:
        return RevolutionaryOffensiveEvent(
            tick=tick,
            timestamp=timestamp,
            periphery_id=payload.get("periphery_id", ""),
            revolutionary_capacity=payload.get("revolutionary_capacity", 0.0),
            agitation_boost=payload.get("agitation_boost", 0.0),
            narrative_hint=payload.get("narrative_hint", ""),
        )

    if event_type == EventType.FASCIST_REVANCHISM:
        return FascistRevanchismEvent(
            tick=tick,
            timestamp=timestamp,
            core_worker_id=payload.get("core_worker_id"),
            revolutionary_capacity=payload.get("revolutionary_capacity", 0.0),
            identity_boost=payload.get("identity_boost", 0.0),
            acquiescence_boost=payload.get("acquiescence_boost", 0.0),
            narrative_hint=payload.get("narrative_hint", ""),
        )

    if event_type == EventType.SPONTANEOUS_RIOT:
        return SpontaneousRiotEvent(
            tick=tick,
            timestamp=timestamp,
            node_id=payload.get("node_id", ""),
            volatility=payload.get("volatility", 0.0),
            organizational_discipline=payload.get("organizational_discipline", 0.0),
            riot_risk=payload.get("riot_risk", 0.0),
            wealth_before=payload.get("wealth_before", 0.0),
            wealth_after=payload.get("wealth_after", 0.0),
            narrative_hint=payload.get("narrative_hint", ""),
        )

    if event_type == EventType.PERIPHERAL_REVOLT:
        return PeripheralRevoltEvent(
            tick=tick,
            timestamp=timestamp,
            node_id=payload.get("node_id", ""),
            edges_severed=payload.get("edges_severed", 0),
            p_acquiescence=payload.get("p_acquiescence", 0.0),
            p_revolution=payload.get("p_revolution", 0.0),
            capital_labor_gap=payload.get("capital_labor_gap", 0.0),
            narrative_hint=payload.get("narrative_hint", ""),
        )

    # Wave 1 item W1.1 dispossession/reserve-army/metabolism events
    if event_type == EventType.DISPOSSESSION_EVENT:
        return DispossessionEvent(
            tick=tick,
            timestamp=timestamp,
            territory=payload.get("territory", ""),
            intensity=payload.get("intensity", 0.0),
            foreclosure_rate=payload.get("foreclosure_rate", 0.0),
            eviction_rate=payload.get("eviction_rate", 0.0),
            displacement_rate=payload.get("displacement_rate", 0.0),
        )

    if event_type == EventType.VALUE_TRANSFER:
        return ValueTransferEvent(
            tick=tick,
            timestamp=timestamp,
            territory=payload.get("territory", ""),
            total_transferred=payload.get("total_transferred", 0.0),
            net_received=payload.get("net_received", 0.0),
            deadweight_loss=payload.get("deadweight_loss", 0.0),
        )

    if event_type == EventType.RESERVE_ARMY_PRESSURE:
        return ReserveArmyPressureEvent(
            tick=tick,
            timestamp=timestamp,
            territory=payload.get("territory", ""),
            reserve_ratio=payload.get("reserve_ratio", 0.0),
            wage_pressure=payload.get("wage_pressure", 0.0),
            median_wage=payload.get("median_wage", 0.0),
        )

    # DISPOSSESSION_CASCADE's live publish site (TickDynamicsSystem) emits
    # ``EventType.DISPOSSESSION_CASCADE.value`` (a string), not the enum
    # member; the isinstance(str) normalization at the top of this function
    # already converts it back to the enum before this comparison runs.
    if event_type == EventType.DISPOSSESSION_CASCADE:
        return DispossessionCascadeEvent(
            tick=tick,
            timestamp=timestamp,
            fips=payload.get("fips", ""),
            cumulative_la_decline=payload.get("cumulative_la_decline", 0.0),
            milestone_crossed=payload.get("milestone_crossed", 0.0),
            current_la_share=payload.get("current_la_share", 0.0),
            baseline_la_share=payload.get("baseline_la_share", 0.0),
        )

    if event_type == EventType.ECOLOGICAL_OVERSHOOT:
        return EcologicalOvershootEvent(
            tick=tick,
            timestamp=timestamp,
            overshoot_ratio=payload.get("overshoot_ratio", 0.0),
            total_consumption=payload.get("total_consumption", 0.0),
            total_biocapacity=payload.get("total_biocapacity", 0.0),
        )

    # ADR073 Doctrine Tree events (Unit 6a — doctrine.py::DoctrineSystem.step)
    if event_type == EventType.DOCTRINE_TRAP_SPRUNG:
        return DoctrineTrapSprungEvent(
            tick=tick,
            timestamp=timestamp,
            org_id=payload.get("org_id", ""),
            node_id=payload.get("node_id", ""),
        )

    if event_type == EventType.DOCTRINE_TRAP_ESCAPED:
        return DoctrineTrapEscapedEvent(
            tick=tick,
            timestamp=timestamp,
            org_id=payload.get("org_id", ""),
            node_id=payload.get("node_id", ""),
        )

    if event_type == EventType.DOCTRINE_PURGE_FAILED:
        return DoctrinePurgeFailedEvent(
            tick=tick,
            timestamp=timestamp,
            org_id=payload.get("org_id", ""),
            node_id=payload.get("node_id", ""),
        )

    # Feature 002 events (EDGE_MODE_TRANSITION, CO_OPTIVE_BREAKDOWN,
    # LATENT_CONTRADICTION_RELEASE, ASPECT_REVERSAL) and other unsupported
    # event types - graceful degradation
    return None


def _restore_graph_context(
    G: BabylonGraph,
    persistent_context: dict[str, Any] | None,
) -> None:
    """Restore graph-level state from persistent_context before systems run.

    Feature 020: TickDynamicsSystem writes tick_dynamics to graph.graph, but
    it's lost during the WorldState round-trip (to_graph/from_graph). We
    persist it in the context dict so it survives across ticks.
    """
    if not persistent_context:
        return
    if "_base_year" in persistent_context:
        G.graph["base_year"] = persistent_context["_base_year"]
    if "_tick_dynamics" in persistent_context:
        G.graph["tick_dynamics"] = persistent_context["_tick_dynamics"]


def _save_graph_context(
    G: BabylonGraph,
    persistent_context: dict[str, Any] | None,
    tick: int,
) -> None:
    """Save tick_dynamics from graph into persistent_context after systems run.

    Feature 020: Persists tick_dynamics so it survives the WorldState round-trip.
    Also accumulates year-boundary snapshots for get_time_series().
    """
    if persistent_context is None or "tick_dynamics" not in G.graph:
        return
    tick_dynamics_data = G.graph["tick_dynamics"]
    persistent_context["_tick_dynamics"] = tick_dynamics_data
    # Accumulate snapshots at year boundaries for time series extraction
    if tick % 52 == 0:
        snapshots: list[dict[str, Any]] = persistent_context.setdefault(
            "_tick_dynamics_snapshots", []
        )
        snapshots.append(tick_dynamics_data)


def step(
    state: WorldState,
    config: SimulationConfig,
    persistent_context: dict[str, Any] | None = None,
    defines: GameDefines | None = None,
    calculator_overrides: dict[str, Any] | None = None,
) -> WorldState:
    """Advance simulation by one tick using the modular engine.

    This is the heart of Phase 2. It transforms a WorldState through
    one tick of simulated time by applying the MLM-TW formulas.

    Args:
        state: Current world state (immutable)
        config: Simulation configuration with formula coefficients
        persistent_context: Optional context dict that persists across ticks.
            Used by systems that need to track state between ticks (e.g.,
            ConsciousnessSystem's previous_wages for bifurcation mechanic).
        defines: Optional custom GameDefines. If None, loads from default
            defines.yaml location. Use this for scenario-specific calibration.
        calculator_overrides: Optional dict of calculator instances to inject
            into ServiceContainer (e.g., melt_calculator, tensor_registry).

    Returns:
        New WorldState at tick + 1

    Order encodes historical materialism:
        1. Economic base (value extraction)
        2. Consciousness (responds to material conditions)
        3. Survival calculus (probability updates)
        4. Contradictions (tension from all above)
        5. Event capture (log significant changes)
    """
    # Short-circuit for empty state (no entities AND no territories)
    # Skip short-circuit when calculator_overrides are present (Feature 020):
    # TickDynamicsSystem can still compute economic state from TensorRegistry
    # even without traditional entity/territory nodes in the graph.
    if not state.entities and not state.territories and not calculator_overrides:
        return state.model_copy(update={"tick": state.tick + 1})

    # Cost-checking: Log warnings for insolvent states (Epoch 1: The Ledger)
    for state_id, finance in state.state_finances.items():
        if finance.treasury < finance.burn_rate:
            logger.warning(
                f"State {state_id} treasury ({finance.treasury:.2f}) < "
                f"burn_rate ({finance.burn_rate:.2f})"
            )

    # Convert to mutable graph for system application
    G = state.to_graph()
    events: list[str] = list(state.event_log)

    # Feature 020: Restore graph-level state from persistent_context
    _restore_graph_context(G, persistent_context)

    # Create ServiceContainer for this tick
    # Use provided defines, or load from default YAML
    effective_defines = defines if defines is not None else GameDefines.load_default()
    overrides = calculator_overrides or {}
    services = ServiceContainer.create(config, effective_defines, **overrides)

    # Create typed TickContext for this tick
    # persistent_data is initialized from caller's persistent_context if provided
    context = TickContext(
        tick=state.tick,
        persistent_data=dict(persistent_context) if persistent_context else {},
    )

    # Run all systems through the engine
    _DEFAULT_ENGINE.run_tick(G, services, context)

    # Feature 020: Persist tick_dynamics for WorldState round-trip survival
    _save_graph_context(G, persistent_context, state.tick)

    # Sync any changes from context.persistent_data back to caller's dict
    if persistent_context is not None:
        for key, value in context.persistent_data.items():
            persistent_context[key] = value

    # Convert EventBus history to both string log and typed events
    structured_events: list[SimulationEvent] = []
    for event in services.event_bus.get_history():
        # String log for backward compatibility
        events.append(f"Tick {event.tick + 1}: {event.type.upper()}")
        # Typed Pydantic event (Sprint 3.1)
        pydantic_event = _convert_bus_event_to_pydantic(event)
        if pydantic_event is not None:
            structured_events.append(pydantic_event)

    # Include observer events from previous tick (Sprint 3.3)
    # Observer events are emitted AFTER WorldState is frozen, so they
    # appear in the NEXT tick's events via persistent_context
    if persistent_context is not None:
        observer_events = persistent_context.get("_observer_events", [])
        if observer_events:
            # Type assertion: observer_events is list[SimulationEvent]
            for obs_event in observer_events:
                if isinstance(obs_event, SimulationEvent):
                    structured_events.append(obs_event)
            # Clear the observer events after injection
            del persistent_context["_observer_events"]

    # Reconstruct state from modified graph
    return WorldState.from_graph(
        G,
        tick=state.tick + 1,
        event_log=events,
        events=structured_events,
    )
