"""Helper coercion utilities for enum types.

Spec 058: extracted from the historical ``babylon.models.enums`` monolith. The :func:`resolve_edge_type` helper consumes :class:`EdgeType` from :mod:`babylon.models.enums.topology`.
"""

from __future__ import annotations

from babylon.models.enums.topology import EdgeType


def resolve_edge_type(raw: str | EdgeType | None) -> EdgeType | None:
    """Coerce a raw edge type value (str or enum) to EdgeType.

    Args:
        raw: String value, EdgeType instance, or None.

    Returns:
        EdgeType enum or None if input is None.
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        return EdgeType(raw)
    return raw


__all__ = ["resolve_edge_type"]
