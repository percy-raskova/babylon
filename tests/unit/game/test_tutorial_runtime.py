"""Unit tests for the T6 tutorial's live completion-predicate evaluator
(Program v1.0.0 T6, Unit U4; extended by Program 24 P8, "the tutorial learns
the shell"; ``OnPage`` tightened by unit "navigate-pane-couple",
shell-interconnect).

Exercises :class:`~babylon.game.tutorial_runtime.TutorialRuntimeProgress`
against fake ``_TickSource``/``_PausedDriverSource`` doubles — no real
engine, Postgres, or Textual app required (this evaluator's own contract is
"read five plain signals," never anything heavier). Every construction below
passes harmless ``current_pane``/``is_pinned`` stand-ins unless the test is
itself exercising :class:`~babylon.game.tutorial.OnPage`/
:class:`~babylon.game.tutorial.PaneShowing`/
:class:`~babylon.game.tutorial.PinnedInWatchlist` (``TestOnPage``/
``TestPaneShowing``/``TestPinnedInWatchlist`` below), mirroring every OTHER
predicate-kind test class's own "irrelevant signals are harmlessly wired,
never omitted" shape.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pytest

from babylon.game.tutorial import (
    WAYNE_OPENING_ARC,
    EventAcked,
    OnPage,
    PaneShowing,
    PausePending,
    PinnedInWatchlist,
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
        patches="Patches keeps us company on this synthetic step.",
    )


@dataclass
class _FakeCampaign:
    tick: int = 0


@dataclass
class _FakeDriver:
    awaiting_ack: bool = False


class TestOnPage:
    """Unit "navigate-pane-couple" (shell-interconnect): ``OnPage`` requires
    BOTH the matching subject AND the Wiki pane actually showing — subject
    match alone let a step "complete" while the player was looking at a
    different pane entirely (the "P8 dodge": ``nav.current`` changed, but
    ``#dossier`` was invisible)."""

    def test_true_when_current_subject_matches_and_wiki_pane_is_showing(self) -> None:
        steps = (_step("s0", OnPage(subject="county/26163")),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=None,
            current_subject=lambda: "county/26163",
            current_pane=lambda: "wiki",
            is_pinned=lambda _subject: False,
        )
        assert evaluator.is_step_complete(0) is True

    def test_false_when_subject_matches_but_a_different_pane_is_showing(self) -> None:
        """The tightened conjunct: a matching subject is not enough on its
        own — the player must actually be able to SEE ``#dossier``, which
        only the Wiki pane renders."""
        steps = (_step("s0", OnPage(subject="county/26163")),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=None,
            current_subject=lambda: "county/26163",
            current_pane=lambda: "dashboard",
            is_pinned=lambda _subject: False,
        )
        assert evaluator.is_step_complete(0) is False

    def test_flips_true_once_the_live_pane_actually_switches_to_wiki(self) -> None:
        """The mutate-to-verify shape (mirrors ``TestPaneShowing``'s own
        below): the SAME evaluator instance, over a mutable pane holder —
        the subject already matches throughout, so the pane flip alone is
        what turns this true."""
        steps = (_step("s0", OnPage(subject="county/26163")),)
        current: dict[str, str | None] = {"pane": "map"}
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=None,
            current_subject=lambda: "county/26163",
            current_pane=lambda: current["pane"],
            is_pinned=lambda _subject: False,
        )
        assert evaluator.is_step_complete(0) is False
        current["pane"] = "wiki"
        assert evaluator.is_step_complete(0) is True

    def test_false_when_current_subject_differs(self) -> None:
        steps = (_step("s0", OnPage(subject="county/26163")),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=None,
            current_subject=lambda: "economy/USA",
            current_pane=lambda: None,
            is_pinned=lambda _subject: False,
        )
        assert evaluator.is_step_complete(0) is False

    def test_false_when_current_subject_is_none(self) -> None:
        steps = (_step("s0", OnPage(subject="county/26163")),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=None,
            current_subject=lambda: None,
            current_pane=lambda: None,
            is_pinned=lambda _subject: False,
        )
        assert evaluator.is_step_complete(0) is False


