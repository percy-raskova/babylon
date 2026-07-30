"""Reachability sentinel — the declared-but-unemitted gate (§9 W.3.2).

Closes the sentinel family's stated blind spot: ``inert`` catches
*nobody-calls-this*, ``dangling`` catches *this-call-names-a-nonexistent-
target*; **neither catches *this-member-is-declared-and-nobody-emits-it***.
Instance #1 audits the EndgameDetector's gate operands — under the sandbox
ruling (Game Design Standard §1) a writer-less gate operand silently makes an
ending unreachable, which the 2026-07-29 endings audit found had already
happened to four of the five terminal outcomes.

Registry: :mod:`babylon.sentinels.reachability.registry` · checks:
:mod:`babylon.sentinels.reachability.checks` · run:
``uv run python tools/sentinel_check.py reachability --check`` /
``mise run check:reachability``.
"""

from babylon.sentinels.reachability.checks import main
from babylon.sentinels.reachability.registry import (
    GATE_OPERAND_ROWS,
    GateOperandRow,
    Governance,
)

__all__ = ["GATE_OPERAND_ROWS", "GateOperandRow", "Governance", "main"]
