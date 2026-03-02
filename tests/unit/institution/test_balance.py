"""Unit tests for internal balance update function (Feature 040, US3).

Validates:
- SC-003: Crisis drives revanchist weight up
- SC-005: Bonapartist mode triggers when threshold conditions met
- Alpha-smoothed balance dynamics
- Event generation for faction shifts and Bonapartist mode
"""

from __future__ import annotations

import pytest

from babylon.institution.balance import update_internal_balance
from babylon.models.entities.institution import (
    BonapartistModeEvent,
    FactionShiftEvent,
    InternalBalanceOfForces,
)
from babylon.models.enums import RulingClassFraction

from .conftest import make_balance


class TestBasicDynamics:
    """Alpha-smoothed balance shift mechanics."""

    @pytest.mark.math
    def test_crisis_drives_revanchist_up(self) -> None:
        """SC-003: High crisis_intensity should increase revanchist weight."""
        balance = make_balance()
        new_balance, _ = update_internal_balance(
            balance,
            crisis_intensity=0.8,
            legitimacy=0.7,
            external_threat=0.0,
        )
        assert new_balance.revanchist_fascist > balance.revanchist_fascist

    @pytest.mark.math
    def test_low_legitimacy_weakens_liberal(self) -> None:
        """Low legitimacy should reduce liberal weight."""
        balance = make_balance()
        new_balance, _ = update_internal_balance(
            balance,
            crisis_intensity=0.0,
            legitimacy=0.2,
            external_threat=0.0,
        )
        assert new_balance.liberal_technocratic < balance.liberal_technocratic

    @pytest.mark.math
    def test_external_threat_drives_bonapartist_up(self) -> None:
        """External threat should increase bonapartist weight."""
        balance = make_balance()
        new_balance, _ = update_internal_balance(
            balance,
            crisis_intensity=0.0,
            legitimacy=1.0,
            external_threat=0.8,
        )
        assert new_balance.institutionalist_bonapartist > balance.institutionalist_bonapartist

    @pytest.mark.math
    def test_no_change_at_equilibrium(self) -> None:
        """Zero inputs should produce minimal change."""
        balance = make_balance()
        new_balance, _ = update_internal_balance(
            balance,
            crisis_intensity=0.0,
            legitimacy=1.0,
            external_threat=0.0,
        )
        # With zero crisis, full legitimacy, zero threat, deltas are all ~0
        total_shift = (
            abs(new_balance.liberal_technocratic - balance.liberal_technocratic)
            + abs(new_balance.revanchist_fascist - balance.revanchist_fascist)
            + abs(new_balance.institutionalist_bonapartist - balance.institutionalist_bonapartist)
        )
        assert total_shift < 0.01


class TestNormalization:
    """Weights should always sum to 1.0 after update."""

    @pytest.mark.math
    def test_weights_sum_to_one(self) -> None:
        """Updated weights should sum to 1.0."""
        balance = make_balance()
        new_balance, _ = update_internal_balance(
            balance,
            crisis_intensity=0.5,
            legitimacy=0.3,
            external_threat=0.5,
        )
        total = (
            new_balance.liberal_technocratic
            + new_balance.revanchist_fascist
            + new_balance.institutionalist_bonapartist
        )
        assert abs(total - 1.0) < 0.01

    @pytest.mark.math
    def test_weights_clamped_positive(self) -> None:
        """No weight should go below 0.0."""
        # Start with very low liberal, then erode legitimacy
        balance = make_balance(
            liberal_technocratic=0.01,
            revanchist_fascist=0.49,
            institutionalist_bonapartist=0.50,
        )
        new_balance, _ = update_internal_balance(
            balance,
            crisis_intensity=1.0,
            legitimacy=0.0,
            external_threat=1.0,
        )
        assert new_balance.liberal_technocratic >= 0.0
        assert new_balance.revanchist_fascist >= 0.0
        assert new_balance.institutionalist_bonapartist >= 0.0

    @pytest.mark.math
    def test_contestation_range(self) -> None:
        """Contestation should be in [0, 1]."""
        balance = make_balance()
        new_balance, _ = update_internal_balance(
            balance,
            crisis_intensity=0.5,
            legitimacy=0.5,
            external_threat=0.5,
        )
        assert 0.0 <= new_balance.internal_contestation <= 1.0


