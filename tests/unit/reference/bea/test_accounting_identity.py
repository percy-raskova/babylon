"""T017: Unit tests for the FR-002 BEA accounting-identity validator.

The identity: ``|GO - II - VA| / GO <= 0.01`` (1 %).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from babylon.reference.bea.ingest.audit_report import AccountingViolation
from babylon.reference.bea.models import BEAIndustryAnnualRecord


@pytest.fixture
def passing_record() -> BEAIndustryAnnualRecord:
    """Record where II + VA == GO exactly."""
    return BEAIndustryAnnualRecord(
        bea_industry_id=10,
        year=2015,
        gross_output_millions=Decimal("1000.00"),
        intermediate_inputs_millions=Decimal("400.00"),
        value_added_millions=Decimal("600.00"),
    )


@pytest.fixture
def borderline_record() -> BEAIndustryAnnualRecord:
    """Record where residual is exactly 1 % of GO — at the tolerance boundary."""
    return BEAIndustryAnnualRecord(
        bea_industry_id=11,
        year=2015,
        gross_output_millions=Decimal("1000.00"),
        intermediate_inputs_millions=Decimal("400.00"),
        value_added_millions=Decimal("590.00"),  # residual = 10 / 1000 = 0.01
    )


@pytest.fixture
def failing_record() -> BEAIndustryAnnualRecord:
    """Record where residual exceeds 1 % of GO."""
    return BEAIndustryAnnualRecord(
        bea_industry_id=12,
        year=2015,
        gross_output_millions=Decimal("1000.00"),
        intermediate_inputs_millions=Decimal("400.00"),
        value_added_millions=Decimal("500.00"),  # residual = 100 / 1000 = 0.10
    )


@pytest.fixture
def null_record() -> BEAIndustryAnnualRecord:
    """Record with NULL value-added — should be skipped (no violation)."""
    return BEAIndustryAnnualRecord(
        bea_industry_id=13,
        year=2015,
        gross_output_millions=Decimal("1000.00"),
        intermediate_inputs_millions=Decimal("400.00"),
        value_added_millions=None,
    )


@pytest.mark.unit
class TestAccountingIdentity:
    """FR-002: II + VA == GO within ±1 %."""

    def test_passing_returns_none(self, passing_record: BEAIndustryAnnualRecord) -> None:
        from babylon.reference.bea.ingest.validators import validate_accounting_identity

        assert validate_accounting_identity(passing_record) is None

    def test_borderline_returns_none(self, borderline_record: BEAIndustryAnnualRecord) -> None:
        from babylon.reference.bea.ingest.validators import validate_accounting_identity

        # Residual is exactly at tolerance — must pass (<=, not <).
        assert validate_accounting_identity(borderline_record) is None

    def test_failing_returns_violation(self, failing_record: BEAIndustryAnnualRecord) -> None:
        from babylon.reference.bea.ingest.validators import validate_accounting_identity

        v = validate_accounting_identity(failing_record)
        assert isinstance(v, AccountingViolation)
        assert v.bea_industry_id == 12
        assert v.year == 2015
        assert abs(v.residual_fraction - 0.10) < 1e-9

    def test_null_returns_none(self, null_record: BEAIndustryAnnualRecord) -> None:
        """NULL columns are not a violation — they are missing data, not bad data."""
        from babylon.reference.bea.ingest.validators import validate_accounting_identity

        assert validate_accounting_identity(null_record) is None

    def test_zero_gross_output_returns_none(self) -> None:
        """GO == 0 has no defined identity residual_fraction — must be skipped."""
        from babylon.reference.bea.ingest.validators import validate_accounting_identity

        record = BEAIndustryAnnualRecord(
            bea_industry_id=14,
            year=2015,
            gross_output_millions=Decimal("0"),
            intermediate_inputs_millions=Decimal("0"),
            value_added_millions=Decimal("0"),
        )
        assert validate_accounting_identity(record) is None

    def test_custom_tolerance(self, borderline_record: BEAIndustryAnnualRecord) -> None:
        """Tolerance is parameterized — tightening to 0.005 should now fail."""
        from babylon.reference.bea.ingest.validators import validate_accounting_identity

        v = validate_accounting_identity(borderline_record, tolerance=0.005)
        assert isinstance(v, AccountingViolation)
