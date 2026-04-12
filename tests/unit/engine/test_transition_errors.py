"""RED phase: Tests for TransitionError union.

Spec 040 Discipline 2: Closed union of modeled failure modes.
"""

from __future__ import annotations

import pytest


class TestTransitionErrors:
    """Tests for the TransitionError union variants."""

    def test_negative_capital_stock_fields(self) -> None:
        from babylon.engine.errors import NegativeCapitalStock

        err = NegativeCapitalStock(node_id="C001", field="wealth", value=-5.0)
        assert err.node_id == "C001"
        assert err.field == "wealth"
        assert err.value == -5.0

    def test_insufficient_labor_hours_fields(self) -> None:
        from babylon.engine.errors import InsufficientLaborHours

        err = InsufficientLaborHours(node_id="C002", required=100.0, available=50.0)
        assert err.required == 100.0
        assert err.available == 50.0

    def test_missing_organization_fields(self) -> None:
        from babylon.engine.errors import MissingOrganization

        err = MissingOrganization(org_id="ORG_001")
        assert err.org_id == "ORG_001"

    def test_infeasible_migration_fields(self) -> None:
        from babylon.engine.errors import InfeasibleMigration

        err = InfeasibleMigration(
            node_id="C003", from_territory="T1", to_territory="T2", reason="no path"
        )
        assert err.from_territory == "T1"
        assert err.to_territory == "T2"

    def test_conservation_violation_fields(self) -> None:
        from babylon.engine.errors import ConservationViolation

        err = ConservationViolation(
            invariant_name="value_conservation",
            expected=100.0,
            actual=95.0,
            tolerance=1e-9,
        )
        assert err.invariant_name == "value_conservation"

    def test_errors_are_frozen(self) -> None:
        from babylon.engine.errors import NegativeCapitalStock

        err = NegativeCapitalStock(node_id="C001", field="wealth", value=-1.0)
        with pytest.raises(AttributeError):
            err.node_id = "C999"  # type: ignore[misc]

    def test_transition_error_type_alias(self) -> None:
        """TransitionError is a union of all error types."""
        from babylon.engine.errors import (
            NegativeCapitalStock,
            TransitionError,
        )

        err: TransitionError = NegativeCapitalStock(node_id="C001", field="wealth", value=-1.0)
        assert isinstance(err, NegativeCapitalStock)

    def test_all_errors_have_str(self) -> None:
        from babylon.engine.errors import (
            ConservationViolation,
            InfeasibleMigration,
            InsufficientLaborHours,
            MissingOrganization,
            NegativeCapitalStock,
        )

        errors = [
            NegativeCapitalStock(node_id="C1", field="wealth", value=-1.0),
            InsufficientLaborHours(node_id="C2", required=10.0, available=5.0),
            MissingOrganization(org_id="ORG1"),
            InfeasibleMigration(
                node_id="C3", from_territory="T1", to_territory="T2", reason="blocked"
            ),
            ConservationViolation(invariant_name="test", expected=1.0, actual=0.5, tolerance=0.01),
        ]
        for err in errors:
            assert len(str(err)) > 0
