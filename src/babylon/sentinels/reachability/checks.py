"""Loud static checks for the reachability sentinel (§9 W.3.2).

Three gating rules over the registry in
:mod:`babylon.sentinels.reachability.registry`:

1. **gate-operand-writer** — every ``DETECTED`` row's operand has at least one
   statically-found runtime write in the scan roots (subscript assignment, or
   an ``update_node``/``add_node`` stamp).
2. **ledger honesty** — every non-``DETECTED`` row carries a citation, and a
   ledgered operand that *gains* a writer reds the gate until the row is
   promoted (the ratchet only tightens).
3. **detector-read registration** — every ``.get("<attr>")`` read in the
   EndgameDetector is a registered row (new gate reads force registration; the
   type keys belong to the vocabulary sentinel).

Exit codes follow the family contract (:func:`babylon.sentinels.base.run_sensor`):
0 clean, 1 gating violations, 2 infrastructure failure.
"""

from __future__ import annotations

import argparse
import ast
from collections.abc import Iterable, Iterator
from pathlib import Path

from babylon.sentinels.base import SCOPE_NOT_DECLARED, LabelledCheck, SentinelCheckError, run_sensor
from babylon.sentinels.reachability.registry import (
    DETECTOR_PATH,
    GATE_OPERAND_ROWS,
    REPO_ROOT,
    SCAN_EXCLUDES,
    SCAN_ROOTS,
    TYPE_KEYS,
    GateOperandRow,
    Governance,
)

#: Graph-mutation call names whose keyword/dict-literal keys count as writes.
_GRAPH_WRITE_CALLS = frozenset({"update_node", "add_node"})

_WHY = (
    "why: a writer-less gate operand pins an ending's gate at its default "
    "forever — the flat-axis/unreachable-endings class (Standard §9 W.0)."
)


def _parse(path: Path) -> ast.Module:
    """Parse ``path`` loudly (missing/unparseable source is exit 2, not a pass)."""
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc
    except SyntaxError as exc:
        raise SentinelCheckError(f"cannot parse {path}: {exc}") from exc


def _scan_files() -> Iterator[Path]:
    """Yield every runtime ``.py`` under the scan roots, minus seed excludes."""
    for root in SCAN_ROOTS:
        if not root.is_dir():
            raise SentinelCheckError(f"scan root missing: {root}")
        for path in sorted(root.rglob("*.py")):
            if any(exclude in path.parents for exclude in SCAN_EXCLUDES):
                continue
            yield path


def _dict_string_keys(node: ast.Dict) -> Iterator[str]:
    for key in node.keys:
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            yield key.value


def production_attribute_writes(paths: Iterable[Path]) -> dict[str, list[str]]:
    """Index every statically-detectable attribute write in ``paths``.

    A *write* is: a string-keyed subscript assignment (plain or augmented), or
    a keyword / dict-literal key passed to an ``update_node``/``add_node``
    call. Reads (``.get(...)``, comparisons) and keyword arguments to other
    calls are deliberately not writes — a formula *parameter* named like an
    operand is the false-positive the endings audit warned about.

    :param paths: Source files to scan.
    :returns: Mapping of attribute name to its ``file:line`` write sites.
    :raises SentinelCheckError: On unreadable/unparseable source (exit 2).
    """
    index: dict[str, list[str]] = {}

    def _record(name: str, path: Path, lineno: int) -> None:
        index.setdefault(name, []).append(f"{path}:{lineno}")

    for path in paths:
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.Assign | ast.AugAssign):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if (
                        isinstance(target, ast.Subscript)
                        and isinstance(target.slice, ast.Constant)
                        and isinstance(target.slice.value, str)
                    ):
                        _record(target.slice.value, path, node.lineno)
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in _GRAPH_WRITE_CALLS
            ):
                for keyword in node.keywords:
                    if keyword.arg is not None:
                        _record(keyword.arg, path, node.lineno)
                    elif isinstance(keyword.value, ast.Dict):
                        for key in _dict_string_keys(keyword.value):
                            _record(key, path, node.lineno)
                for arg in node.args:
                    if isinstance(arg, ast.Dict):
                        for key in _dict_string_keys(arg):
                            _record(key, path, node.lineno)
    return index


def _cited_writer_holds(row: GateOperandRow, repo_root: Path) -> bool:
    """True if ``row.writer_path`` still passes the operand as a call argument."""
    for node in ast.walk(_parse(repo_root / row.writer_path)):
        if isinstance(node, ast.Call):
            for arg in node.args:
                if isinstance(arg, ast.Constant) and arg.value == row.operand:
                    return True
    return False


