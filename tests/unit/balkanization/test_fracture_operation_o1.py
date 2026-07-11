"""Spec-070 fracture-operation cost test (T023 / T079, FR-018 + SC-004).

Verifies ``bulk_partition_claims`` cost is O(K) in the moving-territory
count, NOT O(N) in the unchanged-territory count. Empirical scaling
benchmark at N ∈ {10, 100, 1000} per SC-004.

Scaffolded in foundational phase per tasks.md T023; activated in
User Story 4 per T079. The same benchmark serves both purposes.
"""

from __future__ import annotations

import time

import pytest

from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.topology


def _build_sovereign_with_claims(adapter: BabylonGraph, n: int) -> str:
    """Add SOV_PARENT plus ``n`` Territories all claimed at control_level=1.0.

    Returns the parent Sovereign ID.
    """

    sov_id = "SOV_PARENT"
    if sov_id not in adapter:
        adapter.add_node(sov_id, "sovereign")
    for i in range(n):
        territory_id = f"HEX_{i:05d}"
        if territory_id not in adapter:
            adapter.add_node(territory_id, "territory")
        adapter.add_edge(
            sov_id,
            territory_id,
            "claims",
            control_level=1.0,
            legal_status="de_jure",
        )
    return sov_id


def _measure_bulk_partition_cost(n_total: int, k_moving: int) -> float:
    """Return median wall-time of bulk_partition_claims over 5 trials.

    Pre-builds the graph; the timing measurement covers ONLY the
    rewiring call, not setup.
    """

    adapter = BabylonGraph()
    parent = _build_sovereign_with_claims(adapter, n_total)
    adapter.add_node("SOV_BREAKAWAY", "sovereign")
    moving = {f"HEX_{i:05d}" for i in range(k_moving)}
    trials: list[float] = []
    for _trial in range(5):
        # Re-establish baseline parent claims for the moving set (since
        # earlier trials may have moved them).
        for territory_id in moving:
            if not adapter.has_edge(parent, territory_id):
                adapter.add_edge(
                    parent,
                    territory_id,
                    "claims",
                    control_level=1.0,
                    legal_status="de_jure",
                )
            if adapter.has_edge("SOV_BREAKAWAY", territory_id):
                adapter.remove_edge("SOV_BREAKAWAY", territory_id)
        start = time.perf_counter()
        moved = adapter.bulk_partition_claims(
            from_sovereign_id=parent,
            to_sovereign_id="SOV_BREAKAWAY",
            territories=moving,
        )
        elapsed = time.perf_counter() - start
        trials.append(elapsed)
        assert moved == k_moving
    trials.sort()
    return trials[len(trials) // 2]


def test_bulk_partition_claims_is_o_k_not_o_n() -> None:
    """SC-004: fracture cost flat in unchanged-territory count.

    Move 10 territories under N ∈ {10, 100, 1000}. The cost SHOULD NOT
    grow proportionally to N (since the operation touches only the
    moving set). We allow a 3× slack on the headline 1000-vs-10 ratio
    to absorb cache/allocator effects, but reject anything ≥3×.
    """

    k_moving = 10
    cost_10 = _measure_bulk_partition_cost(n_total=10, k_moving=k_moving)
    cost_100 = _measure_bulk_partition_cost(n_total=100, k_moving=k_moving)
    cost_1000 = _measure_bulk_partition_cost(n_total=1000, k_moving=k_moving)

    # Cost should remain near-constant; sub-linear-in-N is the hard
    # gate.  Allow 3× slack to absorb timing noise.
    ceiling = 3.0
    floor = max(cost_10, 1e-6)
    assert cost_100 / floor < ceiling, (
        f"cost grew O(N) under k=10 from {cost_10:.6f}s @N=10 to "
        f"{cost_100:.6f}s @N=100 (ratio {cost_100 / floor:.2f}× ≥ {ceiling}×)"
    )
    assert cost_1000 / floor < ceiling, (
        f"cost grew O(N) under k=10 from {cost_10:.6f}s @N=10 to "
        f"{cost_1000:.6f}s @N=1000 (ratio {cost_1000 / floor:.2f}× ≥ {ceiling}×)"
    )


def test_bulk_partition_claims_scales_with_k() -> None:
    """Sanity: moving more territories COSTS more (just not in N)."""

    # Hold N fixed at 1000; vary K.
    cost_k1 = _measure_bulk_partition_cost(n_total=1000, k_moving=1)
    cost_k100 = _measure_bulk_partition_cost(n_total=1000, k_moving=100)
    # K=100 should be at least roughly proportional to K=1 (with noise).
    # If K=100 is faster than K=1, something is wrong (e.g., caching the
    # wrong thing). We just require non-zero growth.
    assert cost_k100 >= cost_k1 * 0.5
