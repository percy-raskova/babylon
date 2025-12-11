"""Scenario configuration for multiverse simulation injection.

ScenarioConfig holds parameters that modify a simulation's starting conditions
to explore different counterfactual paths. This enables the "Multiverse Protocol"
where we run 2^N permutations of High/Low values to prove mathematical divergence.

Sprint 1 (Multiverse Protocol): Initial implementation with three parameters:

- superwage_multiplier: Multiplier for imperial superwage extraction efficiency
- solidarity_index: Base strength for SOLIDARITY edges
- repression_capacity: State violence capacity modifier

Paradox Refactor: Renamed rent_level -> superwage_multiplier for theory alignment.
The term "superwage" (from MLM-TW theory) more accurately describes the mechanism
where core workers receive wages above value produced, subsidized by imperial rent.

Usage::

    from babylon.models.scenario import ScenarioConfig

    scenario = ScenarioConfig(
        name="HighSW_LowSol_HighRep",
        superwage_multiplier=1.5,
        solidarity_index=0.2,
        repression_capacity=0.8,
    )
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.types import Coefficient


class ScenarioConfig(BaseModel):
    """Configuration for multiverse scenario injection.

    ScenarioConfig defines modifiers that transform a base WorldState and
    SimulationConfig into a specific counterfactual scenario. This enables
    deterministic exploration of parameter space without random sampling.

    The model is frozen (immutable) to ensure scenarios remain constant
    throughout simulation runs.

    Attributes:
        name: Human-readable scenario identifier, must be unique within
              a multiverse run. Format: "{SWLevel}_{SolidarityLevel}_{RepressionLevel}"
        superwage_multiplier: Multiplier for extraction_efficiency in SimulationConfig.
                             Default 1.0 (no change). Range: [0, inf).
                             - 0.3 = Low superwage (periphery retains more value)
                             - 1.5 = High superwage (aggressive extraction)
                             Theory: "Superwage" refers to core worker wages above
                             value produced, subsidized by imperial rent extraction.
        solidarity_index: Base strength for SOLIDARITY edges in topology.
                         Default 0.5. Constrained to [0, 1] via Coefficient type.
                         - 0.2 = Low solidarity (atomized workers)
                         - 0.8 = High solidarity (strong worker networks)
        repression_capacity: State violence capacity modifier.
                            Updates repression_faced on entities and repression_level in config.
                            Default 0.5. Constrained to [0, 1] via Coefficient type.
                            - 0.2 = Low repression (weak state)
                            - 0.8 = High repression (police state)
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(
        ...,
        min_length=1,
        description="Human-readable scenario name (must be unique in multiverse)",
    )

    superwage_multiplier: float = Field(
        default=1.0,
        ge=0.0,
        description="Multiplier for imperial superwage extraction efficiency [0, inf)",
    )

    solidarity_index: Coefficient = Field(
        default=0.5,
        description="Base strength for SOLIDARITY edges [0, 1]",
    )

    repression_capacity: Coefficient = Field(
        default=0.5,
        description="State violence capacity modifier [0, 1]",
    )