class TestTickAtLeast:
    def test_true_once_tick_reached(self) -> None:
        steps = (_step("s0", TickAtLeast(tick=3)),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(tick=3),
            driver=None,
            current_subject=lambda: None,
            current_pane=lambda: None,
            is_pinned=lambda _subject: False,
        )
        assert evaluator.is_step_complete(0) is True

    def test_true_past_the_target_tick(self) -> None:
        steps = (_step("s0", TickAtLeast(tick=3)),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(tick=9),
            driver=None,
            current_subject=lambda: None,
            current_pane=lambda: None,
            is_pinned=lambda _subject: False,
        )
        assert evaluator.is_step_complete(0) is True

    def test_false_before_the_target_tick(self) -> None:
        steps = (_step("s0", TickAtLeast(tick=3)),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(tick=2),
            driver=None,
            current_subject=lambda: None,
            current_pane=lambda: None,
            is_pinned=lambda _subject: False,
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
            current_pane=lambda: None,
            is_pinned=lambda _subject: False,
        )
        assert evaluator.is_step_complete(0) is True

    def test_false_when_driver_not_awaiting_ack(self) -> None:
        steps = (_step("s0", PausePending()),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=_FakeDriver(awaiting_ack=False),
            current_subject=lambda: None,
            current_pane=lambda: None,
            is_pinned=lambda _subject: False,
        )
        assert evaluator.is_step_complete(0) is False

    def test_false_with_no_driver_at_all(self) -> None:
        steps = (_step("s0", PausePending()),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=None,
            current_subject=lambda: None,
            current_pane=lambda: None,
            is_pinned=lambda _subject: False,
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
            current_pane=lambda: None,
            is_pinned=lambda _subject: False,
        )
        assert evaluator.is_step_complete(0) is True

    def test_false_while_still_awaiting_ack(self) -> None:
        steps = (_step("s0", EventAcked()),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=_FakeDriver(awaiting_ack=True),
            current_subject=lambda: None,
            current_pane=lambda: None,
            is_pinned=lambda _subject: False,
        )
        assert evaluator.is_step_complete(0) is False

    def test_false_with_no_driver_at_all(self) -> None:
        steps = (_step("s0", EventAcked()),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=None,
            current_subject=lambda: None,
            current_pane=lambda: None,
            is_pinned=lambda _subject: False,
        )
        assert evaluator.is_step_complete(0) is False


class TestPaneShowing:
    """Program 24 P8: ``PaneShowing`` reads the live ``current_pane`` seam —
    proven here by MUTATING the fake pane query between two evaluations of
    the SAME evaluator (the "assert FAILS if the pane was not switched" shape
    the unit's own mandate names), not merely by constructing two separate
    evaluators with different fixed answers.
    """

    def test_true_when_current_pane_matches(self) -> None:
        steps = (_step("s0", PaneShowing(pane="map")),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=None,
            current_subject=lambda: None,
            current_pane=lambda: "map",
            is_pinned=lambda _subject: False,
        )
        assert evaluator.is_step_complete(0) is True

    def test_false_when_current_pane_differs(self) -> None:
        steps = (_step("s0", PaneShowing(pane="map")),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=None,
            current_subject=lambda: None,
            current_pane=lambda: "wiki",
            is_pinned=lambda _subject: False,
        )
        assert evaluator.is_step_complete(0) is False

    def test_false_when_current_pane_is_none(self) -> None:
        steps = (_step("s0", PaneShowing(pane="map")),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=None,
            current_subject=lambda: None,
            current_pane=lambda: None,
            is_pinned=lambda _subject: False,
        )
        assert evaluator.is_step_complete(0) is False

    def test_flips_true_once_the_live_pane_actually_switches(self) -> None:
        """The mutate-to-verify case: the SAME evaluator instance, over a
        mutable pane holder — the predicate is honestly re-read live, not
        cached from construction time."""
        steps = (_step("s0", PaneShowing(pane="topology")),)
        current: dict[str, str | None] = {"pane": "wiki"}
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=None,
            current_subject=lambda: None,
            current_pane=lambda: current["pane"],
            is_pinned=lambda _subject: False,
        )
        assert evaluator.is_step_complete(0) is False
        current["pane"] = "topology"
        assert evaluator.is_step_complete(0) is True


