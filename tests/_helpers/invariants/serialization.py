"""JSON round-trip serialization helper — spec 060 US6(b) / FR-014.

Asserts that ``WorldState.model_dump_json()`` followed by
``WorldState.model_validate_json()`` produces a semantically-equal
state. Distinct from ``WorldState.to_graph() / from_graph()`` which
has documented exclusions (see CLAUDE.md "Graph Round-Trip Can Lose
Mutations").
"""

from __future__ import annotations

from pydantic import BaseModel


def roundtrip_via_json[M: BaseModel](world: M) -> M:
    """Serialize via ``model_dump_json`` then ``model_validate_json``.

    Args:
        world: Any Pydantic model instance.

    Returns:
        A new instance of the same class reconstructed from JSON.

    Raises:
        pydantic.ValidationError: If reconstruction fails — surfaces a
            serializer/deserializer asymmetry.
    """
    json_str = world.model_dump_json()
    return world.__class__.model_validate_json(json_str)


__all__ = ["roundtrip_via_json"]
