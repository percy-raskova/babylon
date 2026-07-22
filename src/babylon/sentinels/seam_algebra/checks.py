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

**Stub-vs-calculator** (T1.1 U5, design §3.2 point 2) is this family's third
check: even a construct that IS live (reachable, per ``check_disconnected_
subsystems`` above) can still be a lie — a live call site can construct a
value type with a bare literal/neutral constant for one field while a
REGISTERED production calculator for exactly that value sits elsewhere,
uncalled. :func:`check_stub_vs_calculator` reds a
:class:`~babylon.sentinels.seam_algebra.registry.StubConsumer` row whose
declared literal stub is still present and whose cited
:class:`~babylon.sentinels.seam_algebra.registry.RegisteredCalculator` is
still real. Deliberately a small, hand-curated registry (mirrors
:data:`~babylon.sentinels.seam_algebra.registry.CONSTRUCT_REGISTRY`/
:data:`~babylon.sentinels.seam_algebra.registry.GATE_REGISTRY`'s own
day-one posture) rather than a full-codebase auto-scan across every
Pydantic-model construction site — **this scoping IS the anti-false-positive
heuristic**: a row only exists when a human has already confirmed the cited
calculator genuinely computes that field from real inputs, so a field that is
LEGITIMATELY constant-by-design is simply never registered here (never
silenced via a vacuous exemption). The AST-level heuristic layered on top
(:func:`~babylon.sentinels._ast.literal_keyword_call_lines`) only ever
classifies a BARE ``ast.Constant`` keyword value as a stub candidate — a
variable, a function call, or any other computed expression is invisible to
it by construction, never misread as a stub. The day-one witness is the
ReproductionBalance stub (``domain/economics/tick/system/__init__.py``),
held open as a dated exemption (design §9 item 4) citing the staged Vol II
circulation-engine program as the actual fix's home.

