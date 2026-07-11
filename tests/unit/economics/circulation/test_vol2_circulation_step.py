"""Contract tests for Vol2CirculationStep (Spec 063 T010 + T012 / US1).

Builds a tiny synthetic 2-hex graph + LODESYearMatrix, runs one step, and
asserts FR-009 formula, FR-010 conservation, FR-011 zero-row-sum guard,
FR-013 industry-mixing invariant, and FR-030a paired emission.

No on-disk LODES or Postgres dependency — fully in-memory.
"""

from __future__ import annotations

from uuid import uuid4

import networkx as nx
import numpy as np
import pytest
import scipy.sparse as sp

from babylon.domain.economics.boundary_flow_register import (
    BoundaryEdgeKind,
    BoundaryFlowRegister,
    NodeKind,
)
from babylon.domain.economics.lodes_commute_matrix import LODESYearMatrix
from babylon.engine.systems.vol2_circulation import (
    Vol2CirculationStep,
)
from babylon.topology.graph import BabylonGraph

pytestmark = [pytest.mark.unit, pytest.mark.topology]


class _StubLoader:
    """Returns a pre-built LODESYearMatrix without touching the disk."""

    def __init__(self, year_matrix: LODESYearMatrix) -> None:
        self._yr = year_matrix

    def load_year(self, year: int) -> LODESYearMatrix:  # noqa: ARG002
        return self._yr


def _build_2hex_matrix(
    *,
    a_to_a: float,
    a_to_b: float,
    b_to_a: float,
    b_to_b: float,
    a_to_canada: float = 0.0,
) -> LODESYearMatrix:
    """Build a 2-hex (A, B) LODES year matrix with explicit OD weights."""
    origins = ["hex_A", "hex_B"]
    dests = ["hex_A", "hex_B"]
    if a_to_canada > 0:
        dests.append("rest_of_usa")
    n_o = len(origins)
    n_d = len(dests)
    rows: list[int] = []
    cols: list[int] = []
    vals: list[float] = []
    for r, origin in enumerate(origins):
        for c, dest in enumerate(dests):
            v = 0.0
            if origin == "hex_A" and dest == "hex_A":
                v = a_to_a
            elif origin == "hex_A" and dest == "hex_B":
                v = a_to_b
            elif origin == "hex_A" and dest == "rest_of_usa":
                v = a_to_canada
            elif origin == "hex_B" and dest == "hex_A":
                v = b_to_a
            elif origin == "hex_B" and dest == "hex_B":
                v = b_to_b
            if v > 0:
                rows.append(r)
                cols.append(c)
                vals.append(v)
    matrix = sp.coo_matrix(
        (np.asarray(vals, dtype=np.float64), (np.asarray(rows), np.asarray(cols))),
        shape=(n_o, n_d),
    ).tocsr()
    row_sums = np.asarray(matrix.sum(axis=1)).ravel().astype(np.float64)
    dest_kinds: list[NodeKind] = []
    for dest in dests:
        dest_kinds.append(NodeKind.HEX if dest.startswith("hex_") else NodeKind.EXTERNAL)
    return LODESYearMatrix(
        year=2010,
        matrix=matrix,
        origin_hex_to_row={origin: i for i, origin in enumerate(origins)},
        dest_to_col={dest: i for i, dest in enumerate(dests)},
        dest_kind_by_col=tuple(dest_kinds),
        dest_node_id_by_col=tuple(dests),
        row_sums=row_sums,
    )


def _build_2hex_graph(v_a: float, v_b: float) -> nx.DiGraph[str]:
    g = BabylonGraph()
    g.add_node("hex_A", _node_type="hex", v=v_a)
    g.add_node("hex_B", _node_type="hex", v=v_b)
    return g


def _new_step(year_matrix: LODESYearMatrix) -> Vol2CirculationStep:
    return Vol2CirculationStep(od_loader=_StubLoader(year_matrix))  # type: ignore[arg-type]


def test_in_area_circulation_redistributes_v_per_fr_009() -> None:
    """FR-009: v[A, t+1] = sum_j(OD[j, A] * v[j, t] / row_sum[j]).

    Scenario: 30 workers A→B, 70 workers A→A (all stay), and B has zero out-flow.
    Pre-state: v_A = 1000, v_B = 0.
    Expected: v_A_post = 0.7 * 1000 = 700; v_B_post = 0.3 * 1000 = 300.
    """
    matrix = _build_2hex_matrix(a_to_a=70, a_to_b=30, b_to_a=0, b_to_b=0)
    step = _new_step(matrix)
    graph = _build_2hex_graph(v_a=1000.0, v_b=0.0)
    register = BoundaryFlowRegister()

    result = step.step(
        graph=graph,
        register=register,
        session_id=uuid4(),
        tick=1,
        simulated_year=2010,
    )

    assert graph.nodes["hex_A"]["v"] == pytest.approx(700.0, rel=1e-9)
    assert graph.nodes["hex_B"]["v"] == pytest.approx(300.0, rel=1e-9)
    # FR-010: full conservation (no boundary out → all v stays in-area)
    assert result.boundary_out_total_v == 0.0
    assert result.conservation_residual < 1e-9


