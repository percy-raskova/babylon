"""The ONE exemption record every ``babylon.sentinels`` gate uses.

**Governance history** (gate-governance task, 2026-07-18). Two postures had
shipped for the identical situation — a sentinel finding a real gap and the
gap being deliberately tolerated for now:

- :mod:`babylon.sentinels.unconsumed` stayed RED against the repo (no
  exemption mechanism used at all for its one real finding,
  ``reification_buffer``).
- :mod:`babylon.sentinels.vocabulary` held five sentinels' worth of
  structurally identical findings open GREEN via ``ATTRIBUTE_EXEMPTIONS`` /
  ``LITERAL_EXEMPTIONS`` — plain ``frozenset[tuple[str, ...]]`` literals
  whose "reason" lived only in a source *comment*, never in validated data.
- Meanwhile :mod:`babylon.sentinels.inert`, :mod:`babylon.sentinels.
  masked_arithmetic`, :mod:`babylon.sentinels.aggregation` and
  :mod:`babylon.sentinels.fog` had each independently hand-rolled an
  IDENTICAL ``InertExemption``/``MaskedArithmeticExemption``/
  ``AggregationExemption``/``FogContainmentExemption`` Pydantic class —
  same four fields (``name``/``reason``/``owner``/``date``), same
  ``_validate_shape`` body, copy-pasted five times.

**Owner ruling:** standardize on ONE dated, owner-approved, explicit-registry
exemption model (every gate stays GREEN; every known finding lives in an
explicit, validated row) — and give it teeth so the debt it records cannot
silently become permanent or silently widen:

1. **Required fields, malformed rows crash the import.** ``key``, ``reason``,
   ``owner``, ``date`` and ``tracking_task`` are ALL required and validated
   (mirrors every sentinel registry's existing "reject a malformed row
   loudly at import" posture, Constitution III.11) — a blank field, a
   non-ISO ``date``, or a ``tracking_task`` that is not a real reference
   anchor (``"#42"``, or ``"N/A (...)"`` for a documented PERMANENT
   exemption) fails construction, not silently coerces to "fine".
2. **Exact-tuple matching, never a bare name.** :func:`is_exempt` matches the
   FULL ``key`` tuple. This closes a real, hand-verified latent hole: the
   pre-unification :mod:`babylon.sentinels.inert` matched by bare ``row.name``
   against ONE flat exemption set shared by BOTH ``DECLARED_STORES`` and
   ``DECLARED_PRODUCERS`` — an exemption named ``"reification_buffer"``
   would have silently exempted a store row AND a producer row sharing that
   name, two semantically unrelated checks. Every migrated registry now
   tags its key with a *kind* discriminant (``("store", name)`` vs
   ``("producer", name)``, ``("node_type_literal", path, literal)``, etc.)
   so a new violation that merely resembles an exempted one — same shape,
   different symbol, OR the same symbol under a different check — still
   fails.
3. **Staleness is surfaced, never a time bomb.** :func:`stale_exemptions`
   is a pure, informational query a sentinel's ADVISORY tier may print
   ("this exemption is N days old, revisit it") — nothing in this module
   ever gates on the calendar. A hard-coded expiry date would be exactly
   the "breaks CI on an arbitrary date" failure mode the owner's directive
   explicitly warned against; a sentinel that cries wolf on a clock gets
   disabled, not obeyed.

Layer 0.5 (same rank as :mod:`babylon.sentinels.base`): importable by every
sentinel package, ``tools/*`` probes, and the sentinel test suite; imports
nothing above :mod:`babylon.models`.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date as _date
from typing import Final

from pydantic import BaseModel, ConfigDict, model_validator

__all__ = ["SentinelExemption", "is_exempt", "stale_exemptions"]

#: ``YYYY-MM-DD`` only — the one canonical date shape every sentinel
#: registry already writes by hand; validated so a typo'd date cannot
#: silently defeat :func:`stale_exemptions`.
_ISO_DATE_RE: Final[re.Pattern[str]] = re.compile(r"^\d{4}-\d{2}-\d{2}$")

#: A ``tracking_task`` must be a real, greppable anchor: either a
#: ``#<digits>`` ticket reference (this project's task-ledger convention —
#: see ``ai/_inbox``/the task tracker; e.g. ``"#42"``) or the literal token
#: ``N/A`` documenting a DELIBERATELY PERMANENT exemption (a negative-control
#: test, a generic attribute-agnostic utility) that has no remediation to
#: track. Free prose ("fix this someday") is rejected -- it is not
#: re-discoverable and cannot be grepped for later.
_TRACKING_TASK_RE: Final[re.Pattern[str]] = re.compile(r"^(#\d+|n/a\b)", re.IGNORECASE)


class SentinelExemption(BaseModel):
    """One dated, owner-approved decision to hold a sentinel finding open.

    The single exemption shape for the whole ``babylon.sentinels`` family —
    every gate's registry declares its exemptions as a
    ``tuple[SentinelExemption, ...]`` and matches with :func:`is_exempt`,
    never a bespoke per-gate class or a bare tuple-in-a-set membership test.

    :ivar key: The exact identity of the ONE finding this row exempts, as a
        tuple of non-blank strings. Convention: the first element is a
        *kind* discriminant naming which declared-registry/rule this key
        belongs to (``"store"``, ``"producer"``, ``"computed_field"``,
        ``"node_type_literal"``, ``"node_attribute"``, …), so two different
        checks can never collide on a shared bare name. Matching is always
        FULL-TUPLE equality (see :func:`is_exempt`) — never a substring,
        prefix, or name-only match.
    :ivar reason: Why the gap is tolerated right now — the WHY, not just the
        WHAT (cite the concrete consequence, mirroring every sentinel
        registry's own ``consequence_if_*``/``failure_if_*`` fields).
    :ivar owner: Who approved the exemption (this is a Benevolent-Dictator
        project; every exemption is a recorded, revisitable BD decision, not
        a shrug).
    :ivar date: ISO date (``YYYY-MM-DD``) the exemption was recorded.
    :ivar tracking_task: A ``"#<n>"`` reference into the project's task
        ledger tracking remediation, or ``"N/A (<why)"`` for an exemption
        that documents a deliberately PERMANENT pattern rather than a live
        bug awaiting a fix. Never blank, never free prose with no anchor.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: tuple[str, ...]
    reason: str
    owner: str
    date: str
    tracking_task: str

    @model_validator(mode="after")
    def _validate_shape(self) -> SentinelExemption:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If ``key`` is empty or contains a blank part,
            any other field is blank, ``date`` is not ``YYYY-MM-DD``, or
            ``tracking_task`` does not start with a real reference anchor
            (``"#<digits>"`` or ``"N/A"``).
        """
        if not self.key:
            raise ValueError("SentinelExemption.key must be a non-empty tuple")
        for index, part in enumerate(self.key):
            if not part.strip():
                raise ValueError(f"SentinelExemption.key[{index}] must be non-empty")
        for field_name in ("reason", "owner", "date", "tracking_task"):
            value = getattr(self, field_name)
            if not value.strip():
                raise ValueError(f"SentinelExemption.{field_name} must be non-empty")
        if not _ISO_DATE_RE.match(self.date):
            raise ValueError(f"SentinelExemption.date must be ISO YYYY-MM-DD, got {self.date!r}")
        if not _TRACKING_TASK_RE.match(self.tracking_task):
            raise ValueError(
                "SentinelExemption.tracking_task must start with a real reference anchor "
                f"('#<n>' or 'N/A'), got {self.tracking_task!r}"
            )
        return self


def is_exempt(key: tuple[str, ...], exemptions: Iterable[SentinelExemption]) -> bool:
    """Whether ``key`` exactly matches some recorded exemption's own key.

    Full-tuple equality ONLY — deliberately not a prefix, substring, or
    name-only match, so a new violation that merely resembles an exempted
    one (same shape, different symbol; or the same symbol under a
    different check) still fails the gate.

    :param key: The exact identity of the finding under test (same
        kind-tagged shape the gate's registry rows use).
    :param exemptions: The gate's declared exemption rows.
    :returns: Whether some row's ``key`` equals ``key``.
    """
    return any(exemption.key == key for exemption in exemptions)


def stale_exemptions(
    exemptions: Iterable[SentinelExemption],
    *,
    as_of: str,
    max_age_days: int,
) -> tuple[SentinelExemption, ...]:
    """Exemptions recorded more than ``max_age_days`` before ``as_of``.

    Purely informational — a sentinel's ADVISORY tier may print these
    (Constitution III.11, "loud" over "silent"), but nothing in this module
    ever gates on the result. A hard-coded expiry that reds the build on an
    arbitrary future date would itself be a silently-armed guardrail (the
    exact failure mode this whole convention exists to prevent) — staleness
    is a prompt to review, never an automatic failure.

    :param exemptions: The rows to check.
    :param as_of: ISO date (``YYYY-MM-DD``) to measure age against — pass
        the real "today" in production; a test passes a fixed value for
        determinism.
    :param max_age_days: Age threshold in days.
    :returns: The stale rows, in their input order.
    """
    today = _date.fromisoformat(as_of)
    return tuple(
        exemption
        for exemption in exemptions
        if (today - _date.fromisoformat(exemption.date)).days > max_age_days
    )