**Severity single-source** (T1.1 U6, design §3.2 point 3) is this family's
fourth check, and generalizes :func:`babylon.sentinels.seam.checks.
check_severity_vocabulary` (which only guarded ``web/game/engine_bridge.py``
against a reappeared ``_EVENT_SEVERITY`` literal, by NAME, never by value) into
the full three-way parity gate T1.1 promises: web severity == Archive severity
== U1's generated table (:func:`babylon.models.event_severity.resolve_severity`),
across all 84 :class:`~babylon.models.enums.events.EventType` members including
the loud ``unclassified -> warning`` floor. Static by the same family
discipline as every check above (never importing ``web.game.engine_bridge`` or
``babylon.tui.chronicle_salience`` live — the former transitively reaches
``babylon.engine``, which the layer-0.5 import contract forbids reaching from
``babylon.sentinels`` at all): :func:`check_severity_single_source` confirms,
via :func:`~babylon.sentinels._ast.referenced_names`, that both surfaces still
genuinely reference ``resolve_severity``; via
:func:`~babylon.sentinels._ast.optional_dict_literal_str_items`, that neither
retired hand-copied literal name (``_EVENT_SEVERITY``/``EVENT_SEVERITY``) has
reappeared in EITHER file with a value diverging from the generated table; via
:func:`~babylon.sentinels._ast.all_dict_literal_str_items`, that no OTHER
module-level dict literal — reintroduced under any other name — carries a
diverging entry either (a re-fork dodging the two watched names by simply
being renamed); and, via
:func:`~babylon.sentinels._ast.conditional_literal_returns_by_enum_member`,
that no inline ``if event_type == EventType.MEMBER: return "<tier>"``-shaped
branch anywhere in either file diverges from the generated table for that
member (a re-fork introducing no dict literal at all, folded straight into
the classify function's own control flow). Because each surface is checked
independently against the SAME generated table, transitive equality (web ==
archive) follows whenever both hold, so all three pairwise comparisons the
design names are covered — across all four detection prongs — without a
separate web-vs-archive pass.

**Wall-clock-call-site** (T1.1 U7, design §3.2 point 4) is this family's
fifth and final day-one check: a call site inside a P-tier/hashed-artifact
producer that reads real wall-clock time
(:data:`~babylon.sentinels._ast.WALLCLOCK_SYMBOLS` — ``datetime.now``/
``datetime.utcnow``/``time.time``/``time.perf_counter``/``time.monotonic``)
is a non-determinism smell even where the read is provably excluded from a
byte-identity contract TODAY — a later refactor that folds the value back
into a compared field would silently reintroduce non-determinism with every
existing unit test staying green. :func:`check_wallclock_call_sites` grounds
each declared :class:`~babylon.sentinels.seam_algebra.registry.WallclockCallSite`
row (the exact ``(line, symbol)`` pair is really present in ``def_file``, via
:func:`~babylon.sentinels._ast.wallclock_call_lines`) and reds it unless
exempted — the day-one witnesses are ``engine/observers/jsonl_recorder.py``
(three call sites), ``engine/observers/metrics.py`` (one), and "the run
manifest" (``engine/headless_runner/runner.py``'s ``wallclock_start``/
``wallclock_end``, feeding ``engine/headless_runner/manifest.py``) — all six
held open as dated exemptions (design §9 item 4); the manifest pair's
exclusion from ``input_hash()`` is a pre-existing, grounded design fact
(``manifest.py``'s own docstring already declares it), never a gap this unit
discovers.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final, get_args

from babylon.models.enums.events import EventType
from babylon.models.event_severity import SeverityTier, resolve_severity
from babylon.sentinels._ast import (
    all_dict_literal_str_items,
    attribute_is_none_guard_lines,
    conditional_literal_returns_by_enum_member,
    dict_get_call_lines,
    function_return_annotation_name,
    hasattr_guard_lines,
    literal_keyword_call_lines,
    module_level_function_names,
    optional_dict_literal_str_items,
    referenced_names,
    wallclock_call_lines,
)
from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor
from babylon.sentinels.exemptions import SentinelExemption, is_exempt
from babylon.sentinels.report import finding
from babylon.sentinels.seam_algebra.registry import (
    CALCULATOR_REGISTRY,
    CONSTRUCT_REGISTRY,
    EDGE_REGISTRY,
    GATE_REGISTRY,
    GATE_SATISFACTION_EXEMPTIONS,
    PRODUCTION_ENTRY_POINTS,
    SEAM_ALGEBRA_EXEMPTIONS,
    STUB_REGISTRY,
    STUB_VS_CALCULATOR_EXEMPTIONS,
    WALLCLOCK_EXEMPTIONS,
    WALLCLOCK_REGISTRY,
    ConstructNode,
    ExpectedConsumer,
    GatedInput,
    RegisteredCalculator,
    StubConsumer,
    WallclockCallSite,
)

__all__ = [
    "build_live_set",
    "check_disconnected_subsystems",
    "check_gate_satisfaction",
    "check_severity_single_source",
    "check_stub_vs_calculator",
    "check_wallclock_call_sites",
    "main",
]

#: Repo root (this file is ``<root>/src/babylon/sentinels/seam_algebra/checks.py``).
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]

#: The two severity surfaces T1.1 U2 single-sourced onto ``resolve_severity``.
_WEB_SEVERITY_PATH: Final[Path] = _REPO_ROOT / "web" / "game" / "engine_bridge.py"
_ARCHIVE_SEVERITY_PATH: Final[Path] = (
    _REPO_ROOT / "src" / "babylon" / "tui" / "chronicle_salience.py"
)

#: The two hand-copied severity dict names T1.1 U2 retired — checked in BOTH
#: files (not just each name's "home" surface) so a mutation reintroducing
#: either name in either file is caught regardless of which surface it lands on.
_SEVERITY_LITERAL_NAMES: Final[tuple[str, ...]] = ("_EVENT_SEVERITY", "EVENT_SEVERITY")

#: The three-bucket taxonomy's own literal values, read off
#: :data:`~babylon.models.event_severity.SeverityTier` (never duplicated as a
#: hand-typed set) — both the any-name dict scan and the inline-override scan
#: below use this to recognize a candidate re-fork by VALUE shape, not just by
#: a watched name.
_SEVERITY_TIER_VALUES: Final[frozenset[str]] = frozenset(get_args(SeverityTier))

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


_WHY_STUBBED: Final[str] = (
    "WHY THIS FAILS: a live call site that constructs a value type with a bare "
    "literal instead of calling the registered calculator for it will silently "
    "keep returning the SAME fabricated value in production forever -- every "
    "downstream consumer of that value (a crisis detector, a bifurcation gate, "
    "a narrative observer) is reasoning over dead data while its own unit tests, "
    "which construct the type directly, stay green. This is the same silent-drift "
    "failure the other seam-algebra checks catch in their own vocabulary, applied "
    "to a construct that IS reachable but whose VALUE is a lie."
)


