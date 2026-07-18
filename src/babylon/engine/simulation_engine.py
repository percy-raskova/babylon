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
from babylon.engine.event_builders import EVENT_BUILDERS
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
from babylon.engine.systems.market_scissors import MarketScissorsSystem
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
from babylon.kernel.system_base import SystemBase
from babylon.kernel.system_protocol import ContextType, System
from babylon.kernel.tick_partition import TickPartition
from babylon.models.config import SimulationConfig
from babylon.models.enums import EventType
from babylon.models.events import (
    SimulationEvent,
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
            context: TickContext passed to all systems

        Spec 008: Logs within run_tick() include tick and correlation_id.
        """
        # T025: Extract the tick number from the TickContext.
        tick = context.tick

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
        session_id = context.session_id if hasattr(context, "session_id") else None
        if session_id is None:
            # Without a session_id the auditor cannot tag rows; skip silently.
            return

        # Reconstruct hex rows from graph for the determinism hash. The
        # auditor is robust to empty iterables (returns empty rows list).
        hex_rows = [
            attrs for _node, attrs in graph.nodes(data=True) if attrs.get("_node_type") == "hex"
        ]
        # Legacy dict contexts could carry an "actions" list; the TickContext
        # path never populated one, so this stays None (byte-identical).
        action_list = None

        rows, alarms = self._auditor.evaluate(
            session_id=session_id,
            tick=tick,
            hex_rows=hex_rows,
            post_state=graph,
            action_list=action_list,
        )

        # Stash rows on the context's persistent_data so the envelope builder
        # (and the run_tick auditor tests) can pick them up via
        # ``context.get("audit_rows")`` — TickContext routes non-field bracket
        # keys through persistent_data. Production's headless bridge calls the
        # auditor directly; this exposes rows on the run_tick path.
        context.persistent_data.setdefault("audit_rows", []).extend(rows)

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
#: The engine's System registry — MEMBERSHIP only. The tick ORDER and the three
#: partition frozensets below are DERIVED from each System's ``position`` /
#: ``partition`` ClassVars (spec-116 Phase 4 / ADR081), so a System's ordering
#: metadata lives on the System rather than being restated in a hand-ordered
#: list plus three hand-maintained sets. Adding a System: append its class here
#: and declare the two ClassVars on it — everything below follows. (The
#: canonical order + rationale is the comment block above.)
_SYSTEM_CLASSES: Final[tuple[type[SystemBase], ...]] = (
    VitalitySystem,
    TerritorySystem,
    SubstrateSystem,
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
    OODASystem,
    FactionInfluenceSystem,
    DoctrineSystem,
    SurvivalSystem,
    StruggleSystem,
    ConsciousnessSystem,
    FascistFactionSystem,
    SovereigntySystem,
    MarketScissorsSystem,
    ContradictionSystem,
    ContradictionFieldSystem,
    FieldDerivativeSystem,
    CollapseTransitionSystem,
    EdgeTransitionSystem,
    WealthDistributionSystem,
    EpistemicHorizonSystem,
)

# Distinct positions => a stable, unambiguous total order (Constitution III.7).
_SYSTEM_POSITIONS: Final[list[float]] = [cls.position for cls in _SYSTEM_CLASSES]
if len(set(_SYSTEM_POSITIONS)) != len(_SYSTEM_POSITIONS):
    _dupe_positions = sorted({p for p in _SYSTEM_POSITIONS if _SYSTEM_POSITIONS.count(p) > 1})
    raise RuntimeError(
        f"Duplicate System position(s) {_dupe_positions}: the tick order would "
        f"be ambiguous. Give each registered System a distinct `position`."
    )

#: The Systems in strict materialist-causality order (ADR032), DERIVED by sorting
#: the registry on each System's `position` ClassVar.
_DEFAULT_SYSTEMS: list[System] = [
    cls() for cls in sorted(_SYSTEM_CLASSES, key=lambda c: c.position)
]


def _partition_members(partition: TickPartition) -> frozenset[type[System]]:
    """Registry classes declaring ``partition`` (the spec-056 FR-002 sets)."""
    return frozenset(cls for cls in _SYSTEM_CLASSES if cls.partition is partition)


# Spec 056 (FR-002): the three canonical sets partitioning the tick — now DERIVED
# from the per-System `partition` ClassVar (were three hand-maintained frozensets
# kept in sync with `_DEFAULT_SYSTEMS` by import-time assertions). By construction
# they partition `_SYSTEM_CLASSES` exactly and are pairwise disjoint (each System
# declares exactly one partition), so the old drift/overlap assertions are obsolete.
MATERIAL_BASE_SYSTEMS: Final[frozenset[type[System]]] = _partition_members(
    TickPartition.MATERIAL_BASE
)
ACTION_PHASE_SYSTEMS: Final[frozenset[type[System]]] = _partition_members(TickPartition.ACTION)
CONSEQUENCE_SYSTEMS: Final[frozenset[type[System]]] = _partition_members(TickPartition.CONSEQUENCE)

# Belt-and-suspenders: every registered System landed in exactly one partition.
_PARTITIONED_COUNT: Final[int] = (
    len(MATERIAL_BASE_SYSTEMS) + len(ACTION_PHASE_SYSTEMS) + len(CONSEQUENCE_SYSTEMS)
)
if len(_SYSTEM_CLASSES) != _PARTITIONED_COUNT:  # pragma: no cover — TickPartition has 3 members
    raise RuntimeError(
        "TickPartition coverage gap: a registered System declares a partition "
        "outside MATERIAL_BASE / ACTION / CONSEQUENCE."
    )

_DEFAULT_ENGINE = SimulationEngine(_DEFAULT_SYSTEMS)


def _convert_bus_event_to_pydantic(event: Event) -> SimulationEvent | None:
    """Convert an EventBus Event to a typed Pydantic SimulationEvent.

    Thin dispatcher over :data:`babylon.engine.event_builders.EVENT_BUILDERS`.
    Unsupported or unregistered EventTypes return ``None`` (graceful
    degradation — callers filter ``None``); an unknown event-type string
    returns ``None`` too. The per-EventType construction logic lives in
    :mod:`babylon.engine.event_builders`.

    :param event: The EventBus Event dataclass with type, tick, payload.
    :returns: A typed SimulationEvent subclass, or ``None`` if unconvertible.
    """
    raw_type = event.type
    if isinstance(raw_type, EventType):
        event_type = raw_type
    else:
        try:
            event_type = EventType(raw_type)
        except ValueError:
            return None
    builder = EVENT_BUILDERS.get(event_type)
    if builder is None:
        return None
    return builder(event.tick, event.timestamp, event.payload)


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
