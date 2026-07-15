"""Doctrine Tree JSON loader (Phase 0 foundation).

Reads the canonical MVP tree data file
(``babylon/data/game/doctrine_tree_mvp.json``, itself a faithful
transcription of ``ai/epochs/epoch3/doctrine-tree-mvp.yaml``), constructs
the frozen :class:`~babylon.models.entities.doctrine.DoctrineTree` /
:class:`~babylon.models.entities.doctrine.DoctrineNode` models, and runs
structural validation before returning.
"""

from __future__ import annotations

import json
from pathlib import Path

from babylon.domain.doctrine.validation import validate_doctrine_tree
from babylon.models.entities.doctrine import DoctrineNode, DoctrineTree

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "game"
_DEFAULT_TREE_PATH = _DATA_DIR / "doctrine_tree_mvp.json"


def load_doctrine_tree(path: Path | None = None) -> DoctrineTree:
    """Load, construct, and validate the Doctrine Tree from JSON.

    Args:
        path: Optional override for the JSON file path; defaults to the
            in-package ``doctrine_tree_mvp.json``.

    Returns:
        A validated :class:`~babylon.models.entities.doctrine.DoctrineTree`.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        pydantic.ValidationError: If any node record violates the
            :class:`~babylon.models.entities.doctrine.DoctrineNode` /
            :class:`~babylon.models.entities.doctrine.DoctrineTree` schema
            (e.g. an unknown ``trunk`` string, a negative ``cost_tl``).
        babylon.domain.doctrine.validation.DoctrineValidationError: If the
            constructed tree is schema-valid but structurally broken (a
            cycle, multiple roots, a trap missing ``trap_condition``, ...).
    """
    if path is None:
        path = _DEFAULT_TREE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    nodes = {record["id"]: DoctrineNode.model_validate(record) for record in payload["nodes"]}
    tree = DoctrineTree(nodes=nodes, root_id=payload["root_id"])
    validate_doctrine_tree(tree)
    return tree


__all__ = [
    "load_doctrine_tree",
]
