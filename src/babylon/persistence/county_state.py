"""Pydantic models for spec-065 per-tick county-resolution subsystem state.

Three frozen row models, one per subsystem state table introduced by
spec-065 migrations 0020-0022:

- :class:`DynamicConsciousnessState` — survival calculus +
  ternary ideology simplex (migration 0020)
- :class:`DynamicDemographicsState` — population (migration 0021)
- :class:`DynamicEmploymentState`   — employment_proxy (migration 0022)

All three share the same identity key shape
``(session_id, tick, county_fips)`` and are owned by their respective
subsystem per Constitution II.11. The trace-emission view
(``view_runtime_trace_emission``, migration 0023) JOINs all three to
source the previously-NULL columns spec-064 emitted.

See Also:
    ``specs/065-engine-bridging/contracts/subsystem_state_tables.yaml``
    ``specs/065-engine-bridging/data-model.md §2``
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "DynamicConsciousnessState",
    "DynamicDemographicsState",
    "DynamicEmploymentState",
]


class DynamicConsciousnessState(BaseModel):
    """One row of ``dynamic_consciousness_state`` (migration 0020).

    Owner: ``ConsciousnessSystem`` (spec-034 / 043).
    Primary key: ``(session_id, tick, county_fips)``.

    The ternary simplex invariant ``r + l + f ≈ 1.0`` (within ±1e-9)
    is enforced by the engine, not by DB CHECK constraints — float
    drift through serialization may exceed any reasonable DB tolerance.
    The spec-053 US3 invariant test gates this property end-to-end.
    """

    model_config = ConfigDict(frozen=True)

    session_id: UUID
    tick: int = Field(ge=0)
    county_fips: str = Field(pattern=r"^\d{5}$")

    p_acquiescence: float = Field(ge=0.0, le=1.0)
    p_revolution: float = Field(ge=0.0, le=1.0)

    ideology_r: float = Field(ge=0.0, le=1.0)
    ideology_l: float = Field(ge=0.0, le=1.0)
    ideology_f: float = Field(ge=0.0, le=1.0)


class DynamicDemographicsState(BaseModel):
    """One row of ``dynamic_demographics_state`` (migration 0021).

    Owner: demographics subsystem (Census ACS interpolated to weekly
    cadence per spec-062 year-scoped lookup policy).
    Primary key: ``(session_id, tick, county_fips)``.
    """

    model_config = ConfigDict(frozen=True)

    session_id: UUID
    tick: int = Field(ge=0)
    county_fips: str = Field(pattern=r"^\d{5}$")

    population: int = Field(ge=0)


class DynamicEmploymentState(BaseModel):
    """One row of ``dynamic_employment_state`` (migration 0022).

    Owner: employment subsystem (QCEW annual employment interpolated
    to weekly; ``ImperialRentSystem`` modulates via wage-extraction
    feedback).
    Primary key: ``(session_id, tick, county_fips)``.
    """

    model_config = ConfigDict(frozen=True)

    session_id: UUID
    tick: int = Field(ge=0)
    county_fips: str = Field(pattern=r"^\d{5}$")

    employment_proxy: float = Field(ge=0.0)
