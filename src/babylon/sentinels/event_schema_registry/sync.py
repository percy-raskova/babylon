"""The ``EVENT_BUILDERS ⊆ registry`` one-way sync check (theme 7, C-1/I-5).

**Why one-way, not a circular "sync."** "Repair ``EVENT_BUILDERS`` to match
the registry" is circular exactly where the registry's own Tier 2 rows were
BUILT FROM ``EVENT_BUILDERS`` in the first place — asking a transcription to
match its own source proves nothing. The correct direction is
``EVENT_BUILDERS ⊆ registry``, never the reverse: every field a builder
reads off the bus payload must be a key the registry ALREADY documents
(Tier 1 from real BSL evidence, or Tier 2 transcribed straight from the same
builder), never a field the registry has no record of at all. This is
satisfied by construction for every Tier 2 row (it IS the builder's own
field set) and needs real verification only where a Tier 1 (BSL-observed)
row and its builder might disagree — which is exactly where this check earns
its keep: ``ENTITY_DEATH``'s builder reads a ``cause`` no observed BSL site
provides (``vitality.bsl``'s own comment says why: no string payloads,
§2.8), and ``SUPERWAGE_CRISIS``'s builder reads ``payer_id``/``receiver_id``
where content emits only a bare ``receiver`` — both real, both now
DOCUMENTED as ``source="builder-only"`` rows rather than silently
undiscovered (Tier 1's own docstring in :mod:`.registry` names the rule).

**Normalization.** Python builder fields are snake_case
(``payload.get("legitimation_index", …)``); Tier 1's BSL-observed keys are
kebab-case (``(legitimation-index …)``). The ONE normalization rule this
check applies, in both directions, before comparing: ``_`` and ``-`` are the
same character. Nothing else is normalized (case, prefixes, pluralization
all stay literal) — a real spelling divergence must still fail loudly.
"""

from __future__ import annotations

from pathlib import Path

from babylon.sentinels._ast import eventtype_dict_value_get_string_keys
from babylon.sentinels.event_schema_registry.registry import (
    EventSchemaRegistry,
    normalize_key,
)
from babylon.sentinels.fallback_coverage.registry import EVENT_BUILDERS_DICT, EVENT_BUILDERS_PATH

#: Re-exported for callers that import the normalization rule from its
#: natural home in this module (the sync check) rather than from
#: :mod:`.registry`, where it actually lives — the registry owns it because
#: R4.1's own tests need it (comparing a Tier 1 row's ``builder-only`` keys
#: against a fresh ``EVENT_BUILDERS`` read) independent of this module.
__all__ = ["event_builders_subset_violations", "normalize_key"]


def event_builders_subset_violations(
    registry: EventSchemaRegistry,
    *,
    builders_path: Path = EVENT_BUILDERS_PATH,
    builders_dict: str = EVENT_BUILDERS_DICT,
) -> list[str]:
    """Every ``EVENT_BUILDERS`` payload read the registry does not account for.

    :param registry: The loaded event-schema registry.
    :param builders_path: Source file holding the builder dict (overridable
        for tests; defaults to the real ``event_builders.py``).
    :param builders_dict: The dict's module-level assignment name.
    :returns: One violation string per ``(EventType, field)`` pair the
        builder reads that is absent — after ``_``/``-`` normalization —
        from that EventType's registry row; empty means the containment
        holds for the whole estate.
    """
    builder_fields = eventtype_dict_value_get_string_keys(builders_path, builders_dict)
    violations: list[str] = []
    for event_type, raw_fields in sorted(builder_fields.items()):
        registry_keys = registry.key_names_for(event_type)
        if registry_keys is None:
            if raw_fields:
                violations.append(
                    f"EventType.{event_type}: EVENT_BUILDERS has an entry reading "
                    f"{list(raw_fields)} but the registry has NO Tier 1/Tier 2 row "
                    "for this EventType at all — a builder landed with no matching "
                    "registry row (the registry is stale, or this EventType is "
                    "wrongly Tier 3)."
                )
            continue
        normalized_registry = {normalize_key(k) for k in registry_keys}
        for raw_field in raw_fields:
            normalized_field = normalize_key(raw_field)
            if normalized_field not in normalized_registry:
                violations.append(
                    f"EventType.{event_type}: EVENT_BUILDERS reads payload key "
                    f"{raw_field!r} (normalized {normalized_field!r}) which is not "
                    f"in the registry's key set for this EventType "
                    f"({sorted(normalized_registry)}) — the registry row is "
                    "missing this key (add it, source=builder-only, with a note) "
                    "or EVENT_BUILDERS drifted from what it used to read."
                )
    return violations
