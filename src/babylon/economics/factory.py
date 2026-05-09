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
    from babylon.reference.database import get_normalized_session_factory
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

from babylon.core.protocol_kit import SourceRegistry
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
    DefaultMELTCalculator,
)
from babylon.economics.melt.adapters import (
    SQLiteBEANationalGDPSource,
    SQLiteQCEWNationalEmploymentSource,
)
from babylon.economics.melt.basket_visibility import BasketVisibilityCalculator
from babylon.economics.throughput.adapters import (
    SQLiteBEACountyGDPSource,
    SQLiteQCEWCountyNAICSSource,
)
from babylon.economics.throughput.calculator import DefaultThroughputCalculator
from babylon.economics.throughput.supply_chain import DefaultSupplyChainAnalyzer

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from babylon.economics.tensor_registry import TensorRegistry


# Spec 058 / FR-006 / commit 6: process-wide registry holding the parameterless
# subset of melt+gamma Default* classes (per the SC-004-reformulation rationale
# in plan.md §R5). Lazy-constructed on first access; the dep-laden 3 classes
# (MELT, RentDifferential, GammaIII) stay constructed in the create_*_services
# topological resolution below.
_BUILTIN_REGISTRY: SourceRegistry | None = None


def _get_builtin_registry() -> SourceRegistry:
    """Return the process-wide registry, lazy-constructing on first access."""
    global _BUILTIN_REGISTRY
    if _BUILTIN_REGISTRY is None:
        _BUILTIN_REGISTRY = SourceRegistry().builtin_economics()
    return _BUILTIN_REGISTRY


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
    # Level 0: No dependencies — pulled from SourceRegistry per Spec 058 / FR-006.
    # The registry holds the parameterless subset of migrated melt+gamma Default*
    # classes; the dep-laden classes (MELT, etc.) stay constructed below in
    # explicit topological order (SC-004 not-met-by-design — see plan.md §R5).
    registry = _get_builtin_registry()
    basket = registry.get(BasketVisibilityCalculator)

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
        "tensor_registry": tensor_registry,
    }


def load_fred_series_from_db(
    session_factory: Callable[[], Session],
) -> dict[str, dict[int, float]]:
    """Load FRED time series from 3NF SQLite into cache dict.

    Queries fred_series + fred_national tables for Volume III series
    and returns {series_id: {year: annual_avg_value}} format.

    Feature: 024-capital-volume-iii

    Args:
        session_factory: Callable returning a SQLAlchemy Session.

    Returns:
        Dict mapping FRED series IDs to year->value dicts.
        Empty dict for series with no observations.
    """
    from sqlalchemy import text

    # Volume III FRED series IDs
    vol3_series = [
        "FEDFUNDS",
        "DGS10",
        "BAA10Y",
        "TCMDO",
        "GFDEBTN",
        "NCBEILQ027S",
        "B230RC0Q173SBEA",
        "A054RC1Q027SBEA",
        "CPIAUCSL",
        "GDPDEF",
    ]

    # Unit normalisation rules applied at load time so all downstream
    # code works with consistent units: actual dollars, decimal rates.
    # FRED stores percent series as e.g. 1.68 (meaning 1.68%).
    # Dollar aggregates vary: GFDEBTN/TCMDO/NCBEILQ027S/B230RC0 are in
    # "Millions of Dollars"; A054RC1Q027SBEA is NIPA "Billions of Dollars".
    _pct_to_decimal = {"FEDFUNDS", "DGS10", "BAA10Y"}  # divide by 100
    _millions_to_dollars = {
        "GFDEBTN",
        "TCMDO",
        "NCBEILQ027S",
        "B230RC0Q173SBEA",
    }  # multiply by 1e6
    _billions_to_dollars = {
        "A054RC1Q027SBEA",  # NIPA Table: "Billions of Dollars"
    }  # multiply by 1e9

    result: dict[str, dict[int, float]] = {}
    with session_factory() as session:
        placeholders = ", ".join(f"'{s}'" for s in vol3_series)
        # Schema: dim_fred_series(series_id PK int, series_code str, ...)
        #         fact_fred_national(series_id FK, time_id FK, value)
        #         dim_time(time_id PK, year, is_annual bool)
        raw_query = text(f"""
            SELECT fs.series_code, dt.year, AVG(fn.value) AS avg_value
            FROM fact_fred_national fn
            JOIN dim_fred_series fs ON fn.series_id = fs.series_id
            JOIN dim_time dt ON fn.time_id = dt.time_id
            WHERE fs.series_code IN ({placeholders})
            GROUP BY fs.series_code, dt.year
            ORDER BY fs.series_code, dt.year
        """)
        rows = session.execute(raw_query)
        for row in rows:
            code = str(row[0])
            year = int(row[1])
            value = float(row[2])
            if code in _pct_to_decimal:
                value = value / 100.0
            elif code in _millions_to_dollars:
                value = value * 1_000_000.0
            elif code in _billions_to_dollars:
                value = value * 1_000_000_000.0
            if code not in result:
                result[code] = {}
            result[code][year] = value

    return result