class TestPinnedInWatchlist:
    """Program 24 P8: ``PinnedInWatchlist`` reads the live ``is_pinned``
    seam — same mutate-to-verify shape as ``TestPaneShowing`` above."""

    def test_true_when_subject_is_pinned(self) -> None:
        steps = (_step("s0", PinnedInWatchlist(subject="county/26163")),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=None,
            current_subject=lambda: None,
            current_pane=lambda: None,
            is_pinned=lambda subject: subject == "county/26163",
        )
        assert evaluator.is_step_complete(0) is True

    def test_false_when_subject_is_not_pinned(self) -> None:
        steps = (_step("s0", PinnedInWatchlist(subject="county/26163")),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=None,
            current_subject=lambda: None,
            current_pane=lambda: None,
            is_pinned=lambda _subject: False,
        )
        assert evaluator.is_step_complete(0) is False

    def test_flips_true_once_the_live_pin_actually_lands(self) -> None:
        """The mutate-to-verify case: the SAME evaluator instance, over a
        mutable pin set — the predicate is honestly re-read live, not cached
        from construction time."""
        steps = (_step("s0", PinnedInWatchlist(subject="county/26163")),)
        pinned: set[str] = set()
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=None,
            current_subject=lambda: None,
            current_pane=lambda: None,
            is_pinned=lambda subject: subject in pinned,
        )
        assert evaluator.is_step_complete(0) is False
        pinned.add("county/26163")
        assert evaluator.is_step_complete(0) is True


class TestVerbIssuedIsHonestlyUnsupported:
    def test_raises_loudly_rather_than_silently_returning_false(self) -> None:
        """Module docstring: this evaluator is never handed a VerbIssued
        step in production (the composition root slices those off), but if
        it ever IS, it must fail loudly, never rot into a silent 'never
        completes' — Constitution III.11."""
        steps = (_step("s0", VerbIssued(verb="new_campaign")),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=None,
            current_subject=lambda: None,
            current_pane=lambda: None,
            is_pinned=lambda _subject: False,
        )
        with pytest.raises(AssertionError, match="VerbIssued"):
            evaluator.is_step_complete(0)


class TestIndexBounds:
    def test_out_of_range_index_is_honestly_false_not_a_crash(self) -> None:
        steps = (_step("s0", TickAtLeast(tick=1)),)
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(tick=5),
            driver=None,
            current_subject=lambda: None,
            current_pane=lambda: None,
            is_pinned=lambda _subject: False,
        )
        assert evaluator.is_step_complete(1) is False
        assert evaluator.is_step_complete(-1) is False


# --------------------------------------------------------------------------- #
# The defect fix (M3 seam contract §0): the VerbIssued live-crash, pinned.   #
# --------------------------------------------------------------------------- #


class TestVerbIssuedWiredIsDispatchProof:
    """The defect fix (M3 contract §0): once ``was_verb_issued`` is wired,
    a ``VerbIssued`` step no longer raises — it mirrors the caller's own
    dispatch-proof callable, exactly ``VerbIssued``'s documented meaning
    ("proves dispatch, never the outcome"). The default (``None``, omitted
    below every OTHER test in this module) keeps the loud raise unchanged —
    this class is additive, not a replacement for
    ``TestVerbIssuedIsHonestlyUnsupported`` above."""

    def test_false_before_and_true_after_the_verb_is_recorded(self) -> None:
        steps = (_step("s0", VerbIssued(verb="aid")),)
        issued: set[str] = set()
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=None,
            current_subject=lambda: None,
            current_pane=lambda: None,
            is_pinned=lambda _subject: False,
            was_verb_issued=lambda verb: verb in issued,
        )
        assert evaluator.is_step_complete(0) is False
        issued.add("aid")
        assert evaluator.is_step_complete(0) is True

    def test_reads_the_predicates_own_verb_name_not_a_different_one(self) -> None:
        steps = (_step("s0", VerbIssued(verb="aid")),)
        issued = {"peek_wikilink"}  # a DIFFERENT verb recorded — must not leak.
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(),
            driver=None,
            current_subject=lambda: None,
            current_pane=lambda: None,
            is_pinned=lambda _subject: False,
            was_verb_issued=lambda verb: verb in issued,
        )
        assert evaluator.is_step_complete(0) is False


