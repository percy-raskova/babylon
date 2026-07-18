"""Declared invariants of the ``unconsumed`` sentinel — computed values must be read.

Distinct failure mode from :mod:`babylon.sentinels.inert`. Inert asks "is this
producer FUNCTION ever called from production code?" This sentinel asks a
narrower, downstream question about a function that IS called: "is the VALUE
it writes ever READ by anything else?" A producer can pass the inert check
(it has a real caller) while its result rots unread — a computation with a
heartbeat but no listener.

Founding instance (Track 1 audit, 2026-07-18):
:func:`~babylon.formulas.consciousness_routing.compute_reification_buffer` IS
called — ``engine/systems/ideology.py::ConsciousnessSystem.step`` invokes it
every tick a social_class node is processed, and writes the result onto
``material_conditions["reification_buffer"]`` via ``graph.update_node(...)``
(satisfies :mod:`babylon.sentinels.inert`'s producer-reachability rule
cleanly). But grep-verified against the current tree: no file in ``src`` or
``web`` ever reads the ``"reification_buffer"`` key back off a node or a
:class:`~babylon.models.components.material_conditions.MaterialConditionsBuffer`
instance — the reification buffer is computed, stored, and then never
consulted by any consciousness-routing, narrative, or serialization code.
Constitution III.10 (Earn-Its-Keep) requires a construct ship with a LAW, a
PREDICTION, or a COMPUTATION something ELSE consumes — a value nothing reads
is vocabulary with a heartbeat, not a working part.

This registry declares one closed, hand-curated invariant (mirrors
:mod:`babylon.sentinels.inert.registry`'s own "closed, not merely additive"
framing):

- :data:`DECLARED_COMPUTED_FIELDS` — a dict key a production write-site
  stamps onto a node/model, that must have >=1 non-test production READ
  site (a subscript or ``.get()``/``.pop()`` access naming that exact key).

:data:`UNCONSUMED_EXEMPTIONS` is the one narrow escape hatch — an
owner-approved, dated, written reason a declared field is *known* to
currently lack a consumer, mirroring
:data:`babylon.sentinels.inert.registry.INERT_EXEMPTIONS`. As of this
writing it is deliberately EMPTY: the one declared row
(``reification_buffer``) is a real, unremediated gap this sentinel is
built to surface loudly, not paper over — see the module's own liveness
test tier for the current (RED) finding.

Layer 0.5: imports nothing above :mod:`babylon.models`.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, model_validator

__all__ = [
    "DECLARED_COMPUTED_FIELDS",
    "PRODUCTION_ROOTS",
    "UNCONSUMED_EXEMPTIONS",
    "DeclaredComputedField",
    "UnconsumedExemption",
]

#: Trees scanned for a production READ site. Test files are EXCLUDED no
#: matter which root they live under — see
#: :func:`babylon.sentinels.unconsumed.checks.is_test_source`. A test-only
#: reader satisfying this check would silently reproduce the same "closed
#: loop, no external referent" bug the inert sentinel already guards against
#: for writers.
PRODUCTION_ROOTS: Final[tuple[str, ...]] = ("src", "web")


class DeclaredComputedField(BaseModel):
    """One declared computed value: its dict key must have a production reader.

    :ivar name: Stable identity for the row (e.g. ``"reification_buffer"``).
    :ivar write_file: Repo-relative ``.py`` path where the value is written.
    :ivar write_symbol: The enclosing function/method that performs the write
        (documentation anchor only — the check scans the WHOLE codebase for
        a reader, not just this file, since the founding case's reader, if
        it existed, could legitimately live anywhere downstream).
    :ivar dict_key: The exact string key the value is stored under (a dict
        literal key, e.g. ``material_conditions["reification_buffer"]`` or
        ``{"reification_buffer": ...}``).
    :ivar what_it_computes: One-line description of the computed quantity.
    :ivar consequence_if_unread: What is lost while nothing consumes it —
        cite the concrete downstream effect that never happens.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    write_file: str
    write_symbol: str
    dict_key: str
    what_it_computes: str
    consequence_if_unread: str

    @model_validator(mode="after")
    def _validate_shape(self) -> DeclaredComputedField:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If any identity field is blank, or ``write_file``
            is not a ``.py`` path.
        """
        if not self.name.strip():
            raise ValueError("DeclaredComputedField.name must be non-empty")
        if not self.write_symbol.strip():
            raise ValueError(f"{self.name!r}: write_symbol must be non-empty")
        if not self.write_file.endswith(".py"):
            raise ValueError(
                f"{self.name!r}: write_file must be a .py path, got {self.write_file!r}"
            )
        if not self.dict_key.strip():
            raise ValueError(f"{self.name!r}: dict_key must be non-empty")
        return self


class UnconsumedExemption(BaseModel):
    """A declared computed field known to lack a consumer, on record.

    Never a silent shrug: every row names the owner and the dated
    reasoning, exactly as
    :class:`babylon.sentinels.inert.registry.InertExemption` does.

    :ivar name: The exempted row's :class:`DeclaredComputedField.name`.
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
    def _validate_shape(self) -> UnconsumedExemption:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If any field is blank.
        """
        for field_name in ("name", "reason", "owner", "date"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"UnconsumedExemption.{field_name} must be non-empty")
        return self


#: The one seeded row (Track 1 Task 10). Verified 2026-07-18 by grep across
#: ``src``/``web``: only the write site
#: (``engine/systems/ideology.py::ConsciousnessSystem.step``), the model
#: field declaration
#: (``models/components/material_conditions.py::MaterialConditionsBuffer.
#: reification_buffer``), and this sentinel's own files mention
#: ``"reification_buffer"`` at all — no serializer, formula, or narrative
#: module reads it back.
DECLARED_COMPUTED_FIELDS: Final[tuple[DeclaredComputedField, ...]] = (
    DeclaredComputedField(
        name="reification_buffer",
        write_file="src/babylon/engine/systems/ideology.py",
        write_symbol="ConsciousnessSystem.step",
        dict_key="reification_buffer",
        what_it_computes=(
            "Commodity-fetishism reification buffer in [0, 1] "
            "(babylon.formulas.consciousness_routing.compute_reification_buffer: "
            "|Phi| / (|Phi| + v + eps)) — how much imperial rent obscures class "
            "relations from core workers."
        ),
        consequence_if_unread=(
            "Computed and written onto material_conditions['reification_buffer'] "
            "every tick a social_class node is processed by ConsciousnessSystem, but "
            "nothing downstream reads the key back -- the reification signal never "
            "reaches route_agitation_to_ternary, any narrative surface, or any wire "
            "payload. A real formula with a real write site and zero listeners: "
            "distinct from the inert sentinel's producer-reachability rule, which "
            "this row ALREADY satisfies (compute_reification_buffer() has a genuine "
            "production caller) -- inert proves the function is called; this sentinel "
            "proves its RESULT is actually consulted, and today it is not."
        ),
    ),
)

#: Deliberately EMPTY. The one DECLARED_COMPUTED_FIELDS row above is a real,
#: currently-unremediated gap (see its consequence_if_unread) -- this
#: sentinel is built to report that honestly (a RED finding against the real
#: registry, not a green rubber stamp), never to launder it via a silent
#: exemption. A future row here must name an owner and a dated reason, same
#: as babylon.sentinels.inert.registry.INERT_EXEMPTIONS.
UNCONSUMED_EXEMPTIONS: Final[tuple[UnconsumedExemption, ...]] = ()
