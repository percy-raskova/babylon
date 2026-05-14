"""Frozen-model and FR-038 structural test for :class:`ExternalNode` (T022)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from babylon.persistence.external_node import ExternalNode, ExternalNodeKind


def _valid_kwargs() -> dict[str, object]:
    return {
        "session_id": uuid4(),
        "tick": 0,
        "node_id": "canada",
        "kind": ExternalNodeKind.INTERNATIONAL,
        "phi_year_inflow": 1_000_000.0,
        "bilateral_trade_value": 5_000_000.0,
        "bilateral_trade_tons": 200.0,
        "erdi_ratio": 1.5,
    }


@pytest.mark.cross_scale
class TestExternalNodeModel:
    def test_valid_construction(self) -> None:
        node = ExternalNode(**_valid_kwargs())
        assert node.node_id == "canada"
        assert node.kind is ExternalNodeKind.INTERNATIONAL

    def test_is_frozen(self) -> None:
        node = ExternalNode(**_valid_kwargs())
        with pytest.raises(ValidationError):
            node.tick = 1  # type: ignore[misc]

    def test_phi_inflow_non_negative(self) -> None:
        kw = _valid_kwargs()
        kw["phi_year_inflow"] = -1.0
        with pytest.raises(ValidationError):
            ExternalNode(**kw)

    def test_erdi_ratio_strictly_positive(self) -> None:
        kw = _valid_kwargs()
        kw["erdi_ratio"] = 0.0
        with pytest.raises(ValidationError):
            ExternalNode(**kw)

    def test_kind_enum_constrained(self) -> None:
        kw = _valid_kwargs()
        kw["kind"] = "outer_space"
        with pytest.raises(ValidationError):
            ExternalNode(**kw)


@pytest.mark.cross_scale
class TestExternalNodeKindEnum:
    def test_international_value(self) -> None:
        assert ExternalNodeKind.INTERNATIONAL == "international"

    def test_domestic_rest_value(self) -> None:
        assert ExternalNodeKind.DOMESTIC_REST == "domestic_rest"

    def test_exhaustive(self) -> None:
        # FR-036: nine nodes total = 8 international + 1 domestic_rest.
        assert {k.value for k in ExternalNodeKind} == {
            "international",
            "domestic_rest",
        }