def test_fr_010_conservation_holds_with_boundary_exit() -> None:
    """FR-010: total in-area v + COMMUTE_OUT magnitudes == pre v.

    Scenario: A has 100 in-area workers (50 → A, 50 → B) and 50 to rest_of_usa.
    Pre v_A = $1500; row_sum_A = 150; share-out = 50/150 = 1/3.
    Expected boundary_out = 1500/3 = 500; v_A_post = 1500*50/150 = 500;
    v_B_post = 1500*50/150 = 500. Sum = 500 + 500 + 500 = 1500. ✓
    """
    matrix = _build_2hex_matrix(a_to_a=50, a_to_b=50, b_to_a=0, b_to_b=0, a_to_canada=50)
    step = _new_step(matrix)
    graph = _build_2hex_graph(v_a=1500.0, v_b=0.0)
    register = BoundaryFlowRegister()

    result = step.step(
        graph=graph,
        register=register,
        session_id=uuid4(),
        tick=1,
        simulated_year=2010,
    )

    assert result.boundary_out_total_v == pytest.approx(500.0, rel=1e-9)
    assert graph.nodes["hex_A"]["v"] == pytest.approx(500.0, rel=1e-9)
    assert graph.nodes["hex_B"]["v"] == pytest.approx(500.0, rel=1e-9)
    pre = 1500.0
    post_in_area = 500.0 + 500.0
    boundary = 500.0
    assert post_in_area + boundary == pytest.approx(pre, rel=1e-9)


def test_fr_011_zero_row_sum_origin_carries_forward_unchanged() -> None:
    """FR-011: origin hex with row_sum == 0 carries forward unchanged; no boundary rows."""
    # B has no out-flow (row_sum_B == 0). A has all-domestic out.
    matrix = _build_2hex_matrix(a_to_a=70, a_to_b=30, b_to_a=0, b_to_b=0)
    step = _new_step(matrix)
    graph = _build_2hex_graph(v_a=0.0, v_b=500.0)
    register = BoundaryFlowRegister()

    step.step(
        graph=graph,
        register=register,
        session_id=uuid4(),
        tick=1,
        simulated_year=2010,
    )

    # B's pre-state v should carry forward exactly (zero divide-by-zero, zero leak)
    assert graph.nodes["hex_B"]["v"] == pytest.approx(500.0, rel=1e-9)
    # No COMMUTE_OUT rows emitted because no boundary-bound flow originates anywhere
    boundary_rows = [r for r in register._buffer if r.flow_type == BoundaryEdgeKind.COMMUTE_OUT]  # noqa: SLF001
    assert boundary_rows == []


def test_fr_030a_paired_trade_edge_emitted_for_every_commute_out() -> None:
    """FR-030a: every COMMUTE_OUT row has a paired TRADE_EDGE inbound row."""
    matrix = _build_2hex_matrix(a_to_a=70, a_to_b=0, b_to_a=0, b_to_b=0, a_to_canada=30)
    step = _new_step(matrix)
    graph = _build_2hex_graph(v_a=1000.0, v_b=0.0)
    register = BoundaryFlowRegister()

    step.step(
        graph=graph,
        register=register,
        session_id=uuid4(),
        tick=1,
        simulated_year=2010,
    )

    out_rows = [r for r in register._buffer if r.flow_type == BoundaryEdgeKind.COMMUTE_OUT]  # noqa: SLF001
    in_rows = [r for r in register._buffer if r.flow_type == BoundaryEdgeKind.TRADE_EDGE]  # noqa: SLF001
    assert len(out_rows) == 1
    assert len(in_rows) == 1
    out = out_rows[0]
    paired = in_rows[0]
    # Paired row swaps source/dest and carries equal magnitude
    assert paired.source_node_id == out.dest_node_id
    assert paired.dest_node_id == out.source_node_id
    assert paired.source_kind == NodeKind.EXTERNAL
    assert paired.dest_kind == NodeKind.HEX
    assert paired.magnitude == pytest.approx(out.magnitude, rel=1e-12)


def test_fr_013_no_industry_breakdown_persists_on_post_step_graph() -> None:
    """FR-013: Vol II Circulation MUST NOT introduce per-industry breakdown.

    After step(), hex nodes must carry hex-aggregated v only — no v_naics_*,
    no per-industry fields. Spec 062 FR-031 derive-on-read pattern inheritance.
    """
    matrix = _build_2hex_matrix(a_to_a=50, a_to_b=50, b_to_a=0, b_to_b=0)
    step = _new_step(matrix)
    graph = _build_2hex_graph(v_a=1000.0, v_b=0.0)
    register = BoundaryFlowRegister()

    step.step(
        graph=graph,
        register=register,
        session_id=uuid4(),
        tick=1,
        simulated_year=2010,
    )

    for hex_id in ("hex_A", "hex_B"):
        attrs = dict(graph.nodes[hex_id])
        # Only the hex-aggregated 'v' field should exist; no per-industry slot.
        per_industry_keys = [k for k in attrs if k.startswith("v_naics_") or "by_industry" in k]
        assert per_industry_keys == [], f"FR-013 violated on {hex_id}: {per_industry_keys}"


def test_fr_014_determinism_repeated_step_bit_identical() -> None:
    """FR-014: identical pre-state + matrix → bit-identical post-state + rows."""
    matrix = _build_2hex_matrix(a_to_a=30, a_to_b=40, b_to_a=10, b_to_b=20, a_to_canada=10)

    def run_once() -> tuple[dict[str, float], list[tuple[str, str, str, float]]]:
        step = _new_step(matrix)
        graph = _build_2hex_graph(v_a=1000.0, v_b=2000.0)
        register = BoundaryFlowRegister()
        step.step(
            graph=graph,
            register=register,
            session_id=uuid4(),  # session_id varies but does NOT affect math
            tick=1,
            simulated_year=2010,
        )
        v_state = {n: float(graph.nodes[n]["v"]) for n in ("hex_A", "hex_B")}
        rows = sorted(
            (r.source_node_id, r.dest_node_id, r.flow_type.value, r.magnitude)
            for r in register._buffer  # noqa: SLF001
        )
        return v_state, rows

    a, b = run_once(), run_once()
    assert a == b
