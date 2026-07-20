"""Ideology systems for the Babylon simulation - The Superstructure.

Sprint 3.4.2b: Extended with Fascist Bifurcation mechanic.
Sprint 3.4.3: George Jackson Refactor - Multi-dimensional consciousness model.

When wages FALL, crisis creates "agitation energy" that channels into:
- Class Consciousness (if solidarity_pressure > 0) - Revolutionary Path
- National Identity (if solidarity_pressure = 0) - Fascist Path via loss aversion
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from babylon.formulas.consciousness_routing import (
    compute_agitation_delta,
    compute_exploitation_visibility,
    compute_reification_buffer,
    route_agitation_to_ternary,
)
from babylon.formulas.contradiction import calculate_wealth_asymmetry_balance
from babylon.kernel.tick_partition import TickPartition
from babylon.models.enums import EdgeType, NodeType

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol

from babylon.kernel.system_base import SystemBase
from babylon.kernel.system_protocol import ContextType

# Context keys for storing previous values between ticks
PREVIOUS_WAGES_KEY = "previous_wages"
PREVIOUS_WEALTH_KEY = "previous_wealth"


def _get_ideology_profile_from_node(
    node_data: dict[str, Any],
) -> dict[str, float]:  # pragma: no mutate — graph accessor
    """Extract IdeologicalProfile values from graph node data.

    Args:
        node_data: Graph node data dictionary

    Returns:
        Dict with class_consciousness, national_identity, agitation keys
    """
    ideology = node_data.get("ideology")  # pragma: no mutate

    if ideology is None:  # pragma: no mutate
        # No ideology data - return defaults
        return {  # pragma: no mutate
            "class_consciousness": 0.0,  # pragma: no mutate
            "national_identity": 0.5,  # pragma: no mutate
            "agitation": 0.0,  # pragma: no mutate
        }  # pragma: no mutate

    if isinstance(ideology, dict):  # pragma: no mutate
        # IdeologicalProfile format
        return {  # pragma: no mutate
            "class_consciousness": ideology.get("class_consciousness", 0.0),  # pragma: no mutate
            "national_identity": ideology.get("national_identity", 0.5),  # pragma: no mutate
            "agitation": ideology.get("agitation", 0.0),  # pragma: no mutate
        }  # pragma: no mutate

    # Unknown format - return defaults
    return {  # pragma: no mutate
        "class_consciousness": 0.0,  # pragma: no mutate
        "national_identity": 0.5,  # pragma: no mutate
        "agitation": 0.0,  # pragma: no mutate
    }  # pragma: no mutate


class ConsciousnessSystem(SystemBase):
    """Phase 2: Consciousness Drift based on material conditions.

    Sprint 3.4.3 (George Jackson Refactor): Uses multi-dimensional IdeologicalProfile.
    - class_consciousness: Relationship to Capital [0=False, 1=Revolutionary]
    - national_identity: Relationship to State/Tribe [0=Internationalist, 1=Fascist]
    - agitation: Raw political energy from crisis (falling wages)

    Extended with Fascist Bifurcation mechanic:
    - Reads incoming SOLIDARITY edges to calculate solidarity_pressure
    - Tracks wage changes between ticks to detect crisis conditions
    - Routes agitation to either class_consciousness or national_identity
    """

    partition: ClassVar[TickPartition] = TickPartition.CONSEQUENCE
    position: ClassVar[float] = 17.0

    name: ClassVar[str] = "Consciousness Drift"
    # Spec 053 INV-001: does not mutate hex c+v+s; opted in by default-deny.
    creates_value: ClassVar[bool] = False

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        """Apply consciousness drift to all entities with bifurcation routing."""

        # Handle both TickContext (with persistent_data) and raw dict
        # TickContext stores persistent data in .persistent_data attribute
        # Raw dict stores persistent data directly
        persistent: dict[str, Any] = context.persistent_data

        # Lawverian wage-opposition deterioration (C1.5, signed in the Phase D
        # review). ContradictionSystem (position 18) stashes the registry
        # snapshot on the graph attr ``opposition_states``; this system
        # (position 17) reads LAST tick's wage state. Under the Phase D
        # measure the wage opposition is the true (W, V) defect and
        # ``gap == |balance|`` with balance > 0 == wage above value (the
        # bribe). Deterioration is therefore the relation SHARPENING
        # (rate > 0) while labor is on the LOSING side (balance < 0 — wage
        # sinking below value). A growing bribe (balance > 0, rate > 0) is
        # pacification and contributes ZERO agitation — Cope's crisis-gating:
        # flat during a growing bribe is CORRECT. Nominal wage cuts are the
        # separate per-worker ``wage_change`` channel below. Absent snapshot
        # (tick 1 / non-bridged tests) -> 0.
        opposition_states = graph.get_graph_attr("opposition_states", {}) or {}
        wage_state = opposition_states.get("wage", {})
        _wage_rate = float(wage_state.get("rate", 0.0))
        _wage_balance = float(wage_state.get("balance", 0.0))
        wage_deterioration = max(0.0, _wage_rate) if _wage_balance < 0.0 else 0.0

        # Task 2 (2026-07-18, sustained wage-value defect — B in the null-play
        # political-coupling plan): ADDS a LEVEL term alongside the RATE term
        # above. ``wage_deterioration`` only fires while the relation is
        # actively sharpening (rate > 0); once the Imperial Circuit reaches
        # steady state (rate -> 0) that term goes silent even if labor
        # remains permanently on the losing side. ``sustained_exploitation_
        # agitation`` reads a magnitude, not a delta, so a persistent
        # (non-worsening) defect still generates agitation every tick it
        # holds.
        #
        # Defect fix (fix/null-play-coupling, post-948e46ad): this MUST NOT
        # read the global ``_wage_balance`` above. That value is
        # ``_mean_asymmetry`` (catalog.py:134-145) — an unweighted arithmetic
        # mean of an INTENSIVE quantity ((w-v)/(w+v), bounded [-1, 1]) over
        # ALL classes. Averaging intensives without share-weighting is a
        # variance error, AND class_consciousness is PER-CLASS while the
        # global mean is class-independent: a bribed labor aristocracy
        # (balance > 0) folded together with an exploited periphery worker
        # keeps the mean >= 0, so the ``balance < 0`` gate never opens and
        # every class radicalizes (or doesn't) identically — erasing the
        # theory this engine models. Each class's OWN balance is computed
        # per-iteration below, from that class's OWN ``w_paid`` /
        # ``v_produced`` (see the loop). See
        # ``babylon.formulas.sustained_exploitation`` for the Volume III
        # (spec-024) collision-boundary contract this reads through.

        # Initialize or retrieve previous wages tracking from persistent storage
        if PREVIOUS_WAGES_KEY not in persistent:
            persistent[PREVIOUS_WAGES_KEY] = {}
        previous_wages: dict[str, float] = persistent[PREVIOUS_WAGES_KEY]

        # Initialize or retrieve previous wealth tracking from persistent storage
        # Periphery Dynamics Extension: Track wealth extraction between ticks
        if PREVIOUS_WEALTH_KEY not in persistent:
            persistent[PREVIOUS_WEALTH_KEY] = {}
        previous_wealth: dict[str, float] = persistent[PREVIOUS_WEALTH_KEY]

        # Track current wages and wealth for next tick comparison
        current_wages: dict[str, float] = {}
        current_wealth_map: dict[str, float] = {}

        for node in graph.query_nodes(node_type="social_class"):
            attrs = node.attributes

            # Skip inactive (dead) entities - dead can't develop consciousness
            if not attrs.get("active", True):
                continue

            # Per-class sustained wage-value defect (fix/null-play-coupling):
            # ``w_paid``/``v_produced`` are written directly onto THIS node's
            # attributes by EconomicSystem (engine/systems/economic.py:
            # 501-502) on ticks it actually paid this class — same
            # presence-of-both selector ContradictionSystem uses
            # (engine/systems/contradiction.py:279) to build the (unrelated
            # here) global mean. Absent either field means no wage-value
            # transaction was recorded for this class THIS tick (e.g. the
            # class is the payer itself, or its employer had zero wealth).
            #
            # Consciousness Recoupling correction (docs/superpowers/specs/
            # 2026-07-18-consciousness-recoupling-design.md, §2): the OLD
            # sign-gated formula (sustained_exploitation_agitation) mapped
            # "no data this tick" and "balance == 0.0 exactly" to the SAME
            # safe output (0.0), because its gate was `balance >= 0 -> 0.0`.
            # sustained_exploitation_magnitude's positive branch does NOT
            # have that property — it PEAKS near balance == 0 — so an
            # absent-data fallback of `class_wage_balance = 0.0` would now
            # silently fabricate near-peak chauvinist agitation for classes
            # with no recorded wage-value transaction at all. This is
            # exactly the silent `.get(field, 0.0)` masking the project
            # forbids: the presence check below gates the WHOLE computation,
            # not just the balance value, so "no data" reads as an explicit,
            # documented zero contribution — not a data point on the curve.
            #
            # Task #42-A (de-delta wiring): the magnitude itself is no
            # longer computed here as a separate parallel addend —
            # ``class_wage_balance`` (or ``None`` when absent) is passed
            # straight into ``compute_agitation_delta`` below as
            # ``wage_balance``, which is the sole call site of
            # ``sustained_exploitation_magnitude`` now (DRY: one canonical
            # Stage-1 converter, not two un-DRY'd agitation channels).
            node_w_paid = attrs.get("w_paid")
            node_v_produced = attrs.get("v_produced")
            if node_w_paid is not None and node_v_produced is not None:
                wage_data_present = True
                class_wage_balance = calculate_wealth_asymmetry_balance(
                    float(node_v_produced), float(node_w_paid)
                )
                # Balance sign determines bifurcation DIRECTION (spec §2):
                # only a POSITIVE balance (the imperial bribe) biases
                # routing toward the fascist pole. A negative balance
                # (labor losing) contributes zero chauvinist pressure —
                # its direction is instead the revolutionary pull already
                # carried by solidarity_pressure below.
                chauvinist_pressure = (
                    max(0.0, class_wage_balance)
                    * services.defines.consciousness.chauvinist_pressure_scale
                )
            else:
                wage_data_present = False
                class_wage_balance = 0.0
                chauvinist_pressure = 0.0

            # Task #42-B (continuous repression term), corrected task #42
            # fix wave 1 (review MEDIUM-2, 2026-07-20): ``repression_faced``
            # is a continuous [0, 1] LEVEL (bumped by POGROM/VIGILANTISM,
            # ``ooda/action_effects.py``), distinct from StruggleSystem's
            # event-triggered ``repression_backfire`` spike. Presence-gated
            # exactly like ``class_wage_balance`` above — a node that never
            # had ``repression_faced`` stamped at all contributes zero, not
            # a fabricated fallback default.
            #
            # The RAW level must NOT be read directly: ``SocialClass``'s own
            # model default is 0.5 (``social_class.py:169``), stamped on
            # every class from tick 1 regardless of any actual repression
            # EVENT. Reading it raw measures that ambient default as signal
            # -- proven (review MEDIUM-2) to be the ENTIRE +0.00012 tick-1
            # drift on all 5 canonical scenarios, a permanent ratchet with
            # no material referent (Aleksandrov Test: the ambient default
            # corresponds to no relation). Only repression PRODUCED above
            # that baseline counts -- subtract ``DEFAULT_REPRESSION_FACED``
            # (the SAME canonical fallback ``struggle.py``/``economic.py``/
            # ``survival.py`` already read via ``services.defines.
            # DEFAULT_REPRESSION_FACED``) and floor at zero. Canonical
            # scenarios, which never fire POGROM/VIGILANTISM, get exactly
            # zero by construction, matching the shadow-first/absent-safe
            # discipline (ADR077/078). Known residual, documented not
            # fixed: ``repression_faced`` never decays, so once produced
            # this term accumulates monotonically -- defensible as
            # accumulated repression experience.
            node_repression_faced = attrs.get("repression_faced")
            effective_repression = (
                max(
                    0.0,
                    float(node_repression_faced) - services.defines.DEFAULT_REPRESSION_FACED,
                )
                if node_repression_faced is not None
                else None
            )

            # Calculate wages received (sum of incoming WAGES edges)
            core_wages = 0.0
            for edge in graph.query_edges(edge_type=EdgeType.WAGES):
                if edge.target_id == node.id:
                    core_wages += edge.attributes.get("value_flow", 0.0)

            # Store current wages for next tick
            current_wages[node.id] = core_wages

            # Calculate wage_change for bifurcation mechanic
            prev_wage = previous_wages.get(node.id, core_wages)
            wage_change = core_wages - prev_wage

            # Periphery Dynamics Extension: Calculate wealth_change for extraction detection
            # Periphery workers have wealth extracted via EXPLOITATION edges, not wage cuts
            current_wealth = float(attrs.get("wealth", 0.0))
            # Default to current wealth if first tick (no previous baseline)
            prev_wealth = previous_wealth.get(node.id, current_wealth)
            wealth_change = current_wealth - prev_wealth
            current_wealth_map[node.id] = current_wealth

            # Calculate solidarity_pressure from incoming SOLIDARITY edges
            # Sum of solidarity_strength from all incoming SOLIDARITY edges
            solidarity_pressure = 0.0
            activation_threshold = services.defines.solidarity.activation_threshold

            # ADR087 (supersedes the ADR085 invariant comment this replaces):
            # SOLIDARITY edges now have TWO source shapes. class-sourced
            # edges (scenarios/_legacy.py + _legacy_wayne.py, the two static
            # scenario-genesis producers ADR085 audited) still gate on the
            # SOURCE's own revolutionary consciousness — a bribed or
            # unconscious class transmits nothing. org-sourced edges (the
            # Unit 6 write side: EDUCATE/PROPAGANDIZE/PROVIDE_SERVICE mass
            # work, `engine/actions/_mass_work.py`) have no ideology of their
            # own to gate on — the edge's `solidarity_strength` IS the
            # signal (organized mass work materially raises the target's
            # effective solidarity; MIM(P) organizing loop, owner-ratified
            # 2026-07-18/19). Gated instead on a negligible-transmission
            # floor (shared with the class-sourced noise filter) so a
            # freshly-decayed near-zero edge doesn't contribute forever.
            negligible_transmission = services.defines.solidarity.negligible_transmission
            for edge in graph.query_edges(edge_type=EdgeType.SOLIDARITY):
                if edge.target_id == node.id:
                    # Get solidarity_strength from edge
                    strength = edge.attributes.get("solidarity_strength", 0.0)
                    if strength <= 0:
                        continue
                    src_node = graph.get_node(edge.source_id)
                    if src_node is None:
                        continue
                    if src_node.node_type == NodeType.ORGANIZATION.value:
                        if strength > negligible_transmission:
                            solidarity_pressure += strength
                    else:
                        # Only count if source has revolutionary consciousness
                        source_profile = _get_ideology_profile_from_node(src_node.attributes)
                        source_consciousness = source_profile["class_consciousness"]
                        if source_consciousness > activation_threshold:
                            solidarity_pressure += strength

            # Get current ideological profile
            current_profile = _get_ideology_profile_from_node(attrs)

            # Apply consciousness routing (Spec 043 - Value Transparency)
            # Convert wage/wealth changes to agitation via tensor pipeline.
            # Task #42-A/B: wage_balance and repression_level are LEVELS
            # (not deltas), presence-gated to None when absent this tick.
            # ``defines=`` must be threaded through explicitly (task #42-A
            # regression guard): the sustained-exploitation/repression
            # coefficients now live INSIDE this call, and without this the
            # function silently falls back to schema defaults, ignoring any
            # ``services.defines``/``defines.yaml`` override -- exactly the
            # per-run-config respect the old direct
            # ``services.defines.consciousness.*`` reads had.
            agitation_increment = compute_agitation_delta(
                exploitation_rate_delta=abs(wage_change) if wage_change < 0 else 0.0,
                imperial_rent_delta=wealth_change,  # Wealth decline ~ rent decline
                visibility_delta=0.0,  # g₃₃ changes handled in community system
                wage_balance=class_wage_balance if wage_data_present else None,
                repression_level=effective_repression,
                defines=services.defines.consciousness,
            )
            new_agitation = current_profile["agitation"] + agitation_increment + wage_deterioration

            # Route agitation through solidarity → class/nation split.
            # The ternary router (Spec 043) returns shifts in (revolutionary,
            # liberal, fascist). The legacy two-axis IdeologicalProfile maps
            #   class_consciousness  ← revolutionary (delta_r)
            #   national_identity    ← fascist       (delta_f)
            # liberal drain (delta_l) is the *backpressure* on the liberal
            # tendency and intentionally has no projection onto either
            # legacy axis. Until the Spec 043 refactor was completed, this
            # block discarded delta_f and added abs(delta_l) to
            # national_identity, which made every wage cut grow
            # national_identity by the same amount as class_consciousness
            # under any solidarity level — defeating the bifurcation.
            delta_r, _delta_l, delta_f = route_agitation_to_ternary(
                agitation=new_agitation,
                solidarity_factor=min(1.0, solidarity_pressure),
                education_pressure=0.0,  # Education pressure handled in community system
                defines=services.defines.consciousness,
                chauvinist_pressure=chauvinist_pressure,
            )
            new_class = min(1.0, current_profile["class_consciousness"] + delta_r)
            new_nation = min(1.0, current_profile["national_identity"] + delta_f)
            # Decay agitation after routing
            decay_rate = services.defines.consciousness.agitation_decay_rate
            new_agitation = max(0.0, new_agitation * (1.0 - decay_rate))

            # Update the ideology in the graph as a dict (IdeologicalProfile format)
            # Also write MaterialConditionsBuffer for downstream systems
            graph.update_node(
                node.id,
                ideology={
                    "class_consciousness": new_class,
                    "national_identity": new_nation,
                    "agitation": new_agitation,
                },
                material_conditions={
                    "agitation": new_agitation,
                    "exploitation_visibility": compute_exploitation_visibility(
                        exploitation_rate=abs(wage_change) if wage_change < 0 else 0.0,
                        imperial_rent=max(0.0, wealth_change),
                        defines=services.defines.consciousness,
                    ),
                    "reification_buffer": compute_reification_buffer(
                        imperial_rent=max(0.0, wealth_change),
                        total_v=max(1.0, core_wages),
                    ),
                },
            )

        # Update previous wages and wealth for next tick in persistent storage
        persistent[PREVIOUS_WAGES_KEY] = current_wages
        persistent[PREVIOUS_WEALTH_KEY] = current_wealth_map
