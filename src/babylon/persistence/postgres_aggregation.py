"""Cross-scale aggregation queries (Spec 062, US3).

Implements the four read-view query helpers per
``contracts/aggregation_views.yaml``: county / state / national aggregates,
plus the global Φ-balance check used by the annual conservation invariant.

Constitution II.11: the Postgres views ARE the declared cross-subsystem
read interface. This module is a thin typed-facade around ``SELECT`` so
callers receive Pydantic-validated rows rather than raw tuples.

See Also:
    :mod:`babylon.persistence.migrations.0015_aggregation_views`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from babylon.persistence import PostgresRuntime


class CountyValueAggregate(BaseModel):
    """One row of v_county_value_aggregate."""

    model_config = ConfigDict(frozen=True)

    session_id: UUID
    tick: int = Field(ge=0)
    county_fips: str = Field(pattern=r"^\d{5}$")
    c_sum: float = Field(ge=0)
    v_sum: float = Field(ge=0)
    s_sum: float = Field(ge=0)
    k_sum: float = Field(ge=0)
    biocapacity_sum: float = Field(ge=0)
    hex_count: int = Field(ge=0)


class StateValueAggregate(BaseModel):
    """One row of v_state_value_aggregate."""

    model_config = ConfigDict(frozen=True)

    session_id: UUID
    tick: int = Field(ge=0)
    state_fips: str = Field(pattern=r"^\d{2}$")
    c_sum: float = Field(ge=0)
    v_sum: float = Field(ge=0)
    s_sum: float = Field(ge=0)
    k_sum: float = Field(ge=0)
    biocapacity_sum: float = Field(ge=0)
    hex_count: int = Field(ge=0)


class NationalValueAggregate(BaseModel):
    """One row of v_national_value_aggregate."""

    model_config = ConfigDict(frozen=True)

    session_id: UUID
    tick: int = Field(ge=0)
    national_id: str  # "USA"
    c_sum: float = Field(ge=0)
    v_sum: float = Field(ge=0)
    s_sum: float = Field(ge=0)
    k_sum: float = Field(ge=0)
    biocapacity_sum: float = Field(ge=0)
    hex_count: int = Field(ge=0)


class GlobalPhiBalance(BaseModel):
    """One row of v_global_phi_balance.

    The ``residual`` field is the FR-044 conservation check at year-boundary
    ticks: ``phi_week_outflow_total - phi_week_inflow_total`` must be
    within ε of zero modulo a full annual cycle.
    """

    model_config = ConfigDict(frozen=True)

    session_id: UUID
    tick: int = Field(ge=0)
    phi_week_outflow_total: float
    phi_week_inflow_total: float
    residual: float


_COUNTY_SQL = """
SELECT session_id, tick, county_fips, c_sum, v_sum, s_sum, k_sum,
       biocapacity_sum, hex_count
FROM v_county_value_aggregate
WHERE session_id = %s AND tick = %s AND county_fips = %s
"""

_STATE_SQL = """
SELECT session_id, tick, state_fips, c_sum, v_sum, s_sum, k_sum,
       biocapacity_sum, hex_count
FROM v_state_value_aggregate
WHERE session_id = %s AND tick = %s AND state_fips = %s
"""

_NATIONAL_SQL_RANGE = """
SELECT session_id, tick, national_id, c_sum, v_sum, s_sum, k_sum,
       biocapacity_sum, hex_count
FROM v_national_value_aggregate
WHERE session_id = %s AND tick BETWEEN %s AND %s
ORDER BY tick
"""

_PHI_BALANCE_SQL_ANNUAL = """
SELECT session_id, tick, phi_week_outflow_total, phi_week_inflow_total,
       residual
FROM v_global_phi_balance
WHERE session_id = %s AND tick %% 52 = 0
ORDER BY tick
"""

_PHI_BALANCE_SQL_ALL = """
SELECT session_id, tick, phi_week_outflow_total, phi_week_inflow_total,
       residual