def _confirm_calculator_grounded(calculator: RegisteredCalculator) -> None:
    """Confirm ``calculator`` is still a real, module-level function returning ``produces``.

    A registry row citing a calculator that has since been renamed, deleted,
    or whose return type has changed must fail loud, not silently read as
    "still the registered calculator" -- mirrors :func:`_confirm_guard_grounded`'s
    own "reject a stale row" posture.

    :param calculator: The row to ground.
    :raises babylon.sentinels.base.SentinelCheckError: If ``def_file`` is
        missing/unparseable, ``symbol`` is not a module-level function in it,
        or that function's own return annotation does not name ``produces``.
    """
    path = _REPO_ROOT / calculator.def_file
    if calculator.symbol not in module_level_function_names(path):
        raise SentinelCheckError(
            f"{calculator.name!r}: no module-level function {calculator.symbol!r} found "
            f"in {calculator.def_file} -- registry row is stale (renamed, deleted, or "
            "never existed)"
        )
    returned = function_return_annotation_name(path, calculator.symbol)
    if returned != calculator.produces:
        raise SentinelCheckError(
            f"{calculator.name!r}: {calculator.symbol} in {calculator.def_file} returns "
            f"{returned!r}, not the declared produces={calculator.produces!r} -- registry "
            "row is stale"
        )


def _confirm_stub_grounded(stub: StubConsumer) -> None:
    """Confirm ``stub``'s literal call site is still really present.

    :param stub: The row to ground.
    :raises babylon.sentinels.base.SentinelCheckError: If ``consumer_file`` is
        missing/unparseable, or no
        ``consumer_symbol(..., stub_field=<literal>, ...)`` call remains in it
        (the stub was fixed, renamed, or never existed -- a stale registry row).
    """
    path = _REPO_ROOT / stub.consumer_file
    lines = literal_keyword_call_lines(path, stub.consumer_symbol, stub.stub_field)
    if not lines:
        raise SentinelCheckError(
            f"{stub.name!r}: no {stub.consumer_symbol}(..., {stub.stub_field}=<literal>) "
            f"call found in {stub.consumer_file} -- registry row is stale (the stub was "
            "wired to a real value, renamed, or never existed)"
        )


def check_stub_vs_calculator(
    stubs: tuple[StubConsumer, ...] = STUB_REGISTRY,
    calculators: tuple[RegisteredCalculator, ...] = CALCULATOR_REGISTRY,
    exemptions: tuple[SentinelExemption, ...] = STUB_VS_CALCULATOR_EXEMPTIONS,
) -> list[str]:
    """Red every live consumer fed a literal where a registered calculator exists.

    For each declared :class:`~babylon.sentinels.seam_algebra.registry.StubConsumer`
    row: first :func:`_confirm_stub_grounded` (the literal call site is real, or
    this is an infrastructure failure), then :func:`_confirm_calculator_grounded`
    on the row's cited :class:`~babylon.sentinels.seam_algebra.registry.
    RegisteredCalculator` (same discipline). A grounded, non-exempt row is, by
    definition, a live stub -- the registry itself only ever declares a row once
    a human has confirmed the calculator genuinely computes that field from real
    inputs (see the module docstring's "anti-false-positive heuristic" note), so
    every grounded row reds unless exempted.

    :param stubs: Declared stub-consumer rows (defaults to the real
        :data:`~babylon.sentinels.seam_algebra.registry.STUB_REGISTRY`;
        injectable so tests can supply a fixture stub).
    :param calculators: Declared calculator rows (defaults to the real
        :data:`~babylon.sentinels.seam_algebra.registry.CALCULATOR_REGISTRY`;
        injectable).
    :param exemptions: Dated, owner-approved rows holding a known stub open
        (defaults to the real
        :data:`~babylon.sentinels.seam_algebra.registry.STUB_VS_CALCULATOR_EXEMPTIONS`;
        injectable so the mutation test can prove a reverted exemption reds).
    :returns: Sorted agent-legible finding strings (empty when every non-exempt
        stub is grounded-but-tolerated or absent).
    :raises babylon.sentinels.base.SentinelCheckError: If a consumer/calculator
        file is missing/unparseable, a declared literal call site has gone
        stale, a declared calculator has gone stale, or a stub row names a
        calculator absent from ``calculators`` (should already be impossible
        given :data:`STUB_REGISTRY`'s own collection-time validation, but an
        injected fixture pair is checked here too rather than trusting the
        caller).
    """
    by_name = {calculator.name: calculator for calculator in calculators}
    findings: list[str] = []
    for stub in stubs:
        _confirm_stub_grounded(stub)
        calculator = by_name.get(stub.calculator_name)
        if calculator is None:
            raise SentinelCheckError(
                f"{stub.name!r}: names unknown calculator {stub.calculator_name!r} -- "
                "not present in the supplied calculators tuple"
            )
        _confirm_calculator_grounded(calculator)
        if is_exempt(("stub", stub.name), exemptions):
            continue
        findings.append(
            finding(
                error_class="stub-vs-calculator",
                symbol=stub.consumer_symbol,
                file=stub.consumer_file,
                line=0,
                problem=(
                    f"{stub.consumer_symbol}(...) is constructed with a literal "
                    f"{stub.stub_field}=<constant> at a live production call site, even "
                    f"though {calculator.symbol!r} ({calculator.def_file}) is a "
                    "registered calculator for exactly this value."
                ),
                remedy=(
                    f"wire {calculator.symbol}(...) to compute {stub.stub_field} from real "
                    "inputs at this call site, or add a dated SentinelExemption "
                    f"(key=('stub', {stub.name!r})) citing why the literal stands in for "
                    f"now — never a silent registry removal. {_WHY_STUBBED}"
                ),
            )
        )
    return sorted(findings)


