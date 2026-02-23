"""Economics calculator factory for wiring all calculators with data sources.

Feature: 020-detroit-vertical-slice
Task: T007

This module provides the factory function that creates and wires all
economics calculators needed by the simulation engine. The factory
resolves the dependency graph between data sources and calculators,
returning a dict suitable for injection into ServiceContainer.

Dependency wiring order (3 levels):
    Level 0: No dependencies (basket, imperial rent)
    Level 1: Data source adapters (BEA, QCEW, ATUS, savings, dispossession)
    Level 2: Calculators with data deps (MELT, capital, gamma, accumulation, etc.)
    Level 3: Calculators with calculator deps (throughput, transition engine)

Usage:
    from babylon.data.reference.database import get_normalized_session_factory
    from babylon.economics.factory import create_economics_services

    session_factory = get_normalized_session_factory()
    tensor_registry = TensorRegistry()
    # ... hydrate tensor_registry ...

    overrides = create_economics_services(session_factory, tensor_registry)
    services = ServiceContainer.create(config, defines, **overrides)

See Also:
    :mod:`babylon.engine.services`: ServiceContainer that consumes these overrides
    :mod:`babylon.engine.simulation`: Simulation.from_sqlite() which calls this factory
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from babylon.economics.capital_stock import CapitalStockCalculator
from babylon.economics.dynamics.accumulation import DefaultAccumulationCalculator
from babylon.economics.dynamics.crisis import DefaultCrisisAmplifier
from babylon.economics.dynamics.dispossession import DefaultDispossessionCalculator
from babylon.economics.dynamics.hardcoded_data import HardcodedNationalDispossessionSource
from babylon.economics.dynamics.savings_schedule import DefaultSavingsRateSchedule
from babylon.economics.dynamics.transition_engine import DefaultClassTransitionEngine
from babylon.economics.gamma.adapters import MVPUnpaidCareHoursSource, QCEWCareAdapter
from babylon.economics.gamma.gamma_iii import DefaultGammaIIICalculator
from babylon.economics.melt import (
    DefaultBasketVisibilityCalculator,
    DefaultImperialRentCalculator,
    DefaultMELTCalculator,
)
from babylon.economics.melt.adapters import (
    SQLiteBEANationalGDPSource,
    SQLiteQCEWNationalEmploymentSource,
)
from babylon.economics.throughput.adapters import (
    SQLiteBEACountyGDPSource,
    SQLiteQCEWCountyNAICSSource,
)
from babylon.economics.throughput.calculator import DefaultThroughputCalculator
from babylon.economics.throughput.supply_chain import DefaultSupplyChainAnalyzer

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from babylon.economics.tensor_registry import TensorRegistry


def create_economics_services(
    session_factory: Callable[[], Session],
    tensor_registry: TensorRegistry,
) -> dict[str, Any]:
    """Create all economics calculators wired with data sources.

    Resolves the full dependency graph between adapters, data sources,
    and calculators, returning a flat dict of service overrides suitable
    for unpacking into ServiceContainer.create().

    Args:
        session_factory: Callable returning a SQLAlchemy Session for
            querying the normalized reference database.
        tensor_registry: Pre-hydrated TensorRegistry with county tensor data.

    Returns:
        Dict with keys matching ServiceContainer calculator field names,
        all values non-None.
    """
    # Level 0: No dependencies
    basket = DefaultBasketVisibilityCalculator()
    imperial_rent = DefaultImperialRentCalculator()

    # Level 1: Data source adapters
    bea_national = SQLiteBEANationalGDPSource(session_factory)
    qcew_national = SQLiteQCEWNationalEmploymentSource(session_factory)
    unpaid_care = MVPUnpaidCareHoursSource()
    paid_care = QCEWCareAdapter()
    savings = DefaultSavingsRateSchedule()
    disp_data = HardcodedNationalDispossessionSource()
    bea_county = SQLiteBEACountyGDPSource(session_factory)
    qcew_county = SQLiteQCEWCountyNAICSSource(session_factory)

    # Level 2: Calculators with data deps
    melt = DefaultMELTCalculator(bea_national, qcew_national)
    capital = CapitalStockCalculator(tensor_registry)
    gamma = DefaultGammaIIICalculator(unpaid_care, paid_care)
    accumulation = DefaultAccumulationCalculator(savings)
    dispossession = DefaultDispossessionCalculator(disp_data)
    crisis = DefaultCrisisAmplifier()

    # Level 3: Calculators with calculator deps
    supply_chain = DefaultSupplyChainAnalyzer(qcew_county)
    throughput = DefaultThroughputCalculator(bea_county, qcew_county, supply_chain, melt)
    transition = DefaultClassTransitionEngine(accumulation, dispossession, crisis)

    return {
        "melt_calculator": melt,
        "basket_calculator": basket,
        "gamma_calculator": gamma,
        "capital_calculator": capital,
        "throughput_calculator": throughput,
        "transition_engine": transition,
        "imperial_rent_calculator": imperial_rent,
        "tensor_registry": tensor_registry,
    }


__all__ = ["create_economics_services"]
