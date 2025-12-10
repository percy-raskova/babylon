"""Scenario configuration for multiverse simulation injection.

ScenarioConfig holds parameters that modify a simulation's starting conditions
to explore different counterfactual paths. This enables the "Multiverse Protocol"
where we run 2^N permutations of High/Low values to prove mathematical divergence.

Sprint 1 (Multiverse Protocol): Initial implementation with three parameters:
- rent_level: Multiplier for imperial rent extraction efficiency
- solidarity_index: Base strength for SOLIDARITY edges
- repression_capacity: State violence capacity modifier

Usage:
    from babylon.models.scenario import ScenarioConfig

    scenario = ScenarioConfig(
        name="HighRent_LowSol_HighRep",
        rent_level=1.5,
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
              a multiverse run. Format: "{RentLevel}_{SolidarityLevel}_{RepressionLevel}"
        rent_level: Multiplier for extraction_efficiency in SimulationConfig.
                   Default 1.0 (no change). Range: [0, inf).
                   - 0.3 = Low rent (periphery retains more value)
                   - 1.5 = High rent (aggressive extraction)
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

    rent_level: float = Field(
        default=1.0,
        ge=0.0,
        description="Multiplier for imperial rent extraction efficiency [0, inf)",
    )

    solidarity_index: Coefficient = Field(
        default=0.5,
        description="Base strength for SOLIDARITY edges [0, 1]",
    )

    repression_capacity: Coefficient = Field(
        default=0.5,
        description="State violence capacity modifier [0, 1]",
    )
