"""Bus ``Event`` -> ``ChronicleEvent`` adapter (Program v1.0.0, Unit T4-core/C4).

Promotes the WO-50 pilot test's own documented stand-in
(``tests/integration/archive/test_pilot_first_action.py::
_chronicle_events_from_bus`` — its docstring: *"HONEST GAP: no production
engine-event to ChronicleEvent adapter ships yet ... A future WO must ship
the production adapter this stands in for"*) into production, per the
program plan's Part 2 spine D: *"promote
``tests/integration/archive/test_pilot_first_action.py::
_chronicle_events_from_bus`` into src/ with real summary generation."*

**What changed vs. the test-local stand-in.** The stand-in's summary was a
placeholder — ``f"{event_type.value} · tick {event.tick}"`` — the same
generic line for every event, real content or not. :func:`summarize_event`
replaces that with a deterministic, human-readable, PER-``EventType`` one
line, built as a **pure function over the event's payload** (no randomness,
no wall-clock, no I/O): the same ``(event_type, payload)`` always renders
the same text.

**NO LLM here.** Narrator prose is T5's lane (``babylon.projection.vault.
narrator_cache`` / the corpus-grounded RAG digest) — this module only ever
does deterministic string formatting over real payload fields, never a
generated sentence.

**Ground truth, not invention.** :data:`_SUMMARY_BUILDERS` covers every
``EventType`` this module could VERIFY a real production payload shape for
— cross-checked field-by-field against ``babylon.engine.event_builders.
EVENT_BUILDERS`` (the tested bus->pydantic contract table
``tests/unit/engine/test_event_builders.py`` already pins) and the engine's
own ``EventBus.publish(Event(...))`` call sites. That is 64 of the 84
``EventType`` values — exactly ``EVENT_BUILDERS``' own coverage, and the
field-by-field cross-check is no longer prose-only: ``tests/unit/game/
test_chronicle_adapter.py::
test_summary_builders_only_read_wire_keys_event_builders_also_reads``
statically parses both registries' source and asserts every wire key a
``_SUMMARY_BUILDERS`` lambda reads is a key ``EVENT_BUILDERS``' OWN builder
for that ``EventType`` also reads (this is what caught ``CLASS_DECOMPOSITION``
reading the pydantic field name ``original_id`` instead of the wire key
``source_class``). The remaining 20 (e.g. ``ENDGAME_REACHED``,
``PATTERN_SHIFT``, ``SOLIDARITY_AWAKENING``, ``STATE_ACTION_EXECUTED``, the
institution/faction/thread-escalation family) have NO verified production
publish site as of this writing — several are documented gaps elsewhere
(``babylon.game.session``'s own module docstring notes ``ENDGAME_REACHED``/
the endgame fold has no bus event yet; the WO-50 pilot's crisis leg
constructs an ``ENDGAME_REACHED`` :class:`~babylon.tui.chronicle.
ChronicleEvent` BY HAND for exactly this reason). Inventing a phrased
summary for a payload shape nobody can verify would be a fabrication
(Constitution III.11), so those — and any ``EventType`` added after this
module was written — fall through to :func:`_generic_summary` instead:
never dropped, never guessed at, always loud about the gap.

**Malformed events still raise.** :func:`chronicle_events_from_bus` mirrors
the pilot's own coercion discipline: a bus ``Event`` whose ``.type`` is not
a real ``EventType`` value raises (a bug elsewhere — a malformed event is
never silently absorbed into the Chronicle).

**Event-to-territory anchoring (Unit U5).** Several verified payload shapes
carry a bare social_class node id with no place to report — e.g. struggle.py's
``EventType.UPRISING``/``EXCESSIVE_FORCE``/``SOLIDARITY_SPIKE`` all publish
the SAME struggling class's ``node.id``; ``reactionary.py`` does the same
for ``FASCIST_DRIFT``; the reactionary-verb family (``POGROM``/``LOCKOUT``/
``VIGILANTISM``) publishes the victim class as ``target_id`` — the SAME
``target_id`` the legacy ``web/game/engine_bridge.py::
_TERRITORY_ANCHORED_VERB_EVENTS`` precedent already anchors for the map
layer. :data:`_CLASS_ANCHOR_FIELD` names, per ``EventType``, which payload
key holds that resolvable social_class id; when a live ``graph`` is threaded
through (:func:`chronicle_events_from_bus`'s ``graph=`` parameter —
``GameSession.advance_tick`` threads its own live, post-tick graph, never a
``WorldState.from_graph()`` round trip, which drops the TENANCY edges this
resolution reads), the resolved :class:`~babylon.projection.
territory_anchor.TerritoryAnchor` is added as ``data["anchor"]`` and
appended to the human summary. The TENANCY-inversion primitive itself
(:func:`~babylon.projection.territory_anchor.tenancy_members_by_territory` /
:func:`~babylon.projection.territory_anchor.class_to_territory`) is the ONE
shared home :mod:`babylon.projection.verbs.plate` also consumes — no third
copy. An event whose payload never carries the field, or whose class id
carries no live TENANCY edge into any territory, resolves to no anchor at
all (Constitution III.11: honest absence, never a fabricated territory);
``graph=None`` (the default) reproduces the exact pre-U5 behavior.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, Final

from babylon.kernel.event_bus import Event
from babylon.models.enums.events import EventType
from babylon.projection.territory_anchor import (
    TerritoryAnchor,
    class_to_territory,
    resolve_class_territory_anchor,
    tenancy_members_by_territory,
)
from babylon.topology import BabylonGraph
from babylon.tui.chronicle import ChronicleEvent

__all__ = [
    "SummaryBuilder",
    "summarize_event",
    "chronicle_events_from_bus",
]

_CLASS_ANCHOR_FIELD: Final[dict[EventType, str]] = {
    EventType.EXCESSIVE_FORCE: "node_id",
    EventType.UPRISING: "node_id",
    EventType.SOLIDARITY_SPIKE: "node_id",
    EventType.FASCIST_DRIFT: "node_id",
    EventType.POGROM: "target_id",
    EventType.LOCKOUT: "target_id",
    EventType.VIGILANTISM: "target_id",
}
"""``EventType`` -> the payload key holding a resolvable social_class node id
(see the module docstring's "Event-to-territory anchoring" section for the
per-EventType provenance). Deliberately narrow: only EventTypes this module
could VERIFY carry a social_class id here — the same "ground truth, not
invention" discipline :data:`_SUMMARY_BUILDERS` already applies. An
``EventType`` absent from this table never gains an anchor, even when a
live ``graph`` is supplied."""

SummaryBuilder = Callable[[Mapping[str, Any]], str]
"""A pure function: one event's raw ``payload`` -> its one-line summary."""


