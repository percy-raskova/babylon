"""The seam-algebra sensor — static Lawvere co-Heyting boundary computation.

Builds the ambient graph ``G`` from :mod:`babylon.sentinels.seam_algebra.registry`
(declared :class:`~babylon.sentinels.seam_algebra.registry.ConstructNode` +
:class:`~babylon.sentinels.seam_algebra.registry.ExpectedConsumer` edges), computes
the live subgraph ``L`` reachable from :data:`~babylon.sentinels.seam_algebra.
registry.PRODUCTION_ENTRY_POINTS`, and reports every construct in ``G \\ L`` — a
**disconnected subsystem** — that is not covered by a dated
:class:`~babylon.sentinels.exemptions.SentinelExemption`.

**Verification is uniform across all four edge kinds** (``read``/``call``/
``import``/``publish``): an edge is confirmed real when
:func:`babylon.sentinels._ast.referenced_names` on the edge's ``consumer_file``
contains the construct's ``symbol`` — the exact primitive
:mod:`babylon.sentinels.liveness.checks` already uses for its own
computed-but-never-consumed rule. This is a deliberate day-one reduction: the six
legacy families each verify their own narrower claim with a bespoke AST walk
(``store_writer_call_sites``, ``producer_reference_sites``, node-type
stamp/query matching, watched-receiver member resolution, …); this family
proves that ONE uniform "does the consumer file mention this symbol" rule is
sufficient to re-express — and, cross-validated, to catch the same mutation
as — a representative construct from each of them (see
``tests/unit/sentinels/test_seam_algebra_cross_validation.py``). Sharpening the
edge-kind-specific verification (e.g. requiring a genuine *call* AST shape for
``edge_kind="call"``) is named future work, not silently claimed here.

**Reachability is a bounded fixed-point closure**, not unbounded recursion
(Constitution "no unbounded loop" discipline, mirroring
:func:`babylon.sentinels.inert.checks._close_writer_chains`'s own
``_MAX_CHAIN_PASSES`` bound): starting from ``L₀`` = the entry-point files, each
pass adds any not-yet-live construct whose edge targets an already-live file
and whose symbol the target file genuinely references; its OWN ``def_file``
joins the live-file set too, letting a second construct chain off it. Passes
stop the moment nothing grows, bounded by :data:`_MAX_CLOSURE_PASSES`.

Day-one scope (design §3.1): **static ∂L only** — no engine import, no probe
run. The trace-based residual leg (reachable from probe goldens) is staged to
the nightly lane, not this family.

**Gate-satisfaction** (T1.1 U4, design §3.2 point 1) is this family's second
check: a construct's LIVENESS (above) says nothing about whether a
production-reachable function's OWN early-return guards (``context.get(K)``,
``services.X is None``, the ``X if hasattr(obj, "X") else None`` optional-
attribute form) ever actually pass in production. :func:`check_gate_satisfaction`
reds a :class:`~babylon.sentinels.seam_algebra.registry.GatedInput` row whose
``gated_input`` has no declared, AST-grounded, UNCONDITIONAL production
supplier — the day-one witnesses are F-1 (``session_id``) and F-2
(``distribution_calculator``, ``vol2_step``), both held open as dated
exemptions (design §9 item 4); ``melt_calculator`` is the shipped POSITIVE
control proving the check recognizes a genuinely satisfied gate too.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

from babylon.sentinels._ast import (
    attribute_is_none_guard_lines,
    dict_get_call_lines,
    hasattr_guard_lines,
    referenced_names,
)
from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor
from babylon.sentinels.exemptions import SentinelExemption, is_exempt
from babylon.sentinels.report import finding
from babylon.sentinels.seam_algebra.registry import (
    CONSTRUCT_REGISTRY,
    EDGE_REGISTRY,
    GATE_REGISTRY,
    GATE_SATISFACTION_EXEMPTIONS,
    PRODUCTION_ENTRY_POINTS,
    SEAM_ALGEBRA_EXEMPTIONS,
    ConstructNode,
    ExpectedConsumer,
    GatedInput,
)

__all__ = [
    "build_live_set",
    "check_disconnected_subsystems",
    "check_gate_satisfaction",
    "main",
]

#: Repo root (this file is ``<root>/src/babylon/sentinels/seam_algebra/checks.py``).
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]

#: A fixed, statically-provable upper bound on the reachability fixed-point
#: closure (Constitution "no unbounded loop" discipline) — mirrors
#: ``babylon.sentinels.inert.checks._MAX_CHAIN_PASSES``. Each pass can only add
#: at least one previously-dead construct to ``L`` or the closure halts early,
#: so the true number of passes needed is bounded by the registry's own size;
#: 50 is comfortably above any registry this hand-curated family is expected
#: to reach for the foreseeable future. A future registry that ever needed
#: more (an unrealistically long single chain) would UNDER-report reachable
#: constructs as disconnected — a false positive, never a false negative, and
#: loud (the gate reds, it does not silently pass) — see the module docstring.
_MAX_CLOSURE_PASSES: Final[int] = 50

_WHY_DISCONNECTED: Final[str] = (
    "WHY THIS FAILS: a construct with no path from PRODUCTION_ENTRY_POINTS in the "
    "unified graph is a nonempty core severed from the live subgraph L -- it may "
    "run under its own unit tests forever without a single production caller ever "
    "reaching it. This is the same failure the inert/unconsumed/liveness families "
    "each catch in their own narrower vocabulary, generalized to one boundary "
    "computation (Lawvere 1991 co-Heyting boundary, seam = dL)."
)


def _index_edges_by_construct(
    edges: tuple[ExpectedConsumer, ...],
) -> dict[str, tuple[ExpectedConsumer, ...]]:
    """Group edges by their originating construct name.

    :param edges: The declared edge rows.
    :returns: ``{construct_name: (edge, ...)}``, preserving each group's
        original declaration order.
    """
    grouped: dict[str, list[ExpectedConsumer]] = {}
    for edge in edges:
        grouped.setdefault(edge.construct_name, []).append(edge)
    return {name: tuple(rows) for name, rows in grouped.items()}


def build_live_set(
    constructs: tuple[ConstructNode, ...] = CONSTRUCT_REGISTRY,
    edges: tuple[ExpectedConsumer, ...] = EDGE_REGISTRY,
    entry_points: tuple[str, ...] = PRODUCTION_ENTRY_POINTS,
) -> frozenset[str]:
    """Compute ``L`` — the constructs transitively reachable from entry points.

    A construct joins ``L`` the moment one of its declared edges targets a
    file already known live (initially just ``entry_points``, then growing to
    include every live construct's own ``def_file``) AND that target file's
    :func:`~babylon.sentinels._ast.referenced_names` genuinely contains the
    construct's ``symbol``. Runs to a fixed point, bounded by
    :data:`_MAX_CLOSURE_PASSES`.

    :param constructs: Declared node rows (defaults to the real
        :data:`~babylon.sentinels.seam_algebra.registry.CONSTRUCT_REGISTRY`;
        injectable so tests can supply a fixture graph).
    :param edges: Declared edge rows (defaults to the real
        :data:`~babylon.sentinels.seam_algebra.registry.EDGE_REGISTRY`).
    :param entry_points: The reachability roots (defaults to the real
        :data:`~babylon.sentinels.seam_algebra.registry.PRODUCTION_ENTRY_POINTS`).
    :returns: The names of every construct in ``L``.
    :raises babylon.sentinels.base.SentinelCheckError: If an edge's
        ``consumer_file`` is missing or unparseable once it is actually
        examined — an infrastructure failure, never a silent pass.
    """
    edges_by_construct = _index_edges_by_construct(edges)
    live_files: set[str] = set(entry_points)
    live_constructs: set[str] = set()

    for _pass in range(_MAX_CLOSURE_PASSES):
        grew = False
        for construct in constructs:
            if construct.name in live_constructs:
                continue
            for edge in edges_by_construct.get(construct.name, ()):
                if edge.consumer_file not in live_files:
                    continue
                if construct.symbol in referenced_names(_REPO_ROOT / edge.consumer_file):
                    live_constructs.add(construct.name)
                    live_files.add(construct.def_file)
                    grew = True
                    break
        if not grew:
            break

    return frozenset(live_constructs)


def check_disconnected_subsystems(
    constructs: tuple[ConstructNode, ...] = CONSTRUCT_REGISTRY,
    edges: tuple[ExpectedConsumer, ...] = EDGE_REGISTRY,
    entry_points: tuple[str, ...] = PRODUCTION_ENTRY_POINTS,
    exemptions: tuple[SentinelExemption, ...] = SEAM_ALGEBRA_EXEMPTIONS,
) -> list[str]:
    """``seam = ∂L``: every declared construct outside ``L`` is a violation.

    :param constructs: Declared node rows (injectable — see :func:`build_live_set`).
    :param edges: Declared edge rows (injectable).
    :param entry_points: Reachability roots (injectable).
    :param exemptions: Dated, owner-approved rows holding a known disconnection
        open (defaults to the real
        :data:`~babylon.sentinels.seam_algebra.registry.SEAM_ALGEBRA_EXEMPTIONS`;
        injectable so the mutation test can prove a reverted exemption reds).
    :returns: Sorted agent-legible finding strings (empty when every
        non-exempt construct is reachable).
    :raises babylon.sentinels.base.SentinelCheckError: If a consumer file is
        missing or unparseable.
    """
    live = build_live_set(constructs, edges, entry_points)
    findings: list[str] = []
    for construct in constructs:
        if construct.name in live:
            continue
        if is_exempt(("construct", construct.name), exemptions):
            continue
        findings.append(
            finding(
                error_class="disconnected-subsystem",
                symbol=construct.symbol,
                file=construct.def_file,
                line=0,
                problem=(
                    f"{construct.name!r} ({construct.origin_family} family) has no "
                    "path from PRODUCTION_ENTRY_POINTS in the unified seam-algebra "
                    "graph — a nonempty core severed from L."
                ),
                remedy=(
                    "wire a real ExpectedConsumer edge (a consumer_file that "
                    "genuinely references this symbol, chained to a live file), "
                    "or add a dated SentinelExemption (key=('construct', name)) "
                    "citing why the disconnection is tolerated for now — never a "
                    f"silent registry removal. {_WHY_DISCONNECTED}"
                ),
            )
        )
    return sorted(findings)


_WHY_UNSATISFIED: Final[str] = (
    "WHY THIS FAILS: an early-return guard whose gated input has no declared, "
    "grounded, unconditional production supplier will silently no-op forever in "
    "production while every unit test that hand-supplies the input stays green -- "
    "the exact gate-blindness failure mode III.11 forbids staying quiet."
)


def _confirm_guard_grounded(gate: GatedInput) -> None:
    """Confirm ``gate.guard_shape``'s AST pattern is still present in ``gate.guard_file``.

    A registry row citing a guard that has since been edited away (or renamed)
    must fail loud, not silently read as "still enforced" -- mirrors
    :func:`_validate_edges_resolve`'s "reject a malformed/stale row" posture,
    deferred to check-run time here because it requires reading a file.

    :param gate: The row to ground.
    :raises babylon.sentinels.base.SentinelCheckError: If ``guard_file`` is
        missing/unparseable, or the declared ``guard_shape`` pattern for
        ``gated_input`` is not found in it (a stale registry row).
    """
    path = _REPO_ROOT / gate.guard_file
    if gate.guard_shape == "context_get":
        lines = dict_get_call_lines(path, gate.gated_input)
    elif gate.guard_shape == "services_attr_none":
        lines = attribute_is_none_guard_lines(path, gate.gated_input)
    else:
        lines = hasattr_guard_lines(path, gate.gated_input)
    if not lines:
        raise SentinelCheckError(
            f"{gate.name!r}: no {gate.guard_shape!r} guard for {gate.gated_input!r} "
            f"found in {gate.guard_file} -- registry row is stale (guard was edited "
            "away, renamed, or never existed)"
        )


def check_gate_satisfaction(
    gates: tuple[GatedInput, ...] = GATE_REGISTRY,
    exemptions: tuple[SentinelExemption, ...] = GATE_SATISFACTION_EXEMPTIONS,
) -> list[str]:
    """Red every construct-entry guard whose gated input has no production supplier.

    For each declared :class:`~babylon.sentinels.seam_algebra.registry.GatedInput`
    row: first :func:`_confirm_guard_grounded` (the guard itself is real, or this
    is an infrastructure failure), then check whether ``gated_input`` is
    genuinely SUPPLIED -- present in :func:`~babylon.sentinels._ast.referenced_names`
    of at least one declared ``supplier_files`` entry. A row declaring
    ``supplier_files`` that do NOT actually reference ``gated_input`` is itself a
    stale/ungrounded positive claim and is also an infrastructure failure (the
    same "a declared edge/producer must be verifiable" discipline
    :func:`build_live_set` and every sibling family enforce). An empty
    ``supplier_files`` tuple is the deliberate "no production supplier declared"
    claim and reds directly (unless exempted).

    :param gates: Declared gate rows (defaults to the real
        :data:`~babylon.sentinels.seam_algebra.registry.GATE_REGISTRY`;
        injectable so tests can supply a fixture gate).
    :param exemptions: Dated, owner-approved rows holding a known unsatisfied
        gate open (defaults to the real
        :data:`~babylon.sentinels.seam_algebra.registry.GATE_SATISFACTION_EXEMPTIONS`;
        injectable so the mutation test can prove a reverted exemption reds).
    :returns: Sorted agent-legible finding strings (empty when every non-exempt
        gate is satisfied).
    :raises babylon.sentinels.base.SentinelCheckError: If a guard/supplier file
        is missing/unparseable, a declared guard has gone stale, or a declared
        ``supplier_files`` entry does not actually reference ``gated_input``.
    """
    findings: list[str] = []
    for gate in gates:
        _confirm_guard_grounded(gate)
        supplied_by = [
            supplier_file
            for supplier_file in gate.supplier_files
            if gate.gated_input in referenced_names(_REPO_ROOT / supplier_file)
        ]
        if gate.supplier_files and not supplied_by:
            raise SentinelCheckError(
                f"{gate.name!r}: declared supplier_files {gate.supplier_files!r} do "
                f"not reference {gate.gated_input!r} -- registry row is stale"
            )
        if supplied_by:
            continue
        if is_exempt(("gate", gate.name), exemptions):
            continue
        findings.append(
            finding(
                error_class="gate-blindness",
                symbol=gate.gated_input,
                file=gate.guard_file,
                line=0,
                problem=(
                    f"{gate.name!r} ({gate.guard_shape}) gates on {gate.gated_input!r} "
                    "with no declared, grounded, unconditional production supplier."
                ),
                remedy=(
                    "wire a real, unconditional production supplier and cite it in "
                    "GatedInput.supplier_files, or add a dated SentinelExemption "
                    "(key=('gate', name)) citing why the gate stays unsatisfied for "
                    f"now — never a silent registry removal. {_WHY_UNSATISFIED}"
                ),
            )
        )
    return sorted(findings)


#: Any non-exempt disconnected subsystem OR unsatisfied construct-entry gate
#: is a live defect.
_GATING_CHECKS: Final[tuple[LabelledCheck, ...]] = (
    ("disconnected-subsystem", check_disconnected_subsystems),
    ("gate-satisfaction", check_gate_satisfaction),
)


def _summary(advisory_count: int) -> str:
    """Clean one-line summary: registry size, live-subgraph size, gate count.

    :param advisory_count: Number of advisory findings (0 — no advisory tier).
    :returns: The summary line.
    """
    _ = advisory_count  # This sentinel declares no advisory tier.
    live = build_live_set()
    return (
        f"Seam-algebra clean: {len(live)}/{len(CONSTRUCT_REGISTRY)} declared "
        f"construct(s) reachable from {len(PRODUCTION_ENTRY_POINTS)} production "
        f"entry point(s); {len(SEAM_ALGEBRA_EXEMPTIONS)} disconnected subsystem(s) "
        f"and {len(GATE_SATISFACTION_EXEMPTIONS)} unsatisfied gate(s) held open "
        "by a dated exemption."
    )


def main(argv: list[str] | None = None) -> int:
    """Run the seam-algebra boundary check and return the exit code.

    :param argv: CLI args (``--check`` is accepted as the CI-mode alias; the
        behavior is always to gate).
    :returns: 0 clean, 1 gating violations found, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Seam-algebra — static Lawvere co-Heyting boundary (dL) over the "
            "unified construct-to-expected-consumer registry (III.10 / III.11)."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)
    return run_sensor("SEAM-ALGEBRA", _GATING_CHECKS, (), _summary)


if __name__ == "__main__":
    sys.exit(main())
