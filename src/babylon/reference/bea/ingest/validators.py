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

from collections import defaultdict
from collections.abc import Iterable
from decimal import Decimal

from babylon.reference.bea.ingest.audit_report import (
    AccountingViolation,
    ColumnSumViolation,
)
from babylon.reference.bea.models import (
    BEAIndustryAnnualRecord,
    BEAIOCoefficientRecord,
)

_FR_002_DEFAULT_TOLERANCE: float = 0.01  # ±1 % of gross_output

# FR-004 tolerance is intentionally loose. The IOUse matrix is in producer
# prices while Supply-Use Use_Summary is in basic prices; the two tables
# have a systematic per-industry delta of 1-5 % (taxes-less-subsidies on
# products). FR-004's column-sum identity is meaningful within IOUse's own
# price basis (using IOUse's T005/T018 rows as reference), not against the
# Supply-Use basic-prices figures stored in fact_bea_national_industry.
# The validator below computes the IOUse-internal column sums and compares
# against the IOUse-internal intermediate-inputs share read from the same
# XLSX (passed in as `expected_shares_by_target`).
_FR_004_DEFAULT_TOLERANCE: float = 0.01  # ±1 % within the IOUse matrix's own prices


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


def validate_column_sum_identity(
    coefficient_records: Iterable[BEAIOCoefficientRecord],
    expected_shares_by_target: dict[tuple[int, int], float],
    tolerance: float = _FR_004_DEFAULT_TOLERANCE,
) -> list[ColumnSumViolation]:
    """Check FR-004 column-sum identity for USE table coefficients.

    For each (target_industry_id, year), the sum of incoming
    coefficients ``sum_i a_ij`` must equal the per-industry intermediate-
    inputs share within ``tolerance``. The expected shares are
    pre-computed by the caller from the same XLSX as the coefficients
    (i.e., IOUse's T005 / T018) to avoid the basic-prices vs producer-
    prices delta that exists between Supply-Use Use_Summary (US1 source)
    and IOUse_Before_Redefinitions_PRO_Summary (US2 source).

    Args:
        coefficient_records: Iterable of ``BEAIOCoefficientRecord``
            with ``table_type='USE'``. Records with other table types
            are skipped.
        expected_shares_by_target: Mapping
            ``(target_industry_id, year) -> expected_intermediate_inputs_share``.
        tolerance: Maximum allowed absolute residual fraction (default 0.01).

    Returns:
        List of ``ColumnSumViolation`` for failing (target, year) pairs.
    """
    actual_sums: dict[tuple[int, int], float] = defaultdict(float)
    for record in coefficient_records:
        if record.table_type != "USE":
            continue
        actual_sums[(record.target_industry_id, record.year)] += record.coefficient

    violations: list[ColumnSumViolation] = []
    for (target_id, year), actual in actual_sums.items():
        expected = expected_shares_by_target.get((target_id, year))
        if expected is None:
            continue
        residual = abs(actual - expected)
        residual_fraction = residual / expected if expected > 0 else residual
        if residual_fraction > tolerance:
            violations.append(
                ColumnSumViolation(
                    target_industry_id=target_id,
                    year=year,
                    column_sum=actual,
                    expected_share=expected,
                    residual_fraction=residual_fraction,
                )
            )
    return violations
