"""Derived event-severity catalog (T1.1 Unit U1, ``ai/_inbox/t11-seam-severity-design.md``).

Replaces the two hand-copied 47-entry severity dicts (``web/game/engine_bridge.py``'s
``_EVENT_SEVERITY`` and ``babylon.tui.chronicle_salience``'s ``EVENT_SEVERITY``, byte-identical
twins with no mechanical guarantee they stayed equal) with ONE generated column, computed by a
pure rule from ``(kind, terminal_proximity)`` per the R-EC-1 event-kind taxonomy
(``ai/_inbox/math/babylon-events.md`` §II.7). U2 retargets both surfaces at :func:`resolve_severity`;
U6 adds the CI equality gate. This module is that single source of truth.

**The derivation rule** (design §2)::

    ALARM                          -> critical            # invariant residual, III.11, always
    CROSSING & TERMINAL_ADJACENT   -> critical             # void-adjacency / regime->crisis entry
    CROSSING & INTRA_LEVEL         -> informational        # reversible intra-level crossing
    FLOW | ACT                     -> salience_floor       # warning | informational, NEVER critical
    PATTERN                        -> tier of its declared base crossing
    unclassified (no row)          -> warning (loud floor, EventSeverity.unclassified=True)

**Load-bearing finding (design §2, restated here as the reconciliation this module performs).**
The pure rule is NOT a rubber stamp of the current 47 hand tiers: ``warning`` is reachable only
from FLOW/ACT (or the unclassified floor); a CROSSING is binary critical-or-informational. The
hand-copy has 20 members at ``warning``; of those, 4 are ACT (``state_repression``, ``pogrom``,
``lockout``, ``vigilantism`` — legitimately warning) and 16 are CROSSING or PATTERN-over-CROSSING,
which the pure rule **mechanically forces** off ``warning`` toward critical or informational.
:data:`DRIFT_TABLE` is the resulting old-tier -> new-tier reconciliation, one row per member whose
derived tier differs from its legacy hand tier, each carrying a declared rationale
(:data:`_DRIFT_RATIONALES`) — a drift with no rationale is a loud ``ValueError`` at import, never a
silent surprise ahead of the owner-facing ceremony (design §7).

**Open owner questions (design §9, unresolved here — U1 proposes, the owner confirms at ceremony):**

1. ``calibration_warning.*`` kind (§9.1). These are the ``CALIBRATION_*`` invariant-residual
   family; census/§II.7 names them as the ALARM exemplar. Under the pure rule ALARM is always
   critical, which would newly autopause on data-quality notices. This module defaults to
   classifying them **FLOW** (not ALARM), preserving their current ``informational`` tier — a
   flagged disposition, not a drift, pending an owner ruling on whether they are true
   invariant-residual ALARMs.
2. The 16-member CROSSING-at-``warning`` reclassification (§9.2 names 6 of them as illustrative;
   this reconciliation found 10 more forced by the same mechanical constraint). Every one carries
   a rationale in :data:`_DRIFT_RATIONALES`; see :data:`DRIFT_TABLE` for the full table.
3. ``CRISIS_PHASE_TRANSITION``'s rationale flags a genuine day-one granularity limitation: one
   ``EventType`` covers all 6 arcs of the ``CreditCyclePhase`` machine, including its one terminal
   arc (``STAGNATION``), which this generic event under-signals — a candidate for a future
   per-arc split, not resolved here.

**Home & layering (design §2 "Home & layering").** This module imports only
:class:`~babylon.models.enums.events.EventType` — nothing from ``engine``, ``domain``, ``tui``, or
``web`` — so it is importable by the projection-pure TUI and by the Django-layer web bridge alike.
**Amendment-S tripwire**: severity is a ``G∘P`` read-only projection. Nothing in
``babylon/engine`` or ``babylon/domain`` may read :func:`resolve_severity` — it never feeds back
into physics and never enters the tick hash (enforced day-one by
``tests/unit/models/test_event_severity.py``'s grep gate; U6 promotes this to a standing sentinel).

**E-2 (no numbers in events).** :data:`SeverityTier` is a closed string literal
(``"critical" | "warning" | "informational"``); nothing in this module is numeric, and no
:class:`~babylon.models.entities` event model gains a severity field — severity is computed
external to the event stream, never carried on it.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from babylon.models.enums.events import EventType


class EventKind(StrEnum):
    """The R-EC-1 generator-fact kind (``babylon-events.md`` §II.7).

    Every :class:`~babylon.models.enums.events.EventType` member is produced by exactly one of
    five registries; this enum names which one. Severity is derived from
    ``(kind, terminal_proximity)`` (or, for :attr:`FLOW`/:attr:`ACT`, a declared salience floor;
    or, for :attr:`PATTERN`, the resolved tier of a declared base crossing) — see
    :func:`derive_severity`.

    :cvar ALARM: an invariant residual (conservation/invariant registries) — always
        :data:`SeverityTier` ``"critical"`` (Constitution III.11: an alarm firing is never
        routine).
    :cvar CROSSING: chi changes at a sited atom (guard, calendar, arc, existential, or hazard
        species) — the Boundary Registry (A7). Binary severity:
        :attr:`TerminalProximity.TERMINAL_ADJACENT` -> critical,
        :attr:`TerminalProximity.INTRA_LEVEL` -> informational. There is no ``warning`` tier for a
        CROSSING under the pure rule.
    :cvar FLOW: a register/ledger row above its salience floor (``BoundaryFlowRegister`` + the
        Theta salience floors already resident in ``economy_basic``) — tier is the row's declared
        :attr:`EventKindRow.salience_floor`, never critical.
    :cvar ACT: a verb resolved (player/state action registries, ``_FASCIST_VERBS`` included) —
        tier is the row's declared :attr:`EventKindRow.salience_floor`, never critical.
    :cvar PATTERN: a distinguished cell entered/exited (curated conjunction list over A7 atoms,
        e.g. ``DUAL_POWER_ACTIVE``/``RED_SETTLER_TRAP_DETECTED``) — tier is the resolved tier of
        its declared :attr:`EventKindRow.base_crossing`.
    """

    ALARM = "alarm"
    CROSSING = "crossing"
    FLOW = "flow"
    ACT = "act"
    PATTERN = "pattern"


class TerminalProximity(StrEnum):
    """How close a CROSSING sits to a terminal/endgame-axis lock.

    Meaningful only for :attr:`EventKind.CROSSING` rows — every other kind declares :attr:`NA`
    (enforced by :meth:`EventKindRow._validate_shape`). The full feasibility-atlas derivation of
    proximity (A9) is staged post-1.0 (design §6); day-one proximity is hand-declared, grounded in
    each member's semantics.

    :cvar TERMINAL_ADJACENT: void-adjacency / regime->crisis entry / endgame-axis lock — derives
        to ``"critical"``.
    :cvar INTRA_LEVEL: a reversible crossing that stays within the current qualitative level —
        derives to ``"informational"``.
    :cvar NA: not applicable — every non-CROSSING kind declares this.
    """

    TERMINAL_ADJACENT = "terminal_adjacent"
    INTRA_LEVEL = "intra_level"
    NA = "na"


SeverityTier = Literal["critical", "warning", "informational"]
"""The three-bucket taxonomy (spec-061 FR-012), unchanged by this derivation — only how a tier is
assigned changes, not the vocabulary of tiers themselves."""


class EventKindRow(BaseModel):
    """One declared classification for a real :class:`~babylon.models.enums.events.EventType` member.

    Frozen and ``extra="forbid"`` so a malformed row is a loud import-time failure (Constitution
    III.11), never a quiet ``None`` at derivation time. Typing ``event_type`` as
    :class:`~babylon.models.enums.events.EventType` (rather than ``str``) makes "every taxonomy
    key is a real EventType value" a type-system guarantee, not a runtime check.

    :ivar event_type: the classified event.
    :ivar kind: the R-EC-1 generator-fact kind (§II.7).
    :ivar terminal_proximity: required (non-:attr:`~TerminalProximity.NA`) for
        :attr:`EventKind.CROSSING`; must be :attr:`~TerminalProximity.NA` for every other kind.
    :ivar salience_floor: required for :attr:`EventKind.FLOW`/:attr:`EventKind.ACT` (never
        ``"critical"``); forbidden for every other kind.
    :ivar base_crossing: required for :attr:`EventKind.PATTERN` — the
        :class:`~babylon.models.enums.events.EventType` of the (non-PATTERN) row whose resolved
        tier this pattern inherits; forbidden for every other kind.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_type: EventType
    kind: EventKind
    terminal_proximity: TerminalProximity
    salience_floor: SeverityTier | None = None
    base_crossing: EventType | None = None

    @model_validator(mode="after")
    def _validate_shape(self) -> EventKindRow:
        """Reject a row whose optional fields don't match its declared ``kind`` (III.11).

        Dispatches to one small per-kind validator so each stays independently readable (and
        under the complexity gate) rather than one large branch.

        :returns: ``self`` when valid.
        :raises ValueError: on a shape mismatch (wrong/missing ``terminal_proximity``, a
            ``salience_floor`` on a kind that forbids or requires one, a ``salience_floor`` of
            ``"critical"`` on FLOW/ACT, or a missing/extra ``base_crossing``).
        """
        if self.kind is EventKind.CROSSING:
            self._validate_crossing_shape()
        elif self.kind in (EventKind.FLOW, EventKind.ACT):
            self._validate_flow_or_act_shape()
        elif self.kind is EventKind.ALARM:
            self._validate_alarm_shape()
        else:  # EventKind.PATTERN
            self._validate_pattern_shape()
        return self

    def _validate_crossing_shape(self) -> None:
        """:raises ValueError: on a CROSSING row's shape mismatch."""
        if self.terminal_proximity is TerminalProximity.NA:
            raise ValueError(
                f"{self.event_type}: CROSSING rows must declare a real terminal_proximity"
            )
        if self.salience_floor is not None:
            raise ValueError(f"{self.event_type}: CROSSING rows never carry a salience_floor")
        if self.base_crossing is not None:
            raise ValueError(f"{self.event_type}: CROSSING rows never carry base_crossing")

    def _validate_flow_or_act_shape(self) -> None:
        """:raises ValueError: on a FLOW/ACT row's shape mismatch."""
        if self.terminal_proximity is not TerminalProximity.NA:
            raise ValueError(
                f"{self.event_type}: {self.kind} rows must declare terminal_proximity=NA"
            )
        if self.salience_floor is None:
            raise ValueError(f"{self.event_type}: {self.kind} rows require a salience_floor")
        if self.salience_floor == "critical":
            raise ValueError(
                f"{self.event_type}: {self.kind} salience_floor may never be 'critical'"
            )
        if self.base_crossing is not None:
            raise ValueError(f"{self.event_type}: {self.kind} rows never carry base_crossing")

    def _validate_alarm_shape(self) -> None:
        """:raises ValueError: on an ALARM row's shape mismatch."""
        if self.terminal_proximity is not TerminalProximity.NA:
            raise ValueError(f"{self.event_type}: ALARM rows must declare terminal_proximity=NA")
        if self.salience_floor is not None:
            raise ValueError(f"{self.event_type}: ALARM rows never carry a salience_floor")
        if self.base_crossing is not None:
            raise ValueError(f"{self.event_type}: ALARM rows never carry base_crossing")

    def _validate_pattern_shape(self) -> None:
        """:raises ValueError: on a PATTERN row's shape mismatch."""
        if self.terminal_proximity is not TerminalProximity.NA:
            raise ValueError(f"{self.event_type}: PATTERN rows must declare terminal_proximity=NA")
        if self.salience_floor is not None:
            raise ValueError(f"{self.event_type}: PATTERN rows never carry a salience_floor")
        if self.base_crossing is None:
            raise ValueError(f"{self.event_type}: PATTERN rows require a base_crossing")


