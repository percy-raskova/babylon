"""Hypothesis strategy for generating capital-stock perpetual-inventory triples.

Spec 053 T014: Generates ``(K_t, δ, I_t)`` triples within physical bounds
for property-based tests of the perpetual-inventory recurrence (INV-005 /
contracts/capital_recurrence.md).

The recurrence under test is ``K_{t+1} = (1 − δ) K_t + I_t``, implemented
in the codebase by ``DepreciationConfig.next_K(K_prev, c)`` (see
``src/babylon/domain/economics/depreciation.py``). The "investment" term ``I_t``
corresponds to the ``c`` (constant capital flow) argument.

Bounds:
    - K_t ∈ [0, 1e9]: physically realistic capital stock magnitudes
    - δ ∈ [0.01, 0.20]: depreciation rate. The ``DepreciationConfig.__post_init__``
      validator restricts δ to this range (BEA fixed-asset-table empirical bounds);
      the strategy honors it. Boundary cases δ=0 and δ=1 from the spec's User
      Story 5 acceptance scenarios are tested algebraically (formula directly)
      rather than through the validated calculator.
    - I_t ∈ [0, 1e9]: non-negative investment per tick
"""

from __future__ import annotations

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy


def capital_stock_triple_strategy() -> SearchStrategy[tuple[float, float, float]]:
    """Generate (K_t, δ, I_t) triples within ``DepreciationConfig`` valid bounds.

    Returns:
        A Hypothesis ``SearchStrategy`` producing tuples of three floats:
        ``(K_t, δ, I_t)`` with ``K_t, I_t ∈ [0, 1e9]`` and ``δ ∈ [0.01, 0.20]``,
        all finite and non-NaN. Bounds match
        ``DepreciationConfig.__post_init__`` validation.
    """
    return st.tuples(
        st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.01, max_value=0.20, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False),
    )
