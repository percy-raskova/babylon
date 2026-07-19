"""Family-level test: every U7 sensor is dispatchable and self-describing.

The six error classes are only useful if an agent can find and run them. This
pins the CLI surface: each new sensor is registered and exits 0 clean. Five
(liveness x2, aggregation, coupling, gate-blindness) are advisory per the
standing owner ruling; the sixth (public-surface baseline blindness, U7.11)
is wired as a real check:surface gate, not advisory (owner ruling 2026-07-19
-- see U7.11's Files: block).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TOOL_PATH = _REPO_ROOT / "tools" / "sentinel_check.py"


def _run(sensor: str) -> subprocess.CompletedProcess[str]:
    """Run one sensor through the family dispatcher.

    :param sensor: The sensor name to dispatch.
    :returns: The completed process.
    """
    return subprocess.run(
        [sys.executable, str(_TOOL_PATH), sensor],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("sensor", "expected_word"),
    [
        ("liveness", "Liveness"),
        ("aggregation", "Aggregation"),
        ("coupling", "Coupling"),
        ("coverage", "Data coverage"),
    ],
)
def test_sensor_is_dispatchable_and_advisory(sensor: str, expected_word: str) -> None:
    """Each U7 sensor runs from the family CLI and does not gate."""
    result = _run(sensor)
    assert result.returncode == 0, result.stderr
    assert expected_word in result.stdout


def test_surface_sensor_is_dispatchable_and_gates() -> None:
    """The surface sensor runs from the family CLI and reports clean.

    Unlike the four sensors above, ``surface`` is not advisory (owner ruling
    2026-07-19; U7.11) -- it gates on drift. On the committed, clean repo
    state it must still exit 0 with its own summary line, proving the CLI
    actually dispatches this sensor rather than silently omitting it.
    """
    result = _run("surface")
    assert result.returncode == 0, result.stderr
    assert "Public surface" in result.stdout


def test_unknown_sensor_is_rejected() -> None:
    """An unregistered sensor name is refused by argparse, not silently ignored."""
    result = _run("no_such_sensor")
    assert result.returncode == 2
    assert "invalid choice" in result.stderr


def test_reference_doc_names_all_six_error_classes() -> None:
    """The reference doc is the agent-facing index of the six classes."""
    doc = (_REPO_ROOT / "docs/reference/sentinel-error-classes.rst").read_text(encoding="utf-8")
    for error_class in (
        "correct-but-inert",
        "computed-but-never-consumed",
        "gate-blindness",
        "intensive-aggregation",
        "undeclared-coupling",
        "public-surface baseline blindness",
    ):
        assert error_class in doc


def test_state_yaml_strikes_the_four_owed_sentinel_classes() -> None:
    """U7 acceptance: the four previously-owed classes are struck by name."""
    state = (_REPO_ROOT / "ai/state.yaml").read_text(encoding="utf-8")
    for owed_class in (
        "correct-but-inert",
        "computed-but-never-consumed",
        "gate-blindness",
        "intensive-aggregation",
    ):
        assert owed_class in state, (
            f"ai/state.yaml does not record {owed_class!r} as struck from the "
            "owed-sentinel list (design §4 U7 acceptance)"
        )
    assert "STRUCK from the owed-sentinel list" in state