def _num(value: Any) -> str:
    """Render a numeric payload value to 2 decimals; ``"?"`` when absent.

    Honest-absence helper (Constitution III.11) for the handful of fields
    ``engine.event_builders.EVENT_BUILDERS`` itself reads with NO default
    (``payload.get(key)`` — e.g. ``profit_rate``, ``max_abs_df_dt``'s sibling
    ``previous_field``): a genuinely missing optional value renders as
    ``"?"`` rather than a fabricated ``0.00``.

    :param value: the raw payload value (typically ``float | int | None``).
    :returns: the formatted string.
    """
    if value is None:
        return "?"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _txt(value: Any, *, default: str = "?") -> str:
    """Render a string-ish payload value; ``default`` when absent/empty.

    :param value: the raw payload value.
    :param default: what to render for ``None`` or ``""``.
    :returns: the formatted string.
    """
    return str(value) if value not in (None, "") else default


# --------------------------------------------------------------------------- #
# Per-EventType summary builders — one line each, field names + defaults      #
# cross-checked against babylon.engine.event_builders.EVENT_BUILDERS.         #
# --------------------------------------------------------------------------- #

_SUMMARY_BUILDERS: Final[dict[EventType, SummaryBuilder]] = {
    # --- Economic core -------------------------------------------------- #
    EventType.SURPLUS_EXTRACTION: lambda p: (
        f"{p.get('source_id', '')} yields {p.get('amount', 0.0):.2f} in surplus "
        f"to {p.get('target_id', '')} via {p.get('mechanism', 'imperial_rent')}"
    ),
    EventType.IMPERIAL_SUBSIDY: lambda p: (
        f"{p.get('source_id', '')} subsidizes {p.get('target_id', '')} with "
        f"{p.get('amount', 0.0):.2f} (repression +{p.get('repression_boost', 0.0):.2f})"
    ),
    EventType.ECONOMIC_CRISIS: lambda p: (
        f"economic crisis: pool ratio {p.get('pool_ratio', 0.0):.2f}, "
        f"tension {p.get('aggregate_tension', 0.0):.2f} — {p.get('decision', 'UNKNOWN')} "
        f"(wage Δ{p.get('wage_delta', 0.0):.2f})"
    ),
    EventType.MARKET_CORRECTION: lambda p: (
        f"market correction: overhang {p.get('overhang', 0.0):.2f}, "
        f"serviceable {p.get('serviceable', 0.0):.2f} (fictitious log "
        f"{p.get('fictitious_log_before', 0.0):.2f}->{p.get('fictitious_log_after', 0.0):.2f})"
    ),
    EventType.VALUE_TRANSFER: lambda p: (
        f"{p.get('territory', '')} transfers {p.get('total_transferred', 0.0):.2f} in value "
        f"(net {p.get('net_received', 0.0):.2f}, deadweight loss "
        f"{p.get('deadweight_loss', 0.0):.2f})"
    ),
    EventType.RESERVE_ARMY_PRESSURE: lambda p: (
        f"{p.get('territory', '')} reserve-army pressure: ratio "
        f"{p.get('reserve_ratio', 0.0):.2f}, wage pressure {p.get('wage_pressure', 0.0):.2f} "
        f"(median wage {p.get('median_wage', 0.0):.2f})"
    ),
    EventType.DISPOSSESSION_EVENT: lambda p: (
        f"dispossession in {p.get('territory', '')}: intensity "
        f"{p.get('intensity', 0.0):.2f} (foreclosure {p.get('foreclosure_rate', 0.0):.2f}, "
        f"eviction {p.get('eviction_rate', 0.0):.2f})"
    ),
    EventType.DISPOSSESSION_CASCADE: lambda p: (
        f"{p.get('fips', '')} dispossession cascade: labor-aristocracy share "
        f"{p.get('current_la_share', 0.0):.2f} (baseline {p.get('baseline_la_share', 0.0):.2f}, "
        f"milestone {p.get('milestone_crossed', 0.0):.2f})"
    ),
    EventType.INHERITANCE_TRANSFER: lambda p: (
        f"{p.get('territory_id', '')} inheritance transfer: "
        f"{p.get('total_transferred', 0.0):.2f} total (net {p.get('net_inheritance', 0.0):.2f}, "
        f"gini {p.get('inheritance_gini', 0.0):.2f})"
    ),
    EventType.ECOLOGICAL_OVERSHOOT: lambda p: (
        f"ecological overshoot: ratio {p.get('overshoot_ratio', 0.0):.2f} "
        f"(consumption {p.get('total_consumption', 0.0):.2f} / "
        f"biocapacity {p.get('total_biocapacity', 0.0):.2f})"
    ),
    # --- Consciousness / agency ------------------------------------------ #
    EventType.CONSCIOUSNESS_TRANSMISSION: lambda p: (
        f"{p.get('source_id', '')} transmits consciousness to {p.get('target_id', '')} "
        f"(Δ{p.get('delta', 0.0):.2f}, solidarity {p.get('solidarity_strength', 0.0):.2f})"
    ),
    EventType.MASS_AWAKENING: lambda p: (
        f"{p.get('target_id', '')} mass-awakens: consciousness "
        f"{p.get('old_consciousness', 0.0):.2f} -> {p.get('new_consciousness', 0.0):.2f} "
        f"(via {p.get('triggering_source', '')})"
    ),
    EventType.EXCESSIVE_FORCE: lambda p: (
        f"excessive force at {p.get('node_id', '')}: repression "
        f"{p.get('repression', 0.0):.2f}, spark probability "
        f"{p.get('spark_probability', 0.0):.2f}"
    ),
    EventType.UPRISING: lambda p: (
        f"uprising at {p.get('node_id', '')}: trigger {p.get('trigger', 'unknown')}, "
        f"agitation {p.get('agitation', 0.0):.2f}, repression {p.get('repression', 0.0):.2f}"
    ),
    EventType.SOLIDARITY_SPIKE: lambda p: (
        f"solidarity spike at {p.get('node_id', '')}: "
        f"+{p.get('solidarity_gained', 0.0):.2f} across {p.get('edges_affected', 0)} edges "
        f"(triggered by {p.get('triggered_by', 'unknown')})"
    ),
    # --- Dialectical field topology --------------------------------------- #
    EventType.RUPTURE: lambda p: (
        f"rupture on {p.get('edge', '')}: {p.get('opposition', '')} gap "
        f"{p.get('gap', 0.0):.2f} at rate {p.get('rate', 0.0):.2f}"
    ),
    EventType.PHASE_TRANSITION: lambda p: (
        f"phase transition: {p.get('previous_state', '')} -> {p.get('new_state', '')} "
        f"(percolation {p.get('percolation_ratio', 0.0):.2f}, "
        f"{p.get('num_components', 0)} components)"
    ),
    EventType.EDGE_MODE_TRANSITION: lambda p: (
        f"{p.get('source_id', '')}->{p.get('target_id', '')} edge mode: "
        f"{p.get('from_mode', '')} -> {p.get('to_mode', '')} ({p.get('predicate', '')})"
    ),
    EventType.PRINCIPAL_CONTRADICTION_SHIFT: lambda p: (
        f"principal contradiction shifts to {p.get('new_field', '')} "
        f"(from {_txt(p.get('previous_field'))}; max|df/dt| {_num(p.get('max_abs_df_dt', 0.0))})"
    ),
    EventType.LEVEL_TRANSITION: lambda p: (
        f"{p.get('opposition', '')} sublated: {p.get('from_level', '')} -> "
        f"{p.get('to_level', '')} (gap {p.get('gap', 0.0):.2f}, rate {p.get('rate', 0.0):.2f})"
    ),
    EventType.CO_OPTIVE_BREAKDOWN: lambda p: (
        f"co-optation breaks down between {p.get('source_id', '')} and "
        f"{p.get('target_id', '')}: latent contradictions released "
        f"(×{p.get('multiplier', 0.0):.2f})"
    ),
    EventType.LATENT_CONTRADICTION_RELEASE: lambda p: (
        f"{p.get('node_id', '')} releases latent contradictions: "
        + (", ".join(sorted(str(k) for k in p.get("released_fields", {}) or {})) or "none named")
    ),
    EventType.ASPECT_REVERSAL: lambda p: (
        f"{p.get('source_id', '')}->{p.get('target_id', '')} aspect reverses: "
        f"{p.get('previous_dominant', '')} -> {p.get('new_dominant', '')} dominant"
    ),
    # --- Terminal crisis dynamics ------------------------------------------ #
    EventType.PERIPHERAL_REVOLT: lambda p: (
        f"peripheral revolt at {p.get('node_id', '')}: "
        f"{p.get('edges_severed', 0)} exploitation edges severed "
        f"(P(revolution) {p.get('p_revolution', 0.0):.2f} vs "
        f"P(acquiescence) {p.get('p_acquiescence', 0.0):.2f})"
    ),
    EventType.SUPERWAGE_CRISIS: lambda p: (
        f"superwage crisis: {p.get('payer_id', '')} cannot cover "
        f"{p.get('receiver_id', '')}'s wages ({p.get('desired_wages', 0.0):.2f} desired, "
        f"{p.get('available_pool', 0.0):.2f} available)"
    ),
    EventType.CLASS_DECOMPOSITION: lambda p: (
        # Wire key is `source_class` — see engine.systems.decomposition's
        # publish site and event_builders.EVENT_BUILDERS' own
        # `original_id=payload.get("source_class", "")`. `original_id` is
        # only the POST-ADAPTATION pydantic field name, never a wire key.
        f"{p.get('source_class', '')} decomposes: "
        f"{p.get('enforcer_fraction', 0.3):.2f} enforcers / "
        f"{p.get('proletariat_fraction', 0.7):.2f} proletariat"
    ),
    EventType.CONTROL_RATIO_CRISIS: lambda p: (
        f"control-ratio crisis: {p.get('prisoner_population', 0)} prisoners vs "
        f"{p.get('enforcer_population', 0)} enforcers "
        f"(ratio {p.get('control_ratio', 0.0):.2f}, "
        f"threshold {p.get('capacity_threshold', 0.0):.2f})"
    ),
    EventType.TERMINAL_DECISION: lambda p: (
        f"terminal decision: {p.get('outcome', 'genocide')} "
        f"(organization {p.get('avg_organization', 0.0):.2f} vs "
        f"threshold {p.get('revolution_threshold', 0.0):.2f})"
    ),
    # --- Crisis / devaluation ------------------------------------------ #
    EventType.CRISIS_PHASE_TRANSITION: lambda p: (
        f"{p.get('fips', '')} crisis phase: {p.get('previous_phase', '')} -> "
        f"{p.get('new_phase', '')} ({p.get('crisis_duration', 0)} ticks; "
        f"profit rate {_num(p.get('profit_rate'))})"
    ),
    EventType.BIFURCATION_THRESHOLD: lambda p: (
        f"{p.get('fips', '')} bifurcation threshold crossed {p.get('direction', '')}: "
        f"score {p.get('score', 0.0):.2f} (solidarity density "
        f"{p.get('solidarity_density', 0.0):.2f}, legitimation {p.get('legitimation', 0.0):.2f})"
    ),
    # --- Institution (Feature 040) -------------------------------------- #
    EventType.INSTITUTION_FACTION_SHIFT: lambda p: (
        f"{p.get('institution_id', '')} hegemonic fraction shifts: "
        f"{p.get('old_fraction', '')} -> {p.get('new_fraction', '')}"
    ),
    EventType.INSTITUTION_BONAPARTIST_MODE: lambda p: (
        f"{p.get('institution_id', '')} crosses the Bonapartist threshold "
        f"(weight {p.get('bonapartist_weight', 0.0):.2f})"
    ),
    # --- Balkanization (spec-070) ---------------------------------------- #
    EventType.SOVEREIGN_COLLAPSE: lambda p: (
        f"{p.get('sovereign_id', '')} sovereign collapses ({p.get('trigger', 'legitimacy_zero')}); "
        f"{p.get('claimed_territories_count', 0)} territories contested"
    ),
    EventType.TERRITORY_TRANSITION: lambda p: (
        f"{p.get('territory_id', '')} transitions: "
        f"{_txt(p.get('from_sovereign_id'), default='unclaimed')} -> "
        f"{_txt(p.get('to_sovereign_id'), default='unclaimed')} "
        f"({p.get('reason', 'influence_flip')})"
    ),
    EventType.FACTION_VICTORY: lambda p: (
        f"{p.get('faction_id', '')} declares victory "
        f"(influence share {p.get('aggregate_influence_share', 0.0):.2f})"
    ),
    EventType.SECESSION_DECLARED: lambda p: (
        f"{p.get('secessionist_faction_id', '')} secedes from "
        f"{p.get('parent_sovereign_id', '')} "
        f"({len(p.get('contiguous_territory_ids', ()) or ())} territories)"
    ),
    EventType.CIVIL_WAR_DECLARED: lambda p: (
        f"civil war: {p.get('secessionist_faction_id', '')} vs "
        f"{p.get('parent_sovereign_id', '')} "
        f"({p.get('contested_territory_count', 0)} territories contested)"
    ),
    EventType.RED_SETTLER_TRAP_DETECTED: lambda p: (
        f"{p.get('faction_id', '')} red-settler trap detected: class reduction "
        f"{p.get('class_reduction', 0.0):.2f} ({p.get('colonial_stance', 'uphold')})"
    ),
    EventType.DUAL_POWER_ACTIVE: lambda p: (
        f"dual power active in {p.get('territory_id', '')}: "
        f"{len(p.get('competing_sovereign_ids', ()) or ())} competing sovereigns "
        f"(control sum {p.get('control_level_sum', 0.0):.2f})"
    ),
    # --- Reactionary subject (spec-071) ----------------------------------- #
    EventType.FASCIST_DRIFT: lambda p: (
        f"{p.get('node_id', '')} drifts fascist: pull {p.get('fascist_pull', 0.0):.2f}, "
        f"alignment {p.get('fascist_alignment', 0.0):.2f}"
    ),
    EventType.FASCIST_RECRUITMENT: lambda p: (
        f"{p.get('faction_id', '')} recruits {p.get('node_id', '')} "
        f"(fascist alignment {p.get('fascist_alignment', 0.0):.2f})"
    ),
    EventType.ORGANIZATIONAL_FRACTURE: lambda p: (
        f"{p.get('member_id', '')} defects from {p.get('org_id', '')} "
        f"(chauvinism {p.get('chauvinism', 0.0):.2f}, "
        f"P(defect) {p.get('defection_probability', 0.0):.2f})"
    ),
    EventType.RED_BROWN_COUP: lambda p: (
        f"{p.get('org_id', '')} suffers a red-brown coup: "
        f"{p.get('defections', 0)}/{p.get('member_count', 0)} members defected"
    ),
    EventType.POGROM: lambda p: (
        f"{p.get('org_id', '')} carries out a pogrom against {p.get('target_id', '')} "
        f"(wealth destroyed {p.get('wealth_destroyed', 0.0):.2f})"
    ),
    EventType.LOCKOUT: lambda p: (
        f"{p.get('org_id', '')} locks out {p.get('target_id', '')} "
        f"(wage attenuation {p.get('wage_attenuation', 0.0):.2f})"
    ),
    EventType.VIGILANTISM: lambda p: (
        f"{p.get('org_id', '')} commits vigilante violence against "
        f"{p.get('target_id', '')} (repression +{p.get('repression_increment', 0.0):.2f})"
    ),
    EventType.SPONTANEOUS_RIOT: lambda p: (
        f"spontaneous riot at {p.get('node_id', '')}: risk {p.get('riot_risk', 0.0):.2f} "
        f"(volatility {p.get('volatility', 0.0):.2f}, "
        f"discipline {p.get('organizational_discipline', 0.0):.2f})"
    ),
    # --- George Jackson bifurcation --------------------------------------- #
    EventType.POWER_VACUUM: lambda p: (
        f"power vacuum: {p.get('comprador_id', '')} insolvent "
        f"(wealth {p.get('comprador_wealth', 0.0):.2f} < "
        f"subsistence {p.get('subsistence_threshold', 0.0):.2f})"
    ),
    EventType.REVOLUTIONARY_OFFENSIVE: lambda p: (
        f"{p.get('periphery_id', '')} launches a revolutionary offensive "
        f"(capacity {p.get('revolutionary_capacity', 0.0):.2f}, "
        f"agitation +{p.get('agitation_boost', 0.0):.2f})"
    ),
    EventType.FASCIST_REVANCHISM: lambda p: (
        f"{_txt(p.get('core_worker_id'))} reacts with fascist revanchism "
        f"(identity +{p.get('identity_boost', 0.0):.2f}, "
        f"acquiescence +{p.get('acquiescence_boost', 0.0):.2f})"
    ),
    # --- D-P-D' lifecycle circuit (Feature 030) --------------------------- #
    EventType.LIFECYCLE_TRANSITION: lambda p: (
        f"{p.get('territory_id', '')} lifecycle: D={p.get('pop_d', 0.0):.2f} "
        f"P={p.get('pop_p', 0.0):.2f} D'={p.get('pop_d_prime', 0.0):.2f} "
        f"(dependency ratio {p.get('dependency_ratio', 0.0):.2f})"
    ),
    EventType.LEGITIMATION_CRISIS: lambda p: (
        f"{p.get('territory_id', '')} legitimation crisis "
        f"(index {p.get('legitimation_index', 0.0):.2f})"
    ),
    EventType.LEGITIMATION_RECOVERY: lambda p: (
        f"{p.get('territory_id', '')} legitimation recovers "
        f"(index {p.get('legitimation_index', 0.0):.2f})"
    ),
    # --- OODA loop system (Feature 032) ----------------------------------- #
    EventType.ORGANIZATIONAL_ACTION: lambda p: (
        f"{p.get('org_count', 0)} organizations acted this tick "
        f"({p.get('action_count', 0)} actions across {p.get('layer0_count', 0)} "
        "layer-0 businesses)"
    ),
    EventType.STATE_REPRESSION: lambda p: (
        f"{p.get('org_id', '')} represses {p.get('target_id', '')} "
        f"(backfire Δ{p.get('backfire_delta', 0.0):.2f})"
    ),
    EventType.STATE_SURVEILLANCE: lambda p: (
        f"{p.get('org_id', '')} surveils {p.get('target_id', '')} "
        f"(backfire Δ{p.get('backfire_delta', 0.0):.2f})"
    ),
    # --- ADR073 Doctrine Tree ---------------------------------------------- #
    EventType.DOCTRINE_TRAP_SPRUNG: lambda p: (
        f"{p.get('org_id', '')} falls into an ideological trap ({p.get('node_id', '')})"
    ),
    EventType.DOCTRINE_TRAP_ESCAPED: lambda p: (
        f"{p.get('org_id', '')}'s Party Congress purge escapes the trap ({p.get('node_id', '')})"
    ),
    EventType.DOCTRINE_PURGE_FAILED: lambda p: (
        f"{p.get('org_id', '')}'s Party Congress purge fails ({p.get('node_id', '')})"
    ),
    # --- Entity / population ---------------------------------------------- #
    EventType.ENTITY_DEATH: lambda p: (
        f"{p.get('entity_id', '')} dies ({p.get('cause', 'unknown')}): "
        f"wealth {p.get('wealth', 0.0):.2f} < needs {p.get('consumption_needs', 0.0):.2f}"
    ),
    EventType.POPULATION_ATTRITION: lambda p: (
        f"{p.get('entity_id', '')} suffers {p.get('deaths', 0)} attrition deaths "
        f"(rate {p.get('attrition_rate', 0.0):.2f}, "
        f"{p.get('remaining_population', 0)} remaining)"
    ),
    # --- Calibration warnings (spec-057) ----------------------------------- #
    EventType.CALIBRATION_AXIOM_VIOLATION: lambda p: (
        f"calibration: {p.get('industry', '')} ({p.get('year', 0)}) wage ratio "
        f"{p.get('ratio', 0.0):.2f} violates axiom (threshold {p.get('threshold', 1.0):.2f})"
    ),
    EventType.CALIBRATION_QCEW_CARRY_FORWARD: lambda p: (
        f"calibration: {p.get('county_fips', '')} QCEW data carried forward from "
        f"{p.get('look_back_year', 0)} ({p.get('look_back_distance', 0)} years back)"
    ),
    EventType.CALIBRATION_PHI_HOUR_OUTLIER: lambda p: (
        f"calibration: {p.get('county_fips', '')} phi-hour "
        f"{p.get('phi_hour', 0.0):.2f} outside "
        f"[{p.get('threshold_low', -1000.0):.2f}, {p.get('threshold_high', 1000.0):.2f}]"
    ),
}
"""``EventType`` -> its one-line summary builder. Covers 63 of 84 values —
every one this module could verify a real production payload shape for
(see the module docstring). Every other value renders through
:func:`_generic_summary`."""


