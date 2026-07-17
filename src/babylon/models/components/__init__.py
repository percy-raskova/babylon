"""Component system for the Babylon Entity-Component architecture.

This package contains the foundational component types that define
the material ontology of the simulation:

- Component: Protocol defining the interface for all components
- MaterialComponent: Wealth, resources, means of production
- VitalityComponent: Population, subsistence needs
- SpatialComponent: Location, mobility
- MaterialConditionsBuffer: Value-tensor-derived consciousness inputs
- OrganizationComponent: Cohesion, cadre level

All components are immutable (frozen) Pydantic models that use
constrained types from babylon.models.types.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

from babylon.models.components.base import Component
from babylon.models.components.material import MaterialComponent
from babylon.models.components.material_conditions import MaterialConditionsBuffer
from babylon.models.components.spatial import SpatialComponent
from babylon.models.components.vitality import VitalityComponent

if TYPE_CHECKING:
    from babylon.models.components.organization import OrganizationComponent

__all__ = [
    "Component",
    "MaterialComponent",
    "VitalityComponent",
    "SpatialComponent",
    "MaterialConditionsBuffer",
    "OrganizationComponent",
]


def __getattr__(name: str) -> Any:
    """Lazy deprecation shim (PEP 562).

    ``OrganizationComponent`` is deprecated (Feature 031) but its eager
    re-export made EVERY ``import babylon.models`` trip the deprecation —
    which turned into a hard ImportError once first-party
    ``DeprecationWarning``s became errors (pyproject ``filterwarnings``).
    The warning must fire on USE, not on package import.
    """
    if name == "OrganizationComponent":
        warnings.warn(
            "OrganizationComponent is deprecated. Use "
            "babylon.models.entities.organization.Organization and its "
            "subtypes (StateApparatus, Business, PoliticalFaction, "
            "CivilSocietyOrg) instead. See Feature 031.",
            DeprecationWarning,
            stacklevel=2,
        )
        from babylon.models.components.organization import (
            OrganizationComponent as _OrganizationComponent,
        )

        return _OrganizationComponent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
