"""The unified construct → expected-consumer registry (Lawvere-1991 seam algebra).

T1.1 Unit 3 (``ai/_inbox/t11-seam-severity-design.md`` §3, §4 "U3"). Six sibling
sentinel families — :mod:`~babylon.sentinels.inert`, :mod:`~babylon.sentinels.
unconsumed`, :mod:`~babylon.sentinels.coupling`, :mod:`~babylon.sentinels.liveness`,
:mod:`~babylon.sentinels.vocabulary`, :mod:`~babylon.sentinels.dangling` — each ask a
narrow version of the SAME question ("does a real production file actually
reference this declared thing?") through six different bespoke registry shapes
(``DeclaredStore``/``DeclaredProducer``, ``DeclaredComputedField``,
``MeasurementDependency``, ``LivenessRow``, the ``NodeType``-driven vocabulary
scan, ``WatchedClass``/``WatchedReceiver``). This module gives that one question
ONE graph-theoretic home:

- **Ambient graph** ``G`` — every :class:`ConstructNode` (a declared, named
  production symbol) plus every :class:`ExpectedConsumer` edge (a
  ``read``/``call``/``import``/``publish`` claim that some file references that
  symbol), read live from the row data below.
- **Live subgraph** ``L`` — the constructs *transitively* reachable from
  :data:`PRODUCTION_ENTRY_POINTS` (the 30-system tick's own module, the verb
  resolvers, the projection/``observe()`` contract) by following edges whose
  target file is already known live, verified statically via
  :func:`babylon.sentinels._ast.referenced_names` (never an import, never an
  engine run — see :mod:`babylon.sentinels.seam_algebra.checks`).
- **Seam** ``∂L`` — the co-Heyting boundary: every declared construct NOT in
  ``L`` is a **disconnected subsystem** — a nonempty core severed from
  production, exactly the failure inert/unconsumed/liveness/etc. each detect
  in their own narrower vocabulary.

This registry is deliberately SMALL and load-bearing, not a re-scan of the
whole codebase: it ships the one real, verified 2-hop production chain
(:data:`PRODUCTION_ENTRY_POINTS` → ``consciousness_system`` → the inert
family's own ``reification_buffer`` producer) that proves transitive
reachability actually works end to end, plus the one currently-open
disconnected-subsystem finding this unit exists to close: **F-EC-1**
(``anisotropic_observation_error`` — day-one catch list, ``ai/_inbox/
PROGRAM_v1_0_0_playable_archive.md`` §A). Cross-validation that the unified
``∂L`` re-expresses (and loses no coverage against) the other five families'
OWN mutation-catching behaviour lives in
``tests/unit/sentinels/test_seam_algebra_cross_validation.py`` as small,
self-contained, real-file-grounded fixtures — see that module's docstring.

:data:`SEAM_ALGEBRA_EXEMPTIONS` is the same family-wide
:class:`~babylon.sentinels.exemptions.SentinelExemption` every sibling sentinel
uses (gate-governance ruling, 2026-07-18) — never a bespoke exemption class.

Layer 0.5: imports nothing above :mod:`babylon.models` (in fact nothing above
:mod:`babylon.sentinels` itself) — never the engine/topology/persistence/domain
(import-linter contract, ``pyproject.toml``).
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, model_validator

from babylon.sentinels.exemptions import SentinelExemption

__all__ = [
    "CALCULATOR_REGISTRY",
    "CONSTRUCT_REGISTRY",
    "EDGE_REGISTRY",
    "GATE_REGISTRY",
    "GATE_SATISFACTION_EXEMPTIONS",
    "GUARD_SHAPES",
    "ORIGIN_FAMILIES",
    "PRODUCTION_ENTRY_POINTS",
    "SEAM_ALGEBRA_EXEMPTIONS",
    "STUB_REGISTRY",
    "STUB_VS_CALCULATOR_EXEMPTIONS",
    "ConstructNode",
    "ExpectedConsumer",
    "GatedInput",
    "RegisteredCalculator",
    "StubConsumer",
]

#: The six legacy families this registry unifies, plus ``"native"`` for a
#: construct seeded directly by the seam-algebra family with no legacy-family
#: precedent (e.g. the day-one F-EC-1 catch-list witness). Closed set: a typo'd
#: family name fails the row's own validator loudly rather than silently
#: widening what "re-expresses a legacy family" means.
ORIGIN_FAMILIES: Final[frozenset[str]] = frozenset(
    {
        "inert",
        "unconsumed",
        "coupling",
        "liveness",
        "vocabulary",
        "dangling",
        "native",
    }
)

#: The four edge kinds the design names (§3.1): a construct's symbol may be
#: statically confirmed inside a consumer file because that file READS an
#: attribute/dict-key, CALLs it, IMPORTs it, or the construct PUBLISHES it for
#: something else to pick up. All four resolve identically today (a name
#: appearing in :func:`~babylon.sentinels._ast.referenced_names`'s output) —
#: the kind is a documentation/provenance tag, not (yet) a distinct check
#: rule; see the checks module's Scope note for why a uniform verification
#: rule is the correct day-one reduction.
_EDGE_KINDS: Final[frozenset[str]] = frozenset({"read", "call", "import", "publish"})

#: The declared production entry points — the roots :class:`ConstructNode`
#: reachability is measured FROM. Each is a real, architecturally-central file
#: (never a test, never a fixture):
#:
#: - the 30-system materialist-causality tick (``_DEFAULT_SYSTEMS``) — every
#:   System file it imports is, by construction, wired into the live game loop;
#: - the nine-verb player-action dispatcher (``VERB_RESOLVERS`` /
#:   ``resolve_player_action``) — the Action-phase's own entry point;
#: - the projection registry — Amendment V / II.8's ``observe()`` contract,
#:   the one declared read-seam every client (TUI, legacy web bridge) uses.
PRODUCTION_ENTRY_POINTS: Final[tuple[str, ...]] = (
    "src/babylon/engine/simulation_engine.py",
    "src/babylon/engine/actions/__init__.py",
    "src/babylon/projection/registry.py",
)


class ConstructNode(BaseModel):
    """One declared node in the ambient seam-algebra graph ``G``.

    :ivar name: Stable identity, unique within :data:`CONSTRUCT_REGISTRY`.
    :ivar def_file: Repo-relative ``.py`` path declaring/producing the construct.
    :ivar symbol: The bare production symbol name this construct denotes — a
        class name, a function name, an enum member, or a dict/attribute key —
        whatever string a consumer must reference to count as reaching it.
    :ivar origin_family: Which pre-existing sentinel family's vocabulary this
        construct re-expresses (one of :data:`ORIGIN_FAMILIES`); ``"native"``
        for a construct with no legacy-family precedent.
    :ivar material_relation: The material relation the construct carries
        (Aleksandrov Test) — why anything downstream should want it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    def_file: str
    symbol: str
    origin_family: str
    material_relation: str

    @model_validator(mode="after")
    def _validate_shape(self) -> ConstructNode:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If ``name``/``symbol``/``material_relation`` is
            blank, ``def_file`` is not a ``.py`` path, or ``origin_family`` is
            not one of :data:`ORIGIN_FAMILIES`.
        """
        for label, value in (
            ("name", self.name),
            ("symbol", self.symbol),
            ("material_relation", self.material_relation),
        ):
            if not value.strip():
                raise ValueError(f"ConstructNode.{label} must be non-empty")
        if not self.def_file.endswith(".py"):
            raise ValueError(f"{self.name!r}: def_file must be a .py path, got {self.def_file!r}")
        if self.origin_family not in ORIGIN_FAMILIES:
            raise ValueError(
                f"{self.name!r}: origin_family {self.origin_family!r} not in "
                f"{sorted(ORIGIN_FAMILIES)!r}"
            )
        return self


class ExpectedConsumer(BaseModel):
    """One declared edge: ``construct_name``'s symbol is expected inside ``consumer_file``.

    :ivar construct_name: The :attr:`ConstructNode.name` this edge originates from
        — must resolve against :data:`CONSTRUCT_REGISTRY` (validated at
        collection time, see :func:`_validate_edges_resolve`, mirroring
        :mod:`babylon.sentinels.vocabulary.registry`'s own
        ``_validate_member_classes_resolve`` pattern).
    :ivar consumer_file: Repo-relative ``.py`` path expected to reference the
        construct's symbol.
    :ivar edge_kind: One of :data:`_EDGE_KINDS` — ``read``/``call``/``import``/
        ``publish``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    construct_name: str
    consumer_file: str
    edge_kind: str

    @model_validator(mode="after")
    def _validate_shape(self) -> ExpectedConsumer:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If ``construct_name`` is blank, ``consumer_file`` is
            not a ``.py`` path, or ``edge_kind`` is not one of
            :data:`_EDGE_KINDS`.
        """
        if not self.construct_name.strip():
            raise ValueError("ExpectedConsumer.construct_name must be non-empty")
        if not self.consumer_file.endswith(".py"):
            raise ValueError(
                f"{self.construct_name!r}: consumer_file must be a .py path, "
                f"got {self.consumer_file!r}"
            )
        if self.edge_kind not in _EDGE_KINDS:
            raise ValueError(
                f"{self.construct_name!r}: edge_kind {self.edge_kind!r} not in "
                f"{sorted(_EDGE_KINDS)!r}"
            )
        return self


#: The unified, hand-curated node set. Deliberately small (§ module docstring):
#: one real 2-hop chain proving transitive reachability, plus the one day-one
#: disconnected-subsystem witness (F-EC-1).
CONSTRUCT_REGISTRY: Final[tuple[ConstructNode, ...]] = (
    ConstructNode(
        name="consciousness_system",
        def_file="src/babylon/engine/systems/ideology.py",
        symbol="ConsciousnessSystem",
        origin_family="native",
        material_relation=(
            "One of the 30 materialist-causality Systems (CONSEQUENCE phase, "
            "position 17) `_DEFAULT_SYSTEMS` runs every tick — the production "
            "bridge from the tick-loop entry point into the ideology domain, "
            "and the second hop of this registry's one real transitive chain."
        ),
    ),
    ConstructNode(
        name="reification_buffer_producer",
        def_file="src/babylon/formulas/consciousness_routing.py",
        symbol="compute_reification_buffer",
        origin_family="inert",
        material_relation=(
            "Commodity-fetishism reification buffer in [0, 1] "
            "(|Phi| / (|Phi| + v + eps)) — re-expresses "
            "babylon.sentinels.inert.registry.DECLARED_PRODUCERS's "
            "'reification_buffer' row (the inert family's own founding "
            "producer-reachability case) as one node of this unified graph, "
            "reached transitively via consciousness_system -> "
            "simulation_engine.py."
        ),
    ),
    ConstructNode(
        name="anisotropic_observation_error",
        def_file="src/babylon/domain/bifurcation/consciousness.py",
        symbol="anisotropic_observation_error",
        origin_family="native",
        material_relation=(
            "Anisotropic per-axis observation-noise formula (FR-009) — "
            "perturbs a TernaryConsciousness position so the state's estimate "
            "of revolutionary consciousness (r) carries ~3x the noise of the "
            "legal/fascist (l/f) split, modelling that r is hidden from "
            "surveillance. F-EC-1 (the T1.1 day-one seam-algebra catch list, "
            "ai/_inbox/PROGRAM_v1_0_0_playable_archive.md §A): zero production "
            "callers exist anywhere in src/ or web/ — only "
            "tests/unit/bifurcation/test_consciousness.py exercises it — so "
            "this node is DELIBERATELY given no EDGE_REGISTRY entry: it is the "
            "disconnected-subsystem witness this unit's mutation test proves "
            "the boundary computation catches."
        ),
    ),
)

#: The unified, hand-curated edge set. ``anisotropic_observation_error`` has NO
#: edge here by construction (see its ConstructNode docstring) — that absence
#: IS the disconnected-subsystem finding F-EC-1.
EDGE_REGISTRY: Final[tuple[ExpectedConsumer, ...]] = (
    ExpectedConsumer(
        construct_name="consciousness_system",
        consumer_file="src/babylon/engine/simulation_engine.py",
        edge_kind="import",
    ),
    ExpectedConsumer(
        construct_name="reification_buffer_producer",
        consumer_file="src/babylon/engine/systems/ideology.py",
        edge_kind="call",
    ),
)


def _validate_edges_resolve(
    constructs: tuple[ConstructNode, ...], edges: tuple[ExpectedConsumer, ...]
) -> None:
    """Every edge's ``construct_name`` must name a real :data:`CONSTRUCT_REGISTRY` row.

    Mirrors :mod:`babylon.sentinels.vocabulary.registry`'s own
    ``_validate_member_classes_resolve`` — a typo'd or stale ``construct_name``
    reference would silently make an edge inert (it would never match any
    node during the boundary computation), which is precisely the class of
    silent drift this whole family exists to forbid.

    :param constructs: The declared node rows to resolve against.
    :param edges: The declared edge rows to check.
    :raises ValueError: If any edge names a construct absent from ``constructs``.
    """
    known = {node.name for node in constructs}
    unknown = sorted({edge.construct_name for edge in edges if edge.construct_name not in known})
    if unknown:
        raise ValueError(
            f"ExpectedConsumer row(s) name unknown construct(s): {unknown!r} — not "
            f"present in CONSTRUCT_REGISTRY ({sorted(known)!r})"
        )


_validate_edges_resolve(CONSTRUCT_REGISTRY, EDGE_REGISTRY)

#: The three construct-entry guard shapes T1.1 U4's gate-satisfaction check
#: recognizes (design §3.2 point 1): ``context_get`` (``context.get("K")``),
#: ``services_attr_none`` (``services.X is None``), ``context_hasattr`` (the
#: ``X if hasattr(obj, "X") else None`` optional-attribute form). Closed set
#: for the same reason :data:`ORIGIN_FAMILIES`/``_EDGE_KINDS`` are: a typo'd
#: shape fails a :class:`GatedInput` row loudly rather than silently widening
#: what this check verifies. The fourth guard shape the design also names --
#: an OPTIONAL kwarg silently omitted at a call site (the ``defines=``
#: passthrough pattern :mod:`babylon.sentinels.defines_passthrough` already
#: polices via ``_ast.optional_defines_param_index`` /
#: ``_ast.calls_missing_keyword_or_positional_arg``) -- has no day-one witness
#: among F-1/F-2 (both are ``services_attr_none``/``context_get``/
#: ``context_hasattr`` shaped) and is deliberately NOT populated here; it is
#: named future scope for the LODES-kwargs / transition_engine / reserve-army
#: seed findings the design's "Closes:" list also names (§3.2 point 1),
#: promoted in a later pass rather than force-fit against witnesses that do
#: not exhibit it.
GUARD_SHAPES: Final[frozenset[str]] = frozenset(
    {"context_get", "services_attr_none", "context_hasattr"}
)


class GatedInput(BaseModel):
    """One construct-entry guard: an early-return that fires when ``gated_input`` is absent.

    :ivar name: Stable identity, unique within :data:`GATE_REGISTRY`.
    :ivar guard_file: Repo-relative ``.py`` path containing the guard.
    :ivar guard_shape: One of :data:`GUARD_SHAPES` -- which AST pattern
        grounds this row (see :mod:`babylon.sentinels.seam_algebra.checks`'s
        ``_confirm_guard_grounded``).
    :ivar gated_input: The context key / services attribute name the guard
        tests for absence.
    :ivar supplier_files: Repo-relative ``.py`` path(s) hand-declared as a
        genuine, unconditional production supplier of ``gated_input``. Empty
        -- the deliberate "no production supplier exists" claim (F-1's own
        witness) -- reds unless a dated :class:`SentinelExemption` holds it
        open. A CONDITIONAL supplier (wired only inside an ``if`` branch
        elsewhere, e.g. ``distribution_calculator`` only when a headless
        run's ``scope_fips`` is truthy) is deliberately left undeclared here
        -- this check does not attempt control-flow analysis (mirrors every
        other ``_ast`` helper's documented "cannot resolve without
        value-flow analysis" boundary), so a conditionally-wired input reads
        honestly as "no unconditional supplier", never as a false-clean pass.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    guard_file: str
    guard_shape: str
    gated_input: str
    supplier_files: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate_shape(self) -> GatedInput:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If ``name``/``gated_input`` is blank, ``guard_file``
            (or any ``supplier_files`` entry) is not a ``.py`` path, or
            ``guard_shape`` is not one of :data:`GUARD_SHAPES`.
        """
        for label, value in (("name", self.name), ("gated_input", self.gated_input)):
            if not value.strip():
                raise ValueError(f"GatedInput.{label} must be non-empty")
        if not self.guard_file.endswith(".py"):
            raise ValueError(
                f"{self.name!r}: guard_file must be a .py path, got {self.guard_file!r}"
            )
        if self.guard_shape not in GUARD_SHAPES:
            raise ValueError(
                f"{self.name!r}: guard_shape {self.guard_shape!r} not in {sorted(GUARD_SHAPES)!r}"
            )
        for supplier_file in self.supplier_files:
            if not supplier_file.endswith(".py"):
                raise ValueError(
                    f"{self.name!r}: supplier_files entry must be a .py path, got {supplier_file!r}"
                )
        return self


#: The unified, hand-curated gate set -- T1.1 U4's day-one witnesses.
#:
#: - ``run_audit_session_id`` is **F-1**: ``SimulationEngine._run_audit``
#:   early-returns "skip silently" when ``context.session_id`` is absent
#:   (``engine/simulation_engine.py:227-230``). No production caller ever
#:   sets the ATTRIBUTE ``context.session_id`` -- the headless runner sets
#:   ``context["session_id"]`` (a dict-style write, routed by
#:   ``TickContext.__setitem__`` into ``persistent_data``, not the attribute
#:   ``hasattr`` tests), so the guard can never see it either way. Empty
#:   ``supplier_files``: verified, no attribute-style supplier anywhere.
#: - ``financial_layer_distribution_calculator`` is **F-2**'s headline
#:   example: ``_compute_financial_layer`` returns ``county_states``
#:   unchanged when ``services.distribution_calculator is None``
#:   (``domain/economics/tick/system/__init__.py:1439``). The only
#:   production wiring (``domain/economics/factory.py::
#:   create_financial_services``, invoked from the headless runner's
#:   ``_build_economics_overrides``) is CONDITIONAL on a truthy
#:   ``scope_fips`` -- not a supplier this check declares (see
#:   :class:`GatedInput` docstring). Empty ``supplier_files``.
#: - ``vol2_circulation_vol2_step`` is **F-2**'s other half: ``ImperialRent
#:   System._invoke_vol2_circulation_if_wired`` returns silently when
#:   ``context.get("vol2_step")`` is ``None`` (``engine/systems/
#:   economic.py:174-178``). Verified: zero production writers of
#:   ``context["vol2_step"]``/``context.persistent_data["vol2_step"]``
#:   anywhere in ``src/`` or ``web/`` -- the sibling
#:   ``_invoke_phi_distribution_if_wired`` guard on the SAME line range
#:   (``session_id``/``boundary_flow_register``/``external_nodes_phi``/
#:   ``county_exposure_by_external``) is, by contrast, genuinely wired by the
#:   headless runner's ``_run_tick_once`` (conditionally, but for the
#:   standard tick-loop path) and is correctly NOT flagged here. Empty
#:   ``supplier_files``.
#: - ``tick_dynamics_melt_calculator`` is the POSITIVE control: ``services.
#:   melt_calculator is None`` (``domain/economics/tick/system/
#:   __init__.py:174``) IS unconditionally wired by the headless runner's
#:   ``_build_economics_overrides`` (``overrides["melt_calculator"] = melt``,
#:   ``engine/headless_runner/runner.py:1055``, whenever a session factory is
#:   supplied -- the one production path this sentinel's declared
#:   ``supplier_files`` name) -- proves the check recognizes a genuinely
#:   satisfied gate, not just a red-everything scanner.
GATE_REGISTRY: Final[tuple[GatedInput, ...]] = (
    GatedInput(
        name="run_audit_session_id",
        guard_file="src/babylon/engine/simulation_engine.py",
        guard_shape="context_hasattr",
        gated_input="session_id",
        supplier_files=(),
    ),
    GatedInput(
        name="financial_layer_distribution_calculator",
        guard_file="src/babylon/domain/economics/tick/system/__init__.py",
        guard_shape="services_attr_none",
        gated_input="distribution_calculator",
        supplier_files=(),
    ),
    GatedInput(
        name="vol2_circulation_vol2_step",
        guard_file="src/babylon/engine/systems/economic.py",
        guard_shape="context_get",
        gated_input="vol2_step",
        supplier_files=(),
    ),
    GatedInput(
        name="tick_dynamics_melt_calculator",
        guard_file="src/babylon/domain/economics/tick/system/__init__.py",
        guard_shape="services_attr_none",
        gated_input="melt_calculator",
        supplier_files=("src/babylon/engine/headless_runner/runner.py",),
    ),
)

#: F-1 + F-2's day-one dispositions (design §9 item 4: T1.1 defaults to
#: exemption-with-rationale over a raise/loud-log behavior change, since this
#: lane is Amendment-S read-only projection/diagnostics -- it may not feed
#: back into physics or change engine behavior). The BD-owed raise-vs-exempt
#: call per §9 item 4 is left open, same as F-EC-1's disposition above.
GATE_SATISFACTION_EXEMPTIONS: Final[tuple[SentinelExemption, ...]] = (
    SentinelExemption(
        key=("gate", "run_audit_session_id"),
        reason=(
            "F-1: SimulationEngine._run_audit (engine/simulation_engine.py:227-230) "
            "early-returns 'skip silently' when context.session_id is absent. "
            "Verified: no production caller ever sets the ATTRIBUTE "
            "context.session_id -- the headless runner's _run_tick_once sets "
            "context['session_id'] instead (a dict-style write TickContext."
            "__setitem__ routes into persistent_data, never the pydantic "
            "attribute the hasattr() guard tests), so the two never meet "
            "regardless of whether session_id is 'wired' upstream. Per the "
            "T1.1 default (design §9 item 4), held open as an exemption "
            "rather than this lane changing engine behavior (a raise/loud-log "
            "fix touches _run_audit's production control flow, out of scope "
            "for a read-only G-of-P diagnostics lane, Amendment-S tripwire)."
        ),
        owner="Persephone Raskova",
        date="2026-07-21",
        tracking_task="N/A (BD-owed raise-vs-exempt disposition per design "
        "ai/_inbox/t11-seam-severity-design.md §9 item 4)",
    ),
    SentinelExemption(
        key=("gate", "financial_layer_distribution_calculator"),
        reason=(
            "F-2 (headline example): _compute_financial_layer "
            "(domain/economics/tick/system/__init__.py:1439) returns "
            "county_states unchanged when services.distribution_calculator "
            "is None. The one production wiring path "
            "(domain/economics/factory.py::create_financial_services, via "
            "the headless runner's _build_economics_overrides) is CONDITIONAL "
            "on a truthy scope_fips -- a run without county scoping silently "
            "skips the whole Volume III financial layer with no log. Per the "
            "T1.1 default (design §9 item 4: 'loud one-time log OR exemption'), "
            "held open as an exemption -- the loud-log alternative is a "
            "production code change out of scope for this Amendment-S "
            "read-only lane."
        ),
        owner="Persephone Raskova",
        date="2026-07-21",
        tracking_task="N/A (BD-owed raise-vs-exempt disposition per design "
        "ai/_inbox/t11-seam-severity-design.md §9 item 4)",
    ),
    SentinelExemption(
        key=("gate", "vol2_circulation_vol2_step"),
        reason=(
            "F-2 (vol2/Phi sub-stage half): ImperialRentSystem."
            "_invoke_vol2_circulation_if_wired (engine/systems/economic.py:"
            "174-178) returns silently when context.get('vol2_step') (also "
            "boundary_flow_register/session_id/simulated_year) is absent. "
            "Verified: zero production writers of context['vol2_step'] "
            "anywhere in src/ or web/ -- the Vol II Circulation sub-stage "
            "(spec 063 T019) has never been wired into the headless runner's "
            "context construction; the sibling _invoke_phi_distribution_if_"
            "wired guard on the adjacent lines IS wired (runner.py:431-439) "
            "and is correctly not flagged. Per the T1.1 default (design §9 "
            "item 4), held open as an exemption -- wiring vol2_step is a "
            "production change (the vol2-circulation-program-staged effort) "
            "out of scope for this read-only diagnostics lane."
        ),
        owner="Persephone Raskova",
        date="2026-07-21",
        tracking_task="N/A (BD-owed raise-vs-exempt disposition per design "
        "ai/_inbox/t11-seam-severity-design.md §9 item 4)",
    ),
)


class RegisteredCalculator(BaseModel):
    """One real production calculator computing a specific value type from inputs.

    T1.1 Unit 5 (design §3.2 point 2): the calculator-side half of the
    stub-vs-calculator pair. A row here is the positive claim "a real function
    exists that computes this value from real inputs" — grounded at
    check-run time by :mod:`babylon.sentinels.seam_algebra.checks`'s
    ``_confirm_calculator_grounded`` (the function is really defined at
    module level in ``def_file``, and its own ``->`` return annotation really
    names ``produces``).

    :ivar name: Stable identity, unique within :data:`CALCULATOR_REGISTRY`.
    :ivar def_file: Repo-relative ``.py`` path declaring the calculator.
    :ivar symbol: The calculator's bare function name.
    :ivar produces: The bare name of the type the calculator's return
        annotation names — grounds the claim "this IS the calculator for
        exactly this stubbed value", never just a same-named coincidence.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    def_file: str
    symbol: str
    produces: str

    @model_validator(mode="after")
    def _validate_shape(self) -> RegisteredCalculator:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If ``name``/``symbol``/``produces`` is blank, or
            ``def_file`` is not a ``.py`` path.
        """
        for label, value in (
            ("name", self.name),
            ("symbol", self.symbol),
            ("produces", self.produces),
        ):
            if not value.strip():
                raise ValueError(f"RegisteredCalculator.{label} must be non-empty")
        if not self.def_file.endswith(".py"):
            raise ValueError(f"{self.name!r}: def_file must be a .py path, got {self.def_file!r}")
        return self


class StubConsumer(BaseModel):
    """One live production call site fed a literal instead of a computed value.

    T1.1 Unit 5 (design §3.2 point 2): the consumer-side half of the
    stub-vs-calculator pair. A row here is the positive claim "this
    production call site constructs ``consumer_symbol`` with a bare literal
    for ``stub_field``, even though ``calculator_name`` is a registered
    calculator for exactly that value" — grounded at check-run time by
    :mod:`babylon.sentinels.seam_algebra.checks`'s ``_confirm_stub_grounded``
    (the literal call really appears in ``consumer_file``, via
    :func:`~babylon.sentinels._ast.literal_keyword_call_lines`).

    :ivar name: Stable identity, unique within :data:`STUB_REGISTRY`.
    :ivar consumer_file: Repo-relative ``.py`` path containing the stub
        construction.
    :ivar consumer_symbol: The bare type/class name constructed at the stub
        site (e.g. ``"ReproductionBalance"``).
    :ivar stub_field: The keyword field fed a literal/neutral constant instead
        of a value the cited calculator would compute.
    :ivar calculator_name: The :attr:`RegisteredCalculator.name` this field
        SHOULD be sourced from — must resolve against
        :data:`CALCULATOR_REGISTRY` (validated at collection time, see
        :func:`_validate_stub_calculators_resolve`, mirroring
        :func:`_validate_edges_resolve`'s own pattern).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    consumer_file: str
    consumer_symbol: str
    stub_field: str
    calculator_name: str

    @model_validator(mode="after")
    def _validate_shape(self) -> StubConsumer:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If ``name``/``consumer_symbol``/``stub_field``/
            ``calculator_name`` is blank, or ``consumer_file`` is not a ``.py``
            path.
        """
        for label, value in (
            ("name", self.name),
            ("consumer_symbol", self.consumer_symbol),
            ("stub_field", self.stub_field),
            ("calculator_name", self.calculator_name),
        ):
            if not value.strip():
                raise ValueError(f"StubConsumer.{label} must be non-empty")
        if not self.consumer_file.endswith(".py"):
            raise ValueError(
                f"{self.name!r}: consumer_file must be a .py path, got {self.consumer_file!r}"
            )
        return self


#: The unified, hand-curated production-calculator set (T1.1 U5). Deliberately
#: ONE row today — the founding-case calculator this unit's day-one witness
#: cites (design §3.2 point 2's "Day-one witness"). Like
#: :data:`CONSTRUCT_REGISTRY`/:data:`GATE_REGISTRY`, this is a small,
#: hand-curated registry that grows as later units register more
#: stub-vs-calculator pairs — deliberately NEVER a full-codebase auto-scan
#: across every Pydantic-model construction site (see
#: :mod:`babylon.sentinels.seam_algebra.checks`'s module docstring for why
#: that scoping IS the anti-false-positive heuristic, not an omission).
CALCULATOR_REGISTRY: Final[tuple[RegisteredCalculator, ...]] = (
    RegisteredCalculator(
        name="check_simple_reproduction",
        def_file="src/babylon/domain/economics/circulation/reproduction.py",
        symbol="check_simple_reproduction",
        produces="ReproductionBalance",
    ),
)

#: The unified, hand-curated stub-consumer set — T1.1 U5's day-one witness.
#:
#: ``reproduction_balance_default_stub`` is the founding case (design §3.2
#: point 2; recon detail: ``ai/_inbox/vol2-circulation-engine-program-
#: prompt.md`` §2c, "worse than inert: the live consumer is fed a lying
#: stub"): ``domain/economics/tick/system/__init__.py:1378-1382`` hardcodes
#: ``ReproductionBalance(condition_met=True, gap=0.0, interpretation="Default
#: reproduction balance")`` and feeds it straight into the LIVE
#: ``assess_circulation_crisis(...)`` call a few lines below — every county's
#: reproduction-crisis flag reads permanently "balanced" regardless of that
#: county's real departmental proportions, because the registered calculator
#: for exactly this value (``check_simple_reproduction``, the ``I(v+s) =
#: IIc`` law) is never called from production anywhere in ``src/`` or
#: ``web/`` — only ``tests/unit/economics/circulation/test_reproduction.py``
#: exercises it.
STUB_REGISTRY: Final[tuple[StubConsumer, ...]] = (
    StubConsumer(
        name="reproduction_balance_default_stub",
        consumer_file="src/babylon/domain/economics/tick/system/__init__.py",
        consumer_symbol="ReproductionBalance",
        stub_field="condition_met",
        calculator_name="check_simple_reproduction",
    ),
)


def _validate_stub_calculators_resolve(
    calculators: tuple[RegisteredCalculator, ...], stubs: tuple[StubConsumer, ...]
) -> None:
    """Every stub row's ``calculator_name`` must name a real :data:`CALCULATOR_REGISTRY` row.

    Mirrors :func:`_validate_edges_resolve` — a typo'd or stale
    ``calculator_name`` reference would silently make a stub row uncheckable
    (or resolve against the wrong calculator), the same class of silent drift
    this whole family forbids.

    :param calculators: The declared calculator rows to resolve against.
    :param stubs: The declared stub-consumer rows to check.
    :raises ValueError: If any stub names a calculator absent from ``calculators``.
    """
    known = {calc.name for calc in calculators}
    unknown = sorted({stub.calculator_name for stub in stubs if stub.calculator_name not in known})
    if unknown:
        raise ValueError(
            f"StubConsumer row(s) name unknown calculator(s): {unknown!r} — not present "
            f"in CALCULATOR_REGISTRY ({sorted(known)!r})"
        )


_validate_stub_calculators_resolve(CALCULATOR_REGISTRY, STUB_REGISTRY)

#: The one day-one exemption: the ReproductionBalance stub (design §3.2 point
#: 2 / §9 item 4's raise-vs-exempt default). Wiring the REAL fix — computing
#: genuine Dept I/II ``DepartmentRow(c, v, s)`` rows from county circulation
#: data and calling ``check_simple_reproduction(...)`` for real — is the Vol
#: II circulation-engine program's own opening task
#: (``ai/_inbox/vol2-circulation-engine-program-prompt.md`` §2c), gated
#: behind that program's own sequencing gates (Vol III merge + the parquet
#: cutover). It would also change ``assess_circulation_crisis``'s real
#: inputs — i.e. change simulation math, which would break the
#: ``qa:regression`` byte-identical contract this Amendment-S read-only
#: diagnostics lane must never touch by construction. Held open here per the
#: T1.1 default (exemption-with-rationale) rather than this lane patching
#: production physics unilaterally.
STUB_VS_CALCULATOR_EXEMPTIONS: Final[tuple[SentinelExemption, ...]] = (
    SentinelExemption(
        key=("stub", "reproduction_balance_default_stub"),
        reason=(
            "domain/economics/tick/system/__init__.py:1378-1382 hardcodes "
            "ReproductionBalance(condition_met=True, gap=0.0, "
            "interpretation='Default reproduction balance') and feeds it "
            "straight into the LIVE assess_circulation_crisis(...) call a "
            "few lines below -- every county's reproduction-crisis flag "
            "reads permanently 'balanced' regardless of real departmental "
            "proportions. The registered calculator (check_simple_"
            "reproduction, the I(v+s) = IIc law, circulation/reproduction.py"
            ":71) is never called from production anywhere in src/ or web/ "
            "-- only tests/unit/economics/circulation/test_reproduction.py "
            "exercises it. Wiring the real fix requires computing genuine "
            "Dept I/II DepartmentRow(c, v, s) rows from county circulation "
            "data -- new physics plumbing that is the Vol II "
            "circulation-engine program's own opening task "
            "(ai/_inbox/vol2-circulation-engine-program-prompt.md §2c, "
            "'worse than inert: the live consumer is fed a lying stub'), "
            "gated behind the Vol III merge + parquet cutover sequencing "
            "that program declares, and would change assess_circulation_"
            "crisis's real inputs (the tick hash) -- out of scope for this "
            "Amendment-S read-only diagnostics lane."
        ),
        owner="Persephone Raskova",
        date="2026-07-21",
        tracking_task="N/A (tracked by the staged Vol II circulation-engine "
        "program, ai/_inbox/vol2-circulation-engine-program-prompt.md §2c; "
        "no standalone ticket opened for this stub alone)",
    ),
)

#: The one day-one exemption: F-EC-1. Per the T1.1 default (design §9 item 3/4
#: — exemption-with-rationale unless the owner prefers otherwise), this holds
#: the finding open rather than unilaterally retiring or wiring the formula —
#: that choice (retire vs. wire as the R-EC-2 "observation-noise fifth
#: stratum") is a named BD-owed question, not this lane's to make.
SEAM_ALGEBRA_EXEMPTIONS: Final[tuple[SentinelExemption, ...]] = (
    SentinelExemption(
        key=("construct", "anisotropic_observation_error"),
        reason=(
            "anisotropic_observation_error (FR-009) has zero production callers "
            "in src/ or web/ -- only tests/unit/bifurcation/test_consciousness.py "
            "exercises it. This is F-EC-1, the T1.1 day-one seam-algebra catch "
            "list's disconnected-subsystem witness. Whether to retire it or wire "
            "it as the R-EC-2 'observation-noise fifth stratum' is a BD-owed "
            "disposition (design doc ai/_inbox/t11-seam-severity-design.md §9 "
            "item 3); held open here per the T1.1 default (exemption-with-"
            "rationale) rather than this lane choosing unilaterally."
        ),
        owner="Persephone Raskova",
        date="2026-07-21",
        tracking_task="N/A (BD-owed R-EC-2 disposition -- retire vs. wire as "
        "observation-noise fifth stratum; no tracking ticket opened yet)",
    ),
)
