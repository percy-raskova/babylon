"""Unit tests for babylon.tui.tutorial_overlay: the guided opening-arc
overlay (Program v1.0.0 T6, Unit U4).

Three families: seam conformance (the real
:class:`~babylon.game.tutorial.TutorialStep` structurally satisfies
:data:`~babylon.tui.tutorial_overlay.TutorialStepView`), verbatim rendering
(the reviewer-diffable "zero copy divergence" contract — the overlay's own
rendered text equals the REAL model's own ``scenario_name``/``overlay_text``
fields, walked across the whole authored arc, not reconstructed locally),
and widget behavior (advance-on-predicate, dismiss) against a scripted
:data:`~babylon.tui.tutorial_overlay.TutorialProgress` double — no
``ArchiveApp``/campaign/engine required, mirroring
``tests/unit/tui/test_directives.py``'s own bare-host-``App`` idiom.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label

from babylon.game.tutorial import WAYNE_OPENING_ARC
from babylon.tui.tutorial_overlay import TutorialOverlay, TutorialProgress, TutorialStepView

pytestmark = [pytest.mark.unit]


@dataclass(frozen=True)
class _FakeStep:
    """A minimal :data:`TutorialStepView` double: only the two rendered fields."""

    scenario_name: str
    overlay_text: str


@dataclass
class _FakeProgress:
    """A scripted :data:`TutorialProgress` double.

    ``is_step_complete(i)`` reads a caller-controlled dict, defaulting to
    ``False`` for any index never explicitly set — never a real predicate
    evaluation (that's :mod:`babylon.game.tutorial_runtime`'s own job,
    tested separately).
    """

    _complete: dict[int, bool] = field(default_factory=dict)

    def is_step_complete(self, step_index: int) -> bool:
        return self._complete.get(step_index, False)

    def set_complete(self, step_index: int, value: bool = True) -> None:
        self._complete[step_index] = value


class _OverlayHost(App[None]):
    """Bare host mounting exactly one :class:`TutorialOverlay`."""

    def __init__(self, steps: Sequence[TutorialStepView], progress: TutorialProgress) -> None:
        super().__init__()
        self._steps = steps
        self._progress = progress

    def compose(self) -> ComposeResult:
        yield TutorialOverlay(self._steps, self._progress, id="tutorial-overlay")


def _overlay(app: _OverlayHost) -> TutorialOverlay:
    return app.query_one(TutorialOverlay)


def _heading_text(app: _OverlayHost) -> str:
    return str(_overlay(app).query_one("#tutorial-heading", Label).content)


def _body_text(app: _OverlayHost) -> str:
    return str(_overlay(app).query_one("#tutorial-body", Label).content)


class TestSeamConformance:
    def test_fake_progress_satisfies_the_protocol(self) -> None:
        assert isinstance(_FakeProgress(), TutorialProgress)

    def test_fake_step_satisfies_the_view_protocol(self) -> None:
        assert isinstance(_FakeStep("s.", "S"), TutorialStepView)

    def test_every_real_authored_step_satisfies_the_view_protocol(self) -> None:
        """The REAL model — not just a test double — structurally satisfies
        what the widget consumes; this is what makes verbatim rendering
        possible without ``babylon.tui`` ever importing
        ``babylon.game.tutorial``."""
        for step in WAYNE_OPENING_ARC.steps:  # loop bound: len(steps) == 14
            assert isinstance(step, TutorialStepView)


class TestRendersVerbatimFromTheRealModel:
    """The T6 ruling's "zero copy divergence" contract, string-compared
    against the REAL :data:`~babylon.game.tutorial.WAYNE_OPENING_ARC` — not
    a local fixture that could quietly drift from the model's own fields.
    """

    @pytest.mark.asyncio
    async def test_first_step_renders_its_own_fields_verbatim_on_mount(self) -> None:
        steps = WAYNE_OPENING_ARC.steps
        app = _OverlayHost(steps, _FakeProgress())
        async with app.run_test():
            first = steps[0]
            assert first.scenario_name in _heading_text(app)
            assert _body_text(app) == first.overlay_text

    @pytest.mark.asyncio
    async def test_every_step_renders_its_own_fields_verbatim_when_current(self) -> None:
        """Walks every real authored step forward one at a time, asserting
        the rendered heading/body match THAT step's own fields at every
        position — proves derivation across the whole arc, not merely the
        first beat."""
        steps = WAYNE_OPENING_ARC.steps
        progress = _FakeProgress()
        app = _OverlayHost(steps, progress)
        async with app.run_test():
            overlay = _overlay(app)
            for index, step in enumerate(steps):  # loop bound: len(steps) == 14
                assert overlay.current_step_index == index
                assert step.scenario_name in _heading_text(app)
                assert _body_text(app) == step.overlay_text
                progress.set_complete(index, True)
                overlay.check_progress()
            assert overlay.finished is True


class TestAdvanceOnPredicate:
    @pytest.mark.asyncio
    async def test_stays_on_the_current_step_while_the_predicate_is_false(self) -> None:
        steps = (
            _FakeStep("first sentence.", "FIRST BLOCK"),
            _FakeStep("second sentence.", "SECOND BLOCK"),
        )
        app = _OverlayHost(steps, _FakeProgress())
        async with app.run_test():
            overlay = _overlay(app)
            overlay.check_progress()
            assert overlay.current_step_index == 0
            assert "first sentence." in _heading_text(app)

    @pytest.mark.asyncio
    async def test_advances_to_the_next_step_once_the_predicate_holds(self) -> None:
        steps = (
            _FakeStep("first sentence.", "FIRST BLOCK"),
            _FakeStep("second sentence.", "SECOND BLOCK"),
        )
        progress = _FakeProgress()
        app = _OverlayHost(steps, progress)
        async with app.run_test():
            overlay = _overlay(app)
            progress.set_complete(0, True)
            overlay.check_progress()
            assert overlay.current_step_index == 1
            assert "second sentence." in _heading_text(app)
            assert _body_text(app) == "SECOND BLOCK"

    @pytest.mark.asyncio
    async def test_advances_through_every_consecutive_true_step_in_one_poll(self) -> None:
        steps = tuple(_FakeStep(f"s{i}.", f"B{i}") for i in range(4))
        progress = _FakeProgress({0: True, 1: True, 2: True})
        app = _OverlayHost(steps, progress)
        async with app.run_test():
            overlay = _overlay(app)
            overlay.check_progress()
            assert overlay.current_step_index == 3

    @pytest.mark.asyncio
    async def test_finishing_every_step_renders_the_completion_message(self) -> None:
        steps = (_FakeStep("only sentence.", "ONLY BLOCK"),)
        progress = _FakeProgress({0: True})
        app = _OverlayHost(steps, progress)
        async with app.run_test():
            overlay = _overlay(app)
            overlay.check_progress()
            assert overlay.finished is True
            assert "complete" in _heading_text(app).lower()


class TestDismissBinding:
    @pytest.mark.asyncio
    async def test_escape_dismisses_the_overlay_and_removes_it_from_the_dom(self) -> None:
        steps = (_FakeStep("only sentence.", "ONLY BLOCK"),)
        app = _OverlayHost(steps, _FakeProgress())
        async with app.run_test() as pilot:
            overlay = _overlay(app)
            assert overlay.dismissed is False
            await pilot.press("escape")
            await pilot.pause()
            assert overlay.dismissed is True
            assert len(app.query(TutorialOverlay)) == 0

    @pytest.mark.asyncio
    async def test_check_progress_is_a_harmless_no_op_after_dismissal(self) -> None:
        steps = (_FakeStep("only sentence.", "ONLY BLOCK"),)
        progress = _FakeProgress()
        app = _OverlayHost(steps, progress)
        async with app.run_test() as pilot:
            overlay = _overlay(app)
            await pilot.press("escape")
            await pilot.pause()
            progress.set_complete(0, True)
            overlay.check_progress()  # must not raise against an unmounted widget
            assert overlay.current_step_index == 0
