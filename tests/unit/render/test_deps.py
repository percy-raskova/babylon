"""The Tier-1 pixel lane and snapshot mechanism must be importable (ADR097 D2/D3)."""

from __future__ import annotations

import importlib

import pytest

RUNTIME_MODULES = ["textual", "textual_plotext", "textual_image", "PIL", "tomlkit"]


@pytest.mark.parametrize("module_name", RUNTIME_MODULES)
def test_runtime_dependency_importable(module_name: str) -> None:
    assert importlib.import_module(module_name) is not None


def test_snapshot_plugin_available() -> None:
    # pytest-textual-snapshot registers the ``snap_compare`` fixture as a plugin.
    plugin = importlib.import_module("pytest_textual_snapshot")
    assert plugin is not None
