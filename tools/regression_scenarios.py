"""Canonical qa:regression scenario definitions and coverage declarations.

Extracted from ``tools/regression_test.py`` (this is its "successor module"
per the modernization spec §E1) so the scenario estate is importable data,
AST-readable by ``babylon.sentinels.gate_coverage``, and shared with the
coverage-truth probe without dragging in the whole harness.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, model_validator

# Add src and tools to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from shared import inject_parameter

from babylon.config.defines import GameDefines
from babylon.engine.scenarios import (
    create_imperial_circuit_scenario,
    create_single_county_scenario,
    create_two_node_scenario,
)

# Scenario configurations
SCENARIOS: Final[dict[str, dict[str, Any]]] = {
    "imperial_circuit": {
        "description": "4-node default scenario",
        "factory": "create_imperial_circuit_scenario",
        "defines_overrides": {},
    },
    "two_node": {
        "description": "Minimal worker vs owner",
        "factory": "create_two_node_scenario",
        "defines_overrides": {},
    },
    "starvation": {
        "description": "Low extraction efficiency stress",
        "factory": "create_imperial_circuit_scenario",
        "defines_overrides": {
            "economy.extraction_efficiency": 0.05,
        },
    },
    "glut": {
        "description": "High extraction with metabolic overshoot",
        "factory": "create_imperial_circuit_scenario",
        "defines_overrides": {
            "economy.extraction_efficiency": 0.99,
            "survival.default_subsistence": 0.0,
        },
    },
    "fascist_bifurcation": {
        "description": "Consciousness routing to national identity",
        "factory": "create_imperial_circuit_scenario",
        "defines_overrides": {
            "economy.extraction_efficiency": 0.7,
            "consciousness.sensitivity": 0.3,
        },
    },
    "single_county": {
        "description": "Wayne-seeded minimal county: Vol III financial layer, "
        "MELT path, and distribution identity all fire",
        "factory": "create_single_county_scenario",
        "defines_overrides": {},
    },
}

#: Scenarios registered in SCENARIOS whose baseline (checkpoint JSON + dense CSV
#: golden) has not been minted yet. Declared explicitly — NOT inferred from
#: golden-file absence — so the dense-golden gate
#: (tests/unit/tools/test_dense_goldens.py) and the report-completeness gate
#: (tests/unit/tools/test_vol3_baseline_delta_report.py) skip these scenarios
#: LOUDLY while still failing hard if a golden for one of the five ALREADY-minted
#: scenarios ever goes missing (a file-absence-keyed skip would silently mask
#: that accident instead of catching it). Task 11's ceremony mints
#: single_county's baseline and removes it from this set in the same commit.
PENDING_CEREMONY: Final[frozenset[str]] = frozenset({"single_county"})


def create_scenario(
    name: str,
) -> tuple[Any, Any, GameDefines]:
    """Create scenario by name.

    Args:
        name: Scenario name from SCENARIOS

    Returns:
        Tuple of (WorldState, SimulationConfig, GameDefines)
    """
    config = SCENARIOS[name]

    # Call factory function
    factory_name = config["factory"]
    if factory_name == "create_imperial_circuit_scenario":
        state, sim_config, base_defines = create_imperial_circuit_scenario()
    elif factory_name == "create_two_node_scenario":
        state, sim_config, base_defines = create_two_node_scenario()
    elif factory_name == "create_single_county_scenario":
        state, sim_config, base_defines = create_single_county_scenario()
    else:
        raise ValueError(f"Unknown factory: {factory_name}")

    # Apply overrides
    defines = base_defines
    for path, value in config["defines_overrides"].items():
        defines = inject_parameter(defines, path, value)

    return state, sim_config, defines


# =============================================================================
# Coverage declarations (E1): ScenarioCoverage data model + honest per-scenario
# declarations for the canonical qa:regression scenarios (five original +
# single_county, Task 8/E2a).
# =============================================================================


class _StrictModel(BaseModel):
    """Frozen, extra-forbidding base for coverage data (sentinel-family idiom)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def _no_blank_strings(self) -> _StrictModel:
        for name, value in self:
            if isinstance(value, str) and not value.strip():
                raise ValueError(f"{type(self).__name__}.{name} must not be blank")
        return self