FROM v_global_phi_balance
WHERE session_id = %s
ORDER BY tick
"""


def fetch_county_aggregate(
    *,
    runtime: PostgresRuntime,
    session_id: UUID,
    tick: int,
    county_fips: str,
) -> CountyValueAggregate | None:
    """Single-county c/v/s/k aggregate at one tick (SC-002 test target)."""
    with runtime._pool.connection() as conn:  # noqa: SLF001 — sibling-module access
        row = conn.execute(_COUNTY_SQL, (str(session_id), tick, county_fips)).fetchone()
    if row is None:
        return None
    return CountyValueAggregate(
        session_id=row[0],
        tick=row[1],
        county_fips=row[2],
        c_sum=row[3] or 0.0,
        v_sum=row[4] or 0.0,
        s_sum=row[5] or 0.0,
        k_sum=row[6] or 0.0,
        biocapacity_sum=row[7] or 0.0,
        hex_count=row[8] or 0,
    )


def fetch_state_aggregate(
    *,
    runtime: PostgresRuntime,
    session_id: UUID,
    tick: int,
    state_fips: str,
) -> StateValueAggregate | None:
    """Single-state c/v/s/k aggregate at one tick."""
    with runtime._pool.connection() as conn:  # noqa: SLF001
        row = conn.execute(_STATE_SQL, (str(session_id), tick, state_fips)).fetchone()
    if row is None:
        return None
    return StateValueAggregate(
        session_id=row[0],
        tick=row[1],
        state_fips=row[2],
        c_sum=row[3] or 0.0,
        v_sum=row[4] or 0.0,
        s_sum=row[5] or 0.0,
        k_sum=row[6] or 0.0,
        biocapacity_sum=row[7] or 0.0,
        hex_count=row[8] or 0,
    )


def fetch_national_aggregate(
    *,
    runtime: PostgresRuntime,
    session_id: UUID,
    tick_range: tuple[int, int],
) -> list[NationalValueAggregate]:
    """National-aggregate time-series for an inclusive tick range."""
    lo, hi = tick_range
    with runtime._pool.connection() as conn:  # noqa: SLF001
        rows = conn.execute(_NATIONAL_SQL_RANGE, (str(session_id), lo, hi)).fetchall()
    return [
        NationalValueAggregate(
            session_id=r[0],
            tick=r[1],
            national_id=r[2],
            c_sum=r[3] or 0.0,
            v_sum=r[4] or 0.0,
            s_sum=r[5] or 0.0,
            k_sum=r[6] or 0.0,
            biocapacity_sum=r[7] or 0.0,
            hex_count=r[8] or 0,
        )
        for r in rows
    ]


def fetch_global_phi_balance(
    *,
    runtime: PostgresRuntime,
    session_id: UUID,
    annual_only: bool = False,
) -> list[GlobalPhiBalance]:
    """Cross-boundary Φ-balance time-series.

    ``annual_only=True`` filters to year-boundary ticks (``tick % 52 == 0``),
    which is the cadence at which FR-044 asserts the residual is zero.
    """
    sql = _PHI_BALANCE_SQL_ANNUAL if annual_only else _PHI_BALANCE_SQL_ALL
    with runtime._pool.connection() as conn:  # noqa: SLF001
        rows = conn.execute(sql, (str(session_id),)).fetchall()
    return [
        GlobalPhiBalance(
            session_id=r[0],
            tick=r[1],
            phi_week_outflow_total=r[2] or 0.0,
            phi_week_inflow_total=r[3] or 0.0,
            residual=r[4] or 0.0,
        )
        for r in rows
    ]


__all__ = [
    "CountyValueAggregate",
    "StateValueAggregate",
    "NationalValueAggregate",
    "GlobalPhiBalance",
    "fetch_county_aggregate",
    "fetch_state_aggregate",
    "fetch_national_aggregate",
    "fetch_global_phi_balance",
]
