"""Validators for the spec-068 BEA I-O ingest pipeline.

Two identities are checked at ingest time:

* **FR-002 accounting identity** — ``|GO - II - VA| / GO <= 0.01`` per
  ``fact_bea_national_industry`` row. Failing rows are recorded as
  ``AccountingViolation`` entries in the audit report; rows are still
  written (the audit surface is what fails SC-003, not the DB write).
* **FR-004 column-sum identity** — for every (target_industry, year),
  ``sum_i a_ij ≈ intermediate_inputs_share[j] ± 0.001``. Validated in
  US2 (see :mod:`babylon.reference.bea.ingest.validators` US2 helpers,
  added in T036).
"""

from __future__ import annotations

from decimal import Decimal

from babylon.reference.bea.ingest.audit_report import AccountingViolation
from babylon.reference.bea.models import BEAIndustryAnnualRecord

_FR_002_DEFAULT_TOLERANCE: float = 0.01  # ±1 % of gross_output


def validate_accounting_identity(
    record: BEAIndustryAnnualRecord,
    tolerance: float = _FR_002_DEFAULT_TOLERANCE,
) -> AccountingViolation | None:
    """Check the BEA accounting identity ``|GO - II - VA| / GO <= tolerance``.

    Args:
        record: One in-transit ``fact_bea_national_industry`` row.
        tolerance: Maximum allowed residual fraction (default ``0.01``).

    Returns:
        ``None`` if the row passes (or if any of GO/II/VA is NULL, or if
        GO is exactly zero — these cases are skipped, not failed).
        Otherwise an ``AccountingViolation`` describing the residual.
    """
    go = record.gross_output_millions
    ii = record.intermediate_inputs_millions
    va = record.value_added_millions

    if go is None or ii is None or va is None:
        return None
    if go == Decimal("0"):
        return None

    residual = go - ii - va
    residual_fraction = float(abs(residual) / go)

    if residual_fraction <= tolerance:
        return None

    return AccountingViolation(
        bea_industry_id=record.bea_industry_id,
        year=record.year,
        gross_output=go,
        intermediate_inputs=ii,
        value_added=va,
        residual_fraction=residual_fraction,
    )