def create_financial_services(
    fred_series_cache: dict[str, dict[int, float]] | None = None,
) -> dict[str, Any]:
    """Create all Volume III financial calculators wired with real data sources.

    Resolves the dependency graph for national financial state and county-level
    surplus distribution. Uses FRED API for interest rates and credit aggregates,
    Z.1 hardcoded defaults for balance sheet data, and Census/ACS defaults for
    housing data.

    Feature: 024-capital-volume-iii

    Args:
        fred_series_cache: Optional pre-loaded FRED series data as
            {series_id: {year: value}}. If None, uses hardcoded defaults.

    Returns:
        Dict with keys matching ServiceContainer financial field names.
    """
    from babylon.economics.counter_tendencies.calculator import (
        DefaultCounterTendencyCalculator,
    )
    from babylon.economics.credit.credit_cycle import DefaultCreditCycleDetector
    from babylon.economics.credit.data_sources import (
        FredCreditAggregateAdapter,
        FredInterestRateAdapter,
    )
    from babylon.economics.credit.fictitious_capital import (
        DefaultFictitiousCapitalCalculator,
    )
    from babylon.economics.credit.interest import DefaultInterestCalculator
    from babylon.economics.data_adapters import CensusHousingLoader, Z1Loader
    from babylon.economics.distribution.calculator import (
        DefaultDistributionCalculator,
    )
    from babylon.economics.financial_crisis.assessment import (
        DefaultFinancialCrisisAssessor,
    )
    from babylon.economics.monetary.converter import DefaultValueBasisConverter
    from babylon.economics.rent.calculator import (
        DefaultHousingDecompositionCalculator,
        DefaultRentCalculator,
    )

    # Build FRED series cache (use provided or empty)
    series: dict[str, dict[int, float]] = fred_series_cache or {}

    # Level 0: Data source adapters
    interest_rates = FredInterestRateAdapter(series)
    credit_aggregates = FredCreditAggregateAdapter(series)
    z1 = Z1Loader()  # Uses hardcoded Z.1 defaults
    housing = CensusHousingLoader()  # Uses hardcoded Census defaults

    # Level 0.5: Price index adapter (wraps FRED CPI + GDP deflator)
    class _FredPriceIndexAdapter:
        """Adapter: FRED CPIAUCSL/GDPDEF -> PriceIndexSource."""

        def get_cpi(self, year: int) -> float | None:
            return series.get("CPIAUCSL", {}).get(year)

        def get_gdp_deflator(self, year: int) -> float | None:
            return series.get("GDPDEF", {}).get(year)

        def get_total_labor_hours(self, _year: int) -> float | None:
            # Derive from QCEW employment * 2080 hours/year (standard)
            # For now return None — will be populated when QCEW is loaded
            return None

        def get_nominal_gdp(self, _year: int) -> float | None:
            return None  # Populated via BEA data, not in FRED cache

    # Level 1: National-level calculators
    interest_calc = DefaultInterestCalculator(interest_rates)
    credit_cycle = DefaultCreditCycleDetector()
    fictitious_calc = DefaultFictitiousCapitalCalculator(credit_aggregates, z1)
    counter_tendency = DefaultCounterTendencyCalculator()
    value_converter = DefaultValueBasisConverter(_FredPriceIndexAdapter())

    # Level 2: County-level calculators
    # Distribution needs rental income, taxes, and national interest data.
    # These use BEA NIPA series from FRED cache.
    class _FredRentalAdapter:
        """Adapter: FRED B230RC0Q173SBEA -> RentalIncomeSource."""

        def get_rental_income(self, _fips: str, year: int) -> float | None:
            # National rental income, not county-specific
            return series.get("B230RC0Q173SBEA", {}).get(year)

    class _FredTaxAdapter:
        """Adapter: FRED A054RC1Q027SBEA -> TaxOnSurplusSource."""

        def get_corporate_tax(self, _fips: str, year: int) -> float | None:
            return series.get("A054RC1Q027SBEA", {}).get(year)

    class _FredInterestIncomeAdapter:
        """Adapter: derives interest income from rates and credit aggregates."""

        def get_national_net_interest(self, year: int) -> float | None:
            rate = interest_rates.get_federal_funds_rate(year)
            credit = credit_aggregates.get_total_credit(year)
            if rate is None or credit is None:
                return None
            return rate * credit  # Approximate net interest = rate * total credit

    distribution = DefaultDistributionCalculator(
        rental_source=_FredRentalAdapter(),
        tax_source=_FredTaxAdapter(),
        interest_source=_FredInterestIncomeAdapter(),
    )

    # Rent calculators use Census data

    class _DefaultCountyRentalAdapter:
        """Stub: returns None until BEA REIS county data is loaded."""

        def get_agricultural_rent(self, _fips: str, _year: int) -> float | None:
            return None

        def get_resource_rent(self, _fips: str, _year: int) -> float | None:
            return None

        def get_urban_rent(self, _fips: str, _year: int) -> float | None:
            return None

    rent_calc = DefaultRentCalculator(_DefaultCountyRentalAdapter())
    # Default 5% interest rate for rent capitalization; overridden per-tick
    _default_interest = 0.05
    housing_calc = DefaultHousingDecompositionCalculator(housing, _default_interest)
    crisis_assessor = DefaultFinancialCrisisAssessor()

    return {
        "distribution_calculator": distribution,
        "interest_calculator": interest_calc,
        "credit_cycle_detector": credit_cycle,
        "fictitious_capital_calculator": fictitious_calc,
        "rent_calculator": rent_calc,
        "housing_calculator": housing_calc,
        "counter_tendency_calculator": counter_tendency,
        "value_basis_converter": value_converter,
        "financial_crisis_assessor": crisis_assessor,
        "z1_source": z1,
        "housing_data_source": housing,
    }


