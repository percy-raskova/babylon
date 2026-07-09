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
        county_fips: Real 5-digit county FIPS when this territory maps to a US
            county (None for abstract territories); the county identity the
            TickDynamics economy reads, decoupled from the graph-local node id
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
        median_wage: Median wage paid in this territory (Feature 021)
        reserve_ratio: Reserve-army fraction of the labor force [0, 1]
        wealth: Aggregate territory wealth (dispossession transfer source)
        foreclosure_rate: Foreclosure rate [0, 1] (Feature 021)
        eviction_rate: Eviction rate [0, 1] (Feature 021)
        displacement_rate: Displacement rate [0, 1] (Feature 021)
        concentrated_ownership: Ownership concentration index [0, 1]
        absentee_landlord_share: Absentee landlord share of rentals [0, 1]
    """

    model_config = ConfigDict(
        extra="forbid",  # Reject unknown fields
        frozen=True,  # Spec 056 / Constitution III.7 — immutable state
        str_strip_whitespace=True,  # Clean string inputs
    )

    # Required fields
    id: str = Field(
        ...,
        pattern=r"^(T[0-9]{3,}|[0-9a-f]{15})$",
        description="Unique identifier (T[0-9]{3,} or 15-char H3 hex; 3+ digits for national scale)",
    )
    county_fips: str | None = Field(
        default=None,
        min_length=5,
        max_length=5,
        description=(
            "Real 5-digit county FIPS when this territory maps to a US county "
            "(None for abstract territories). The bridge mints graph-local node "
            "ids (e.g. 'T001'); the engine reads this as the county identity so "
            "ClassDistribution's 5-char fips is satisfied (owner item 25)."
        ),
    )
    h3_index: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{15}$",
        description="H3 hexagonal index (resolution 4)",
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

    # Metabolic Dynamics (Slice 1.4)
    biocapacity: Currency = Field(
        default=100.0,
        ge=0.0,
        description="Current stock of extractable resources/ecosystem services",
    )
    max_biocapacity: Currency = Field(
        default=100.0,
        ge=0.0,
        description="Maximum biocapacity ceiling",
    )
    regeneration_rate: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description="Fraction of max_biocapacity restored per tick",
    )
    extraction_intensity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Current extraction pressure applied by economy",
    )

    # Feature 021 (Capital Volume I) — labor-market and dispossession state.
    # Inputs are scenario/loader-seeded; ReserveArmySystem (#5) and
    # DispossessionEventSystem (#10) read and mutate them each tick. Zero
    # defaults keep both systems inert unless a scenario seeds them (both
    # early-continue on reserve_ratio <= 0 / all rates <= 0).
    median_wage: Currency = Field(
        default=0.0,
        description="Median wage paid in this territory (reserve-army pressure target)",
    )
    reserve_ratio: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of labor force in the reserve army [0, 1]",
    )
    wealth: Currency = Field(
        default=0.0,
        description="Aggregate territory wealth (dispossession value-transfer source)",
    )
    foreclosure_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Foreclosure rate feeding dispossession intensity [0, 1]",
    )
    eviction_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Eviction rate feeding dispossession intensity [0, 1]",
    )
    displacement_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Displacement rate feeding dispossession intensity [0, 1]",
    )
    concentrated_ownership: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Ownership concentration index [0, 1]",
    )
    absentee_landlord_share: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Absentee landlord share of rental stock [0, 1]",
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
