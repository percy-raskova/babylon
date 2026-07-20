"""Feature-020 extension: national_financial gets save-side observability only.

qa-modernization E3-pre (descoped 2026-07-20): ``_save_graph_context`` persists
``graph.graph["national_financial"]`` into ``persistent_context["_national_financial"]``
whenever the Vol III financial layer stamped it that tick, so the qa harness and
the gate-coverage-truth probe can read it out of ``persistent_context``. There is
deliberately NO restore side — see ``_save_graph_context``'s docstring in
``babylon.engine.simulation_engine`` for why re-stamping the graph attr changes
live tick-N engine dynamics (MarketScissorsSystem/ContradictionSystem), which is
an owner-gated Vol III design question, not something this observability-only
task decides.
"""

from __future__ import annotations

import pytest

from babylon.engine.simulation_engine import _save_graph_context
from babylon.topology import BabylonGraph

pytestmark = pytest.mark.unit


def test_national_financial_saves_into_context() -> None:
    graph = BabylonGraph()
    payload = {"endogenous_interest": {"rate": 0.019855, "profit_rate_ceiling": 0.0597}}
    graph.graph["national_financial"] = payload
    context: dict = {}
    _save_graph_context(graph, context, tick=1)
    assert context["_national_financial"] == payload


def test_national_financial_persists_in_context_across_absent_saves() -> None:
    """Once saved, the value survives later saves where the graph attr is absent.

    A fresh per-tick graph (post ``WorldState`` round-trip) never carries
    ``national_financial`` except on the tick the financial layer just
    stamped it — ``_save_graph_context`` must not clear the previously
    saved value just because the current tick's graph doesn't have it.
    """
    graph = BabylonGraph()
    payload = {"endogenous_interest": {"rate": 0.019855, "profit_rate_ceiling": 0.0597}}
    graph.graph["national_financial"] = payload
    context: dict = {}
    _save_graph_context(graph, context, tick=1)
    assert context["_national_financial"] == payload

    fresh = BabylonGraph()
    _save_graph_context(fresh, context, tick=2)
    assert context["_national_financial"] == payload


def test_absent_attr_is_not_invented() -> None:
    graph = BabylonGraph()
    context: dict = {}
    _save_graph_context(graph, context, tick=1)
    assert "_national_financial" not in context