def _generic_summary(event_type: EventType, tick: int, payload: Mapping[str, Any]) -> str:
    """The loud, honest fallback for any ``EventType`` with no bespoke builder.

    Never invents a narrative for a payload shape this module has not
    verified (Constitution III.11): names the raw wire value and tick, and
    lists whichever payload fields ARE present — or says so honestly when
    there are none — so the gap is visible rather than smoothed over.

    :param event_type: the event's real (coerced) :class:`EventType`.
    :param tick: the event's tick.
    :param payload: the event's raw payload dict.
    :returns: the generic one-line summary.
    """
    if not payload:
        return f"{event_type.value} (tick {tick}) — no payload recorded"
    fields = ", ".join(sorted(str(key) for key in payload))
    return f"{event_type.value} (tick {tick}) — fields: {fields}"


def summarize_event(event_type: EventType, tick: int, payload: Mapping[str, Any]) -> str:
    """Render ``event_type``'s deterministic, human-readable one-line summary.

    A pure function over ``payload``: the SAME ``(event_type, payload)``
    pair always renders the SAME text — no randomness, no wall-clock, no
    LLM (see the module docstring's "NO LLM here"). Dispatches through
    :data:`_SUMMARY_BUILDERS`; an ``event_type`` absent from that table
    renders through :func:`_generic_summary` instead — never dropped, never
    fabricated.

    :param event_type: the coerced, real :class:`EventType`.
    :param tick: the event's tick (unused by a bespoke builder — the
        Chronicle's own per-tick bulletin header already carries it, see
        ``babylon.tui.chronicle.render_bulletin``; used only by the
        generic fallback, which has no bespoke content to lead with).
    :param payload: the event's raw payload dict.
    :returns: the one-line summary.
    """
    builder = _SUMMARY_BUILDERS.get(event_type)
    if builder is not None:
        return builder(payload)
    return _generic_summary(event_type, tick, payload)


