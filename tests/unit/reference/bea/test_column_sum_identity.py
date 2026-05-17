"""T029: Unit tests for the FR-004 column-sum-identity validator (spec-068)."""

from __future__ import annotations

import pytest

from babylon.reference.bea.ingest.audit_report import ColumnSumViolation
from babylon.reference.bea.ingest.validators import validate_column_sum_identity
from babylon.reference.bea.models import BEAIOCoefficientRecord


def _record(
    src: int, tgt: int, year: int, coef: float, table_type: str = "USE"
) -> BEAIOCoefficientRecord:
    return BEAIOCoefficientRecord(
        source_industry_id=src,
        target_industry_id=tgt,
        table_type=table_type,  # type: ignore[arg-type]
        year=year,
        coefficient=coef,
    )


@pytest.mark.unit
class TestColumnSumIdentity:
    """FR-004: sum_i a_ij ≈ intermediate_inputs_share[j] within tolerance."""

    def test_exact_match_no_violations(self) -> None:
        records = [
            _record(1, 10, 2015, 0.3),
            _record(2, 10, 2015, 0.2),
            _record(3, 10, 2015, 0.1),
        ]
        # Expected col-sum = 0.6 for tgt=10
        expected = {(10, 2015): 0.6}
        assert validate_column_sum_identity(records, expected) == []

    def test_violation_exceeding_tolerance(self) -> None:
        records = [
            _record(1, 10, 2015, 0.3),
            _record(2, 10, 2015, 0.2),
        ]
        # Expected says 0.6 but actual is 0.5 → residual 0.1/0.6 = 16.6% > 1%
        expected = {(10, 2015): 0.6}
        violations = validate_column_sum_identity(records, expected)
        assert len(violations) == 1
        assert isinstance(violations[0], ColumnSumViolation)
        assert violations[0].target_industry_id == 10
        assert violations[0].year == 2015
        assert abs(violations[0].column_sum - 0.5) < 1e-9
        assert abs(violations[0].expected_share - 0.6) < 1e-9

    def test_total_req_records_are_skipped(self) -> None:
        """Only USE records are validated by FR-004 (TDR is Leontief inverse)."""
        records = [
            _record(1, 10, 2015, 0.99, table_type="TOTAL_REQ"),
        ]
        expected = {(10, 2015): 0.6}
        # No USE records → no col-sum to compare against → no violation.
        assert validate_column_sum_identity(records, expected) == []

    def test_missing_expected_share_is_skipped(self) -> None:
        """If we don't have an expected share for (tgt, year), no violation reported."""
        records = [_record(1, 99, 2015, 0.3)]
        expected: dict[tuple[int, int], float] = {}
        assert validate_column_sum_identity(records, expected) == []

    def test_borderline_just_under_tolerance(self) -> None:
        """Residual slightly under tolerance must pass."""
        records = [_record(1, 10, 2015, 0.5945)]
        expected = {(10, 2015): 0.6}
        # residual = 0.0055 / 0.6 ≈ 0.00917 < 0.01 → passes
        violations = validate_column_sum_identity(records, expected, tolerance=0.01)
        assert violations == []

    def test_custom_tolerance(self) -> None:
        records = [_record(1, 10, 2015, 0.594)]
        expected = {(10, 2015): 0.6}
        # Tightening tolerance to 0.005 should fail.
        violations = validate_column_sum_identity(records, expected, tolerance=0.005)
        assert len(violations) == 1
