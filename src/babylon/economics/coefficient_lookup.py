"""Coefficient lookup policy classifier for year-scoped reference series.

Spec 062 — FR-011 / FR-012 / FR-013. Each immutable reference series is
classified as either ``slowly_varying`` (linear interpolation across the 52
weeks of the simulated year) or ``event_discrete`` (step-function at the
year-boundary tick). The classification is data, not behavior — concrete
interpolation is performed by
:class:`babylon.persistence.postgres_reference.ImmutableReferenceLookup`.

See Also:
    :mod:`babylon.persistence.postgres_reference`: Runtime dispatch.
    ``specs/062-cross-scale-integration/data-model.md`` §2.5.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class LookupPolicy(StrEnum):
    """Per-series interpolation policy.

    SLOWLY_VARYING:
        Linear interpolation across the 52 weeks of the simulated year
        (FR-012). Used for aggregate economic coefficients (BEA I-O, MELT,
        Hickel drain, etc.) where the underlying federal series moves
        smoothly.

    EVENT_DISCRETE:
        Step-function: the value for tick ``t`` is the series value for
        ``start_year + (t // 52)`` (FR-013). Used for policy-step series
        (FOMC rate decisions, regulatory regime changes, datacenter
        commissioning) where the underlying event IS discrete.
    """

    SLOWLY_VARYING = "slowly_varying"
    EVENT_DISCRETE = "event_discrete"


class CoefficientLookupPolicy(BaseModel):
    """Per-reference-series lookup policy descriptor.

    Stored in :attr:`babylon.config.defines.GameDefines.coefficient_lookup_policies`
    as ``dict[str, CoefficientLookupPolicy]``.

    Attributes:
        series_id: Stable identifier (e.g., ``"bea_io_imports"``,
            ``"hickel_drain"``, ``"fred_fed_funds_rate"``).
        policy: One of :class:`LookupPolicy`.
        canonical_reference: Human-readable source identifier
            (e.g., ``"BEA Make-Use-Imports 2010-2024"``).
    """

    model_config = ConfigDict(frozen=True)

    series_id: str = Field(min_length=1, max_length=64)
    policy: LookupPolicy
    canonical_reference: str = Field(min_length=1)


__all__ = ["LookupPolicy", "CoefficientLookupPolicy"]
