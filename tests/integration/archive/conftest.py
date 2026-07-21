"""Env pinning for the county e2e snapshot golden.

Same rationale as ``tests/unit/tui/conftest.py``: mise exports
``NO_COLOR=1`` repo-wide, Textual desaturates under it even headless, and a
golden generated in one lane (mise/CI grayscale vs direct-pytest truecolor)
can never match the other. The snapshot tests own the knob explicitly so
every lane renders the same truecolor bytes.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _truecolor_snapshots(monkeypatch: pytest.MonkeyPatch) -> None:
    """Render snapshot goldens in full color regardless of the host env."""
    monkeypatch.delenv("NO_COLOR", raising=False)
