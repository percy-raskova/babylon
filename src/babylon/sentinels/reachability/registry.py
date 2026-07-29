"""Declared-invariant registry for the reachability sentinel (§9 W.3.2).

The Game Design Standard's Wiring Completeness Doctrine (``docs/superpowers/
specs/2026-07-29-game-design-standard-design.md`` §9) names the blind spot this
sentinel closes: *a member can be declared, tested, documented, and never
emitted, and no gate notices*. Rule W.3.2 is its cheapest instance — **every
gate operand the EndgameDetector reads must have a runtime production writer**,
or a ledgered disposition (§9 W.2) citing the charter that will wire it.

Under the sandbox ruling (Standard §1: horizon is the ending, patterns are the
verdict) a writer-less gate operand silently pins an ending's gate at its
default forever — the 2026-07-29 endings audit found four of five terminal
outcomes provably unreachable through exactly this class
(``reports/design-inputs-dossier-2026-07-29.md`` §3).

Governance mirrors the family's exemption discipline (see
``vocabulary/registry.py``): every row is either **DETECTED** (a writer must be
statically found in the runtime scan roots — and the check reds if it ever
disappears) or a **ledgered disposition** (CHARTER / BLOCKED / RULED_ABSENT,
citation required — and the check reds if a writer *appears*, forcing the row's
promotion; the ratchet only tightens).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

#: The gate-reading module this sentinel audits (rule W.3.2's read side).
DETECTOR_PATH = REPO_ROOT / "src" / "babylon" / "engine" / "observers" / "endgame_detector.py"

#: Runtime tick-path roots scanned for writers. ``engine/scenarios`` is
#: excluded below: scenario fixtures are *seed* writers, and a gate that only
#: ever sees its seeded value is exactly the flat-axis defect this sentinel
#: exists to expose (all five recognizer axes flat under null play,
#: spec-116 closeout).
SCAN_ROOTS: tuple[Path, ...] = (
    REPO_ROOT / "src" / "babylon" / "engine",
    REPO_ROOT / "src" / "babylon" / "domain",
)

#: Subtrees excluded from the writer scan (seed fixtures, not runtime writes).
SCAN_EXCLUDES: tuple[Path, ...] = (REPO_ROOT / "src" / "babylon" / "engine" / "scenarios",)

#: Node/edge type keys are the vocabulary sentinel's estate, not operands.
TYPE_KEYS: frozenset[str] = frozenset({"_node_type", "_edge_type"})


class Governance(enum.Enum):
    """How a gate operand row is allowed to satisfy the writer obligation."""

    #: A runtime writer must be statically detectable in ``SCAN_ROOTS``.
    DETECTED = "detected"
    #: The writer is helper-mediated (invisible to the direct-write scan);
    #: ``writer_path`` cites it and the check verifies the cite still holds.
    CITED_WRITER = "cited-writer"
    #: Writer-less by known defect; a charter (cited) owns wiring it.
    CHARTER = "charter"
    #: Writer-less; wiring is blocked on a named dependency (cited).
    BLOCKED = "blocked"
    #: Writer-less **by design**; the absence is Director-ruled (cited).
    RULED_ABSENT = "ruled-absent"


@dataclass(frozen=True)
class GateOperandRow:
    """One audited gate operand: who reads it, and how its writer is governed.

    :param operand: The graph-payload attribute name the gate reads.
    :param reader: Human citation of the reading gate (file + which gate).
    :param governance: The row's :class:`Governance` mode.
    :param citation: Charter/ruling citation — required for every ledgered
        (``CHARTER``/``BLOCKED``/``RULED_ABSENT``) row, empty otherwise.
    :param writer_path: Repo-relative path of the helper-mediated writer —
        required for ``CITED_WRITER`` rows (machine-verified), empty otherwise.
    """

    operand: str
    reader: str
    governance: Governance
    citation: str
    writer_path: str = ""


_POLITICAL_WRITERS_CHARTER = (
    "Game Design Standard §10 Phase 3 (the six political writers); "
    "docs/superpowers/plans/2026-07-18-null-play-political-coupling.md Tasks 4-9; "
    "ledger: reports/wiring-completeness-2026-07-29.md"
)

#: The audited rows. Truth as of 2026-07-29: four of the six substantive
#: operands have no runtime writer — each carries the charter that wires it.
GATE_OPERAND_ROWS: tuple[GateOperandRow, ...] = (
    GateOperandRow(
        operand="colonial_stance",
        reader="endgame_detector.py (RED_OGV / REVOLUTIONARY_VICTORY stance gates)",
        governance=Governance.CHARTER,
        citation=_POLITICAL_WRITERS_CHARTER,
    ),
    GateOperandRow(
        operand="state_violence_index",
        reader="endgame_detector.py (FASCIST_CONSOLIDATION violence gate)",
        governance=Governance.CHARTER,
        citation=_POLITICAL_WRITERS_CHARTER,
    ),
    GateOperandRow(
        operand="state_violence_index_max",
        reader="endgame_detector.py (FASCIST_CONSOLIDATION violence gate ceiling)",
        governance=Governance.CHARTER,
        citation=_POLITICAL_WRITERS_CHARTER,
    ),
    GateOperandRow(
        operand="ruling_faction_id",
        reader="endgame_detector.py (sovereign stance lookup)",
        governance=Governance.DETECTED,
        citation="",
    ),
    GateOperandRow(
        operand="sovereignty_type",
        reader="endgame_detector.py (FRAGMENTED_COLLAPSE crisis-sovereignty gate)",
        governance=Governance.DETECTED,
        citation="",
    ),
    GateOperandRow(
        operand="extraction_policy",
        reader="endgame_detector.py (RED_OGV extraction gate)",
        governance=Governance.DETECTED,
        citation="",
    ),
    GateOperandRow(
        operand="habitability",
        reader="endgame_detector.py (RED_OGV / ECOLOGICAL habitability gates)",
        governance=Governance.CITED_WRITER,
        citation="MetabolismSystem._write_clamped stamps it each tick",
        writer_path="src/babylon/engine/systems/metabolism.py",
    ),
)
