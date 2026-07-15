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

from babylon.intelligence.ai.prompt_registry import get_prompt_registry


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "tests/unit/ai/" in str(item.fspath).replace("\\", "/"):
            item.add_marker(pytest.mark.ai)


@pytest.fixture(autouse=True)
def _clear_prompt_registry_cache() -> None:
    """Clear the ``get_prompt_registry()`` ``lru_cache`` singleton around
    every AI-suite test.

    Trap this guards against: ``get_prompt_registry()`` is a
    ``maxsize=1`` process-wide cache. A test that builds it once (e.g. by
    importing ``director``, which calls it at module scope) permanently
    pins the DEFAULT directory's registry for the rest of the process — a
    later test that monkeypatches the prompt/archetype directory would
    silently observe the STALE cached instance instead of its own tmp_path
    fixture, with no error to signal the mismatch.
    """
    get_prompt_registry.cache_clear()
    yield
    get_prompt_registry.cache_clear()