def load_circulation_series_from_db(
    session_factory: Callable[[], Session],
) -> dict[str, dict[int, float]]:
    """Load FRED circulation series from 3NF SQLite into cache dict.

    Queries fred_series + fred_national tables for Volume II circulation series
    and returns {series_id: {year: annual_avg_value}} with unit conversions applied.

    Unit conversions:
        - MNFCTIRSA, ISRATIO: months → days (× 30.4)
        - AMDMNO: millions of dollars → dollars (× 1e6)
        - A271RX1Q020SBEA, GPDI: billions of dollars → dollars (× 1e9)

    Feature: 023-capital-volume-ii

    Args:
        session_factory: Callable returning a SQLAlchemy Session.

    Returns:
        Dict mapping FRED series IDs to year->value dicts.
        Empty dict for series with no observations.
    """
    from sqlalchemy import text

    _circulation_series = [
        "ISRATIO",  # Total Business: Inventories to Sales Ratio (months)
        "GPDI",  # Gross Private Domestic Investment (billions of dollars)
    ]

    # Unit normalisation rules
    _ratio_to_days = {"ISRATIO"}  # months → days (× 30.4)
    _millions_to_dollars: set[str] = set()
    _billions_to_dollars = {"GPDI"}  # × 1e9

    result: dict[str, dict[int, float]] = {}
    with session_factory() as session:
        placeholders = ", ".join(f"'{s}'" for s in _circulation_series)
        raw_query = text(f"""
            SELECT fs.series_code, dt.year, AVG(fn.value) AS avg_value
            FROM fact_fred_national fn
            JOIN dim_fred_series fs ON fn.series_id = fs.series_id
            JOIN dim_time dt ON fn.time_id = dt.time_id
            WHERE fs.series_code IN ({placeholders})
            GROUP BY fs.series_code, dt.year
            ORDER BY fs.series_code, dt.year
        """)
        rows = session.execute(raw_query)
        for row in rows:
            code = str(row[0])
            year = int(row[1])
            value = float(row[2])
            if code in _ratio_to_days:
                value = value * 30.4
            elif code in _millions_to_dollars:
                value = value * 1_000_000.0
            elif code in _billions_to_dollars:
                value = value * 1_000_000_000.0
            if code not in result:
                result[code] = {}
            result[code][year] = value

    return result


