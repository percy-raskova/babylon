"""Shared fixtures for infrastructure topology tests (Feature 036)."""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines


@pytest.fixture()
def game_defines() -> GameDefines:
    """Default GameDefines instance for testing."""
    return GameDefines()
