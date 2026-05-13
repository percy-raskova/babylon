"""Pydantic model for the dynamic_hex_state Postgres row.

Spec 062, data-model.md §2.1. Hex resolution 7 is the only persisted
source-of-truth for c/v/s/K/biocapacity (FR-018/FR-019). Coarser-scale
values are computed on read from the v_county/state/national_value_aggregate
views — never stored.

See Also:
    ``specs/062-cross-scale-integration/contracts/persistence.yaml``.
    :mod:`babylon.persistence.migrations.0011_dynamic_hex_state`.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DynamicHexState(BaseModel):
    """One row of the ``dynamic_hex_state`` table.

    Primary key: ``(session_id, tick, h3_index)``.

    Value-substance fields (c, v, s, k) and substrate stocks
    (biocapacity_stock, energy_stock, raw_material_stock) MUST be
    non-negative. ``internet_access_pct`` and ``surveillance_coupling`` are
    bounded to ``[0, 1]``. The spatial mapping fields (county/state/region)
    are immutable per hex; they're stamped at initialization and never
    change across ticks.
    """

    model_config = ConfigDict(frozen=True)

    session_id: UUID
    tick: int = Field(ge=0)
    h3_index: str = Field(min_length=15, max_length=15)

    county_fips: str = Field(pattern=r"^\d{5}$")
    state_fips: str = Field(pattern=r"^\d{2}$")
    region_id: str = Field(min_length=1)

    c: float = Field(ge=0)
    v: float = Field(ge=0)
    s: float = Field(ge=0)
    k: float = Field(ge=0)

    biocapacity_stock: float = Field(ge=0)
    energy_stock: float = Field(ge=0)
    raw_material_stock: float = Field(ge=0)

    internet_access_pct: float = Field(ge=0, le=1)
    surveillance_coupling: float = Field(ge=0, le=1)


__all__ = ["DynamicHexState"]
