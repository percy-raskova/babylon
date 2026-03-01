"""Simulation facade class for running multi-tick simulations.

This module provides a Simulation class that wraps the ServiceContainer
and step() function, providing a convenient API for:
- Running simulations over multiple ticks
- Preserving history of all WorldState snapshots
- Maintaining a persistent ServiceContainer across ticks
- Observer pattern for AI narrative generation (Sprint 3.1)

Observer Pattern Integration (Sprint 3.1):
- Observers are registered via constructor or add_observer()
- Notifications occur AFTER state reconstruction (per design decision)
- Observer errors are logged but don't halt simulation (ADR003)
- Lifecycle hooks: on_simulation_start, on_tick, on_simulation_end

MVP Simulation Engine (001-mvp-sim-engine):
- Implements SimulationState and SimulationControl protocols
- Tracks territory profit_rate for GUI visualization
- Provides get_snapshot(), get_territory_state(), reset() methods
- Deterministic profit_rate decay toward territory-specific equilibrium
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import h3

from babylon.config.defines import GameDefines
from babylon.engine.observer_adapter import ProtocolObserverAdapter
from babylon.engine.services import ServiceContainer
from babylon.engine.simulation_engine import step
from babylon.models.config import SimulationConfig
from babylon.models.enums import GameOutcome
from babylon.models.snapshots import (
    HexState,
    SimulationSnapshot,
    TerritoryState,
)
from babylon.models.world_state import WorldState

if TYPE_CHECKING:
    from babylon.economics.tensor_registry import TensorRegistry
    from babylon.engine.observer import SimulationObserver
    from babylon.protocols import ObserverCallback

logger = logging.getLogger(__name__)


class Simulation:
    """Facade class for running multi-tick simulations with history preservation.

    The Simulation class provides a stateful wrapper around the pure step() function,
    managing:
    - Current WorldState
    - History of all previous states
    - Persistent ServiceContainer for dependency injection
    - Observer notifications for AI/narrative components (Sprint 3.1)

    Example:
        >>> from babylon.engine.factories import create_proletariat, create_bourgeoisie
        >>> from babylon.models import WorldState, SimulationConfig, Relationship, EdgeType
        >>>
        >>> worker = create_proletariat()
        >>> owner = create_bourgeoisie()
        >>> exploitation = Relationship(
        ...     source_id=worker.id, target_id=owner.id,
        ...     edge_type=EdgeType.EXPLOITATION
        ... )
        >>> state = WorldState(entities={worker.id: worker, owner.id: owner},
        ...                    relationships=[exploitation])
        >>> config = SimulationConfig()
        >>>
        >>> sim = Simulation(state, config)
        >>> sim.run(100)
        >>> print(f"Worker wealth after 100 ticks: {sim.current_state.entities[worker.id].wealth}")

    With observers:
        >>> from babylon.ai import NarrativeDirector
        >>> director = NarrativeDirector()
        >>> sim = Simulation(state, config, observers=[director])
        >>> sim.run(10)
        >>> sim.end()  # Triggers on_simulation_end
    """

    def __init__(
        self,
        initial_state: WorldState,
        config: SimulationConfig,
        observers: list[SimulationObserver] | None = None,
        defines: GameDefines | None = None,
        tensor_registry: TensorRegistry | None = None,
        calculator_overrides: dict[str, Any] | None = None,
    ) -> None:
        """Initialize simulation with initial state and configuration.

        Args:
            initial_state: Starting WorldState at tick 0
            config: Simulation configuration with formula coefficients
            observers: Optional list of SimulationObserver instances to notify
            defines: Optional custom GameDefines for scenario-specific coefficients.
                     If None, loads from default defines.yaml location.
            tensor_registry: Optional TensorRegistry for cached tensor data access.
                     If None, tensor data is not available. If provided, it should
                     be pre-hydrated with the relevant counties and years.
            calculator_overrides: Optional dict of calculator instances to inject
                     into ServiceContainer on each tick (Feature 020).
        """
        self._config = config
        self._defines = defines if defines is not None else GameDefines.load_default()
        self._services = ServiceContainer.create(config, self._defines)
        self._current_state = initial_state
        self._history: list[WorldState] = [initial_state]
        self._observers: list[SimulationObserver] = list(observers or [])
        self._started = False
        # Persistent context that spans across ticks (Sprint 3.4.3)
        # Used for tracking state between ticks like previous_wages
        self._persistent_context: dict[str, object] = {}

        # MVP Simulation Engine: Territory state tracking
        # These are separate from WorldState.territories for GUI-facing snapshot creation
        self._mvp_territories: dict[str, TerritoryState] = {}
        self._mvp_hexes: dict[str, HexState] = {}
        # Cache initial state for reset() functionality
        self._initial_mvp_territories: dict[str, TerritoryState] = {}
        self._initial_mvp_hexes: dict[str, HexState] = {}
        self._initial_world_state: WorldState = initial_state

        # Fundamental Tensor Primitive (011): Cached economic tensor access
        # Provides read-only access to labor-hour tensors without database queries
        self._tensor_registry: TensorRegistry | None = tensor_registry

        # Detroit Vertical Slice (020): Calculator overrides for step()
        # When set, these are passed to step() to inject real calculators
        self._calculator_overrides: dict[str, Any] | None = calculator_overrides

        # Detroit Vertical Slice (020): Base year for multi-year simulations
        # Used by TickDynamicsSystem to determine current simulation year
        self._base_year: int | None = None

        # GUI Protocol Extension (006): Thread-safe observer adapter
        # Callbacks receive frozen SimulationSnapshot, not live references
        self._adapter = ProtocolObserverAdapter(self)

    @classmethod
    def from_sqlite(
        cls,
        fips_codes: list[str],
        year: int = 2022,
        observers: list[SimulationObserver] | None = None,
        defines: GameDefines | None = None,
        years: Sequence[int] | None = None,
    ) -> Simulation:
        """Create simulation initialized from SQLite reference database.

        This is the main entry point for the MVP simulation engine.
        It hydrates territories from the reference database with profit_rate
        computed from QCEW/BEA data.

        Args:
            fips_codes: List of 5-digit FIPS codes for counties to simulate.
                Example: ["26163", "26125"] for Wayne and Oakland counties.
            year: Data year for QCEW/BEA data (default 2022).
            observers: Optional list of SimulationObserver instances.
            defines: Optional custom GameDefines for scenario-specific coefficients.
            years: Optional sequence of years for multi-year time series.
                When provided, tensor data is hydrated for all specified years
                and the economics calculator factory is wired automatically.

        Returns:
            Initialized Simulation with territories hydrated from database.

        Raises:
            ValueError: If fips_codes is empty, contains duplicates that reduce
                to fewer unique codes, or any county is not found in database.

        Example:
            >>> sim = Simulation.from_sqlite(
            ...     fips_codes=["26163", "26125"],  # Detroit metro
            ...     year=2022
            ... )
            >>> snapshot = sim.get_snapshot()
            >>> wayne = snapshot.territories["26163"]
            >>> print(f"Wayne County profit rate: {wayne.profit_rate}")

        See Also:
            - plan.md#Hydration Flow
            - quickstart.md
        """
        from pathlib import Path

        from babylon.economics.adapters import SQLiteQCEWSource
        from babylon.economics.department_mapper import DepartmentMapper
        from babylon.economics.hydrator import MarxianHydrator
        from babylon.economics.tensor_registry import TensorRegistry
        from babylon.engine.hydration.reference import (
            StubBEASource,
            hydrate_economy_constants,
            hydrate_reserve_army,
            hydrate_territories,
        )
        from babylon.reference.database import get_reference_session

        # Validate input
        if not fips_codes:
            msg = "fips_codes list cannot be empty"
            raise ValueError(msg)

        # Hydrate territories from database
        territories, hexes = hydrate_territories(fips_codes, year)

        # Create and hydrate TensorRegistry for cached economic data access
        tensor_registry = TensorRegistry()

        # Locate NAICS-to-department mapping YAML
        economics_path = Path(__file__).parent.parent / "economics" / "data" / "naics_to_dept.yaml"

        with get_reference_session() as session:
            qcew_source = SQLiteQCEWSource(session)
            bea_source = StubBEASource()  # Falls back to DepartmentMapper defaults
            dept_mapper = DepartmentMapper.from_yaml(economics_path)

            hydrator = MarxianHydrator(qcew_source, bea_source, dept_mapper)

            # Hydrate tensor data for all counties and requested years
            hydration_years = list(years) if years is not None else [year]
            tensor_registry.hydrate_counties(hydrator, fips_codes, hydration_years)

        logger.info(
            "TensorRegistry hydrated with %d counties for %d year(s)",
            len(fips_codes),
            len(hydration_years),
        )

        # Hydrate Tier A constants from federal data (Feature 028)
        if defines is None:
            defines = GameDefines.load_default()
        primary_fips = fips_codes[0]
        economy_data = hydrate_economy_constants(primary_fips, year)
        reserve_data = hydrate_reserve_army(primary_fips, year)

        # Override GameDefines with data-derived values
        updates: dict[str, Any] = {}
        if economy_data.get("extraction_efficiency") is not None:
            updates["economy"] = defines.economy.model_copy(
                update={"extraction_efficiency": economy_data["extraction_efficiency"]}
            )
        if economy_data.get("shadow_wage_hourly") is not None:
            updates["economy"] = updates.get("economy", defines.economy).model_copy(
                update={"shadow_wage_hourly": economy_data["shadow_wage_hourly"]}
            )
        if reserve_data.get("sigmoid_r0") is not None:
            updates["reserve_army"] = defines.reserve_army.model_copy(
                update={"sigmoid_r0": reserve_data["sigmoid_r0"]}
            )
        if updates:
            defines = defines.model_copy(update=updates)
            logger.info("Tier A constants hydrated from %s/%d: %s", primary_fips, year, updates)

        # Wire calculator factory if multi-year mode requested
        calculator_overrides: dict[str, Any] | None = None
        if years is not None:
            from babylon.economics.factory import create_economics_services
            from babylon.reference.database import get_normalized_session_factory

            calc_session_factory = get_normalized_session_factory()
            calculator_overrides = create_economics_services(calc_session_factory, tensor_registry)

            # Feature 024: Wire Volume III financial calculators with real data
            from babylon.economics.factory import (
                create_financial_services,
                load_fred_series_from_db,
            )

            fred_cache = load_fred_series_from_db(calc_session_factory)
            financial_overrides = create_financial_services(fred_series_cache=fred_cache)
            calculator_overrides.update(financial_overrides)

            # Feature 023: Wire Volume II circulation calculators
            from babylon.economics.factory import (
                create_circulation_services,
                load_circulation_series_from_db,
            )

            circulation_cache = load_circulation_series_from_db(calc_session_factory)
            circulation_overrides = create_circulation_services(
                circulation_series_cache=circulation_cache,
                fred_series_cache=fred_cache,
            )
            calculator_overrides.update(circulation_overrides)

            # Feature 021: Wire Volume I production layer (reserve army, productivity, dispossession)
            from babylon.economics.factory import create_vol1_services, load_vol1_series_from_db

            vol1_cache = load_vol1_series_from_db(calc_session_factory)
            vol1_overrides = create_vol1_services(
                vol1_series_cache=vol1_cache,
                fred_series_cache=fred_cache,
            )
            calculator_overrides.update(vol1_overrides)

        # Create base WorldState and config
        state = WorldState()
        config = SimulationConfig()

        # Create simulation instance with tensor registry and calculator overrides
        sim = cls(
            state,
            config,
            observers=observers,
            defines=defines,
            tensor_registry=tensor_registry,
            calculator_overrides=calculator_overrides,
        )

        # Set base year for multi-year simulations (T013)
        if years is not None:
            sim._base_year = min(years)
        else:
            sim._base_year = year

        # Initialize MVP territory state
        sim._initialize_mvp_territories(territories=territories, hexes=hexes)

        return sim

    @property
    def config(self) -> SimulationConfig:
        """Return the simulation configuration."""
        return self._config

    @property
    def defines(self) -> GameDefines:
        """Return the game defines."""
        return self._defines

    @property
    def services(self) -> ServiceContainer:
        """Return the persistent ServiceContainer."""
        return self._services

    @property
    def tensor_registry(self) -> TensorRegistry | None:
        """Return the TensorRegistry for cached economic data access.

        Returns:
            TensorRegistry if initialized, None otherwise.
        """
        return self._tensor_registry

    @property
    def current_state(self) -> WorldState:
        """Return the current WorldState."""
        return self._current_state

    @property
    def observers(self) -> list[SimulationObserver]:
        """Return copy of registered observers.

        Returns a copy to preserve encapsulation - modifying the
        returned list does not affect the internal observer list.

        Returns:
            A copy of the list of registered observers.
        """
        return list(self._observers)

    def add_observer(self, observer: SimulationObserver) -> None:
        """Register an observer for simulation notifications.

        Observers added after simulation has started will not
        receive on_simulation_start, but will receive on_tick
        and on_simulation_end notifications.

        Args:
            observer: Observer implementing SimulationObserver protocol.
        """
        self._observers.append(observer)

    def remove_observer(self, observer: SimulationObserver) -> None:
        """Remove an observer. No-op if observer not present.

        Args:
            observer: Observer to remove from notifications.
        """
        if observer in self._observers:
            self._observers.remove(observer)

    # =========================================================================
    # GUI Protocol Extension (006): Observer Callback Registration
    # =========================================================================

    def register_observer(self, callback: ObserverCallback) -> None:
        """Register a GUI callback for tick notifications.

        Implements SimulationControl protocol.

        Thread Safety:
            Callbacks receive a frozen SimulationSnapshot, not a live reference
            to mutable simulation state. The ProtocolObserverAdapter creates the
            snapshot BEFORE iterating callbacks, ensuring:
            - All callbacks see the same consistent state
            - GUI code cannot race with engine mutations
            - Callback processing time does not affect snapshot consistency

        Callbacks are invoked in registration order. Duplicate registration
        is idempotent (callback invoked once per tick).

        Args:
            callback: Function to call after each tick.
                      Signature: (tick: int, snapshot: SimulationSnapshot) -> None
        """
        self._adapter.register(callback)

    def unregister_observer(self, callback: ObserverCallback) -> None:
        """Remove a previously registered GUI callback.

        Implements SimulationControl protocol.

        If the callback was not registered, this is a no-op (no error raised).

        Args:
            callback: The callback function to remove.
        """
        self._adapter.unregister(callback)

    def _notify_gui_observers(self) -> None:
        """Notify GUI observers with frozen snapshot.

        Called at the end of each step() tick. The adapter creates a snapshot
        BEFORE iterating callbacks to ensure thread safety.
        """
        self._adapter.notify(self.get_current_tick())

    def _notify_observers_start(self) -> None:
        """Notify observers of simulation start.

        Errors in observers are logged but do not halt simulation (ADR003).
        """
        for observer in self._observers:
            try:
                observer.on_simulation_start(self._current_state, self._config)
            except Exception as e:
                logger.warning(
                    "Observer %s failed on_simulation_start: %s",
                    observer.name,
                    e,
                )

    def _notify_observers_tick(
        self,
        previous: WorldState,
        new: WorldState,
    ) -> None:
        """Notify observers of tick completion.

        Errors in observers are logged but do not halt simulation (ADR003).

        Args:
            previous: WorldState before the tick.
            new: WorldState after the tick.
        """
        for observer in self._observers:
            try:
                observer.on_tick(previous, new)
            except Exception as e:
                logger.warning(
                    "Observer %s failed on_tick: %s",
                    observer.name,
                    e,
                )

    def _notify_observers_end(self) -> None:
        """Notify observers of simulation end.

        Errors in observers are logged but do not halt simulation (ADR003).
        """
        for observer in self._observers:
            try:
                observer.on_simulation_end(self._current_state)
            except Exception as e:
                logger.warning(
                    "Observer %s failed on_simulation_end: %s",
                    observer.name,
                    e,
                )

    def _collect_observer_events(self) -> None:
        """Collect pending events from observers for next tick.

        Sprint 3.3: Observer events are collected after each tick and stored
        in persistent_context for injection into the NEXT tick's WorldState.

        Observers run AFTER WorldState is frozen, so their events cannot be
        added to the current tick. Instead, events are collected here and
        the step() function in simulation_engine.py will inject them into
        the next tick's structured events.
        """
        from babylon.models.events import SimulationEvent

        observer_events: list[SimulationEvent] = []
        for observer in self._observers:
            if hasattr(observer, "get_pending_events"):
                try:
                    events = observer.get_pending_events()
                    observer_events.extend(events)
                except Exception as e:
                    logger.warning(
                        "Observer %s failed get_pending_events: %s",
                        observer.name,
                        e,
                    )

        if observer_events:
            self._persistent_context["_observer_events"] = observer_events

    def step(self, n: int = 1) -> WorldState:
        """Advance simulation by n ticks.

        Implements SimulationControl protocol's step(n) method.

        Applies the step() function to transform the current state,
        records the new state in history, updates current_state, and
        notifies registered observers.

        On first step, observers receive on_simulation_start before on_tick.

        The persistent context is passed to step() to maintain state
        across ticks (e.g., previous_wages for bifurcation mechanic).

        Args:
            n: Number of ticks to advance. Must be positive.
                Defaults to 1 for backward compatibility.

        Returns:
            The new WorldState after all ticks complete.

        Raises:
            ValueError: If n <= 0.
        """
        if n <= 0:
            msg = f"n must be positive, got {n}"
            raise ValueError(msg)

        for _ in range(n):
            self._step_single()

        return self._current_state

    def _step_single(self) -> WorldState:
        """Advance simulation by exactly one tick (internal).

        This is the core tick advancement logic, separated for use by step(n).

        Returns:
            The new WorldState after one tick of simulation.
        """
        # On first step, notify observers of simulation start
        if not self._started:
            self._notify_observers_start()
            self._started = True

        # GUI Protocol Extension (006): Invalidate spatial index cache (T028)
        # Cache must be invalidated each tick since territory state may change
        self._hex_to_territory = None

        previous_state = self._current_state

        # Inject base_year into persistent context for TickDynamicsSystem (T013)
        if self._base_year is not None:
            self._persistent_context["_base_year"] = self._base_year

        # Pass persistent context to preserve state across ticks (Sprint 3.4.3)
        # Pass custom defines for scenario-specific coefficients
        # Pass calculator overrides for wired economics (Feature 020)
        new_state = step(
            previous_state,
            self._config,
            self._persistent_context,
            self._defines,
            calculator_overrides=self._calculator_overrides,
        )
        self._current_state = new_state
        self._history.append(new_state)

        # Notify observers after state reconstruction (per design decision)
        self._notify_observers_tick(previous_state, new_state)

        # Collect observer events for next tick (Sprint 3.3)
        self._collect_observer_events()

        # Update MVP territory profit_rates
        self._update_mvp_profit_rates()

        # GUI Protocol Extension (006): Notify GUI observers with frozen snapshot
        self._notify_gui_observers()

        return new_state

    def run(self, ticks: int) -> WorldState:
        """Run simulation for N ticks.

        Args:
            ticks: Number of ticks to advance the simulation

        Returns:
            The final WorldState after all ticks complete.

        Raises:
            ValueError: If ticks is negative or zero
        """
        if ticks <= 0:
            if ticks < 0:
                error_message = f"ticks must be non-negative, got {ticks}"
                raise ValueError(error_message)
            # ticks == 0: no-op
            return self._current_state

        return self.step(ticks)

    def get_history(self) -> list[WorldState]:
        """Return all WorldState snapshots from initial to current.

        The history includes:
        - Index 0: Initial state (tick 0)
        - Index N: State after N steps (tick N)

        Returns:
            List of WorldState snapshots in chronological order.
        """
        return list(self._history)

    def get_time_series(self) -> list[dict[str, Any]]:
        """Extract time series records from completed simulation.

        Reads accumulated tick dynamics snapshots stored in persistent_context
        by the step() function at each year boundary. Each snapshot contains
        county-level economic state computed by TickDynamicsSystem.

        Returns:
            List of dicts with keys: year, fips, class distribution shares
            (bourgeoisie_share, petit_bourgeoisie_share, la_share,
            proletariat_share, lumpen_share), profit_rate, phi_hour,
            throughput_position, data_source, and Vol I/II/III fields:
            capital_stock, median_wage, employment (Vol I);
            circuit_money, circuit_productive, circuit_commodity,
            liquidity_ratio, realization_crisis (Vol II);
            surplus_total, interest_payments, ground_rent,
            profit_of_enterprise, financialization_share,
            overaccumulation, profit_squeeze (Vol III).

        Example:
            >>> sim = Simulation.from_sqlite(["26163"], year=2022, years=[2022])
            >>> sim.run(52)
            >>> ts = sim.get_time_series()
            >>> for record in ts:
            ...     print(f"{record['year']} {record['fips']}: LA={record['la_share']:.2f}")
        """
        from babylon.economics.tick.derived_rates import DerivedRateCalculator
        from babylon.economics.tick.graph_bridge import (
            _reconstruct_tick_state,
        )

        records: list[dict[str, Any]] = []
        rate_calc = DerivedRateCalculator()

        # Read accumulated snapshots from persistent context
        raw_snapshots = self._persistent_context.get("_tick_dynamics_snapshots", [])
        snapshots: list[dict[str, Any]] = raw_snapshots if isinstance(raw_snapshots, list) else []

        for snap_data in snapshots:
            tick_state = _reconstruct_tick_state(snap_data)
            if tick_state is None:
                continue

            for fips, county in tick_state.county_states.items():
                dist = county.class_distribution
                rates = rate_calc.compute_county_rates(
                    county,
                    tick_state.national_params,
                )
                circ = county.circulation_state
                surplus = county.surplus_distribution
                crisis = county.financial_crisis
                records.append(
                    {
                        "year": tick_state.year,
                        "fips": fips,
                        "bourgeoisie_share": dist.bourgeoisie_share,
                        "petit_bourgeoisie_share": dist.petit_bourgeoisie_share,
                        "la_share": dist.labor_aristocracy_share,
                        "proletariat_share": dist.proletariat_share,
                        "lumpen_share": dist.lumpenproletariat_share,
                        "profit_rate": rates.profit_rate,
                        "phi_hour": county.phi_hour,
                        "throughput_position": county.throughput_position,
                        "data_source": "simulation",
                        # Vol I production
                        "capital_stock": county.capital_stock,
                        "median_wage": county.median_wage,
                        "employment": county.employment,
                        # Vol II circulation
                        "circuit_money": circ.circuit_state.money_capital,
                        "circuit_productive": circ.circuit_state.productive_capital,
                        "circuit_commodity": circ.circuit_state.commodity_capital,
                        "liquidity_ratio": circ.circuit_state.liquidity_ratio,
                        "realization_crisis": (
                            circ.latest_assessment.realization_crisis
                            if circ.latest_assessment is not None
                            else None
                        ),
                        # Vol III finance
                        "surplus_total": (
                            surplus.total_surplus_produced if surplus is not None else None
                        ),
                        "interest_payments": (
                            surplus.interest_payments if surplus is not None else None
                        ),
                        "ground_rent": (surplus.ground_rent if surplus is not None else None),
                        "profit_of_enterprise": (
                            surplus.profit_of_enterprise if surplus is not None else None
                        ),
                        "financialization_share": (
                            surplus.financialization_share if surplus is not None else None
                        ),
                        "overaccumulation": (
                            crisis.overaccumulation if crisis is not None else None
                        ),
                        "profit_squeeze": (crisis.profit_squeeze if crisis is not None else None),
                    }
                )

        return records

    def update_state(self, new_state: WorldState) -> None:
        """Update the current state mid-simulation.

        This allows modifying the simulation state (e.g., changing relationships)
        while preserving the persistent context across ticks. Useful for testing
        scenarios like wage cuts where the previous_wages context must be preserved.

        Args:
            new_state: New WorldState to use as current state.
                       The tick should match the expected continuation tick.

        Note:
            This does NOT add the new state to history - history reflects
            actual simulation progression, not manual state updates.
        """
        self._current_state = new_state

    def end(self) -> None:
        """Signal simulation end and notify observers.

        Calls on_simulation_end on all registered observers with
        the current (final) state.

        No-op if simulation has not started (no step() calls made).
        Can be called multiple times, but only the first call after
        step() will notify observers.
        """
        if self._started:
            self._notify_observers_end()
            self._started = False

    def get_outcome(self) -> GameOutcome:
        """Return current game outcome from EndgameDetector if present.

        Searches registered observers for an EndgameDetector and returns
        its current outcome. If no EndgameDetector is registered, returns
        IN_PROGRESS.

        Returns:
            GameOutcome enum value indicating current game state.

        Example:
            >>> from babylon.engine.observers import EndgameDetector
            >>> detector = EndgameDetector()
            >>> sim = Simulation(state, config, observers=[detector])
            >>> sim.get_outcome()
            <GameOutcome.IN_PROGRESS: 'in_progress'>
        """
        from babylon.engine.observers.endgame_detector import EndgameDetector

        for observer in self._observers:
            if isinstance(observer, EndgameDetector):
                return observer.outcome

        return GameOutcome.IN_PROGRESS

    # =========================================================================
    # MVP Simulation Engine: Protocol Methods (001-mvp-sim-engine)
    # =========================================================================

    # STUB: Placeholder decay rate - replace with TRPF mechanics
    _MVP_DECAY_RATE: float = 0.05

    def get_current_tick(self) -> int:
        """Return the current tick number.

        Implements SimulationState protocol.

        Returns:
            Non-negative integer representing the current simulation tick.
            Tick 0 is the initial state before any step() calls.
        """
        return self._current_state.tick

    def get_snapshot(self) -> SimulationSnapshot:
        """Return a complete snapshot of the current simulation state.

        Implements SimulationState protocol.

        The snapshot is immutable - modifying the returned object does not
        affect the simulation. The tensor_registry reference allows cached
        tensor data access without database queries.

        Returns:
            SimulationSnapshot containing all state at the current tick.
        """
        return SimulationSnapshot(
            tick=self._current_state.tick,
            territories=dict(self._mvp_territories),
            hexes=dict(self._mvp_hexes),
            edges=[],  # Empty for MVP - no inter-territory edges yet
            tensor_registry=self._tensor_registry,
        )

    def get_territory_state(self, territory_id: str) -> TerritoryState | None:
        """Return the state of a specific territory.

        Implements SimulationState protocol.

        Args:
            territory_id: Unique identifier for the territory (FIPS code for counties).

        Returns:
            TerritoryState if the territory exists, None otherwise.
        """
        return self._mvp_territories.get(territory_id)

    def get_hexes_for_territory(self, territory_id: str) -> set[str]:
        """Return the H3 indices claimed by a territory.

        Implements SimulationState protocol.

        Args:
            territory_id: Unique identifier for the territory.

        Returns:
            Set of H3 index strings. Empty set if territory not found.
        """
        territory = self._mvp_territories.get(territory_id)
        if territory is None:
            return set()
        return set(territory.hex_claims)

    # =========================================================================
    # GUI Protocol Extension (006): Spatial Query by H3 Index
    # =========================================================================

    # Lazy cache for reverse H3 -> territory_id mapping (T025)
    _hex_to_territory: dict[str, str] | None = None

    def _build_hex_index(self) -> dict[str, str]:
        """Build reverse H3 -> territory_id mapping (T026).

        Iterates all territories and creates a reverse index from each
        H3 hex claim to its owning territory_id.

        Returns:
            Dict mapping h3_index -> territory_id.
        """
        index: dict[str, str] = {}
        for territory_id, territory in self._mvp_territories.items():
            for h3_idx in territory.hex_claims:
                index[h3_idx] = territory_id
        return index

    def get_node_by_spatial_index(self, h3_index: str) -> TerritoryState | None:
        """Return the territory that claims a specific H3 hex (T027).

        Implements SimulationState protocol.

        This method bridges the spatial representation (H3 hexes used by
        map visualization like pydeck) to the simulation's territory model.

        Args:
            h3_index: H3 cell index (15-character lowercase hex string).

        Returns:
            TerritoryState if a territory claims this hex, None otherwise.

        Raises:
            ValueError: If h3_index is not a valid H3 cell index.
        """
        # Validate H3 format using library function
        if not h3.is_valid_cell(h3_index):
            msg = f"Invalid H3 index: {h3_index}"
            raise ValueError(msg)

        # Build cache lazily on first query
        if self._hex_to_territory is None:
            self._hex_to_territory = self._build_hex_index()

        # Lookup territory by hex claim
        territory_id = self._hex_to_territory.get(h3_index)
        if territory_id is None:
            return None

        return self._mvp_territories.get(territory_id)

    def _update_mvp_profit_rates(self) -> None:
        """Update territory profit_rates using placeholder decay formula.

        Formula (STUB - replace with TRPF):
            r_new = r_old * (1 - decay_rate) + equilibrium_r * decay_rate

        Where:
            decay_rate = 0.05 (configurable)
            equilibrium_r = territory-specific initial profit_rate
        """
        current_tick = self._current_state.tick
        updated_territories: dict[str, TerritoryState] = {}

        for territory_id, territory in self._mvp_territories.items():
            # Apply exponential smoothing toward equilibrium
            old_r = territory.profit_rate
            equilibrium_r = territory.equilibrium_r
            new_r = old_r * (1 - self._MVP_DECAY_RATE) + equilibrium_r * self._MVP_DECAY_RATE

            # Create new TerritoryState with clamped profit_rate
            updated_territories[territory_id] = TerritoryState.with_clamped_profit_rate(
                territory_id=territory_id,
                controlling_polity=territory.controlling_polity,
                hex_claims=territory.hex_claims,
                tick=current_tick,
                profit_rate=new_r,
                equilibrium_r=equilibrium_r,
            )

        self._mvp_territories = updated_territories

    def reset(self) -> None:
        """Reset simulation to initial state (tick 0).

        Implements SimulationControl protocol.

        Restores the simulation to its state immediately after initialization:
        - tick = 0
        - All territory states reset to initial values
        - profit_rate returns to initial computed values
        - WorldState reset to initial state
        - History cleared

        Implementation note: reset() restores CACHED initial state.
        """
        # Reset WorldState
        self._current_state = self._initial_world_state
        self._history = [self._initial_world_state]
        self._started = False
        self._persistent_context = {}

        # Reset MVP territory state
        self._mvp_territories = dict(self._initial_mvp_territories)
        self._mvp_hexes = dict(self._initial_mvp_hexes)

    def _initialize_mvp_territories(
        self,
        territories: dict[str, TerritoryState],
        hexes: dict[str, HexState],
    ) -> None:
        """Initialize MVP territory state from hydration.

        Called by from_sqlite() class method after loading data.

        Args:
            territories: Map of territory_id to TerritoryState.
            hexes: Map of h3_index to HexState.
        """
        self._mvp_territories = dict(territories)
        self._mvp_hexes = dict(hexes)
        # Cache for reset()
        self._initial_mvp_territories = dict(territories)
        self._initial_mvp_hexes = dict(hexes)

    def run_until_endgame(
        self,
        max_ticks: int = 1000,
    ) -> tuple[WorldState, GameOutcome]:
        """Run simulation until an endgame condition is met or max_ticks reached.

        This method runs the simulation step by step, checking after each tick
        whether the EndgameDetector has detected a game ending condition.
        It terminates early if an endgame is reached.

        Args:
            max_ticks: Maximum number of ticks to run before returning.
                Defaults to 1000 to prevent infinite loops.

        Returns:
            Tuple of (final_state, outcome):
            - final_state: The WorldState when simulation stopped
            - outcome: GameOutcome indicating why simulation stopped
              (may be IN_PROGRESS if max_ticks reached without endgame)

        Raises:
            ValueError: If max_ticks is negative.

        Example:
            >>> from babylon.engine.observers import EndgameDetector
            >>> detector = EndgameDetector()
            >>> sim = Simulation(state, config, observers=[detector])
            >>> final_state, outcome = sim.run_until_endgame(max_ticks=100)
            >>> if outcome == GameOutcome.REVOLUTIONARY_VICTORY:
            ...     print("The workers have won!")
        """
        if max_ticks < 0:
            error_message = f"max_ticks must be non-negative, got {max_ticks}"
            raise ValueError(error_message)

        from babylon.engine.observers.endgame_detector import EndgameDetector

        # Find the EndgameDetector
        detector: EndgameDetector | None = None
        for observer in self._observers:
            if isinstance(observer, EndgameDetector):
                detector = observer
                break

        tick_count = 0
        while tick_count < max_ticks:
            self.step()
            tick_count += 1

            # Check if game ended
            if detector is not None and detector.is_game_over:
                break

        # Return final state and outcome
        outcome = detector.outcome if detector is not None else GameOutcome.IN_PROGRESS
        return (self._current_state, outcome)
