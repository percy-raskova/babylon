"""Local fix for a Textual SVG-export vs. ``trailing-whitespace`` hook clash.

Every ``pytest-textual-snapshot`` ``.raw`` golden under any ``__snapshots__/``
directory in this repo carries one line of trailing whitespace baked into
Rich's own SVG export template (not our code) — confirmed present in every
existing golden (``tests/unit/tui/__snapshots__/...``,
``tests/integration/archive/__snapshots__/...``, both pre-dating this WO).
The repo's ``trailing-whitespace`` pre-commit hook strips it from whatever is
staged, desyncing a freshly-committed golden from the byte-identical SVG a
fresh render always reproduces on the very next plain test run — a
pre-existing, repo-wide tooling gap outside this WO's touch boundary (see the
WO-29 integrator report; the existing keel/integration-archive goldens
happen to have escaped the hook so far, which is how they still pass).

Rather than edit the shared ``.pre-commit-config.yaml`` (out of scope, and a
change the WO-29 auto-mode classifier declined), this conftest normalizes
trailing whitespace on the captured SVG *before* the ``syrupy`` comparison,
scoped to this directory only: both the freshly-captured "actual" screenshot
and the golden on disk (which stays hook-stable because it never carries the
trailing whitespace) end up in agreement, now and on every future run.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from typing import Any

import pytest
import textual._doc
from textual.app import App
from textual.pilot import Pilot

_original_take_svg_screenshot = textual._doc.take_svg_screenshot


def _stripped_take_svg_screenshot(
    app: App[Any] | None = None,
    app_path: str | None = None,
    press: Iterable[str] = (),
    hover: str = "",
    title: str | None = None,
    terminal_size: tuple[int, int] = (80, 24),
    run_before: Callable[[Pilot], Awaitable[None] | None] | None = None,
    wait_for_animation: bool = True,
    simplify: bool = True,
) -> str:
    """Delegate to the real ``take_svg_screenshot``, then strip trailing
    whitespace per line — matching what the ``trailing-whitespace`` hook
    would do to a committed golden, so both sides of the comparison agree.

    :returns: the SVG screenshot text, with every line's trailing whitespace
        removed.
    """
    svg = _original_take_svg_screenshot(
        app=app,
        app_path=app_path,
        press=press,
        hover=hover,
        title=title,
        terminal_size=terminal_size,
        run_before=run_before,
        wait_for_animation=wait_for_animation,
        simplify=simplify,
    )
    return "\n".join(line.rstrip() for line in svg.split("\n"))


@pytest.fixture(autouse=True)
def _normalize_svg_trailing_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip trailing whitespace from every SVG captured by ``snap_compare``
    in this directory, so goldens stay hook-stable across a real commit.

    :param monkeypatch: standard pytest fixture, reverted automatically.
    """
    monkeypatch.setattr(textual._doc, "take_svg_screenshot", _stripped_take_svg_screenshot)
