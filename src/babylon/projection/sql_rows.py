"""Frozen row shapes retained for language-neutral projection contracts.

These models describe projection payloads only. They open no database and do
not imply that the retired Python PostgreSQL views remain available after the
Gate 3 authority transition.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CountyValueAggregate(BaseModel):
    """One county value aggregate projection row."""

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
    """One state value aggregate projection row."""

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
    """One national value aggregate projection row."""

    model_config = ConfigDict(frozen=True)

    session_id: UUID
    tick: int = Field(ge=0)
    national_id: str
    c_sum: float = Field(ge=0)
    v_sum: float = Field(ge=0)
    s_sum: float = Field(ge=0)
    k_sum: float = Field(ge=0)
    biocapacity_sum: float = Field(ge=0)
    hex_count: int = Field(ge=0)


class GlobalPhiBalance(BaseModel):
    """One global phi balance projection row."""

    model_config = ConfigDict(frozen=True)

    session_id: UUID
    tick: int = Field(ge=0)
    phi_week_outflow_total: float
    phi_week_inflow_total: float
    residual: float


__all__ = [
    "CountyValueAggregate",
    "GlobalPhiBalance",
    "NationalValueAggregate",
    "StateValueAggregate",
]