class SystemEvidence(_StrictModel):
    """One checkable claim that a System exercises its logic in a scenario.

    :param system: Engine System class name (must appear in
        ``simulation_engine._SYSTEM_CLASSES`` — the sentinel enforces this).
    :param kind: How the probe verifies the claim.

        - ``event``: ``key`` is an ``EventType`` value observed in some tick's
          ``state.events``.
        - ``entity_delta``: ``key`` is ``"<entity_id>.<attr>"``; the attribute's
          value changes at least once across the run.
        - ``economy_delta``: ``key`` is an ``state.economy`` attribute that
          changes at least once across the run.
        - ``state_presence``: ``key`` is a ``WorldState`` field (e.g.
          ``market``) that is non-None by the final tick.
        - ``context_presence``: ``key`` is a ``persistent_context`` key (e.g.
          ``_tick_dynamics``) present by the final tick.
        - ``bundle_event`` / ``bundle_field``: verified statically against the
          committed e2e baseline bundle, not by the probe.
    :param key: The evidence key, interpreted per ``kind``.
    :param claim: Human sentence naming the material relation exercised.
    :param forbidden_values: ``bundle_field``-only. If the baseline's value at
        ``key`` (compared as ``str(value)``) equals any of these, the gate
        reds: presence alone doesn't prove the claimed System ran when the
        field is schema-static (always emitted, even when the System is
        inert) — this pins the *value* the row is actually relying on
        (typically the field's seeded/default value) so a future baseline
        regen that silently collapses back to that value is caught, not
        waved through by a presence-only check. Empty (the default) for
        every kind except the rows that need it.
    """

    system: str
    kind: Literal[
        "event",
        "entity_delta",
        "economy_delta",
        "state_presence",
        "context_presence",
        "bundle_event",
        "bundle_field",
    ]
    key: str
    claim: str
    forbidden_values: tuple[str, ...] = ()


class AtRestChannel(_StrictModel):
    """A dense-trace channel declared legitimately all-zeros for a scenario."""

    channel: str
    reason: str


class ScenarioCoverage(_StrictModel):
    """What one canonical scenario demonstrably exercises."""

    scenario: str
    layers: tuple[str, ...]
    systems: tuple[SystemEvidence, ...]
    at_rest: tuple[AtRestChannel, ...] = ()


class CoverageGap(_StrictModel):
    """A system NO canonical scenario exercises — declared, reviewable debt.

    An uncovered system without a gap row is a gating sentinel failure; a gap
    row makes the hole loud and owner-reviewable instead of silent.
    """

    system: str
    reason: str
    remediation: str


