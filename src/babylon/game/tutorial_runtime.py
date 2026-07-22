"""The T6 tutorial's completion-predicate evaluator (Program v1.0.0 T6, Unit U4).

Fulfills :class:`~babylon.tui.tutorial_overlay.TutorialProgress` for real —
the composition root's concrete answer to "is this step complete right now?",
built over the SAME closed :data:`~babylon.game.tutorial.CompletionPredicate`
vocabulary the headless Pilot executor (Unit U2, :mod:`tests.unit.tui.
test_tutorial_pilot`) already asserts against, so the player-facing overlay
and CI never diverge on what "complete" means for a given step.

**Never handed a ``VerbIssued``-completion step.** Unlike the Pilot
executor (which can wrap a step's own ``action_<verb>`` in a
``mock.patch.object`` spy — see :func:`tests.unit.tui.test_tutorial_pilot.
_drive_verb_issued`), this evaluator runs inside the REAL, shipped game: it
has no license to instrument production action dispatch just to observe
whether a keypress fired. :meth:`TutorialRuntimeProgress.is_step_complete`
therefore raises loudly (Constitution III.11) if it is ever asked to
evaluate a ``VerbIssued`` step — never a silent ``False`` masquerading as
"not yet complete" forever. This is why :mod:`babylon.cli.play`'s own
composition root only ever hands this evaluator the authored arc's SLICE
starting after its two ``VerbIssued`` beats (``boot_into_lobby``,
``begin_the_operation``) — both already necessarily true by the time the
campaign shell (and this overlay) exist, since reaching the shell requires
having done them.
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
    committed tick (:class:`~babylon.tui.app.CampaignHandle` satisfies this)."""

    @property
    def tick(self) -> int: ...


@runtime_checkable
class _PausedDriverSource(Protocol):
    """Structural shape this module needs from the paced driver: only
    ``awaiting_ack`` (:class:`~babylon.tui.app.PacedDriverHandle` satisfies
    this)."""

    @property
    def awaiting_ack(self) -> bool: ...


class TutorialRuntimeProgress:
    """The live evaluator: closed dispatch over :data:`~babylon.game.
    tutorial.CompletionPredicate`, reading the campaign's tick, the paced
    driver's ``awaiting_ack``, the nav shell's current subject, the hybrid
    shell's current pane, and the watchlist's pinned subjects (the last two,
    Program 24 P8, "the tutorial learns the shell").

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
    ) -> None:
        self._steps: tuple[TutorialStep, ...] = tuple(steps)
        self._campaign = campaign
        self._driver = driver
        self._current_subject = current_subject
        self._current_pane = current_pane
        self._is_pinned = is_pinned

    def is_step_complete(self, step_index: int) -> bool:
        """See :meth:`~babylon.tui.tutorial_overlay.TutorialProgress.is_step_complete`.

        :raises AssertionError: ``step_index`` names a ``VerbIssued``-completion
            step (module docstring), or the completion is outside the closed
            vocabulary entirely — never silently ``False``.
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
            msg = (
                f"TutorialRuntimeProgress: step {self._steps[step_index].id!r}'s "
                f"VerbIssued({predicate.verb!r}) completion is not observable from "
                "inside the live campaign shell (see module docstring) — the "
                "composition root must never hand this evaluator a VerbIssued step"
            )
            raise AssertionError(msg)
        msg = f"TutorialRuntimeProgress: unrecognized completion predicate kind {predicate!r}"
        raise AssertionError(msg)