_WHY_SEVERITY_FORKED: Final[str] = (
    "WHY THIS FAILS: web/game/engine_bridge.py and babylon.tui.chronicle_salience used to "
    "each carry their own hand-copied 47-entry severity dict with no mechanical guarantee "
    "they stayed equal -- T1.1 U2 deleted both in favor of ONE generated resolver "
    "(babylon.models.event_severity.resolve_severity). A reintroduced local severity "
    "literal, or a classify function that no longer calls resolve_severity at all, is "
    "exactly that silent-refork failure resurfacing -- the two surfaces (and the "
    "render-tier / autopause behavior they drive) would drift apart again with every "
    "green unit test unaware, until a player sees two different severities for the same "
    "event on two different clients."
)


def _generated_severity_table() -> dict[str, str]:
    """Build the real ``{EventType.value: tier}`` table for all 84 members.

    Imports only :mod:`babylon.models.event_severity` (layer 0 — never the
    engine), so calling this from a sentinel check carries no engine/web
    weight, unlike importing either live surface would.

    :returns: The generated table, one entry per :class:`~babylon.models.
        enums.events.EventType` member — the 47 U1 classifies directly, plus
        the 37 that resolve through the loud ``unclassified -> warning`` floor.
    """
    return {event_type.value: resolve_severity(event_type).tier for event_type in EventType}


def _tier_divergence_finding(
    label: str, symbol: str, path: Path, key: str, tier: str, table: dict[str, str]
) -> str | None:
    """A finding string when ``symbol`` (in the ``label`` surface) resolves
    ``key`` to ``tier`` but the generated ``table`` disagrees.

    Shared by BOTH re-fork-detection prongs added to close the review finding
    against :func:`check_severity_single_source`'s original single prong
    (a named-dict-literal scan alone): the any-name dict scan and the
    inline-conditional-override scan both reduce to this same "does this
    resolved value match the generated table" question once they have
    extracted a ``(key, tier)`` candidate from wherever it was hiding.

    :param label: ``"web"``/``"archive"`` — which surface this candidate came
        from.
    :param symbol: An agent-legible name for the candidate re-fork site.
    :param path: The surface's source file (the finding's ``file`` field).
    :param key: The ``EventType.value`` the candidate resolves.
    :param tier: The tier the candidate resolves ``key`` to.
    :param table: The generated reference table.
    :returns: A finding string, or ``None`` when ``tier`` matches the table,
        or ``key`` is absent from it (not a key either real generated table
        row this comparison can speak to — e.g. a caller-supplied fixture
        table narrower than the real 84 members).
    """
    generated_tier = table.get(key)
    if generated_tier is None or tier == generated_tier:
        return None
    return finding(
        error_class="severity-single-source",
        symbol=symbol,
        file=str(path),
        line=0,
        problem=(
            f"the {label} surface's {symbol} resolves {key!r} to {tier!r} but the generated "
            f"table resolves {key!r} to {generated_tier!r} — single source violated."
        ),
        remedy=(
            "delete the reintroduced override and resolve severity "
            f"through resolve_severity() instead. {_WHY_SEVERITY_FORKED}"
        ),
    )


