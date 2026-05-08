"""Territorial substrate, topology, metabolism, carceral and infrastructure.

Spec 058: extracted from the historical ``babylon.config.defines`` monolith.
Re-exported via :mod:`babylon.config.defines.__init__`; composed into :class:`GameDefines` in :mod:`babylon.config.defines._assembler`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TerritoryDefines(BaseModel):
    """Territory dynamics coefficients."""

    model_config = ConfigDict(frozen=True)

    heat_decay_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="= decay_lambda: heat entropy on same 7-week half-life (FM 3-24).",
    )
    high_profile_heat_gain: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="= rent_spike × heat_decay = 1.5 × 0.1: FM 3-24 clear-phase convergence in 6-8 weeks.",
    )
    eviction_heat_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="= α (extraction_efficiency): eviction triggers at full extraction capacity.",
    )
    rent_spike_multiplier: float = Field(
        default=1.5,
        gt=0.0,
        description="1.5×: Census/HUD gentrification rent premium (UCLA Urban Displacement Project).",
    )
    displacement_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Population displacement during eviction",
    )
    heat_spillover_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="= heat_decay_rate / 2: ink-spot spillover at half the decay rate.",
    )
    clarity_profile_coefficient: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Clarity bonus for HIGH_PROFILE territories",
    )
    concentration_camp_decay_rate: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Population decay rate in CONCENTRATION_CAMP territories (elimination)",
    )

    # Displacement Priority Mode (Sprint 3.7.1: Dynamic Displacement Routing)
    # Stored as string for YAML compatibility, converted to enum at runtime
    displacement_priority_mode: str = Field(
        default="EXTRACTION",
        description="Sink routing mode: EXTRACTION (prison first), CONTAINMENT (reservation first), ELIMINATION (camp first)",
    )

    # AUTO mode thresholds (Sprint 3.7.1 - reserved for future use)
    elimination_rent_threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Imperial rent ratio below which ELIMINATION mode activates",
    )
    elimination_tension_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Tension threshold above which ELIMINATION mode activates",
    )
    containment_rent_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Imperial rent ratio below which CONTAINMENT mode activates",
    )
    containment_tension_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Tension threshold above which CONTAINMENT mode activates",
    )


class TopologyDefines(BaseModel):
    """Phase transition coefficients for solidarity network analysis.

    The topology system tracks phase transitions in class solidarity:
    - Gaseous: Atomized, no collective action capacity
    - Transitional: Solidarity building, weak ties forming
    - Liquid: Mass movement (percolation but low cadre density)
    - Solid: Vanguard party (percolation with high cadre density)
    """

    model_config = ConfigDict(frozen=True)

    gaseous_threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Game design: percolation ratio below this = atomized (no collective action).",
    )
    condensation_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Game design: percolation ratio for phase transition (gaseous→liquid/solid).",
    )
    vanguard_density_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Game design: cadre density threshold for vanguard party (liquid→solid).",
    )
    brittle_multiplier: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description="Game design: potential > actual * this = brittle network (fragile solidarity).",
    )
    solidarity_sympathizer_threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Game design: minimum SOLIDARITY edge strength for sympathizer classification.",
    )
    solidarity_cadre_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Game design: minimum SOLIDARITY edge strength for cadre classification.",
    )
    resilience_removal_rate: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Game design: fraction of nodes removed during resilience test (default 20%).",
    )
    resilience_survival_threshold: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Game design: L_max must survive at this fraction of original after removal.",
    )


class MetabolismDefines(BaseModel):
    """Metabolic rift coefficients (Slice 1.4 - Ecological Limits).

    The Metabolism System tracks the widening rift between extraction and regeneration:
    - Biocapacity regeneration and depletion
    - ECOLOGICAL_OVERSHOOT event when consumption exceeds biocapacity
    """

    model_config = ConfigDict(frozen=True)

    entropy_factor: float = Field(
        default=1.2,
        gt=1.0,
        le=3.0,
        description="Game design: extraction costs more than it yields (thermodynamic inefficiency).",
    )
    overshoot_threshold: float = Field(
        default=1.0,
        gt=0.0,
        le=2.0,
        description="Game design: consumption/biocapacity ratio triggering ECOLOGICAL_OVERSHOOT.",
    )
    max_overshoot_ratio: float = Field(
        default=999.0,
        gt=0.0,
        description="Engineering: overflow cap. Prevents division-by-near-zero when biocapacity approaches 0.",
    )


class CarceralDefines(BaseModel):
    """Carceral equilibrium coefficients (Terminal Crisis Dynamics).

    The carceral system models the transition from wage suppression to
    outright incarceration as the imperial rent pool exhausts:

    1. SUPERWAGE_CRISIS: Rent pool can't sustain LA wages
    2. CLASS_DECOMPOSITION: LA splits into enforcers + prisoners
    3. CONTROL_RATIO_CRISIS: Prisoners exceed control capacity
    4. TERMINAL_DECISION: Revolution vs genocide based on organization

    Real-world staffing ratios (sources: BJS, Marshall Project 2024):
    - 1:1 = Maximum control (Massachusetts, best-staffed)
    - 4:1 = US national jail average (2022)
    - 15:1 = Federal DOJ theoretical baseline
    - 200:1 = Crisis/collapse (Georgia, 2024)

    With 70/30 decomposition, prisoner/enforcer = 2.33:1, so:
    - control_capacity <= 2: Crisis triggers immediately
    - control_capacity >= 3: No crisis (stable carceral state)
    """

    model_config = ConfigDict(frozen=True)

    control_capacity: int = Field(
        default=4,
        ge=1,
        le=20,
        description="Game design: prisoners one enforcer can control (1:N). US average ~4, crisis >15.",
    )
    enforcer_fraction: float = Field(
        default=0.15,
        ge=0.05,
        le=0.50,
        description="Game design: after SUPERWAGE_CRISIS: % of former LA who BECOME guards/cops.",
    )
    proletariat_fraction: float = Field(
        default=0.85,
        ge=0.50,
        le=0.95,
        description="Game design: after SUPERWAGE_CRISIS: % of former LA who BECOME prisoners.",
    )
    revolution_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Game design: average prisoner organization threshold for revolution (vs genocide).",
    )

    # Phase staggering delays (ticks) - ensures temporal separation between phases
    decomposition_delay: int = Field(
        default=52,
        ge=0,
        le=520,
        description="Game design: ticks to wait after SUPERWAGE_CRISIS before CLASS_DECOMPOSITION (1 year default).",
    )
    control_ratio_delay: int = Field(
        default=52,
        ge=0,
        le=520,
        description="Game design: ticks to wait after CLASS_DECOMPOSITION before checking control ratio (1 year default).",
    )
    terminal_decision_delay: int = Field(
        default=1,
        ge=0,
        le=52,
        description="Game design: ticks to wait after CONTROL_RATIO_CRISIS before TERMINAL_DECISION.",
    )


class InfraTerrainDefines(BaseModel):
    """Terrain classification and biocapacity coefficients (Feature 036).

    Configures majority-coverage thresholds, initial biocapacity stock
    values, and per-tick depletion rates. Also includes internet access
    defaults.

    See Also:
        :mod:`babylon.infrastructure.terrain`: DefaultTerrainClassifier.
        ``specs/036-infrastructure-topology/spec.md``: FR-001 through FR-008.
    """

    model_config = ConfigDict(frozen=True)

    # Terrain classification (FR-001)
    majority_coverage_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "SYNTHETIC: Coverage fraction above which a hex is classified "
            "as WATER or RESOURCE. 0.5 = majority rule."
        ),
    )

    # Biocapacity initial stocks (FR-005, FR-006)
    # SYNTHETIC: Game-design values, no empirical source
    initial_freshwater: float = Field(
        default=100.0,
        ge=0.0,
        description="SYNTHETIC: Initial FRESHWATER stock for WATER hexes.",
    )
    initial_fishery: float = Field(
        default=80.0,
        ge=0.0,
        description="SYNTHETIC: Initial FISHERY stock for WATER hexes.",
    )
    initial_shipping_access: float = Field(
        default=50.0,
        ge=0.0,
        description="SYNTHETIC: Initial SHIPPING_ACCESS stock for WATER hexes.",
    )
    initial_mineral: float = Field(
        default=120.0,
        ge=0.0,
        description="SYNTHETIC: Initial MINERAL stock for RESOURCE hexes.",
    )
    initial_timber: float = Field(
        default=90.0,
        ge=0.0,
        description="SYNTHETIC: Initial TIMBER stock for RESOURCE hexes.",
    )
    initial_hydroelectric: float = Field(
        default=60.0,
        ge=0.0,
        description="SYNTHETIC: Initial HYDROELECTRIC stock for RESOURCE hexes.",
    )

    # Biocapacity depletion rates (FR-007)
    # SYNTHETIC: Per-tick extraction fraction of current stock
    depletion_freshwater: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="SYNTHETIC: Per-tick depletion rate for FRESHWATER.",
    )
    depletion_fishery: float = Field(
        default=0.04,
        ge=0.0,
        le=1.0,
        description="SYNTHETIC: Per-tick depletion rate for FISHERY.",
    )
    depletion_shipping_access: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description="SYNTHETIC: Per-tick depletion rate for SHIPPING_ACCESS.",
    )
    depletion_mineral: float = Field(
        default=0.03,
        ge=0.0,
        le=1.0,
        description="SYNTHETIC: Per-tick depletion rate for MINERAL.",
    )
    depletion_timber: float = Field(
        default=0.04,
        ge=0.0,
        le=1.0,
        description="SYNTHETIC: Per-tick depletion rate for TIMBER.",
    )
    depletion_hydroelectric: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="SYNTHETIC: Per-tick depletion rate for HYDROELECTRIC.",
    )

    # Internet access defaults (FR-024)
    internet_access_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "SYNTHETIC: Minimum FCC broadband penetration percentage / 100 "
            "for internet_access=True. 0.5 = 50% coverage required."
        ),
    )
    default_surveillance_coupling: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description=(
            "SYNTHETIC: Default fraction of consciousness flow visible "
            "to state apparatus at internet-connected hexes."
        ),
    )

    def get_initial_stock(self, stock_type: str) -> float:
        """Get initial biocapacity stock value by type.

        Args:
            stock_type: BiocapacityType value (lowercase).

        Returns:
            Initial stock value.

        Raises:
            ValueError: If stock_type is not recognized.
        """
        stock_map: dict[str, float] = {
            "freshwater": self.initial_freshwater,
            "fishery": self.initial_fishery,
            "shipping_access": self.initial_shipping_access,
            "mineral": self.initial_mineral,
            "timber": self.initial_timber,
            "hydroelectric": self.initial_hydroelectric,
        }
        if stock_type not in stock_map:
            msg = f"Unknown stock_type: {stock_type!r}"
            raise ValueError(msg)
        return stock_map[stock_type]

    def get_depletion_rate(self, stock_type: str) -> float:
        """Get per-tick depletion rate by stock type.

        Args:
            stock_type: BiocapacityType value (lowercase).

        Returns:
            Depletion rate per tick.

        Raises:
            ValueError: If stock_type is not recognized.
        """
        rate_map: dict[str, float] = {
            "freshwater": self.depletion_freshwater,
            "fishery": self.depletion_fishery,
            "shipping_access": self.depletion_shipping_access,
            "mineral": self.depletion_mineral,
            "timber": self.depletion_timber,
            "hydroelectric": self.depletion_hydroelectric,
        }
        if stock_type not in rate_map:
            msg = f"Unknown stock_type: {stock_type!r}"
            raise ValueError(msg)
        return rate_map[stock_type]


class InfrastructureDefines(BaseModel):
    """Infrastructure capacity and internet operation coefficients (Feature 036).

    Configures per-type capacity values, natural capacity defaults,
    OPSEC tradeoff ratios, and internet throttle fractions.

    See Also:
        :mod:`babylon.infrastructure.capacity`: DefaultEdgeCapacityCalculator.
        ``specs/036-infrastructure-topology/spec.md``: FR-009 through FR-029.
    """

    model_config = ConfigDict(frozen=True)

    # Per-type base capacity coefficients (FR-012)
    # Format: {infra_type}_{flow_category}
    # SYNTHETIC: Game-design values
    highway_freight: float = Field(default=1.0, ge=0.0, description="SYNTHETIC")
    highway_commuter: float = Field(default=1.0, ge=0.0, description="SYNTHETIC")
    highway_value: float = Field(default=0.5, ge=0.0, description="SYNTHETIC")
    highway_consciousness: float = Field(default=0.3, ge=0.0, description="SYNTHETIC")

    arterial_freight: float = Field(default=0.6, ge=0.0, description="SYNTHETIC")
    arterial_commuter: float = Field(default=0.7, ge=0.0, description="SYNTHETIC")
    arterial_value: float = Field(default=0.3, ge=0.0, description="SYNTHETIC")
    arterial_consciousness: float = Field(default=0.2, ge=0.0, description="SYNTHETIC")

    local_road_freight: float = Field(default=0.2, ge=0.0, description="SYNTHETIC")
    local_road_commuter: float = Field(default=0.4, ge=0.0, description="SYNTHETIC")
    local_road_value: float = Field(default=0.1, ge=0.0, description="SYNTHETIC")
    local_road_consciousness: float = Field(default=0.3, ge=0.0, description="SYNTHETIC")

    rail_freight: float = Field(default=1.2, ge=0.0, description="SYNTHETIC")
    rail_commuter: float = Field(default=0.3, ge=0.0, description="SYNTHETIC")
    rail_value: float = Field(default=0.2, ge=0.0, description="SYNTHETIC")
    rail_consciousness: float = Field(default=0.1, ge=0.0, description="SYNTHETIC")

    pipeline_energy: float = Field(default=1.5, ge=0.0, description="SYNTHETIC")

    transmission_energy: float = Field(default=1.0, ge=0.0, description="SYNTHETIC")

    shipping_lane_freight: float = Field(default=1.5, ge=0.0, description="SYNTHETIC")

    air_link_freight: float = Field(default=0.3, ge=0.0, description="SYNTHETIC")
    air_link_commuter: float = Field(default=0.8, ge=0.0, description="SYNTHETIC")
    air_link_value: float = Field(default=0.5, ge=0.0, description="SYNTHETIC")
    air_link_consciousness: float = Field(default=0.5, ge=0.0, description="SYNTHETIC")

    # Natural capacity (FR-014)
    natural_capacity_coefficient: float = Field(
        default=0.1,
        ge=0.0,
        description=(
            "SYNTHETIC: Base natural capacity for LAND-LAND edges without "
            "infrastructure. Applied to COMMUTER and CONSCIOUSNESS only."
        ),
    )

    # Minimum capacity threshold (EC-006)
    minimum_capacity_threshold: float = Field(
        default=0.01,
        ge=0.0,
        description=(
            "SYNTHETIC: Minimum edge capacity below which flow is zero. "
            "Prevents numerical noise from near-zero weights."
        ),
    )

    # OPSEC tradeoff (FR-028)
    opsec_tradeoff_ratio: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "SYNTHETIC: Ratio of surveillance coupling reduction to "
            "consciousness throughput loss when applying COUNTER_INTEL."
        ),
    )

    # Throttle throughput (FR-029)
    throttle_throughput_fraction: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description=(
            "SYNTHETIC: Fraction of consciousness throughput remaining "
            "when state sets THROTTLE response mode."
        ),
    )

    # Snapping tolerance (FR-011)
    snap_buffer_fraction: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description=(
            "SYNTHETIC: Buffer around shared boundary as fraction of "
            "hex diameter for spatial snapping of linear features."
        ),
    )

    # Nonlocal locality thresholds (FR-020)
    local_ratio_threshold: float = Field(
        default=3.0,
        gt=0.0,
        description=(
            "SYNTHETIC: Distance/hex_diameter ratio below which edge is classified as LOCAL."
        ),
    )
    semi_local_ratio_threshold: float = Field(
        default=20.0,
        gt=0.0,
        description=(
            "SYNTHETIC: Distance/hex_diameter ratio below which edge "
            "is classified as SEMI_LOCAL. Above = NONLOCAL."
        ),
    )

    def get_capacity(self, infra_type: str, flow_category: str) -> float:
        """Get base capacity for an infrastructure type and flow category.

        Args:
            infra_type: InfrastructureType value (lowercase).
            flow_category: FlowCategory value (lowercase).

        Returns:
            Base capacity value, or 0.0 if combination not applicable.
        """
        key = f"{infra_type}_{flow_category}"
        return getattr(self, key, 0.0)


__all__ = [
    "CarceralDefines",
    "InfraTerrainDefines",
    "InfrastructureDefines",
    "MetabolismDefines",
    "TerritoryDefines",
    "TopologyDefines",
]
