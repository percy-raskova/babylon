"""Frozen Pydantic models for the spec-068 BEA I-O ingest pipeline.

These are in-memory record types produced by the XLSX parsers and
consumed by the UPSERT writers. They are NOT persistence models —
the SQLAlchemy ORM in `src/babylon/reference/schema.py` owns the DB
shape; these mirror it for type-safe ingest validation.

Per constitution II.2 (Primitives vs Derived), the share fields
(``intermediate_inputs_share``, ``value_added_share``) are NOT
modeled here — they live only on the lookup-service result types
(see :mod:`babylon.reference.bea.lookup_results`).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt

BEATableType = Literal["USE", "MAKE", "SUPPLY", "TOTAL_REQ", "IMPORT_USE"]


class BEAIndustryAnnualRecord(BaseModel):
    """One row of ``fact_bea_national_industry`` in transit (ingest-side).

    Maps 1-to-1 to a persisted row, including the three BEA primitives
    and the spec-068 vintage tracking column.
    """

    model_config = ConfigDict(frozen=True)

    bea_industry_id: NonNegativeInt
    year: NonNegativeInt
    gross_output_millions: Decimal | None
    intermediate_inputs_millions: Decimal | None
    value_added_millions: Decimal | None
    vintage_published_date: date | None = None


class BEAIOCoefficientRecord(BaseModel):
    """One row of ``fact_bea_io_coefficient`` in transit (ingest-side).

    Represents a single ``a_ij`` entry of the BEA direct-requirements
    matrix for a given (source, target, year, table_type) tuple.
    """

    model_config = ConfigDict(frozen=True)

    source_industry_id: NonNegativeInt
    target_industry_id: NonNegativeInt
    table_type: BEATableType
    year: NonNegativeInt
    coefficient: float = Field(ge=0.0, le=1.5)
    vintage_published_date: date | None = None


class BEAConcordanceRecord(BaseModel):
    """One row of ``bridge_naics_bea`` in transit (ingest-side)."""

    model_config = ConfigDict(frozen=True)

    naics_id: NonNegativeInt
    bea_industry_id: NonNegativeInt