def check_severity_single_source(
    web_path: Path = _WEB_SEVERITY_PATH,
    archive_path: Path = _ARCHIVE_SEVERITY_PATH,
    generated_table: dict[str, str] | None = None,
) -> list[str]:
    """GATING: web severity == Archive severity == U1's generated table, all 84 members.

    T1.1 U6 (design §3.2 point 3) generalizes :func:`babylon.sentinels.seam.
    checks.check_severity_vocabulary` (which only guarded the web bridge
    against a reappeared ``_EVENT_SEVERITY`` literal, by NAME, regardless of
    value) into the full three-way parity gate the design names. For each
    surface (web bridge, Archive Chronicle) this check:

    1. confirms, via :func:`~babylon.sentinels._ast.referenced_names`, that the
       surface still genuinely references ``resolve_severity`` (T1.1 U2's
       single-sourcing has not been quietly undone);
    2. confirms, via :func:`~babylon.sentinels._ast.optional_dict_literal_str_items`,
       that neither retired hand-copied literal name (``_EVENT_SEVERITY`` /
       ``EVENT_SEVERITY``) has reappeared in that file with an entry whose
       value diverges from ``generated_table``;
    3. confirms, via :func:`~babylon.sentinels._ast.all_dict_literal_str_items`,
       that NO OTHER module-level dict literal — reintroduced under any name,
       not just the two retired ones — carries an entry whose key is a real
       ``EventType.value`` and whose value is a taxonomy tier that diverges
       from ``generated_table`` (a hand-copied severity dict does not stop
       being a hand-copied severity dict just because it is renamed; a
       finding here was a silent miss before this prong existed); and
    4. confirms, via
       :func:`~babylon.sentinels._ast.conditional_literal_returns_by_enum_member`,
       that no ``if <x> == EventType.MEMBER: return "<tier>"``-shaped inline
       branch anywhere in the file returns a tier that diverges from
       ``generated_table`` for that member — the re-fork vector that
       bypasses BOTH dict-literal prongs above by never introducing a dict at
       all (an inline per-member override folded straight into the classify
       function's control flow was a silent miss before this prong existed).

    Because both surfaces are checked independently against the SAME
    ``generated_table``, transitive equality (web == archive) is implied
    whenever both individually hold — so all three pairwise comparisons the
    design names (web/archive, web/generated, archive/generated) are covered
    without a separate web-vs-archive pass, across all four prongs above.

    :param web_path: The web bridge source (defaults to the real
        ``web/game/engine_bridge.py``; injectable so tests can supply a
        deliberately-forked fixture).
    :param archive_path: The Archive Chronicle source (defaults to the real
        ``src/babylon/tui/chronicle_salience.py``; injectable).
    :param generated_table: The ``{EventType.value: tier}`` reference table
        (defaults to the real 84-member table via
        :func:`_generated_severity_table` when ``None``; injectable so a
        fixture table can accompany a fixture path without touching the real
        module — covers all 84 members, including the 37 that resolve
        through the loud unclassified floor, by construction of
        :func:`_generated_severity_table`).
    :returns: Sorted agent-legible finding strings (empty when both surfaces
        are clean — no reintroduced literal, any-name dict, or inline
        conditional diverges from the generated table, and both still
        reference ``resolve_severity``).
    :raises babylon.sentinels.base.SentinelCheckError: If a source file is
        missing/unparseable, or a reintroduced named literal is assigned to
        something other than a dict literal.
    """
    table = generated_table if generated_table is not None else _generated_severity_table()
    findings: list[str] = []
    for label, path in (("web", web_path), ("archive", archive_path)):
        if "resolve_severity" not in referenced_names(path):
            findings.append(
                finding(
                    error_class="severity-single-source",
                    symbol="resolve_severity",
                    file=str(path),
                    line=0,
                    problem=(
                        f"the {label} surface no longer references resolve_severity at all — "
                        "severity has been re-forked away from the single source."
                    ),
                    remedy=(
                        "restore a delegation to babylon.models.event_severity.resolve_severity "
                        f"in this surface's classify function. {_WHY_SEVERITY_FORKED}"
                    ),
                )
            )
        for literal_name in _SEVERITY_LITERAL_NAMES:
            for key, tier in optional_dict_literal_str_items(path, literal_name).items():
                generated_tier = table.get(key)
                if generated_tier is None:
                    findings.append(
                        finding(
                            error_class="severity-single-source",
                            symbol=f"{literal_name}[{key!r}]",
                            file=str(path),
                            line=0,
                            problem=(
                                f"the {label} surface's local {literal_name} names key {key!r}, "
                                "which is not a value in the generated table (not a real "
                                "EventType.value, or the table is stale)."
                            ),
                            remedy=(
                                "delete the reintroduced literal dict and resolve severity "
                                f"through resolve_severity() instead. {_WHY_SEVERITY_FORKED}"
                            ),
                        )
                    )
                elif tier != generated_tier:
                    findings.append(
                        finding(
                            error_class="severity-single-source",
                            symbol=f"{literal_name}[{key!r}]",
                            file=str(path),
                            line=0,
                            problem=(
                                f"the {label} surface's local {literal_name}[{key!r}] = {tier!r} "
                                f"but the generated table resolves {key!r} to {generated_tier!r} "
                                "— single source violated."
                            ),
                            remedy=(
                                "delete the reintroduced literal dict and resolve severity "
                                f"through resolve_severity() instead. {_WHY_SEVERITY_FORKED}"
                            ),
                        )
                    )
        # Prong 3: a re-forked severity dict reintroduced under ANY OTHER
        # module-level name (review finding: the two prongs above only ever
        # watched the two retired names by construction, so a dict-shaped
        # re-fork simply renamed to dodge them was a silent miss).
        for var_name, items in all_dict_literal_str_items(path).items():
            if var_name in _SEVERITY_LITERAL_NAMES:
                continue  # already checked above -- do not double-report
            for key, tier in items.items():
                if tier not in _SEVERITY_TIER_VALUES:
                    continue  # not tier-shaped -- not a severity re-fork candidate
                divergence = _tier_divergence_finding(
                    label, f"{var_name}[{key!r}]", path, key, tier, table
                )
                if divergence is not None:
                    findings.append(divergence)
        # Prong 4: an inline per-member override folded straight into a
        # classify function's control flow, introducing NO dict literal at
        # all (review finding: neither dict-literal prong above can ever see
        # this vector by construction).
        for key, tier in conditional_literal_returns_by_enum_member(
            path, _SEVERITY_TIER_VALUES, EventType, "EventType"
        ).items():
            divergence = _tier_divergence_finding(
                label, f"inline branch resolving {key!r}", path, key, tier, table
            )
            if divergence is not None:
                findings.append(divergence)
    return sorted(findings)