# PURE LITERAL — the gate_coverage sentinel ast.literal_eval's this. No
# variables, no calls, no enum references. Validated into SCENARIO_COVERAGE
# below at import.
#
# Method (per CLAUDE.md Verification First): every row below was verified by
# a live spot-run (PYTHONPATH="$PWD/src:$PWD" poetry run python — create_scenario
# + step() loops printing state.events / entity attribute deltas / economy
# deltas / context keys over 40-150 ticks), not invented from source reading
# alone. Rows that looked plausible from source but did NOT verify (e.g.
# ContradictionSystem's RUPTURE/LEVEL_TRANSITION, MetabolismSystem's
# ECOLOGICAL_OVERSHOOT even in "glut") were dropped and the system moved to
# COVERAGE_GAPS_DATA instead — see task-2-report.md for the full evidence
# trail and the "trivial dict-default state_presence" / "unconditional
# empty-dict bookkeeping write" traps this ruled out.
SCENARIO_COVERAGE_DATA: Final[tuple[dict[str, Any], ...]] = (
    {
        "scenario": "imperial_circuit",
        "layers": ("material_base", "consciousness", "survival", "dialectics"),
        "systems": (
            {
                "system": "VitalitySystem",
                "kind": "entity_delta",
                "key": "C001.wealth",
                "claim": "periphery worker wealth drains under population-scaled subsistence burn",
            },
            {
                "system": "ProductionSystem",
                "kind": "entity_delta",
                "key": "C003.wealth",
                "claim": "labor-aristocracy production routes its value to the employing core "
                "bourgeoisie's wealth (Amin/Wallerstein employed-producer routing)",
            },
            {
                "system": "ImperialRentSystem",
                "kind": "economy_delta",
                "key": "imperial_rent_pool",
                "claim": "surplus extraction and tribute feed the imperial rent pool, which also "
                "decays under the TRPF surrogate",
            },
            {
                "system": "ImperialRentSystem",
                "kind": "entity_delta",
                "key": "C004.effective_wealth",
                "claim": "the wages phase pays the labor aristocracy productivity plus a "
                "PPP-scaled super-wage bonus from the rent pool",
            },
            {
                "system": "SurvivalSystem",
                "kind": "entity_delta",
                "key": "C001.p_acquiescence",
                "claim": "survival calculus recomputes P(S|A) from per-capita wealth every tick",
            },
            {
                "system": "ConsciousnessSystem",
                "kind": "entity_delta",
                "key": "C002.national_identity",
                "claim": "crisis agitation routes to the national-identity axis when "
                "solidarity_pressure is zero (no solidarity infrastructure seeded)",
            },
            {
                "system": "StruggleSystem",
                "kind": "event",
                "key": "excessive_force",
                "claim": "the stochastic EXCESSIVE_FORCE spark rolls every tick from repression_faced",
            },
            {
                "system": "FascistFactionSystem",
                "kind": "event",
                "key": "fascist_drift",
                "claim": "entitled-role (comprador/labor-aristocracy) agitation over near-zero "
                "incident solidarity crosses the fascist-pull threshold",
            },
            {
                "system": "MarketScissorsSystem",
                "kind": "event",
                "key": "market_correction",
                "claim": "the national price-value scissors axis snaps a correction once its "
                "divergence threshold is crossed",
            },
            {
                "system": "ContradictionFieldSystem",
                "kind": "context_presence",
                "key": "contradiction_history",
                "claim": "the opposition-sourced exploitation/atomization field history is seeded "
                "and rolled every tick (absent before the first tick, present after)",
            },
            {
                "system": "FieldDerivativeSystem",
                "kind": "event",
                "key": "principal_contradiction_shift",
                "claim": "the fastest-developing contradiction field (max |df/dt|) changes identity "
                "across the run",
            },
            {
                "system": "WealthDistributionSystem",
                "kind": "entity_delta",
                "key": "C001.wealth_share",
                "claim": "the national 4-bracket wealth-share ODE advances and projects onto each "
                "class's bracket every tick",
            },
            {
                "system": "LifecycleSystem",
                "kind": "event",
                "key": "lifecycle_transition",
                "claim": "the D-P-D' population-cohort circuit steps every territory every tick",
            },
        ),
        "at_rest": (),
    },
    {
        "scenario": "two_node",
        "layers": ("material_base", "consciousness", "survival"),
        "systems": (
            {
                "system": "VitalitySystem",
                "kind": "entity_delta",
                "key": "C001.wealth",
                "claim": "worker wealth drains under population-scaled subsistence burn even in "
                "the minimal two-node dialectic",
            },
            {
                "system": "ImperialRentSystem",
                "kind": "entity_delta",
                "key": "C001.effective_wealth",
                "claim": "the WAGES edge from owner directly to worker pays a PPP-scaled super-wage "
                "bonus (two_node's simplified topology has no labor aristocracy)",
            },
            {
                "system": "SurvivalSystem",
                "kind": "entity_delta",
                "key": "C001.p_acquiescence",
                "claim": "survival calculus recomputes P(S|A) from per-capita wealth every tick",
            },
            {
                "system": "ConsciousnessSystem",
                "kind": "entity_delta",
                "key": "C001.national_identity",
                "claim": "crisis agitation routes to national identity under zero solidarity "
                "(two_node seeds no SOLIDARITY edge at all)",
            },
            {
                "system": "StruggleSystem",
                "kind": "event",
                "key": "excessive_force",
                "claim": "the stochastic EXCESSIVE_FORCE spark rolls every tick from repression_faced",
            },
            {
                "system": "LifecycleSystem",
                "kind": "event",
                "key": "lifecycle_transition",
                "claim": "the D-P-D' lifecycle circuit steps the sole territory every tick",
            },
            {
                "system": "MarketScissorsSystem",
                "kind": "state_presence",
                "key": "market",
                "claim": "the national price-value scissors axis seeds/advances from the WAGES "
                "edge's wage/value flow (market_correction itself never crosses threshold "
                "here, but the axis is live)",
            },
            {
                "system": "ContradictionFieldSystem",
                "kind": "context_presence",
                "key": "contradiction_history",
                "claim": "the opposition-sourced field history is seeded and rolled every tick",
            },
            {
                "system": "WealthDistributionSystem",
                "kind": "entity_delta",
                "key": "C001.wealth_share",
                "claim": "the national wealth-share ODE projects onto the worker's bracket",
            },
        ),
        "at_rest": (),
    },
    {
        "scenario": "starvation",
        "layers": ("material_base", "survival"),
        "systems": (
            {
                "system": "VitalitySystem",
                "kind": "event",
                "key": "entity_death",
                "claim": "under starvation-level extraction (0.05), the comprador's coverage ratio "
                "collapses to full extinction (Phase 3 - The Reaper)",
            },
            {
                "system": "VitalitySystem",
                "kind": "entity_delta",
                "key": "C002.active",
                "claim": "the comprador is marked inactive on extinction",
            },
            {
                "system": "SurvivalSystem",
                "kind": "entity_delta",
                "key": "C001.p_acquiescence",
                "claim": "survival calculus still recomputes P(S|A) under the starvation "
                "extraction-efficiency override",
            },
            {
                "system": "ImperialRentSystem",
                "kind": "economy_delta",
                "key": "imperial_rent_pool",
                "claim": "the rent pool still accrues/decays even at low (0.05) extraction efficiency",
            },
        ),
        "at_rest": (),
    },
    {
        "scenario": "glut",
        "layers": ("material_base", "consciousness"),
        "systems": (
            {
                "system": "VitalitySystem",
                "kind": "entity_delta",
                "key": "C001.wealth",
                "claim": "periphery worker wealth still moves under the zero-subsistence, "
                "high-extraction (0.99) override",
            },
            {
                "system": "ImperialRentSystem",
                "kind": "economy_delta",
                "key": "imperial_rent_pool",
                "claim": "extraction at 0.99 efficiency drives the rent pool sharply",
            },
            {
                "system": "ConsciousnessSystem",
                "kind": "entity_delta",
                "key": "C004.national_identity",
                "claim": "labor-aristocracy agitation routes to national identity under high "
                "extraction with zero solidarity",
            },
            {
                "system": "StruggleSystem",
                "kind": "event",
                "key": "excessive_force",
                "claim": "the stochastic spark still rolls every tick under the glut override",
            },
        ),
        "at_rest": (),
    },
    {
        "scenario": "fascist_bifurcation",
        "layers": ("material_base", "consciousness"),
        "systems": (
            {
                "system": "ConsciousnessSystem",
                "kind": "entity_delta",
                "key": "C002.national_identity",
                "claim": "wage-crisis agitation routes to national identity — the named Fascist "
                "Bifurcation mechanic, solidarity_pressure=0 by scenario design",
            },
            {
                "system": "FascistFactionSystem",
                "kind": "event",
                "key": "fascist_drift",
                "claim": "entitled-role agitation over zero incident solidarity crosses the "
                "fascist-pull threshold",
            },
            {
                "system": "StruggleSystem",
                "kind": "event",
                "key": "fascist_revanchism",
                "claim": "on comprador insolvency, low periphery revolutionary capacity routes the "
                "George Jackson bifurcation to Fascist Revanchism, boosting the labor "
                "aristocracy's national_identity and p_acquiescence",
            },
            {
                "system": "ImperialRentSystem",
                "kind": "economy_delta",
                "key": "imperial_rent_pool",
                "claim": "the rent pool still accrues/decays under the calibrated "
                "extraction/consciousness-sensitivity override",
            },
        ),
        "at_rest": (),
    },
    {
        # detroit_tri_county: not one of the five canonical qa:regression
        # scenarios (it is the committed e2e headless-runner baseline, spec-102/
        # spec-065), but its bundle is a real, verified fixture — used here ONLY
        # for bundle_event/bundle_field rows checked against the committed JSON,
        # per Task 3's controller resolution. Every candidate row was probed
        # against tests/baselines/detroit-tri-county-5t.json before being kept;
        # OODASystem's "organizational_action" event was tried and REJECTED —
        # its payload is {"org_count": 0, "action_count": 0, "layer0_count": 0}
        # on every one of the 5 ticks in this baseline, the identical weakness
        # that put OODASystem in COVERAGE_GAPS_DATA in the first place, so it
        # stays a gap (see task-3-report.md for the full evidence trail).
        "scenario": "detroit_tri_county",
        "layers": ("dialectics",),
        "systems": (
            {
                "system": "ContradictionSystem",
                "kind": "bundle_field",
                "key": "terminal_state.max_tension",
                "claim": "the committed baseline's terminal max_tension (0.667728, "
                "MAX(tension) over EXPLOITATION edges per "
                "headless_runner.runner._query_max_tension) diverges from the "
                "bridge's static tick-0 EXPLOITATION seed (tension=0.1, "
                "bridge._build_per_county_relationships), proving "
                "ContradictionSystem._write_edge_tensions computed and "
                "persisted a real wealth-asymmetry gap rather than leaving the "
                "seed value untouched",
                # Presence alone doesn't prove this — max_tension is
                # schema-static (always emitted, even 0.0 when inert). "0.1"
                # is the bridge's static tick-0 EXPLOITATION seed;
                # "0.0" is _query_max_tension's own inert/empty-table
                # default. A future baseline regen landing on either value
                # means ContradictionSystem's edge-tension write did NOT
                # fire, and this row's claim would be false.
                "forbidden_values": ("0.1", "0.0"),
            },
        ),
        "at_rest": (),
    },
    {
        # single_county (Task 8, E2a): the smallest graph where the Vol III
        # financial layer fires THROUGH THE PRODUCTION PATH — the scenario
        # this program exists for (U9's interest-rate inertness shipped
        # invisible because no gate scenario carried a county). Verified by
        # a live 52-tick spot-run (2026-07-20, task-8-report.md) with
        # tools.regression_test.build_single_county_overrides' real
        # Wayne-County tensor_registry: distribution.interest_payments ==
        # 970247586.15 (> 0, real, not a fixture stamp), national_financial
        # endogenous_interest.rate == 0.01783... (> 0), and state.market is
        # a live MarketState (not None) by tick 52.
        "scenario": "single_county",
        "layers": ("material_base", "financial", "market"),
        "systems": (
            {
                "system": "TickDynamicsSystem",
                "kind": "context_presence",
                "key": "_tick_dynamics",
                "claim": "county economic state computed from realized Wayne tensors",
            },
            {
                "system": "TickDynamicsSystem",
                "kind": "context_presence",
                "key": "_national_financial",
                "claim": "endogenous interest rate (Vol III Part V) computed and published",
            },
            {
                "system": "MarketScissorsSystem",
                "kind": "state_presence",
                "key": "market",
                "claim": "price-value axis live over a county-bearing graph",
            },
        ),
        "at_rest": (),
    },
)

