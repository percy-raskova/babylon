"""Declared invariants of the ``formula_registration`` sentinel.

Babylon's :class:`~babylon.engine.formula_registry.FormulaRegistry` is a
hot-swappable surface (Sprint 3 Central Committee DI) — every
``registry.register(key, formulas.symbol)`` call in
``engine/formula_registry.py`` is an IMPLIED public API: modding/testing code
may swap the callable, and a narrator/vault surface may resolve it by key. But
registration is not consumption. The Vol I value-production program's own
recon (``ai/_inbox/vol1-value-production-program-prompt.md`` §2d) found three
Fundamental-Theorem formulas registered and, at the time, invoked from
NOWHERE but their own registration/tests:
``calculate_labor_aristocracy_ratio``, ``is_labor_aristocracy``,
``calculate_consciousness_drift`` — the exact blind spot
:mod:`babylon.sentinels.inert` cannot see, because its own rule (b) counts
``formulas.calculate_labor_aristocracy_ratio`` (an ``ast.Attribute`` Load
node right there in the ``register(...)`` call) as a satisfied reference.
Registering a formula is not the same claim as USING it — this sentinel
draws that line explicitly.

Vol I's U2 (ADR117, ``feat(dialectics): the Fundamental Theorem, computed``)
wired two of the three into
:func:`~babylon.domain.dialectics.instances.value_form.compute_fundamental_theorem`:
``calculate_labor_aristocracy_ratio`` (direct call) and ``is_labor_aristocracy``
(imported under a LOCAL ALIAS, ``_is_labor_aristocracy`` — see
:mod:`babylon.sentinels.formula_registration.checks`'s alias-resolution note).
The third, ``calculate_consciousness_drift``, was deliberately left
unwired (ADR117's own recorded scope boundary: it is a rate/drift formula,
not part of the ``Wc``-vs-``Vc`` comparison U2 computed) and stays a real,
open gap — held GREEN via the one recorded exemption below, not silently
dropped.

This registry declares one closed, hand-curated invariant (mirrors
:mod:`babylon.sentinels.inert.registry`'s and :mod:`babylon.sentinels.
unconsumed.registry`'s own "closed, not merely additive" framing — this is
NOT an exhaustive audit of every ``FormulaRegistry.default()`` entry; it is
the three the Vol I recon actually found and named):

- :data:`DECLARED_FORMULAS` — a ``FormulaRegistry``-registered formula whose
  underlying ``symbol`` must have >=1 non-test production reference OTHER
  than its own ``engine/formula_registry.py`` registration call.

:data:`FORMULA_EXEMPTIONS` is the one narrow escape hatch (gate-governance
ruling, 2026-07-18 — the shared :class:`~babylon.sentinels.exemptions.
SentinelExemption` record every sentinel family uses).

Layer 0.5: imports nothing above :mod:`babylon.models` — in particular never
imports :mod:`babylon.engine` (the import-linter contract in
``pyproject.toml`` forbids it); ``engine/formula_registry.py`` is read as
SOURCE TEXT via :mod:`ast`, never imported, exactly like every sibling
sentinel treats the engine/domain files it polices.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, model_validator

from babylon.sentinels.exemptions import SentinelExemption

__all__ = [
    "DECLARED_FORMULAS",
    "FORMULA_EXEMPTIONS",
    "FORMULA_REGISTRY_FILE",
    "PRODUCTION_ROOTS",
    "DeclaredFormula",
]

#: Trees scanned for a production reference. Test files are EXCLUDED no
#: matter which root they live under (mirrors every sibling sentinel's own
#: ``is_test_source`` exclusion) — a test-only caller is exactly the false
#: liveness this gate exists to catch.
PRODUCTION_ROOTS: Final[tuple[str, ...]] = ("src", "web")

#: The one file whose OWN reference to ``formulas.<symbol>`` must never count
#: as a production call site — it is the registration act itself, not
#: downstream consumption. This is the precise fix for the gap this
#: sentinel's module docstring names: "the inert family sees the
#: registration as a satisfied reference."
FORMULA_REGISTRY_FILE: Final[str] = "src/babylon/engine/formula_registry.py"


class DeclaredFormula(BaseModel):
    """One ``FormulaRegistry``-registered formula: reachability required.

    Frozen and ``extra="forbid"`` so a malformed row fails loudly at import
    (Constitution III.11) rather than quietly at check time.

    :ivar name: The registry key (``FormulaRegistry.register``'s first
        argument, e.g. ``"labor_aristocracy_ratio"``).
    :ivar def_file: Repo-relative ``.py`` path defining ``symbol``.
    :ivar symbol: The bare module-level function name registered under
        ``name`` (e.g. ``"calculate_labor_aristocracy_ratio"``).
    :ivar what_it_computes: One-line description of the computed quantity.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    def_file: str
    symbol: str
    what_it_computes: str

    @model_validator(mode="after")
    def _validate_shape(self) -> DeclaredFormula:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If ``name``/``symbol`` is blank, or ``def_file``
            is not a ``.py`` path.
        """
        if not self.name.strip():
            raise ValueError("DeclaredFormula.name must be non-empty")
        if not self.symbol.strip():
            raise ValueError(f"{self.name!r}: symbol must be non-empty")
        if not self.def_file.endswith(".py"):
            raise ValueError(f"{self.name!r}: def_file must be a .py path, got {self.def_file!r}")
        return self


#: The three Fundamental-Theorem formulas the Vol I recon named
#: (``formula_registry.py``'s own "Fundamental Theorem formulas" comment
#: block, ``register()`` calls for ``labor_aristocracy_ratio``/
#: ``is_labor_aristocracy``/``consciousness_drift``). Verified against the
#: current tree (2026-07-21): the first two now have a genuine production
#: caller (``value_form.py::compute_fundamental_theorem``, U2/ADR117); the
#: third does not and is held open via :data:`FORMULA_EXEMPTIONS`.
DECLARED_FORMULAS: Final[tuple[DeclaredFormula, ...]] = (
    DeclaredFormula(
        name="labor_aristocracy_ratio",
        def_file="src/babylon/formulas/fundamental_theorem.py",
        symbol="calculate_labor_aristocracy_ratio",
        what_it_computes=("Wc/Vc labor-aristocracy ratio — the Fundamental Theorem's ratio form."),
    ),
    DeclaredFormula(
        name="is_labor_aristocracy",
        def_file="src/babylon/formulas/fundamental_theorem.py",
        symbol="is_labor_aristocracy",
        what_it_computes="Wc > Vc (strict) — the Fundamental Theorem's boolean form.",
    ),
    DeclaredFormula(
        name="consciousness_drift",
        def_file="src/babylon/formulas/fundamental_theorem.py",
        symbol="calculate_consciousness_drift",
        what_it_computes="dPsi/dt consciousness drift rate, including bifurcation.",
    ),
)

#: One recorded exemption (gate-governance ruling, 2026-07-21, Vol I U7).
#: ``calculate_consciousness_drift`` is registered and has a real REFERENCE
#: (``web/game/provenance.py``'s ``consciousness_drift`` ``MetricProvenance``
#: entry resolves it via ``FormulaRegistry.default().get("consciousness_drift")``)
#: but that reference only ever reads the formula's ``__doc__`` — see
#: ``provenance.py``'s own ``_consciousness_drift_value`` and its docstring
#: ("the formula cannot be honestly invoked without them" — its
#: ``solidarity_pressure``/``wage_change`` inputs are formula-default
#: literals, never real tick data). ADR117 (Vol I U2) recorded the same
#: finding and deliberately left the formula unwired: it is a rate/drift
#: formula, not part of the ``Wc``-vs-``Vc`` comparison U2 computed. This is
#: a real, open gap — wiring a genuine consumer is future work, not a
#: committed follow-up unit — held GREEN here rather than silently dropped.
FORMULA_EXEMPTIONS: Final[tuple[SentinelExemption, ...]] = (
    SentinelExemption(
        key=("formula", "consciousness_drift"),
        reason=(
            "calculate_consciousness_drift is registered and referenced by "
            "web/game/provenance.py's consciousness_drift MetricProvenance entry, but "
            "that reference (_consciousness_drift_value) only ever reads the formula's "
            "__doc__ -- it never invokes it for a value (see provenance.py's own comment: "
            "'the formula cannot be honestly invoked without them'). ADR117 (Vol I U2) "
            "independently recorded this as a deliberate scope boundary: consciousness_drift "
            "is a rate/drift formula, not part of the Wc-vs-Vc Fundamental Theorem comparison "
            "U2 wired via compute_fundamental_theorem. A real invoking consumer is possible "
            "future work, not a committed unit -- this exemption records the gap honestly "
            "rather than silently passing it."
        ),
        owner="Persephone Raskova",
        date="2026-07-21",
        tracking_task="N/A (ADR117 scope boundary; no committed remediation unit exists)",
    ),
)
