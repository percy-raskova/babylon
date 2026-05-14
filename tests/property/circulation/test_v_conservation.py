"""Property-based conservation test for Vol II Circulation (Spec 063 T011 / US1).

For 50 random pre-state v vectors over a fixed synthetic OD matrix, asserts
FR-010 conservation holds within 1e-9 × pre_total_v. Uses Hypothesis per
the spec-053..056 property-test convention.
"""

from __future__ import annotations

from uuid import uuid4

import networkx as nx
import numpy as np
import pytest
import scipy.sparse as sp
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from babylon.economics.boundary_flow_register import (
    BoundaryEdgeKind,
    BoundaryFlowRegister,
    NodeKind,
)
from babylon.economics.lodes_commute_matrix import LODESYearMatrix
from babylon.engine.systems.vol2_circulation import Vol2CirculationStep

pytestmark = [pytest.mark.math, pytest.mark.topology]


# A fixed 3-hex synthetic OD matrix with one out-of-area destination.
def _fixed_3hex_matrix() -> LODESYearMatrix:
    origins = ["hex_A", "hex_B", "hex_C"]
    dests = ["hex_A", "hex_B", "hex_C", "rest_of_usa"]
    # Synthetic worker counts:
    #   A → A: 40, A → B: 30, A → C: 20, A → ext: 10  (row_sum = 100)
    #   B → A: 10, B → B: 50, B → C: 30, B → ext:  0  (row_sum =  90)
    #   C → A:  0, C → B:  5, C → C: 95, C → ext:  0  (row_sum = 100)
    pairs = [
        (0, 0, 40.0),
        (0, 1, 30.0),
        (0, 2, 20.0),
        (0, 3, 10.0),
        (1, 0, 10.0),
        (1, 1, 50.0),
        (1, 2, 30.0),
        (2, 1, 5.0),
        (2, 2, 95.0),
    ]
    rows = np.array([p[0] for p in pairs], dtype=np.int32)
    cols = np.array([p[1] for p in pairs], dtype=np.int32)
    vals = np.array([p[2] for p in pairs], dtype=np.float64)
    matrix = sp.coo_matrix((vals, (rows, cols)), shape=(3, 4)).tocsr()
    row_sums = np.asarray(matrix.sum(axis=1)).ravel().astype(np.float64)
    return LODESYearMatrix(
        year=2010,
        matrix=matrix,
        origin_hex_to_row={h: i for i, h in enumerate(origins)},
        dest_to_col={d: i for i, d in enumerate(dests)},
        dest_kind_by_col=(NodeKind.HEX, NodeKind.HEX, NodeKind.HEX, NodeKind.EXTERNAL),
        dest_node_id_by_col=("hex_A", "hex_B", "hex_C", "rest_of_usa"),
        row_sums=row_sums,
    )


_MATRIX = _fixed_3hex_matrix()


class _StubLoader:
    def load_year(self, year: int) -> LODESYearMatrix:  # noqa: ARG002
        return _MATRIX


@given(
    v_vec=st.tuples(
        st.floats(min_value=0.0, max_value=1e8, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.0, max_value=1e8, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.0, max_value=1e8, allow_nan=False, allow_infinity=False),
    ),
)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_fr_010_conservation_holds_for_random_v_vectors(
    v_vec: tuple[float, float, float],
) -> None:
    """FR-010: sum(v_post) + sum(COMMUTE_OUT) == sum(v_pre) within tolerance.

    Hypothesis generates 50 random v-vectors over the fixed OD matrix and
    verifies conservation holds in every trial.
    """
    v_a, v_b, v_c = v_vec
    graph: nx.DiGraph[str] = nx.DiGraph()
    graph.add_node("hex_A", _node_type="hex", v=v_a)
    graph.add_node("hex_B", _node_type="hex", v=v_b)
    graph.add_node("hex_C", _node_type="hex", v=v_c)
    register = BoundaryFlowRegister()

    step = Vol2CirculationStep(od_loader=_StubLoader())  # type: ignore[arg-type]
    result = step.step(
        graph=graph,
        register=register,
        session_id=uuid4(),
        tick=1,
        simulated_year=2010,
    )

    pre_total = v_a + v_b + v_c
    post_total = sum(float(graph.nodes[n]["v"]) for n in ("hex_A", "hex_B", "hex_C"))
    boundary_total = sum(
        r.magnitude
        for r in register._buffer  # noqa: SLF001
        if r.flow_type == BoundaryEdgeKind.COMMUTE_OUT
    )
    tolerance = max(1e-9 * pre_total, 1e-9)
    assert abs(pre_total - (post_total + boundary_total)) <= tolerance, (
        f"FR-010 violated: pre={pre_total} post={post_total} boundary={boundary_total} "
        f"residual={pre_total - (post_total + boundary_total)} tol={tolerance}"
    )
    # Also assert the step's own residual reporting matches.
    assert result.conservation_residual <= tolerance