SCENARIO_COVERAGE: Final[tuple[ScenarioCoverage, ...]] = tuple(
    ScenarioCoverage(**d) for d in SCENARIO_COVERAGE_DATA
)

# Systems NO canonical scenario evidences, with TRUE reasons verified by
# spot-run (see task-2-report.md). Every one of these is a real, checked
# finding, not a placeholder: each was read in source AND probed live
# (40-150 tick runs) before being declared a gap here — originally audited
# against the first five scenarios; TickDynamicsSystem was CLOSED in Task 8
# via single_county's context_presence rows (see that entry above and
# task-8-report.md) and removed from this list. detroit_tri_county and any
# nationwide/hex-seeded scenario are the natural remediation path for the
# remaining organization/faction/sovereign/hex-dependent rows; a few
# (MetabolismSystem, TerritorySystem, EdgeTransitionSystem) need either a new
# evidence *kind* (territory_delta doesn't exist yet) or a scenario
# specifically calibrated to cross a threshold that never gets crossed in
# the six canonical scenarios today. ContradictionSystem was CLOSED in Task 3
# via a bundle_field row against the committed detroit-tri-county-5t.json
# baseline (terminal_state.max_tension diverges from the seeded tick-0
# value) — see the detroit_tri_county entry above and task-3-report.md.
COVERAGE_GAPS_DATA: Final[tuple[dict[str, str], ...]] = (
    {
        "system": "SubstrateSystem",
        "reason": "no canonical scenario seeds HEX-type nodes; the substrate stock pass-through "
        "(raw_material_stock/energy_stock/biocapacity_stock) never touches a single node",
        "remediation": "owner-gated nationwide scenario (task #49) or a hex-seeded canonical scenario",
    },
    {
        "system": "EpistemicHorizonSystem",
        "reason": "writes shadow mass_receptivity/intel_confidence/vision_state onto TERRITORY "
        "nodes only (not state.entities) and emits no events; Phase-1 observe-only shadow "
        "per its own docstring",
        "remediation": "a bundle_field row against the committed detroit_tri_county baseline "
        "(Task 6+), which sets player_org_id",
    },
    {
        "system": "OODASystem",
        "reason": "no organizations are seeded in any canonical scenario (single_county, Task 8, "
        "seeds only 2 SocialClass + 1 Territory — no ORGANIZATION nodes); the per-tick "
        "ORGANIZATIONAL_ACTION summary event fires every tick but with "
        "org_count=action_count=layer0_count=0 — the turn-resolution loop's own control "
        "flow runs, but no organizational action, initiative resolution, or verb-resolver "
        "logic ever exercises",
        "remediation": "detroit_tri_county / a future org-seeding scenario, which would carry "
        "OODASystem's real evidence",
    },
    {
        "system": "FactionInfluenceSystem",
        "reason": "no FACTION nodes are seeded; winning_faction_for_territory returns None for "
        "every territory every tick, so balkanization.winning_faction_by_territory stays "
        "an empty dict and no TERRITORY_TRANSITION/FACTION_VICTORY/RED_SETTLER_TRAP_DETECTED"
        "/SECESSION_DECLARED event fires",
        "remediation": "a balkanization-scenario fixture seeding FACTION + INFLUENCES edges",
    },
    {
        "system": "DoctrineSystem",
        "reason": "no ORGANIZATION nodes are seeded (single_county, Task 8, included); the "
        "system's own module docstring documents it as a no-op on the qa:regression "
        "goldens for exactly this reason",
        "remediation": "detroit_tri_county / nationwide, which seed the Cadre Council player org",
    },
    {
        "system": "SovereigntySystem",
        "reason": "no SOVEREIGN nodes are seeded; CLAIMS-based effective-controller/metabolic-impact "
        "resolution and DUAL_POWER_ACTIVE detection never exercise (the unconditional "
        "empty-dict persistent_data write every tick is bookkeeping, not material logic)",
        "remediation": "a balkanization-scenario fixture seeding SOVEREIGN nodes + CLAIMS edges",
    },
    {
        "system": "MetabolismSystem",
        "reason": "writes biocapacity/max_biocapacity onto TERRITORY nodes only (unobservable via "
        "entity_delta); ECOLOGICAL_OVERSHOOT never fires in 150 ticks in ANY of the five "
        "scenarios, including 'glut' ('High extraction with metabolic overshoot') — its "
        "extraction_efficiency override does not push total_consumption/total_biocapacity "
        "past overshoot_threshold within the horizon tested",
        "remediation": "recalibrate glut's defines_overrides to actually cross overshoot_threshold, "
        "or add a territory_delta evidence kind",
    },
    {
        "system": "TerritorySystem",
        "reason": "no PENAL_COLONY/CONCENTRATION_CAMP territory types are seeded, and the default "
        "OperationalProfile decays heat from a 0.0 starting value (0 * anything = 0), so "
        "heat/eviction/necropolitics never engage; the one write that does occur (heat) "
        "is territory-scoped, unobservable via entity_delta",
        "remediation": "a scenario seeding a HIGH_PROFILE territory or a PENAL_COLONY/"
        "CONCENTRATION_CAMP sink node, plus a territory_delta evidence kind",
    },
    {
        "system": "ReserveArmySystem",
        "reason": "no territory carries a positive reserve_ratio in any of the five scenarios; "
        "RESERVE_ARMY_PRESSURE never fires and median_wage/wage_pressure are "
        "territory-scoped",
        "remediation": "seed reserve_ratio on a canonical scenario's territories",
    },
    {
        "system": "DispossessionEventSystem",
        "reason": "no territory carries a positive foreclosure_rate/eviction_rate/displacement_rate "
        "in any of the five scenarios; DISPOSSESSION_EVENT/VALUE_TRANSFER never fire in "
        "150 ticks",
        "remediation": "seed dispossession rates on a canonical scenario's territories",
    },
    {
        "system": "DecompositionSystem",
        "reason": "SUPERWAGE_CRISIS never fires (neither ImperialRentSystem's pool-exhaustion path "
        "nor this system's own approaching-death early-warning path) within 150 ticks in "
        "any of the five scenarios, so CLASS_DECOMPOSITION correspondingly never fires",
        "remediation": "a longer-horizon or more austerity-calibrated scenario that actually "
        "exhausts the imperial rent pool or starves the labor aristocracy",
    },
    {
        "system": "ControlRatioSystem",
        "reason": "gated entirely behind persistent_data['_class_decomposition_tick'], set only by "
        "a successful DecompositionSystem run — which never happens in these five (see "
        "the DecompositionSystem gap); the step() body returns on its first guard clause "
        "every tick",
        "remediation": "resolves automatically once the DecompositionSystem gap is closed",
    },
    {
        "system": "SolidaritySystem",
        "reason": "every SOLIDARITY edge in all five scenarios has solidarity_strength=0.0 "
        "(imperial_circuit's scenario-seed default; two_node has no SOLIDARITY edge at "
        "all); the transmission loop's 'if solidarity_strength <= 0: continue' skips "
        "every edge every tick, so CONSCIOUSNESS_TRANSMISSION/MASS_AWAKENING never fire",
        "remediation": "a canonical scenario seeded with solidarity_strength > 0 (an "
        "internationalist variant)",
    },
    {
        "system": "CollapseTransitionSystem",
        "reason": "no SOVEREIGN nodes are seeded; SOVEREIGN_COLLAPSE/CIVIL_WAR_DECLARED/"
        "TERRITORY_TRANSITION never fire — both the collapse-driven and active-secession "
        "paths are gated on Sovereign/Faction state that does not exist",
        "remediation": "a balkanization-scenario fixture seeding SOVEREIGN nodes",
    },
    {
        "system": "CommunitySystem",
        "reason": "services.community_hypergraph is None (the plain in-memory step() API's "
        "default) and no MEMBERSHIP edges are seeded; the step() body returns on its "
        "first or second guard clause every tick",
        "remediation": "wire a community_hypergraph via step()'s calculator_overrides, or a "
        "scenario seeding MEMBERSHIP edges + community states",
    },
    {
        "system": "EdgeTransitionSystem",
        "reason": "no edge in any of the five scenarios carries an edge_mode attribute (Relationship "
        "does not declare that field, and no scenario factory sets it); the 17-transition "
        "predicate table never evaluates a real transition. The one unconditional write "
        "(persistent_data['latent_contradictions'] = {}, from _co_optive_suppression "
        "finding zero CO_OPTIVE edges) is an empty-dict bookkeeping stamp, not material "
        "logic",
        "remediation": "a scenario seeding an edge_mode-bearing edge with a predicate-crossing "
        "condition",
    },
)

