"""BDD harness — headless Pilot text-capture (design §G).

Runs the shell via Textual Pilot, issues a step's verb, and captures the emitted screen text —
the raw render of what the player sees. Determinism: narrator OFF (byte-reproducible); no
wall-clock. Text export uses a recording Rich Console (Textual 8.2.8 has no App.export_text).
"""

from __future__ import annotations

import io
from typing import Any

from pydantic import BaseModel, ConfigDict
from rich.console import Console
from textual.app import App
from textual.pilot import Pilot
from textual.widget import Widget


class TutorialStep(BaseModel):
    """One tutorial/BDD step: a verb to issue and the text expected on the resulting screen."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    verb: str
    expect_text: tuple[str, ...]


def export_visible_text(app: App[Any]) -> str:
    """Export the currently-visible widget tree as plain text via a recording Console.

    Textual 8.2.8 has no ``App.export_text``; content-bearing widgets (``Static`` and its
    subclasses) expose their visual via ``render()`` — containers render blank and are skipped
    by the emptiness check, keeping the capture to what the player actually reads.
    """
    console = Console(record=True, width=app.size.width or 120, file=io.StringIO())
    for node in app.screen.walk_children():
        if not isinstance(node, Widget):
            continue
        rendered = node.render()
        # Only content-bearing renders carry .plain (textual Content / rich Text);
        # container fills (Blank) stringify with memory addresses — never capture those.
        text = getattr(rendered, "plain", None)
        if text is not None and text.strip():
            console.print(text)
    return console.export_text()


async def run_step(pilot: Pilot[Any], step: TutorialStep) -> str:
    """Issue ``step.verb`` and return the captured screen text after it settles."""
    await pilot.press(*step.verb)  # verb keybinding; integration maps verb→key
    await pilot.pause()
    return export_visible_text(pilot.app)
