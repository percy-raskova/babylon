"""Declared invariants of the ``dangling`` sentinel — dynamic-reference targets must exist.

This is the DUAL of :mod:`babylon.sentinels.inert`. Inert catches a declared
construct (store/producer) with NO production caller; this catches the
opposite defect — a CALL SITE that dynamically references a target *by
string name* which does not actually exist anywhere on the object it is
invoked against. Both are instances of the same root failure (machinery
whose wiring nobody verified), approached from opposite ends: inert asks "is
this declared thing ever reached?"; dangling asks "does this reaching
reference land on something real?"

**Founding specimen** (task #43 audit, 2026-07-18):
``web/game/engine_bridge.py:10990`` —
``getattr(persistence, "persist_action_result", None)`` (SINGULAR). The
``RuntimePersistence``/``PostgresRuntimeExtensions`` protocols and both
concrete backends (``PostgresRuntime``, ``RuntimeDatabase``) only ever
declare ``persist_action_results`` (PLURAL, batched — ``(tick, results:
list[dict], *, session_id)``). The guarded branch
(``if persist_fn is not None: persist_fn(**result_data)``) is therefore
**structurally dead** — ``persist_fn`` is always ``None`` and every call
silently falls through to the Django-ORM fallback. A naive rename to the
plural would itself break at runtime (`TypeError: unexpected keyword
argument`) because the plural method's signature is batched, not
per-action — wiring the real path is a separate, owner-gated change; this
sentinel's job is only to make the CLASS of defect (dangling reference)
impossible to reintroduce silently.

**Scope (read before extending — mirrors inert's own scope discipline):**
a general "flag every ``getattr(x, "name", default)`` in the repo" checker
drowns in false positives (``getattr(request, ...)``, ``getattr(settings,
...)``, arbitrary duck-typed dispatch that is NOT a persistence-layer call).
The deliberate scope is a **registry of watched classes**
(:data:`WATCHED_CLASSES`) plus a **registry of watched receivers**
(:data:`WATCHED_RECEIVERS` — how a getattr's first argument is statically
recognized as an instance of one of those watched classes). Only a
dynamic reference whose receiver is provably typed as a watched class is
checked; everything else is silently out of scope, not silently declared
safe.

:data:`DANGLING_EXEMPTIONS` is the same family-wide
:class:`~babylon.sentinels.exemptions.SentinelExemption` every other
sentinel uses (gate-governance ruling, 2026-07-18) — never a bespoke
exemption class.

Layer 0.5: imports nothing above :mod:`babylon.models`.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, model_validator

from babylon.sentinels.exemptions import SentinelExemption

__all__ = [
    "DANGLING_EXEMPTIONS",
    "PRODUCTION_ROOTS",
    "WATCHED_CLASSES",
    "WATCHED_RECEIVERS",
    "WatchedClass",
    "WatchedReceiver",
]

#: Trees scanned for a dangling dynamic reference. Test files are EXCLUDED
#: no matter which root they live under — see
#: :func:`babylon.sentinels.dangling.checks.is_test_source`.
PRODUCTION_ROOTS: Final[tuple[str, ...]] = ("src", "web")


class WatchedClass(BaseModel):
    """One class/Protocol whose declared member names are valid dynamic-reference targets.

    :ivar name: Stable identity for this row (e.g. ``"postgres_runtime_impl"``).
    :ivar def_file: Repo-relative ``.py`` path defining ``class_name``.
    :ivar class_name: The bare class name to statically enumerate members of —
        every method (including private ``_foo``/dunder) declared directly in
        the class body, plus every ``self.<attr> = ...`` instance attribute
        assigned anywhere in the class's own methods (e.g.
        ``PostgresRuntime.__init__``'s ``self._pool = pool``), plus any
        class-body-level ``Assign``/``AnnAssign`` target.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    def_file: str
    class_name: str

    @model_validator(mode="after")
    def _validate_shape(self) -> WatchedClass:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If any identity field is blank, or ``def_file``
            is not a ``.py`` path.
        """
        if not self.name.strip():
            raise ValueError("WatchedClass.name must be non-empty")
        if not self.class_name.strip():
            raise ValueError(f"{self.name!r}: class_name must be non-empty")
        if not self.def_file.endswith(".py"):
            raise ValueError(f"{self.name!r}: def_file must be a .py path, got {self.def_file!r}")
        return self


class WatchedReceiver(BaseModel):
    """One recognized getattr-receiver family.

    Declares (a) which type-annotation name(s) statically mark a name as
    holding an instance of this family, and (b) which :data:`WATCHED_CLASSES`
    rows' members union together to form the valid target-name set for a
    dynamic reference against such a receiver.

    :ivar name: Stable identity for this row (e.g. ``"persistence"``).
    :ivar annotation_names: Type-annotation name(s) that mark a parameter (or
        annotated assignment) as belonging to this family — e.g.
        ``("RuntimePersistence",)`` matches ``persistence: RuntimePersistence``
        and ``persistence: RuntimePersistence | None``.
    :ivar member_classes: :attr:`WatchedClass.name` values (must each resolve
        against :data:`WATCHED_CLASSES`) whose members union to form this
        receiver family's valid dynamic-reference target set. A receiver
        typed via *any one* of ``annotation_names`` is checked against the
        UNION of all these classes' members — the duck-typed protocol may be
        satisfied by any one concrete backend.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    annotation_names: tuple[str, ...]
    member_classes: tuple[str, ...]

    @model_validator(mode="after")
    def _validate_shape(self) -> WatchedReceiver:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If any identity field is blank, or either tuple
            field is empty or contains a blank element.
        """
        if not self.name.strip():
            raise ValueError("WatchedReceiver.name must be non-empty")
        if not self.annotation_names:
            raise ValueError(f"{self.name!r}: annotation_names must be non-empty")
        for value in self.annotation_names:
            if not value.strip():
                raise ValueError(f"{self.name!r}: annotation_names entries must be non-empty")
        if not self.member_classes:
            raise ValueError(f"{self.name!r}: member_classes must be non-empty")
        for value in self.member_classes:
            if not value.strip():
                raise ValueError(f"{self.name!r}: member_classes entries must be non-empty")
        return self


#: The persistence-layer family: the ``RuntimePersistence``/
#: ``PostgresRuntimeExtensions`` protocols plus both concrete backends. A
#: dynamic reference against a receiver typed ``RuntimePersistence`` may
#: legitimately land on either backend at runtime (duck typing across the
#: protocol boundary is the whole point of Feature 037), so all four are
#: watched and their members unioned.
WATCHED_CLASSES: Final[tuple[WatchedClass, ...]] = (
    WatchedClass(
        name="runtime_persistence_protocol",
        def_file="src/babylon/persistence/protocols.py",
        class_name="RuntimePersistence",
    ),
    WatchedClass(
        name="postgres_runtime_extensions_protocol",
        def_file="src/babylon/persistence/protocols.py",
        class_name="PostgresRuntimeExtensions",
    ),
    WatchedClass(
        name="postgres_runtime_impl",
        def_file="src/babylon/persistence/postgres_runtime/_legacy.py",
        class_name="PostgresRuntime",
    ),
    WatchedClass(
        name="sqlite_runtime_impl",
        def_file="src/babylon/persistence/runtime_db.py",
        class_name="RuntimeDatabase",
    ),
)

#: The one seeded receiver family: any name typed (directly, or via a
#: ``self.<attr> = <typed-name>`` alias) as ``RuntimePersistence`` in
#: production code.
WATCHED_RECEIVERS: Final[tuple[WatchedReceiver, ...]] = (
    WatchedReceiver(
        name="persistence",
        annotation_names=("RuntimePersistence",),
        member_classes=(
            "runtime_persistence_protocol",
            "postgres_runtime_extensions_protocol",
            "postgres_runtime_impl",
            "sqlite_runtime_impl",
        ),
    ),
)


def _unknown_member_classes(
    receivers: tuple[WatchedReceiver, ...], classes: tuple[WatchedClass, ...]
) -> dict[str, list[str]]:
    """Map each receiver naming an unresolvable ``member_classes`` entry to those entries.

    Pure and parameterized (rather than reading the module globals directly)
    so the unit tests can exercise a deliberately-broken row without needing
    to monkeypatch-and-reload the real module-level registry tuples.

    :param receivers: Receiver rows to check.
    :param classes: The watched-class rows to resolve against.
    :returns: ``{receiver_name: [unknown_member_class_name, ...]}`` for every
        receiver with at least one unresolvable entry (empty when all
        resolve).
    """
    known = {row.name for row in classes}
    result: dict[str, list[str]] = {}
    for receiver in receivers:
        unknown = [name for name in receiver.member_classes if name not in known]
        if unknown:
            result[receiver.name] = unknown
    return result


def _validate_member_classes_resolve() -> None:
    """Every :attr:`WatchedReceiver.member_classes` entry must name a real row.

    A typo'd or stale ``member_classes`` entry would silently shrink the
    union it is meant to check against, making the gate quietly less strict
    with no visible signal — this fails the import loudly instead
    (Constitution III.11).

    :raises ValueError: If any receiver names a :data:`WatchedClass` that
        does not exist in :data:`WATCHED_CLASSES`.
    """
    unknown = _unknown_member_classes(WATCHED_RECEIVERS, WATCHED_CLASSES)
    if unknown:
        raise ValueError(
            f"WatchedReceiver row(s) name unknown member_classes: {unknown!r} "
            f"-- not present in WATCHED_CLASSES ({sorted({r.name for r in WATCHED_CLASSES})!r})"
        )


_validate_member_classes_resolve()

#: No current exemptions: the one live finding (``persist_action_result``,
#: task #43) is deliberately left GATING (not exempted) — it is the founding
#: specimen this sentinel exists to catch, and remains open until the
#: parallel fix lane retires the dead branch. A future genuinely-irreducible
#: dangling reference goes here instead, keyed ``("dangling", receiver_name,
#: rel_path, attr)`` (see the checks module).
DANGLING_EXEMPTIONS: Final[tuple[SentinelExemption, ...]] = ()
