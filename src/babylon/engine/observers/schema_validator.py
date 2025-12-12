"""JSON Schema validation for observer outputs (Sprint 3.2).

Provides schema validation for NarrativeFrame and other observer JSON outputs.
Uses Draft 2020-12 JSON Schema with referencing registry for $ref resolution.

Usage::

    from babylon.engine.observers.schema_validator import validate_narrative_frame

    frame = {"pattern": "SHOCK_DOCTRINE", "causal_graph": {...}}
    errors = validate_narrative_frame(frame)
    if errors:
        for error in errors:
            print(f"Validation error: {error}")
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)

# Schema paths
_SCHEMAS_DIR = Path(__file__).parent.parent.parent / "schemas"
_NARRATIVE_SCHEMA_PATH = _SCHEMAS_DIR / "narrative" / "narrative_frame.schema.json"


@lru_cache(maxsize=1)
def _load_schema_registry() -> Registry[Any]:
    """Build a schema registry for $ref resolution.

    Lazily loads all schemas from the schemas directory and caches the result.

    Returns:
        Registry containing all loaded schemas for $ref resolution.
    """
    resources: list[tuple[str, Resource[Any]]] = []

    for schema_path in _SCHEMAS_DIR.rglob("*.schema.json"):
        try:
            with open(schema_path, encoding="utf-8") as f:
                schema = json.load(f)
            schema_id = schema.get("$id")
            if schema_id:
                resource: Resource[Any] = Resource.from_contents(
                    schema, default_specification=DRAFT202012
                )
                resources.append((schema_id, resource))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to load schema %s: %s", schema_path, e)

    return Registry().with_resources(resources)


@lru_cache(maxsize=1)
def _get_narrative_frame_validator() -> Draft202012Validator:
    """Get a cached validator for NarrativeFrame schema.

    Returns:
        Validator instance with registry for $ref resolution.

    Raises:
        FileNotFoundError: If the schema file doesn't exist.
        json.JSONDecodeError: If the schema is malformed.
    """
    with open(_NARRATIVE_SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)

    registry = _load_schema_registry()
    return Draft202012Validator(schema, registry=registry)


def validate_narrative_frame(frame: dict[str, Any]) -> list[str]:
    """Validate a NarrativeFrame against the JSON schema.

    Args:
        frame: Dictionary representing the NarrativeFrame to validate.

    Returns:
        List of validation error messages. Empty list if valid.

    Example:
        >>> frame = {"pattern": "TEST", "causal_graph": {"nodes": [], "edges": []}}
        >>> errors = validate_narrative_frame(frame)
        >>> # Returns errors because nodes must have minItems: 1
    """
    validator = _get_narrative_frame_validator()
    errors: list[str] = []

    for error in validator.iter_errors(frame):
        path = " -> ".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"{path}: {error.message}")

    return errors


def is_valid_narrative_frame(frame: dict[str, Any]) -> bool:
    """Check if a NarrativeFrame is valid against the JSON schema.

    Convenience method that returns a boolean instead of error list.

    Args:
        frame: Dictionary representing the NarrativeFrame to validate.

    Returns:
        True if valid, False otherwise.

    Example:
        >>> frame = {
        ...     "pattern": "SHOCK_DOCTRINE",
        ...     "causal_graph": {
        ...         "nodes": [{"id": "n1", "type": "ECONOMIC_SHOCK", "tick": 0}],
        ...         "edges": []
        ...     }
        ... }
        >>> is_valid_narrative_frame(frame)
        True
    """
    return len(validate_narrative_frame(frame)) == 0


def iter_validation_errors(frame: dict[str, Any]) -> Iterator[str]:
    """Iterate over validation errors for a NarrativeFrame.

    Generator version of validate_narrative_frame for memory efficiency
    when processing many frames.

    Args:
        frame: Dictionary representing the NarrativeFrame to validate.

    Yields:
        Validation error messages.
    """
    validator = _get_narrative_frame_validator()
    for error in validator.iter_errors(frame):
        path = " -> ".join(str(p) for p in error.absolute_path) or "(root)"
        yield f"{path}: {error.message}"
