"""OrganizationComponent - Organizational capacity of an entity.

OrganizationComponent represents the organizational state of an entity in the
Babylon simulation. It tracks internal unity/coordination (cohesion) and the
quality of organizational leadership (cadre level).

This component is essential for modeling collective action capacity and
the ability to coordinate resistance or maintain social order.
"""

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.types import Probability


class OrganizationComponent(BaseModel):
    """Organizational capacity of an entity.

    Tracks the organizational state of an entity:
    - Internal unity and coordination (Probability)
    - Quality of organizational leadership (Probability)

    All values use constrained types for automatic validation:
    - cohesion: Probability [0, 1]
    - cadre_level: Probability [0, 1]

    This component is immutable (frozen) to ensure state integrity.

    Attributes:
        cohesion: Internal unity and coordination [0=atomized, 1=unified] (default: 0.1)
        cadre_level: Quality of organizational leadership [0=none, 1=elite] (default: 0.0)
    """

    model_config = ConfigDict(frozen=True)

    cohesion: Probability = Field(
        default=0.1,
        description="Internal unity and coordination [0=atomized, 1=unified]",
    )
    cadre_level: Probability = Field(
        default=0.0,
        description="Quality of organizational leadership [0=none, 1=elite]",
    )

    @property
    def component_type(self) -> str:
        """Return the component type identifier.

        Returns:
            The string 'organization' identifying this component type.
        """
        return "organization"
