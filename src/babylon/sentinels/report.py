"""The agent-legible finding format shared by the U7 sentinel family.

A sentinel finding is read by a coding agent, not a human dashboard. To be
actionable it must answer five questions in one line, always in the same order:

1. **which error class** — the named failure taxonomy (``correct-but-inert``,
   ``computed-but-never-consumed``, ``gate-blindness``,
   ``intensive-aggregation``, ``undeclared-coupling``);
2. **which symbol** — the offending name, not a vague area;
3. **where** — repo-relative ``file:line`` the agent can open directly;
4. **what to do** — a concrete remedy, never "investigate".

The rendered shape is::

    [<error-class>] <symbol> @ <file>:<line> — <problem> | REMEDY: <remedy>

:mod:`babylon.sentinels.base`'s runner prefixes this with its sensor tag, so a
full advisory line reads ``LIVENESS ADVISORY [label]: [class] symbol @ ...``.

Layer 0.5 (stdlib only): importable by every sentinel package.
"""

from __future__ import annotations


def finding(
    *,
    error_class: str,
    symbol: str,
    file: str,
    line: int,
    problem: str,
    remedy: str,
) -> str:
    """Render one agent-legible sentinel finding.

    :param error_class: The named failure taxonomy this finding belongs to.
    :param symbol: The offending symbol (class, function, constant, graph key).
    :param file: Repo-relative path to the offending source file.
    :param line: 1-indexed line of the offending symbol; ``0`` means the whole
        file (rendered without a line suffix).
    :param problem: One clause stating what is wrong, in the present tense.
    :param remedy: One clause stating the concrete fix — never "investigate".
    :returns: The single-line finding string.
    :raises ValueError: If ``error_class``, ``symbol``, ``file``, ``problem`` or
        ``remedy`` is blank (a finding missing any of the five facts is not
        agent-legible, Constitution III.11).
    """
    for label, value in (
        ("error_class", error_class),
        ("symbol", symbol),
        ("file", file),
        ("problem", problem),
        ("remedy", remedy),
    ):
        if not value.strip():
            raise ValueError(f"sentinel finding: {label} must be non-empty")
    location = f"{file}:{line}" if line > 0 else f"{file} "
    return f"[{error_class}] {symbol} @ {location} — {problem} | REMEDY: {remedy}"