_WHY_WALLCLOCK: Final[str] = (
    "WHY THIS FAILS: a call site inside a P-tier/hashed-artifact producer that reads real "
    "wall-clock time is a non-determinism smell -- even where the value is provably excluded "
    "from a byte-identity contract TODAY, a later refactor that folds it back into a compared "
    "field would silently reintroduce non-determinism while every existing unit test (which "
    "never exercises byte-identity across two runs) stays green."
)


def _confirm_wallclock_grounded(site: WallclockCallSite) -> None:
    """Confirm ``site``'s exact ``(line, wallclock_call)`` pair is still really present.

    A registry row citing a call site that has since been edited away, moved
    to a different line, or changed to a different wall-clock symbol must
    fail loud, not silently read as still-live -- mirrors
    :func:`_confirm_guard_grounded`/:func:`_confirm_stub_grounded`'s own
    "reject a stale row" posture.

    :param site: The row to ground.
    :raises babylon.sentinels.base.SentinelCheckError: If ``def_file`` is
        missing/unparseable, or ``(site.line, site.wallclock_call)`` is not
        among :func:`~babylon.sentinels._ast.wallclock_call_lines`'s output
        for ``def_file`` (the registry row is stale -- the call was moved,
        edited to a different wall-clock symbol, or removed entirely).
    """
    path = _REPO_ROOT / site.def_file
    calls = wallclock_call_lines(path)
    if (site.line, site.wallclock_call) not in calls:
        raise SentinelCheckError(
            f"{site.name!r}: no {site.wallclock_call}() call found at "
            f"{site.def_file}:{site.line} -- registry row is stale (the call was moved, "
            "edited to a different wall-clock symbol, or removed entirely)"
        )


