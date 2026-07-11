"""Simulation event-bus enums (event types, resolutions, outcomes).

Spec 058: extracted from the historical ``babylon.models.enums`` monolith.
Re-exported via :mod:`babylon.models.enums.__init__`.
"""

from __future__ import annotations

from enum import StrEnum


class ResolutionType(StrEnum):
    """How contradictions can resolve.

    Based on dialectical materialism, contradictions resolve through
    one of three mechanisms. The resolution type determines what
    happens to the system after a contradiction reaches critical intensity.

    Values:
        SYNTHESIS: Dialectical resolution - opposites unite at higher level
        RUPTURE: Revolutionary break - system undergoes fundamental change
        SUPPRESSION: Forced dormancy - contradiction remains but is contained
    """

    SYNTHESIS = "synthesis"
    RUPTURE = "rupture"
    SUPPRESSION = "suppression"


class EventType(StrEnum):
    """Types of simulation events for the narrative layer.

    These event types are published to the EventBus when significant
    state changes occur, enabling the AI Observer to generate narrative.

    Values:
        SURPLUS_EXTRACTION: Imperial rent extracted from worker to owner
        IMPERIAL_SUBSIDY: Wealth converted to suppression to stabilize client state
        SOLIDARITY_AWAKENING: Periphery worker enters active struggle (consciousness >= threshold)
        CONSCIOUSNESS_TRANSMISSION: Consciousness flows via SOLIDARITY edge from periphery to core
        MASS_AWAKENING: Target consciousness crosses mass awakening threshold
        ECONOMIC_CRISIS: Imperial rent pool depleted below critical threshold (Sprint 3.4.4)
        ECOLOGICAL_OVERSHOOT: Consumption exceeds biocapacity (Slice 1.4 - Metabolic Rift)
        EXCESSIVE_FORCE: State violence "spark" - police brutality event (Agency Layer)
        UPRISING: Mass insurrection triggered by spark + accumulated agitation (Agency Layer)
        SOLIDARITY_SPIKE: Solidarity infrastructure built through shared struggle (Agency Layer)
        POWER_VACUUM: Comprador insolvency triggers George Jackson Bifurcation
        REVOLUTIONARY_OFFENSIVE: Organized labor seizes opportunity during power vacuum
        FASCIST_REVANCHISM: Core workers react with nationalism during power vacuum
        RUPTURE: Contradiction tension reached critical threshold, triggering phase transition
        PHASE_TRANSITION: Topology percolation threshold crossed (Sprint 3.3)
        ENTITY_DEATH: Entity starved (wealth < consumption_needs) - Material Reality Refactor
        POPULATION_DEATH: Probabilistic mortality from inequality (Mass Line Refactor)
        POPULATION_ATTRITION: Grinding Attrition deaths from coverage deficit (Mass Line Phase 3)

    Terminal Crisis Dynamics (ai/terminal-crisis-dynamics.md):
        PERIPHERAL_REVOLT: Periphery severs EXPLOITATION edges when P(S|R) > P(S|A)
        SUPERWAGE_CRISIS: Core bourgeoisie can't afford super-wages (pool exhausted)
        CLASS_DECOMPOSITION: Labor aristocracy splits into enforcers + internal proletariat
        CONTROL_RATIO_CRISIS: Prisoners exceed guard capacity (ratio inverted)
        TERMINAL_DECISION: System bifurcates to revolution or genocide
    """

    SURPLUS_EXTRACTION = "surplus_extraction"
    IMPERIAL_SUBSIDY = "imperial_subsidy"
    SOLIDARITY_AWAKENING = "solidarity_awakening"
    CONSCIOUSNESS_TRANSMISSION = "consciousness_transmission"
    MASS_AWAKENING = "mass_awakening"
    ECONOMIC_CRISIS = "economic_crisis"  # Sprint 3.4.4 - Dynamic Balance
    ECOLOGICAL_OVERSHOOT = "ecological_overshoot"  # Slice 1.4 - Metabolic Rift
    EXCESSIVE_FORCE = "excessive_force"  # Agency Layer - The Spark (Police Brutality)
    UPRISING = "uprising"  # Agency Layer - The Explosion (Riot/Insurrection)
    SOLIDARITY_SPIKE = "solidarity_spike"  # Agency Layer - The Bridge Building
    POWER_VACUUM = "power_vacuum"  # George Jackson Bifurcation - Comprador insolvency
    REVOLUTIONARY_OFFENSIVE = (
        "revolutionary_offensive"  # Jackson: Organized labor seizes opportunity
    )
    FASCIST_REVANCHISM = "fascist_revanchism"  # Jackson: Core reacts with nationalism
    RUPTURE = "rupture"  # Contradiction rupture - tension reached critical threshold
    PHASE_TRANSITION = "phase_transition"  # Topology: percolation threshold crossed
    ENDGAME_REACHED = "endgame_reached"  # Game ended (victory/defeat condition met)
    ENTITY_DEATH = "entity_death"  # Material Reality: Entity starved (wealth < consumption)
    POPULATION_DEATH = "population_death"  # Mass Line: Probabilistic mortality from inequality
    POPULATION_ATTRITION = "population_attrition"  # Mass Line Phase 3: Coverage deficit deaths
    # Terminal Crisis Dynamics - Endgame Arc
    PERIPHERAL_REVOLT = "peripheral_revolt"  # Periphery severs EXPLOITATION edges
    SUPERWAGE_CRISIS = "superwage_crisis"  # C_b can't afford super-wages
    CLASS_DECOMPOSITION = "class_decomposition"  # LA splits into enforcers + proletariat
    CONTROL_RATIO_CRISIS = "control_ratio_crisis"  # Prisoners > guards × capacity
    TERMINAL_DECISION = "terminal_decision"  # Revolution or genocide bifurcation
    # Crisis and Devaluation Mechanics (Feature 018)
    CRISIS_PHASE_TRANSITION = "crisis_phase_transition"  # Phase lifecycle change
    DISPOSSESSION_CASCADE = "dispossession_cascade"  # LA share decline milestone
    BIFURCATION_THRESHOLD = "bifurcation_threshold"  # |score| crosses threshold
    # Dialectical Field Topology (Feature 002)
    EDGE_MODE_TRANSITION = "edge_mode_transition"  # Edge qualitative mode change
    PRINCIPAL_CONTRADICTION_SHIFT = "principal_contradiction_shift"  # Principal field changed
    # Lawverian Aufhebung (Phase E): the principal contradiction is resolved at a
    # higher level while diverging below — a sublation (quality from quantity).
    LEVEL_TRANSITION = "level_transition"  # Opposition sublated to a higher level (E2)
    CO_OPTIVE_BREAKDOWN = "co_optive_breakdown"  # Co-optation failure with bifurcation
    LATENT_CONTRADICTION_RELEASE = "latent_contradiction_release"  # Suppressed df/dt spike
    ASPECT_REVERSAL = "aspect_reversal"  # Dominant party switches on directed edge
    # Capital Volume I Production Dynamics (Feature 021)
    RESERVE_ARMY_PRESSURE = "reserve_army_pressure"  # Reserve army wage pressure applied
    DISPOSSESSION_EVENT = "dispossession_event"  # Aggregate dispossession recorded
    VALUE_TRANSFER = "value_transfer"  # Inter-territory value transfer from dispossession
    EXPLOITATION_MODE_SHIFT = "exploitation_mode_shift"  # Exploitation mode reclassified
    # D-P-D' Lifecycle Circuit (Feature 030)
    LIFECYCLE_TRANSITION = "lifecycle_transition"  # Population moved between phases
    LEGITIMATION_CRISIS = "legitimation_crisis"  # Classification changed to CRISIS
    LEGITIMATION_RECOVERY = "legitimation_recovery"  # Classification improved from CRISIS
    INHERITANCE_TRANSFER = "inheritance_transfer"  # D' death triggered inheritance flow
    DUAL_CIRCUIT_INTERFERENCE = "dual_circuit_interference"  # Resource competition detected
    # OODA Loop System (Feature 032)
    ORGANIZATIONAL_ACTION = "organizational_action"  # Any org action executed
    STATE_REPRESSION = "state_repression"  # REPRESS action by state
    STATE_SURVEILLANCE = "state_surveillance"  # SURVEIL action by state
    CONSCIOUSNESS_SHIFT = "consciousness_shift"  # Community CI change exceeds threshold
    INITIATIVE_CONTESTED = "initiative_contested"  # Non-state org seizes initiative
    INFRASTRUCTURE_CHANGE = "infrastructure_change"  # BUILD or ATTACK infrastructure
    # Bifurcation Topology Analysis (Feature 033)
    BIFURCATION_TENDENCY_CHANGE = "bifurcation_tendency_change"  # Overall tendency shifted
    # Unified Class System (Feature 038)
    CALIBRATION_DISAGREEMENT = "calibration_disagreement"  # Accounting vs wealth criteria disagree
    # State Apparatus AI (Feature 039)
    STATE_ACTION_EXECUTED = "state_action_executed"  # Any state AI verb executed
    FASCIST_CONVERGENCE = "fascist_convergence"  # Three-pillar fascist conditions met
    FACTION_SHIFT = "faction_shift"  # FactionBalance weights changed
    THREAD_ESCALATION = "thread_escalation"  # AttentionThread phase advanced
    LEGAL_FRAMEWORK_ENACTED = "legal_framework_enacted"  # LEGISLATE created new law
    LEGAL_FRAMEWORK_REVOKED = "legal_framework_revoked"  # REVOKE removed a law
    # Institution Base Model (Feature 040)
    INSTITUTION_FACTION_SHIFT = "institution_faction_shift"  # Hegemonic fraction changed
    INSTITUTION_REPRODUCTION = "institution_reproduction"  # Institution spawned replacement org
    INSTITUTION_BONAPARTIST_MODE = "institution_bonapartist_mode"  # Bonapartist threshold crossed
    # Spec 057 — Leontief Imperial Rent Integration: CalibrationWarning event family
    CALIBRATION_AXIOM_VIOLATION = "calibration_warning.axiom_violation"
    """Periphery-wage source published a ratio < 1.0 (FR-002, Clarifications 2026-05-08)."""
    CALIBRATION_QCEW_CARRY_FORWARD = "calibration_warning.qcew_carry_forward"
    """QCEW data missing for (county, year); employment shares carried forward (FR-004)."""
    CALIBRATION_PHI_HOUR_OUTLIER = "calibration_warning.phi_hour_outlier"
    """Per-county phi_hour fell outside the LeontiefRentDefines plausibility bounds (FR-008)."""
    # Spec-070 Balkanization (political-topology overlay events)
    SOVEREIGN_COLLAPSE = "sovereign_collapse"  # FR-023
    TERRITORY_TRANSITION = "territory_transition"  # FR-022
    FACTION_VICTORY = "faction_victory"  # FR-026
    SECESSION_DECLARED = "secession_declared"  # FR-029a (2)
    CIVIL_WAR_DECLARED = "civil_war_declared"  # FR-028
    RED_SETTLER_TRAP_DETECTED = "red_settler_trap_detected"  # FR-034
    DUAL_POWER_ACTIVE = "dual_power_active"  # FR-035
    RED_OGV_ENDGAME = "red_ogv_endgame"  # FR-031
    FRAGMENTED_COLLAPSE_ENDGAME = "fragmented_collapse_endgame"  # FR-031
    # Spec-071 Reactionary Subject (fascism branch of the George Jackson bifurcation)
    FASCIST_DRIFT = "fascist_drift"  # C_pb/C_la node drifts fascist (pull > threshold)
    FASCIST_RECRUITMENT = "fascist_recruitment"  # drifted node captured by a fascist faction
    ORGANIZATIONAL_FRACTURE = "organizational_fracture"  # LA member defects from a player org
    RED_BROWN_COUP = "red_brown_coup"  # majority LA defection captures the org
    POGROM = "pogrom"  # reactionary org action: targeted communal violence
    LOCKOUT = "lockout"  # reactionary org action: employer withdraws wages/employment
    VIGILANTISM = "vigilantism"  # reactionary org action: extra-state local repression
    SPONTANEOUS_RIOT = "spontaneous_riot"  # L_u volatility-gated undirected disorder