def derive_severity(
    kind: EventKind,
    terminal_proximity: TerminalProximity,
    salience_floor: SeverityTier | None = None,
    base_crossing_tier: SeverityTier | None = None,
) -> SeverityTier:
    """The pure derivation rule (design §2) — kind x terminal_proximity -> tier.

    Deliberately takes plain values rather than an :class:`EventKindRow` so the mutation test can
    call it directly with a flipped input and observe a different output with no other machinery
    involved.

    :param kind: the event's :class:`EventKind`.
    :param terminal_proximity: the event's :class:`TerminalProximity` (meaningful for
        :attr:`EventKind.CROSSING` only).
    :param salience_floor: the declared floor for :attr:`EventKind.FLOW`/:attr:`EventKind.ACT`.
    :param base_crossing_tier: the already-resolved tier of a :attr:`EventKind.PATTERN` row's
        base crossing.
    :returns: the derived :data:`SeverityTier`.
    :raises ValueError: if a required argument for ``kind`` is missing, or ``terminal_proximity``
        is :attr:`~TerminalProximity.NA` for a :attr:`EventKind.CROSSING`, or ``salience_floor``
        is ``"critical"`` for FLOW/ACT.
    """
    if kind is EventKind.ALARM:
        return "critical"
    if kind is EventKind.CROSSING:
        if terminal_proximity is TerminalProximity.TERMINAL_ADJACENT:
            return "critical"
        if terminal_proximity is TerminalProximity.INTRA_LEVEL:
            return "informational"
        raise ValueError(
            "CROSSING requires terminal_proximity in {TERMINAL_ADJACENT, INTRA_LEVEL}, "
            f"got {terminal_proximity!r}"
        )
    if kind in (EventKind.FLOW, EventKind.ACT):
        if salience_floor is None:
            raise ValueError(f"{kind} requires a declared salience_floor")
        if salience_floor == "critical":
            raise ValueError(f"{kind} salience_floor may never be 'critical'")
        return salience_floor
    # kind is EventKind.PATTERN
    if base_crossing_tier is None:
        raise ValueError("PATTERN requires its base_crossing's resolved tier")
    return base_crossing_tier


