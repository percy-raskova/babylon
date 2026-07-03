"""Unit tests for FactionBalance model (Feature 039, T006).

Tests frozen Pydantic validation, weight normalization invariant,
computed dominant_faction, and immutability.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.entities.state_apparatus_ai import FactionBalance
from babylon.models.enums import StateFaction
from tests.constants import TestConstants

TC = TestConstants


class TestFactionBalanceConstruction:
    """T006: FactionBalance model validation."""

    def test_detroit_2010_default(self) -> None:
        fb = FactionBalance(
            finance_capital=TC.StateAI.DETROIT_FC_WEIGHT,
            security_state=TC.StateAI.DETROIT_SS_WEIGHT,
            settler_populist=TC.StateAI.DETROIT_SP_WEIGHT,
            stability=TC.StateAI.DETROIT_STABILITY,
            legitimacy=TC.StateAI.DETROIT_LEGITIMACY,
        )
        assert fb.finance_capital == TC.StateAI.DETROIT_FC_WEIGHT
        assert fb.security_state == TC.StateAI.DETROIT_SS_WEIGHT
        assert fb.settler_populist == TC.StateAI.DETROIT_SP_WEIGHT

    def test_weights_sum_to_one(self) -> None:
        fb = FactionBalance(
            finance_capital=0.33,
            security_state=0.34,
            settler_populist=0.33,
            stability=0.5,
            legitimacy=0.5,
        )
        total = fb.finance_capital + fb.security_state + fb.settler_populist
        assert 0.99 <= total <= 1.01

    def test_weights_not_summing_to_one_rejected(self) -> None:
        with pytest.raises(ValidationError, match="sum to 1.0"):
            FactionBalance(
                finance_capital=0.5,
                security_state=0.5,
                settler_populist=0.5,
                stability=0.5,
                legitimacy=0.5,
            )

    def test_tolerance_accepts_floating_point_drift(self) -> None:
        """0.99 and 1.01 tolerance for floating-point arithmetic."""
        fb = FactionBalance(
            finance_capital=0.333,
            security_state=0.333,
            settler_populist=0.334,
            stability=0.5,
            legitimacy=0.5,
        )
        assert fb is not None

    def test_negative_weight_rejected(self) -> None:
        with pytest.raises(ValidationError):
            FactionBalance(
                finance_capital=-0.1,
                security_state=0.6,
                settler_populist=0.5,
                stability=0.5,
                legitimacy=0.5,
            )

    def test_weight_exceeding_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            FactionBalance(
                finance_capital=1.1,
                security_state=0.0,
                settler_populist=0.0,
                stability=0.5,
                legitimacy=0.5,
            )


class TestFactionBalanceDominant:
    """T006: Computed dominant_faction field."""

    def test_finance_capital_dominant(self) -> None:
        fb = FactionBalance(
            finance_capital=0.5,
            security_state=0.3,
            settler_populist=0.2,
            stability=0.5,
            legitimacy=0.5,
        )
        assert fb.dominant_faction == StateFaction.FINANCE_CAPITAL

    def test_security_state_dominant(self) -> None:
        fb = FactionBalance(
            finance_capital=0.2,
            security_state=0.5,
            settler_populist=0.3,
            stability=0.5,
            legitimacy=0.5,
        )
        assert fb.dominant_faction == StateFaction.SECURITY_STATE

    def test_settler_populist_dominant(self) -> None:
        fb = FactionBalance(
            finance_capital=0.2,
            security_state=0.3,
            settler_populist=0.5,
            stability=0.5,
            legitimacy=0.5,
        )
        assert fb.dominant_faction == StateFaction.SETTLER_POPULIST

    def test_detroit_2010_finance_capital_dominant(self) -> None:
        fb = FactionBalance(
            finance_capital=TC.StateAI.DETROIT_FC_WEIGHT,
            security_state=TC.StateAI.DETROIT_SS_WEIGHT,
            settler_populist=TC.StateAI.DETROIT_SP_WEIGHT,
            stability=TC.StateAI.DETROIT_STABILITY,
            legitimacy=TC.StateAI.DETROIT_LEGITIMACY,
        )
        assert fb.dominant_faction == StateFaction.FINANCE_CAPITAL


class TestFactionBalanceImmutability:
    """T006: Frozen model enforcement."""

    def test_frozen(self) -> None:
        fb = FactionBalance(
            finance_capital=0.45,
            security_state=0.30,
            settler_populist=0.25,
            stability=0.6,
            legitimacy=0.5,
        )
        with pytest.raises(ValidationError):
            fb.finance_capital = 0.5  # type: ignore[misc]

    def test_model_copy_produces_new_instance(self) -> None:
        fb = FactionBalance(
            finance_capital=0.45,
            security_state=0.30,
            settler_populist=0.25,
            stability=0.6,
            legitimacy=0.5,
        )
        fb2 = fb.model_copy(
            update={
                "finance_capital": 0.40,
                "security_state": 0.35,
            }
        )
        assert fb2.finance_capital == 0.40
        assert fb2.security_state == 0.35
        assert fb.finance_capital == 0.45  # Original unchanged
