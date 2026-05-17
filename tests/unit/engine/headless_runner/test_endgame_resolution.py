"""Spec-065 T058/T059: endgame detector resolution + argparse acceptance.

T058: --endgame-detector argparse accepts a dotted path.
T059: bridge.set_endgame_detector resolves a valid path; rejects bogus paths.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.headless_runner.argparse_cli import build_parser
from babylon.engine.headless_runner.bridge import WorldStateBridge

# ----------------------------------------------------------------------
# T058: argparse acceptance
# ----------------------------------------------------------------------


def test_endgame_detector_accepts_dotted_path() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["--endgame-detector", "tests.integration.fixtures.endgame.NeverFires"]
    )
    assert args.endgame_detector == "tests.integration.fixtures.endgame.NeverFires"


def test_endgame_detector_default_is_none() -> None:
    parser = build_parser()
    args = parser.parse_args([])
    assert args.endgame_detector is None


# ----------------------------------------------------------------------
# T059: resolution unit tests
# ----------------------------------------------------------------------


@pytest.fixture
def bridge() -> WorldStateBridge:
    return WorldStateBridge(runtime=None, defines=GameDefines())


def test_set_endgame_detector_resolves_valid_path(bridge: WorldStateBridge) -> None:
    """Valid dotted path → instance stored on the bridge."""
    bridge.set_endgame_detector("tests.integration.fixtures.endgame.NeverFires")
    # Endgame poll on a never-fires detector returns None.
    assert bridge.poll_endgame(world=None, tick=42) is None


def test_set_endgame_detector_imperial_collapse(bridge: WorldStateBridge) -> None:
    """ImperialCollapseAtTick250 fires only at tick 250."""
    bridge.set_endgame_detector("tests.integration.fixtures.endgame.ImperialCollapseAtTick250")
    assert bridge.poll_endgame(world=None, tick=249) is None
    event = bridge.poll_endgame(world=None, tick=250)
    assert event is not None
    assert event["condition"] == "IMPERIAL_COLLAPSE"
    assert event["tick"] == 250
    assert bridge.poll_endgame(world=None, tick=251) is None


def test_set_endgame_detector_rejects_invalid_path(bridge: WorldStateBridge) -> None:
    with pytest.raises(ImportError, match="not a dotted path"):
        bridge.set_endgame_detector("invalidpath")


def test_set_endgame_detector_rejects_unknown_module(bridge: WorldStateBridge) -> None:
    with pytest.raises(ImportError, match="could not be imported"):
        bridge.set_endgame_detector("no.such.module.Detector")


def test_set_endgame_detector_rejects_unknown_attr(bridge: WorldStateBridge) -> None:
    with pytest.raises(ImportError, match="has no attribute"):
        bridge.set_endgame_detector("tests.integration.fixtures.endgame.NotARealClass")
