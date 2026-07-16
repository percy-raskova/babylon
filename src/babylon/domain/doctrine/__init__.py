"""Doctrine Tree domain logic (Epoch 3, Wave 6).

Data foundation: loading, DAG-validity checking, and pure tag computation for the
MVP Doctrine Tree (3 trunks, 3 tags, 11 nodes; see
``ai/epochs/epoch3/doctrine-tree-mvp.yaml``). Plus the DoctrineSystem *mechanics*
(Unit 3, owner-ratified 2026-07-15): the safe :func:`evaluate_trap_condition`
trap evaluator. These are pure — the engine wiring lives in the DoctrineSystem
(``babylon.engine.systems``), not here.
"""

from __future__ import annotations

from babylon.domain.doctrine.loader import load_doctrine_tree
from babylon.domain.doctrine.mechanics import (
    DoctrineExpressionError,
    evaluate_trap_condition,
)
from babylon.domain.doctrine.tags import compute_tags, starting_tags
from babylon.domain.doctrine.validation import (
    DoctrineValidationError,
    validate_doctrine_tree,
)

__all__ = [
    "DoctrineExpressionError",
    "DoctrineValidationError",
    "compute_tags",
    "evaluate_trap_condition",
    "load_doctrine_tree",
    "starting_tags",
    "validate_doctrine_tree",
]
