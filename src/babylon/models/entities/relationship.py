"""Relationship entity model.

A Relationship is the fundamental edge type in the Babylon simulation.
It represents a directed relationship between two entities (typically SocialClasses).

Relationships encode:
1. Value flows (imperial rent, unequal exchange)
2. Social dynamics (solidarity, repression, competition)
3. Dialectical tension (accumulated contradiction intensity)

This is the Phase 1 edge type from the four-phase blueprint.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.models.enums import EdgeType
from babylon.models.types import Currency, Intensity


class FlowComponent(BaseModel):
    """Value flow and tension state of a relationship."""

    model_config = ConfigDict(frozen=True)

    value_flow: Currency = Field(default=0.0, description="Imperial rent (Phi)")
    tension: Intensity = Field(default=0.0, description="Dialectical tension")


class Relationship(BaseModel):
    """A directed edge between two entities.

    Represents flows of value, solidarity, or repression between classes.
    In Phase 1, the primary relationship is exploitation: value flows
    from the periphery worker (source) to the core owner (target).

    This model uses Sprint 1 constrained types for automatic validation:
    - Currency: [0, inf) for value_flow
    - Intensity: [0, 1] for tension

    Attributes:
        source_id: Origin entity ID (value/action flows FROM here)
        target_id: Destination entity ID (value/action flows TO here)
        edge_type: Nature of the relationship (EdgeType enum)
        value_flow: Imperial rent or value transfer amount (Currency, default 0.0)
        tension: Dialectical tension/contradiction intensity (Intensity, default 0.0)
        description: Optional description of the relationship
    """

    model_config = ConfigDict(
        extra="forbid",  # Reject unknown fields
        validate_assignment=True,  # Validate on attribute mutation
        str_strip_whitespace=True,  # Clean string inputs
    )

    @model_validator(mode="before")
    @classmethod
    def unpack_flow_component(cls, data: Any) -> Any:
        """Unpack flow component into flat fields if provided."""
        if not isinstance(data, dict):
            return data

        if "flow" in data:
            flow = data.pop("flow")
            if isinstance(flow, FlowComponent):
                flow = flow.model_dump()
            elif not isinstance(flow, dict):
                raise ValueError("flow must be FlowComponent or dict")
            data.setdefault("value_flow", flow.get("value_flow", 0.0))
            data.setdefault("tension", flow.get("tension", 0.0))

        return data

    # Required fields
    source_id: str = Field(
        ...,
        min_length=1,
        description="Origin entity ID (value flows FROM here)",
    )
    target_id: str = Field(
        ...,
        min_length=1,
        description="Destination entity ID (value flows TO here)",
    )
    edge_type: EdgeType = Field(
        ...,
        description="Nature of the relationship",
    )

    # Value flows
    value_flow: Currency = Field(
        default=0.0,
        description="Imperial rent or value transfer amount (Φ)",
    )

    # Relational state
    tension: Intensity = Field(
        default=0.0,
        description="Dialectical tension / contradiction intensity",
    )

    # Metadata
    description: str = Field(
        default="",
        description="Description of this relationship",
    )

    @model_validator(mode="after")
    def validate_no_self_loop(self) -> "Relationship":
        """Ensure entities cannot have a relationship with themselves."""
        if self.source_id == self.target_id:
            raise ValueError(
                f"Self-loops not allowed: source_id and target_id are both '{self.source_id}'"
            )
        return self

    @property
    def edge_tuple(self) -> tuple[str, str]:
        """Return (source_id, target_id) tuple for NetworkX edge creation.

        Usage:
            G.add_edge(*relationship.edge_tuple, **relationship.edge_data)
        """
        return (self.source_id, self.target_id)

    @property
    def edge_data(self) -> dict[str, object]:
        """Return edge attributes dict for NetworkX, excluding IDs.

        Usage:
            G.add_edge(*relationship.edge_tuple, **relationship.edge_data)
        """
        return self.model_dump(exclude={"source_id", "target_id"})

    @property
    def flow(self) -> FlowComponent:
        """Return flow component view (computed, not live)."""
        return FlowComponent(
            value_flow=self.value_flow,
            tension=self.tension,
        )
