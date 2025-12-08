"""SpatialComponent - Location and mobility of an entity.

SpatialComponent represents the spatial position and movement capability
of an entity in the Babylon simulation. It tracks the geographic or
topological location and the ability to relocate.

This component enables modeling of migration, geographic constraints,
and spatial relationships in the world system.
"""

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.types import Probability


class SpatialComponent(BaseModel):
    """Location and mobility of an entity.

    Tracks the spatial state of an entity:
    - Geographic/topological location identifier (string)
    - Ability to relocate (Probability)

    All numeric values use constrained types for automatic validation:
    - mobility: Probability [0, 1]

    This component is immutable (frozen) to ensure state integrity.

    Attributes:
        location_id: Geographic or topological location identifier (default: "")
        mobility: Ability to relocate [0=immobile, 1=fully mobile] (default: 0.5)
    """

    model_config = ConfigDict(frozen=True)

    location_id: str = Field(
        default="",
        description="Geographic or topological location identifier",
    )
    mobility: Probability = Field(
        default=0.5,
        description="Ability to relocate [0=immobile, 1=fully mobile]",
    )

    @property
    def component_type(self) -> str:
        """Return the component type identifier.

        Returns:
            The string 'spatial' identifying this component type.
        """
        return "spatial"
