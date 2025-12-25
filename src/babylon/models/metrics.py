"""Metrics data models for simulation observation and analysis.

These Pydantic models define the contract for MetricsCollector output,
enabling unified metrics collection between the parameter sweeper and
dashboard components.

Sprint 4.1: Phase 4 Dashboard/Sweeper unification.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.types import Currency, Probability


class EntityMetrics(BaseModel):
    """Metrics snapshot for a single entity at a specific tick.

    Captures wealth, consciousness, and survival probabilities for
    analysis and visualization.
    """

    model_config = ConfigDict(frozen=True)

    wealth: Currency = Field(
        ge=0.0,
        description="Entity wealth (Currency >= 0)",
    )
    consciousness: Probability = Field(
        ge=0.0,
        le=1.0,
        description="Class consciousness [0, 1]",
    )
    national_identity: Probability = Field(
        ge=0.0,
        le=1.0,
        description="National identity [0, 1]",
    )
    agitation: Probability = Field(
        ge=0.0,
        le=1.0,
        description="Agitation level [0, 1]",
    )
    p_acquiescence: Probability = Field(
        ge=0.0,
        le=1.0,
        description="P(S|A) - probability of survival through acquiescence [0, 1]",
    )
    p_revolution: Probability = Field(
        ge=0.0,
        le=1.0,
        description="P(S|R) - probability of survival through revolution [0, 1]",
    )
    organization: Probability = Field(
        ge=0.0,
        le=1.0,
        description="Organization level [0, 1]",
    )


class EdgeMetrics(BaseModel):
    """Metrics snapshot for relationship edges at a specific tick.

    Captures tension, value flows, and solidarity strength for
    analysis and visualization.
    """

    model_config = ConfigDict(frozen=True)

    exploitation_tension: Probability = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Tension on EXPLOITATION edge [0, 1]",
    )
    exploitation_rent: Currency = Field(
        default=0.0,
        ge=0.0,
        description="Value flow on EXPLOITATION edge (Currency >= 0)",
    )
    tribute_flow: Currency = Field(
        default=0.0,
        ge=0.0,
        description="Value flow on TRIBUTE edge (Currency >= 0)",
    )
    wages_paid: Currency = Field(
        default=0.0,
        ge=0.0,
        description="Value flow on WAGES edge (Currency >= 0)",
    )
    solidarity_strength: Probability = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Solidarity strength on SOLIDARITY edge [0, 1]",
    )


class TickMetrics(BaseModel):
    """Complete metrics snapshot for a single simulation tick.

    Aggregates entity and edge metrics for comprehensive tick analysis.
    """

    model_config = ConfigDict(frozen=True)

    tick: int = Field(
        ge=0,
        description="Tick number (>= 0)",
    )
    p_w: EntityMetrics | None = Field(
        default=None,
        description="Periphery Worker (C001) metrics",
    )
    p_c: EntityMetrics | None = Field(
        default=None,
        description="Comprador (C002) metrics",
    )
    c_b: EntityMetrics | None = Field(
        default=None,
        description="Core Bourgeoisie (C003) metrics",
    )
    c_w: EntityMetrics | None = Field(
        default=None,
        description="Labor Aristocracy (C004) metrics",
    )
    edges: EdgeMetrics = Field(
        default_factory=EdgeMetrics,
        description="Edge metrics snapshot",
    )
    imperial_rent_pool: Currency = Field(
        default=0.0,
        ge=0.0,
        description="Global imperial rent pool (Currency >= 0)",
    )
    global_tension: Probability = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Average tension across all relationships [0, 1]",
    )


class SweepSummary(BaseModel):
    """Summary statistics for a completed simulation run.

    Aggregates metrics across all ticks for parameter sweep analysis.
    """

    model_config = ConfigDict(frozen=True)

    ticks_survived: int = Field(
        ge=0,
        description="Number of ticks in the simulation (>= 0)",
    )
    outcome: Literal["SURVIVED", "DIED", "ERROR"] = Field(
        description="Simulation outcome",
    )
    final_p_w_wealth: Currency = Field(
        ge=0.0,
        description="Final Periphery Worker wealth (Currency >= 0)",
    )
    final_p_c_wealth: Currency = Field(
        ge=0.0,
        description="Final Comprador wealth (Currency >= 0)",
    )
    final_c_b_wealth: Currency = Field(
        ge=0.0,
        description="Final Core Bourgeoisie wealth (Currency >= 0)",
    )
    final_c_w_wealth: Currency = Field(
        ge=0.0,
        description="Final Labor Aristocracy wealth (Currency >= 0)",
    )
    max_tension: Probability = Field(
        ge=0.0,
        le=1.0,
        description="Maximum tension across all ticks [0, 1]",
    )
    crossover_tick: int | None = Field(
        default=None,
        ge=0,
        description="First tick where P(S|R) > P(S|A), or None if never",
    )
    cumulative_rent: Currency = Field(
        ge=0.0,
        description="Sum of all exploitation rent across ticks (Currency >= 0)",
    )
    peak_p_w_consciousness: Probability = Field(
        ge=0.0,
        le=1.0,
        description="Maximum Periphery Worker consciousness [0, 1]",
    )
    peak_c_w_consciousness: Probability = Field(
        ge=0.0,
        le=1.0,
        description="Maximum Labor Aristocracy consciousness [0, 1]",
    )