class GameOutcome(StrEnum):
    """Possible game ending outcomes (Slice 1.6: Endgame Detection).

    The simulation can end in three ways, plus the ongoing state:

    Values:
        IN_PROGRESS: Game is still ongoing (no endgame condition met yet).

        REVOLUTIONARY_VICTORY: The masses have won. Requires:
            - percolation_ratio >= 0.7 (70%+ in giant component)
            - average class_consciousness > 0.8 (ideological clarity)

        ECOLOGICAL_COLLAPSE: The planet has collapsed. Requires:
            - overshoot_ratio > 2.0 for 5 consecutive ticks
            (Capital's metabolic rift has become fatal)

        FASCIST_CONSOLIDATION: Fascism has won. Requires:
            - national_identity > class_consciousness for 3+ nodes
            (False consciousness prevents class-based organization)

    Priority when multiple conditions are met:
        REVOLUTIONARY_VICTORY > ECOLOGICAL_COLLAPSE > FASCIST_CONSOLIDATION
    """

    IN_PROGRESS = "in_progress"
    REVOLUTIONARY_VICTORY = "revolutionary_victory"
    ECOLOGICAL_COLLAPSE = "ecological_collapse"
    FASCIST_CONSOLIDATION = "fascist_consolidation"
    # Spec-070 Balkanization endgames
    RED_OGV = "red_ogv"  # FR-031: settler-socialist trap (IGNORE-majority + class-tension-down)
    FRAGMENTED_COLLAPSE = "fragmented_collapse"  # FR-032a: no-majority + ≥3 sovereigns


__all__ = [
    "EventType",
    "GameOutcome",
    "ResolutionType",
]
