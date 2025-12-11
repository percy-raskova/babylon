"""Topology metrics data models for the Condensation Monitor (Sprint 3.1).

These Pydantic models capture the state of the solidarity network at each tick,
enabling phase transition detection using percolation theory.

Models:
    TopologySnapshot: Metrics snapshot at a specific tick
    ResilienceResult: Result of purge simulation (Sword of Damocles)

Theoretical Background:
    - Gaseous State: Many small components, percolation < 0.5
    - Liquid State: Giant component spans majority, percolation >= 0.5
    - Phase Shift: The tick where percolation crosses threshold
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.types import Probability


class TopologySnapshot(BaseModel):
    """Metrics snapshot of the solidarity subgraph at a specific tick.

    Captures the topological state of SOLIDARITY edges in the social graph,
    enabling detection of phase transitions from atomized (gaseous) to
    condensed (liquid) movement states.

    Attributes:
        tick: Simulation tick when snapshot was taken
        num_components: Number of disconnected subgraphs (solidarity cells)
        max_component_size: Size of the largest connected component (L_max)
        total_nodes: Total number of social_class nodes (N)
        percolation_ratio: L_max / N, measures giant component dominance
        potential_liquidity: Count of SOLIDARITY edges > 0.1 (sympathizers)
        actual_liquidity: Count of SOLIDARITY edges > 0.5 (cadre)
        is_resilient: Whether movement survives 20% purge (optional)

    Interpretation:
        - percolation_ratio < 0.1: Gaseous (atomized, vulnerable to purge)
        - percolation_ratio >= 0.5: Liquid (condensed, vanguard formed)
        - potential >> actual: Broad but brittle (lacks cadre discipline)
    """

    model_config = ConfigDict(frozen=True)

    tick: int = Field(ge=0, description="Simulation tick when snapshot was taken")
    num_components: int = Field(ge=0, description="Number of disconnected subgraphs")
    max_component_size: int = Field(ge=0, description="Size of largest component (L_max)")
    total_nodes: int = Field(ge=0, description="Total social_class nodes (N)")
    percolation_ratio: Probability = Field(
        description="L_max / N, giant component dominance [0, 1]"
    )
    potential_liquidity: int = Field(ge=0, description="SOLIDARITY edges > 0.1 (sympathizers)")
    actual_liquidity: int = Field(ge=0, description="SOLIDARITY edges > 0.5 (cadre)")
    is_resilient: bool | None = Field(
        default=None, description="Survives 20% purge (None if not tested)"
    )


class ResilienceResult(BaseModel):
    """Result of purge simulation (Sword of Damocles test).

    Tests whether the solidarity network survives targeted removal of
    a percentage of nodes. A resilient network maintains its giant
    component after losing key members.

    Attributes:
        is_resilient: True if post-purge L_max > threshold of original L_max
        original_max_component: Size of L_max before purge
        post_purge_max_component: Size of L_max after purge
        removal_rate: Fraction of nodes removed (e.g., 0.2 = 20%)
        survival_threshold: Required fraction of original L_max to survive
        seed: RNG seed for reproducibility (None if random)

    Interpretation:
        - is_resilient=True: Network can survive targeted repression
        - is_resilient=False: "Sword of Damocles" - purge would destroy movement
    """

    model_config = ConfigDict(frozen=True)

    is_resilient: bool = Field(description="Whether network survived the purge")
    original_max_component: int = Field(ge=0, description="L_max before purge")
    post_purge_max_component: int = Field(ge=0, description="L_max after purge")
    removal_rate: float = Field(ge=0.0, le=1.0, description="Fraction of nodes removed")
    survival_threshold: float = Field(
        ge=0.0, le=1.0, description="Required fraction of original L_max"
    )
    seed: int | None = Field(default=None, description="RNG seed for reproducibility")
