"""Property-based tests for the monotonic-idempotent persistence causal
invariant (INV-016 / spec-056 US4).

See ``specs/056-causal-invariants/contracts/tick_persistence_monotonic.md``
for the full predicate specification. Encodes Constitution II.6 (State is
Data), II.10 World Runtime, and III.7 Determinism (replay from any tick) —
once a tick is persisted, same-payload retries succeed (preserving
existing UPSERT-retry callers in persistence_observer + session_recorder)
and different-payload re-persists raise MonotonicityViolationError.

Four predicates:

  Predicate A — Sequential persists succeed (covers spec US4 AS3) (T024)
  Predicate B — Different-payload re-persist raises (covers AS1) (T025)
  Predicate B' — Same-payload re-persist succeeds idempotently (covers AS2) (T025)
  Predicate C — Back-in-time rewrite raises (covers AS4) (T026)

Parametrized over RuntimeDatabase (default fast gate) and PostgresRuntime
(integration only, T027).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import networkx as nx
import pytest
from hypothesis import HealthCheck, given, settings

from babylon.persistence import MonotonicityViolationError, RuntimeDatabase
from babylon.topology.graph import BabylonGraph
from tests.property.strategies.multi_tick_sequence import (
    different_payload_pair_strategy,
    multi_tick_sequence_strategy,
    same_payload_pair_strategy,
)


def _make_runtime_database() -> RuntimeDatabase:
    """Factory: fresh in-memory RuntimeDatabase per test parametrization."""
    return RuntimeDatabase(in_memory=True)


def _payload_to_graph(payload: dict) -> nx.DiGraph[str]:
    """Materialize a Hypothesis-generated payload dict as a one-node graph.

    The payload is stored as the single node's attributes — this gives
    persist_tick / hydrate_graph distinct round-trippable content per
    tick without depending on full WorldState semantics.
    """
    graph = BabylonGraph()
    graph.add_node("payload_node", type="Test", **payload)
    return graph


def _graph_payload(graph: nx.DiGraph) -> dict:
    """Extract the payload dict from a graph hydrated by hydrate_graph."""
    if "payload_node" not in graph.nodes:
        return {}
    attrs = dict(graph.nodes["payload_node"])
    # Strip the type marker we added in _payload_to_graph
    attrs.pop("type", None)
    return attrs


# Default-fast-gate parametrization: only RuntimeDatabase. PostgresRuntime
# is added under pytest.mark.integration in T027.
PERSISTENCE_FACTORIES: list[Any] = [
    pytest.param(_make_runtime_database, id="runtime_database"),
]


@pytest.mark.unit
class TestTickPersistenceMonotonic:
    """INV-016: monotonic-idempotent persist_tick contract."""

    @pytest.mark.parametrize("persistence_factory", PERSISTENCE_FACTORIES)
    @given(sequence=multi_tick_sequence_strategy(n_ticks=5))
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_sequential_persists_succeed(
        self,
        persistence_factory: Callable[[], Any],
        sequence: list[tuple[int, dict]],
    ) -> None:
        """Predicate A (covers AS3): 5 sequential persists + reads."""
        persistence = persistence_factory()
        try:
            for tick, payload in sequence:
                persistence.persist_tick(tick=tick, graph=_payload_to_graph(payload))

            for tick, expected_payload in sequence:
                hydrated = persistence.hydrate_graph(tick=tick)
                actual_payload = _graph_payload(hydrated)
                assert actual_payload == expected_payload, (
                    f"hydrate_graph(tick={tick}) returned {actual_payload!r}, "
                    f"expected {expected_payload!r}"
                )
        finally:
            persistence.close()

    @pytest.mark.parametrize("persistence_factory", PERSISTENCE_FACTORIES)
    @given(triple=different_payload_pair_strategy())
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_different_payload_re_persist_raises(
        self,
        persistence_factory: Callable[[], Any],
        triple: tuple[int, dict, dict],
    ) -> None:
        """Predicate B (covers AS1): different-payload re-persist raises
        MonotonicityViolationError, original payload survives."""
        tick, original, retry = triple
        assert original != retry, "strategy invariant violated"

        persistence = persistence_factory()
        try:
            persistence.persist_tick(tick=tick, graph=_payload_to_graph(original))

            with pytest.raises(MonotonicityViolationError) as exc_info:
                persistence.persist_tick(tick=tick, graph=_payload_to_graph(retry))

            assert exc_info.value.tick == tick

            # Original payload must survive the failed overwrite
            hydrated = persistence.hydrate_graph(tick=tick)
            assert _graph_payload(hydrated) == original, (
                "Original payload was corrupted by the failed overwrite — "
                "audit trail invariant violated"
            )
        finally:
            persistence.close()

    @pytest.mark.parametrize("persistence_factory", PERSISTENCE_FACTORIES)
    @given(triple=same_payload_pair_strategy())
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_same_payload_re_persist_idempotent(
        self,
        persistence_factory: Callable[[], Any],
        triple: tuple[int, dict, dict],
    ) -> None:
        """Predicate B' (covers AS2): same-payload re-persist succeeds
        idempotently — preserves observer/recorder retry semantics."""
        tick, original, retry = triple
        assert original == retry, "strategy invariant violated"

        persistence = persistence_factory()
        try:
            persistence.persist_tick(tick=tick, graph=_payload_to_graph(original))

            # Re-persist with IDENTICAL payload — no exception expected
            persistence.persist_tick(tick=tick, graph=_payload_to_graph(retry))

            hydrated = persistence.hydrate_graph(tick=tick)
            assert _graph_payload(hydrated) == original, (
                "Idempotent retry corrupted the payload — preservation guarantee violated"
            )
        finally:
            persistence.close()

    @pytest.mark.parametrize("persistence_factory", PERSISTENCE_FACTORIES)
    @given(
        sequence=multi_tick_sequence_strategy(n_ticks=5),
        rewrite_payload=different_payload_pair_strategy(),
    )
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_back_in_time_rewrite_raises(
        self,
        persistence_factory: Callable[[], Any],
        sequence: list[tuple[int, dict]],
        rewrite_payload: tuple[int, dict, dict],
    ) -> None:
        """Predicate C (covers AS4): back-in-time rewrite of an
        already-persisted earlier tick raises; all 5 records remain
        intact."""
        # Use the third element of rewrite_payload as the rewrite content;
        # discard the strategy's tick (we want the rewrite tick to be 2).
        _ignored_tick, _ignored_original, rewrite_content = rewrite_payload

        # Ensure the rewrite content differs from sequence[2]'s payload
        rewrite_target_tick = 2
        original_payload_at_target = sequence[rewrite_target_tick][1]
        if rewrite_content == original_payload_at_target:
            pytest.skip("rewrite_content happens to equal target payload — vacuous")

        persistence = persistence_factory()
        try:
            for tick, payload in sequence:
                persistence.persist_tick(tick=tick, graph=_payload_to_graph(payload))

            # Attempt back-in-time rewrite of tick 2
            with pytest.raises(MonotonicityViolationError) as exc_info:
                persistence.persist_tick(
                    tick=rewrite_target_tick,
                    graph=_payload_to_graph(rewrite_content),
                )
            assert exc_info.value.tick == rewrite_target_tick

            # ALL 5 records must remain intact
            for tick, expected_payload in sequence:
                hydrated = persistence.hydrate_graph(tick=tick)
                assert _graph_payload(hydrated) == expected_payload, (
                    f"Tick {tick}: failed-rewrite caused spurious side-effect on adjacent record"
                )
        finally:
            persistence.close()
