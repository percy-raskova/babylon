"""IdeologicalComponent - Multi-dimensional ideological state (George Jackson Model).

IdeologicalComponent represents the ideological state of an entity in the
Babylon simulation using the George Jackson Model of consciousness:

- class_consciousness: Relationship to Capital [0=False, 1=Revolutionary]
- national_identity: Relationship to State [0=Internationalist, 1=Fascist]
- agitation: Raw political energy accumulated from wage crises [0, inf)

The key insight: "Fascism is the defensive form of capitalism."
- Agitation + Solidarity -> Class Consciousness (Revolutionary Path)
- Agitation + No Solidarity -> National Identity (Fascist Path)

This component is essential for modeling consciousness drift and
political transformation in the simulation.
"""

from pydantic import BaseModel, ConfigDict, Field


class IdeologicalComponent(BaseModel):
    """Multi-dimensional ideological state (George Jackson Model).

    Tracks the ideological state of an entity using three axes:
    - Relationship to Capital (class consciousness)
    - Relationship to State/Tribe (national identity)
    - Accumulated political energy (agitation)

    The bifurcation mechanism:
    - When wages fall, agitation accumulates
    - If solidarity edges exist: agitation routes to class_consciousness
    - If no solidarity edges: agitation routes to national_identity

    All values use constrained floats for automatic validation:
    - class_consciousness: [0, 1] (0=False Consciousness, 1=Revolutionary)
    - national_identity: [0, 1] (0=Internationalist, 1=Fascist)
    - agitation: [0, inf) (no upper bound - accumulates during crises)

    This component is immutable (frozen) to ensure state integrity.

    Attributes:
        class_consciousness: Relationship to Capital [0=False, 1=Revolutionary] (default: 0.0)
        national_identity: Relationship to State [0=Internationalist, 1=Fascist] (default: 0.5)
        agitation: Raw political energy from wage crises [0, inf) (default: 0.0)
    """

    model_config = ConfigDict(frozen=True)

    class_consciousness: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Relationship to Capital (0=False Consciousness, 1=Revolutionary)",
    )
    national_identity: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Relationship to State (0=Internationalist, 1=Fascist)",
    )
    agitation: float = Field(
        default=0.0,
        ge=0.0,
        description="Raw political energy accumulated from wage crises",
    )

    @property
    def component_type(self) -> str:
        """Return the component type identifier.

        Returns:
            The string 'ideological' identifying this component type.
        """
        return "ideological"
