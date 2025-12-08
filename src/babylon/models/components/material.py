"""MaterialComponent - Material conditions of an entity.

MaterialComponent represents the material conditions of an entity in the
Babylon simulation. It tracks economic resources (wealth), available
material resources, and control over the means of production.

This is the fundamental component for the Material Ontology in the
Entity-Component architecture.
"""

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.types import Currency, Probability


class MaterialComponent(BaseModel):
    """Material conditions of an entity.

    Tracks the economic and material state of an entity including:
    - Accumulated wealth (Currency)
    - Available resources (Currency)
    - Control over means of production (Probability)

    All values use constrained types for automatic validation:
    - wealth, resources: Currency [0, inf)
    - means_of_production: Probability [0, 1]

    This component is immutable (frozen) to ensure state integrity.

    Attributes:
        wealth: Accumulated economic resources (default: 10.0)
        resources: Available material resources (default: 0.0)
        means_of_production: Control over productive apparatus [0, 1] (default: 0.0)
    """

    model_config = ConfigDict(frozen=True)

    wealth: Currency = Field(
        default=10.0,
        description="Accumulated economic resources",
    )
    resources: Currency = Field(
        default=0.0,
        description="Available material resources",
    )
    means_of_production: Probability = Field(
        default=0.0,
        description="Control over the means of production [0=none, 1=full]",
    )

    @property
    def component_type(self) -> str:
        """Return the component type identifier.

        Returns:
            The string 'material' identifying this component type.
        """
        return "material"
