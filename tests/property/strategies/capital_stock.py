"""Hypothesis strategy for generating capital-stock perpetual-inventory triples.

Spec 053 T014: Generates ``(K_t, δ, I_t)`` triples within physical bounds
for property-based tests of the perpetual-inventory recurrence (INV-005 /
contracts/capital_recurrence.md).

The recurrence under test is ``K_{t+1} = (1 − δ) K_t + I_t``, implemented
in the codebase by ``DepreciationConfig.next_K(K_prev, c)`` (see
``src/babylon/economics/depreciation.py``). The "investment" term ``I_t``
corresponds to the ``c`` (constant capital flow) argument.

Bounds:
    - K_t ∈ [0, 1e9]: physically realistic capital stock magnitudes
    - δ ∈ [0, 1]: depreciation rate (0 = no depreciation, 1 = full annual)
    - I_t ∈ [0, 1e9]: non-negative investment per tick
"""

from __future__ import annotations

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy


def capital_stock_triple_strategy() -> SearchStrategy[tuple[float, float, float]]:
    """Generate (K_t, δ, I_t) triples within physical bounds.

    Returns:
        A Hypothesis ``SearchStrategy`` producing tuples of three floats:
        ``(K_t, δ, I_t)`` with ``K_t, I_t ∈ [0, 1e9]`` and ``δ ∈ [0, 1]``,
        all finite and non-NaN.
    """
    return st.tuples(
        st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False),
    )