class TestTheRealSlicedArcVerbIssuedLiveCrash:
    """THE DEFECT PIN. Verified twice independently (firsthand + scout, per
    the contract): the authored arc's mid-slice ``VerbIssued`` beats
    (``issue_aid_on_the_proletariat``, ``peek_a_wikilink_with_the_keyboard``)
    sit INSIDE the ``steps[2:]`` slice ``babylon.cli.play.
    _tutorial_progress_factory`` hands this evaluator — built here EXACTLY
    that way (the real slice, no ``was_verb_issued``) — whose
    ``is_step_complete`` raised ``AssertionError`` on any ``VerbIssued``
    predicate before this fix, crashing ``TutorialOverlay.check_progress``'s
    multi-advance loop live. Pinned as a durable regression, then proven
    green once ``was_verb_issued`` is wired (the fix's own other half)."""

    @staticmethod
    def _issue_aid_index() -> int:
        steps = WAYNE_OPENING_ARC.steps[2:]
        return next(i for i, step in enumerate(steps) if step.id == "issue_aid_on_the_proletariat")

    def test_the_slice_arithmetic_lands_issue_aid_at_index_19(self) -> None:
        # Pins the arithmetic itself: steps[2:] drops boot_into_lobby/
        # begin_the_operation, so issue_aid_on_the_proletariat's own
        # original index 21 becomes 19 in the sliced space.
        assert self._issue_aid_index() == 19

    def test_red_the_real_sliced_arc_crashes_with_no_was_verb_issued_wired(self) -> None:
        steps = WAYNE_OPENING_ARC.steps[2:]
        issue_aid_index = self._issue_aid_index()
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(tick=1),
            driver=_FakeDriver(awaiting_ack=False),
            current_subject=lambda: "social_class/C001",
            current_pane=lambda: "wiki",
            is_pinned=lambda subject: subject == "social_class/C001",
        )

        with pytest.raises(AssertionError, match="issue_aid_on_the_proletariat"):
            evaluator.is_step_complete(issue_aid_index)

    def test_green_with_was_verb_issued_wired_false_before_true_after(self) -> None:
        steps = WAYNE_OPENING_ARC.steps[2:]
        issue_aid_index = self._issue_aid_index()
        issued: set[str] = set()
        evaluator = TutorialRuntimeProgress(
            steps=steps,
            campaign=_FakeCampaign(tick=1),
            driver=_FakeDriver(awaiting_ack=False),
            current_subject=lambda: "social_class/C001",
            current_pane=lambda: "wiki",
            is_pinned=lambda subject: subject == "social_class/C001",
            was_verb_issued=lambda verb: verb in issued,
        )

        assert evaluator.is_step_complete(issue_aid_index) is False

        issued.add("aid")

        assert evaluator.is_step_complete(issue_aid_index) is True


class TestWaynePatchesLinesNeverNameAKey:
    """Cheap guard for the §0 keyless rule: Patches owns the why/
    encouragement, the *when* owns the key — a step's ``patches`` line must
    never itself name a key (the Rust/Textual clients bind differently, so
    a key literal in Patches' own voice would lie in at least one of them)."""

    def test_every_wayne_step_has_a_non_empty_patches_line(self) -> None:
        for step in WAYNE_OPENING_ARC.steps:  # loop bound: len(steps) == 24
            assert step.patches.strip() != ""

    def test_no_patches_line_names_a_key_by_fragment_or_standalone_word(self) -> None:
        """Widened token list (review fix pass, R19) — the original
        two-fragment check (``"press '"`` substring + the nine F-keys)
        missed named NAVIGATION keys spelled out in prose (e.g. "press
        Enter"). Every Patches line is scanned for the ``"press '"``
        fragment, each F-key substring, AND
        ``enter``/``tab``/``esc``/``escape``/``ctrl``/``shift`` as
        STANDALONE words (``\\b``-bounded, case-insensitive) — Patches'
        own prose is free to use ordinary English words that happen to
        share a spelling, so the standalone-word boundary (never a bare
        substring match) is what keeps this a real signal rather than a
        false-positive risk; verified none of Wayne's 24 lines use any of
        these words as prose today."""
        f_keys = tuple(f"F{n}" for n in range(1, 10))
        named_keys = ("enter", "tab", "esc", "escape", "ctrl", "shift")
        for step in WAYNE_OPENING_ARC.steps:  # loop bound: len(steps) == 24
            assert "press '" not in step.patches, (
                f"{step.id}: Patches line names a key by quoted fragment"
            )
            for f_key in f_keys:  # loop bound: len(f_keys) == 9
                assert f_key not in step.patches, f"{step.id}: Patches line names {f_key}"
            for named_key in named_keys:  # loop bound: len(named_keys) == 6
                assert not re.search(rf"\b{named_key}\b", step.patches, re.IGNORECASE), (
                    f"{step.id}: Patches line names the {named_key!r} key by name"
                )
