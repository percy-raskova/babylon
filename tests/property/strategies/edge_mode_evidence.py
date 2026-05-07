"""Hypothesis strategies for synthesized edge-mode evidence events (spec-055 US1).

Two strategies that drive the synthesized branch of US1's trajectory test:

  - ``evidence_event_strategy()`` → a single evidence-event payload as a dict
    that can be written directly to a graph node's ``contradiction_fields[…]``
    or ``field_derivatives[…][…]`` attributes (per research §2).
  - ``edge_mode_trajectory_strategy()`` → a tuple ``(starting_mode, events)``
    where ``starting_mode`` is uniformly drawn from the 5 ``EdgeMode``
    enum values and ``events`` is a list of length 10–20 (FR-003 lower
    bound + F5 widened upper bound).
"""

from __future__ import annotations

from typing import Any

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from babylon.models.enums import EdgeMode

# Predicate space pulled from edge_transition.py's PredicateCondition fields.
_FIELDS = ("exploitation", "imperial_rent", "immiseration")
_METRICS = ("value", "df_dt", "d2f_dt2", "laplacian")
_SCOPES = ("source", "target")


def evidence_event_strategy() -> SearchStrategy[dict[str, Any]]:
    """Return a Hypothesis strategy producing a single evidence-event payload.

    Each event is a dict with keys ``field``, ``metric``, ``value``,
    ``scope``. Tests apply the event by writing into the appropriate
    graph-node attribute dict.

    Returns:
        Strategy producing dicts compatible with
        ``_apply_event_to_graph(graph, event)`` in
        ``test_edge_mode_trajectory.py``.
    """
    return st.fixed_dictionaries(
        {
            "field": st.sampled_from(_FIELDS),
            "metric": st.sampled_from(_METRICS),
            "value": st.floats(
                min_value=-10.0,
                max_value=10.0,
                allow_nan=False,
                allow_infinity=False,
            ),
            "scope": st.sampled_from(_SCOPES),
        }
    )


def edge_mode_trajectory_strategy() -> SearchStrategy[tuple[EdgeMode, list[dict[str, Any]]]]:
    """Return a Hypothesis strategy producing a (starting_mode, events) tuple.

    The trajectory is exactly what US1's synthesized predicate consumes:
    a starting ``EdgeMode`` value plus a sequence of evidence events to
    apply between consecutive ``EdgeTransitionSystem.step`` invocations.

    Returns:
        Strategy producing tuples ``(EdgeMode, list[dict])`` where
        ``len(events) in [10, 20]`` per FR-003 + F5.
    """
    return st.tuples(
        st.sampled_from(list(EdgeMode)),
        st.lists(evidence_event_strategy(), min_size=10, max_size=20),
    )


__all__ = ["edge_mode_trajectory_strategy", "evidence_event_strategy"]
