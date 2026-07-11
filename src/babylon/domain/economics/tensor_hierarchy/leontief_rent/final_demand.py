"""Per-industry final-demand vector source for Spec 057.

Implements the existing ``FinalDemandSource`` Protocol (declared in
``babylon.domain.economics.tensor_hierarchy.production_chain_rent``) via
:class:`DefaultFinalDemandSource`, which reads the BEA Use Table
"Total Final Uses (GDP)" column from ``fact_bea_final_demand_annual`` in the
reference SQLite (per Spec 057 / R2 + R8 schema check).

Adapter pattern (per FR-007 + Spec 058 contract):
  - ``_fetch(year)`` returns ``np.ndarray | NoDataSentinel`` (CachedSource[T] contract)
  - ``get_final_demand(year)`` raises ``ValueError`` if ``_fetch`` returned
    the sentinel — preserves the existing FinalDemandSource Protocol contract
    that callers using ``ProductionChainRentCalculator`` depend on.
"""

from __future__ import annotations

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from babylon.domain.economics.protocol_kit import CachedSource
from babylon.domain.economics.tensor import NoDataSentinel
from babylon.reference.schema import (
    DimBEAIndustry,
    DimTime,
    FactBEAFinalDemandAnnual,
)

__all__ = ["DefaultFinalDemandSource"]


class DefaultFinalDemandSource(CachedSource[np.ndarray]):
    """BEA Use Table-based final-demand vector source per FR-003.

    Returns the per-industry "Total Final Uses (GDP)" column for the
    requested year, ordered to match the configured BEA Summary industry
    list. Industries without a fact_bea_final_demand_annual row for the
    year contribute 0.0 (gap-fill at source layer; FR-006 industry-list
    alignment failures are detected later at the pipeline level).

    Args:
        db_session: SQLAlchemy session pointing at the reference database
            (where ``fact_bea_final_demand_annual`` lives).
        bea_industries: Ordered list of BEA Summary industry codes — defines
            the shape and order of the returned numpy vector.
    """

    cache_negative_results: bool = True  # BEA Use Table is static within session

    def __init__(
        self,
        *,
        db_session: Session,
        bea_industries: list[str],
    ) -> None:
        super().__init__()
        self._db = db_session
        self._industries = list(bea_industries)

    def _fetch(self, year: int) -> np.ndarray | NoDataSentinel:
        """Query fact_bea_final_demand_annual + dim_bea_industry for year;
        return np.ndarray of shape (n_industries,) ordered to match
        self._industries. Industries with no row contribute 0.0."""
        stmt = (
            select(
                DimBEAIndustry.bea_code,
                FactBEAFinalDemandAnnual.total_final_uses_millions,
            )
            .join(
                FactBEAFinalDemandAnnual,
                DimBEAIndustry.bea_industry_id == FactBEAFinalDemandAnnual.bea_industry_id,
            )
            .join(DimTime, FactBEAFinalDemandAnnual.time_id == DimTime.time_id)
            .where(DimTime.year == year)
        )
        rows = self._db.execute(stmt).all()
        if not rows:
            return NoDataSentinel(
                fips="",
                year=year,
                reason=f"No fact_bea_final_demand_annual rows for year={year}",
            )

        # Build per-code lookup; assemble vector in self._industries order.
        by_code: dict[str, float] = {code: float(value) for code, value in rows}
        result = np.zeros(len(self._industries), dtype=np.float64)
        for i, code in enumerate(self._industries):
            result[i] = by_code.get(code, 0.0)
        return result

    def get_final_demand(self, year: int) -> np.ndarray:
        """Adapter for the legacy FinalDemandSource Protocol contract.

        Delegates to :meth:`_resolve` (cached lookup); raises ``ValueError``
        if the cached value is :class:`NoDataSentinel`. Callers using the
        Protocol get exception semantics; callers using ``_resolve`` directly
        get sentinel semantics (FR-007).
        """
        result = self._resolve(year, lambda: self._fetch(year))
        if isinstance(result, NoDataSentinel):
            raise ValueError(f"No final-demand data for year {year}")
        return result
