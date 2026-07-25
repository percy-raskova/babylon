"""Behavioral contract for the BDD Pilot text-capture harness (Task 10)."""

import pytest
from pydantic import ValidationError

from babylon.tui.shell.app_shell import AppShell
from babylon.tui.shell.bdd.harness import TutorialStep, export_visible_text


def test_tutorial_step_is_frozen():
    step = TutorialStep(verb="educate", expect_text=("Educate",))
    with pytest.raises(ValidationError):
        step.verb = "attack"


@pytest.mark.asyncio
async def test_export_visible_text_is_deterministic():
    app = AppShell()
    async with app.run_test():
        first = export_visible_text(app)
        second = export_visible_text(app)
        assert first == second  # no wall-clock, reproducible
        assert "action bar" in first