def create_circulation_services(
    circulation_series_cache: dict[str, dict[int, float]],
    fred_series_cache: dict[str, dict[int, float]],  # noqa: ARG001 reserved for future use
) -> dict[str, Any]:
    """Create Volume II circulation calculators wired with real FRED data.

    Builds three service adapters for the circulation layer:
    - turnover_profile_source: NAICS sector turnover profiles
    - inventory_data_source: National inventory levels / days-of-inventory
    - depreciation_data_source: Fixed capital depreciation and replacement

    Feature: 023-capital-volume-ii

    Args:
        circulation_series_cache: Pre-loaded circulation FRED series as
            {series_id: {year: value}} with unit conversions applied.
        fred_series_cache: Pre-loaded Vol III FRED series (reused cache).

    Returns:
        Dict with keys matching ServiceContainer circulation field names.
    """
    from babylon.economics.circulation.turnover import DefaultTurnoverProfileSource

    series = circulation_series_cache  # local alias

    class _InventoryDataSource:
        """Adapter: FRED ISRATIO -> inventory days data.

        ISRATIO (Total Business: Inventories to Sales Ratio) is used for
        both raw and finished goods days-of-inventory. Unit conversion
        (months → days × 30.4) is applied in load_circulation_series_from_db().
        National inventory stock is derived as GPDI × 0.2 (rough proxy).
        """

        def get_days_inventory_raw(self, year: int) -> float | None:
            return series.get("ISRATIO", {}).get(year)

        def get_days_inventory_finished(self, year: int) -> float | None:
            return series.get("ISRATIO", {}).get(year)

        def get_national_inventory(self, year: int) -> float | None:
            # Derive national inventory stock from GPDI (20% proxy)
            gpdi = series.get("GPDI", {}).get(year)
            return gpdi * 0.20 if gpdi is not None else None

    class _DepreciationDataSource:
        """Adapter: FRED GPDI -> depreciation data.

        GPDI (Gross Private Domestic Investment) used as a proxy for
        replacement investment. Annual depreciation (CCA) is approximated
        as 70% of GPDI following BEA Fixed Asset Tables ratios.
        """

        def get_annual_depreciation(self, year: int) -> float | None:
            gpdi = series.get("GPDI", {}).get(year)
            return gpdi * 0.70 if gpdi is not None else None

        def get_gross_investment(self, year: int) -> float | None:
            return series.get("GPDI", {}).get(year)

    return {
        "turnover_profile_source": DefaultTurnoverProfileSource(),
        "inventory_data_source": _InventoryDataSource(),
        "depreciation_data_source": _DepreciationDataSource(),
    }


