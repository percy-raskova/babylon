"""The T6 tutorial's completion-predicate evaluator (Program v1.0.0 T6, Unit U4).

Fulfills :class:`~babylon.tui.tutorial_overlay.TutorialProgress` for real —
the composition root's concrete answer to "is this step complete right now?",
built over the SAME closed :data:`~babylon.game.tutorial.CompletionPredicate`
vocabulary the headless Pilot executor (Unit U2, :mod:`tests.unit.tui.
test_tutorial_pilot`) already asserts against, so the player-facing overlay
and CI never diverge on what "complete" means for a given step.

**The ``was_verb_issued`` seam (M3 defect fix — the raster-cutover
``VerbIssued`` live crash, ``docs/superpowers/specs/
2026-07-27-m3-tutorial-contracts.md`` §0).** The authored arc
(:data:`~babylon.game.tutorial.WAYNE_OPENING_ARC`) carries THREE
``VerbIssued``-completion beats — ``boot_into_lobby``
(``VerbIssued(verb="new_campaign")``), ``issue_aid_on_the_proletariat``
(``VerbIssued(verb="aid")``), and ``peek_a_wikilink_with_the_keyboard``
(``VerbIssued(verb="peek_wikilink")``); ``begin_the_operation`` is an
:class:`~babylon.game.tutorial.OnPage` step, NOT a ``VerbIssued`` one (a
fix-pass correction over this docstring's own earlier, stale "two
``VerbIssued`` beats" count). The first of the three sits BEFORE any
campaign exists at all — there is genuinely nothing to read a page/tick/
pane/pin FROM yet — which is why :mod:`babylon.cli.play`'s own composition
root still only ever hands this evaluator the arc's SLICE starting AFTER
``boot_into_lobby`` (``WAYNE_OPENING_ARC.steps[2:]``, skipping
``begin_the_operation`` too): that first beat stays necessarily true by
construction, never evaluated here at all.

The other two, though, sit INSIDE that same slice — and before this fix
pass, :meth:`TutorialRuntimeProgress.is_step_complete` raised
UNCONDITIONALLY on any ``VerbIssued`` step, on the (once-true, now
outdated) theory that "this evaluator ... has no license to instrument
production action dispatch just to observe whether a keypress fired." That
theory held only until something wired dispatch-proof recording; once the
Textual shell (:class:`~babylon.tui.app.ArchiveApp`'s own ``_verbs_issued``
set, recording on ``action_issue_verb``/``action_peek_wikilink`` dispatch)
and the Rust host (:class:`~babylon.tui.host.RustClientHost`'s own
``verb_log`` union its per-poll ``chrome_verbs`` report) both did, the old
unconditional raise became a real, verified LIVE CRASH: the multi-advance
poll loop in :meth:`~babylon.tui.tutorial_overlay.TutorialOverlay.
check_progress` reaches ``issue_aid_on_the_proletariat`` the instant the
player opens the watchlist's pinned row (the immediately preceding step),
and used to raise ``AssertionError`` right there — no test caught it,
because the overlay's own tests use bool-returning fakes (the fixture-shape
failure class CLAUDE.md's own vocabulary-sentinel section documents).

The fix: :meth:`TutorialRuntimeProgress.__init__` now takes a keyword-only
``was_verb_issued: Callable[[str], bool] | None = None`` — a plain
predicate answering "has ``verb`` been dispatched at least once this
session?", never an instrumentation hook this module installs itself.
Dispatch on a ``VerbIssued`` predicate: ``was_verb_issued is None`` -> the
ORIGINAL loud raise, completely unchanged (the contract for any
composition that still hands this evaluator a ``VerbIssued`` step with no
wired seam — never a silent ``False`` masquerading as "not yet complete"
forever); wired -> ``return self._was_verb_issued(predicate.verb)`` —
exactly ``VerbIssued``'s own documented dispatch-proof meaning, resolved
with zero instrumentation of production dispatch.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol, runtime_checkable

from babylon.game.tutorial import (
    EventAcked,
    OnPage,
    PaneShowing,
    PausePending,
    PinnedInWatchlist,
    TickAtLeast,
    TutorialStep,
    VerbIssued,
)

__all__ = ["TutorialRuntimeProgress"]


@runtime_checkable
class _TickSource(Protocol):
    """Structural shape this module needs from the live campaign: only its
    committed tick (:class:`~babylon.tui.contract.CampaignHandle` satisfies this)."""

    @property
    def tick(self) -> int: ...


@runtime_checkable
class _PausedDriverSource(Protocol):
    """Structural shape this module needs from the paced driver: only
    ``awaiting_ack`` (:class:`~babylon.tui.contract.PacedDriverHandle` satisfies
    this)."""

    @property
    def awaiting_ack(self) -> bool: ...


class TutorialRuntimeProgress:
    """The live evaluator: closed dispatch over :data:`~babylon.game.
    tutorial.CompletionPredicate`, reading the campaign's tick, the paced
    driver's ``awaiting_ack``, the nav shell's current subject, the hybrid
    shell's current pane, the watchlist's pinned subjects (the last two,
    Program 24 P8, "the tutorial learns the shell"), and — M3 — whether a
    named verb has been dispatched at least once this session.

    :param steps: the exact step sequence :class:`~babylon.tui.
        tutorial_overlay.TutorialOverlay` was ALSO constructed with — indices
        must line up between the two (the composition root's job to keep
        them so; see ``babylon.cli.play``'s own wiring).
    :param campaign: the live campaign (only its ``tick`` is read).
    :param driver: the live paced driver, or ``None`` when no
        ``driver_factory`` was wired — ``PausePending``/``EventAcked`` then
        never hold (there is no driver to have ever paused).
    :param current_subject: reads the nav shell's CURRENT subject at call
        time — a plain callable rather than a nav-shell import, so this
        module never needs to know :class:`~babylon.tui.nav.NavShell` exists.
    :param current_pane: reads the hybrid shell's ``ContentSwitcher``
        ``.current`` pane id at call time (Program 24 P8) — a plain callable
        rather than a Textual import, mirroring :attr:`current_subject`'s own
        seam-crossing idiom. Also consulted by :class:`~babylon.game.tutorial.
        OnPage` itself (unit "navigate-pane-couple", shell-interconnect): a
        subject match alone cannot prove the player actually SAW the page —
        only ``current_pane() == "wiki"`` does, since that is where
        ``#dossier`` renders.
    :param is_pinned: reads whether a given subject id currently holds a pin
        on the watchlist at call time (Program 24 P8), mirroring
        :meth:`~babylon.tui.watchlist.WatchlistState.is_pinned` — a plain
        callable rather than a ``babylon.tui.watchlist`` import, same reason.
    :param was_verb_issued: the M3 defect-fix seam (module docstring) — a
        plain callable answering whether ``verb`` has been dispatched at
        least once this session, fulfilled for real by
        :class:`~babylon.tui.host.RustClientHost`'s own ``verb_log`` union
        its latest poll's ``chrome_verbs`` (the Textual shell's
        ``_verbs_issued`` set filled this role until the M7 cutover).
        ``None`` (the default) preserves the ORIGINAL behavior exactly: any
        ``VerbIssued`` step raises loudly rather than being silently
        unresolvable.
    """

    def __init__(
        self,
        *,
        steps: Sequence[TutorialStep],
        campaign: _TickSource,
        driver: _PausedDriverSource | None,
        current_subject: Callable[[], str | None],
        current_pane: Callable[[], str | None],
        is_pinned: Callable[[str], bool],
        was_verb_issued: Callable[[str], bool] | None = None,
    ) -> None:
        self._steps: tuple[TutorialStep, ...] = tuple(steps)
        self._campaign = campaign
        self._driver = driver
        self._current_subject = current_subject
        self._current_pane = current_pane
        self._is_pinned = is_pinned
        self._was_verb_issued = was_verb_issued

    def is_step_complete(self, step_index: int) -> bool:
        """See :meth:`~babylon.tui.tutorial_overlay.TutorialProgress.is_step_complete`.

        :raises AssertionError: ``step_index`` names a ``VerbIssued``-completion
            step AND no ``was_verb_issued`` callable was wired (module
            docstring's M3 defect fix — the ORIGINAL, unchanged raise), or
            the completion is outside the closed vocabulary entirely —
            never silently ``False``.
        """
        if not 0 <= step_index < len(self._steps):
            return False
        predicate = self._steps[step_index].completion
        if isinstance(predicate, OnPage):
            # Unit "navigate-pane-couple" (shell-interconnect): subject-match
            # alone let a step "complete" even while the player was looking
            # at a different pane entirely — nav.current changed, but the
            # dossier that changed was invisible. The Wiki pane is where
            # `#dossier` actually renders (see WikiView), so an OnPage step
            # is only truly satisfied once the player can SEE it there.
            return self._current_subject() == predicate.subject and self._current_pane() == "wiki"
        if isinstance(predicate, TickAtLeast):
            return self._campaign.tick >= predicate.tick
        if isinstance(predicate, PausePending):
            return self._driver is not None and self._driver.awaiting_ack
        if isinstance(predicate, EventAcked):
            return self._driver is not None and not self._driver.awaiting_ack
        if isinstance(predicate, PaneShowing):
            return self._current_pane() == predicate.pane
        if isinstance(predicate, PinnedInWatchlist):
            return self._is_pinned(predicate.subject)
        if isinstance(predicate, VerbIssued):
            # M3 defect fix (module docstring): wired -> dispatch-proof
            # resolution, exactly VerbIssued's own documented meaning;
            # unwired -> the ORIGINAL loud raise, byte-for-byte unchanged.
            if self._was_verb_issued is not None:
                return self._was_verb_issued(predicate.verb)
            msg = (
                f"TutorialRuntimeProgress: step {self._steps[step_index].id!r}'s "
                f"VerbIssued({predicate.verb!r}) completion is not observable from "
                "inside the live campaign shell (see module docstring) — the "
                "composition root must never hand this evaluator a VerbIssued step"
            )
            raise AssertionError(msg)
        msg = f"TutorialRuntimeProgress: unrecognized completion predicate kind {predicate!r}"
        raise AssertionError(msg)
