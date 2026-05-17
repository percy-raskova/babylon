"""``BEAShareLookupService`` — the II.11 cross-subsystem contract (spec-068 US3).

Per constitution II.11 (Subsystem Table Ownership), every cross-
subsystem read of ``fact_bea_national_industry``, ``fact_bea_io_coefficient``,
and ``bridge_naics_bea`` MUST go through this Protocol. Direct SQL
on those tables from outside ``src/babylon/reference/bea/`` is a
constitutional violation.

See ``specs/068-bea-national-io-ingest/contracts/bea_share_lookup_service.md``
for the contract specification.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal
from functools import lru_cache
from typing import ClassVar, Literal, Protocol

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from babylon.reference.bea.lookup_results import (
    CountyShareLookupResult,
    IndustryShareLookupResult,
)
from babylon.reference.schema import (
    BridgeNAICSBEA,
    DimBEAIOTableType,
    DimTime,
    FactBEAIOCoefficient,
    FactBEANationalIndustry,
    FactQcewAnnual,
)

log = logging.getLogger(__name__)

_MAX_FORWARD_FILL_YEARS_DEFAULT = 5


class BEAShareLookupService(Protocol):
    """Declared cross-subsystem interface (Constitution II.11).

    See contracts/bea_share_lookup_service.md.
    """

    def lookup_industry_share(
        self,
        bea_industry_id: int,
        year: int,
    ) -> IndustryShareLookupResult: ...

    def lookup_county_share(
        self,
        county_fips: str,
        year: int,
    ) -> CountyShareLookupResult: ...

    def lookup_io_coefficient(
        self,
        source_industry_id: int,
        target_industry_id: int,
        year: int,
        table_type: Literal["USE", "MAKE", "SUPPLY", "TOTAL_REQ"] = "USE",
    ) -> float | None: ...


class DefaultBEAShareLookupService:
    """Concrete implementation of :class:`BEAShareLookupService`.

    Forward-fills missing years (up to ``max_forward_fill_years``) per
    Clarification Q3. Beyond the walk-back cap, falls back to the
    economy-wide ``GLOBAL_FALLBACK_SHARE = 0.5`` — preserves the
    spec-066/067 baseline behavior when the BEA tables are empty (FR-010).
    """

    GLOBAL_FALLBACK_SHARE: ClassVar[float] = 0.5

    def __init__(
        self,
        session: Session,
        max_forward_fill_years: int = _MAX_FORWARD_FILL_YEARS_DEFAULT,
    ) -> None:
        self._session = session
        self._max_forward_fill_years = max_forward_fill_years

    def lookup_industry_share(
        self,
        bea_industry_id: int,
        year: int,
    ) -> IndustryShareLookupResult:
        """Return the per-(BEA-industry, year) intermediate-inputs share.

        Walks back up to ``max_forward_fill_years`` if the requested year
        is absent for this industry. Returns ``fallback_reason="none"``
        on direct hit, ``"forward_fill"`` on walk-back hit, or
        ``"global_default"`` when the walk-back exhausts.
        """
        for delta in range(0, self._max_forward_fill_years + 1):
            target_year = year - delta
            row = self._fetch_industry_row(bea_industry_id, target_year)
            if row is None:
                continue
            ii, va, go, vintage = row
            if go is None or go == Decimal(0) or ii is None or va is None:
                continue
            ii_share = float(ii / go)
            va_share = float(va / go)
            return IndustryShareLookupResult(
                intermediate_inputs_share=max(0.0, min(1.0, ii_share)),
                value_added_share=max(0.0, min(1.0, va_share)),
                vintage_published_date=vintage,
                used_fallback=(delta > 0),
                fallback_reason="forward_fill" if delta > 0 else "none",
            )

        # Walk-back exhausted — emit global default per FR-010.
        log.debug(
            "lookup_industry_share: global-default fallback for (bea_id=%d, year=%d)",
            bea_industry_id,
            year,
        )
        return IndustryShareLookupResult(
            intermediate_inputs_share=self.GLOBAL_FALLBACK_SHARE,
            value_added_share=1.0 - self.GLOBAL_FALLBACK_SHARE,
            vintage_published_date=None,
            used_fallback=True,
            fallback_reason="global_default",
        )

    def lookup_county_share(
        self,
        county_fips: str,
        year: int,
    ) -> CountyShareLookupResult:
        """Return the per-county intermediate-inputs share (QCEW-weighted).

        Computes the QCEW-employment-weighted average of per-BEA-industry
        shares via ``fact_qcew_annual → dim_industry → bridge_naics_bea →
        dim_bea_industry → fact_bea_national_industry``.
        """
        employment_by_bea_industry = self._fetch_county_employment_by_bea(county_fips, year)

        if not employment_by_bea_industry:
            log.debug(
                "lookup_county_share: no QCEW employment found for (fips=%s, year=%d)",
                county_fips,
                year,
            )
            return CountyShareLookupResult(
                intermediate_inputs_share=self.GLOBAL_FALLBACK_SHARE,
                value_added_share=1.0 - self.GLOBAL_FALLBACK_SHARE,
                fallback_employment_fraction=1.0,
                per_industry_breakdown={},
            )

        total_employment = sum(employment_by_bea_industry.values())
        if total_employment <= 0:
            return CountyShareLookupResult(
                intermediate_inputs_share=self.GLOBAL_FALLBACK_SHARE,
                value_added_share=1.0 - self.GLOBAL_FALLBACK_SHARE,
                fallback_employment_fraction=1.0,
                per_industry_breakdown={},
            )

        weighted_ii_share = 0.0
        fallback_employment = 0.0
        per_industry_breakdown: dict[int, float] = {}

        for bea_id, employment in employment_by_bea_industry.items():
            weight = employment / total_employment
            per_industry_breakdown[bea_id] = weight
            share = self.lookup_industry_share(bea_id, year)
            weighted_ii_share += weight * share.intermediate_inputs_share
            if share.fallback_reason == "global_default":
                fallback_employment += employment

        return CountyShareLookupResult(
            intermediate_inputs_share=max(0.0, min(1.0, weighted_ii_share)),
            value_added_share=max(0.0, min(1.0, 1.0 - weighted_ii_share)),
            fallback_employment_fraction=fallback_employment / total_employment,
            per_industry_breakdown=per_industry_breakdown,
        )

    def lookup_io_coefficient(
        self,
        source_industry_id: int,
        target_industry_id: int,
        year: int,
        table_type: Literal["USE", "MAKE", "SUPPLY", "TOTAL_REQ"] = "USE",
    ) -> float | None:
        """Return the Leontief direct-requirements coefficient a_ij.

        Forward-fills up to ``max_forward_fill_years`` per Clarification Q3.
        """
        table_type_id = self._lookup_table_type_id(table_type)
        if table_type_id is None:
            return None

        for delta in range(0, self._max_forward_fill_years + 1):
            target_year = year - delta
            time_id = self._lookup_time_id(target_year)
            if time_id is None:
                continue
            row = self._session.execute(
                select(FactBEAIOCoefficient.coefficient).where(
                    and_(
                        FactBEAIOCoefficient.source_industry_id == source_industry_id,
                        FactBEAIOCoefficient.target_industry_id == target_industry_id,
                        FactBEAIOCoefficient.table_type_id == table_type_id,
                        FactBEAIOCoefficient.time_id == time_id,
                    )
                )
            ).scalar_one_or_none()
            if row is not None:
                return float(row)

        return None

    # --- internals ---------------------------------------------------------

    def _fetch_industry_row(
        self,
        bea_industry_id: int,
        year: int,
    ) -> tuple[Decimal | None, Decimal | None, Decimal | None, date | None] | None:
        """Return ``(II, VA, GO, vintage)`` for a specific (industry, year)."""
        time_id = self._lookup_time_id(year)
        if time_id is None:
            return None
        result = self._session.execute(
            select(
                FactBEANationalIndustry.intermediate_inputs_millions,
                FactBEANationalIndustry.value_added_millions,
                FactBEANationalIndustry.gross_output_millions,
                FactBEANationalIndustry.vintage_published_date,
            ).where(
                and_(
                    FactBEANationalIndustry.bea_industry_id == bea_industry_id,
                    FactBEANationalIndustry.time_id == time_id,
                )
            )
        ).one_or_none()
        if result is None:
            return None
        ii, va, go, vintage = result
        return (ii, va, go, vintage)

    def _fetch_county_employment_by_bea(
        self,
        county_fips: str,
        year: int,
    ) -> dict[int, float]:
        """Return ``bea_industry_id -> total_employment`` for a county-year.

        Joins QCEW → dim_industry → bridge_naics_bea → dim_bea_industry.
        Aggregates over all NAICS-6-digit rows for the county-year.
        """
        time_id = self._lookup_time_id(year)
        if time_id is None:
            return {}
        # bridge_naics_bea references dim_industry.industry_id, NOT
        # dim_naics_industry.naics_id. fact_qcew_annual uses industry_id too.
        county_id = self._lookup_county_id(county_fips)
        if county_id is None:
            return {}
        rows = self._session.execute(
            select(
                BridgeNAICSBEA.bea_industry_id,
                FactQcewAnnual.employment,
            )
            .join(BridgeNAICSBEA, BridgeNAICSBEA.industry_id == FactQcewAnnual.industry_id)
            .where(
                and_(
                    FactQcewAnnual.county_id == county_id,
                    FactQcewAnnual.time_id == time_id,
                )
            )
        ).all()
        bucket: dict[int, float] = defaultdict(float)
        for bea_id, emp in rows:
            if emp is None:
                continue
            bucket[int(bea_id)] += float(emp)
        return dict(bucket)

    @lru_cache(maxsize=128)  # noqa: B019 — instance cache on session-bound service
    def _lookup_time_id(self, year: int) -> int | None:
        return self._session.execute(
            select(DimTime.time_id).where(and_(DimTime.year == year, DimTime.is_annual.is_(True)))
        ).scalar_one_or_none()

    @lru_cache(maxsize=16)  # noqa: B019
    def _lookup_table_type_id(self, table_type: str) -> int | None:
        return self._session.execute(
            select(DimBEAIOTableType.id).where(DimBEAIOTableType.table_type == table_type)
        ).scalar_one_or_none()

    @lru_cache(maxsize=512)  # noqa: B019
    def _lookup_county_id(self, county_fips: str) -> int | None:
        from babylon.reference.schema import DimCounty

        return self._session.execute(
            select(DimCounty.county_id).where(DimCounty.fips == county_fips)
        ).scalar_one_or_none()


__all__ = [
    "BEAShareLookupService",
    "DefaultBEAShareLookupService",
]
