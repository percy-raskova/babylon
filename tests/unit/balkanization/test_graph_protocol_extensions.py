"""Spec-070 GraphProtocol extensions test (T020).

Covers all 6 new methods documented in
``contracts/graph_protocol_extensions.md``:

1. ``query_faction_influence_by_territory``
2. ``query_sovereign_claims``
3. ``query_territory_claims``
4. ``query_adjacent_territories``
5. ``bulk_partition_claims``
6. ``query_contiguous_component_under_predicate``

Each method is tested for type signature + determinism guarantees.
"""

from __future__ import annotations

import pytest

from babylon.engine.graph import BabylonGraph
from babylon.engine.graph_protocol import GraphProtocol

pytestmark = pytest.mark.topology


@pytest.fixture
def adapter_with_influences() -> BabylonGraph:
    adapter = BabylonGraph()
    adapter.add_node("HEX_001", "territory")
    adapter.add_node("FAC_A", "balkanization_faction")
    adapter.add_node("FAC_B", "balkanization_faction")
    adapter.add_node("FAC_C", "balkanization_faction")
    adapter.add_edge(
        "FAC_A",
        "HEX_001",
        "influences",
        influence_level=0.6,
        support_type="electoral",
    )
    adapter.add_edge(
        "FAC_B",
        "HEX_001",
        "influences",
        influence_level=0.9,
        support_type="labor",
    )
    adapter.add_edge(
        "FAC_C",
        "HEX_001",
        "influences",
        influence_level=0.3,
        support_type="ideological",
    )
    return adapter


@pytest.fixture
def adapter_with_claims() -> BabylonGraph:
    adapter = BabylonGraph()
    adapter.add_node("SOV_USA", "sovereign")
    adapter.add_node("SOV_DETROIT", "sovereign")
    adapter.add_node("HEX_001", "territory")
    adapter.add_node("HEX_002", "territory")
    adapter.add_node("HEX_003", "territory")
    adapter.add_edge(
        "SOV_USA",
        "HEX_001",
        "claims",
        control_level=1.0,
        legal_status="de_jure",
    )
    adapter.add_edge(
        "SOV_USA",
        "HEX_002",
        "claims",
        control_level=0.8,
        legal_status="de_facto",
    )
    adapter.add_edge(
        "SOV_DETROIT",
        "HEX_002",
        "claims",
        control_level=0.5,
        legal_status="disputed",
    )
    adapter.add_edge(
        "SOV_USA",
        "HEX_003",
        "claims",
        control_level=0.9,
        legal_status="de_jure",
    )
    return adapter


@pytest.fixture
def adjacency_grid() -> BabylonGraph:
    """3-hex strip: HEX_A — HEX_B — HEX_C plus isolated HEX_D."""

    adapter = BabylonGraph()
    for hex_id in ("HEX_A", "HEX_B", "HEX_C", "HEX_D"):
        adapter.add_node(hex_id, "territory")
    adapter.add_edge("HEX_A", "HEX_B", "adjacency")
    adapter.add_edge("HEX_B", "HEX_A", "adjacency")
    adapter.add_edge("HEX_B", "HEX_C", "adjacency")
    adapter.add_edge("HEX_C", "HEX_B", "adjacency")
    return adapter


def test_adapter_satisfies_protocol() -> None:
    adapter = BabylonGraph()
    assert isinstance(adapter, GraphProtocol)


def test_query_faction_influence_returns_three_tuples_sorted_desc(
    adapter_with_influences: BabylonGraph,
) -> None:
    rows = adapter_with_influences.query_faction_influence_by_territory("HEX_001")
    assert rows == [
        ("FAC_B", 0.9, "labor"),
        ("FAC_A", 0.6, "electoral"),
        ("FAC_C", 0.3, "ideological"),
    ]


def test_query_faction_influence_empty_for_unknown_territory(
    adapter_with_influences: BabylonGraph,
) -> None:
    assert adapter_with_influences.query_faction_influence_by_territory("NOPE") == []


def test_query_sovereign_claims_sorted_desc_by_control(
    adapter_with_claims: BabylonGraph,
) -> None:
    rows = adapter_with_claims.query_sovereign_claims("SOV_USA")
    assert rows == [
        ("HEX_001", 1.0, "de_jure"),
        ("HEX_003", 0.9, "de_jure"),
        ("HEX_002", 0.8, "de_facto"),
    ]


def test_query_territory_claims_returns_all_claimants_sorted(
    adapter_with_claims: BabylonGraph,
) -> None:
    rows = adapter_with_claims.query_territory_claims("HEX_002")
    assert rows == [
        ("SOV_USA", 0.8, "de_facto"),
        ("SOV_DETROIT", 0.5, "disputed"),
    ]


def test_query_adjacent_territories_bidirectional_sorted(
    adjacency_grid: BabylonGraph,
) -> None:
    assert adjacency_grid.query_adjacent_territories("HEX_B") == ["HEX_A", "HEX_C"]
    assert adjacency_grid.query_adjacent_territories("HEX_A") == ["HEX_B"]
    assert adjacency_grid.query_adjacent_territories("HEX_D") == []


def test_bulk_partition_claims_rewires_only_specified_territories(
    adapter_with_claims: BabylonGraph,
) -> None:
    adapter_with_claims.add_node("SOV_NEW", "sovereign")
    moved = adapter_with_claims.bulk_partition_claims(
        from_sovereign_id="SOV_USA",
        to_sovereign_id="SOV_NEW",
        territories={"HEX_001", "HEX_003"},
    )
    assert moved == 2
    # SOV_USA only retains HEX_002 (its other DE_FACTO claim).
    usa_claims = adapter_with_claims.query_sovereign_claims("SOV_USA")
    assert {row[0] for row in usa_claims} == {"HEX_002"}
    new_claims = adapter_with_claims.query_sovereign_claims("SOV_NEW")
    assert {row[0] for row in new_claims} == {"HEX_001", "HEX_003"}
    # Legal status preserved post-rewire.
    statuses = {row[0]: row[2] for row in new_claims}
    assert statuses == {"HEX_001": "de_jure", "HEX_003": "de_jure"}


def test_bulk_partition_claims_ignores_non_claim_territories(
    adapter_with_claims: BabylonGraph,
) -> None:
    adapter_with_claims.add_node("SOV_NEW", "sovereign")
    adapter_with_claims.add_node("HEX_999", "territory")  # not claimed
    moved = adapter_with_claims.bulk_partition_claims(
        from_sovereign_id="SOV_USA",
        to_sovereign_id="SOV_NEW",
        territories={"HEX_001", "HEX_999"},
    )
    assert moved == 1


def test_contiguous_component_walks_predicate_satisfying_neighbors(
    adjacency_grid: BabylonGraph,
) -> None:
    component = adjacency_grid.query_contiguous_component_under_predicate(
        territory_seed="HEX_A",
        predicate=lambda _t: True,
    )
    assert component == {"HEX_A", "HEX_B", "HEX_C"}


def test_contiguous_component_respects_predicate_failure(
    adjacency_grid: BabylonGraph,
) -> None:
    component = adjacency_grid.query_contiguous_component_under_predicate(
        territory_seed="HEX_A",
        predicate=lambda t: t != "HEX_B",
    )
    # HEX_B fails predicate so the BFS cannot cross from HEX_A to HEX_C.
    assert component == {"HEX_A"}


def test_contiguous_component_empty_when_seed_fails_predicate(
    adjacency_grid: BabylonGraph,
) -> None:
    component = adjacency_grid.query_contiguous_component_under_predicate(
        territory_seed="HEX_A",
        predicate=lambda _t: False,
    )
    assert component == set()