# =============================================================================
# SEVERITY_TAXONOMY — the 47 currently hand-tiered EventType members, reclassified
# by (kind, terminal_proximity) per the R-EC-1 taxonomy. Grouped by kind; each
# CROSSING/PATTERN row whose derived tier differs from its legacy hand tier is
# commented with the direction of drift (full rationale: _DRIFT_RATIONALES /
# DRIFT_TABLE).
# =============================================================================

SEVERITY_TAXONOMY: Final[tuple[EventKindRow, ...]] = (
    # --- CROSSING: Terminal Crisis Dynamics family (guard/arc, terminal by name) ---
    EventKindRow(
        event_type=EventType.ECONOMIC_CRISIS,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    EventKindRow(
        event_type=EventType.CLASS_DECOMPOSITION,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    EventKindRow(
        event_type=EventType.SUPERWAGE_CRISIS,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    EventKindRow(
        event_type=EventType.PERIPHERAL_REVOLT,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    # --- CROSSING: Agency Layer / George Jackson bifurcation axis (all terminal-adjacent) ---
    EventKindRow(
        event_type=EventType.UPRISING,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    EventKindRow(
        event_type=EventType.POWER_VACUUM,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    EventKindRow(
        event_type=EventType.REVOLUTIONARY_OFFENSIVE,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    EventKindRow(
        event_type=EventType.FASCIST_REVANCHISM,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    EventKindRow(
        event_type=EventType.SPONTANEOUS_RIOT,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    # DRIFT (warning -> informational): reversible precursor, not itself an axis lock.
    EventKindRow(
        event_type=EventType.EXCESSIVE_FORCE,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.INTRA_LEVEL,
    ),
    # --- CROSSING: ecological / endgame ---
    EventKindRow(
        event_type=EventType.ECOLOGICAL_OVERSHOOT,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    EventKindRow(
        event_type=EventType.ENDGAME_REACHED,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    # --- CROSSING: fascist-capture escalation stack (drift/recruitment/fracture/coup) ---
    # DRIFT (warning -> informational): early-stage, reversible per-node pull.
    EventKindRow(
        event_type=EventType.FASCIST_DRIFT,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.INTRA_LEVEL,
    ),
    # DRIFT (warning -> critical): a node is captured by a fascist faction — completed hostile
    # transition, same axis as RED_BROWN_COUP below.
    EventKindRow(
        event_type=EventType.FASCIST_RECRUITMENT,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    # DRIFT (warning -> informational): a single member's defection, reversible/cumulative.
    EventKindRow(
        event_type=EventType.ORGANIZATIONAL_FRACTURE,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.INTRA_LEVEL,
    ),
    EventKindRow(
        event_type=EventType.RED_BROWN_COUP,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    # --- CROSSING: Doctrine Tree hazard-crossing family (ADR073) ---
    EventKindRow(
        event_type=EventType.DOCTRINE_TRAP_SPRUNG,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    # DRIFT (warning -> informational): the org's positive resolution out of the trap.
    EventKindRow(
        event_type=EventType.DOCTRINE_TRAP_ESCAPED,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.INTRA_LEVEL,
    ),
    # DRIFT (warning -> critical): the org remains trapped after a failed escape attempt.
    EventKindRow(
        event_type=EventType.DOCTRINE_PURGE_FAILED,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    # --- CROSSING: balkanization ---
    EventKindRow(
        event_type=EventType.SECESSION_DECLARED,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    # --- CROSSING: consciousness / dispossession threshold family ---
    # DRIFT (warning -> informational): reversible, frequently-recurring per-node crossing.
    EventKindRow(
        event_type=EventType.MASS_AWAKENING,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.INTRA_LEVEL,
    ),
    # DRIFT (warning -> informational): a recurring milestone marker on a continuous decline.
    EventKindRow(
        event_type=EventType.DISPOSSESSION_CASCADE,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.INTRA_LEVEL,
    ),
    # DRIFT (warning -> informational): per-entity starvation; aggregate mortality
    # (POPULATION_ATTRITION) already carries the system-level informational signal.
    EventKindRow(
        event_type=EventType.ENTITY_DEATH,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.INTRA_LEVEL,
    ),
    # --- CROSSING: market scissors ---
    # DRIFT (warning -> critical): a profit-rate-serviceability "snap" is a completed
    # crisis-axis crossing, on par with ECONOMIC_CRISIS/SUPERWAGE_CRISIS above.
    EventKindRow(
        event_type=EventType.MARKET_CORRECTION,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    # --- CROSSING: enum-machine arcs (CreditCyclePhase / EdgeMode / Aufhebung) ---
    # DRIFT (warning -> informational): one EventType covers all 6 CreditCyclePhase arcs,
    # most of which are routine reversible business-cycle churn; the machine's one terminal
    # arc (STAGNATION) is under-signaled by this generic event (a day-one granularity gap,
    # flagged for a possible future per-arc split, not resolved here).
    EventKindRow(
        event_type=EventType.CRISIS_PHASE_TRANSITION,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.INTRA_LEVEL,
    ),
    # DRIFT (warning -> critical): the George-Jackson bifurcation-axis crossing itself,
    # feeding POWER_VACUUM's branch resolution — an endgame-axis lock.
    EventKindRow(
        event_type=EventType.BIFURCATION_THRESHOLD,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    EventKindRow(
        event_type=EventType.EDGE_MODE_TRANSITION,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.INTRA_LEVEL,
    ),
    # DRIFT (warning -> critical): co-optation failure WITH bifurcation — structurally the
    # same bifurcation-axis event as POWER_VACUUM/REVOLUTIONARY_OFFENSIVE/FASCIST_REVANCHISM.
    EventKindRow(
        event_type=EventType.CO_OPTIVE_BREAKDOWN,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    EventKindRow(
        event_type=EventType.LATENT_CONTRADICTION_RELEASE,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.INTRA_LEVEL,
    ),
    EventKindRow(
        event_type=EventType.ASPECT_REVERSAL,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.INTRA_LEVEL,
    ),
    # DRIFT (warning -> critical): sublating the principal contradiction to a higher level
    # is a major structural/regime-level leap.
    EventKindRow(
        event_type=EventType.LEVEL_TRANSITION,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    # --- ACT: verb resolutions (state + reactionary-org registries) ---
    EventKindRow(
        event_type=EventType.STATE_REPRESSION,
        kind=EventKind.ACT,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="warning",
    ),
    EventKindRow(
        event_type=EventType.POGROM,
        kind=EventKind.ACT,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="warning",
    ),
    EventKindRow(
        event_type=EventType.LOCKOUT,
        kind=EventKind.ACT,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="warning",
    ),
    EventKindRow(
        event_type=EventType.VIGILANTISM,
        kind=EventKind.ACT,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="warning",
    ),
    # --- FLOW: register/ledger rows above their Theta salience floor ---
    EventKindRow(
        event_type=EventType.SURPLUS_EXTRACTION,
        kind=EventKind.FLOW,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="informational",
    ),
    EventKindRow(
        event_type=EventType.IMPERIAL_SUBSIDY,
        kind=EventKind.FLOW,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="informational",
    ),
    EventKindRow(
        event_type=EventType.CONSCIOUSNESS_TRANSMISSION,
        kind=EventKind.FLOW,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="informational",
    ),
    EventKindRow(
        event_type=EventType.DISPOSSESSION_EVENT,
        kind=EventKind.FLOW,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="informational",
    ),
    EventKindRow(
        event_type=EventType.VALUE_TRANSFER,
        kind=EventKind.FLOW,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="informational",
    ),
    EventKindRow(
        event_type=EventType.RESERVE_ARMY_PRESSURE,
        kind=EventKind.FLOW,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="informational",
    ),
    EventKindRow(
        event_type=EventType.POPULATION_ATTRITION,
        kind=EventKind.FLOW,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="informational",
    ),
    # Open owner question (§9.1): classified FLOW (not ALARM) to preserve the current
    # informational tier and avoid a surprise autopause — see module docstring.
    EventKindRow(
        event_type=EventType.CALIBRATION_AXIOM_VIOLATION,
        kind=EventKind.FLOW,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="informational",
    ),
    EventKindRow(
        event_type=EventType.CALIBRATION_QCEW_CARRY_FORWARD,
        kind=EventKind.FLOW,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="informational",
    ),
    EventKindRow(
        event_type=EventType.CALIBRATION_PHI_HOUR_OUTLIER,
        kind=EventKind.FLOW,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="informational",
    ),
    # --- PATTERN: distinguished cells, inheriting a declared base crossing's tier ---
    # DRIFT (warning -> critical): detecting this pattern means the RED_OGV terminal-endgame
    # track (settler-socialist trap) is live — inherits BIFURCATION_THRESHOLD's tier.
    EventKindRow(
        event_type=EventType.RED_SETTLER_TRAP_DETECTED,
        kind=EventKind.PATTERN,
        terminal_proximity=TerminalProximity.NA,
        base_crossing=EventType.BIFURCATION_THRESHOLD,
    ),
    # DRIFT (warning -> critical): a recognized-endgame-pattern change is directly
    # endgame-axis content by definition — inherits ENDGAME_REACHED's tier.
    EventKindRow(
        event_type=EventType.PATTERN_SHIFT,
        kind=EventKind.PATTERN,
        terminal_proximity=TerminalProximity.NA,
        base_crossing=EventType.ENDGAME_REACHED,
    ),
    # --- P25 electoral machine (ADR128): derived, never hand-tiered ---
    EventKindRow(
        event_type=EventType.ELECTION_HELD,
        kind=EventKind.ACT,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="informational",
    ),
    EventKindRow(
        event_type=EventType.GOVERNMENT_FORMED,
        kind=EventKind.ACT,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="warning",
    ),
    EventKindRow(
        event_type=EventType.POLICY_ENACTED,
        kind=EventKind.ACT,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="informational",
    ),
    EventKindRow(
        event_type=EventType.POLICY_STRUCK,
        kind=EventKind.ACT,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="warning",
    ),
    EventKindRow(
        event_type=EventType.POLICY_PREEMPTED,
        kind=EventKind.ACT,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="warning",
    ),
    # CAPITAL_STRIKE is a FLOW: the equalization operator's outflow is a register
    # row (BoundaryFlowRegister discipline), not a chi change at a sited atom.
    EventKindRow(
        event_type=EventType.CAPITAL_STRIKE,
        kind=EventKind.FLOW,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="warning",
    ),
    # Betrayal/disillusion crossings are reversible within the current qualitative
    # level (the window closes; patience can be re-earned) -> INTRA_LEVEL.
    EventKindRow(
        event_type=EventType.DELIVERY_GAP_CROSSED,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.INTRA_LEVEL,
    ),
    EventKindRow(
        event_type=EventType.DISILLUSION_WINDOW_OPEN,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.INTRA_LEVEL,
    ),
    EventKindRow(
        event_type=EventType.HOPE_SPIKE,
        kind=EventKind.FLOW,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="informational",
    ),
    EventKindRow(
        event_type=EventType.LEGITIMATION_REFRESH,
        kind=EventKind.FLOW,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="informational",
    ),
    # Bonapartist clock suspension is regime->crisis entry — TERMINAL_ADJACENT by
    # the TerminalProximity docstring's own definition; derives critical.
    EventKindRow(
        event_type=EventType.ELECTIONS_SUSPENDED,
        kind=EventKind.CROSSING,
        terminal_proximity=TerminalProximity.TERMINAL_ADJACENT,
    ),
    # POPULAR_FRONT_CALLED is a PATTERN over the fascist_consolidation axis —
    # same family as RED_SETTLER_TRAP_DETECTED, inheriting BIFURCATION_THRESHOLD.
    EventKindRow(
        event_type=EventType.POPULAR_FRONT_CALLED,
        kind=EventKind.PATTERN,
        terminal_proximity=TerminalProximity.NA,
        base_crossing=EventType.BIFURCATION_THRESHOLD,
    ),
    EventKindRow(
        event_type=EventType.LINE_STRUGGLE_SPLIT,
        kind=EventKind.ACT,
        terminal_proximity=TerminalProximity.NA,
        salience_floor="warning",
    ),
)


def _validate_taxonomy(taxonomy: tuple[EventKindRow, ...]) -> None:
    """Loudly reject a malformed taxonomy at import time (III.11).

    :param taxonomy: the declared rows to validate.
    :raises ValueError: on a duplicate ``event_type``, or a PATTERN row whose ``base_crossing``
        is not a declared non-PATTERN row in ``taxonomy``.
    """
    by_event: dict[EventType, EventKindRow] = {}
    for row in taxonomy:
        if row.event_type in by_event:
            raise ValueError(f"duplicate SEVERITY_TAXONOMY row for {row.event_type!r}")
        by_event[row.event_type] = row
    for row in taxonomy:
        if row.kind is not EventKind.PATTERN:
            continue
        if row.base_crossing is None:  # pragma: no cover - guarded by EventKindRow._validate_shape
            raise ValueError(f"{row.event_type}: PATTERN row missing base_crossing")
        base_row = by_event.get(row.base_crossing)
        if base_row is None:
            raise ValueError(
                f"{row.event_type}: base_crossing {row.base_crossing!r} is not a declared "
                "SEVERITY_TAXONOMY row"
            )
        if base_row.kind is EventKind.PATTERN:
            raise ValueError(
                f"{row.event_type}: base_crossing {row.base_crossing!r} is itself a PATTERN "
                "row — chained PATTERN bases are not supported day-one"
            )


_validate_taxonomy(SEVERITY_TAXONOMY)


def _build_severity_by_event(
    taxonomy: tuple[EventKindRow, ...],
) -> dict[EventType, SeverityTier]:
    """Generate the ``event_type -> resolved tier`` table.

    Two-pass: every non-PATTERN row resolves directly; PATTERN rows resolve in a second pass
    once their ``base_crossing``'s tier is known from the first pass.

    :param taxonomy: the declared rows to derive from (injectable so tests — including the
        mutation test — can supply a deliberately-altered fixture without touching the module
        global).
    :returns: the resolved :data:`SeverityTier` for every row in ``taxonomy``.
    :raises ValueError: if a PATTERN row's ``base_crossing`` did not resolve in the first pass
        (:func:`_validate_taxonomy` already catches this for the real module-level taxonomy;
        this re-check protects a fixture built without going through that validator).
    """
    resolved: dict[EventType, SeverityTier] = {}
    deferred: list[EventKindRow] = []
    for row in taxonomy:
        if row.kind is EventKind.PATTERN:
            deferred.append(row)
            continue
        resolved[row.event_type] = derive_severity(
            row.kind, row.terminal_proximity, row.salience_floor
        )
    for row in deferred:
        if row.base_crossing is None:
            raise ValueError(f"{row.event_type}: PATTERN row missing base_crossing")
        base_tier = resolved.get(row.base_crossing)
        if base_tier is None:
            raise ValueError(
                f"{row.event_type}: base_crossing {row.base_crossing!r} did not resolve in "
                "the first pass"
            )
        resolved[row.event_type] = derive_severity(
            row.kind, row.terminal_proximity, row.salience_floor, base_tier
        )
    return resolved


SEVERITY_BY_EVENT: Final[dict[EventType, SeverityTier]] = _build_severity_by_event(
    SEVERITY_TAXONOMY
)
"""The generated ``EventType -> SeverityTier`` table — U2's single source of truth for both the
web bridge and the Archive Chronicle. Covers exactly the members :data:`SEVERITY_TAXONOMY` classifies (the day-one 47
plus :data:`_POST_DAY_ONE_ADDITIONS`); every other :class:`~babylon.models.enums.events.EventType` resolves through
:func:`resolve_severity`'s loud unclassified floor."""


class EventSeverity(BaseModel):
    """One event type's resolved severity tier, plus the loud-unclassified flag.

    :ivar tier: the resolved :data:`SeverityTier`.
    :ivar unclassified: ``True`` when ``tier`` came from the loud ``unclassified -> warning``
        floor (no :class:`EventKindRow` declared for this member) rather than a real
        classification.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    tier: SeverityTier
    unclassified: bool = False


def resolve_severity(event_type: EventType) -> EventSeverity:
    """Resolve ``event_type``'s severity tier.

    Constitution III.11 (Loud Failure): an ``event_type`` with no declared :class:`EventKindRow`
    (any of the 37 members outside the day-one 47, or a future
    :class:`~babylon.models.enums.events.EventType` addition) resolves to ``"warning"`` — never a
    quiet ``"informational"`` degrade — with :attr:`EventSeverity.unclassified` set so callers can
    visibly mark it.

    :param event_type: the event type to resolve.
    :returns: the resolved :class:`EventSeverity`.
    """
    tier = SEVERITY_BY_EVENT.get(event_type)
    if tier is None:
        return EventSeverity(tier="warning", unclassified=True)
    return EventSeverity(tier=tier, unclassified=False)


# =============================================================================
# Reconciliation: the legacy 47-member hand tier vs. the derived table above,
# and the declared rationale for every member whose tier moved.
# =============================================================================

_LEGACY_HAND_TIERS: Final[dict[EventType, SeverityTier]] = {
    # Critical (14) — ported verbatim from web/game/engine_bridge.py::_EVENT_SEVERITY.
    EventType.ECONOMIC_CRISIS: "critical",
    EventType.CLASS_DECOMPOSITION: "critical",
    EventType.SUPERWAGE_CRISIS: "critical",
    EventType.UPRISING: "critical",
    EventType.ENDGAME_REACHED: "critical",
    EventType.POWER_VACUUM: "critical",
    EventType.REVOLUTIONARY_OFFENSIVE: "critical",
    EventType.FASCIST_REVANCHISM: "critical",
    EventType.SPONTANEOUS_RIOT: "critical",
    EventType.PERIPHERAL_REVOLT: "critical",
    EventType.ECOLOGICAL_OVERSHOOT: "critical",
    EventType.RED_BROWN_COUP: "critical",
    EventType.DOCTRINE_TRAP_SPRUNG: "critical",
    EventType.SECESSION_DECLARED: "critical",
    # Warning (20).
    EventType.STATE_REPRESSION: "warning",
    EventType.RED_SETTLER_TRAP_DETECTED: "warning",
    EventType.EXCESSIVE_FORCE: "warning",
    EventType.MASS_AWAKENING: "warning",
    EventType.FASCIST_DRIFT: "warning",
    EventType.DISPOSSESSION_CASCADE: "warning",
    EventType.FASCIST_RECRUITMENT: "warning",
    EventType.ORGANIZATIONAL_FRACTURE: "warning",
    EventType.DOCTRINE_TRAP_ESCAPED: "warning",
    EventType.DOCTRINE_PURGE_FAILED: "warning",
    EventType.POGROM: "warning",
    EventType.LOCKOUT: "warning",
    EventType.VIGILANTISM: "warning",
    EventType.MARKET_CORRECTION: "warning",
    EventType.ENTITY_DEATH: "warning",
    EventType.CRISIS_PHASE_TRANSITION: "warning",
    EventType.BIFURCATION_THRESHOLD: "warning",
    EventType.CO_OPTIVE_BREAKDOWN: "warning",
    EventType.LEVEL_TRANSITION: "warning",
    EventType.PATTERN_SHIFT: "warning",
    # Informational (13).
    EventType.SURPLUS_EXTRACTION: "informational",
    EventType.IMPERIAL_SUBSIDY: "informational",
    EventType.CONSCIOUSNESS_TRANSMISSION: "informational",
    EventType.DISPOSSESSION_EVENT: "informational",
    EventType.VALUE_TRANSFER: "informational",
    EventType.RESERVE_ARMY_PRESSURE: "informational",
    EventType.POPULATION_ATTRITION: "informational",
    EventType.EDGE_MODE_TRANSITION: "informational",
    EventType.LATENT_CONTRADICTION_RELEASE: "informational",
    EventType.ASPECT_REVERSAL: "informational",
    EventType.CALIBRATION_AXIOM_VIOLATION: "informational",
    EventType.CALIBRATION_QCEW_CARRY_FORWARD: "informational",
    EventType.CALIBRATION_PHI_HOUR_OUTLIER: "informational",
}
"""The 47-member hand-tiered snapshot this module supersedes — frozen here ONLY as reconciliation
input for :data:`DRIFT_TABLE`, never a runtime dependency. U2 deletes the live copies in
``web/game/engine_bridge.py`` and ``babylon.tui.chronicle_salience``."""

_POST_DAY_ONE_ADDITIONS: Final[frozenset[EventType]] = frozenset(
    {
        # P25 electoral machine (ADR128): classified at birth, no legacy hand tier exists.
        EventType.ELECTION_HELD,
        EventType.GOVERNMENT_FORMED,
        EventType.POLICY_ENACTED,
        EventType.POLICY_STRUCK,
        EventType.POLICY_PREEMPTED,
        EventType.CAPITAL_STRIKE,
        EventType.DELIVERY_GAP_CROSSED,
        EventType.HOPE_SPIKE,
        EventType.DISILLUSION_WINDOW_OPEN,
        EventType.LEGITIMATION_REFRESH,
        EventType.ELECTIONS_SUSPENDED,
        EventType.POPULAR_FRONT_CALLED,
        EventType.LINE_STRUGGLE_SPLIT,
    }
)
"""Taxonomy members added after the day-one 47 — each entry cites its ADR. An addition
appears here AND in :data:`SEVERITY_TAXONOMY` (classified, derived) but never in
:data:`_LEGACY_HAND_TIERS` (there is no hand tier to reconcile against)."""

if set(_LEGACY_HAND_TIERS) | _POST_DAY_ONE_ADDITIONS != {
    row.event_type for row in SEVERITY_TAXONOMY
}:
    raise ValueError(
        "SEVERITY_TAXONOMY must classify exactly the legacy 47 plus the declared "
        "_POST_DAY_ONE_ADDITIONS — grow the taxonomy only alongside its additions "
        "ledger (each entry citing its ADR), never silently"
    )
if set(_LEGACY_HAND_TIERS) & _POST_DAY_ONE_ADDITIONS:
    raise ValueError(
        "_POST_DAY_ONE_ADDITIONS may not overlap the legacy 47 — a legacy member has "
        "a hand tier to reconcile and belongs in DRIFT_TABLE instead"
    )


_DRIFT_RATIONALES: Final[dict[EventType, str]] = {
    EventType.RED_SETTLER_TRAP_DETECTED: (
        "PATTERN kind (design brief §II.7 exemplar, alongside DUAL_POWER_ACTIVE) inheriting "
        "BIFURCATION_THRESHOLD's tier: detecting this pattern means the RED_OGV terminal-endgame "
        "track (settler-socialist trap) is live — correctly promotes to critical/autopause "
        "rather than the hand-tier's routine warning."
    ),
    EventType.EXCESSIVE_FORCE: (
        "CROSSING (forcing-hazard atom firing, babylon-events.md §II.8b) classified "
        "INTRA_LEVEL: the spark is a reversible precursor — it does not itself lock any "
        "terminal axis (UPRISING, already critical, is the completed rupture-adjacent crossing "
        "once agitation gates it); demotes from warning to informational."
    ),
    EventType.MASS_AWAKENING: (
        "CROSSING (guard: consciousness > threshold) classified INTRA_LEVEL: a reversible, "
        "frequently-recurring per-node consciousness threshold-cross, not itself an "
        "endgame-axis lock; demotes from warning to informational."
    ),
    EventType.FASCIST_DRIFT: (
        "CROSSING (guard: fascist pull > threshold) classified INTRA_LEVEL: an early-stage, "
        "reversible per-node drift — FASCIST_RECRUITMENT is the completed capture this "
        "precedes; demotes from warning to informational."
    ),
    EventType.DISPOSSESSION_CASCADE: (
        "CROSSING (guard: LA share decline milestone) classified INTRA_LEVEL: a recurring "
        "milestone marker on a continuous decline, not itself a terminal lock; demotes from "
        "warning to informational."
    ),
    EventType.FASCIST_RECRUITMENT: (
        "CROSSING (guard: fascist alignment > recruitment threshold) classified "
        "TERMINAL_ADJACENT: a node is captured by a fascist faction — a completed hostile "
        "transition on the same axis as RED_BROWN_COUP (already critical); promotes from "
        "warning to critical."
    ),
    EventType.ORGANIZATIONAL_FRACTURE: (
        "CROSSING (a single member's defection) classified INTRA_LEVEL: an individual, "
        "reversible defection that only completes the hostile capture (RED_BROWN_COUP, "
        "already critical) once a majority accumulates; demotes from warning to informational."
    ),
    EventType.DOCTRINE_TRAP_ESCAPED: (
        "CROSSING (hazard-crossing family, congress purge succeeded) classified INTRA_LEVEL: "
        "the org's positive resolution out of DOCTRINE_TRAP_SPRUNG's critical condition; "
        "demotes from warning to informational."
    ),
    EventType.DOCTRINE_PURGE_FAILED: (
        "CROSSING (hazard-crossing family, congress purge attempt failed) classified "
        "TERMINAL_ADJACENT: the org remains in DOCTRINE_TRAP_SPRUNG's critical trapped "
        "condition after a failed escape attempt; promotes from warning to critical so the "
        "persisting crisis is not under-signaled."
    ),
    EventType.MARKET_CORRECTION: (
        "CROSSING (census: 'crossing, snap') classified TERMINAL_ADJACENT: a fictitious/real "
        "divergence exceeding profit-rate serviceability is a completed crisis-axis 'snap', "
        "materially on par with ECONOMIC_CRISIS/SUPERWAGE_CRISIS (both already critical); "
        "promotes from warning to critical."
    ),
    EventType.ENTITY_DEATH: (
        "CROSSING (guard: wealth < consumption_needs) classified INTRA_LEVEL: an individual, "
        "per-entity starvation event — the aggregate mortality signal (POPULATION_ATTRITION, "
        "already informational) carries the system-level severity; demotes from warning to "
        "informational for consistency with its aggregate sibling."
    ),
    EventType.CRISIS_PHASE_TRANSITION: (
        "CROSSING (arc, CreditCyclePhase machine, 6 arcs) classified INTRA_LEVEL: the single "
        "EventType covers every arc of the machine, most of which are routine reversible "
        "business-cycle churn; the machine's one terminal arc (STAGNATION) is under-signaled "
        "by this generic event — a genuine day-one granularity limitation, flagged for a "
        "possible future per-arc split rather than resolved here; demotes from warning to "
        "informational."
    ),
    EventType.BIFURCATION_THRESHOLD: (
        "CROSSING (guard: |score| crosses threshold) classified TERMINAL_ADJACENT: this IS "
        "the George-Jackson bifurcation-axis crossing feeding POWER_VACUUM's branch "
        "resolution — an endgame-axis lock; promotes from warning to critical."
    ),
    EventType.CO_OPTIVE_BREAKDOWN: (
        "CROSSING (arc, EdgeTransition) classified TERMINAL_ADJACENT: a co-optation failure "
        "WITH bifurcation is structurally the same bifurcation-axis event as "
        "POWER_VACUUM/REVOLUTIONARY_OFFENSIVE/FASCIST_REVANCHISM (all already critical); "
        "promotes from warning to critical."
    ),
    EventType.LEVEL_TRANSITION: (
        "CROSSING (arc, Lawverian Aufhebung) classified TERMINAL_ADJACENT: sublating the "
        "principal contradiction to a higher level is a major structural/regime-level leap; "
        "promotes from warning to critical."
    ),
    EventType.PATTERN_SHIFT: (
        "PATTERN kind inheriting ENDGAME_REACHED's tier: a recognized-endgame-pattern change "
        "is directly endgame-axis content by definition; promotes from warning to critical."
    ),
}
"""Declared rationale for every member whose derived tier differs from its legacy hand tier —
required, never inferred: :func:`_build_drift_table` raises loudly at import if a drifted member
has no entry here."""


class DriftRow(BaseModel):
    """One old-tier -> new-tier reclassification surfaced by this module's derivation — the
    owner-visible feature disclosure required before the T1.1 severity ceremony (design §7).

    :ivar event_type: the reclassified event.
    :ivar old_tier: the legacy hand tier (:data:`_LEGACY_HAND_TIERS`).
    :ivar new_tier: the derived tier (:data:`SEVERITY_BY_EVENT`).
    :ivar rationale: the declared reason for the reclassification (:data:`_DRIFT_RATIONALES`).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_type: EventType
    old_tier: SeverityTier
    new_tier: SeverityTier
    rationale: str


def _build_drift_table(
    legacy: dict[EventType, SeverityTier],
    derived: dict[EventType, SeverityTier],
    rationales: dict[EventType, str],
) -> tuple[DriftRow, ...]:
    """Generate the old-tier -> new-tier drift table (design §2, §7).

    :param legacy: the hand-tiered 47-member snapshot this module supersedes.
    :param derived: :data:`SEVERITY_BY_EVENT` (or a mutation-test fixture built by
        :func:`_build_severity_by_event`).
    :param rationales: the declared rationale per drifted member.
    :returns: one :class:`DriftRow` per member whose tier changed, in ``legacy``
        declaration order.
    :raises ValueError: if any drifted member lacks a declared rationale, or if ``derived``
        does not cover every ``legacy`` member.
    """
    rows: list[DriftRow] = []
    for event_type, old_tier in legacy.items():
        new_tier = derived.get(event_type)
        if new_tier is None:
            raise ValueError(f"{event_type}: legacy member missing from the derived table")
        if new_tier == old_tier:
            continue
        rationale = rationales.get(event_type)
        if rationale is None:
            raise ValueError(
                f"{event_type}: drifted {old_tier} -> {new_tier} with no declared rationale "
                "in _DRIFT_RATIONALES"
            )
        rows.append(
            DriftRow(
                event_type=event_type, old_tier=old_tier, new_tier=new_tier, rationale=rationale
            )
        )
    return tuple(rows)


DRIFT_TABLE: Final[tuple[DriftRow, ...]] = _build_drift_table(
    _LEGACY_HAND_TIERS, SEVERITY_BY_EVENT, _DRIFT_RATIONALES
)
"""The generated, owner-visible old-tier -> new-tier drift table (design §7's severity/vault-
surface ceremony note draws on this directly). 16 of the 47 members drift; every one carries a
declared rationale in :data:`_DRIFT_RATIONALES`."""


__all__ = [
    "EventKind",
    "TerminalProximity",
    "SeverityTier",
    "EventKindRow",
    "SEVERITY_TAXONOMY",
    "derive_severity",
    "SEVERITY_BY_EVENT",
    "EventSeverity",
    "resolve_severity",
    "DriftRow",
    "DRIFT_TABLE",
]
