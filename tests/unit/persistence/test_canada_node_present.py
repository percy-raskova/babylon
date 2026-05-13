"""Canada-node-present test (T072 / R4 / GATE-5).

Constitution IV.1 + R4 amendment: Canada MUST appear in the international
external node set. ``initialize_session`` is expected to instantiate it
alongside the other seven international regions and the rest_of_usa
domestic node.

This is the unit-level structural check. The companion integration test
verifies Postgres state after a real initialize_session call.
"""

from __future__ import annotations

import pytest

from babylon.persistence.postgres_initialization import (
    DOMESTIC_REST_NODE,
    INTERNATIONAL_NODES,
)


@pytest.mark.cross_scale
def test_canada_is_an_international_node() -> None:
    """R4 / GATE-5: Canada is a first-class international boundary."""
    assert "canada" in INTERNATIONAL_NODES


@pytest.mark.cross_scale
def test_eight_international_plus_one_domestic() -> None:
    """FR-036 amendment: 9 total external nodes."""
    all_nodes = set(INTERNATIONAL_NODES) | {DOMESTIC_REST_NODE}
    assert len(all_nodes) == 9


@pytest.mark.cross_scale
def test_no_canada_inside_rest_of_usa() -> None:
    """Canada is NOT modeled as part of rest_of_usa (Constitution IV.1)."""
    assert DOMESTIC_REST_NODE == "rest_of_usa"
    assert DOMESTIC_REST_NODE != "canada"
