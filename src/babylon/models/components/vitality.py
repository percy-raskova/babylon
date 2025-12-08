"""VitalityComponent - Population and survival needs of an entity.

VitalityComponent represents the population and basic survival requirements
of an entity in the Babylon simulation. It tracks the size of the population
and the resources needed for subsistence.

This component is essential for the survival calculus in the simulation.
"""

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.types import Currency


class VitalityComponent(BaseModel):
    """Population and survival needs of an entity.

    Tracks the demographic and subsistence state of an entity:
    - Population size (Currency)
    - Minimum resources required for survival (Currency)

    All values use constrained types for automatic validation:
    - population, subsistence_needs: Currency [0, inf)

    This component is immutable (frozen) to ensure state integrity.

    Attributes:
        population: Size of the population (default: 1.0)
        subsistence_needs: Resources needed for survival (default: 5.0)
    """

    model_config = ConfigDict(frozen=True)

    population: Currency = Field(
        default=1.0,
        description="Size of the population",
    )
    subsistence_needs: Currency = Field(
        default=5.0,
        description="Minimum resources required for survival",
    )

    @property
    def component_type(self) -> str:
        """Return the component type identifier.

        Returns:
            The string 'vitality' identifying this component type.
        """
        return "vitality"
