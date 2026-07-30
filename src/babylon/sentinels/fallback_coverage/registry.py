"""Disposition ledger for the fallback-coverage sentinel (ADR176 ruling 25).

The Game Design Standard's two verdict-surface checks, promoted from the seam
sentinel's advisory tier to a gate (the Director's ruling: *"promote the two
verdict-surface checks to GATING after the Phase-0 disposition pass"* —
ADR176 ruling 25, director-gate #380). The disposition pass is this ledger:
every ``EventType`` member that today lacks coverage on a surface carries a
row naming HOW that absence is governed, with a citation — an unruled absence
is indistinguishable from an oversight (Standard §9 W.2).

Two surfaces, one law each:

- **bus boundary** — a member absent from ``engine.event_builders.
  EVENT_BUILDERS`` drops to ``None`` at the bus->pydantic boundary and never
  reaches the player. The 2026-07-29 endings audit found every endgame event
  in this class: the verdict surface was dropped at the source.
- **chronicle** — a wire-reaching member absent from ``game.chronicle_adapter.
  _SUMMARY_BUILDERS`` renders the loud generic field-list line instead of
  real content. Empty since the P25 bespoke widening; kept so a future
  exemption must arrive as a cited row.

Governance mirrors the family's ratchet discipline (``reachability/
registry.py``): coverage arriving for a ledgered member reds the gate until
the row is removed — the ledger can only shrink toward full coverage.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

#: The bus->pydantic builder registry (surface 1) — dict literal + module.
EVENT_BUILDERS_PATH = REPO_ROOT / "src" / "babylon" / "engine" / "event_builders.py"
EVENT_BUILDERS_DICT = "_BUILDERS"

#: The bespoke chronicle-summary registry (surface 2) — dict literal + module.
CHRONICLE_PATH = REPO_ROOT / "src" / "babylon" / "game" / "chronicle_adapter.py"
CHRONICLE_DICT = "_SUMMARY_BUILDERS"


class Governance(enum.Enum):
    """How an uncovered ``EventType`` member's absence is governed."""

    #: Coverage is owed by a named, cited train — the row retires when the
    #: train lands its builder/publisher (the ratchet reds it automatically).
    CHARTER = "charter"
    #: No production publisher or consumer exists (evidence cited); retained
    #: as vocabulary pending a WIRE / CHARTER / RETIRE-WITH-RECORD disposition
    #: (Standard §9 W.2). Retiring enum values is a save-compat motion that
    #: belongs to a declared ceremony, never a sentinel side effect.
    DORMANT = "dormant"


@dataclass(frozen=True)
class EventCoverageRow:
    """One ledgered ``EventType`` member on one surface.

    :param member: The ``EventType`` member name (``.name``, not ``.value``).
    :param governance: The row's :class:`Governance` mode.
    :param citation: Charter/evidence citation — required on every row.
    """

    member: str
    governance: Governance
    citation: str


_ENDINGS_TRAIN = (
    "the endings train: ADR176 rulings 1-3 (director-gate #376) — the "
    "EndgameDetector detects but never publishes; typed payload exists "
    "with no production publisher"
)

_DORMANT_SCAN = (
    "2026-07-29 scan: no production publisher, builder, or typed payload "
    "class outside the enum — dead vocabulary retained pending a declared "
    "WIRE/CHARTER/RETIRE disposition (Standard §9 W.2; the BSL event-"
    "vocabulary re-mint, P27 Phase 2, is the natural retirement ceremony)"
)

