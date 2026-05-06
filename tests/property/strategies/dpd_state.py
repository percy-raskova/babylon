"""Hypothesis strategy for generating DPDState distributions.

Spec 053 T013: Generates per-hex ``DPDState`` cohort distributions for
property-based tests of population conservation (INV-004 / contracts/
population_lifecycle.md).

Note (spec drift): the original spec/tasks described DPDState cohorts as
integer-valued. The actual ``DPDState`` model uses float fields with
``ge=0.0``. The strategy therefore draws non-negative floats; the
population conservation test uses a small numerical tolerance instead of
strict integer equality (see contracts/population_lifecycle.md).
"""

from __future__ import annotations

from collections.abc import Mapping

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from babylon.economics.lifecycle.types import DPDState
from tests.property.strategies.hex_grid import MICHIGAN_RES7_SEED_CELLS


def _cohort_count() -> SearchStrategy[float]:
    """Non-negative cohort population. Bounded for sanity."""
    return st.floats(min_value=0.0, max_value=10_000.0, allow_nan=False, allow_infinity=False)


def _rate() -> SearchStrategy[float]:
    """Transition rate in [0, 1]."""
    return st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


@st.composite
def _dpd_state(draw: st.DrawFn) -> DPDState:
    return DPDState(
        pop_d=draw(_cohort_count()),
        pop_p=draw(_cohort_count()),
        pop_d_prime=draw(_cohort_count()),
        rate_d_to_p=draw(_rate()),
        rate_p_to_d_prime=draw(_rate()),
        rate_d_prime_to_death=draw(_rate()),
        birth_rate=draw(_rate()),
        wealth_d_prime=draw(
            st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False)
        ),
    )


@st.composite
def _dpd_grid(
    draw: st.DrawFn,
    min_hexes: int,
    max_hexes: int,
) -> Mapping[str, DPDState]:
    pool = MICHIGAN_RES7_SEED_CELLS
    upper = min(max_hexes, len(pool))
    n = draw(st.integers(min_value=min_hexes, max_value=max(min_hexes, upper)))
    n = min(n, len(pool))
    indices = draw(
        st.lists(
            st.integers(min_value=0, max_value=len(pool) - 1),
            min_size=n,
            max_size=n,
            unique=True,
        )
    )
    return {pool[i]: draw(_dpd_state()) for i in indices}


def dpd_state_grid_strategy(
    min_hexes: int = 1,
    max_hexes: int = 25_000,
) -> SearchStrategy[Mapping[str, DPDState]]:
    """Generate a mapping of hex_id → DPDState across the Michigan tri-county pool.

    Args:
        min_hexes: Minimum hex count per generated grid (default 1).
        max_hexes: Maximum hex count. Clamped to seed-pool size; Hypothesis
            size-biased shrinking favors small grids.

    Returns:
        A Hypothesis ``SearchStrategy[Mapping[str, DPDState]]``.
    """
    return _dpd_grid(min_hexes, max_hexes)
