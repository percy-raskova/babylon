"""Typed vocabulary for the Seam Observatory registry.

The Seam Observatory is Babylon's mechanical enforcement of Constitution
Article VIII.12 ("silent no-op / disarmed guardrail") and III.11 (Loud
Failure). This codebase's most dangerous bugs are not crashes but **silence**:
a quantity computed by the engine, dropped on the wire, and rendered blank —
type-checking, importing, and passing tests the entire way. This module gives
that failure mode a name and a shape so the sensors in
``babylon.sentinels.seam.checks`` can catch it.

Every player-observable quantity that crosses the engine → web-bridge →
frontend seam is declared as one :class:`SeamEntry`. The registry
(:data:`babylon.sentinels.seam.registry.SEAM_REGISTRY`) is the single source of
truth; the sensors diff reality against it and fail loudly.

Dependency-light **by design** — this module sits at layer 0.5 (same rank as
:mod:`babylon.config`), importable by ``engine``, ``domain``, ``web.game.*``
and ``tools/*`` alike. It may import :mod:`babylon.models.enums` (for
:class:`~babylon.models.enums.events.EventType`) but nothing above ``models``;
the boundary is enforced by an import-linter contract in ``pyproject.toml``.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, computed_field, model_validator

from babylon.models.enums.events import EventType


class SeamScope(StrEnum):
    """The observable surface a wire key is serialized onto.

    Scoping the registry key by surface is what resolves the
    ``(payload, wire-key)`` collision. The literal wire key ``imperial_rent``
    names a Leontief **flow** rate on :attr:`MAP`/:attr:`TERRITORY` features but
    an accumulated **stock** on the :attr:`ECONOMY` dashboard — the same string
    for two unrelated quantities. Keying the registry by ``scope.wire_key``
    keeps them distinct instead of silently conflated.

    Members are added as later build phases register their surfaces; every
    member below corresponds to a concrete emission site verified during recon.

    :cvar MAP: ``/map/`` feature properties (hex- and county-zoom lenses;
        ``web/game/map_contract.py`` ``MAP_METRIC_PROPERTIES``).
    :cvar TERRITORY: per-territory ``tick_*`` graph attributes serialized by the
        bridge's ``_serialize_territory``.
    :cvar ECONOMY: the economy summary/dashboard payloads
        (``get_game_summary`` / ``get_economy_dashboard``).
    :cvar ENDGAME: terminal-outcome payload (``get_endgame_state``).
    :cvar EVENT: per-tick simulation events (the ``EventType`` vocabulary).
    """

    MAP = "map"
    TERRITORY = "territory"
    ECONOMY = "economy"
    ENDGAME = "endgame"
    EVENT = "event"


class LivenessClass(StrEnum):
    """How Sensor 2 (liveness) must interpret a field that reads null.

    A null value is only a bug relative to a **declared expectation**. This
    enum is that declaration, so the liveness sensor neither false-passes on a
    permanently-dark field nor nags about one that is legitimately out of scope.

    :cvar MUST_BE_LIVE: the strongest contract — the field must be non-null in
        every applicable ``(tick, entity)`` cell (subject to its declared
        deadline). A single null is a Sensor-2 failure. Structural fields such
        as ``population``/``heat`` live here.
    :cvar DECLARED_CONDITIONAL: live only under a stated condition
        (``liveness_condition``); Sensor 2 requires at least one non-null
        witness across the golden scenarios, not universal liveness. The
        year-boundary Φ/derived-rate family and ``endgame.outcome`` live here.
    :cvar STRUCTURALLY_IMPOSSIBLE: cannot be computed with today's graph shape
        (e.g. a co-optive-edge count with no such edges). Sensor 2 skips it, but
        Sensor 1 still requires the row so its absence is documented, not silent.
    :cvar NOT_YET_COMPUTED: planned but unimplemented (e.g. territory-level
        consciousness). Sensor 2 skips it; Sensor 1 keeps it declared so it
        cannot be quietly forgotten.
    """

    MUST_BE_LIVE = "must_be_live"
    DECLARED_CONDITIONAL = "declared_conditional"
    STRUCTURALLY_IMPOSSIBLE = "structurally_impossible"
    NOT_YET_COMPUTED = "not_yet_computed"


#: Liveness classes Sensor 2 actively checks (the rest are documented stubs).
_LIVENESS_CHECKED: frozenset[LivenessClass] = frozenset(
    {LivenessClass.MUST_BE_LIVE, LivenessClass.DECLARED_CONDITIONAL}
)


class SeamEntry(BaseModel):
    """One declared player-observable quantity crossing the engine↔web↔UI seam.

    Frozen and ``extra="forbid"`` so a malformed row is itself a loud failure at
    import time (Constitution III.11) rather than a quiet ``None`` at runtime.

    :ivar payload: the true internal quantity name (engine graph attribute or
        economy field) — may differ from the wire key(s).
    :ivar wire_keys: the serialized JSON key(s) this payload is emitted under.
        The first entry forms the registry :attr:`key`; additional entries
        record *inconsistent* wire keys for the same payload (drift Sensor 1
        reports, e.g. ``imperial_rent`` vs ``imperial_rent_pool``).
    :ivar scope: the observable surface (:class:`SeamScope`).
    :ivar owner_layer: the dotted module that computes the payload, or
        ``"bridge-derived"`` for quantities the bridge derives with no engine
        write-site.
    :ivar write_site: an anchor (``path:line`` + note) for the engine write, or
        ``None`` when the payload has no single engine write-site.
    :ivar derivation_site: an anchor for the bridge computation, when the
        payload is derived at serialization time rather than read off the graph.
    :ivar read_paths: every bridge/serializer call-site that emits this
        ``(scope, wire_key)``.
    :ivar liveness_class: how Sensor 2 interprets a null (:class:`LivenessClass`).
    :ivar liveness_condition: the actual condition text, for
        ``DECLARED_CONDITIONAL`` rows.
    :ivar known_conditional: ``True`` marks a field whose liveness is blocked on
        a genuinely-external data artifact (never a standing excuse — Φ rows are
        **not** ``known_conditional``; their reference data is published to CI).
    :ivar dtype: the serialized value type
        (``"float" | "int" | "str" | "bool" | "enum:<Name>" | "json"``).
    :ivar nullable: whether ``None`` is a legitimate serialized value.
    :ivar event_type: the ``EventType`` member, for ``scope=EVENT`` rows only.
    :ivar spec_ref: originating spec / ADR, for provenance.
    :ivar notes: free-text clarification.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    payload: str
    wire_keys: tuple[str, ...]
    scope: SeamScope
    owner_layer: str
    liveness_class: LivenessClass
    dtype: str
    write_site: str | None = None
    derivation_site: str | None = None
    read_paths: tuple[str, ...] = ()
    liveness_condition: str | None = None
    known_conditional: bool = False
    nullable: bool = True
    event_type: EventType | None = None
    spec_ref: str | None = None
    notes: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def key(self) -> str:
        """Stable identity ``"{scope}.{primary wire_key}"`` — resolves collisions.

        :returns: The scoped key; two rows may share a wire key only if their
            scopes differ.
        """
        return f"{self.scope.value}.{self.wire_keys[0]}"

    @property
    def liveness_checked(self) -> bool:
        """Whether Sensor 2 asserts liveness for this row.

        :returns: ``True`` for :attr:`LivenessClass.MUST_BE_LIVE` /
            :attr:`LivenessClass.DECLARED_CONDITIONAL`; ``False`` for the
            documented out-of-scope stubs.
        """
        return self.liveness_class in _LIVENESS_CHECKED

    @model_validator(mode="after")
    def _validate_shape(self) -> SeamEntry:
        """Reject malformed rows loudly at import (III.11).

        :returns: ``self`` when valid.
        :raises ValueError: on an empty ``wire_keys``; a ``known_conditional``
            row that is not ``DECLARED_CONDITIONAL``; an ``EVENT``-scope row
            without an ``event_type`` (or a non-``EVENT`` row carrying one).
        """
        if not self.wire_keys:
            raise ValueError(f"{self.payload!r}: wire_keys must be non-empty")
        if self.known_conditional and self.liveness_class is not LivenessClass.DECLARED_CONDITIONAL:
            raise ValueError(
                f"{self.key}: known_conditional requires DECLARED_CONDITIONAL, "
                f"got {self.liveness_class}"
            )
        if self.scope is SeamScope.EVENT and self.event_type is None:
            raise ValueError(f"{self.key}: EVENT-scope rows require an event_type")
        if self.scope is not SeamScope.EVENT and self.event_type is not None:
            raise ValueError(f"{self.key}: event_type is only valid on EVENT-scope rows")
        return self
