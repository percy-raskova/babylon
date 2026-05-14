"""FR-022 edge-hex boundary-mapping test (T031c).

For a hex at the study-area edge whose ``h3_to_county()`` mapping returns
no FIPS county, :func:`initialize_session` MUST associate it with the
appropriate boundary node (``rest_of_usa`` for non-international,
``canada`` for Windsor-side) and persist a hex_state row anchored to that
boundary. No hex may be silently dropped.

For the MVP, the initialization stub does not yet perform real hex
distribution (Phase 6 work). This test validates the contract surface:
the :class:`InitializationReport` carries the two boundary node IDs needed
for the fallback, and the spec module exposes the canonical mapping.
"""

from __future__ import annotations

import pytest

from babylon.persistence.postgres_initialization import (
    DOMESTIC_REST_NODE,
    INTERNATIONAL_NODES,
)


@pytest.mark.cross_scale
def test_rest_of_usa_is_canonical_domestic_fallback() -> None:
    """Per FR-022, non-international edge hexes route to rest_of_usa."""
    assert DOMESTIC_REST_NODE == "rest_of_usa"


@pytest.mark.cross_scale
def test_canada_is_first_class_international_node() -> None:
    """Per Constitution IV.1 + R4 amendment, Canada is in the international set."""
    assert "canada" in INTERNATIONAL_NODES


@pytest.mark.cross_scale
def test_no_partial_overlap_between_boundary_sets() -> None:
    """rest_of_usa and the international set are disjoint."""
    assert DOMESTIC_REST_NODE not in INTERNATIONAL_NODES


@pytest.mark.cross_scale
def test_eight_international_nodes_per_fr_036() -> None:
    """FR-036 amendment lists 8 international + 1 domestic_rest = 9 total."""
    assert len(INTERNATIONAL_NODES) == 8
    expected = {
        "canada",
        "china",
        "eu",
        "india",
        "sub_saharan_africa",
        "latin_america",
        "russia_csi",
        "southeast_asia",
    }
    assert set(INTERNATIONAL_NODES) == expected
