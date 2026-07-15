"""The declared source of truth for round-trip-critical ``WorldState`` fields.

Every field a graph round trip (``to_graph()`` → ``from_graph()``) MUST conserve
value-for-value is declared here as one :class:`RoundTripField`. The Round-Trip
sentinel (``tests/unit/sentinels/test_roundtrip.py``) round-trips the shared tick
artifact's ``final_state`` and asserts each declared field survives unchanged.

**Why a curated core set, not whole-state equality.** ``from_graph`` is lossy by
design: transient per-tick graph attributes (``tick_*`` / ``flow_*``, computed
fields, ``w_paid``/``v_produced``, threat scores) and rich metadata
(``institution_relations``, non-core ``Relationship`` attrs) are dropped on
reconstruction — see ``WorldState.TERRITORY_EXCLUDED_FIELDS`` /
``SOCIAL_CLASS_COMPUTED_FIELDS``. Asserting whole-state equality would red on
that intentional loss. This registry names only the material, load-bearing node
fields that empirically survive today, so a drift on *those* is a real bug (the
tick-52 ``county_fips`` crash class) rather than a false alarm.

The registry grows with the codebase: any new core field a system relies on
surviving a round trip should be declared here, forcing the round-trip contract
to be stated rather than silently assumed.

Dependency-light **by design** (layer 0.5, same rank as :mod:`babylon.config`):
pure declared data — names and node-type tags — carrying no engine, topology, or
``WorldState`` import weight. The round-trip logic that consumes a live
``WorldState`` lives in the test layer above the import boundary.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class RoundTripNodeType(StrEnum):
    """The ``_node_type`` marker a declared field's owning node carries.

    Scopes each declared field to the node collection it is read from, so the
    check knows to compare ``state.entities`` vs ``state.territories``.

    :cvar SOCIAL_CLASS: fields on ``WorldState.entities`` (``SocialClass`` nodes).
    :cvar TERRITORY: fields on ``WorldState.territories`` (``Territory`` nodes).
    """

    SOCIAL_CLASS = "social_class"
    TERRITORY = "territory"


class RoundTripField(BaseModel):
    """One core node field that a graph round trip MUST conserve.

    Frozen and ``extra="forbid"`` so a malformed row is a loud failure at import
    time (Constitution III.11) rather than a silent skip at check time.

    :ivar node_type: the node collection this field lives on
        (:class:`RoundTripNodeType`).
    :ivar field: the model field name, read via ``getattr`` on the node model.
    :ivar rationale: why this field is round-trip-critical (the material
        relation it carries) — provenance for the declaration.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    node_type: RoundTripNodeType
    field: str
    rationale: str


#: SocialClass core fields — identity, the survival-calculus inputs (wealth,
#: population, organization, repression), and the class's spatial anchor
#: (county_fips). Each is read by downstream systems every tick and MUST survive
#: reconstruction; a silent drop is the tick-52 crash class.
_SOCIAL_CLASS_FIELDS: tuple[RoundTripField, ...] = (
    RoundTripField(
        node_type=RoundTripNodeType.SOCIAL_CLASS,
        field="id",
        rationale="node identity — a changed id re-keys the entity and orphans its edges",
    ),
    RoundTripField(
        node_type=RoundTripNodeType.SOCIAL_CLASS,
        field="role",
        rationale="SocialRole partition tag — drives class-specific formula dispatch",
    ),
    RoundTripField(
        node_type=RoundTripNodeType.SOCIAL_CLASS,
        field="wealth",
        rationale="survival-calculus input P(S|A)=Sigmoid(Wealth-Subsistence)",
    ),
    RoundTripField(
        node_type=RoundTripNodeType.SOCIAL_CLASS,
        field="population",
        rationale="aggregation weight for every per-capita → territory rollup",
    ),
    RoundTripField(
        node_type=RoundTripNodeType.SOCIAL_CLASS,
        field="organization",
        rationale="survival-calculus input P(S|R)=Organization/Repression",
    ),
    RoundTripField(
        node_type=RoundTripNodeType.SOCIAL_CLASS,
        field="repression_faced",
        rationale="survival-calculus input P(S|R)=Organization/Repression",
    ),
    RoundTripField(
        node_type=RoundTripNodeType.SOCIAL_CLASS,
        field="ideology",
        rationale="consciousness state carried across ticks by ConsciousnessSystem",
    ),
    RoundTripField(
        node_type=RoundTripNodeType.SOCIAL_CLASS,
        field="county_fips",
        rationale="spatial anchor tying the class to its county economy (tick-52 crash field)",
    ),
)

#: Territory core fields — identity + spatial keys (county_fips, h3_index), the
#: metabolic-rift stocks (biocapacity), and the material base (population,
#: wealth, heat, extraction_intensity) every consequence system reads.
_TERRITORY_FIELDS: tuple[RoundTripField, ...] = (
    RoundTripField(
        node_type=RoundTripNodeType.TERRITORY,
        field="id",
        rationale="node identity — a changed id orphans the territory's edges",
    ),
    RoundTripField(
        node_type=RoundTripNodeType.TERRITORY,
        field="county_fips",
        rationale="FIPS join key to the county economy (the tick-52 crash field)",
    ),
    RoundTripField(
        node_type=RoundTripNodeType.TERRITORY,
        field="h3_index",
        rationale="immutable spatial-substrate cell id (Constitution II — substrate is immutable)",
    ),
    RoundTripField(
        node_type=RoundTripNodeType.TERRITORY,
        field="population",
        rationale="material-base headcount for every territory-scoped rollup",
    ),
    RoundTripField(
        node_type=RoundTripNodeType.TERRITORY,
        field="wealth",
        rationale="territory wealth stock read by economic consequence systems",
    ),
    RoundTripField(
        node_type=RoundTripNodeType.TERRITORY,
        field="heat",
        rationale="tension/heat state carried across ticks",
    ),
    RoundTripField(
        node_type=RoundTripNodeType.TERRITORY,
        field="biocapacity",
        rationale="metabolic-rift stock B in ΔB=R-(E·η); overshoot O=C/B",
    ),
    RoundTripField(
        node_type=RoundTripNodeType.TERRITORY,
        field="extraction_intensity",
        rationale="unequal-exchange extraction rate read by ImperialRentSystem",
    ),
)

#: The declared round-trip contract: every core field the graph round trip must
#: conserve value-for-value. Hand-written (a dev-time contract, not moddable
#: runtime config), so it carries no regeneration machinery.
ROUNDTRIP_REGISTRY: tuple[RoundTripField, ...] = _SOCIAL_CLASS_FIELDS + _TERRITORY_FIELDS
