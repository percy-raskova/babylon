"""Vol2CirculationStep + CrossBorderCommuteClassifier integration (Spec 063 T032 / US3).

Asserts that when a classifier is wired into the step, COMMUTE_OUT rows
emit dest_node_id='canada' for Canadian-coded synthetic destinations
(per FR-023 / FR-027 emission-time classification).
"""

from __future__ import annotations

from uuid import uuid4

import numpy as np
import pytest
import scipy.sparse as sp

from babylon.economics.boundary_flow_register import (
    BoundaryEdgeKind,
    BoundaryFlowRegister,
    NodeKind,
)
from babylon.economics.lodes_commute_matrix import LODESYearMatrix
from babylon.engine.graph import BabylonGraph
from babylon.engine.systems.cross_border_commute import CrossBorderCommuteClassifier
from babylon.engine.systems.vol2_circulation import Vol2CirculationStep

pytestmark = [pytest.mark.unit]


def _make_classifier(hex_id: str) -> CrossBorderCommuteClassifier:
    return CrossBorderCommuteClassifier(
        study_area_hexes=frozenset([hex_id]),
        study_area_states=frozenset(["26"]),
        domestic_states=frozenset(
            [f"{n:02d}" for n in range(1, 57) if n not in (3, 7, 14, 43, 52)]
            + ["60", "66", "69", "72", "78"]
        ),
    )


def _matrix_with_two_external_dests() -> LODESYearMatrix:
    """A 1-hex matrix routing 50% to a 'Canadian' block (state 99) and 50% to Toledo (state 39)."""
    # Loader pre-resolves all out-of-area to 'rest_of_usa', but for this test
    # we simulate the case where the classifier reclassifies at emission time
    # by storing two distinct external dest IDs: the Toledo block code and a
    # synthetic Canadian-coded block.
    rows = np.array([0, 0], dtype=np.int32)
    cols = np.array([0, 1], dtype=np.int32)
    vals = np.array([50.0, 50.0], dtype=np.float64)
    matrix = sp.coo_matrix((vals, (rows, cols)), shape=(1, 2)).tocsr()
    row_sums = np.asarray(matrix.sum(axis=1)).ravel().astype(np.float64)
    return LODESYearMatrix(
        year=2010,
        matrix=matrix,
        origin_hex_to_row={"hex_origin": 0},
        dest_to_col={"390951234567890": 0, "990001234567890": 1},
        dest_kind_by_col=(NodeKind.EXTERNAL, NodeKind.EXTERNAL),
        dest_node_id_by_col=("390951234567890", "990001234567890"),
        row_sums=row_sums,
    )


class _StubLoader:
    def __init__(self, matrix: LODESYearMatrix) -> None:
        self._m = matrix

    def load_year(self, _year: int) -> LODESYearMatrix:
        return self._m


def test_classifier_reclassifies_canadian_block_to_canada_dest() -> None:
    """FR-023/027: emission-time classifier routes 99-prefixed blocks to canada."""
    matrix = _matrix_with_two_external_dests()
    classifier = _make_classifier("hex_origin")
    step = Vol2CirculationStep(
        od_loader=_StubLoader(matrix),  # type: ignore[arg-type]
        classifier=classifier,
    )
    graph = BabylonGraph()
    graph.add_node("hex_origin", _node_type="hex", v=1000.0)
    register = BoundaryFlowRegister()

    step.step(
        graph=graph,
        register=register,
        session_id=uuid4(),
        tick=1,
        simulated_year=2010,
    )

    out_rows = [r for r in register._buffer if r.flow_type == BoundaryEdgeKind.COMMUTE_OUT]  # noqa: SLF001
    dest_ids = {r.dest_node_id for r in out_rows}
    # Classifier should split the two external dests:
    #   - Toledo (39 prefix) → rest_of_usa
    #   - Synthetic 99 prefix → canada
    assert "canada" in dest_ids
    assert "rest_of_usa" in dest_ids
    # Each external destination produces one COMMUTE_OUT row → 2 rows total.
    assert len(out_rows) == 2


def test_no_classifier_keeps_loader_provided_dest_id() -> None:
    """Back-compat: without a classifier, dest_id flows through unchanged from the matrix."""
    matrix = _matrix_with_two_external_dests()
    step = Vol2CirculationStep(od_loader=_StubLoader(matrix))  # type: ignore[arg-type]
    graph = BabylonGraph()
    graph.add_node("hex_origin", _node_type="hex", v=1000.0)
    register = BoundaryFlowRegister()

    step.step(
        graph=graph,
        register=register,
        session_id=uuid4(),
        tick=1,
        simulated_year=2010,
    )

    out_rows = [r for r in register._buffer if r.flow_type == BoundaryEdgeKind.COMMUTE_OUT]  # noqa: SLF001
    dest_ids = {r.dest_node_id for r in out_rows}
    # No classifier → raw dest_id from the matrix flows through.
    assert "390951234567890" in dest_ids
    assert "990001234567890" in dest_ids


def test_paired_trade_edge_uses_classified_dest_id() -> None:
    """FR-030a: paired TRADE_EDGE row has source = classifier-resolved dest."""
    matrix = _matrix_with_two_external_dests()
    classifier = _make_classifier("hex_origin")
    step = Vol2CirculationStep(
        od_loader=_StubLoader(matrix),  # type: ignore[arg-type]
        classifier=classifier,
    )
    graph = BabylonGraph()
    graph.add_node("hex_origin", _node_type="hex", v=1000.0)
    register = BoundaryFlowRegister()

    step.step(
        graph=graph,
        register=register,
        session_id=uuid4(),
        tick=1,
        simulated_year=2010,
    )

    # Every COMMUTE_OUT has a paired TRADE_EDGE with swapped source/dest
    # and the same (classifier-resolved) external node id.
    out_rows = [r for r in register._buffer if r.flow_type == BoundaryEdgeKind.COMMUTE_OUT]  # noqa: SLF001
    in_rows = [r for r in register._buffer if r.flow_type == BoundaryEdgeKind.TRADE_EDGE]  # noqa: SLF001
    out_ids = sorted(r.dest_node_id for r in out_rows)
    in_ids = sorted(r.source_node_id for r in in_rows)
    assert out_ids == in_ids
