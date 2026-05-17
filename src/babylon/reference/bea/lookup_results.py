"""Frozen Pydantic result types returned by ``BEAShareLookupService``.

These are the only data types that cross the II.11 subsystem boundary
from the BEA subsystem into the persistence subsystem (hex_hydrator)
or any other consumer.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat

FallbackReason = Literal["none", "forward_fill", "global_default"]


class IndustryShareLookupResult(BaseModel):
    """Per-(BEA-industry, year) intermediate-inputs share lookup result.

    Shares are computed at read time from the three BEA primitives
    stored in ``fact_bea_national_industry`` (II.2 — Primitives vs Derived).
    """

    model_config = ConfigDict(frozen=True)

    intermediate_inputs_share: float = Field(ge=0.0, le=1.0)
    value_added_share: float = Field(ge=0.0, le=1.0)
    vintage_published_date: date | None
    used_fallback: bool
    fallback_reason: FallbackReason


class CountyShareLookupResult(BaseModel):
    """Per-(county, year) intermediate-inputs share lookup result.

    Weighted by the county's QCEW industry employment mix via the
    ``bridge_naics_bea`` concordance.
    """

    model_config = ConfigDict(frozen=True)

    intermediate_inputs_share: float = Field(ge=0.0, le=1.0)
    value_added_share: float = Field(ge=0.0, le=1.0)
    fallback_employment_fraction: NonNegativeFloat = Field(le=1.0)
    per_industry_breakdown: dict[int, float]
