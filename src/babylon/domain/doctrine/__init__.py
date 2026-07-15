"""Doctrine Tree domain logic (Epoch 3, Wave 6 foundation — Phase 0).

Data-foundation layer only: loading, DAG-validity checking, and pure tag
computation for the MVP Doctrine Tree (3 trunks, 3 tags, 11 nodes; see
``ai/epochs/epoch3/doctrine-tree-mvp.yaml``). Deliberately excludes any
engine wiring — no ``DoctrineSystem``, no OODA verb, no tick integration,
no trap-condition evaluator, no auto-acquisition side effects. Those
depend on owner rulings and are out of scope for this layer.
"""

from __future__ import annotations

from babylon.domain.doctrine.loader import load_doctrine_tree
from babylon.domain.doctrine.tags import compute_tags, starting_tags
from babylon.domain.doctrine.validation import (
    DoctrineValidationError,
    validate_doctrine_tree,
)

__all__ = [
    "DoctrineValidationError",
    "compute_tags",
    "load_doctrine_tree",
    "starting_tags",
    "validate_doctrine_tree",
]
