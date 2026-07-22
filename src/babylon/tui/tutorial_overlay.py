"""The guided opening-arc overlay — the PLAYER-facing consumer of the T6
tutorial step script (Program v1.0.0 T6, Unit U4).

Per ``ai/_inbox/t6-tutorial-bdd-ruling.md``: ONE data artifact —
:class:`~babylon.game.tutorial.TutorialStep` — is consumed three ways. Units
U1/U2 shipped the model and the headless Pilot executor; this unit ships the
THIRD consumer, the live overlay a player actually sees, rendered over the
campaign shell. Because "the strings the player reads ARE the scenario
definitions CI runs," this widget renders :attr:`~babylon.game.tutorial.
TutorialStep.scenario_name`/:attr:`~babylon.game.tutorial.TutorialStep.
overlay_text` VERBATIM — it never reconstructs its own copy of the
given/when/then prose.

**Projection-pure, by construction (import-linter: ``babylon.tui`` may never
reach ``babylon.engine``).** :mod:`babylon.game.tutorial` imports
``babylon.engine.scenarios.wayne_county`` directly, so this module — a real
``babylon.tui`` package member — must never import it either (a direct
import here would create the exact forbidden ``tui -> game -> engine`` chain
import-linter's "tui client reads projections only" contract exists to
catch). The WO-37 trick applies one more time: :data:`TutorialStepView` and
:data:`TutorialProgress` below are STRUCTURAL protocols describing only the
handful of members this widget actually touches;
:class:`~babylon.game.tutorial.TutorialStep` and the composition-root's
concrete predicate evaluator (:class:`~babylon.game.tutorial_runtime.
TutorialRuntimeProgress`) satisfy them without either module importing the
other — the exact shape :class:`~babylon.tui.app.CampaignHandle`/
:class:`~babylon.tui.app.PacedDriverHandle` already establish for the
engine/game seam.

**The widget renders and advances; it never evaluates a predicate itself.**
:meth:`TutorialOverlay.check_progress` is a dumb poll: ask
:attr:`TutorialProgress.is_step_complete` whether the CURRENT step's
completion holds, and if so, advance — the actual predicate logic (reading
the live campaign's tick, the paced driver's ``awaiting_ack``, the nav
shell's current subject) lives entirely in the composition root's evaluator,
never here. The composition root is responsible for calling
:meth:`check_progress` after whatever it considers a "committed tick or
navigation event" (:class:`~babylon.tui.app.ArchiveApp` does this at the tail
of ``action_advance_tick``/``action_run_until_paused``/
``action_acknowledge_pause``/``_navigate``).

**Consecutive same-target steps can collapse in one poll.** :meth:`check_progress`
loops forward through every consecutive TRUE predicate starting at the
current index (bounded by :data:`len(steps)`, Power-of-10 rule 2) — so two
adjacent steps sharing the identical completion (e.g. the authored arc's
``palette_to_the_economy_dossier``/``read_the_theorem_verdict``, both
``OnPage(subject="economy/USA")``) both advance in the SAME poll, and the
first of the pair's own instruction text is never separately shown. This is
an honest consequence of steps being GATE conditions rather than
individually-timed beats, not a bug this unit works around — flagged here
per this repo's own "surface the gap, don't silently smooth it" culture
(Constitution III.11), mirroring the executor unit's own documented
``run_until_autopause`` no-op finding.

**Dismiss is a binding on the widget itself**, not on
:class:`~babylon.tui.app.ArchiveApp` (unlike ``t``/``r``/``a``, which are App
actions) — deliberately, so the overlay's own lifecycle (mount, advance,
dismiss) stays fully encapsulated wherever it is mounted, never requiring its
host to know its internals beyond "mount me, poll me." Because Textual
resolves a widget's own ``BINDINGS`` only via the FOCUS chain (a sibling that
never has focus never sees its own bindings fire), :meth:`on_mount` gives the
widget focus so ``escape`` reaches it; the App's own ``ctrl+o``/``t``/``r``/
``a`` bindings are unaffected either way (``App`` is always in the bubble
chain regardless of which descendant currently holds focus).

**A NEW player-facing option — declared, not silently exempt-by-omission.**
``TutorialOverlay.BINDINGS``'s own ``escape`` entry is exactly the kind of
option the T6 ruling's option-coverage sentinel (Unit U3,
:mod:`babylon.sentinels.tutorial_coverage`) polices: every real ``Binding`` a
Babylon TUI class declares must be exercised by a ``TutorialStep`` or carry a
cited :class:`~babylon.sentinels.exemptions.SentinelExemption`. This one is
cited, not scripted — ``babylon.sentinels.tutorial_coverage.registry.
TUTORIAL_COVERAGE_EXEMPTIONS`` keyed ``("binding", "TutorialOverlay",
"escape")`` — because dismissing the tutorial is the tutorial system's own
chrome, never a beat the opening arc itself teaches.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final, Protocol, runtime_checkable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Label

__all__ = ["TutorialOverlay", "TutorialProgress", "TutorialStepView"]


@runtime_checkable
class TutorialStepView(Protocol):
    """Structural shape of one rendered step (:class:`~babylon.game.tutorial.
    TutorialStep` satisfies this without either module importing the other).

    Deliberately narrow: only the two DERIVED rendering properties the
    overlay actually paints, never the raw ``given``/``when``/``then``
    fields directly — rendering through the model's own properties (rather
    than reassembling the fields here) is what keeps this widget's output a
    verbatim, zero-copy-divergence render of U1's own rendering contract.
    """

    @property
    def scenario_name(self) -> str:
        """The step's one-sentence summary (the developer-docs title)."""
        ...

    @property
    def overlay_text(self) -> str:
        """The GIVEN/WHEN/THEN block, the SAME fields as :attr:`scenario_name`."""
        ...


