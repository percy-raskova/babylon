"""Structural protocol for the simulation's DI service container.

``babylon.engine.services.ServiceContainer`` is the concrete container; this
protocol is its kernel-level shadow so lower layers (economics systems, the
system base class) can type-hint the services they receive without importing
the engine — the exact back-edge Program 14 Phase 1 removed.

Only ``event_bus`` is typed precisely (it lives in the kernel). Everything
else is deliberately ``Any``: the concrete types live in upper layers the
kernel must not name at runtime, and the container's optional-calculator
surface (``Any`` fields defaulting to ``None``) is already dynamically typed
at the source. Structural conformance of ``ServiceContainer`` to this
protocol is pinned by ``tests/unit/kernel/test_services_protocol.py``.
"""

from __future__ import annotations

from typing import Any, Protocol

from babylon.kernel.event_bus import EventBus


class ServicesProtocol(Protocol):
    """Attribute surface of the simulation service container.

    :ivar config: Run-scoped ``SimulationConfig`` (carries ``rng_seed``).
    :ivar database: Database connection satisfying the persistence protocol.
    :ivar event_bus: Kernel publish/subscribe bus.
    :ivar formulas: ``FormulaRegistry`` of hot-swappable formulas.
    :ivar defines: ``GameDefines`` — the moddable coefficient space.
    :ivar metrics: Telemetry collector.
    """

    config: Any
    database: Any
    event_bus: EventBus
    formulas: Any
    defines: Any
    metrics: Any

    # Optional service surface (populated by the composition root; None when
    # unwired). Mirrors ServiceContainer's optional fields — all Any there too.
    field_registry: Any
    opposition_registry: Any
    reserve_army_data_source: Any
    dispossession_data_source: Any
    productivity_data_source: Any
    melt_calculator: Any
    basket_calculator: Any
    gamma_calculator: Any
    capital_calculator: Any
    throughput_calculator: Any
    transition_engine: Any
    tensor_registry: Any
    employment_source: Any
    unemployment_source: Any
    housing_source: Any
    wage_source: Any
    income_source: Any
    economics_fallbacks: Any
    community_hypergraph: Any
    turnover_profile_source: Any
    inventory_data_source: Any
    depreciation_data_source: Any
    hex_grid: Any
    persistence: Any
    tracer: Any
    boundary_register: Any
    auditor: Any
    distribution_calculator: Any
    interest_calculator: Any
    credit_cycle_detector: Any
    fictitious_capital_calculator: Any
    rent_calculator: Any
    housing_calculator: Any
    counter_tendency_calculator: Any
    value_basis_converter: Any
    financial_crisis_assessor: Any
    z1_source: Any
    housing_data_source: Any
    periphery_labor_source: Any
    final_demand_source: Any
    industry_county_allocator: Any
    production_chain_calculator: Any
    bea_industries: list[str] | None
