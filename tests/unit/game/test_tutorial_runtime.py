"""Unit tests for the T6 tutorial's live completion-predicate evaluator
(Program v1.0.0 T6, Unit U4).

Exercises :class:`~babylon.game.tutorial_runtime.TutorialRuntimeProgress`
against fake ``_TickSource``/``_PausedDriverSource`` doubles — no real
engine, Postgres, or Textual app required (this evaluator's own contract is
"read three plain signals," never anything heavier).
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from babylon.game.tutorial import (
    EventAcked,
    OnPage,
    PausePending,
    TickAtLeast,
    TutorialStep,
    VerbIssued,
)
from babylon.game.tutorial_runtime import TutorialRuntimeProgress

pytestmark = [pytest.mark.unit]


def _step(step_id: str, completion: object) -> TutorialStep:
    return TutorialStep(
        id=step_id,
        given="g",
        when="w",
        then="t",
        anchor="page:x",
        completion=completion,  # type: ignore[arg-type]
    )


@dataclass
class _FakeCampaign:
    tick: int = 0


@dataclass
class _FakeDriver:
    awaiting_ack: bool = False


class TestOnPage:
    def test_true_when_current_subject_matches(self) -> None:
        steps = (_step("s0", OnPage(subject="county/26163")),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=None,
            current_subject=lambda: "county/26163",
        )
        assert evaluator.is_step_complete(0) is True

    def test_false_when_current_subject_differs(self) -> None:
        steps = (_step("s0", OnPage(subject="county/26163")),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=None,
            current_subject=lambda: "economy/USA",
        )
        assert evaluator.is_step_complete(0) is False

    def test_false_when_current_subject_is_none(self) -> None:
        steps = (_step("s0", OnPage(subject="county/26163")),)
        evaluator = TutorialRuntimeProgress(
            steps=steps, campaign=_FakeCampaign(), driver=None, current_subject=lambda: None
        )
        assert evaluator.is_step_complete(0) is False


class TestTickAtLeast:
    def test_true_once_tick_reached(self) -> None:
        steps = (_step("s0", TickAtLeast(tick=3)),)
        evaluator = TutorialRuntimeProgress(
            steps=steps, campaign=_FakeCampaign(tick=3), driver=None, current_subject=lambda: None
        )
        assert evaluator.is_step_complete(0) is True

    def test_true_past_the_target_tick(self) -> None:
        steps = (_step("s0", TickAtLeast(tick=3)),)
        evaluator = TutorialRuntimeProgress(
            steps=steps, campaign=_FakeCampaign(tick=9), driver=None, current_subject=lambda: None
        )
        assert evaluator.is_step_complete(0) is True

    def test_false_before_the_target_tick(self) -> None:
        steps = (_step("s0", TickAtLeast(tick=3)),)
        evaluator = TutorialRuntimeProgress(
            steps=steps, campaign=_FakeCampaign(tick=2), driver=None, current_subject=lambda: None
        )
        assert evaluator.is_step_complete(0) is False


class TestPausePending:
    def test_true_when_driver_awaiting_ack(self) -> None:
        steps = (_step("s0", PausePending()),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=_FakeDriver(awaiting_ack=True),
            current_subject=lambda: None,
        )
        assert evaluator.is_step_complete(0) is True

    def test_false_when_driver_not_awaiting_ack(self) -> None:
        steps = (_step("s0", PausePending()),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=_FakeDriver(awaiting_ack=False),
            current_subject=lambda: None,
        )
        assert evaluator.is_step_complete(0) is False

    def test_false_with_no_driver_at_all(self) -> None:
        steps = (_step("s0", PausePending()),)
        evaluator = TutorialRuntimeProgress(
            steps=steps, campaign=_FakeCampaign(), driver=None, current_subject=lambda: None
        )
        assert evaluator.is_step_complete(0) is False


class TestEventAcked:
    def test_true_once_driver_no_longer_awaiting_ack(self) -> None:
        steps = (_step("s0", EventAcked()),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=_FakeDriver(awaiting_ack=False),
            current_subject=lambda: None,
        )
        assert evaluator.is_step_complete(0) is True

    def test_false_while_still_awaiting_ack(self) -> None:
        steps = (_step("s0", EventAcked()),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=_FakeDriver(awaiting_ack=True),
            current_subject=lambda: None,
        )
        assert evaluator.is_step_complete(0) is False

    def test_false_with_no_driver_at_all(self) -> None:
        steps = (_step("s0", EventAcked()),)
        evaluator = TutorialRuntimeProgress(
            steps=steps, campaign=_FakeCampaign(), driver=None, current_subject=lambda: None
        )
        assert evaluator.is_step_complete(0) is False


class TestVerbIssuedIsHonestlyUnsupported:
    def test_raises_loudly_rather_than_silently_returning_false(self) -> None:
        """Module docstring: this evaluator is never handed a VerbIssued
        step in production (the composition root slices those off), but if
        it ever IS, it must fail loudly, never rot into a silent 'never
        completes' — Constitution III.11."""
        steps = (_step("s0", VerbIssued(verb="new_campaign")),)
        evaluator = TutorialRuntimeProgress(
            steps=steps, campaign=_FakeCampaign(), driver=None, current_subject=lambda: None
        )
        with pytest.raises(AssertionError, match="VerbIssued"):
            evaluator.is_step_complete(0)


class TestIndexBounds:
    def test_out_of_range_index_is_honestly_false_not_a_crash(self) -> None:
        steps = (_step("s0", TickAtLeast(tick=1)),)
        evaluator = TutorialRuntimeProgress(
            steps=steps, campaign=_FakeCampaign(tick=5), driver=None, current_subject=lambda: None
        )
        assert evaluator.is_step_complete(1) is False
        assert evaluator.is_step_complete(-1) is False