@runtime_checkable
class TutorialProgress(Protocol):
    """The predicate-evaluation seam: is step ``step_index`` complete RIGHT
    NOW against the live campaign?

    Fulfilled for real by :class:`~babylon.game.tutorial_runtime.
    TutorialRuntimeProgress` (the composition root's concrete evaluator,
    reading the live campaign's tick, the paced driver's ``awaiting_ack``,
    and the nav shell's current subject) — never implemented in this
    module, which only ever calls through this seam.
    """

    def is_step_complete(self, step_index: int) -> bool:
        """Whether the step at ``step_index`` currently holds.

        :param step_index: an index into the SAME step sequence the caller
            constructed this evaluator with — the overlay and its evaluator
            must always share one common, identically-ordered step list.
        :returns: ``True`` iff that step's completion predicate is satisfied
            by the live campaign's CURRENT state.
        """
        ...


#: Generous static bound mirroring ``TutorialScript._MAX_SCRIPT_STEPS``
#: (Power-of-10 rule 2): :meth:`TutorialOverlay.check_progress` never
#: advances past this many steps in one poll, and the authored arc this
#: unit renders sits far below it either way.
_MAX_OVERLAY_STEPS: Final = 64


class TutorialOverlay(Container):
    """Renders the current tutorial step over the live campaign shell.

    :param steps: the ordered step sequence to walk — MUST be the exact
        same sequence (same length, same order) the ``progress`` evaluator
        was itself built against, since :meth:`check_progress` indexes both
        by the same integer position.
    :param progress: the predicate-evaluation seam (see :data:`TutorialProgress`).
    """

    BINDINGS = [Binding("escape", "dismiss_tutorial", "Dismiss Tutorial")]

    DEFAULT_CSS = """
    TutorialOverlay {
        dock: top;
        height: auto;
        max-height: 40%;
        background: $panel;
        border: round $accent;
        padding: 0 1;
        margin: 1 2;
    }
    """

    can_focus = True

    def __init__(
        self,
        steps: Sequence[TutorialStepView],
        progress: TutorialProgress,
        *,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._steps: tuple[TutorialStepView, ...] = tuple(steps)
        if len(self._steps) > _MAX_OVERLAY_STEPS:
            msg = (
                f"TutorialOverlay: {len(self._steps)} steps exceeds the static bound "
                f"{_MAX_OVERLAY_STEPS} (Power-of-10 rule 2)"
            )
            raise ValueError(msg)
        self._progress = progress
        self._current_index = 0
        self.dismissed = False
        """``True`` once the player has dismissed this overlay via ``escape``
        (or it has been removed some other way) — :meth:`check_progress`
        becomes a permanent no-op afterward."""

    @property
    def current_step_index(self) -> int:
        """The step index currently shown (may equal ``len(steps)`` once finished)."""
        return self._current_index

    @property
    def finished(self) -> bool:
        """``True`` once every step's completion has been observed."""
        return self._current_index >= len(self._steps)

    def compose(self) -> ComposeResult:
        yield Label("", id="tutorial-heading")
        yield Label("", id="tutorial-body")

    def on_mount(self) -> None:
        self.focus()
        self.check_progress()

    def check_progress(self) -> None:
        """Re-evaluate the current step's completion predicate; advance
        through every consecutive TRUE step (see module docstring on why
        more than one can advance in a single poll), then re-render.

        A no-op once :attr:`dismissed` — the composition root may keep
        calling this after the player dismisses the overlay (it has no way
        to know without asking), and this method must stay a harmless no-op
        rather than raise against an already-removed widget.
        """
        if self.dismissed:
            return
        for _ in range(len(self._steps)):  # loop bound: _current_index < len(steps) each time
            if self.finished or not self._progress.is_step_complete(self._current_index):
                break
            self._current_index += 1
        self._render_current_step()

    def _render_current_step(self) -> None:
        heading = self.query_one("#tutorial-heading", Label)
        body = self.query_one("#tutorial-body", Label)
        if self.finished:
            heading.update("Opening arc complete.")
            body.update("Press Escape to dismiss this tutorial.")
            return
        step = self._steps[self._current_index]
        heading.update(f"Step {self._current_index + 1}/{len(self._steps)}: {step.scenario_name}")
        body.update(step.overlay_text)

    async def action_dismiss_tutorial(self) -> None:
        """``escape``: dismiss the overlay for the rest of this session."""
        self.dismissed = True
        await self.remove()
