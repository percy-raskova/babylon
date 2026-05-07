"""Re-export of ``simplex_points`` strategy for spec-054 US3.

The canonical strategy lives in ``tests/test_simplex_invariants.py`` (the
legacy per-construction simplex test). Spec-054 needs it from a stable
import path under ``tests/property/strategies/`` so the per-pipeline
simplex test (``test_simplex_pipeline.py``) does not couple to the legacy
test file's location.

When the legacy file is eventually moved or deleted, this module is the
single migration point.
"""

from __future__ import annotations

from tests.test_simplex_invariants import simplex_points

__all__ = ["simplex_points"]
