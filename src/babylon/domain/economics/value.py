"""Marxian value categories: Use-value, Exchange-value, Concrete labor, and Abstract labor.

These models represent the fundamental dualities in Marx's Capital Volume I.
They are pure data models defining the properties of commodities and labor.
"""

from pydantic import BaseModel, ConfigDict, Field


class UseValue(BaseModel):
    """Properties of a commodity as use-value (V1 Ch1).

    Attributes:
        utility: How useful the commodity is to its possessor, ∈ [0, 1].
        demand: Aggregate demand (labor-hours or units).
    """

    model_config = ConfigDict(frozen=True)

    utility: float = Field(default=0.5, ge=0.0, le=1.0)
    demand: float = Field(default=0.0, ge=0.0)


class ExchangeValue(BaseModel):
    """Properties of a commodity as exchange-value (V1 Ch1).

    Attributes:
        price: Monetary price of the commodity.
        snlt: Socially Necessary Labour Time embodied.
    """

    model_config = ConfigDict(frozen=True)

    price: float = Field(default=0.0, ge=0.0)
    snlt: float = Field(default=0.0, ge=0.0)


class ConcreteLabor(BaseModel):
    """Properties of labor as concrete, particular activity (V1 Ch1§2).

    Concrete labor creates use-values: spinning produces yarn, weaving
    produces cloth. It is labor in its specific, qualitative form.

    Attributes:
        skill: Worker skill level ∈ [0, 1].
        intensity: Labor intensity ∈ [0, 1].
        hours: Hours of concrete labor performed.
        labor_type: Qualitative type of labor (spinning, mining, etc.).
    """

    model_config = ConfigDict(frozen=True)

    skill: float = Field(default=0.5, ge=0.0, le=1.0)
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    hours: float = Field(default=0.0, ge=0.0)
    labor_type: str = Field(default="general")


class AbstractLabor(BaseModel):
    """Properties of labor as abstract, homogeneous substance (V1 Ch1§2).

    Abstract labor is the social substance of value — labor stripped of
    its concrete characteristics and reduced to expenditure of human
    labor-power in general.

    Attributes:
        snlt: Socially Necessary Labour Time embodied.
        productivity: Labor productivity multiplier (> 1.0 = above average).
    """

    model_config = ConfigDict(frozen=True)

    snlt: float = Field(default=0.0, ge=0.0)
    productivity: float = Field(default=1.0, gt=0.0)
