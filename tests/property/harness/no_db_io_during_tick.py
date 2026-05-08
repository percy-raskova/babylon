"""no_db_io_during_tick — context manager patching every DB-bearing
``ServiceContainer`` field for spec-056 US3.

Per research.md §4: introspect ``dataclasses.fields(services)`` and
identify DB-bearing fields by declared type or attribute-name regex
``(?i).*(database|persistence|runtime|store).*``. Each non-None
DB-bearing field is replaced with a sentinel object whose
``__getattr__`` raises ``DBIONotPermittedError`` on any access.

Restores originals on exit (including the exception path).

Constitution alignment: II.6 verbatim ("No DB I/O during tick"); the
patched scope is exactly the ``SimulationEngine.run_tick`` boundary
(per the 2026-05-07 Q3 clarification — hydration + persistence happen
outside the patched scope).
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from babylon.engine.services import ServiceContainer


_DB_BEARING_NAME_PATTERN = re.compile(r".*(database|persistence|runtime|store).*", re.IGNORECASE)


class DBIONotPermittedError(Exception):
    """Raised when a System touches a patched DB-bearing surface inside
    the ``no_db_io_during_tick`` scope.

    Per Constitution II.6, ``engine.run_tick`` operates over an
    in-memory graph; intra-tick I/O is non-determinism by another name.
    Spec 056 US3 enforces this as a property test.
    """

    def __init__(self, surface: str, attribute: str) -> None:
        self.surface = surface
        self.attribute = attribute
        super().__init__(
            f"DB I/O is forbidden during tick execution: "
            f"attempted access to services.{surface}.{attribute} "
            f"(spec-056 US3 / Constitution II.6)"
        )


class _DBIOSentinel:
    """Stand-in for a DB-bearing service inside the patched scope.

    Every attribute access raises ``DBIONotPermittedError`` naming the
    surface and attribute. Used by :func:`no_db_io_during_tick`.
    """

    def __init__(self, surface_name: str) -> None:
        # Use object.__setattr__ to avoid triggering our own __setattr__
        object.__setattr__(self, "_surface_name", surface_name)

    def __getattr__(self, attr: str) -> Any:
        # __getattr__ only fires for missing attrs; this catches every
        # access from System code that expected the original service.
        raise DBIONotPermittedError(
            surface=object.__getattribute__(self, "_surface_name"),
            attribute=attr,
        )

    def __repr__(self) -> str:
        return f"_DBIOSentinel({object.__getattribute__(self, '_surface_name')!r})"


@contextmanager
def no_db_io_during_tick(services: ServiceContainer) -> Iterator[None]:
    """Patch every DB-bearing field on ``services`` to raise on access,
    yield, then restore originals.

    DB-bearing detection (research.md §4):
      - Any field whose declared type name matches the regex
        ``(?i).*(database|persistence|runtime|store).*``
      - Any field whose attribute name matches the same regex
      - Any field whose runtime type's name matches the same regex
        (catches duck-typed ``Any`` fields like ``persistence``)

    Skipped (in-memory, no I/O risk):
      - ``metrics``, ``event_bus``, ``formula_registry``, ``config``

    Yields:
        None. Inside the with-block, any System that touches a patched
        field via attribute access raises ``DBIONotPermittedError``.

    Example::

        with no_db_io_during_tick(services):
            engine.run_tick(graph, services, context)
    """
    # Build the set of fields to patch
    field_specs: list[tuple[str, Any]] = []
    for f in dataclasses.fields(services):  # type: ignore[arg-type]
        if not _is_db_bearing_field(services, f):
            continue
        original = getattr(services, f.name)
        if original is None:
            continue  # nothing to patch
        field_specs.append((f.name, original))

    # Patch all in one pass; restore in reverse on exit
    try:
        for name, _original in field_specs:
            object.__setattr__(services, name, _DBIOSentinel(name))
        yield
    finally:
        for name, original in field_specs:
            object.__setattr__(services, name, original)


def _is_db_bearing_field(
    services: ServiceContainer,
    field: dataclasses.Field[Any],
) -> bool:
    """Predicate: should this dataclass field be patched?"""
    # Name regex match
    if _DB_BEARING_NAME_PATTERN.match(field.name):
        return True
    # Declared type regex match (when available as a string)
    type_str = field.type if isinstance(field.type, str) else getattr(field.type, "__name__", "")
    if isinstance(type_str, str) and _DB_BEARING_NAME_PATTERN.match(type_str):
        return True
    # Runtime type regex match (catches Any-typed fields like `persistence`)
    value = getattr(services, field.name, None)
    if value is not None:
        runtime_type_name = type(value).__name__
        if _DB_BEARING_NAME_PATTERN.match(runtime_type_name):
            return True
    return False
