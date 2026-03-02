"""Attention thread and Sparrow analysis entity models (Feature 039).

Defines:
- AttentionThread: State intelligence resource tracking a specific target
- SparrowAnalysis: Network vulnerability analysis results on G_observed

All models are frozen (immutable) Pydantic BaseModels.

See Also:
    ``specs/039-state-apparatus-ai/data-model.md``: Entity definitions.
    :mod:`babylon.models.entities.state_apparatus_ai`: FactionBalance, StateAction, etc.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.models.enums import SurveillanceMethod, ThreadPhase
from babylon.models.types import Probability

#: Valid target types for attention threads.
VALID_TARGET_TYPES: frozenset[str] = frozenset(
    {
        "organization",
        "territory",
        "community",
    }
)


class AttentionThread(BaseModel):
    """State intelligence resource tracking a specific target (Feature 039).

    Each thread maintains a growing G_observed subgraph (always incomplete,
    always distorted) of the target. Thread pool size derives from the sum
    of surveillance_capacity across all StateApparatus nodes. Sparrow
    analysis operates on G_observed per thread.

    Attributes:
        thread_id: Unique identifier for this attention thread.
        target_type: Type of target entity.
        target_id: ID of target entity.
        phase: Current intelligence phase.
        intensity: Resource allocation intensity [0,1].
        intel_completeness: Accumulated intelligence [0,1].
        surveillance_methods: Active collection methods.
        observed_node_ids: Node IDs discovered in G_observed.
        observed_edge_ids: Edge ID pairs discovered in G_observed.
        stickiness: Resistance to reallocation by meta-OODA [0,1].
        ticks_active: Ticks since thread allocation.
        owning_apparatus_id: StateApparatus that owns this thread.

    Reference: FR-A01 through FR-A08, R-002, R-007.
    """

    model_config = ConfigDict(frozen=True)

    thread_id: str = Field(min_length=1, description="Unique thread identifier")
    target_type: str = Field(description="Target entity type")
    target_id: str = Field(min_length=1, description="ID of target entity")
    phase: ThreadPhase = Field(description="Current intelligence phase")
    intensity: Probability = Field(description="Resource allocation intensity [0,1]")
    intel_completeness: Probability = Field(
        description="Accumulated intelligence level [0,1]",
    )
    surveillance_methods: list[SurveillanceMethod] = Field(
        default_factory=list,
        description="Active collection methods",
    )
    observed_node_ids: frozenset[str] = Field(
        default_factory=frozenset,
        description="Node IDs in G_observed",
    )
    observed_edge_ids: frozenset[tuple[str, str]] = Field(
        default_factory=frozenset,
        description="Edge ID pairs in G_observed",
    )
    stickiness: Probability = Field(
        description="Resistance to reallocation [0=easily moved, 1=locked]",
    )
    ticks_active: int = Field(ge=0, description="Ticks since thread allocation")
    owning_apparatus_id: str = Field(
        min_length=1,
        description="StateApparatus that owns this thread",
    )

    @model_validator(mode="after")
    def _validate_target_type(self) -> Self:
        """Validate target_type is a recognized entity type."""
        if self.target_type not in VALID_TARGET_TYPES:
            msg = f"target_type must be one of {sorted(VALID_TARGET_TYPES)}, got {self.target_type}"
            raise ValueError(msg)
        return self


class SparrowAnalysis(BaseModel):
    """Network vulnerability analysis results on G_observed (Feature 039).

    Implements Sparrow's framework: centrality computation, equivalence
    class identification, singleton detection, and minimal cutset analysis.
    All results are contingent on G_observed quality -- they may be wrong
    because the state's view is always incomplete.

    This is a COMPUTED artifact -- derived from G_observed, not stored in
    the graph. Constitution II.2: derived state, not primitive.

    Attributes:
        thread_id: Source thread ID.
        tick: Tick of computation.
        centrality_rankings: Per-node centrality scores.
        equivalence_classes: Groups of structurally equivalent nodes.
        identified_singletons: Nodes in singleton equivalence classes.
        known_cutsets: Minimal node cutsets in G_observed.
        confidence: Analysis confidence based on intel_completeness [0,1].

    Reference: FR-A03, R-002.
    """

    model_config = ConfigDict(frozen=True)

    thread_id: str = Field(min_length=1, description="Source thread ID")
    tick: int = Field(ge=0, description="Tick of computation")
    centrality_rankings: dict[str, dict[str, float]] = Field(
        description="node_id -> {metric_name: score}",
    )
    equivalence_classes: list[frozenset[str]] = Field(
        description="Groups of structurally equivalent nodes",
    )
    identified_singletons: frozenset[str] = Field(
        description="Nodes in singleton equivalence classes",
    )
    known_cutsets: list[frozenset[str]] = Field(
        description="Minimal node cutsets in G_observed",
    )
    confidence: Probability = Field(
        description="Analysis confidence based on intel_completeness [0,1]",
    )