def load_vol1_series_from_db(
    session_factory: Callable[[], Session],
) -> dict[str, dict[int, float]]:
    """Load FRED Vol I production series from 3NF SQLite into cache dict.

    Queries fred_series + fred_national tables for Volume I series with unit
    conversions applied. OPHNFB and HOANBS are index values (2012=100) stored
    as-is; NROU is a percent and is converted to decimal.

    Feature: 021-capital-volume-i

    Args:
        session_factory: Callable returning a SQLAlchemy Session.

    Returns:
        Dict mapping FRED series IDs to year->value dicts.
    """
    from sqlalchemy import text

    _vol1_series = ["OPHNFB", "HOANBS", "NROU", "UNRATE"]
    _pct_to_decimal = {"NROU", "UNRATE"}  # percent → decimal (÷ 100)

    result: dict[str, dict[int, float]] = {}
    with session_factory() as session:
        placeholders = ", ".join(f"'{s}'" for s in _vol1_series)
        raw_query = text(f"""
            SELECT fs.series_code, dt.year, AVG(fn.value) AS avg_value
            FROM fact_fred_national fn
            JOIN dim_fred_series fs ON fn.series_id = fs.series_id
            JOIN dim_time dt ON fn.time_id = dt.time_id
            WHERE fs.series_code IN ({placeholders})
            GROUP BY fs.series_code, dt.year
            ORDER BY fs.series_code, dt.year
        """)
        rows = session.execute(raw_query)
        for row in rows:
            code = str(row[0])
            year = int(row[1])
            value = float(row[2])
            if code in _pct_to_decimal:
                value = value / 100.0
            if code not in result:
                result[code] = {}
            result[code][year] = value

    return result


