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

from babylon.models.components.base import Component
from babylon.models.components.material import MaterialComponent
from babylon.models.components.material_conditions import MaterialConditionsBuffer
from babylon.models.components.organization import OrganizationComponent
from babylon.models.components.spatial import SpatialComponent
from babylon.models.components.vitality import VitalityComponent

__all__ = [
    "Component",
    "MaterialComponent",
    "VitalityComponent",
    "SpatialComponent",
    "MaterialConditionsBuffer",
    "OrganizationComponent",
]
