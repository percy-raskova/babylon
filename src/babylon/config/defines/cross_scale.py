"""Cross-scale lookup-policy model (Spec 062).

Lives in :mod:`babylon.config.defines` (not :mod:`babylon.economics`) so that
:class:`babylon.config.defines.economy_basic.EconomyDefines` can import it
without triggering the heavy ``babylon.economics/__init__.py`` import chain
(which itself depends on ``GameDefines``, producing a circular import).

Re-exported via :mod:`babylon.economics.coefficient_lookup` for downstream
callsites that conceptually treat the policy as an economics primitive.

See Also:
    ``specs/062-cross-scale-integration/data-model.md`` §2.5.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class LookupPolicy(StrEnum):
    """Per-series interpolation policy.

    SLOWLY_VARYING:
        Linear interpolation across the 52 weeks of the simulated year
        (FR-012).

    EVENT_DISCRETE:
        Step-function: the value for tick ``t`` is the series value for
        ``start_year + (t // 52)`` (FR-013).
    """

    SLOWLY_VARYING = "slowly_varying"
    EVENT_DISCRETE = "event_discrete"


class CoefficientLookupPolicy(BaseModel):
    """Per-reference-series lookup policy descriptor.

    Attributes:
        series_id: Stable identifier (e.g., ``"bea_io_imports"``).
        policy: One of :class:`LookupPolicy`.
        canonical_reference: Human-readable source identifier.
    """

    model_config = ConfigDict(frozen=True)

    series_id: str = Field(min_length=1, max_length=64)
    policy: LookupPolicy
    canonical_reference: str = Field(min_length=1)


__all__ = ["LookupPolicy", "CoefficientLookupPolicy"]
