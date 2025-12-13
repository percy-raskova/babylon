"""Persona loader with JSON Schema validation (Sprint 4.2).

This module provides functions to load and validate persona JSON files
against the persona.schema.json definition.

Follows the pattern established in schema_validator.py for the observer layer.

Usage:
    >>> from babylon.ai.persona_loader import load_persona, load_default_persona
    >>>
    >>> # Load specific persona
    >>> percy = load_persona(Path("path/to/persona.json"))
    >>>
    >>> # Load default persona (Percy Raskova)
    >>> default = load_default_persona()

See Also:
    :class:`babylon.ai.persona.Persona`: The Pydantic model for personas.
    :mod:`babylon.engine.observers.schema_validator`: Pattern reference.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from babylon.ai.persona import Persona, VoiceConfig

logger = logging.getLogger(__name__)

# Constants
_SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"
_PERSONA_SCHEMA_PATH = _SCHEMAS_DIR / "entities" / "persona.schema.json"

PERSONAS_DIR = Path(__file__).parent.parent / "data" / "game" / "personas"
DEFAULT_PERSONA_PATH = PERSONAS_DIR / "persephone_raskova.json"


class PersonaLoadError(Exception):
    """Error raised when persona loading fails.

    Attributes:
        path: Path to the persona file that failed to load.
        errors: List of validation error messages (if validation failed).
    """

    def __init__(
        self,
        message: str,
        path: Path,
        errors: list[str] | None = None,
    ) -> None:
        """Initialize PersonaLoadError.

        Args:
            message: Human-readable error message.
            path: Path to the persona file.
            errors: List of validation error messages.
        """
        super().__init__(message)
        self.path = path
        self.errors = errors or []


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
def _get_persona_validator() -> Draft202012Validator:
    """Get a cached validator for Persona schema.

    Returns:
        Validator instance with registry for $ref resolution.

    Raises:
        FileNotFoundError: If the schema file doesn't exist.
        json.JSONDecodeError: If the schema is malformed.
    """
    with open(_PERSONA_SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)

    registry = _load_schema_registry()
    return Draft202012Validator(schema, registry=registry)


def _validate_persona_data(data: dict[str, Any]) -> list[str]:
    """Validate persona data against JSON Schema.

    Args:
        data: Parsed JSON data to validate.

    Returns:
        List of validation error messages. Empty list if valid.
    """
    validator = _get_persona_validator()
    errors: list[str] = []

    for error in validator.iter_errors(data):
        error_path = " -> ".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"{error_path}: {error.message}")

    return errors


def load_persona(path: Path) -> Persona:
    """Load and validate a persona from a JSON file.

    Args:
        path: Path to the persona JSON file.

    Returns:
        Validated Persona instance.

    Raises:
        PersonaLoadError: If file doesn't exist, JSON is invalid,
            or schema validation fails.

    Example:
        >>> from pathlib import Path
        >>> from babylon.ai.persona_loader import load_persona
        >>> persona = load_persona(Path("path/to/persona.json"))
        >>> persona.name
        "Persephone 'Percy' Raskova"
    """
    # Check file exists
    if not path.exists():
        raise PersonaLoadError(
            f"Persona file not found: {path}",
            path=path,
        )

    # Parse JSON
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise PersonaLoadError(
            f"Invalid JSON in persona file: {e}",
            path=path,
        ) from e

    # Validate against schema
    errors = _validate_persona_data(data)
    if errors:
        raise PersonaLoadError(
            f"Schema validation failed for {path}: {errors}",
            path=path,
            errors=errors,
        )

    # Construct Pydantic model
    voice = VoiceConfig(
        tone=data["voice"]["tone"],
        style=data["voice"]["style"],
        address_user_as=data["voice"]["address_user_as"],
    )

    return Persona(
        id=data["id"],
        name=data["name"],
        role=data["role"],
        voice=voice,
        obsessions=data["obsessions"],
        directives=data["directives"],
        restrictions=data.get("restrictions", []),
    )


def load_default_persona() -> Persona:
    """Load the default persona (Persephone 'Percy' Raskova).

    Returns:
        The default Persona instance.

    Raises:
        PersonaLoadError: If the default persona file is missing or invalid.

    Example:
        >>> from babylon.ai.persona_loader import load_default_persona
        >>> percy = load_default_persona()
        >>> percy.id
        'persephone_raskova'
    """
    return load_persona(DEFAULT_PERSONA_PATH)
