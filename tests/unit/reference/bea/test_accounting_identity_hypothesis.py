"""T020: Hypothesis property tests for FR-002 invariance (spec-068)."""

from __future__ import annotations

from decimal import Decimal

import hypothesis.strategies as st
import pytest
from hypothesis import HealthCheck, assume, given, settings

from babylon.reference.bea.ingest.audit_report import AccountingViolation
from babylon.reference.bea.ingest.validators import validate_accounting_identity
from babylon.reference.bea.models import BEAIndustryAnnualRecord

_REASONABLE_DECIMAL = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("999999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


_HYPOTHESIS_SETTINGS = settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)


@pytest.mark.unit
class TestAccountingIdentityHypothesis:
    """Property: validator detects violations exactly when residual exceeds tolerance."""

    @_HYPOTHESIS_SETTINGS
    @given(go=_REASONABLE_DECIMAL, ii_frac=st.floats(min_value=0.0, max_value=1.0))
    def test_exact_identity_always_passes(self, go: Decimal, ii_frac: float) -> None:
        """If II + VA == GO exactly, identity must always pass."""
        ii = (go * Decimal(str(ii_frac))).quantize(Decimal("0.01"))
        va = go - ii
        record = BEAIndustryAnnualRecord(
            bea_industry_id=1,
            year=2015,
            gross_output_millions=go,
            intermediate_inputs_millions=ii,
            value_added_millions=va,
        )
        assert validate_accounting_identity(record) is None

    @_HYPOTHESIS_SETTINGS
    @given(
        go=_REASONABLE_DECIMAL,
        ii=_REASONABLE_DECIMAL,
        va=_REASONABLE_DECIMAL,
    )
    def test_violation_iff_residual_exceeds_tolerance(
        self, go: Decimal, ii: Decimal, va: Decimal
    ) -> None:
        """Validator returns Violation iff actual residual fraction > 1 %."""
        assume(go > Decimal("0"))
        record = BEAIndustryAnnualRecord(
            bea_industry_id=1,
            year=2015,
            gross_output_millions=go,
            intermediate_inputs_millions=ii,
            value_added_millions=va,
        )
        actual_residual = abs(float((go - ii - va) / go))
        result = validate_accounting_identity(record)
        if actual_residual <= 0.01:
            assert result is None
        else:
            assert isinstance(result, AccountingViolation)
            assert abs(result.residual_fraction - actual_residual) < 1e-9

    @_HYPOTHESIS_SETTINGS
    @given(
        go=_REASONABLE_DECIMAL,
        ii=_REASONABLE_DECIMAL,
        va=_REASONABLE_DECIMAL,
        tolerance=st.floats(min_value=0.001, max_value=0.5),
    )
    def test_tolerance_parameter_is_monotonic(
        self, go: Decimal, ii: Decimal, va: Decimal, tolerance: float
    ) -> None:
        """Loosening tolerance can only convert violations to passes, never vice-versa."""
        assume(go > Decimal("0"))
        record = BEAIndustryAnnualRecord(
            bea_industry_id=1,
            year=2015,
            gross_output_millions=go,
            intermediate_inputs_millions=ii,
            value_added_millions=va,
        )
        loose = validate_accounting_identity(record, tolerance=tolerance)
        strict = validate_accounting_identity(record, tolerance=tolerance / 2)
        if loose is not None:
            # strict tolerance can only also fail (or be equal)
            assert strict is not None
