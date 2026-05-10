"""Scenario ABC + auto-registry — ADR-006.1 / Spec 059 US4.

Lifts the implicit "scenario builder" contract that 6 free functions duplicate
into an abstract base class with auto-registry via ``__init_subclass__``.
Existing free-function names are preserved as thin shims in this package's
``__init__.py``.

Usage::

    class MyScenario(Scenario):
        name = "my_scenario"
        description = "Brief description"

        def build(self) -> tuple[WorldState, SimulationConfig, GameDefines]:
            # ... assemble territories, classes, relationships, return tuple
            ...

The subclass auto-registers via ``__init_subclass__``; no manual registry
edit is required. Lookup via ``_SCENARIO_REGISTRY[name]``.

For the 6 historical builders, subclasses delegate ``build()`` to the
free-function implementations in ``_legacy.py`` / ``_legacy_wayne.py`` to
preserve byte-equality with the pre-Bundle-2 baseline (SC-007).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from babylon.config.defines import GameDefines
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState


# Module-private registry: name → Scenario subclass.
_SCENARIO_REGISTRY: dict[str, type[Scenario]] = {}


class Scenario(ABC):
    """Abstract base for scenario builders.

    Subclasses MUST set ``name`` (ClassVar str) and ``description`` (ClassVar
    str), and implement :meth:`build`. They auto-register via
    :meth:`__init_subclass__`.

    Optional ``build_territories`` / ``build_classes`` / ``build_relationships``
    methods are provided for the new-style composition pattern; subclasses MAY
    use them with a custom ``build()`` that calls them, or override ``build()``
    directly (the pattern used by Bundle 2's port of the 6 legacy builders).
    """

    name: ClassVar[str]
    description: ClassVar[str] = ""

    @abstractmethod
    def build(self, *args: Any, **kwargs: Any) -> tuple[WorldState, SimulationConfig, GameDefines]:
        """Build the scenario and return ``(state, config, defines)``."""

    def build_territories(self) -> dict[str, Any]:
        """Optional: territory builder for composition pattern."""
        raise NotImplementedError("Override build() OR implement build_territories")

    def build_classes(self) -> dict[str, Any]:
        """Optional: social-class builder for composition pattern."""
        raise NotImplementedError("Override build() OR implement build_classes")

    def build_relationships(self) -> dict[str, Any]:
        """Optional: relationship builder for composition pattern."""
        raise NotImplementedError("Override build() OR implement build_relationships")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Auto-register subclass in ``_SCENARIO_REGISTRY`` keyed on ``cls.name``.

        Raises:
            ValueError: When two subclasses share the same ``name`` (collision
                detection at import time, per US4 acceptance #2).
        """
        super().__init_subclass__(**kwargs)
        name = getattr(cls, "name", None)
        if name is None:
            return  # subclass declared no name yet (may be intermediate)
        if name in _SCENARIO_REGISTRY and _SCENARIO_REGISTRY[name] is not cls:
            raise ValueError(
                f"Scenario name collision: '{name}' already registered for "
                f"{_SCENARIO_REGISTRY[name].__name__}; cannot register {cls.__name__}"
            )
        _SCENARIO_REGISTRY[name] = cls


def get_scenario(name: str) -> type[Scenario]:
    """Look up a Scenario subclass by name."""
    return _SCENARIO_REGISTRY[name]


def list_scenarios() -> list[str]:
    """Return the names of all registered scenarios, sorted."""
    return sorted(_SCENARIO_REGISTRY.keys())
