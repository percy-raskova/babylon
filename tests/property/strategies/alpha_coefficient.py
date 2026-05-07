"""Hypothesis strategy for alpha-smoothing triples (spec-054 US4 Predicate A).

Generates ``(prev: float, raw: float, override_alpha: float | None)`` triples
where ``prev, raw`` lie in a wide bounded range and ``override_alpha`` is
either ``None`` (use the coefficient's declared ``default_alpha``) or a draw
from ``(0.0, 1.0]`` to override.

Used by :func:`tests.property.invariants.test_alpha_smoothing.\
test_alpha_inequality_synthesized` for the synthesized layer of the hybrid
US4 strategy (per Q3 clarification).
"""

from __future__ import annotations

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

_VALUE_RANGE = 1e9
"""Bound on prev/raw draws — wide enough to exercise large-magnitude EMA
behavior without overflowing intermediate float arithmetic."""


@st.composite
def _alpha_triple(draw: st.DrawFn) -> tuple[float, float, float | None]:
    prev = draw(
        st.floats(
            min_value=-_VALUE_RANGE,
            max_value=_VALUE_RANGE,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    raw = draw(
        st.floats(
            min_value=-_VALUE_RANGE,
            max_value=_VALUE_RANGE,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    use_override = draw(st.booleans())
    if use_override:
        override = draw(
            st.floats(
                min_value=1e-6,
                max_value=1.0,
                allow_nan=False,
                allow_infinity=False,
                exclude_min=False,
            )
        )
    else:
        override = None
    return prev, raw, override


def alpha_coefficient_triple_strategy() -> SearchStrategy[tuple[float, float, float | None]]:
    """Return a strategy producing ``(prev, raw, override_alpha)`` triples.

    The override slot is ``None`` to mean "use the discovered coefficient's
    own ``default_alpha``" or a draw from ``[1e-6, 1.0]`` to exercise the
    EMA inequality across the full rate range.

    Returns:
        Hypothesis ``SearchStrategy`` producing tuples suitable for the
        synthesized US4 sweep.
    """
    return _alpha_triple()


__all__ = ["alpha_coefficient_triple_strategy"]
