"""Boundary register hex-pair dimensional fields (T073 / FR-040 / R2)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from babylon.domain.economics.boundary_flow_register import (
    BoundaryEdgeKind,
    BoundaryFlowRegister,
    BoundaryFlowRegisterRow,
    NodeKind,
)


@pytest.mark.cross_scale
class TestBoundaryFlowRegisterRowSchema:
    """R2: hex/county/state/national/external on either end."""

    def _row(self, **overrides: object) -> BoundaryFlowRegisterRow:
        defaults: dict[str, object] = {
            "session_id": uuid4(),
            "tick": 0,
            "source_node_id": "872d34a89ffffff",
            "source_kind": NodeKind.HEX,
            "dest_node_id": "canada",
            "dest_kind": NodeKind.EXTERNAL,
            "flow_type": BoundaryEdgeKind.COMMUTE_OUT,
            "magnitude": 12.4,
        }
        defaults.update(overrides)
        return BoundaryFlowRegisterRow(**defaults)  # type: ignore[arg-type]

    def test_hex_to_external_pair_accepted(self) -> None:
        row = self._row()
        assert row.source_kind is NodeKind.HEX
        assert row.dest_kind is NodeKind.EXTERNAL

    def test_external_to_county_drain(self) -> None:
        row = self._row(
            source_node_id="china",
            source_kind=NodeKind.EXTERNAL,
            dest_node_id="26163",
            dest_kind=NodeKind.COUNTY,
            flow_type=BoundaryEdgeKind.DRAIN_EDGE,
        )
        assert row.source_kind is NodeKind.EXTERNAL
        assert row.dest_kind is NodeKind.COUNTY
        assert row.flow_type is BoundaryEdgeKind.DRAIN_EDGE

    def test_hex_to_hex_pair_accepted(self) -> None:
        row = self._row(
            dest_node_id="872d34b0bffffff",
            dest_kind=NodeKind.HEX,
            flow_type=BoundaryEdgeKind.COMMUTE_OUT,
        )
        assert row.source_kind is NodeKind.HEX
        assert row.dest_kind is NodeKind.HEX

    def test_county_to_external_for_trade_edge(self) -> None:
        row = self._row(
            source_node_id="26163",
            source_kind=NodeKind.COUNTY,
            dest_node_id="canada",
            dest_kind=NodeKind.EXTERNAL,
            flow_type=BoundaryEdgeKind.TRADE_EDGE,
        )
        assert row.flow_type is BoundaryEdgeKind.TRADE_EDGE

    def test_magnitude_is_signed(self) -> None:
        row_neg = self._row(magnitude=-1.0)
        assert row_neg.magnitude == -1.0


@pytest.mark.cross_scale
class TestBoundaryFlowRegisterFacade:
    """In-memory buffer + query path."""

    def test_record_and_flush(self) -> None:
        reg = BoundaryFlowRegister()
        sid = uuid4()
        reg.record(
            session_id=sid,
            tick=0,
            source_node_id="872d34a89ffffff",
            source_kind=NodeKind.HEX,
            dest_node_id="canada",
            dest_kind=NodeKind.EXTERNAL,
            flow_type=BoundaryEdgeKind.COMMUTE_OUT,
            magnitude=5.0,
        )
        assert reg.buffered_count() == 1
        flushed = reg.flush()
        assert len(flushed) == 1
        assert reg.buffered_count() == 0

    def test_query_filters_by_flow_type(self) -> None:
        reg = BoundaryFlowRegister()
        sid = uuid4()
        reg.record(
            session_id=sid,
            tick=0,
            source_node_id="china",
            source_kind=NodeKind.EXTERNAL,
            dest_node_id="26163",
            dest_kind=NodeKind.COUNTY,
            flow_type=BoundaryEdgeKind.DRAIN_EDGE,
            magnitude=100.0,
        )
        reg.record(
            session_id=sid,
            tick=0,
            source_node_id="872d34a89ffffff",
            source_kind=NodeKind.HEX,
            dest_node_id="canada",
            dest_kind=NodeKind.EXTERNAL,
            flow_type=BoundaryEdgeKind.COMMUTE_OUT,
            magnitude=12.4,
        )
        drains = reg.query(flow_type=BoundaryEdgeKind.DRAIN_EDGE)
        assert len(drains) == 1
        assert drains[0].dest_node_id == "26163"
