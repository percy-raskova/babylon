"""Unit tests for ``ReferenceCacheEntry`` Pydantic model (spec-069 T006).

Per data-model.md §1:

- ``population: int | None`` — None ⇒ Census + QCEW fallback both missing.
- ``employment_proxy: float | None`` — None ⇒ QCEW missing.
- Per-field independent nullability (all four combinations legitimate).
- Non-negative validators on both fields when not None.
- Frozen (``ConfigDict(frozen=True)``).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.engine.headless_runner.reference_data_cache import ReferenceCacheEntry


class TestReferenceCacheEntry:
    """Frozen Pydantic ``ReferenceCacheEntry`` per data-model.md §1."""

    def test_both_present(self) -> None:
        entry = ReferenceCacheEntry(population=1_770_000, employment_proxy=620_000.0)
        assert entry.population == 1_770_000
        assert entry.employment_proxy == 620_000.0

    def test_population_present_employment_missing(self) -> None:
        """Census present + QCEW missing (rare but legitimate)."""
        entry = ReferenceCacheEntry(population=100, employment_proxy=None)
        assert entry.population == 100
        assert entry.employment_proxy is None

    def test_population_missing_employment_present(self) -> None:
        """Census missing + QCEW present (QCEW × 0.33 fallback in cache)."""
        entry = ReferenceCacheEntry(population=None, employment_proxy=500.0)
        assert entry.population is None
        assert entry.employment_proxy == 500.0

    def test_both_missing(self) -> None:
        """Both fields independently nullable (asymmetric coverage)."""
        entry = ReferenceCacheEntry(population=None, employment_proxy=None)
        assert entry.population is None
        assert entry.employment_proxy is None

    def test_negative_population_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReferenceCacheEntry(population=-1, employment_proxy=0.0)

    def test_negative_employment_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReferenceCacheEntry(population=0, employment_proxy=-0.1)

    def test_zero_values_accepted(self) -> None:
        """Zero is a valid empirical value, not missing."""
        entry = ReferenceCacheEntry(population=0, employment_proxy=0.0)
        assert entry.population == 0
        assert entry.employment_proxy == 0.0

    def test_frozen_semantics(self) -> None:
        """Pydantic frozen=True forbids attribute mutation."""
        entry = ReferenceCacheEntry(population=100, employment_proxy=50.0)
        with pytest.raises(ValidationError):
            entry.population = 200  # type: ignore[misc]
