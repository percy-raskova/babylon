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
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

from babylon.sentinels._ast import referenced_names
from babylon.sentinels.base import LabelledCheck, run_sensor
from babylon.sentinels.exemptions import SentinelExemption, is_exempt
from babylon.sentinels.report import finding
from babylon.sentinels.seam_algebra.registry import (
    CONSTRUCT_REGISTRY,
    EDGE_REGISTRY,
    PRODUCTION_ENTRY_POINTS,
    SEAM_ALGEBRA_EXEMPTIONS,
    ConstructNode,
    ExpectedConsumer,
)

__all__ = [
    "build_live_set",
    "check_disconnected_subsystems",
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


#: The one rule: any non-exempt disconnected subsystem is a live defect.
_GATING_CHECKS: Final[tuple[LabelledCheck, ...]] = (
    ("disconnected-subsystem", check_disconnected_subsystems),
)


def _summary(advisory_count: int) -> str:
    """Clean one-line summary: registry size and live-subgraph size.

    :param advisory_count: Number of advisory findings (0 — no advisory tier).
    :returns: The summary line.
    """
    _ = advisory_count  # This sentinel declares no advisory tier.
    live = build_live_set()
    return (
        f"Seam-algebra clean: {len(live)}/{len(CONSTRUCT_REGISTRY)} declared "
        f"construct(s) reachable from {len(PRODUCTION_ENTRY_POINTS)} production "
        f"entry point(s); {len(SEAM_ALGEBRA_EXEMPTIONS)} disconnected subsystem(s) "
        "held open by a dated exemption."
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
