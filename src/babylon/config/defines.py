"""Game defines for centralized coefficient configuration.

This module provides the GameDefines model which extracts hardcoded values
from systems into a single, configurable location. This enables:
1. Easier calibration of game balance
2. Scenario-specific coefficient overrides
3. Clear documentation of magic numbers

Sprint: Paradox Refactor Phase 1
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class EconomyDefines(BaseModel):
    """Economic system coefficients."""

    model_config = ConfigDict(frozen=True)

    # Imperial rent extraction
    extraction_efficiency: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Alpha - how efficiently core extracts value from periphery",
    )
    comprador_cut: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Fraction of tribute kept by comprador class",
    )

    # Super-wages (PPP Model)
    super_wage_rate: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Fraction of tribute paid as super-wages",
    )
    superwage_multiplier: float = Field(
        default=1.0,
        ge=0.0,
        description="PPP multiplier for labor aristocracy purchasing power",
    )
    superwage_ppp_impact: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How much extraction translates to PPP bonus",
    )

    # Imperial rent pool (Dynamic Balance)
    initial_rent_pool: float = Field(
        default=100.0,
        ge=0.0,
        description="Starting imperial rent pool",
    )
    pool_high_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Pool ratio for prosperity mode",
    )
    pool_low_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Pool ratio for austerity mode",
    )
    pool_critical_threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Pool ratio for ECONOMIC_CRISIS",
    )

    # Wage bounds
    min_wage_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Minimum super-wage rate during crisis",
    )
    max_wage_rate: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Maximum super-wage rate during prosperity",
    )

    # Client state subsidy (The Iron Lung)
    subsidy_conversion_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Rate at which wealth converts to repression",
    )
    subsidy_trigger_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="P(S|R)/P(S|A) ratio threshold for subsidy",
    )


class SurvivalDefines(BaseModel):
    """Survival calculus coefficients."""

    model_config = ConfigDict(frozen=True)

    # Acquiescence probability P(S|A)
    steepness_k: float = Field(
        default=10.0,
        gt=0.0,
        description="Sigmoid sharpness in acquiescence probability",
    )
    default_subsistence: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum wealth for survival through compliance",
    )

    # Revolution probability P(S|R)
    default_organization: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Fallback organization value",
    )
    default_repression: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Fallback repression value",
    )
    revolution_threshold: float = Field(
        default=1.0,
        gt=0.0,
        description="Tipping point for P(S|R) formula",
    )
    repression_base: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Base resistance to revolution in denominator",
    )


class SolidarityDefines(BaseModel):
    """Solidarity and consciousness transmission coefficients."""

    model_config = ConfigDict(frozen=True)

    scaling_factor: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="Multiplier for graph edge weights affecting organization",
    )
    activation_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum source consciousness for transmission",
    )
    mass_awakening_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Target consciousness for MASS_AWAKENING event",
    )
    negligible_transmission: float = Field(
        default=0.01,
        ge=0.0,
        description="Threshold below which transmissions are skipped",
    )
    superwage_impact: float = Field(
        default=1.0,
        ge=0.0,
        description="How much imperial extraction affects Core wealth",
    )


class BehavioralDefines(BaseModel):
    """Behavioral economics coefficients."""

    model_config = ConfigDict(frozen=True)

    loss_aversion_lambda: float = Field(
        default=2.25,
        gt=0.0,
        description="Kahneman-Tversky loss aversion coefficient",
    )


class TensionDefines(BaseModel):
    """Tension dynamics coefficients."""

    model_config = ConfigDict(frozen=True)

    accumulation_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Rate at which tension accumulates from wealth gaps",
    )


class ConsciousnessDefines(BaseModel):
    """Consciousness drift coefficients."""

    model_config = ConfigDict(frozen=True)

    sensitivity: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How quickly consciousness responds to material conditions",
    )
    decay_lambda: float = Field(
        default=0.1,
        gt=0.0,
        description="Decay rate for consciousness without material basis",
    )


class TerritoryDefines(BaseModel):
    """Territory dynamics coefficients."""

    model_config = ConfigDict(frozen=True)

    heat_decay_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Heat decay for LOW_PROFILE territories",
    )
    high_profile_heat_gain: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Heat gain for HIGH_PROFILE territories",
    )
    eviction_heat_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Heat threshold for eviction pipeline",
    )
    rent_spike_multiplier: float = Field(
        default=1.5,
        gt=0.0,
        description="Rent multiplier during eviction",
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
        description="Heat spillover via ADJACENCY edges",
    )
    clarity_profile_coefficient: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Clarity bonus for HIGH_PROFILE territories",
    )


class StruggleDefines(BaseModel):
    """Struggle dynamics coefficients (Agency Layer - "George Floyd" Dynamic).

    The Struggle System gives political agency to oppressed classes by modeling:
    - The Spark: State violence (EXCESSIVE_FORCE) triggers insurrection
    - The Combustion: Spark + High Agitation + Low P(S|A) = UPRISING
    - The Result: Uprisings destroy wealth but build solidarity infrastructure
    """

    model_config = ConfigDict(frozen=True)

    spark_probability_scale: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Base 10% chance scaled by repression_faced for EXCESSIVE_FORCE",
    )
    resistance_threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Minimum agitation level for uprising to trigger",
    )
    wealth_destruction_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Fraction of wealth destroyed during uprising (riot damage)",
    )
    solidarity_gain_per_uprising: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Solidarity strength increase on edges per uprising",
    )


class InitialDefines(BaseModel):
    """Initial condition coefficients."""

    model_config = ConfigDict(frozen=True)

    worker_wealth: float = Field(
        default=0.5,
        ge=0.0,
        description="Starting wealth for periphery worker",
    )
    owner_wealth: float = Field(
        default=0.5,
        ge=0.0,
        description="Starting wealth for core owner",
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
    - economy: Imperial rent extraction and value flow
    - survival: P(S|A) and P(S|R) survival calculus
    - solidarity: Consciousness transmission
    - behavioral: Behavioral economics (loss aversion)
    - tension: Tension dynamics
    - consciousness: Consciousness drift
    - territory: Territory dynamics
    - struggle: Struggle dynamics (Agency Layer)
    - initial: Initial conditions
    """

    model_config = ConfigDict(frozen=True)

    economy: EconomyDefines = Field(default_factory=EconomyDefines)
    survival: SurvivalDefines = Field(default_factory=SurvivalDefines)
    solidarity: SolidarityDefines = Field(default_factory=SolidarityDefines)
    behavioral: BehavioralDefines = Field(default_factory=BehavioralDefines)
    tension: TensionDefines = Field(default_factory=TensionDefines)
    consciousness: ConsciousnessDefines = Field(default_factory=ConsciousnessDefines)
    territory: TerritoryDefines = Field(default_factory=TerritoryDefines)
    struggle: StruggleDefines = Field(default_factory=StruggleDefines)
    initial: InitialDefines = Field(default_factory=InitialDefines)

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

        return cls(
            economy=EconomyDefines(**data.get("economy", {})),
            survival=SurvivalDefines(**data.get("survival", {})),
            solidarity=SolidarityDefines(**data.get("solidarity", {})),
            behavioral=BehavioralDefines(**data.get("behavioral", {})),
            tension=TensionDefines(**data.get("tension", {})),
            consciousness=ConsciousnessDefines(**data.get("consciousness", {})),
            territory=TerritoryDefines(**data.get("territory", {})),
            struggle=StruggleDefines(**data.get("struggle", {})),
            initial=InitialDefines(**data.get("initial", {})),
        )

    @classmethod
    def default_yaml_path(cls) -> Path:
        """Return the default path to defines.yaml.

        Returns:
            Path to src/babylon/data/defines.yaml
        """
        return Path(__file__).parent.parent / "data" / "defines.yaml"

    @classmethod
    def load_default(cls) -> GameDefines:
        """Load GameDefines from the default YAML location.

        Falls back to default values if file doesn't exist.

        Returns:
            GameDefines instance
        """
        default_path = cls.default_yaml_path()
        if default_path.exists():
            return cls.load_from_yaml(default_path)
        return cls()
