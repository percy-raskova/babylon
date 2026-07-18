"""D4: tools/regression_test.py's qa:regression harness must thread Vol III
calculator_overrides (built from the committed FRED fixture) into every
step() call — and must do so hermetically, from the fixture file alone.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import regression_test as rt  # type: ignore[import-not-found]  # noqa: E402


def test_run_scenario_passes_vol3_calculator_overrides_to_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RED->GREEN: _run_scenario_ticks must build calculator_overrides from
    the fixture and pass them into every step() call."""
    fixture = {"FEDFUNDS": {"2020": 0.0038}, "BAA10Y": {"2020": 0.021}}
    fixture_path = tmp_path / "vol3_fred_series.json"
    fixture_path.write_text(json.dumps(fixture))
    monkeypatch.setattr(rt, "FRED_FIXTURE_PATH", fixture_path)

    captured: dict[str, Any] = {}

    def _fake_step(
        state: Any, sim_config: Any, persistent_context: Any, defines: Any, **kwargs: Any
    ) -> Any:
        captured.update(kwargs)
        return state

    monkeypatch.setattr(rt, "step", _fake_step)

    rt.run_scenario("two_node", max_ticks=1)

    assert "calculator_overrides" in captured, "step() was not called with calculator_overrides"
    overrides = captured["calculator_overrides"]
    assert overrides.get("distribution_calculator") is not None
    assert overrides.get("interest_calculator") is not None
    assert overrides.get("fictitious_capital_calculator") is not None