class TestAlphaSmoothing:
    """Alpha parameter controls rate of change."""

    @pytest.mark.math
    def test_higher_alpha_faster_shift(self) -> None:
        """Higher alpha should produce larger shifts."""
        balance = make_balance()
        _, _ = update_internal_balance(
            balance,
            crisis_intensity=0.8,
            legitimacy=0.5,
            external_threat=0.0,
            alpha=0.01,
        )
        new_slow, _ = update_internal_balance(
            balance,
            crisis_intensity=0.8,
            legitimacy=0.5,
            external_threat=0.0,
            alpha=0.01,
        )
        new_fast, _ = update_internal_balance(
            balance,
            crisis_intensity=0.8,
            legitimacy=0.5,
            external_threat=0.0,
            alpha=0.2,
        )
        shift_slow = abs(new_slow.revanchist_fascist - balance.revanchist_fascist)
        shift_fast = abs(new_fast.revanchist_fascist - balance.revanchist_fascist)
        assert shift_fast > shift_slow


class TestFactionShiftEvent:
    """Events generated when hegemonic fraction changes."""

    @pytest.mark.math
    def test_faction_shift_event_generated(self) -> None:
        """Changing hegemonic fraction should produce FactionShiftEvent."""
        # Start with liberal hegemony, push revanchist hard
        balance = make_balance(
            liberal_technocratic=0.35,
            revanchist_fascist=0.34,
            institutionalist_bonapartist=0.31,
        )
        new_balance, events = update_internal_balance(
            balance,
            crisis_intensity=1.0,
            legitimacy=0.0,
            external_threat=0.0,
            alpha=0.5,  # Large alpha to force shift
        )
        faction_events = [e for e in events if isinstance(e, FactionShiftEvent)]
        if new_balance.hegemonic_fraction != balance.hegemonic_fraction:
            assert len(faction_events) == 1
            assert faction_events[0].old_fraction == RulingClassFraction.LIBERAL_TECHNOCRATIC

    @pytest.mark.math
    def test_no_event_when_fraction_unchanged(self) -> None:
        """No FactionShiftEvent if hegemonic fraction stays same."""
        balance = make_balance(
            liberal_technocratic=0.7,
            revanchist_fascist=0.2,
            institutionalist_bonapartist=0.1,
        )
        _, events = update_internal_balance(
            balance,
            crisis_intensity=0.1,
            legitimacy=0.9,
            external_threat=0.0,
            alpha=0.01,
        )
        faction_events = [e for e in events if isinstance(e, FactionShiftEvent)]
        assert len(faction_events) == 0


class TestBonapartistMode:
    """SC-005: Bonapartist mode triggers when conditions met."""

    @pytest.mark.math
    def test_bonapartist_mode_event(self) -> None:
        """High bonapartist weight with others below threshold should trigger event."""
        # Start already near Bonapartist dominance
        balance = make_balance(
            liberal_technocratic=0.15,
            revanchist_fascist=0.15,
            institutionalist_bonapartist=0.70,
        )
        _, events = update_internal_balance(
            balance,
            crisis_intensity=0.0,
            legitimacy=1.0,
            external_threat=0.8,
        )
        bonapartist_events = [e for e in events if isinstance(e, BonapartistModeEvent)]
        assert len(bonapartist_events) == 1
        assert bonapartist_events[0].bonapartist_weight > 0.4

    @pytest.mark.math
    def test_no_bonapartist_mode_when_others_high(self) -> None:
        """Bonapartist mode should NOT trigger if other fractions above exclusion threshold."""
        balance = make_balance(
            liberal_technocratic=0.30,
            revanchist_fascist=0.30,
            institutionalist_bonapartist=0.40,
        )
        _, events = update_internal_balance(
            balance,
            crisis_intensity=0.0,
            legitimacy=1.0,
            external_threat=0.0,
        )
        bonapartist_events = [e for e in events if isinstance(e, BonapartistModeEvent)]
        assert len(bonapartist_events) == 0


class TestReturnTypes:
    """Return type validation."""

    def test_returns_balance_and_events(self) -> None:
        """Function should return tuple of (balance, events)."""
        balance = make_balance()
        result = update_internal_balance(
            balance,
            crisis_intensity=0.5,
            legitimacy=0.5,
            external_threat=0.5,
        )
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], InternalBalanceOfForces)
        assert isinstance(result[1], list)

    def test_events_have_institution_id(self) -> None:
        """Events should carry the provided institution_id."""
        balance = make_balance(
            liberal_technocratic=0.15,
            revanchist_fascist=0.15,
            institutionalist_bonapartist=0.70,
        )
        _, events = update_internal_balance(
            balance,
            crisis_intensity=0.0,
            legitimacy=1.0,
            external_threat=0.8,
            institution_id="doj",
        )
        for event in events:
            assert event.institution_id == "doj"