COVERAGE_GAPS: Final[tuple[CoverageGap, ...]] = tuple(CoverageGap(**d) for d in COVERAGE_GAPS_DATA)

# Dense-column suffix -> System class names that may write it (E4 attribution;
# the sentinel proves every named system exists). PURE LITERAL. Corrected
# against source (`rg -n "update_node\(|update_edge\(" src/babylon/engine/
# systems/`) — see task-2-report.md for the per-channel writer audit; several
# entries here differ from the brief's scouting hypothesis (e.g. "wealth"
# gains ImperialRentSystem/StruggleSystem/DispossessionEventSystem/
# DecompositionSystem/OODASystem and drops SurvivalSystem/WealthDistribution
# System, which write p_acquiescence/p_revolution and wealth_share
# respectively, never wealth itself).
CHANNEL_WRITERS: Final[dict[str, tuple[str, ...]]] = {
    "wealth": (
        "VitalitySystem",
        "ProductionSystem",
        "ImperialRentSystem",
        "StruggleSystem",
        "MarketScissorsSystem",
        "DispossessionEventSystem",
        "DecompositionSystem",
        "OODASystem",
    ),
    "effective_wealth": ("ImperialRentSystem",),
    "p_acquiescence": ("SurvivalSystem", "StruggleSystem"),
    "p_revolution": ("SurvivalSystem", "StruggleSystem"),
    "active": ("VitalitySystem", "DecompositionSystem"),
    "class_consciousness": ("ConsciousnessSystem", "SolidaritySystem", "StruggleSystem"),
    "national_identity": ("ConsciousnessSystem", "StruggleSystem"),
    "agitation": ("ConsciousnessSystem", "StruggleSystem"),
    "organization": ("TerritorySystem",),
    "repression_faced": ("ImperialRentSystem", "OODASystem"),
    "value_flow": ("ImperialRentSystem",),
    "tension": ("ContradictionSystem",),
    "economy_imperial_rent_pool": ("ImperialRentSystem",),
    "economy_current_super_wage_rate": ("ImperialRentSystem",),
    "economy_current_repression_level": ("ImperialRentSystem",),
}
