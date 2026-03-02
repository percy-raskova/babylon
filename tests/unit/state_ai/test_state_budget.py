"""Unit tests for StateBudget and LegalFramework models (Feature 039, T008).

Tests frozen Pydantic validation, budget constraints, allocation validation,
and LegalFramework law_type validation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from tests.unit.state_ai.conftest import make_legal_framework, make_state_budget

from babylon.models.entities.state_apparatus_ai import (
    VALID_LAW_TYPES,
    StateBudget,
)
from babylon.models.enums import StateActionType


class TestStateBudgetConstruction:
    """T008: StateBudget model validation."""

    def test_valid_budget(self) -> None:
        budget = make_state_budget()
        assert budget.revenue == 100.0
        assert budget.available == 100.0
        assert len(budget.allocated) == 6

    def test_available_cannot_exceed_revenue(self) -> None:
        with pytest.raises(ValidationError, match="cannot exceed revenue"):
            make_state_budget(available=200.0, revenue=100.0)

    def test_allocation_keys_must_be_top_level(self) -> None:
        with pytest.raises(ValidationError, match="top-level verb"):
            StateBudget(
                revenue=100.0,
                available=100.0,
                allocated={StateActionType.RAID: 50.0},
                imperial_rent_pool=50.0,
            )

    def test_allocation_values_must_be_non_negative(self) -> None:
        with pytest.raises(ValidationError, match=">= 0"):
            StateBudget(
                revenue=100.0,
                available=100.0,
                allocated={StateActionType.REPRESS: -10.0},
                imperial_rent_pool=50.0,
            )

    def test_allocation_sum_cannot_exceed_revenue(self) -> None:
        with pytest.raises(ValidationError, match="cannot exceed revenue"):
            StateBudget(
                revenue=100.0,
                available=100.0,
                allocated={
                    StateActionType.ADMINISTER: 60.0,
                    StateActionType.REPRESS: 60.0,
                },
                imperial_rent_pool=50.0,
            )

    def test_zero_budget(self) -> None:
        budget = StateBudget(
            revenue=0.0,
            available=0.0,
            allocated={},
            imperial_rent_pool=0.0,
        )
        assert budget.revenue == 0.0
        assert budget.available == 0.0

    def test_frozen(self) -> None:
        budget = make_state_budget()
        with pytest.raises(ValidationError):
            budget.available = 50.0  # type: ignore[misc]


class TestLegalFrameworkConstruction:
    """T008: LegalFramework model validation."""

    def test_valid_framework(self) -> None:
        law = make_legal_framework()
        assert law.framework_id == "law_001"
        assert law.law_type == "SURVEILLANCE_EXPANSION"

    def test_all_valid_law_types(self) -> None:
        for law_type in VALID_LAW_TYPES:
            law = make_legal_framework(law_type=law_type)
            assert law.law_type == law_type

    def test_invalid_law_type_rejected(self) -> None:
        with pytest.raises(ValidationError, match="law_type"):
            make_legal_framework(law_type="INVALID_TYPE")

    def test_severity_within_probability_range(self) -> None:
        law = make_legal_framework(severity=0.0)
        assert law.severity == 0.0

        law2 = make_legal_framework(severity=1.0)
        assert law2.severity == 1.0

    def test_severity_out_of_range_rejected(self) -> None:
        with pytest.raises(ValidationError):
            make_legal_framework(severity=1.5)

    def test_negative_tick_rejected(self) -> None:
        with pytest.raises(ValidationError):
            make_legal_framework(created_tick=-1)

    def test_empty_framework_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            make_legal_framework(framework_id="")

    def test_frozen(self) -> None:
        law = make_legal_framework()
        with pytest.raises(ValidationError):
            law.severity = 0.9  # type: ignore[misc]
