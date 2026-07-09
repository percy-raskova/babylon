"""Contract: verb dispatch is baseline-neutral BY CONSTRUCTION.

Player verbs only ever run when the web bridge injects
``persistent_context["player_actions"]``. Nothing in the engine (``src``) writes
that key, so headless / canonical runs never dispatch a resolver — the NPC path
and the byte-for-byte baseline are untouched. These tests pin that guarantee:

* no ``src/babylon`` module references ``player_actions`` except the OODA reader;
* a headless tick never fabricates ``player_actions`` (it only *reads* them), yet
  still publishes ``turn_resolution`` (the new seam runs, inertly).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.engine.scenarios import create_imperial_circuit_scenario
from babylon.engine.simulation_engine import step

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC_BABYLON = _REPO_ROOT / "src" / "babylon"
#: The ONLY engine module allowed to reference player_actions (it reads them
#: from context; it never populates them).
_ALLOWED_READER = "engine/systems/ooda.py"


class TestNoHeadlessPlayerActionWriter:
    """No src module fabricates player_actions (only the OODA reader names it)."""

    def test_only_ooda_references_player_actions(self) -> None:
        offenders: list[str] = []
        max_files = 5000  # fixed upper bound (static-analysis friendly)
        for count, path in enumerate(sorted(_SRC_BABYLON.rglob("*.py"))):
            if count >= max_files:
                break
            if "player_actions" in path.read_text(encoding="utf-8"):
                rel = path.relative_to(_SRC_BABYLON).as_posix()
                if rel != _ALLOWED_READER:
                    offenders.append(rel)
        assert offenders == [], (
            f"player_actions referenced outside the OODA reader — a headless "
            f"code path may now inject player actions and shift the baseline: {offenders}"
        )


class TestHeadlessTickInertness:
    """A headless tick never populates player_actions but does run the new seam."""

    def test_headless_tick_does_not_fabricate_player_actions(self) -> None:
        state, config, defines = create_imperial_circuit_scenario()
        ctx: dict[str, object] = {}
        step(state, config, persistent_context=ctx, defines=defines)
        # The engine reads player_actions; it must never create the key itself.
        assert "player_actions" not in ctx
        # The verb-dispatch seam still runs each tick (inertly, no player input).
        assert "turn_resolution" in ctx