def _resolve_event_anchor(
    event_type: EventType,
    payload: Mapping[str, Any],
    class_to_territory_map: Mapping[str, str],
    graph: BabylonGraph,
) -> TerritoryAnchor | None:
    """Resolve one event's :class:`TerritoryAnchor`, or ``None`` if it has none.

    :param event_type: the event's coerced, real :class:`EventType`.
    :param payload: the event's raw payload dict.
    :param class_to_territory_map: this tick's precomputed
        :func:`~babylon.projection.territory_anchor.class_to_territory` map
        (computed once per :func:`chronicle_events_from_bus` call, never
        recomputed per-event).
    :param graph: the live world graph (for the territory's display name).
    :returns: the resolved anchor, or ``None`` when ``event_type`` carries no
        anchor-eligible field (:data:`_CLASS_ANCHOR_FIELD`), the field is
        absent/malformed, or the class id resolves to no territory.
    """
    field = _CLASS_ANCHOR_FIELD.get(event_type)
    if field is None:
        return None
    class_id = payload.get(field)
    if not isinstance(class_id, str) or not class_id:
        return None
    return resolve_class_territory_anchor(graph, dict(class_to_territory_map), class_id)


def chronicle_events_from_bus(
    raw_events: Sequence[Event], *, graph: BabylonGraph | None = None
) -> tuple[ChronicleEvent, ...]:
    """Promote one tick's real bus events into real :class:`ChronicleEvent`\\ s.

    The PRODUCTION replacement for the WO-50 pilot test's own documented
    stand-in (see the module docstring). Per-tick, never cumulative: this
    function does not itself collect the events — it is the CALLER's job to
    have gathered ``raw_events`` from exactly one tick's bus history first,
    exactly as :meth:`~babylon.game.session.GameSession.advance_tick` does
    (``event_bus.clear_history()`` before ``run_tick``, ``get_history()``
    after).

    Coercion of ``event.type`` to a real :class:`EventType` is loud
    (Constitution III.11): a bus event carrying a non-``EventType`` string
    raises here rather than being silently dropped — a malformed event is a
    bug elsewhere, never a quiet omission from the Chronicle. Loop bound:
    ``len(raw_events)``.

    :param raw_events: one tick's raw event-bus history, in emission order.
    :param graph: the live, post-tick world graph (see the module
        docstring's "Event-to-territory anchoring" section) —
        :meth:`~babylon.game.session.GameSession.advance_tick`'s OWN live
        graph object, never a ``WorldState.from_graph()`` round trip (which
        drops the TENANCY edges this resolution reads). ``None`` (the
        default) reproduces the exact pre-U5 behavior: no event gains an
        ``anchor``.
    :returns: one :class:`ChronicleEvent` per input event, same order.
    :raises ValueError: if any event's ``.type`` is not a real
        :class:`EventType` value.
    """
    class_to_territory_map: dict[str, str] = (
        class_to_territory(tenancy_members_by_territory(graph)) if graph is not None else {}
    )
    chronicle: list[ChronicleEvent] = []
    for event in raw_events:  # loop bound: len(raw_events)
        event_type = EventType(event.type)
        summary = summarize_event(event_type, event.tick, event.payload)
        data = dict(event.payload)
        if graph is not None:
            anchor = _resolve_event_anchor(event_type, event.payload, class_to_territory_map, graph)
            if anchor is not None:
                summary = f"{summary} (in {anchor.territory_name})"
                data["anchor"] = anchor.model_dump()
        chronicle.append(
            ChronicleEvent(
                tick=event.tick,
                event_type=event_type,
                summary=summary,
                data=data,
            )
        )
    return tuple(chronicle)
