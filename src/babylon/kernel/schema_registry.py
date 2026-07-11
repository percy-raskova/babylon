"""Shared JSON Schema registry builder for ``$ref`` resolution.

Provides a single, directory-parameterized helper that walks a schemas
directory, loads every ``*.schema.json`` file, and assembles a
:class:`referencing.Registry` keyed by each schema's ``$id``. This registry
is what Draft 2020-12 validators consult to resolve ``$ref`` references
between schema files.

This helper was extracted from two byte-identical private copies
(``babylon.ai.persona_loader`` and
``babylon.engine.observers.schema_validator``) so both call sites share one
implementation. Each call site passes its own schemas directory.

See Also:
    :mod:`babylon.ai.persona_loader`: Persona loading call site.
    :mod:`babylon.engine.observers.schema_validator`: Observer-output call site.
"""

from __future__ import annotations

import json
import logging
from functools import cache
from pathlib import Path
from typing import Any

from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

__all__ = ["build_schema_registry"]

logger = logging.getLogger(__name__)


@cache
def build_schema_registry(schemas_dir: Path) -> Registry[Any]:
    """Build a schema registry for ``$ref`` resolution.

    Lazily loads all schemas from ``schemas_dir`` and caches the result. The
    cache is keyed on the directory argument, so each distinct schemas
    directory is scanned at most once per process.

    Args:
        schemas_dir: Directory tree to scan recursively for ``*.schema.json``
            files.

    Returns:
        Registry containing all loaded schemas for ``$ref`` resolution.
    """
    resources: list[tuple[str, Resource[Any]]] = []

    for schema_path in schemas_dir.rglob("*.schema.json"):
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
