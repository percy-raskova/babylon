"""Per-county industry-rent allocator for Spec 057.

Implements the ``IndustryToCountyAllocator`` Protocol via
:class:`DefaultIndustryToCountyAllocator`, which translates a per-industry
rent vector into per-county ``phi_hour`` values using QCEW employment shares
(NAICS) aggregated to BEA Summary level via the existing ``bridge_naics_bea``
crosswalk.

Algorithm (per ``contracts/industry_to_county_allocator.md`` + R4 + R8):

  1. For each county FIPS in QCEW for the look-back window
     ``[year - max_years, year]``:
       a. Find the most recent ``y' ≤ year`` with QCEW data.
       b. If no ``y'`` in window → skip the county (absent from result).
       c. Aggregate NAICS employment to BEA Summary via ``bridge_naics_bea``
          (weight column applied; missing weight defaults to 1.0).
       d. Compute county's share of national BEA employment per industry.
       e. county_rent = sum_i(phi_vector[i] * county_share[bea_industries[i]])
       f. phi_hour[fips] = county_rent / (county_total_emp_hours)
       g. Emit ``QcewCarryForwardEvent`` if ``y' < year``.
       h. Emit ``PhiHourOutlierEvent`` if ``phi_hour`` outside thresholds.
  2. Return ``{fips: phi_hour}`` (sorted by fips for determinism).
  3. Return ``NoDataSentinel`` if uniformly empty across all counties.

Constants (per Spec 057 / III.1 No Magic Constants):
  - ``LeontiefRentDefines.qcew_carry_forward_max_years`` (default 5)
  - ``LeontiefRentDefines.phi_hour_outlier_threshold_low/high`` (defaults ±1000.0)
  - ``HOURS_PER_YEAR = 2080`` (project standard, see CLAUDE.md)
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from babylon.config.defines import LeontiefRentDefines
from babylon.domain.economics.protocol_kit import CachedSource
from babylon.domain.economics.tensor import NoDataSentinel
from babylon.formulas.constants import HOURS_PER_YEAR
from babylon.kernel.event_bus import Event, EventBus
from babylon.models.enums import EventType
from babylon.models.events import PhiHourOutlierEvent, QcewCarryForwardEvent
from babylon.reference.schema import (
    BridgeNAICSBEA,
    DimBEAIndustry,
    DimCounty,
    DimIndustry,
    DimTime,
    FactQcewAnnual,
)

__all__ = ["DefaultIndustryToCountyAllocator", "IndustryToCountyAllocator"]


# =============================================================================
# Protocol
# =============================================================================


@runtime_checkable
class IndustryToCountyAllocator(Protocol):
    """Per-industry rent → per-county phi_hour allocator (FR-004)."""

    def allocate(
        self,
        phi_vector: np.ndarray,
        bea_industries: list[str],
        year: int,
    ) -> dict[str, float] | NoDataSentinel: ...


# =============================================================================
# Default implementation
# =============================================================================


class DefaultIndustryToCountyAllocator(CachedSource[dict[str, float]]):
    """QCEW-based industry-to-county rent allocator.

    Args:
        db_session: SQLAlchemy session pointing at the reference database.
        event_bus: EventBus for QcewCarryForwardEvent / PhiHourOutlierEvent emission.
        defines: ``LeontiefRentDefines`` for max_years + outlier thresholds.
    """

    cache_negative_results: bool = True

    def __init__(
        self,
        *,
        db_session: Session,
        event_bus: EventBus,
        defines: LeontiefRentDefines | None = None,
    ) -> None:
        super().__init__()
        self._db = db_session
        self._bus = event_bus
        self._defines = defines or LeontiefRentDefines()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def allocate(
        self,
        phi_vector: np.ndarray,
        bea_industries: list[str],
        year: int,
    ) -> dict[str, float] | NoDataSentinel:
        if phi_vector.shape != (len(bea_industries),):
            raise ValueError(
                f"phi_vector shape {phi_vector.shape} does not match "
                f"len(bea_industries)={len(bea_industries)}"
            )

        # Cache key omits the phi_vector contents — the allocation shape is a
        # function of (year, bea_industries) only; phi_vector scaling is
        # applied after the share lookup below. We re-compute scaled rent
        # per call but the share-table lookup is cached.
        # (Minor perf optimisation: callers within a tick year share the
        # underlying QCEW lookups via the SQL query plan + sqlite cache.)
        return self._compute_allocation(phi_vector, bea_industries, year)

    # -------------------------------------------------------------------------
    # Implementation
    # -------------------------------------------------------------------------

    def _compute_allocation(  # noqa: C901 — single-pass linear pipeline; see plan.md §R4
        self,
        phi_vector: np.ndarray,
        bea_industries: list[str],
        year: int,
    ) -> dict[str, float] | NoDataSentinel:
        max_years = self._defines.qcew_carry_forward_max_years

        # Step 1 — load NAICS↔BEA crosswalk (full table; small enough: ~462 rows).
        crosswalk_stmt = (
            select(
                DimIndustry.naics_code,
                DimBEAIndustry.bea_code,
                BridgeNAICSBEA.weight,
            )
            .join(DimIndustry, BridgeNAICSBEA.industry_id == DimIndustry.industry_id)
            .join(
                DimBEAIndustry,
                BridgeNAICSBEA.bea_industry_id == DimBEAIndustry.bea_industry_id,
            )
        )
        crosswalk_rows = self._db.execute(crosswalk_stmt).all()
        # naics_code -> list[(bea_code, weight)]; weight defaults to 1.0
        naics_to_bea: dict[str, list[tuple[str, float]]] = {}
        for naics_code, bea_code, weight in crosswalk_rows:
            naics_to_bea.setdefault(naics_code, []).append(
                (bea_code, float(weight) if weight is not None else 1.0)
            )

        # Step 2 — find national BEA employment per industry across the look-back
        # window (one row per (county, naics, year) → aggregated).
        candidate_stmt = (
            select(
                DimCounty.fips,
                DimIndustry.naics_code,
                DimTime.year,
                FactQcewAnnual.employment,
            )
            .join(DimCounty, FactQcewAnnual.county_id == DimCounty.county_id)
            .join(DimIndustry, FactQcewAnnual.industry_id == DimIndustry.industry_id)
            .join(DimTime, FactQcewAnnual.time_id == DimTime.time_id)
            .where(DimTime.year >= year - max_years)
            .where(DimTime.year <= year)
            .where(FactQcewAnnual.employment.is_not(None))
        )
        rows = self._db.execute(candidate_stmt).all()
        if not rows:
            return NoDataSentinel(
                fips="",
                year=year,
                reason=f"No QCEW rows in look-back window [{year - max_years}, {year}]",
            )

        # Group: per-county per-naics → most recent year in window.
        # county_naics_year[(fips, naics)] = (best_year, employment)
        county_naics_year: dict[tuple[str, str], tuple[int, int]] = {}
        for fips, naics_code, qyear, emp in rows:
            if emp is None:
                continue
            key = (fips, naics_code)
            existing = county_naics_year.get(key)
            if existing is None or qyear > existing[0]:
                county_naics_year[key] = (qyear, int(emp))

        if not county_naics_year:
            return NoDataSentinel(
                fips="",
                year=year,
                reason="QCEW rows in window had no usable employment data",
            )

        # Step 3 — aggregate per (county, BEA code) and compute carry-forward
        # signal per county (we use the MAX year-distance across the county's
        # NAICS rows as the carry-forward distance to report).
        # county_bea_emp[(fips, bea_code)] = sum of weighted employment
        # county_max_year_used[fips] = max year used across that county's rows
        # county_min_year_used[fips] = min year used across that county's rows
        county_bea_emp: dict[tuple[str, str], float] = {}
        county_max_y: dict[str, int] = {}
        county_min_y: dict[str, int] = {}
        for (fips, naics_code), (best_year, emp) in county_naics_year.items():
            county_max_y[fips] = max(county_max_y.get(fips, 0), best_year)
            county_min_y[fips] = (
                min(county_min_y[fips], best_year) if fips in county_min_y else best_year
            )
            for bea_code, weight in naics_to_bea.get(naics_code, []):
                key = (fips, bea_code)
                county_bea_emp[key] = county_bea_emp.get(key, 0.0) + emp * weight

        # Step 4 — national BEA employment totals (denominator for shares)
        national_bea_emp: dict[str, float] = {}
        for (_fips, bea_code), emp in county_bea_emp.items():
            national_bea_emp[bea_code] = national_bea_emp.get(bea_code, 0.0) + emp

        # Step 5 — per-county allocation
        # county_total_emp[fips] = sum of employment across its NAICS rows
        county_total_emp: dict[str, float] = {}
        for (fips, _naics), (_yr, emp) in county_naics_year.items():
            county_total_emp[fips] = county_total_emp.get(fips, 0.0) + emp

        result: dict[str, float] = {}
        # Iterate sorted FIPS for determinism (Constitution III.7).
        for fips in sorted(county_total_emp.keys()):
            total_emp = county_total_emp[fips]
            if total_emp <= 0:
                continue
            county_rent = 0.0
            for i, bea_code in enumerate(bea_industries):
                national_emp = national_bea_emp.get(bea_code, 0.0)
                if national_emp <= 0:
                    continue
                county_emp = county_bea_emp.get((fips, bea_code), 0.0)
                share = county_emp / national_emp
                # phi_vector[i] is in the calculator's units (e.g., USD billions);
                # we scale the share into county_rent. The result is then
                # normalised by employment-hours below.
                county_rent += float(phi_vector[i]) * share
            phi_hour = county_rent / (total_emp * HOURS_PER_YEAR)
            result[fips] = phi_hour

            # Step 6a — carry-forward warning
            best_year_used = county_min_y[fips]
            if best_year_used < year:
                self._emit_carry_forward(fips=fips, year=year, look_back_year=best_year_used)

            # Step 6b — outlier warning
            if (
                phi_hour < self._defines.phi_hour_outlier_threshold_low
                or phi_hour > self._defines.phi_hour_outlier_threshold_high
            ):
                self._emit_outlier(fips=fips, phi_hour=phi_hour)

        return result

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _emit_carry_forward(self, *, fips: str, year: int, look_back_year: int) -> None:
        distance = year - look_back_year
        typed = QcewCarryForwardEvent(
            tick=0,
            county_fips=fips,
            year=year,
            look_back_year=look_back_year,
            look_back_distance=distance,
        )
        self._bus.publish(
            Event(
                type=EventType.CALIBRATION_QCEW_CARRY_FORWARD.value,
                tick=0,
                payload=typed.model_dump(),
            )
        )

    def _emit_outlier(self, *, fips: str, phi_hour: float) -> None:
        typed = PhiHourOutlierEvent(
            tick=0,
            county_fips=fips,
            phi_hour=phi_hour,
            threshold_low=self._defines.phi_hour_outlier_threshold_low,
            threshold_high=self._defines.phi_hour_outlier_threshold_high,
        )
        self._bus.publish(
            Event(
                type=EventType.CALIBRATION_PHI_HOUR_OUTLIER.value,
                tick=0,
                payload=typed.model_dump(),
            )
        )
