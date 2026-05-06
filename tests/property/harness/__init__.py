"""Shared harness utilities for spec-054 bound-invariant property tests.

This package provides cross-cutting plumbing reused across the four
bound-invariant test files (probability, wealth/heat, simplex, alpha-smoothing):

- :func:`tol`: magnitude-aware tolerance helper, extracted from spec-053's
  ``test_value_conservation._tol`` so US3 (simplex) and US4 (alpha-smoothing)
  share a single source of truth for float64 ULP-aware comparison.
- :mod:`.system_registry`: auto-discovery of all 22 engine Systems.
- :mod:`.crisis_inspector`: ``CrisisStateInspector`` (steady vs crisis classifier).
- :mod:`.probability_discovery`: Pydantic ``model_fields`` walker + type-driven
  formula discovery.
- :mod:`.alpha_discovery`: ``defines.py`` field-name heuristic with
  false-positive exclusion list.
- :mod:`.bound_harness`: ``BoundInvariantHarness`` runner.

See ``specs/054-bound-invariants/`` for the spec and contracts.
"""

from __future__ import annotations


def tol(n: int, magnitude: float = 0.0) -> float:
    """Magnitude-aware tolerance for bound-invariant comparisons.

    Combines three components:

        max(
            1e-10,            # absolute floor for tiny inputs
            1e-11 * N,        # accumulation error linear in input count
            1e-13 * |mag|,    # relative ULP component (~450x machine epsilon)
        )

    The relative component is necessary because absolute drift at large sums
    (e.g. ~1e6) reaches ~1e-10 purely from float64 round-off: machine eps is
    ~2.22e-16, and accumulating N ~ 200 entries through ~3 ops each contributes
    ~3N * eps ~ 1.3e-13 relative drift in the worst case. The 1e-13 coefficient
    gives ~7x headroom over that bound.

    Extracted verbatim from
    ``tests/property/invariants/test_value_conservation._tol`` (spec-053) so
    US3 (simplex) and US4 (alpha-smoothing) can share one source of truth.

    Args:
        n: Number of entities / coefficients in the comparison.
        magnitude: Absolute scale of the quantity being compared.

    Returns:
        Tolerance value suitable for ``abs(a - b) <= tol(...)`` checks.
    """
    return max(1e-10, 1e-11 * n, 1e-13 * abs(magnitude))


__all__ = ["tol"]
