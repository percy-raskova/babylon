"""State Apparatus AI entity models (Feature 039).

Defines entity models for the state-as-adversary system:
- FactionBalance: Power distribution among ruling-class factions
- StateBudget: Fiscal constraint on state action
- StateAction: State verb execution instance
- LegalFramework: Active legislation modifying game rules
- VERB_CHILDREN: Parent-child verb hierarchy mapping

All models are frozen (immutable) Pydantic BaseModels.

See Also:
    ``specs/039-state-apparatus-ai/data-model.md``: Entity definitions.
    :mod:`babylon.models.entities.attention_thread`: AttentionThread, SparrowAnalysis.
"""

from __future__ import annotations

from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from babylon.models.enums import StateActionType, StateFaction
from babylon.models.types import Probability

# =============================================================================
# VERB_CHILDREN: Parent-child verb hierarchy (R-005)
# =============================================================================

#: Source of truth for hierarchy validation. Each top-level verb maps to
#: its valid sub-verbs. Used by StateAction model validator.
VERB_CHILDREN: dict[StateActionType, frozenset[StateActionType]] = {
    StateActionType.ADMINISTER: frozenset(
        {
            StateActionType.FUND,
            StateActionType.STAFF,
            StateActionType.LEGISLATE,
            StateActionType.AUDIT,
            StateActionType.REVOKE,
        }
    ),
    StateActionType.DEVELOP: frozenset(
        {
            StateActionType.INVEST,
            StateActionType.REZONE,
            StateActionType.DISPLACE,
            StateActionType.NEGLECT,
        }
    ),
    StateActionType.RESEARCH: frozenset(
        {
            StateActionType.PURSUE_TECH,
            StateActionType.DEPLOY_TECH,
        }
    ),
    StateActionType.CO_OPT: frozenset(
        {
            StateActionType.BRIBE,
            StateActionType.PROPAGANDIZE,
            StateActionType.INCORPORATE,
            StateActionType.DIVIDE,
        }
    ),
    StateActionType.REPRESS: frozenset(
        {
            StateActionType.SURVEIL,
            StateActionType.INFILTRATE,
            StateActionType.RAID,
            StateActionType.PROSECUTE,
            StateActionType.LIQUIDATE,
        }
    ),
    StateActionType.WITHDRAW: frozenset(
        {
            StateActionType.STRATEGIC_WITHDRAWAL,
            StateActionType.TACTICAL_RETREAT,
            StateActionType.SCORCHED_EARTH,
        }
    ),
}

#: Set of top-level verbs (keys of VERB_CHILDREN).
TOP_LEVEL_VERBS: frozenset[StateActionType] = frozenset(VERB_CHILDREN.keys())

#: Set of all sub-verbs (union of all VERB_CHILDREN values).
ALL_SUB_VERBS: frozenset[StateActionType] = frozenset().union(*VERB_CHILDREN.values())


def get_parent_verb(sub_verb: StateActionType) -> StateActionType | None:
    """Look up the parent verb of a sub-verb.

    Args:
        sub_verb: A StateActionType that may be a sub-verb.

    Returns:
        The top-level parent verb, or None if the input is itself a top-level verb
        or not found in any parent's children.
    """
    max_parents = len(VERB_CHILDREN)
    for checked, (parent, children) in enumerate(VERB_CHILDREN.items()):
        if checked >= max_parents:
            break
        if sub_verb in children:
            return parent
    return None


# =============================================================================
# FactionBalance
# =============================================================================


