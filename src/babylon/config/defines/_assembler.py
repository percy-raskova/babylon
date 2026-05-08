"""GameDefines assembler — composes the 41 child Defines models.

Spec 058: extracted from the historical ``babylon.config.defines`` monolith. The :class:`GameDefines` class is the canonical assembler facade re-exported via :mod:`babylon.config.defines.__init__`.

Includes the YAML loader (:meth:`GameDefines.load_from_yaml`, :meth:`GameDefines.load_default`) and the 8 legacy ``@property`` accessors that delegate to nested fields for backward compatibility.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from babylon.config.defines.consciousness import (
    BifurcationDefines,
    ConsciousnessDefines,
    ContradictionFieldDefines,
    EdgeTransitionDefines,
    SolidarityDefines,
)
from babylon.config.defines.economy_basic import (
    CrisisDefines,
    EconomyDefines,
)
from babylon.config.defines.economy_class import (
    ClassDynamicsDefines,
    ClassSystemDefines,
    RentCircuitDefines,
)
from babylon.config.defines.economy_labor import (
    DispossessionDefines,
    ReserveArmyDefines,
    WorkingDayDefines,
)
from babylon.config.defines.endgame import (
    EndgameDefines,
    InitialDefines,
)
from babylon.config.defines.external_data import (
    ArcGISDefines,
    ExternalDataDefines,
    ServicesDefines,
)
from babylon.config.defines.ooda import OODADefines
from babylon.config.defines.organizations import (
    CommunityDefines,
    LifecycleDefines,
    MobilizeDefines,
    MoveDefines,
    NegotiateDefines,
    OrganizationDefines,
)
from babylon.config.defines.state_apparatus import (
    InstitutionDefines,
    StateApparatusAIDefines,
)
from babylon.config.defines.survival import (
    BehavioralDefines,
    StruggleDefines,
    SurvivalDefines,
    TensionDefines,
    VitalityDefines,
)
from babylon.config.defines.territory import (
    CarceralDefines,
    InfrastructureDefines,
    InfraTerrainDefines,
    MetabolismDefines,
    TerritoryDefines,
    TopologyDefines,
)
from babylon.config.defines.tunables import (
    PrecisionDefines,
    TimescaleDefines,
)


class GameDefines(BaseModel):
    """Centralized game coefficients extracted from hardcoded values.

    GameDefines collects numerical constants that were previously scattered
    across system implementations. By centralizing them here, we can:
    - Document their purpose and valid ranges
    - Override them per-scenario for calibration
    - Test the sensitivity of outcomes to coefficient changes

    The model is frozen (immutable) to ensure defines remain constant
    throughout a simulation run.

    Structure follows the YAML file organization:
    - crisis: Crisis detection and devaluation mechanics (Feature 018)
    - economy: Imperial rent extraction and value flow
    - survival: P(S|A) and P(S|R) survival calculus
    - solidarity: Consciousness transmission
    - behavioral: Behavioral economics (loss aversion)
    - tension: Tension dynamics
    - consciousness: Consciousness drift
    - territory: Territory dynamics
    - topology: Phase transition thresholds (gaseous/liquid/solid)
    - metabolism: Metabolic rift (ecological limits)
    - struggle: Struggle dynamics (Agency Layer)
    - carceral: Carceral equilibrium (Terminal Crisis Dynamics)
    - endgame: Endgame detection thresholds
    - initial: Initial conditions
    - contradiction_field: Dialectical field topology (Feature 002)
    - reserve_army: Reserve army of labor coefficients (Feature 021)
    - dispossession: Dispossession event intensity weights (Feature 021)
    - working_day: Working day characterization thresholds (Feature 021)
    - community: Hypergraph community layer coefficients (Feature 022)
    - class_dynamics: Class wealth flow dynamics (Feature 016, FRED DFA-derived)
    - edge_transition: Edge mode transition thresholds (Feature 002)
    - organization: Organization system coefficients (Feature 031)
    - ooda: OODA loop system coefficients (Feature 032)
    - class_system: Unified class system coefficients (Feature 038)
    - bifurcation: Bifurcation topology analysis coefficients (Feature 033)
    - infra_terrain: Terrain classification and biocapacity coefficients (Feature 036)
    - infrastructure: Infrastructure capacity and internet coefficients (Feature 036)
    """

    model_config = ConfigDict(frozen=True)

    crisis: CrisisDefines = Field(default_factory=CrisisDefines)
    mobilize: MobilizeDefines = Field(default_factory=MobilizeDefines)
    economy: EconomyDefines = Field(default_factory=EconomyDefines)
    survival: SurvivalDefines = Field(default_factory=SurvivalDefines)
    vitality: VitalityDefines = Field(default_factory=VitalityDefines)
    solidarity: SolidarityDefines = Field(default_factory=SolidarityDefines)
    behavioral: BehavioralDefines = Field(default_factory=BehavioralDefines)
    tension: TensionDefines = Field(default_factory=TensionDefines)
    consciousness: ConsciousnessDefines = Field(default_factory=ConsciousnessDefines)
    territory: TerritoryDefines = Field(default_factory=TerritoryDefines)
    topology: TopologyDefines = Field(default_factory=TopologyDefines)
    metabolism: MetabolismDefines = Field(default_factory=MetabolismDefines)
    struggle: StruggleDefines = Field(default_factory=StruggleDefines)
    carceral: CarceralDefines = Field(default_factory=CarceralDefines)
    endgame: EndgameDefines = Field(default_factory=EndgameDefines)
    initial: InitialDefines = Field(default_factory=InitialDefines)
    precision: PrecisionDefines = Field(default_factory=PrecisionDefines)
    timescale: TimescaleDefines = Field(default_factory=TimescaleDefines)
    external_data: ExternalDataDefines = Field(default_factory=ExternalDataDefines)
    contradiction_field: ContradictionFieldDefines = Field(
        default_factory=ContradictionFieldDefines
    )
    # Capital Volume I Production Dynamics (Feature 021)
    reserve_army: ReserveArmyDefines = Field(default_factory=ReserveArmyDefines)
    dispossession: DispossessionDefines = Field(default_factory=DispossessionDefines)
    working_day: WorkingDayDefines = Field(default_factory=WorkingDayDefines)
    # Hypergraph Community Layer (Feature 022)
    community: CommunityDefines = Field(default_factory=CommunityDefines)
    # Class Dynamics (Feature 016, FRED DFA-derived)
    class_dynamics: ClassDynamicsDefines = Field(default_factory=ClassDynamicsDefines)
    # Edge Transition Thresholds (Feature 002/028)
    edge_transition: EdgeTransitionDefines = Field(default_factory=EdgeTransitionDefines)
    # D-P-D' Lifecycle Circuit (Feature 030)
    lifecycle: LifecycleDefines = Field(default_factory=LifecycleDefines)
    # Organization Base Model (Feature 031)
    organization: OrganizationDefines = Field(default_factory=OrganizationDefines)
    # OODA Loop System (Feature 032)
    ooda: OODADefines = Field(default_factory=OODADefines)
    # Bifurcation Topology Analysis (Feature 033)
    bifurcation: BifurcationDefines = Field(default_factory=BifurcationDefines)
    # Infrastructure Topology Layer (Feature 036)
    infra_terrain: InfraTerrainDefines = Field(default_factory=InfraTerrainDefines)
    infrastructure: InfrastructureDefines = Field(default_factory=InfrastructureDefines)
    # Unified Class System (Feature 038)
    rent_circuit: RentCircuitDefines = Field(default_factory=RentCircuitDefines)
    class_system: ClassSystemDefines = Field(default_factory=ClassSystemDefines)
    # State Apparatus AI (Feature 039)
    state_ai: StateApparatusAIDefines = Field(default_factory=StateApparatusAIDefines)
    # Institution Base Model (Feature 040)
    institution: InstitutionDefines = Field(default_factory=InstitutionDefines)
    move: MoveDefines = Field(default_factory=MoveDefines)
    negotiate: NegotiateDefines = Field(default_factory=NegotiateDefines)

    # Legacy flat attributes for backward compatibility
    # These delegate to the nested structure

    @property
    def SUPERWAGE_IMPACT(self) -> float:
        """How much 1 unit of imperial extraction increases Core wealth."""
        return self.solidarity.superwage_impact

    @property
    def SOLIDARITY_SCALING(self) -> float:
        """Multiplier for graph edge weights affecting Organization."""
        return self.solidarity.scaling_factor

    @property
    def REPRESSION_BASE(self) -> float:
        """Base resistance to revolution in P(S|R) denominator."""
        return self.survival.repression_base

    @property
    def REVOLUTION_THRESHOLD(self) -> float:
        """The tipping point for P(S|R) formula."""
        return self.survival.revolution_threshold

    @property
    def DEFAULT_ORGANIZATION(self) -> float:
        """Fallback organization value when not specified on entity."""
        return self.survival.default_organization

    @property
    def DEFAULT_REPRESSION_FACED(self) -> float:
        """Fallback repression value when not specified on entity."""
        return self.survival.default_repression

    @property
    def DEFAULT_SUBSISTENCE(self) -> float:
        """Fallback subsistence threshold when not specified on entity."""
        return self.survival.default_subsistence

    @property
    def NEGLIGIBLE_TRANSMISSION(self) -> float:
        """Threshold below which transmissions are skipped as noise."""
        return self.solidarity.negligible_transmission

    @classmethod
    def load_from_yaml(cls, path: str | Path) -> GameDefines:
        """Load GameDefines from a YAML file.

        Args:
            path: Path to the YAML file (absolute or relative)

        Returns:
            GameDefines instance populated from YAML

        Raises:
            FileNotFoundError: If the YAML file doesn't exist
            yaml.YAMLError: If the YAML is malformed
            pydantic.ValidationError: If values fail validation
        """
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return cls._from_yaml_dict(data)

    @classmethod
    def _from_yaml_dict(cls, data: dict[str, Any]) -> GameDefines:
        """Create GameDefines from parsed YAML dictionary.

        Args:
            data: Parsed YAML data

        Returns:
            GameDefines instance
        """
        if data is None:
            data = {}

        # Parse external_data section with nested arcgis/services
        external_data_raw = data.get("external_data", {})
        external_data = ExternalDataDefines(
            arcgis=ArcGISDefines(**external_data_raw.get("arcgis", {})),
            services=ServicesDefines(**external_data_raw.get("services", {})),
        )

        return cls(
            mobilize=MobilizeDefines(**data.get("mobilize", {})),
            crisis=CrisisDefines(**data.get("crisis", {})),
            economy=EconomyDefines(**data.get("economy", {})),
            survival=SurvivalDefines(**data.get("survival", {})),
            vitality=VitalityDefines(**data.get("vitality", {})),
            solidarity=SolidarityDefines(**data.get("solidarity", {})),
            behavioral=BehavioralDefines(**data.get("behavioral", {})),
            tension=TensionDefines(**data.get("tension", {})),
            consciousness=ConsciousnessDefines(**data.get("consciousness", {})),
            territory=TerritoryDefines(**data.get("territory", {})),
            topology=TopologyDefines(**data.get("topology", {})),
            metabolism=MetabolismDefines(**data.get("metabolism", {})),
            struggle=StruggleDefines(**data.get("struggle", {})),
            carceral=CarceralDefines(**data.get("carceral", {})),
            endgame=EndgameDefines(**data.get("endgame", {})),
            initial=InitialDefines(**data.get("initial", {})),
            precision=PrecisionDefines(**data.get("precision", {})),
            timescale=TimescaleDefines(**data.get("timescale", {})),
            external_data=external_data,
            contradiction_field=ContradictionFieldDefines(**data.get("contradiction_field", {})),
            community=CommunityDefines(**data.get("community", {})),
            class_dynamics=ClassDynamicsDefines(**data.get("class_dynamics", {})),
            reserve_army=ReserveArmyDefines(**data.get("reserve_army", {})),
            dispossession=DispossessionDefines(**data.get("dispossession", {})),
            working_day=WorkingDayDefines(**data.get("working_day", {})),
            edge_transition=EdgeTransitionDefines(**data.get("edge_transition", {})),
            lifecycle=LifecycleDefines(**data.get("lifecycle", {})),
            organization=OrganizationDefines(**data.get("organization", {})),
            ooda=OODADefines(**data.get("ooda", {})),
            bifurcation=BifurcationDefines(**data.get("bifurcation", {})),
            infra_terrain=InfraTerrainDefines(**data.get("infra_terrain", {})),
            infrastructure=InfrastructureDefines(**data.get("infrastructure", {})),
            rent_circuit=RentCircuitDefines(**data.get("rent_circuit", {})),
            class_system=ClassSystemDefines(**data.get("class_system", {})),
            state_ai=StateApparatusAIDefines(**data.get("state_ai", {})),
            institution=InstitutionDefines(**data.get("institution", {})),
            move=MoveDefines(**data.get("move", {})),
            negotiate=NegotiateDefines(**data.get("negotiate", {})),
        )

    @classmethod
    def default_yaml_path(cls) -> Path:
        """Return the conventional path for an optional ``defines.yaml`` override.

        The repository does not ship a ``defines.yaml`` (the file was removed
        in commit ``4ce7c96a`` when the data layer was extracted). Callers
        may drop a YAML at this path to override the dataclass defaults
        compiled into :class:`GameDefines`; if the file is absent,
        :meth:`load_default` returns the dataclass defaults unchanged.

        Returns:
            ``Path`` pointing at ``src/babylon/data/defines.yaml`` (which
            may or may not exist on disk).
        """
        return Path(__file__).parent.parent.parent / "data" / "defines.yaml"

    @classmethod
    def load_default(cls) -> GameDefines:
        """Load :class:`GameDefines`, preferring the optional YAML override.

        If ``src/babylon/data/defines.yaml`` exists, it is loaded as a
        full override of the dataclass defaults. Otherwise the dataclass
        defaults are returned. The repository ships without the YAML, so
        the dataclass defaults are the canonical values today.

        Returns:
            ``GameDefines`` instance — YAML-loaded if present, otherwise
            the dataclass defaults.
        """
        default_path = cls.default_yaml_path()
        if default_path.exists():
            return cls.load_from_yaml(default_path)
        return cls()


__all__ = ["GameDefines"]
