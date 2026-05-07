"""WorldState strategy that exercises Probability-typed fields (spec-054 US1).

The base ``worldstate_strategy()`` already populates every Probability field
on ``SocialClass`` (and via ``Relationship`` strategy on every SOLIDARITY
edge) with valid floats drawn from ``[0, 1]``. This strategy is a thin
wrapper that ensures ``min_entities >= 1`` so the discovered Probability
field set is always exercised by at least one entity.

Per ``research.md §7`` the WorldState scale defaults to small (≤ 4 entities,
≤ 3 territories) for the bound suite — falsification quality saturates well
below ``N=200`` because bound violations almost always shrink to a
single-entity counterexample.
"""

from __future__ import annotations

from hypothesis.strategies import SearchStrategy

from babylon.models.world_state import WorldState

from .worldstate import worldstate_strategy


def worldstate_with_probability_fields_strategy() -> SearchStrategy[WorldState]:
    """Generate a WorldState whose entities collectively populate every
    Probability-typed field discovered by the harness.

    Guarantees ``len(entities) >= 1`` so the Probability checks always have
    something to assert against. Returns the base ``worldstate_strategy()``
    output otherwise.

    Returns:
        Hypothesis ``SearchStrategy[WorldState]``.
    """
    return worldstate_strategy(min_entities=1)


__all__ = ["worldstate_with_probability_fields_strategy"]