#: Surface 1 — members with no ``EVENT_BUILDERS`` entry (drop at the bus
#: boundary). Truth as of 2026-07-29: 20 of 100, dispositioned 5 CHARTER /
#: 15 DORMANT.
BUS_BOUNDARY_LEDGER: tuple[EventCoverageRow, ...] = (
    EventCoverageRow(
        member="ENDGAME_REACHED",
        governance=Governance.CHARTER,
        citation=(
            f"{_ENDINGS_TRAIN} (EndgameEvent, models/events/_legacy.py; "
            "game/session.py's docstring documents the missing bus event)"
        ),
    ),
    EventCoverageRow(
        member="RED_OGV_ENDGAME",
        governance=Governance.CHARTER,
        citation=(
            f"{_ENDINGS_TRAIN} (RED_OGV payload, models/events/"
            "balkanization_payloads.py; ruling 2 names the George Jackson "
            "routing defect this event must carry)"
        ),
    ),
    EventCoverageRow(
        member="FRAGMENTED_COLLAPSE_ENDGAME",
        governance=Governance.CHARTER,
        citation=(
            f"{_ENDINGS_TRAIN} (fragmented-collapse payload, models/events/"
            "balkanization_payloads.py)"
        ),
    ),
    EventCoverageRow(
        member="PATTERN_SHIFT",
        governance=Governance.CHARTER,
        citation=(
            f"{_ENDINGS_TRAIN} (PatternShiftEvent, models/events/_legacy.py; "
            "Standard §2: patterns are the verdict — a silent pattern shift "
            "is a verdict the player never hears)"
        ),
    ),
    EventCoverageRow(
        member="INFRASTRUCTURE_CHANGE",
        governance=Governance.CHARTER,
        citation=(
            "the BUILD lane: ADR176 rulings 15/37 (director-gate #378) — "
            "engine/actions/build.py declares events_generated=["
            "INFRASTRUCTURE_CHANGE] as its first production emission"
        ),
    ),
    EventCoverageRow(
        member="BIFURCATION_TENDENCY_CHANGE",
        governance=Governance.DORMANT,
        citation=(
            "2026-07-29 scan: typed BifurcationTendencyEvent exists "
            "(models/events/_legacy.py EVENT_CLASS_MAP) with no production "
            "publisher — consciousness-feedback lane (Doctrine Tree Unit 6) "
            "is its natural WIRE home when chartered"
        ),
    ),
    EventCoverageRow(
        member="CALIBRATION_DISAGREEMENT",
        governance=Governance.DORMANT,
        citation=_DORMANT_SCAN,
    ),
    EventCoverageRow(
        member="CONSCIOUSNESS_SHIFT",
        governance=Governance.DORMANT,
        citation=_DORMANT_SCAN,
    ),
    EventCoverageRow(
        member="DUAL_CIRCUIT_INTERFERENCE",
        governance=Governance.DORMANT,
        citation=_DORMANT_SCAN,
    ),
    EventCoverageRow(
        member="EXPLOITATION_MODE_SHIFT",
        governance=Governance.DORMANT,
        citation=_DORMANT_SCAN,
    ),
    EventCoverageRow(
        member="FACTION_SHIFT",
        governance=Governance.DORMANT,
        citation=_DORMANT_SCAN,
    ),
    EventCoverageRow(
        member="FASCIST_CONVERGENCE",
        governance=Governance.DORMANT,
        citation=_DORMANT_SCAN,
    ),
    EventCoverageRow(
        member="INITIATIVE_CONTESTED",
        governance=Governance.DORMANT,
        citation=_DORMANT_SCAN,
    ),
    EventCoverageRow(
        member="INSTITUTION_REPRODUCTION",
        governance=Governance.DORMANT,
        citation=(
            "2026-07-29 scan: referenced only by models/entities/"
            "institution.py's FR-019 docstring — no publisher, no builder; "
            "dead vocabulary pending a declared disposition (Standard §9 W.2)"
        ),
    ),
    EventCoverageRow(
        member="LEGAL_FRAMEWORK_ENACTED",
        governance=Governance.DORMANT,
        citation=_DORMANT_SCAN,
    ),
    EventCoverageRow(
        member="LEGAL_FRAMEWORK_REVOKED",
        governance=Governance.DORMANT,
        citation=_DORMANT_SCAN,
    ),
    EventCoverageRow(
        member="POPULATION_DEATH",
        governance=Governance.DORMANT,
        citation=_DORMANT_SCAN,
    ),
    EventCoverageRow(
        member="SOLIDARITY_AWAKENING",
        governance=Governance.DORMANT,
        citation=_DORMANT_SCAN,
    ),
    EventCoverageRow(
        member="STATE_ACTION_EXECUTED",
        governance=Governance.DORMANT,
        citation=_DORMANT_SCAN,
    ),
    EventCoverageRow(
        member="THREAD_ESCALATION",
        governance=Governance.DORMANT,
        citation=_DORMANT_SCAN,
    ),
)

#: Surface 2 — wire-reaching members with no bespoke chronicle summary.
#: EMPTY since the P25 bespoke widening (2026-07-29): every event that can
#: reach the Chronicle renders real content. A future exemption must be a
#: cited row here — a deliberate act, never drift.
CHRONICLE_LEDGER: tuple[EventCoverageRow, ...] = ()
