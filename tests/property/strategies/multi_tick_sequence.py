"""Hypothesis strategies for spec-056 US4 monotonic-idempotent tests.

Per research.md §7: synthetic ``(tick, payload)`` sequences for the
US4 persistence contract. Payloads are minimal Pydantic-serializable
dicts — they need NOT be valid ``WorldState`` snapshots, because US4
tests the persistence contract not engine semantics. This isolates US4
from engine regressions covered by Specs 053–055.

Three exports:
  - ``multi_tick_sequence_strategy(n_ticks=5)``: 5-tick sequences.
  - ``same_payload_pair_strategy()``: ``(tick, original, retry)``
    triples where ``retry == original`` (Predicate B' — idempotent).
  - ``different_payload_pair_strategy()``: ``(tick, original, retry)``
    triples where ``retry != original`` (Predicate B — raises).
"""

from __future__ import annotations

import copy

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy


def _payload_strategy() -> SearchStrategy[dict]:
    """A small payload dict with one distinguishing field."""
    return st.fixed_dictionaries(
        {
            "marker": st.text(min_size=1, max_size=10, alphabet="abcdef0123456789"),
            "value": st.integers(min_value=0, max_value=1000),
        }
    )


def multi_tick_sequence_strategy(
    *,
    n_ticks: int = 5,
) -> SearchStrategy[list[tuple[int, dict]]]:
    """Generate a list of ``(tick, payload)`` pairs of length ``n_ticks``.

    Ticks are ``[0, 1, ..., n_ticks-1]`` in order. Each payload is a
    small distinguishing dict so reads after any failed overwrite are
    unambiguous. Used by US4 Predicates A and C.

    Args:
        n_ticks: Number of consecutive ticks (default 5 per
            ``contracts/tick_persistence_monotonic.md``).

    Returns:
        Hypothesis strategy producing ``list[tuple[int, dict]]``.
    """

    @st.composite
    def _build(draw: st.DrawFn) -> list[tuple[int, dict]]:
        return [(N, draw(_payload_strategy())) for N in range(n_ticks)]

    return _build()


def same_payload_pair_strategy() -> SearchStrategy[tuple[int, dict, dict]]:
    """Generate ``(tick, original, retry)`` where ``retry == original``.

    Used by US4 Predicate B' (idempotent same-payload retry succeeds).
    The two dicts are deep-copies, so callers can mutate one without
    affecting equality with the other.
    """

    @st.composite
    def _build(draw: st.DrawFn) -> tuple[int, dict, dict]:
        tick = draw(st.integers(min_value=0, max_value=100))
        original = draw(_payload_strategy())
        retry = copy.deepcopy(original)
        return tick, original, retry

    return _build()


def different_payload_pair_strategy() -> SearchStrategy[tuple[int, dict, dict]]:
    """Generate ``(tick, original, retry)`` where ``retry != original``.

    Used by US4 Predicate B (different-payload re-persist raises).
    Hypothesis filters out any draw where the two payloads happen to
    coincide.
    """

    @st.composite
    def _build(draw: st.DrawFn) -> tuple[int, dict, dict]:
        tick = draw(st.integers(min_value=0, max_value=100))
        original = draw(_payload_strategy())
        retry = draw(_payload_strategy().filter(lambda p: p != original))
        return tick, original, retry

    return _build()
