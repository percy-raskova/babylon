"""SQLite adapter hydrating alpha and gamma_import for basket visibility.

Feature: 102-gamma-shocks
Date: 2026-07-04

Kills the hardcoded seam in :mod:`babylon.domain.economics.melt.basket_visibility`
(``MVP_ALPHA=0.25``, ``MVP_GAMMA_IMPORT=0.35``) by computing both
coefficients per calendar year from the read-only reference database
(``marxist-data-3NF.sqlite``), following the same session-factory-based
SQLAlchemy adapter pattern as :mod:`babylon.domain.economics.melt.adapters`.

Formulas:
    - ``alpha`` (import share of the consumption/final-demand basket):
      ``Sigma fact_bilateral_trade_annual.imports_usd_millions`` (all
      countries, year's annual ``time_id``) /
      ``Sigma fact_bea_final_demand_annual.total_final_uses_millions`` (all
      ``bea_industry_id``, same ``time_id``).
    - ``gamma_import`` (basket visibility of imported goods):
      ``1 / fact_hickel_erdi_annual.erdi`` for ``(year, scale_type)``.
      Dimensionally required: the harmonic-mean ``gamma_basket`` formula
      needs ``gamma_import`` in ``(0, 1]``, and ERDI (market/PPP
      exchange-rate ratio) is ``>1`` for undervalued-currency trading
      partners, so ``1/ERDI`` is the visibility measure — matches the
      sibling module :mod:`babylon.domain.economics.gamma.gamma_import`'s formula
      ``gamma_import = sum(import_share[origin] * 1/ERDI[origin])``, here
      degenerating to the single nationally-aggregated ERDI since the
      reference DB has no per-country ERDI resolution (no fabricated
      per-country weighting, Constitution III.8).

Both methods return ``None`` when the reference DB has no data for the
requested year — the caller (``DefaultBasketVisibilityCalculator``) falls
back to the existing MVP hardcode in that case (``estimated=True``), per
the documented Protocol contract. ``fact_hickel_erdi_annual`` only has
``scale_type='Intensive'`` rows for 1980-2016 (see
``specs/102-gamma-shocks/research.md`` R1) — years outside that window
legitimately return ``None``; this is a disclosed data-coverage gap, not a
bug.

See Also:
    :mod:`babylon.domain.economics.melt.basket_visibility`: Consumer of this adapter.
    :mod:`babylon.domain.economics.melt.adapters`: Sibling national-level adapters
        (``SQLiteBEANationalGDPSource``, ``SQLiteQCEWNationalEmploymentSource``)
        whose constructor/query pattern this module follows.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from sqlalchemy import func

from babylon.reference.schema import (
    DimTime,
    FactBEAFinalDemandAnnual,
    FactBilateralTradeAnnual,
    FactHickelERDIAnnual,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

DEFAULT_HICKEL_SCALE_TYPE: str = "Intensive"
"""Default Hickel ERDI scale_type, matching
:class:`babylon.domain.economics.tensor_hierarchy.leontief_rent.periphery_labor_coefficients.DefaultPeripheryLaborCoefficientsSource`'s
existing convention."""

_DISJOINT_BLOC_IDS: frozenset[int] = frozenset({1, 7, 9, 12})
"""Non-overlapping bloc country_ids from dim_country.

Verified disjoint via SQLite: the 4-bloc sum for 2012 is $2.02T, which
is LESS than total real US imports (~$2.75T) — proving no double-count
(undercount is honest: non-Asian Pacific countries are excluded).

Excludes:
- Europe (id=8): geographic aggregate ⊇ European Union (id=1) — summing
  both double-counts ~$381B of EU trade.
- Pacific Rim (id=10): overlaps Asia (id=12) — Pacific Rim includes
  Asian countries (China, Japan, Korea, etc.) also counted in Asia.
  The 5-bloc sum {1,7,9,10,12} = $2.78T EXCEEDS total US imports
  ($2.75T), proving the overlap. Dropping Pacific Rim eliminates it.
- Advanced Technology Products (id=5): cross-cutting commodity category,
  not a geography.
