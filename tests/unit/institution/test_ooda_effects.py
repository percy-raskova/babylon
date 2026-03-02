"""Unit tests for hegemonic fraction OODA effects (Feature 040, US3).

Validates:
- SC-009: LIBERAL favors ASSIMILATE, REVANCHIST favors REPRESS
- Bonapartist produces self-preservation behavior
- Return type and key structure
"""

from __future__ import annotations

import pytest

from babylon.institution.ooda_effects import hegemonic_fraction_effect
from babylon.models.enums import ActionType, RulingClassFraction


class TestLiberalFraction:
    """LIBERAL_TECHNOCRATIC hegemony effects."""

    def test_liberal_prefers_assimilate(self) -> None:
        """SC-009: LIBERAL hegemony should prefer ASSIMILATE."""
        result = hegemonic_fraction_effect(RulingClassFraction.LIBERAL_TECHNOCRATIC)
        assert ActionType.ASSIMILATE in result["preferred_actions"]

    @pytest.mark.math
    def test_liberal_high_escalation_reluctance(self) -> None:
        """LIBERAL should have high escalation reluctance (consent-based)."""
        result = hegemonic_fraction_effect(RulingClassFraction.LIBERAL_TECHNOCRATIC)
        assert result["escalation_reluctance"] == 0.7

    def test_liberal_returns_dict(self) -> None:
        """Return type should be dict with expected keys."""
        result = hegemonic_fraction_effect(RulingClassFraction.LIBERAL_TECHNOCRATIC)
        assert isinstance(result, dict)
        assert "preferred_actions" in result
        assert "escalation_reluctance" in result


class TestRevanchistFraction:
    """REVANCHIST_FASCIST hegemony effects."""

    def test_revanchist_prefers_repress(self) -> None:
        """SC-009: REVANCHIST hegemony should prefer REPRESS."""
        result = hegemonic_fraction_effect(RulingClassFraction.REVANCHIST_FASCIST)
        assert ActionType.REPRESS in result["preferred_actions"]

    @pytest.mark.math
    def test_revanchist_low_escalation_reluctance(self) -> None:
        """REVANCHIST should have low escalation reluctance (naked repression)."""
        result = hegemonic_fraction_effect(RulingClassFraction.REVANCHIST_FASCIST)
        assert result["escalation_reluctance"] == 0.2

    def test_revanchist_not_assimilate(self) -> None:
        """REVANCHIST should not prefer ASSIMILATE."""
        result = hegemonic_fraction_effect(RulingClassFraction.REVANCHIST_FASCIST)
        assert ActionType.ASSIMILATE not in result["preferred_actions"]


class TestBonapartistFraction:
    """INSTITUTIONALIST_BONAPARTIST hegemony effects."""

    def test_bonapartist_prefers_surveil(self) -> None:
        """Bonapartist should prefer SURVEIL (institutional self-preservation)."""
        result = hegemonic_fraction_effect(RulingClassFraction.INSTITUTIONALIST_BONAPARTIST)
        assert ActionType.SURVEIL in result["preferred_actions"]

    @pytest.mark.math
    def test_bonapartist_medium_escalation_reluctance(self) -> None:
        """Bonapartist should have medium escalation reluctance."""
        result = hegemonic_fraction_effect(RulingClassFraction.INSTITUTIONALIST_BONAPARTIST)
        assert result["escalation_reluctance"] == 0.5

    def test_bonapartist_not_repress(self) -> None:
        """Bonapartist should not prefer REPRESS."""
        result = hegemonic_fraction_effect(RulingClassFraction.INSTITUTIONALIST_BONAPARTIST)
        assert ActionType.REPRESS not in result["preferred_actions"]


class TestEscalationOrdering:
    """Escalation reluctance should follow expected ordering."""

    @pytest.mark.math
    def test_reluctance_ordering(self) -> None:
        """REVANCHIST < BONAPARTIST < LIBERAL in escalation reluctance."""
        liberal = hegemonic_fraction_effect(RulingClassFraction.LIBERAL_TECHNOCRATIC)
        revanchist = hegemonic_fraction_effect(RulingClassFraction.REVANCHIST_FASCIST)
        bonapartist = hegemonic_fraction_effect(RulingClassFraction.INSTITUTIONALIST_BONAPARTIST)

        assert revanchist["escalation_reluctance"] < bonapartist["escalation_reluctance"]
        assert bonapartist["escalation_reluctance"] < liberal["escalation_reluctance"]


class TestAllFractions:
    """Ensure all RulingClassFraction values are handled."""

    @pytest.mark.parametrize("fraction", list(RulingClassFraction))
    def test_all_fractions_return_valid_dict(self, fraction: RulingClassFraction) -> None:
        """Every fraction should return a dict with required keys."""
        result = hegemonic_fraction_effect(fraction)
        assert isinstance(result, dict)
        assert "preferred_actions" in result
        assert "escalation_reluctance" in result
        assert isinstance(result["preferred_actions"], list)
        assert 0.0 <= result["escalation_reluctance"] <= 1.0
