"""IdeologicalComponent - Political alignment and adherence of an entity.

IdeologicalComponent represents the ideological state of an entity in the
Babylon simulation. It tracks political alignment on the revolutionary-
reactionary spectrum and the strength of ideological commitment.

This component is essential for modeling consciousness drift and
political transformation in the simulation.
"""

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.types import Ideology, Probability


class IdeologicalComponent(BaseModel):
    """Political alignment and adherence of an entity.

    Tracks the ideological state of an entity:
    - Position on revolutionary-reactionary spectrum (Ideology)
    - Strength of ideological commitment (Probability)

    All values use constrained types for automatic validation:
    - alignment: Ideology [-1, 1]
    - adherence: Probability [0, 1]

    This component is immutable (frozen) to ensure state integrity.

    Attributes:
        alignment: Position on spectrum [-1=revolutionary, 1=reactionary] (default: 0.0)
        adherence: Strength of ideological commitment [0=none, 1=full] (default: 0.5)
    """

    model_config = ConfigDict(frozen=True)

    alignment: Ideology = Field(
        default=0.0,
        description="Position on spectrum [-1=revolutionary, 1=reactionary]",
    )
    adherence: Probability = Field(
        default=0.5,
        description="Strength of ideological commitment [0=none, 1=full]",
    )

    @property
    def component_type(self) -> str:
        """Return the component type identifier.

        Returns:
            The string 'ideological' identifying this component type.
        """
        return "ideological"