def gate_operand_violations(
    rows: tuple[GateOperandRow, ...],
    write_index: dict[str, list[str]],
    repo_root: Path | None = None,
) -> list[str]:
    """Enforce each row's governance against the observed write index.

    :param rows: The registry rows under audit.
    :param write_index: Output of :func:`production_attribute_writes`.
    :param repo_root: Root for resolving ``CITED_WRITER`` paths (defaults to
        the registry's repo root).
    :returns: One violation string per broken obligation.
    """
    root = repo_root if repo_root is not None else REPO_ROOT
    violations: list[str] = []
    for row in rows:
        sites = write_index.get(row.operand, [])
        if row.governance is Governance.DETECTED:
            if not sites:
                violations.append(
                    f'gate operand "{row.operand}" (read by {row.reader}) has no '
                    f"runtime production writer in the scan roots.\n"
                    f"    fix: wire it as a typed motion (Standard §9 W.2 WIRE), or "
                    f"ledger it with a cited CHARTER/BLOCKED/RULED_ABSENT row.\n"
                    f"    {_WHY}"
                )
        elif row.governance is Governance.CITED_WRITER:
            if not row.writer_path:
                violations.append(
                    f'cited-writer gate operand "{row.operand}" is missing its '
                    f"writer_path — a cite the check cannot verify is not a cite."
                )
            elif not _cited_writer_holds(row, root):
                violations.append(
                    f'cited writer for gate operand "{row.operand}" no longer holds: '
                    f'{row.writer_path} does not pass "{row.operand}" as a call '
                    f"argument.\n"
                    f"    fix: re-cite the real writer, or demote the row to a "
                    f"cited disposition (Standard §9 W.2).\n"
                    f"    {_WHY}"
                )
        else:
            if not row.citation:
                violations.append(
                    f'ledgered gate operand "{row.operand}" '
                    f"({row.governance.value}) is missing its citation — an "
                    f"unruled absence is indistinguishable from an oversight "
                    f"(Standard §9 W.2)."
                )
            if sites:
                joined = ", ".join(sites)
                violations.append(
                    f'stale ledger row: "{row.operand}" is ledgered '
                    f"({row.governance.value}) but now has runtime writer(s) at "
                    f"{joined}.\n"
                    f"    fix: promote the row to DETECTED — the ratchet only "
                    f"tightens (Standard §9 W.3)."
                )
    return violations


def unregistered_gate_reads(detector_path: Path, registered: frozenset[str]) -> list[str]:
    """Every ``.get("<attr>")`` read in the detector must be a registry row.

    :param detector_path: The EndgameDetector source file.
    :param registered: Operand names the registry currently declares.
    :returns: One violation per unregistered gate read.
    """
    violations: list[str] = []
    for node in ast.walk(_parse(detector_path)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            attr = node.args[0].value
            if attr in TYPE_KEYS or attr in registered:
                continue
            violations.append(
                f'{detector_path}:{node.lineno} reads unregistered gate operand "{attr}" — '
                f"add a GateOperandRow (DETECTED, or a cited disposition) so the "
                f"writer obligation is governed (Standard §9 W.3.2)."
            )
    return violations


def _registered_operands() -> frozenset[str]:
    return frozenset(row.operand for row in GATE_OPERAND_ROWS)


def _check_gate_operands() -> list[str]:
    return gate_operand_violations(GATE_OPERAND_ROWS, production_attribute_writes(_scan_files()))


def _check_detector_reads() -> list[str]:
    return unregistered_gate_reads(DETECTOR_PATH, _registered_operands())


_GATING: tuple[LabelledCheck, ...] = (
    ("gate-operand-writer", _check_gate_operands),
    ("detector-read-registration", _check_detector_reads),
)


def _summary(advisory_count: int) -> str:
    ledgered = sum(
        1
        for row in GATE_OPERAND_ROWS
        if row.governance in (Governance.CHARTER, Governance.BLOCKED, Governance.RULED_ABSENT)
    )
    return (
        f"REACHABILITY clean: {len(GATE_OPERAND_ROWS)} gate operands governed "
        f"({ledgered} ledgered awaiting their charters), detector reads fully "
        f"registered ({advisory_count} advisories)."
    )


def main(argv: list[str] | None = None) -> int:
    """Run the reachability sentinel and return the exit code.

    :param argv: CLI args (``--check`` is accepted as the CI-mode alias; the
        behavior is always to gate).
    :returns: 0 clean, 1 gating violations, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description="Gate-operand reachability — static writer closure (Standard §9 W.3.2)."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)
    return run_sensor("REACHABILITY", _GATING, (), _summary, scope=SCOPE_NOT_DECLARED)
