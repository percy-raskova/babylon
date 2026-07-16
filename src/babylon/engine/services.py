"""Service container for dependency injection.

This module provides a ServiceContainer dataclass that aggregates all
dependencies needed by the simulation engine, enabling clean injection
for testing and configuration.

Sprint 3: Central Committee (Dependency Injection)
Paradox Refactor: Added GameDefines for centralized coefficients.
Spec 008: Added metrics field for dependency-injected telemetry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from babylon.config.defines import GameDefines
from babylon.engine.formula_registry import FormulaRegistry
from babylon.kernel.database import DatabaseProtocol
from babylon.kernel.event_bus import EventBus
from babylon.models.config import SimulationConfig

if TYPE_CHECKING:
    from babylon.kernel.metrics import MetricsCollectorProtocol


@dataclass
class EconomicsFallbackTally:
    """Loud observability for economics-calculator fallbacks (C.8 / spec 2.R).

    :class:`~babylon.domain.economics.tick.system.TickDynamicsSystem` substitutes a
    hardcoded coefficient whenever an economics calculator is unwired
    (``None``) or returns no data. Historically these substitutions were
    *silent* — a fully-unwired run reported gamma_III = 0.33 forever with no
    trace of why. This tally records each fallback and the wired-vs-None status
    of every calculator so the run manifest can attest whether gamma was
    genuinely computed or merely defaulted.

    Pure instrumentation: recording a fallback NEVER changes a computed value.
    The caller selects the fallback constant first, then calls ``record_*``.

    A fresh tally is created per :class:`ServiceContainer` (``default_factory``),
    so counters are scoped to a single run and safe across processes/tests.
    """

    #: How many times ``_compute_national_params`` ran (year boundaries seen).
    national_params_observations: int = 0
    #: Wired-vs-None status of each calculator (snapshot; last observation wins).
    melt_calculator_wired: bool = False
    basket_calculator_wired: bool = False
    gamma_calculator_wired: bool = False
    #: Per-fallback counters.
    melt_unavailable: int = 0
    gamma_basket_calculator_none: int = 0
    gamma_iii_calculator_none: int = 0
    gamma_iii_returned_none: int = 0

    def observe_wiring(self, *, melt: bool, basket: bool, gamma: bool) -> None:
        """Record calculator wired-vs-None status for this observation.

        Args:
            melt: Whether ``melt_calculator`` is wired (not ``None``).
            basket: Whether ``basket_calculator`` is wired (not ``None``).
            gamma: Whether ``gamma_calculator`` is wired (not ``None``).
        """
        self.national_params_observations += 1
        self.melt_calculator_wired = melt
        self.basket_calculator_wired = basket
        self.gamma_calculator_wired = gamma

    def record_melt_unavailable(self) -> None:
        """Count a MELT-unavailable early return (calculator wired but no data)."""
        self.melt_unavailable += 1

    def record_gamma_basket_calculator_none(self) -> None:
        """Count a gamma_basket fallback taken because the calculator is ``None``."""
        self.gamma_basket_calculator_none += 1

    def record_gamma_iii_calculator_none(self) -> None:
        """Count a gamma_III fallback taken because the calculator is ``None``."""
        self.gamma_iii_calculator_none += 1

    def record_gamma_iii_returned_none(self) -> None:
        """Count a gamma_III fallback taken because a wired calculator returned no data."""
        self.gamma_iii_returned_none += 1

    def to_dict(self) -> dict[str, int | bool]:
        """Serialize to a manifest-ready dict (stable key order).

        Returns:
            Dict of counter/status fields for the manifest
            ``economics_fallbacks`` block.
        """
        return {
            "national_params_observations": self.national_params_observations,
            "melt_calculator_wired": self.melt_calculator_wired,
            "basket_calculator_wired": self.basket_calculator_wired,
            "gamma_calculator_wired": self.gamma_calculator_wired,
            "melt_unavailable": self.melt_unavailable,
            "gamma_basket_calculator_none": self.gamma_basket_calculator_none,
            "gamma_iii_calculator_none": self.gamma_iii_calculator_none,
            "gamma_iii_returned_none": self.gamma_iii_returned_none,
        }


@dataclass
class ServiceContainer:
    """Container for all simulation services.

    Aggregates the six core services needed by the simulation, plus
    optional economics calculator services for tick dynamics (Feature 017):

    Core:
        - config: Immutable simulation parameters
        - database: Database connection for persistence
        - event_bus: Publish/subscribe communication
        - formulas: Registry of mathematical formulas
        - defines: Centralized game coefficients (Paradox Refactor)
        - metrics: Telemetry collector for observability (Spec 008)

    Field Topology (Feature 002, optional for backward compatibility):
        - field_registry: Contradiction field computation registry

    Economics (Feature 017, all optional for backward compatibility):
        - melt_calculator: National MELT computation (Feature 013)
        - basket_calculator: Basket visibility computation (Feature 013)
        - gamma_calculator: Reproductive visibility computation (Feature 015)
        - capital_calculator: Capital stock computation (Feature 012)
        - throughput_calculator: Throughput position computation (Feature 014)
        - transition_engine: Class transition engine (Feature 016)
        - tensor_registry: Cached economic tensor data (Feature 011)

    Example:
        >>> container = ServiceContainer.create()
        >>> rent = container.formulas.get("imperial_rent")
        >>> container.event_bus.publish(Event(...))
        >>> with container.database.session() as session:
        ...     # do database work
        >>> container.database.close()
        >>> default_org = container.defines.DEFAULT_ORGANIZATION
        >>> container.metrics.increment("ticks_processed")
    """

    config: SimulationConfig
    database: DatabaseProtocol
    event_bus: EventBus
    formulas: FormulaRegistry
    defines: GameDefines
    metrics: MetricsCollectorProtocol

    # Field topology services (Feature 002 - optional, default None)
    field_registry: Any = field(default=None)

    # Lawverian opposition registry (Phase C). Unlike ``field_registry`` (the
    # dormant Feature-002 plumbing, still None in production), this is wired by
    # ``create`` by default so ContradictionSystem always has a populated
    # OppositionRegistry to step each tick.
    opposition_registry: Any = field(default=None)

    # Capital Volume I data sources (Feature 021 - optional, default None)
    reserve_army_data_source: Any = field(default=None)
    dispossession_data_source: Any = field(default=None)
    productivity_data_source: Any = field(default=None)

    # Economics calculator services (Feature 017 - all optional, default None)
    melt_calculator: Any = field(default=None)
    basket_calculator: Any = field(default=None)
    gamma_calculator: Any = field(default=None)
    capital_calculator: Any = field(default=None)
    throughput_calculator: Any = field(default=None)
    transition_engine: Any = field(default=None)
    tensor_registry: Any = field(default=None)
    # Program 17 item-25 Fix C: per-county employment headcount source (QCEW
    # county rollup, ``get_county_total_employment``). None => the tick pipeline
    # keeps its documented 100k graceful-degradation default.
    employment_source: Any = field(default=None)
    unemployment_source: Any = field(default=None)
    wage_source: Any = field(default=None)

    # C.8 (spec 2.R): loud economics-fallback observability. A fresh tally per
    # container; TickDynamicsSystem records fallbacks + wired status into it,
    # and the headless runner surfaces it as the manifest ``economics_fallbacks``
    # block. Pure instrumentation — never affects a computed value.
    economics_fallbacks: EconomicsFallbackTally = field(default_factory=EconomicsFallbackTally)

    # Hypergraph community layer (Feature 022 - optional, default None)
    community_hypergraph: Any = field(default=None)

    # Capital Volume II circulation layer (Feature 023 - optional, default None)
    turnover_profile_source: Any = field(default=None)
    inventory_data_source: Any = field(default=None)
    depreciation_data_source: Any = field(default=None)

    # Hex spatial substrate (Feature 026 - optional, default None)
    hex_grid: Any = field(default=None)

    # Persistence layer (Feature 037 - optional, default None)
    persistence: Any = field(default=None)
    tracer: Any = field(default=None)

    # Spec-065 (engine-bridging) — optional services owned by the headless
    # runner's run() and consumed by the engine systems in spec-066.
    # Leaving these as Optional[Any] means existing ServiceContainer.create()
    # call sites are unaffected; spec-066 will populate them when wiring the
    # engine through the bridge.
    boundary_register: Any = field(default=None)
    auditor: Any = field(default=None)

    # Capital Volume III financial layer (Feature 024 - optional, default None)
    distribution_calculator: Any = field(default=None)
    interest_calculator: Any = field(default=None)
    credit_cycle_detector: Any = field(default=None)
    fictitious_capital_calculator: Any = field(default=None)
    rent_calculator: Any = field(default=None)
    housing_calculator: Any = field(default=None)
    counter_tendency_calculator: Any = field(default=None)
    value_basis_converter: Any = field(default=None)
    financial_crisis_assessor: Any = field(default=None)
    z1_source: Any = field(default=None)
    housing_data_source: Any = field(default=None)

    # Spec 057 — Leontief Imperial Rent Integration (optional, default None)
    periphery_labor_source: Any = field(default=None)
    final_demand_source: Any = field(default=None)
    industry_county_allocator: Any = field(default=None)
    production_chain_calculator: Any = field(default=None)
    bea_industries: list[str] | None = field(default=None)
    """The configured BEA Summary industry list — defines the alignment baseline
    for FR-006 (industry-list mismatch fail-fast). Set at scenario-load time;
    None until then (the Spec 057 pipeline falls back to graceful-degradation
    stub behavior when None per data-model.md ServiceContainer notes)."""

    @classmethod
    def create(
        cls,
        config: SimulationConfig | None = None,
        defines: GameDefines | None = None,
        metrics: MetricsCollectorProtocol | None = None,
        *,
        hex_grid: Any = None,
        persistence: Any = None,
        tracer: Any = None,
        reserve_army_data_source: Any = None,
        dispossession_data_source: Any = None,
        productivity_data_source: Any = None,
        field_registry: Any = None,
        opposition_registry: Any = None,
        melt_calculator: Any = None,
        basket_calculator: Any = None,
        gamma_calculator: Any = None,
        capital_calculator: Any = None,
        throughput_calculator: Any = None,
        transition_engine: Any = None,
        tensor_registry: Any = None,
        employment_source: Any = None,
        unemployment_source: Any = None,
        wage_source: Any = None,
        community_hypergraph: Any = None,
        turnover_profile_source: Any = None,
        inventory_data_source: Any = None,
        depreciation_data_source: Any = None,
        distribution_calculator: Any = None,
        interest_calculator: Any = None,
        credit_cycle_detector: Any = None,
        fictitious_capital_calculator: Any = None,
        rent_calculator: Any = None,
        housing_calculator: Any = None,
        counter_tendency_calculator: Any = None,
        value_basis_converter: Any = None,
        financial_crisis_assessor: Any = None,
        z1_source: Any = None,
        housing_data_source: Any = None,
        periphery_labor_source: Any = None,
        final_demand_source: Any = None,
        industry_county_allocator: Any = None,
        production_chain_calculator: Any = None,
        bea_industries: list[str] | None = None,
    ) -> ServiceContainer:
        """Factory method to create a fully-initialized container.

        Creates all services with sensible defaults. Uses in-memory
        SQLite for database isolation in tests.

        Args:
            config: Optional custom config. If None, uses default SimulationConfig.
            defines: Optional custom defines. If None, uses default GameDefines.
            metrics: Optional custom metrics collector. If None, creates a new
                MetricsCollector instance. Pass a mock for testing.
            field_registry: Optional FieldRegistry for contradiction fields (Feature 002).
            melt_calculator: Optional MELTCalculator (Feature 013).
            basket_calculator: Optional BasketVisibilityCalculator (Feature 013).
            gamma_calculator: Optional GammaIIICalculator (Feature 015).
            capital_calculator: Optional CapitalStockCalculator (Feature 012).
            throughput_calculator: Optional ThroughputCalculator (Feature 014).
            transition_engine: Optional ClassTransitionEngine (Feature 016).
            tensor_registry: Optional TensorRegistry for cached tensor data (Feature 011).
            community_hypergraph: Optional XGI Hypergraph for community membership (Feature 022).

        Returns:
            ServiceContainer with all services initialized
        """
        # Lazy import to avoid circular imports (T017)
        if metrics is None:
            from babylon.metrics.collector import MetricsCollector

            metrics = MetricsCollector()

        resolved_defines = defines if defines is not None else GameDefines()

        # Wire the Lawverian OppositionRegistry by default (Phase C). Lazy
        # import: the catalog depends only on formulas + dialectics (never on
        # babylon.engine), so it cannot cycle back into this module.
        if opposition_registry is None:
            from babylon.domain.dialectics.instances.catalog import build_default_registry

            opposition_registry = build_default_registry(
                rate_weight=resolved_defines.tension.principal_rate_weight
            )

        # Lazy import: the concrete SQLAlchemy connection lives in the
        # persistence layer; the engine names only the kernel protocol
        # (Program 14 — Constitution II.6). Engine->persistence is a legal
        # downward edge, confined to this composition factory.
        from babylon.persistence.database import DatabaseConnection

        return cls(
            config=config if config is not None else SimulationConfig(),
            database=DatabaseConnection(url="sqlite:///:memory:"),
            event_bus=EventBus(),
            formulas=FormulaRegistry.default(),
            defines=resolved_defines,
            metrics=metrics,
            hex_grid=hex_grid,
            persistence=persistence,
            tracer=tracer,
            reserve_army_data_source=reserve_army_data_source,
            dispossession_data_source=dispossession_data_source,
            productivity_data_source=productivity_data_source,
            field_registry=field_registry,
            opposition_registry=opposition_registry,
            melt_calculator=melt_calculator,
            basket_calculator=basket_calculator,
            gamma_calculator=gamma_calculator,
            capital_calculator=capital_calculator,
            throughput_calculator=throughput_calculator,
            transition_engine=transition_engine,
            tensor_registry=tensor_registry,
            employment_source=employment_source,
            unemployment_source=unemployment_source,
            wage_source=wage_source,
            community_hypergraph=community_hypergraph,
            turnover_profile_source=turnover_profile_source,
            inventory_data_source=inventory_data_source,
            depreciation_data_source=depreciation_data_source,
            distribution_calculator=distribution_calculator,
            interest_calculator=interest_calculator,
            credit_cycle_detector=credit_cycle_detector,
            fictitious_capital_calculator=fictitious_capital_calculator,
            rent_calculator=rent_calculator,
            housing_calculator=housing_calculator,
            counter_tendency_calculator=counter_tendency_calculator,
            value_basis_converter=value_basis_converter,
            financial_crisis_assessor=financial_crisis_assessor,
            z1_source=z1_source,
            housing_data_source=housing_data_source,
            periphery_labor_source=periphery_labor_source,
            final_demand_source=final_demand_source,
            industry_county_allocator=industry_county_allocator,
            production_chain_calculator=production_chain_calculator,
            bea_industries=bea_industries,
        )
