"""FR-038 structural test (T077a).

Asserts via introspection that :class:`ExternalNode` Pydantic model has no
hex-substructure fields (``hexes``, ``hex_count``, ``h3_index``,
``internal_hexes``, or any field whose type names H3-indexing).

The spec mandates "reduced state representation, no internal hex structure"
at the boundary nodes. Enforcing it at the model layer rather than via
documentation keeps the constraint testable.
"""

from __future__ import annotations

import pytest

from babylon.persistence.external_node import ExternalNode

FORBIDDEN_FIELDS = {"hexes", "hex_count", "h3_index", "internal_hexes"}


@pytest.mark.cross_scale
def test_external_node_has_no_hex_fields() -> None:
    """No hex-substructure field name appears on ExternalNode."""
    fields = set(ExternalNode.model_fields)
    illegal = fields & FORBIDDEN_FIELDS
    assert not illegal, (
        f"FR-038 violated: ExternalNode declares hex-substructure fields: "
        f"{sorted(illegal)}. Boundary nodes carry country-aggregate state only."
    )


@pytest.mark.cross_scale
def test_external_node_no_h3_typed_field() -> None:
    """No field declares an H3-typed annotation either."""
    for name, info in ExternalNode.model_fields.items():
        annotation = info.annotation
        annotation_str = repr(annotation).lower()
        assert "h3" not in annotation_str, (
            f"FR-038 violated: field {name!r} declares H3-typed annotation "
            f"{annotation!r}; boundary nodes carry no hex substructure."
        )