class FactionBalance(BaseModel):
    """Power distribution among ruling-class factions (Feature 039).

    The weight vector determines the state's objective function for
    verb selection. Shifts based on player actions (FR-C04) and
    material conditions (FR-C05). Fascist convergence is detected
    when specific threshold conditions hold (FR-C06).

    Primitive state: finance_capital, security_state, settler_populist,
    stability, legitimacy (stored).
    Derived state: dominant_faction (computed). Constitution II.2.

    Attributes:
        finance_capital: Weight of Finance-Capital faction [0.0, 1.0].
        security_state: Weight of Security-State faction [0.0, 1.0].
        settler_populist: Weight of Settler-Populist faction [0.0, 1.0].
        stability: How stable the current balance is [0=turbulent, 1=settled].
        legitimacy: Overall state legitimacy [0=delegitimized, 1=fully legitimate].

    Reference: FR-C02, R-003.
    """

    model_config = ConfigDict(frozen=True)

    finance_capital: float = Field(
        ge=0.0,
        le=1.0,
        description="Weight of Finance-Capital faction [0.0, 1.0]",
    )
    security_state: float = Field(
        ge=0.0,
        le=1.0,
        description="Weight of Security-State faction [0.0, 1.0]",
    )
    settler_populist: float = Field(
        ge=0.0,
        le=1.0,
        description="Weight of Settler-Populist faction [0.0, 1.0]",
    )
    stability: Probability = Field(
        description="How stable the current balance is [0=turbulent, 1=settled]",
    )
    legitimacy: Probability = Field(
        description="Overall state legitimacy [0=delegitimized, 1=fully legitimate]",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def dominant_faction(self) -> StateFaction:
        """Faction with highest weight."""
        weights = {
            StateFaction.FINANCE_CAPITAL: self.finance_capital,
            StateFaction.SECURITY_STATE: self.security_state,
            StateFaction.SETTLER_POPULIST: self.settler_populist,
        }
        return max(weights, key=lambda k: weights[k])

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> Self:
        """Validate faction weights sum to 1.0."""
        total = self.finance_capital + self.security_state + self.settler_populist
        if not (0.99 <= total <= 1.01):
            msg = f"Faction weights must sum to 1.0, got {total}"
            raise ValueError(msg)
        return self


# =============================================================================
# StateBudget
# =============================================================================


class StateBudget(BaseModel):
    """State budget constraint for verb execution (Feature 039).

    Revenue derives from tax revenue, federal transfers, and imperial
    rent pool. Allocation across verb categories is computed each tick
    as the dot product of faction weights and faction verb preferences.

    Budget is finite -- the fundamental constraint making state behavior
    strategic rather than omnipotent.

    Attributes:
        revenue: Total income this tick.
        available: Unallocated funds remaining this tick.
        allocated: Budget allocated per top-level verb category.
        imperial_rent_pool: Discretionary capacity from imperial rent.

    Reference: FR-D05, R-004.
    """

    model_config = ConfigDict(frozen=True)

    revenue: float = Field(
        ge=0.0,
        description="Total income this tick",
    )
    available: float = Field(
        ge=0.0,
        description="Unallocated funds remaining this tick",
    )
    allocated: dict[StateActionType, float] = Field(
        description="Budget allocated per top-level verb category",
    )
    imperial_rent_pool: float = Field(
        ge=0.0,
        description="Discretionary capacity from imperial rent",
    )

    @model_validator(mode="after")
    def _validate_budget(self) -> Self:
        """Validate budget constraints."""
        if self.available > self.revenue + 0.01:
            msg = f"available ({self.available}) cannot exceed revenue ({self.revenue})"
            raise ValueError(msg)
        for key, val in self.allocated.items():
            if key not in TOP_LEVEL_VERBS:
                msg = f"Allocation key must be a top-level verb, got {key}"
                raise ValueError(msg)
            if val < 0.0:
                msg = f"Allocation for {key} must be >= 0, got {val}"
                raise ValueError(msg)
        if sum(self.allocated.values()) > self.revenue + 0.01:
            msg = "Sum of allocations cannot exceed revenue"
            raise ValueError(msg)
        return self


# =============================================================================
# StateAction
# =============================================================================


class StateAction(BaseModel):
    """State verb execution instance (Feature 039).

    Parallel to the player Action model (Feature 032) but with different
    resource profiles. Budget constrains non-REPRESS verbs; attention
    threads constrain REPRESS verbs (Assumption A-004).

    Attributes:
        verb: Top-level verb category.
        sub_verb: Specific sub-verb within the verb category.
        target_id: Target entity ID (None for self-targeting).
        budget_cost: Budget consumed by this action.
        thread_cost: Attention threads required (for REPRESS verbs).
        legitimacy_cost: Legitimacy impact (negative = delegitimizing).
        faction_alignment: Which faction benefits from this action.
        parameters: Sub-verb-specific parameters.

    Reference: FR-B01 through FR-B11, FR-D05, R-005.
    """

    model_config = ConfigDict(frozen=True)

    verb: StateActionType = Field(description="Top-level verb category")
    sub_verb: StateActionType = Field(description="Specific sub-verb")
    target_id: str | None = Field(
        default=None,
        description="Target entity ID (None for self-targeting)",
    )
    budget_cost: float = Field(ge=0.0, description="Budget consumed")
    thread_cost: int = Field(ge=0, description="Attention threads required")
    legitimacy_cost: float = Field(
        description="Legitimacy impact (negative = delegitimizing)",
    )
    faction_alignment: StateFaction = Field(
        description="Which faction benefits from this action",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Sub-verb-specific parameters",
    )

    @model_validator(mode="after")
    def _validate_verb_hierarchy(self) -> Self:
        """Validate sub_verb is a valid child of verb."""
        if self.verb not in TOP_LEVEL_VERBS:
            msg = f"verb must be a top-level verb, got {self.verb}"
            raise ValueError(msg)
        children = VERB_CHILDREN.get(self.verb, frozenset())
        if self.sub_verb not in children:
            msg = f"{self.sub_verb} is not a valid sub-verb of {self.verb}"
            raise ValueError(msg)
        return self


# =============================================================================
# LegalFramework
# =============================================================================

#: Valid law types for LegalFramework.
VALID_LAW_TYPES: frozenset[str] = frozenset(
    {
        "SURVEILLANCE_EXPANSION",
        "CRIMINALIZATION",
        "EMERGENCY_POWERS",
        "ZONING_CHANGE",
        "TAX_INCENTIVE",
        "LABOR_RESTRICTION",
    }
)


class LegalFramework(BaseModel):
    """Active legislation modifying game rules in a jurisdiction (Feature 039).

    Created by LEGISLATE sub-action, removed by REVOKE sub-action.
    No automatic expiry -- legislation persists until explicitly revoked.
    Revocation carries its own legitimacy cost/gain depending on context.

    Attributes:
        framework_id: Unique framework identifier.
        law_type: Legislation category.
        scope: Jurisdiction scope (JurisdictionLevel value).
        severity: How extreme the legislation is [0=mild, 1=extreme].
        effects: Rule modifications applied (varies by law_type).
        created_tick: Tick when enacted.
        creating_apparatus_id: Apparatus that enacted this.

    Reference: FR-B09, R-011.
    """

    model_config = ConfigDict(frozen=True)

    framework_id: str = Field(
        min_length=1,
        description="Unique framework identifier",
    )
    law_type: str = Field(
        description="Legislation category",
    )
    scope: str = Field(
        description="Jurisdiction scope (JurisdictionLevel value)",
    )
    severity: Probability = Field(
        description="How extreme the legislation is [0=mild, 1=extreme]",
    )
    effects: dict[str, float] = Field(
        description="Rule modifications applied (varies by law_type)",
    )
    created_tick: int = Field(
        ge=0,
        description="Tick when enacted",
    )
    creating_apparatus_id: str = Field(
        min_length=1,
        description="Apparatus that enacted this",
    )

    @model_validator(mode="after")
    def _validate_law_type(self) -> Self:
        """Validate law_type is a recognized category."""
        if self.law_type not in VALID_LAW_TYPES:
            msg = f"law_type must be one of {sorted(VALID_LAW_TYPES)}, got {self.law_type}"
            raise ValueError(msg)
        return self
