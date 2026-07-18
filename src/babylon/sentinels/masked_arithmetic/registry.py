"""Declared invariants of the ``masked_arithmetic`` sentinel.

Fog (:mod:`game.fog.filter`) masks a political field by setting it to
``None`` while KEEPING the dict key present (never omitting it) — see
``apply_fog``'s own docstring: "vision_masked/vision_approx are both set
... present but empty, not omitted". This is deliberate and correct for the
gate itself, but it is a footgun for any DOWNSTREAM consumer of a fogged
payload: ``dict.get(key, default)``'s ``default`` argument only fires when
``key`` is ABSENT — a present-but-``None`` value defeats it silently, so
``float(payload.get("heat", 0.0))`` does not fall back to ``0.0`` when
``"heat"`` is masked; it crashes with ``TypeError: float() argument must be
a string or a real number, not 'NoneType'``.

Founding, hand-verified instance (Track 1 audit, 2026-07-18):
``web/game/engine_bridge.py::_build_state_apparatus_dashboard`` received
``organizations`` — already-fogged :func:`~game.engine_bridge.
_serialize_organization` output, where a masked org's ``heat`` is present
and ``None`` — and originally computed
``total_heat = round(sum(float(o.get("heat", 0.0)) for o in state_orgs), 4)``,
which raised ``TypeError`` the instant one state-apparatus org was
out-of-reach. The shipped fix (commit ``657e415c6``, 2026-07-18) replaced
this with an explicit ``is not None`` guard before touching arithmetic. This
sentinel pins that fix so a future refactor cannot silently reintroduce the
crash.

This registry declares a single, closed, hand-curated invariant (mirrors
:mod:`babylon.sentinels.inert.registry`'s "closed, not merely additive"
framing) rather than a codebase-wide scan: distinguishing a genuinely
fog-masked payload read from an engine's own raw-graph read
(``graph.nodes[id].get("heat", 0.0)``, which is never fog-masked — the
engine always sees true values, fog is a serialization-boundary-only
redaction) requires knowing WHICH parameter of WHICH function carries
already-fogged data. A syntax-only scan cannot tell the two apart (both
look like ``x.get("heat", 0.0)``), and a broad scan across ``web/`` was
hand-verified (Track 1 Task 10 recon) to hit >20 sites, the overwhelming
majority of which are legitimate raw-graph reads inside
``engine_bridge.py`` composer functions that run BEFORE any
``apply_fog``/``_apply_class_vision_gate`` call — flagging them would be
false positives, and Constitution-adjacent doctrine here is explicit: a
sentinel that cries wolf gets disabled. New fogged-consumer risk sites must
therefore be added to :data:`DECLARED_FOGGED_CONSUMERS` by hand as they are
discovered, exactly like
:data:`babylon.sentinels.inert.registry.DECLARED_PRODUCERS` has no
"growth" rule either (see that registry's rule (b) posture).

Layer 0.5: imports nothing above :mod:`babylon.models`; the political field
names below are a documented, hand-mirrored subset of
``web/game/fog/filter.py``'s ``POLITICAL_FIELDS``/``ORG_POLITICAL_FIELDS``
(NOT imported — this package must never depend on ``web.*``, only the
reverse).
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, model_validator

__all__ = [
    "DECLARED_FOGGED_CONSUMERS",
    "MASKED_ARITHMETIC_EXEMPTIONS",
    "DeclaredFoggedConsumer",
    "MaskedArithmeticExemption",
]

#: Arithmetic-ish callables whose direct argument being an unguarded
#: ``.get(field, <non-None>)``/``[field]`` access on masked data is the
#: exact footgun this sentinel exists to catch.
ARITHMETIC_WRAPPERS: Final[tuple[str, ...]] = ("float", "int", "round", "abs", "sum")


class DeclaredFoggedConsumer(BaseModel):
    """One declared function known to consume an already-fogged payload.

    :ivar name: Stable identity for the row.
    :ivar def_file: Repo-relative ``.py`` path defining ``function_name``.
    :ivar function_name: The function/method whose body is checked (dotted
        ``Class.method`` form supported for a method).
    :ivar field: The political field name at risk in this function (e.g.
        ``"heat"`` — see ``web/game/fog/filter.py``'s ``POLITICAL_FIELDS``).
    :ivar payload_note: One-line description of WHERE the fogged payload
        this function reads comes from (documentation only).
    :ivar consequence_if_regressed: What breaks if the guard is removed —
        cite the concrete crash.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    def_file: str
    function_name: str
    field: str
    payload_note: str
    consequence_if_regressed: str

    @model_validator(mode="after")
    def _validate_shape(self) -> DeclaredFoggedConsumer:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If any identity field is blank, or ``def_file``
            is not a ``.py`` path.
        """
        if not self.name.strip():
            raise ValueError("DeclaredFoggedConsumer.name must be non-empty")
        if not self.function_name.strip():
            raise ValueError(f"{self.name!r}: function_name must be non-empty")
        if not self.def_file.endswith(".py"):
            raise ValueError(f"{self.name!r}: def_file must be a .py path, got {self.def_file!r}")
        if not self.field.strip():
            raise ValueError(f"{self.name!r}: field must be non-empty")
        return self


class MaskedArithmeticExemption(BaseModel):
    """A declared row known to currently lack a guard, on record.

    Never a silent shrug: every row names the owner and the dated
    reasoning, exactly as
    :class:`babylon.sentinels.inert.registry.InertExemption` does.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    reason: str
    owner: str
    date: str

    @model_validator(mode="after")
    def _validate_shape(self) -> MaskedArithmeticExemption:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If any field is blank.
        """
        for field_name in ("name", "reason", "owner", "date"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"MaskedArithmeticExemption.{field_name} must be non-empty")
        return self


#: The one seeded row (Track 1 Task 10 founding instance). Verified against
#: the shipped fix (commit 657e415c6): ``_build_state_apparatus_dashboard``
#: guards ``heat`` with ``if o.get("heat") is not None`` before any
#: arithmetic touches it.
DECLARED_FOGGED_CONSUMERS: Final[tuple[DeclaredFoggedConsumer, ...]] = (
    DeclaredFoggedConsumer(
        name="state_apparatus_dashboard_heat",
        def_file="web/game/engine_bridge.py",
        function_name="_build_state_apparatus_dashboard",
        field="heat",
        payload_note=(
            "organizations: list[dict] is already-fogged _serialize_organization "
            "output (Task 5b) -- a masked state_apparatus org's 'heat' key is "
            "present with value None, never omitted (apply_fog's own contract)."
        ),
        consequence_if_regressed=(
            "TypeError: float() argument must be a string or a real number, not "
            "'NoneType' -- the exact HTTP 500 the founding bug produced the instant "
            "one state-apparatus org was out of the player's organizing reach. "
            "dict.get(key, default)'s default only fires on an ABSENT key; a "
            "fog-masked key is PRESENT with value None, so the naive "
            "float(o.get('heat', 0.0)) form does not protect against this at all."
        ),
    ),
)

#: Deliberately EMPTY: the one declared row is currently guarded (the
#: shipped fix). A future row here must name an owner and a dated reason,
#: same as babylon.sentinels.inert.registry.INERT_EXEMPTIONS.
MASKED_ARITHMETIC_EXEMPTIONS: Final[tuple[MaskedArithmeticExemption, ...]] = ()
