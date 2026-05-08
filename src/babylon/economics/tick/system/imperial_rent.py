"""End-to-end Leontief imperial-rent pipeline (Spec 057).

Orchestrates the four upstream components into a per-tick step that writes
structurally-derived ``phi_hour`` values to ``CountyEconomicState``:

  BEA I-O matrix  →  import-share decomposition  →  Leontief inverse  →
  periphery wage coefficients  →  per-industry rent  →  QCEW
  employment-share allocation  →  per-county phi_hour

Per Spec 057 / FR-001 + Spec 058 deferred US2 decomposition: this module
holds the implementation body of ``TickDynamicsSystem._compute_imperial_rent``
which is now a thin 3-line delegation to :func:`compute` below.

Behavioral fence (per Spec 058 / FR-007 + Spec 057 plan.md): preserves the
return-type class (``dict[str, CountyEconomicState]``), exception class
hierarchy (``ValueError`` for FR-006 misalignment), and event-bus emission
ordering (sorted county FIPS, sorted BEA industries) of the original stub.

Three-layer axiom enforcement (research.md §R5):
  1. Source layer — ``DefaultPeripheryLaborCoefficientsSource`` warns on
     ratio < 1.0; passes value through unchanged.
  2. Calculator layer — ``ProductionChainRentCalculator.calculate`` clamps
     ``loss_ratio = np.maximum(loss_ratio, 0.0)`` at line 181.
  3. Data-model layer — ``CountyEconomicState.phi_hour: Field(..., ge=0)``
     would raise ``pydantic.ValidationError`` if a negative value reached
     this far (defense in depth).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.economics.tensor import NoDataSentinel
from babylon.engine.event_bus import Event
from babylon.models.enums import EventType
from babylon.models.events import QcewCarryForwardEvent

if TYPE_CHECKING:
    from babylon.economics.tick.types import CountyEconomicState, NationalTickParameters
    from babylon.engine.services import ServiceContainer

__all__ = ["compute"]


def compute(
    county_states: dict[str, CountyEconomicState],
    national_params: NationalTickParameters,
    services: ServiceContainer,
) -> dict[str, CountyEconomicState]:
    """Compute per-county phi_hour via the Leontief production chain.

    Replaces the no-op stub ``phi_hour = 0.0`` per FR-001. Body lives here
    (≤400 LOC per Spec 058 SC-002); the facade method on
    ``TickDynamicsSystem`` is a 3-line delegation that preserves the
    behavioral fence per Spec 058 / FR-007.

    Pipeline stages:
      1. Verify all 4 Spec 057 services are wired (graceful degradation
         to stub behavior if not — emits a single sentinel-marker event).
      2. Validate industry-list alignment between flow / periphery-wage /
         final-demand sources (FR-006; raises ValueError on mismatch).
      3. Decompose flow → A_d + A_m + L_d via ProductionChainDecomposer.
      4. Calculator: phi_vector = ProductionChainRentCalculator.calculate(...).
      5. Allocator: dict[fips, phi_hour] = IndustryToCountyAllocator.allocate(...).
      6. Write phi_hour to CountyEconomicState via model_copy.

    Sentinel propagation: if any upstream source returns NoDataSentinel
    for the tick year, the step is skipped (county_states returned unchanged)
    and a single ``QcewCarryForwardEvent(county_fips="*", look_back_distance=0)``
    sentinel-marker is published so observers can see the no-data condition.

    Args:
        county_states: Current per-county state dict (frozen Pydantic models).
        national_params: Year-scoped national context (provides tick year).
        services: ServiceContainer carrying the 4 Spec 057 fields plus
            event_bus, defines, and database session.

    Returns:
        New dict with ``phi_hour`` updated for every county that received an
        allocation. Counties absent from the allocator's result are
        passed through with their prior phi_hour preserved.
    """
    # -------------------------------------------------------------------------
    # Stage 1 — graceful-degradation guard
    # -------------------------------------------------------------------------
    if not _spec_057_pipeline_wired(services):
        _publish_pipeline_unwired_signal(services, year=national_params.year)
        return _stub_zero_pass_through(county_states)

    bea_industries: list[str] = services.bea_industries  # type: ignore[assignment]
    year = national_params.year

    # -------------------------------------------------------------------------
    # Stage 2 — fetch upstream data + sentinel propagation
    # -------------------------------------------------------------------------
    periphery = services.periphery_labor_source.get_coefficients(year)
    if isinstance(periphery, NoDataSentinel):
        _publish_no_data_signal(services, year=year, source_name="periphery_labor_source")
        return _stub_zero_pass_through(county_states)

    try:
        final_demand = services.final_demand_source.get_final_demand(year)
    except ValueError:
        _publish_no_data_signal(services, year=year, source_name="final_demand_source")
        return _stub_zero_pass_through(county_states)

    flow = services.production_chain_calculator.flow_source.get_direct_requirements(year)
    if isinstance(flow, NoDataSentinel):
        _publish_no_data_signal(services, year=year, source_name="inter_industry_flow_source")
        return _stub_zero_pass_through(county_states)

    # -------------------------------------------------------------------------
    # Stage 3 — industry-list alignment (FR-006, fail-fast)
    # -------------------------------------------------------------------------
    _validate_industry_alignment(
        bea_industries=bea_industries,
        periphery_industries=periphery.industries,
        flow_industries=flow.industries,
        final_demand_length=len(final_demand),
        year=year,
    )

    # -------------------------------------------------------------------------
    # Stage 4 — decompose + calculate per-industry rent
    # -------------------------------------------------------------------------
    shares = services.production_chain_calculator.import_shares_source.get_import_shares(year)
    decomposed = services.production_chain_calculator.decomposer.decompose(flow, shares)
    rent_result = services.production_chain_calculator.calculator.calculate(
        decomposed=decomposed,
        labor_coeffs=periphery,
        final_demand=final_demand,
        dept_mapping=None,
    )

    # -------------------------------------------------------------------------
    # Stage 5 — allocate per-industry rent to counties
    # -------------------------------------------------------------------------
    allocation = services.industry_county_allocator.allocate(
        phi_vector=rent_result.phi_vector,
        bea_industries=bea_industries,
        year=year,
    )
    if isinstance(allocation, NoDataSentinel):
        _publish_no_data_signal(services, year=year, source_name="industry_county_allocator")
        return _stub_zero_pass_through(county_states)

    # -------------------------------------------------------------------------
    # Stage 6 — write phi_hour to CountyEconomicState
    # -------------------------------------------------------------------------
    return _apply_allocation(county_states, allocation)


# =============================================================================
# Helpers
# =============================================================================


def _spec_057_pipeline_wired(services: ServiceContainer) -> bool:
    """Returns True iff all 4 Spec 057 services + bea_industries are non-None."""
    return all(
        getattr(services, attr, None) is not None
        for attr in (
            "periphery_labor_source",
            "final_demand_source",
            "industry_county_allocator",
            "production_chain_calculator",
            "bea_industries",
        )
    )


def _publish_pipeline_unwired_signal(services: ServiceContainer, *, year: int) -> None:
    """Emit one sentinel QcewCarryForwardEvent signaling pipeline-not-wired.

    Per data-model.md ServiceContainer "Validation invariant": the
    ``county_fips="*"`` + ``look_back_distance=0`` payload is the
    "Spec 057 pipeline not wired" sentinel pattern. (Originally proposed as
    -1 in the contract but bound-tightened to ge=0 at the model layer; we
    use 0 + the wildcard fips marker to convey the same semantic.)
    """
    typed = QcewCarryForwardEvent(
        tick=0,
        county_fips="*",
        year=year,
        look_back_year=year,
        look_back_distance=0,
    )
    services.event_bus.publish(
        Event(
            type=EventType.CALIBRATION_QCEW_CARRY_FORWARD.value,
            tick=0,
            payload=typed.model_dump(),
        )
    )


def _publish_no_data_signal(services: ServiceContainer, *, year: int, source_name: str) -> None:
    """Emit one sentinel QcewCarryForwardEvent signaling source returned NoData.

    Same wildcard-fips pattern as ``_publish_pipeline_unwired_signal``; the
    payload's ``year`` and the bus history's emission timing identify which
    source had no data. (Source-specific subscribers can correlate via the
    EventBus history sequence with the upstream source query.)
    """
    typed = QcewCarryForwardEvent(
        tick=0,
        county_fips="*",
        year=year,
        look_back_year=year,
        look_back_distance=0,
    )
    services.event_bus.publish(
        Event(
            type=EventType.CALIBRATION_QCEW_CARRY_FORWARD.value,
            tick=0,
            payload={**typed.model_dump(), "source_name": source_name},
        )
    )


def _stub_zero_pass_through(
    county_states: dict[str, CountyEconomicState],
) -> dict[str, CountyEconomicState]:
    """Return county_states unchanged (passes through prior phi_hour values).

    Per FR-004 + Clarifications 2026-05-08: counties absent from the
    allocator's result are NOT silently zeroed; they keep their prior
    phi_hour. The graceful-degradation path uses the same semantics.
    """
    return dict(county_states)


def _validate_industry_alignment(
    *,
    bea_industries: list[str],
    periphery_industries: list[str],
    flow_industries: list[str],
    final_demand_length: int,
    year: int,
) -> None:
    """Validate that the 3 sources publish industry lists consistent with the
    configured ``services.bea_industries`` for the tick year (FR-006 +
    research.md §R7). Raises ``ValueError`` with a bounded diagnostic.

    Raises:
        ValueError: if the periphery, flow, or final_demand industry list
            does not align with ``bea_industries``. The diagnostic is
            bounded (≤10 codes per side) per research.md §R7.
    """
    n = len(bea_industries)
    if len(periphery_industries) != n:
        raise ValueError(
            f"BEA industry list mismatch for year {year}: "
            f"periphery_labor_source has {len(periphery_industries)} "
            f"industries, expected {n}"
        )
    if len(flow_industries) != n:
        raise ValueError(
            f"BEA industry list mismatch for year {year}: "
            f"inter_industry_flow_source has {len(flow_industries)} "
            f"industries, expected {n}"
        )
    if final_demand_length != n:
        raise ValueError(
            f"BEA industry list mismatch for year {year}: "
            f"final_demand_source has length {final_demand_length}, expected {n}"
        )

    # Order-sensitive check on the periphery + flow lists (positional vectors).
    for label, source_industries in (
        ("periphery_labor_source", periphery_industries),
        ("inter_industry_flow_source", flow_industries),
    ):
        if source_industries == bea_industries:
            continue
        # Bounded diagnostic per R7 — ≤10 codes per side
        a_set, b_set = set(bea_industries), set(source_industries)
        missing = sorted(a_set - b_set)[:10]
        extra = sorted(b_set - a_set)[:10]
        raise ValueError(
            f"BEA industry list mismatch for year {year}: {label} list "
            f"differs from configured services.bea_industries. "
            f"Missing from {label}: {missing}; "
            f"Extra in {label}: {extra}"
        )


def _apply_allocation(
    county_states: dict[str, CountyEconomicState],
    allocation: dict[str, float],
) -> dict[str, CountyEconomicState]:
    """Update phi_hour on every county present in the allocation.

    Counties absent from the allocation are passed through unchanged
    (per FR-004 — no silent zero).
    """
    updated: dict[str, CountyEconomicState] = {}
    for fips, county in county_states.items():
        if fips in allocation:
            updated[fips] = county.model_copy(update={"phi_hour": allocation[fips]})
        else:
            updated[fips] = county
    return updated
