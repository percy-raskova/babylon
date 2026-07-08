"""Marker enforcement for the AI suite.

Every test under ``tests/unit/ai/`` gets the ``ai`` marker automatically.
Before this hook, the marker was registered and documented (CLAUDE.md's
``pytest -m "ai"`` workflow, the extended-analysis CI ai-evaluation job)
but applied to ZERO tests — so ``-m ai`` selected nothing and
``-m "not ai"`` silently INCLUDED the whole AI suite. Auto-application at
collection keeps the directory and the marker from drifting apart again.
"""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "tests/unit/ai/" in str(item.fspath).replace("\\", "/"):
            item.add_marker(pytest.mark.ai)
