"""The event-schema registry: BSL ``emit`` payloads, tiered by evidence class.

Theme 7 (event-schema registry, C-1 rescope). The data itself lives in
``docs/reference/event-schema-registry.toml`` — a single, cross-toolchain
artifact (TOML, not a hand-kept pair of Rust/Python literals) — this module
only loads and shapes it.

**Why three tiers, not one flat table.** A single "here is EVERY EventType's
schema" table cannot be built honestly today: BSL content emits only a
minority of ``EventType`` members, the Python ``EVENT_BUILDERS`` bus->pydantic
registry is itself already known-narrower-than-its-source in places (the
``CONTROL_RATIO_CRISIS`` case both tiers below carry), and most members have
no observed producer at all. Transcribing ``EVENT_BUILDERS``'s incomplete
entries as "the schema," or inventing key lists for members nobody emits,
would both manufacture a false authority this estate's verifiability
discipline forbids. Instead:

- **Tier 1 — verified-bsl.** Members with at least one observed
  ``(emit EventType/X …)`` site in ``content/rules/*.bsl``
  (:mod:`babylon.sentinels.event_schema_registry.bsl_emit_scan` reads these
  directly — the strongest evidence class). A member with more than one
  observed site carries the UNION of every site's keys; a key present at
  every site is ``required``, a key present at only some is not (documented
  reality, never a forced single shape — port-AS-IS, ADR183). A key no BSL
  site provides but ``EVENT_BUILDERS`` reads anyway (with a default) is
  included too, flagged ``source="builder-only"`` — the registry's job is to
  describe what IS, including a builder expecting a field content does not
  yet carry, not to silently omit that fact.
- **Tier 2 — verified-python-builder.** Members with an ``EVENT_BUILDERS``
  entry but no BSL emit site yet. The row transcribes the builder's own
  field set, EXPLICITLY inheriting that source's own incompleteness — this
  tier makes no claim of completeness, only "this is what the builder
  currently declares."
- **Tier 3 — no-known-emitter.** Every remaining Python ``EventType`` member:
  no builder, no observed BSL emitter. No key list, honestly.

**BSL-only, off the Python vocabulary entirely.** ``organization.bsl``'s
``EventType/ORGANIZATION_SEEDED`` is a documented, deliberate probe-only name
(that file's own D-1 comment) — content emits it, but it is NOT a member of
Python's ``EventType`` enum. Folding it into Tier 1 would falsely imply the
three tiers exhaustively partition the 100-member Python universe (they do —
``python_event_type_total`` in the TOML pins that count, and
``tests/unit/sentinels/test_event_schema_registry.py`` proves
``len(tier1) + len(tier2) + len(tier3) == python_event_type_total`` at every
run). It gets its own, separately-labelled table instead.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from babylon.sentinels.base import SentinelCheckError

REPO_ROOT = Path(__file__).resolve().parents[4]

#: The one canonical, cross-toolchain artifact — TOML avoids hand-keeping a
#: second, Rust-side literal table in sync by construction (a future Rust
#: consumer, R4.2, reads this same file rather than a transcription of it).
REGISTRY_PATH = REPO_ROOT / "docs" / "reference" / "event-schema-registry.toml"


@dataclass(frozen=True)
class RegistryKey:
    """One payload key on one registry row.

    :param name: The key exactly as content or the builder spells it — BSL's
        kebab-case where ``source`` is ``"bsl"``/``"builder-only"`` documents
        a builder read, Python's snake_case where ``source`` is ``"builder"``
        (Tier 2, transcribed straight from ``EVENT_BUILDERS``). This module
        never renames either spelling (port-AS-IS, ADR183); the ``_``/``-``
        normalization is the SYNC CHECK's job
        (:mod:`babylon.sentinels.event_schema_registry.sync`), not the
        registry's.
    :param required: ``True`` if every evidence site for this row carries the
        key; ``False`` if only some do (Tier 1's branch-specific keys) or if
        the key is builder-only (never BSL-observed at all).
    :param source: ``"bsl"`` (a real content citation backs it), ``"builder"``
        (Tier 2 — transcribed from ``EVENT_BUILDERS``, no BSL site exists for
        this row at all), or ``"builder-only"`` (Tier 1 — a BSL site exists
        for this EventType, but THIS key comes only from the builder).
    :param note: Free-text evidence/caveat, required whenever ``source`` is
        ``"builder-only"`` (an unexplained divergence is indistinguishable
        from an oversight).
    """

    name: str
    required: bool
    source: str
    note: str = ""


@dataclass(frozen=True)
class Tier1Row:
    """A ``verified-bsl`` registry row — content demonstrably emits this."""

    event_type: str
    citations: tuple[str, ...]
    keys: tuple[RegistryKey, ...]


@dataclass(frozen=True)
class Tier2Row:
    """A ``verified-python-builder`` row — no BSL site, a builder exists."""

    event_type: str
    note: str
    keys: tuple[RegistryKey, ...]


@dataclass(frozen=True)
class Tier3Row:
    """A ``no-known-emitter`` row — bare vocabulary, no producer at all."""

    event_type: str
    note: str


@dataclass(frozen=True)
class UnmintedRow:
    """A BSL-only emit name absent from Python's ``EventType`` enum entirely."""

    name: str
    citation: str
    note: str
    keys: tuple[RegistryKey, ...]


@dataclass(frozen=True)
class EventSchemaRegistry:
    """The whole loaded registry."""

    schema_version: int
    measured_at: str
    python_event_type_total: int
    bsl_content_glob: str
    tier1: tuple[Tier1Row, ...]
    tier2: tuple[Tier2Row, ...]
    tier3: tuple[Tier3Row, ...]
    unminted_bsl_only: tuple[UnmintedRow, ...] = field(default_factory=tuple)

    def tier1_by_event_type(self) -> dict[str, Tier1Row]:
        return {row.event_type: row for row in self.tier1}

    def tier2_by_event_type(self) -> dict[str, Tier2Row]:
        return {row.event_type: row for row in self.tier2}

    def tier3_by_event_type(self) -> dict[str, Tier3Row]:
        return {row.event_type: row for row in self.tier3}

    def key_names_for(self, event_type: str) -> frozenset[str] | None:
        """Every declared key name for ``event_type`` (Tier 1 or Tier 2 only).

        :returns: The row's key names, or ``None`` if ``event_type`` is not a
            Tier 1 or Tier 2 member (Tier 3 declares no keys by definition).
        """
        tier1 = self.tier1_by_event_type().get(event_type)
        if tier1 is not None:
            return frozenset(k.name for k in tier1.keys)
        tier2 = self.tier2_by_event_type().get(event_type)
        if tier2 is not None:
            return frozenset(k.name for k in tier2.keys)
        return None


def _require(mapping: dict[str, Any], key: str, row_desc: str) -> Any:
    if key not in mapping:
        raise SentinelCheckError(f"{REGISTRY_PATH}: {row_desc} is missing required field {key!r}")
    return mapping[key]


def _parse_keys(raw_keys: list[dict[str, Any]], row_desc: str) -> tuple[RegistryKey, ...]:
    keys = []
    for raw in raw_keys:
        name = _require(raw, "name", f"{row_desc} key")
        required = _require(raw, "required", f"{row_desc} key {name!r}")
        source = _require(raw, "source", f"{row_desc} key {name!r}")
        note = raw.get("note", "")
        if source == "builder-only" and not note:
            raise SentinelCheckError(
                f"{REGISTRY_PATH}: {row_desc} key {name!r} is source=builder-only "
                "with no note — an unexplained content/builder divergence must "
                "be explained, not silently carried"
            )
        keys.append(RegistryKey(name=name, required=bool(required), source=source, note=note))
    return tuple(keys)


def normalize_key(name: str) -> str:
    """The one stated normalization rule between BSL and Python spellings.

    Tier 1 keys are transcribed in BSL's own kebab-case
    (``legitimation-index``); Tier 2 keys and every ``EVENT_BUILDERS`` read
    are transcribed in Python's snake_case (``legitimation_index``). The ONE
    rule this registry and its sync check (:mod:`.sync`, R4.4.1) apply before
    comparing the two: ``_`` and ``-`` are the same character. Nothing else
    is normalized (case, prefixes, pluralization all stay literal) — a real
    spelling divergence must still fail loudly.

    :param name: A raw key spelling, either convention.
    :returns: ``name`` with every underscore replaced by a hyphen.
    """
    return name.replace("_", "-")


def load_registry(path: Path = REGISTRY_PATH) -> EventSchemaRegistry:
    """Load and validate the event-schema registry from ``path``.

    Structural validation is intentionally strict — a malformed row raises
    rather than silently dropping a field, matching the sentinel family's
    loud-failure discipline (Constitution III.11): a registry that failed to
    parse is an infrastructure failure, not "zero coverage."

    :raises SentinelCheckError: If ``path`` is missing/unparseable, or any
        row is missing a required field.
    """
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise SentinelCheckError(f"cannot parse {path}: {exc}") from exc

    tier1 = tuple(
        Tier1Row(
            event_type=(et := _require(row, "event_type", "a tier1 row")),
            citations=tuple(_require(row, "citations", f"tier1 row {et!r}")),
            keys=_parse_keys(_require(row, "keys", f"tier1 row {et!r}"), f"tier1 row {et!r}"),
        )
        for row in data.get("tier1", [])
    )
    measured_at = _require(data, "measured_at", "the registry header")
    _default_tier2_note = (
        f"EVENT_BUILDERS entry only; no BSL emit site observed as of {measured_at} — "
        "transcribed verbatim, inheriting that source's own incompleteness"
    )
    tier2 = tuple(
        Tier2Row(
            event_type=(et := _require(row, "event_type", "a tier2 row")),
            note=row.get("note", _default_tier2_note),
            keys=_parse_keys(_require(row, "keys", f"tier2 row {et!r}"), f"tier2 row {et!r}"),
        )
        for row in data.get("tier2", [])
    )
    _default_tier3_note = f"declared in events.py, no emitter or builder found as of {measured_at}"
    tier3 = tuple(
        Tier3Row(
            event_type=_require(row, "event_type", "a tier3 row"),
            note=row.get("note", _default_tier3_note),
        )
        for row in data.get("tier3", [])
    )
    unminted = tuple(
        UnmintedRow(
            name=(nm := _require(row, "name", "an unminted_bsl_only row")),
            citation=_require(row, "citation", f"unminted row {nm!r}"),
            note=_require(row, "note", f"unminted row {nm!r}"),
            keys=_parse_keys(_require(row, "keys", f"unminted row {nm!r}"), f"unminted row {nm!r}"),
        )
        for row in data.get("unminted_bsl_only", [])
    )

    return EventSchemaRegistry(
        schema_version=_require(data, "schema_version", "the registry header"),
        measured_at=measured_at,
        python_event_type_total=_require(data, "python_event_type_total", "the registry header"),
        bsl_content_glob=_require(data, "bsl_content_glob", "the registry header"),
        tier1=tier1,
        tier2=tier2,
        tier3=tier3,
        unminted_bsl_only=unminted,
    )