def check_wallclock_call_sites(
    sites: tuple[WallclockCallSite, ...] = WALLCLOCK_REGISTRY,
    exemptions: tuple[SentinelExemption, ...] = WALLCLOCK_EXEMPTIONS,
) -> list[str]:
    """Red every live, non-exempt wall-clock read at a declared P-tier call site.

    T1.1 U7 (design §3.2 point 4): for each declared
    :class:`~babylon.sentinels.seam_algebra.registry.WallclockCallSite` row,
    first :func:`_confirm_wallclock_grounded` (the call really exists at the
    declared line, or this is an infrastructure failure), then check whether
    the site is exempted. A grounded, non-exempt row is, by definition, a live
    wall-clock read in a declared P-tier producer -- it reds.

    :param sites: Declared wall-clock call-site rows (defaults to the real
        :data:`~babylon.sentinels.seam_algebra.registry.WALLCLOCK_REGISTRY`;
        injectable so tests can supply a fixture site).
    :param exemptions: Dated, owner-approved rows holding a known wall-clock
        read open (defaults to the real
        :data:`~babylon.sentinels.seam_algebra.registry.WALLCLOCK_EXEMPTIONS`;
        injectable so the mutation test can prove a reverted exemption reds).
    :returns: Sorted agent-legible finding strings (empty when every declared
        site is exempted or absent).
    :raises babylon.sentinels.base.SentinelCheckError: If a declared site's
        file is missing/unparseable, or a declared ``(line, wallclock_call)``
        pair has gone stale.
    """
    findings: list[str] = []
    for site in sites:
        _confirm_wallclock_grounded(site)
        if is_exempt(("wallclock", site.name), exemptions):
            continue
        findings.append(
            finding(
                error_class="wallclock-call-site",
                symbol=site.wallclock_call,
                file=site.def_file,
                line=site.line,
                problem=(
                    f"{site.wallclock_call}() is read here, feeding {site.artifact} -- a "
                    "P-tier/hashed-artifact producer reading real wall-clock time."
                ),
                remedy=(
                    "hoist the timestamp out of the hashed/compared path (inject a clock "
                    "provider, or move the field to a declared non-deterministic-inputs-"
                    "shaped block excluded from any byte-identity comparison), or add a "
                    "dated SentinelExemption (key=('wallclock', name)) proving the field is "
                    f"already excluded — never a silent registry removal. {_WHY_WALLCLOCK}"
                ),
            )
        )
    return sorted(findings)


#: Any non-exempt disconnected subsystem, unsatisfied construct-entry gate,
#: live-consumer-fed-a-literal-over-a-registered-calculator, reforked severity
#: surface, OR a non-exempt wall-clock read at a declared P-tier call site is
#: a live defect.
_GATING_CHECKS: Final[tuple[LabelledCheck, ...]] = (
    ("disconnected-subsystem", check_disconnected_subsystems),
    ("gate-satisfaction", check_gate_satisfaction),
    ("severity-single-source", check_severity_single_source),
    ("stub-vs-calculator", check_stub_vs_calculator),
    ("wallclock-call-site", check_wallclock_call_sites),
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
        f"entry point(s); {len(SEAM_ALGEBRA_EXEMPTIONS)} disconnected subsystem(s), "
        f"{len(GATE_SATISFACTION_EXEMPTIONS)} unsatisfied gate(s), "
        f"{len(STUB_VS_CALCULATOR_EXEMPTIONS)} stub-vs-calculator site(s), and "
        f"{len(WALLCLOCK_EXEMPTIONS)} wall-clock call site(s) held open by a dated "
        "exemption; severity single-sourced across all "
        f"{len(EventType)} EventType member(s), 0 held open (T1.1 U6)."
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