- Australia and Oceania (id=14): no distinct engine node mapped to it.
"""


@runtime_checkable
class GammaHydrationSource(Protocol):
    """Protocol for hydrating basket-visibility coefficients per year.

    Example:
        >>> from babylon.reference.database import get_normalized_session_factory
        >>> source = SQLiteGammaHydrationSource(get_normalized_session_factory())
        >>> alpha = source.get_alpha(2012)
        >>> gamma_import = source.get_gamma_import(2012)
    """

    def get_alpha(self, year: int) -> float | None:
        """Compute the import share of final demand for ``year``.

        Args:
            year: Calendar year.

        Returns:
            ``Sigma imports_usd_millions / Sigma total_final_uses_millions``,
            or ``None`` if either reference table has no rows for the
            year's annual ``time_id``.
        """
        ...

    def get_gamma_import(
        self, year: int, scale_type: str = DEFAULT_HICKEL_SCALE_TYPE
    ) -> float | None:
        """Compute basket visibility of imported goods for ``year``.

        Args:
            year: Calendar year.
            scale_type: Hickel ERDI methodology selector (``'Intensive'``,
                ``'Extensive'``, or ``'Intensive_China_Inflection'``).

        Returns:
            ``1 / erdi``, or ``None`` if no ``fact_hickel_erdi_annual`` row
            matches ``(year, scale_type)``.
        """
        ...


class SQLiteGammaHydrationSource:
    """SQLite adapter implementing :class:`GammaHydrationSource`.

    Queries the normalized reference database for ``alpha`` (import share
    of final demand) and ``gamma_import`` (inverse Hickel ERDI) per year.
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        """Initialize the adapter.

        Args:
            session_factory: Callable that returns a SQLAlchemy session.
        """
        self._session_factory = session_factory

    def _annual_time_id(self, session: Session, year: int) -> int | None:
        time_dim = (
            session.query(DimTime).filter(DimTime.year == year, DimTime.is_annual == 1).first()
        )
        return time_dim.time_id if time_dim is not None else None

    def get_alpha(self, year: int) -> float | None:
        """Compute import share of final demand for ``year``.

        Args:
            year: Calendar year.

        Returns:
            Import share in (typically) ``[0, 1]``, or ``None`` if the
            year's annual ``time_id`` is missing, or either reference
            table has no rows for it (avoids a division by zero/None).
        """
        with self._session_factory() as session:
            time_id = self._annual_time_id(session, year)
            if time_id is None:
                return None

            total_imports = (
                session.query(func.sum(FactBilateralTradeAnnual.imports_usd_millions))
                .filter(
                    FactBilateralTradeAnnual.time_id == time_id,
                    FactBilateralTradeAnnual.country_id.in_(_DISJOINT_BLOC_IDS),
                )
                .scalar()
            )
            if total_imports is None:
                logger.info("No fact_bilateral_trade_annual rows for year %d", year)
                return None

            total_final_uses = (
                session.query(func.sum(FactBEAFinalDemandAnnual.total_final_uses_millions))
                .filter(FactBEAFinalDemandAnnual.time_id == time_id)
                .scalar()
            )
            if total_final_uses is None or float(total_final_uses) == 0.0:
                logger.info("No fact_bea_final_demand_annual rows for year %d", year)
                return None

            return float(total_imports) / float(total_final_uses)

    def get_gamma_import(
        self, year: int, scale_type: str = DEFAULT_HICKEL_SCALE_TYPE
    ) -> float | None:
        """Compute basket visibility of imported goods for ``year``.

        Args:
            year: Calendar year.
            scale_type: Hickel ERDI methodology selector.

        Returns:
            ``1 / erdi`` in ``(0, 1]`` for undervalued-currency partners
            (``erdi > 1``), or ``None`` if no matching row exists (e.g.
            years outside the 1980-2016 ``'Intensive'`` coverage window).
        """
        with self._session_factory() as session:
            time_id = self._annual_time_id(session, year)
            if time_id is None:
                return None

            erdi = (
                session.query(FactHickelERDIAnnual.erdi)
                .filter(
                    FactHickelERDIAnnual.time_id == time_id,
                    FactHickelERDIAnnual.scale_type == scale_type,
                )
                .scalar()
            )
            if erdi is None or float(erdi) == 0.0:
                logger.info(
                    "No fact_hickel_erdi_annual row for year=%d scale_type=%r",
                    year,
                    scale_type,
                )
                return None

            return 1.0 / float(erdi)


__all__ = ["DEFAULT_HICKEL_SCALE_TYPE", "GammaHydrationSource", "SQLiteGammaHydrationSource"]
