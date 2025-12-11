"""Territory entity model.

A Territory is the Phase 3.5 node type - the spatial substrate of the simulation.
It represents a strategic sector in the world system, defined by:
1. Its sector type (industrial, residential, commercial, etc.)
2. Its ownership stack (host/parasite relationship)
3. Its operational profile (visibility stance)
4. Its heat level (state attention)
5. Its territory type (settler-colonial hierarchy classification)

Sprint 3.5.2: Layer 0 - The Territorial Substrate.
Sprint 3.7: The Carceral Geography - Necropolitical Triad.
"""

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.enums import OperationalProfile, SectorType, TerritoryType
from babylon.models.types import Currency, Intensity


class Territory(BaseModel):
    """A strategic sector in the world system.

    Territories are the spatial nodes of the simulation. Unlike SocialClass
    nodes which represent abstract class positions, Territory nodes represent
    physical locations that can be occupied, contested, and liberated.

    The "Host/Parasite Stack" defines territorial control:
    - Host (Legal Sovereign): Recognized by State, collects rent/taxes
    - Occupant (De Facto User): Actually uses the space, may be revolutionary

    The "Operational Profile" trades visibility for recruitment:
    - LOW_PROFILE: Safe from eviction, low recruitment
    - HIGH_PROFILE: High recruitment, high heat (state attention)

    Attributes:
        id: Unique identifier matching pattern ^T[0-9]{3}$
        name: Human-readable sector name
        sector_type: Economic/social character of the territory
        territory_type: Classification in settler-colonial hierarchy (Sprint 3.7)
        host_id: Optional ID of the Legal Sovereign (collects rent)
        occupant_id: Optional ID of the De Facto Occupant (uses space)
        profile: Operational profile (visibility stance)
        heat: State attention level [0, 1]
        rent_level: Economic pressure on occupants [0, inf)
        population: Human shield count (sympathizers)
        under_eviction: Whether eviction pipeline is active
    """

    model_config = ConfigDict(
        extra="forbid",  # Reject unknown fields
        validate_assignment=True,  # Validate on attribute mutation
        str_strip_whitespace=True,  # Clean string inputs
    )

    # Required fields
    id: str = Field(
        ...,
        pattern=r"^T[0-9]{3}$",
        description="Unique identifier matching ^T[0-9]{3}$",
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Human-readable sector name",
    )
    sector_type: SectorType = Field(
        ...,
        description="Economic/social character of the territory",
    )

    # Settler-colonial hierarchy classification (Sprint 3.7)
    territory_type: TerritoryType = Field(
        default=TerritoryType.CORE,
        description="Classification in settler-colonial hierarchy",
    )

    # Ownership stack (host/parasite)
    host_id: str | None = Field(
        default=None,
        description="ID of Legal Sovereign (collects rent/taxes)",
    )
    occupant_id: str | None = Field(
        default=None,
        description="ID of De Facto Occupant (uses space)",
    )

    # Operational profile (visibility stance)
    profile: OperationalProfile = Field(
        default=OperationalProfile.LOW_PROFILE,
        description="Visibility stance: LOW_PROFILE or HIGH_PROFILE",
    )

    # State dynamics
    heat: Intensity = Field(
        default=0.0,
        description="State attention level [0, 1]",
    )

    # Economic dynamics
    rent_level: Currency = Field(
        default=1.0,
        description="Economic pressure on occupants (baseline = 1.0)",
    )

    # Population dynamics
    population: int = Field(
        default=0,
        ge=0,
        description="Population count (human shield / sympathizers)",
    )

    # Eviction state
    under_eviction: bool = Field(
        default=False,
        description="Whether eviction pipeline is active",
    )

    @property
    def clarity_bonus(self) -> float:
        """Recruitment bonus from profile visibility.

        HIGH_PROFILE attracts cadre through ideological clarity.
        LOW_PROFILE is safe but boring.

        Returns:
            0.3 if HIGH_PROFILE, 0.0 if LOW_PROFILE
        """
        if self.profile == OperationalProfile.HIGH_PROFILE:
            return 0.3
        return 0.0

    @property
    def is_liberated(self) -> bool:
        """Whether territory is a Liberated Zone.

        A territory is liberated when there is an occupant
        but no host (legal sovereign). This represents
        successful transition from parasitic to sovereign tenure.

        Returns:
            True if occupant exists and host does not
        """
        return self.occupant_id is not None and self.host_id is None

    @property
    def is_sink_node(self) -> bool:
        """Whether territory is a sink node in the displacement graph.

        Sprint 3.7: The Carceral Geography - Necropolitical Triad.

        Sink nodes are territories where displaced populations are routed.
        They have no economic value - only containment/elimination function.
        Population flows INTO these territories but does not flow OUT easily.

        The three sink node types form the Necropolitical Triad:
        - RESERVATION: Containment (warehousing surplus population)
        - PENAL_COLONY: Extraction (forced labor, suppresses organization)
        - CONCENTRATION_CAMP: Elimination (population decay, generates terror)

        Returns:
            True if territory_type is RESERVATION, PENAL_COLONY, or CONCENTRATION_CAMP
        """
        return self.territory_type in (
            TerritoryType.RESERVATION,
            TerritoryType.PENAL_COLONY,
            TerritoryType.CONCENTRATION_CAMP,
        )
