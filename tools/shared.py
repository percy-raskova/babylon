#!/usr/bin/env python3
"""Shared helpers for retained Python regression tooling (ADR036)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from babylon.models.types import EntityProtocol


def is_dead(entity: EntityProtocol | None) -> bool:
    """Return whether an entity is absent or inactive.

    Raw values are rejected so regression tooling cannot silently substitute a
    wealth threshold for the governed vitality state.
    """

    if entity is None:
        return True
    if not isinstance(entity, EntityProtocol):
        raise TypeError(f"is_dead() requires EntityProtocol, got {type(entity).__name__}")
    return not entity.active


__all__ = ["is_dead"]
