"""Declared invariants of the ``inert`` sentinel — reachable-from-production.

Babylon's dominant failure mode (2026-07-18 audit, 9 instances) is machinery
*built, tested in isolation, never connected*: a store with a real
``append``/writer method and passing unit tests, but ZERO production callers
— so every read answers "unknown" forever. The founding case is
:class:`~game.fog.ledger.IntelLedger`: 13 bridge call sites all read the same
frozen ``_EMPTY_INTEL_LEDGER`` constant, ``IntelEntry`` is never constructed
outside its own class body, and the tests that exercise ``append()`` are all
under ``tests/`` — a test-only caller is exactly the bug, not evidence
against it (Constitution III.10, "Earn-Its-Keep": a construct ships with a
LAW, a PREDICTION, or a COMPUTATION, never as vocabulary alone).

This registry declares two closed, hand-curated invariants (mirrors the
synthetic-data sentinel's own admission that its registry "is meant to stay
CLOSED, not merely additive" — see
:mod:`babylon.sentinels.synthetic.registry`):

- :data:`DECLARED_STORES` — a mutable/accumulator class whose writer
  method(s) must have >=1 non-test production caller.
- :data:`DECLARED_PRODUCERS` — a function/class that must have >=1 non-test
  production reference (a direct call, or an indirect one — passed into a
  registry dict, handed to ``getattr``, used as a callback — anything that is
  NOT merely an import alias or a name inside ``__all__``).

:data:`INERT_EXEMPTIONS` is the one narrow escape hatch: a declared construct
*known* to currently lack a production caller, kept un-gated only with an
owner-approved, dated, written reason — mirroring how
``GameDefines.epistemic_horizon.class_factor_default`` documents an explicit
fallback rather than a silent one. An exemption is not a shrug; it is a
recorded, revisitable decision.

Layer 0.5: imports nothing above :mod:`babylon.models`.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, model_validator

__all__ = [
    "DECLARED_PRODUCERS",
    "DECLARED_STORES",
    "INERT_EXEMPTIONS",
    "PRODUCTION_ROOTS",
    "DeclaredProducer",
    "DeclaredStore",
    "InertExemption",
]

#: Trees scanned for a production caller/reference. Test files are EXCLUDED
#: no matter which root they live under (``web/game/tests/*.py`` as much as
#: top-level ``tests/``) — see
#: :func:`babylon.sentinels.inert.checks.is_test_source`. A test-only caller
#: satisfying this check would silently reproduce the founding bug.
PRODUCTION_ROOTS: Final[tuple[str, ...]] = ("src", "web")


class DeclaredStore(BaseModel):
    """One declared mutable/accumulator store: writer reachability required.

    :ivar name: Stable identity for the store row (e.g. ``"intel_ledger"``).
    :ivar def_file: Repo-relative ``.py`` path defining ``class_name``.
    :ivar class_name: The store's class name (bare, module-level).
    :ivar writer_methods: The method name(s) that mutate/extend the store's
        state (for an immutable model this means "returns a NEW instance with
        the accumulator extended", e.g. ``IntelLedger.append``).
    :ivar what_it_stores: One-line description of the accumulated fact.
    :ivar failure_if_unwired: What silently degrades when no writer exists —
        cite the concrete observable (a field that reads "unknown" forever,
        a coefficient's ``model_validator`` going inert, etc).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    def_file: str
    class_name: str
    writer_methods: tuple[str, ...]
    what_it_stores: str
    failure_if_unwired: str

    @model_validator(mode="after")
    def _validate_shape(self) -> DeclaredStore:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If any identity field is blank, ``writer_methods``
            is empty, or ``def_file`` is not a ``.py`` path.
        """
        if not self.name.strip():
            raise ValueError("DeclaredStore.name must be non-empty")
        if not self.class_name.strip():
            raise ValueError(f"{self.name!r}: class_name must be non-empty")
        if not self.def_file.endswith(".py"):
            raise ValueError(f"{self.name!r}: def_file must be a .py path, got {self.def_file!r}")
        if not self.writer_methods:
            raise ValueError(f"{self.name!r}: writer_methods must be non-empty")
        return self


class DeclaredProducer(BaseModel):
    """One declared function/class that must be reachable from production.

    :ivar name: Stable identity for the producer row.
    :ivar def_file: Repo-relative ``.py`` path defining ``symbol``.
    :ivar symbol: The bare module-level function/class name.
    :ivar what_it_produces: One-line description of the computed value.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    def_file: str
    symbol: str
    what_it_produces: str

    @model_validator(mode="after")
    def _validate_shape(self) -> DeclaredProducer:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If any identity field is blank, or ``def_file``
            is not a ``.py`` path.
        """
        if not self.name.strip():
            raise ValueError("DeclaredProducer.name must be non-empty")
        if not self.symbol.strip():
            raise ValueError(f"{self.name!r}: symbol must be non-empty")
        if not self.def_file.endswith(".py"):
            raise ValueError(f"{self.name!r}: def_file must be a .py path, got {self.def_file!r}")
        return self


class InertExemption(BaseModel):
    """A declared store/producer known to lack a production caller, on record.

    Never a silent shrug: every row names the owner and the dated reasoning,
    exactly as ``GameDefines.epistemic_horizon.class_factor_default``
    documents an explicit fallback rather than an implicit one.

    :ivar name: The exempted row's ``DeclaredStore.name`` or
        ``DeclaredProducer.name``.
    :ivar reason: Why the gap is tolerated right now.
    :ivar owner: Who approved the exemption.
    :ivar date: ISO date the exemption was recorded.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    reason: str
    owner: str
    date: str

    @model_validator(mode="after")
    def _validate_shape(self) -> InertExemption:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If any field is blank.
        """
        for field_name in ("name", "reason", "owner", "date"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"InertExemption.{field_name} must be non-empty")
        return self


#: The two known "immutable accumulator" stores in ``src``/``web`` (verified
#: 2026-07-18 by :func:`babylon.sentinels.inert.checks.detect_accumulator_classes`
#: against the current tree — exactly these two match the shape, so the
#: growth check below has a known, narrow baseline).
DECLARED_STORES: Final[tuple[DeclaredStore, ...]] = (
    DeclaredStore(
        name="intel_ledger",
        def_file="web/game/fog/ledger.py",
        class_name="IntelLedger",
        writer_methods=("append",),
        what_it_stores=(
            "Append-only INVESTIGATE-resolution facts: (node_id, field_group, "
            "tick_observed, value_snapshot) — the record read_intel() ages into "
            "exact/approximate/unknown tiers."
        ),
        failure_if_unwired=(
            "With no production writer, every session's ledger is the shared frozen "
            "_EMPTY_INTEL_LEDGER constant (web/game/engine_bridge.py) — read_intel() "
            "can only ever answer tier='unknown', vision_approx stays permanently empty, "
            "and GameDefines.epistemic_horizon.intel_staleness_ticks / "
            "intel_unknown_ticks (plus their model_validator) are inert coefficients "
            "nothing ever consults. FIXED 2026-07-18 (Track 1/Task 9, landed by a "
            "concurrent agent on this same branch): web/game/fog/ledger.py::"
            "ledger_from_events builds a ledger via IntelLedger().append(...) in a loop, "
            "and engine_bridge.py calls ledger_from_events — this row now stays declared "
            "so a future regression (the writer deleted/renamed) is caught immediately."
        ),
    ),
    DeclaredStore(
        name="class_distribution",
        def_file="src/babylon/domain/economics/dynamics/types.py",
        class_name="ClassDistribution",
        writer_methods=("with_updated_dynamics",),
        what_it_stores=(
            "A county-year's five-class share distribution (bourgeoisie / "
            "petit-bourgeoisie / labor-aristocracy / proletariat / lumpenproletariat)."
        ),
        failure_if_unwired=(
            "If nothing called with_updated_dynamics(), the Class Dynamics Engine "
            "(feature 016) would never advance a county's class shares between years — "
            "the annual transition pipeline would silently replay year 0 forever."
        ),
    ),
)

#: The one seeded producer (Task B). ``compute_reification_buffer`` is the
#: audit's named example of a "zero production consumers" construct; this
#: sentinel's own static check found ONE real caller
#: (``src/babylon/engine/systems/ideology.py``) as of 2026-07-18 — see the
#: checks module's efficacy tests for the verified call site. That caller
#: writes the result into ``material_conditions["reification_buffer"]``,
#: which (separately, and NOT checked by this sentinel — see the checks
#: module docstring's Scope section) nothing downstream reads yet; that is
#: the "computed but never consumed" failure class, a declared but
#: not-yet-built sibling sentinel (see
#: ``ai/_inbox``/MEMORY.md "feedback-sentinel-every-error-class"), not this
#: one's "declared-but-uncalled producer" check.
DECLARED_PRODUCERS: Final[tuple[DeclaredProducer, ...]] = (
    DeclaredProducer(
        name="reification_buffer",
        def_file="src/babylon/formulas/consciousness_routing.py",
        symbol="compute_reification_buffer",
        what_it_produces=(
            "The commodity-fetishism reification buffer in [0, 1] from imperial rent "
            "and total variable capital (Spec 043 pipeline stage 3)."
        ),
    ),
)

#: No current exemptions: both DECLARED_STORES rows and the one
#: DECLARED_PRODUCERS row are checked as real gates and are currently clean
#: (the intel-ledger writer landed during the same session this sentinel was
#: built — see its row's ``failure_if_unwired`` for the caller that closed
#: the gap). This tuple exists so a future genuinely-irreducible gap has
#: somewhere honest to go, mirroring ``class_factor_default``'s "explicit,
#: never silent" fallback — never a bare ``continue`` in the check logic.
INERT_EXEMPTIONS: Final[tuple[InertExemption, ...]] = ()
