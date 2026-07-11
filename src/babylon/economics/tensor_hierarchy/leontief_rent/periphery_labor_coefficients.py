"""Per-industry core/periphery wage-ratio source for Spec 057.

Implements the ``PeripheryLaborCoefficientsSource`` Protocol via
:class:`DefaultPeripheryLaborCoefficientsSource`, which reads the Hickel/
Sullivan/Zoomkawala (2021) ERDI time series from
``fact_hickel_erdi_annual`` and broadcasts the year's ERDI uniformly across
the BEA Summary industries (v1 simplification per
``specs/057-leontief-rent-integration/research.md`` §R1).

The original plan (PWT v10.01 country-aggregate) was rejected during
``/speckit.analyze`` because PWT data is not loaded in the reference SQLite
and is not present in the babylon-data trove. R1 was pivoted to Hickel ERDI
(already in the trove, already covered by the III.4 PATCH-level catalog
amendment per R9). See research.md for the rationale.

Three-layer axiom enforcement (research.md §R5):
  1. Source layer (this module) — detect ratio < 1.0 + emit
     :class:`AxiomViolationEvent` via EventBus. Pass value through unchanged.
  2. Calculator layer — ``ProductionChainRentCalculator.calculate``
     clamps ``loss_ratio = np.maximum(loss_ratio, 0.0)`` at
     ``production_chain_rent.py:181``.
  3. Data-model layer — ``CountyEconomicState.phi_hour: Field(..., ge=0)``
     would raise ``pydantic.ValidationError`` if a negative value reached
     this far (defense in depth).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from babylon.core.protocol_kit import CachedSource
from babylon.economics.tensor import NoDataSentinel
from babylon.economics.tensor_hierarchy.types import PeripheryLaborCoefficients
from babylon.kernel.event_bus import Event, EventBus
from babylon.models.enums import EventType
from babylon.models.events import AxiomViolationEvent
from babylon.reference.schema import DimTime, FactHickelERDIAnnual

__all__ = [
    "DefaultPeripheryLaborCoefficientsSource",
    "PeripheryLaborCoefficientsSource",
    "PeripheryWageMetadata",
]


# =============================================================================
# Metadata payload (FR-002 provenance record)
# =============================================================================


class PeripheryWageMetadata(BaseModel):
    """Source-publication metadata for ``PeripheryLaborCoefficients`` (FR-002).

    Recorded on every ``DefaultPeripheryLaborCoefficientsSource`` instance so
    the data-source provenance is queryable at scenario-load time.
    """

    model_config = ConfigDict(frozen=True)

    publication: str = Field(..., description="Source publication name + version")
    publication_url: str = Field(..., description="Canonical URL")
    periphery_definition: str = Field(..., description="Geographic + methodological definition")
    units: str = Field(..., description="Numerical units of the underlying wage data")
    base_year: int = Field(
        ..., ge=1900, le=2100, description="Reference year for PPP / real adjustments"
    )
    industry_disaggregation: str = Field(
        ...,
        description="None / Manufacturing-only / Sector-level / etc.",
    )
    calibration_anchor: str = Field(
        ...,
        description="Independent estimate referenced for SC-004 OOM check",
    )
    v1_simplification_caveats: list[str] = Field(default_factory=list)


# =============================================================================
# Protocol
# =============================================================================


@runtime_checkable
class PeripheryLaborCoefficientsSource(Protocol):
    """Year-keyed query interface for per-industry core/periphery wage ratios."""

    def get_coefficients(self, year: int) -> PeripheryLaborCoefficients | NoDataSentinel: ...

    @property
    def metadata(self) -> PeripheryWageMetadata: ...


# =============================================================================
# Default implementation: Hickel ERDI broadcast
# =============================================================================


class DefaultPeripheryLaborCoefficientsSource(CachedSource[PeripheryLaborCoefficients]):
    """Hickel/Sullivan/Zoomkawala (2021) ERDI-based periphery-wage source.

    Per Spec 057 R1 (revised post-analyze): the country-aggregate ERDI for
    each year is broadcast uniformly across the configured BEA Summary
    industry list. Industry-disaggregated periphery wage data is deferred
    to v1.5 (QCEW US-side scaling).

    Args:
        db_session: SQLAlchemy session pointing at the reference database
            (where ``fact_hickel_erdi_annual`` lives).
        event_bus: EventBus for ``AxiomViolationEvent`` emission when ERDI < 1.0.
        bea_industries: Ordered list of BEA Summary industry codes — defines
            the shape of the returned ``wage_ratios`` vector.
        scale_type: Hickel methodology selector. Default ``"Intensive"`` (matches
            post-2009 era of the published time series). Other observed values:
            ``"Extensive"`` (pre-2009), ``"Intensive_China_Inflection"`` (post-2017).
    """

    cache_negative_results: bool = True  # Hickel CSV is static within session

    def __init__(
        self,
        *,
        db_session: Session,
        event_bus: EventBus,
        bea_industries: list[str],
        scale_type: str = "Intensive",
    ) -> None:
        super().__init__()
        self._db = db_session
        self._bus = event_bus
        self._industries = list(bea_industries)
        self._scale_type = scale_type

    # -------------------------------------------------------------------------
    # Public API (Protocol contract)
    # -------------------------------------------------------------------------

    def get_coefficients(self, year: int) -> PeripheryLaborCoefficients | NoDataSentinel:
        """Fetch per-industry wage ratios for the requested year.

        Returns:
            ``PeripheryLaborCoefficients`` with ``wage_ratios = ERDI[year]``
            broadcast across ``self._industries``, or ``NoDataSentinel`` if
            no Hickel row exists for ``(year, scale_type)``.
        """
        return self._resolve((year, self._scale_type), lambda: self._fetch(year))

    @property
    def metadata(self) -> PeripheryWageMetadata:
        return PeripheryWageMetadata(
            publication="Hickel, Sullivan & Zoomkawala (2021) — ERDI time series",
            publication_url="https://doi.org/10.1016/j.gloenvcha.2021.102467",
            periphery_definition=(
                "Global South per Hickel 2021 (effectively the high-income / "
                "low-and-middle-income split per World Bank classification)"
            ),
            units="ERDI — dimensionless ratio (market exchange rate / PPP exchange rate)",
            base_year=2017,
            industry_disaggregation=(
                "None — ERDI broadcast uniformly across BEA Summary industries (v1)"
            ),
            calibration_anchor=(
                "babylon_hickel_final.csv `annual_drain_usd_billions` column "
                "(different field of same publication; year-resolved per SC-004 + "
                "research.md §R8.4)"
            ),
            v1_simplification_caveats=[
                "Country-level ERDI broadcast uniformly across all BEA industries",
                "Industry-disaggregated periphery wage data not used; QCEW US-side "
                "industry resolution deferred to v1.5",
                "Source publication (ERDI) and calibration target "
                "(annual_drain_usd_billions) come from the same Hickel CSV — "
                "orthogonality is at the column level, not the dataset level "
                "(research.md §R9)",
            ],
        )

    # -------------------------------------------------------------------------
    # CachedSource hook
    # -------------------------------------------------------------------------

    def _fetch(self, year: int) -> PeripheryLaborCoefficients | NoDataSentinel:
        stmt = (
            select(FactHickelERDIAnnual.erdi)
            .join(DimTime, FactHickelERDIAnnual.time_id == DimTime.time_id)
            .where(DimTime.year == year)
            .where(FactHickelERDIAnnual.scale_type == self._scale_type)
            .limit(1)
        )
        erdi_value = self._db.execute(stmt).scalar_one_or_none()
        if erdi_value is None:
            return NoDataSentinel(
                fips="",  # National-aggregate source — no county context
                year=year,
                reason=(f"No Hickel ERDI row for year={year}, scale_type={self._scale_type!r}"),
            )

        n = len(self._industries)
        wage_ratios = np.full(n, float(erdi_value), dtype=np.float64)

        # Axiom enforcement at the source layer: emit AxiomViolationEvent for
        # each industry where ratio < 1.0. For uniform-broadcast (v1), this
        # fires for all n industries iff ERDI < 1.0 — emit once per industry
        # so subscribers see per-industry attribution (downstream filtering by
        # industry remains possible).
        if erdi_value < 1.0:
            for industry in self._industries:
                self._emit_axiom_violation(industry=industry, year=year, ratio=float(erdi_value))

        return PeripheryLaborCoefficients(
            year=year, industries=self._industries, wage_ratios=wage_ratios
        )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _emit_axiom_violation(self, *, industry: str, year: int, ratio: float) -> None:
        typed = AxiomViolationEvent(
            tick=0, industry=industry, year=year, ratio=ratio, threshold=1.0
        )
        # Use tick=0 because the source has no current-tick context; the
        # subscriber recovers timing from the event arrival order in
        # event_bus.get_history(). The CalibrationWarning event family is
        # tick-agnostic per its FR contract (data-quality signal, not
        # game-time-bound).
        self._bus.publish(
            Event(
                type=EventType.CALIBRATION_AXIOM_VIOLATION.value,
                tick=0,
                payload=typed.model_dump(),
            )
        )