def create_vol1_services(
    vol1_series_cache: dict[str, dict[int, float]],
    fred_series_cache: dict[str, dict[int, float]],  # noqa: ARG001 reserved for future use
) -> dict[str, Any]:
    """Create Volume I production calculators wired with real FRED data.

    Provides three data source adapters for the Vol I production layer:
    - reserve_army_data_source: derives ReserveArmyState from UNRATE + NROU
    - productivity_data_source: derives WorkingDayState from OPHNFB + HOANBS
    - dispossession_data_source: wraps hardcoded 2007-2020 + UNRATE proxy for 2021+

    Feature: 021-capital-volume-i

    Args:
        vol1_series_cache: Pre-loaded Vol I FRED series (OPHNFB, HOANBS, NROU).
        fred_series_cache: Pre-loaded Vol III FRED series containing UNRATE.

    Returns:
        Dict with keys matching ServiceContainer Vol I field names.
    """
    from babylon.economics.dynamics.hardcoded_data import HardcodedNationalDispossessionSource
    from babylon.economics.reserve_army.types import ReserveArmyState
    from babylon.economics.working_day.types import WorkingDayState

    _HOURS_BASELINE = 34.5  # US average weekly hours baseline

    class _FredReserveArmyAdapter:
        """Adapter: FRED UNRATE + NROU -> ReserveArmyState.

        Decomposes unemployment into cyclical (floating) and structural (latent)
        reserve army components using Marx's four-category schema.
        Normalized to labor_force = 1_000_000 so reserve_ratio is accurate.
        """

        def get_unemployment_decomposition(
            self,
            _fips: str,
            year: int,
        ) -> ReserveArmyState | None:
            unrate = vol1_series_cache.get("UNRATE", {}).get(year)
            nrou = vol1_series_cache.get("NROU", {}).get(year)
            if unrate is None:
                return None
            nrou_val = nrou if nrou is not None else 0.04  # fallback 4% structural
            labor_force = 1_000_000
            floating = int(labor_force * max(0.0, unrate - nrou_val))
            latent = int(labor_force * nrou_val)
            stagnant = int(labor_force * unrate * 0.4)
            pauperized = int(labor_force * 0.02)
            return ReserveArmyState(
                fips_code="00000",
                year=min(max(year, 2005), 2030),
                floating_reserve=floating,
                latent_reserve=latent,
                stagnant_reserve=stagnant,
                pauperized=pauperized,
                labor_force=labor_force,
            )

    class _FredProductivityAdapter:
        """Adapter: FRED OPHNFB + HOANBS -> WorkingDayState.

        Converts index values (2012=100) to absolute measures:
        - labor_intensity_index = OPHNFB / 100 (1.0 = 2012 baseline)
        - avg_weekly_hours = (HOANBS / 100) × 34.5 hours
        Returns national productivity applied uniformly across NAICS sectors.
        """

        def get_working_day_state(
            self,
            fips_code: str,
            naics_sector: str,
            year: int,
        ) -> WorkingDayState | None:
            ophnfb = vol1_series_cache.get("OPHNFB", {}).get(year)
            hoanbs = vol1_series_cache.get("HOANBS", {}).get(year)
            intensity = ophnfb / 100.0 if ophnfb is not None else 1.0
            hours = (hoanbs / 100.0) * _HOURS_BASELINE if hoanbs is not None else _HOURS_BASELINE
            clamped_year = min(max(year, 2005), 2030)
            return WorkingDayState(
                fips_code=fips_code if len(fips_code) == 5 else "00000",
                naics_sector=naics_sector[:2] if naics_sector else "00",
                year=clamped_year,
                avg_weekly_hours=round(hours, 2),
                labor_intensity_index=round(intensity, 4),
            )

    _hardcoded = HardcodedNationalDispossessionSource()

    class _FredDispossessionAdapter:
        """Adapter: wraps hardcoded 2007-2020 + FRED UNRATE proxy for 2021+.

        For 2007-2020: delegates to HardcodedNationalDispossessionSource.
        For 2021+: derives rates from national UNRATE using empirical proxies:
          foreclosure ≈ max(0.001, UNRATE × 0.08)
          bankruptcy  ≈ max(0.001, UNRATE × 0.07)
          eviction    ≈ max(0.015, UNRATE × 0.60 + 0.015)
        """

        def get_foreclosure_rate(self, fips: str, year: int) -> float | None:
            if year <= 2020:
                return _hardcoded.get_foreclosure_rate(fips, year)
            unrate = vol1_series_cache.get("UNRATE", {}).get(year)
            return max(0.001, unrate * 0.08) if unrate is not None else None

        def get_bankruptcy_rate(self, fips: str, year: int) -> float | None:
            if year <= 2020:
                return _hardcoded.get_bankruptcy_rate(fips, year)
            unrate = vol1_series_cache.get("UNRATE", {}).get(year)
            return max(0.001, unrate * 0.07) if unrate is not None else None

        def get_eviction_rate(self, fips: str, year: int) -> float | None:
            if year <= 2020:
                return _hardcoded.get_eviction_rate(fips, year)
            unrate = vol1_series_cache.get("UNRATE", {}).get(year)
            return max(0.015, unrate * 0.60 + 0.015) if unrate is not None else None

    return {
        "reserve_army_data_source": _FredReserveArmyAdapter(),
        "productivity_data_source": _FredProductivityAdapter(),
        "dispossession_data_source": _FredDispossessionAdapter(),
    }


__all__ = [
    "create_circulation_services",
    "create_economics_services",
    "create_financial_services",
    "create_vol1_services",
    "load_circulation_series_from_db",
    "load_fred_series_from_db",
    "load_vol1_series_from_db",
]
