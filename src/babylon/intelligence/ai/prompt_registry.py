"""Versioned narrator prompt artifacts.

Prompts are data, not code (Constitution III.12 — durable spec artifacts). The
registry version is derived from content bytes, so an edited prompt can never
ship with a stale version pin (closes the manual PROMPT_VERSION drift gap).

Task B1b extends the registry with :class:`EventArchetype` — AI-fillable
narration templates (structure, not scripted content, per the
emergent-endgames ruling) keyed by ``EventType``. Archetypes are pure JSON
data validated against ``archetype.schema.json`` at load time, so the
web-layer ``DeterministicNarrator`` (which imports zero ``babylon.*`` by
design) can read the same files directly later.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Final

import jsonschema
from pydantic import BaseModel, ConfigDict

_DEFAULT_DIR: Final[Path] = (
    Path(__file__).resolve().parents[2] / "data" / "game" / "prompts" / "narrator"
)

_ARCHETYPE_SCHEMA_NAME: Final[str] = "archetype.schema.json"


class EventArchetype(BaseModel):
    """AI-fillable event-narration template (structure, not scripting).

    Per the emergent-endgames ruling (Program 20 Track B), the engine
    declares *what facts must appear* (``slots``) and *how to narrate them*
    (``guidance``) for a family of related ``EventType`` values; the AI fills
    the slots from observed engine state only — it never invents content.

    :ivar id: Archetype identifier; matches its source JSON filename stem.
    :ivar event_types: ``EventType`` values (uppercased, e.g. ``"UPRISING"``)
        this archetype narrates. Each entry must name a real
        :class:`~babylon.models.enums.EventType` member.
    :ivar slots: Named facts the AI must fill from observed engine state,
        never invented.
    :ivar guidance: Narration instructions steering tone and material
        grounding.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    event_types: list[str]
    slots: list[str]
    guidance: str


class PromptRegistry:
    """Load-once registry of narrator prompt + event-archetype artifacts.

    Archetypes live in an ``archetypes`` directory that is a **sibling** of
    ``root`` (i.e. ``root.parent / "archetypes"``) — for the default
    narrator directory that resolves to
    ``src/babylon/data/game/prompts/archetypes``.

    :param root: Directory containing ``*.txt`` narrator prompt artifacts.
    :raises FileNotFoundError: If ``root`` is missing or contains no ``*.txt``
        artifacts (loud, III.11). The sibling ``archetypes`` directory is
        treated differently: its ABSENCE is tolerated (data simply not
        present is not a failure), but any archetype JSON file it does
        contain must validate against ``archetype.schema.json`` or loading
        fails loud.
    :raises jsonschema.exceptions.ValidationError: If an archetype JSON file
        in the sibling ``archetypes`` directory fails schema validation.
    """

    def __init__(self, root: Path | None = None) -> None:
        self._root: Final[Path] = root or _DEFAULT_DIR
        if not self._root.is_dir():
            raise FileNotFoundError(f"Prompt artifact dir missing: {self._root}")
        self._prompts: Final[dict[str, str]] = {
            p.stem: p.read_text(encoding="utf-8") for p in sorted(self._root.glob("*.txt"))
        }
        if not self._prompts:
            raise FileNotFoundError(f"No prompt artifacts in {self._root}")

        self._archetype_bytes: Final[dict[str, bytes]] = {}
        self._archetypes: Final[dict[str, EventArchetype]] = {}
        self._load_archetypes()

    def _load_archetypes(self) -> None:
        """Load + validate archetype JSON from the sibling ``archetypes`` dir.

        Tolerant of an ABSENT directory (no archetype data shipped yet is
        not a failure). Never tolerant of an invalid file once the directory
        exists: a schema-invalid archetype is a loud
        :class:`jsonschema.exceptions.ValidationError`, and a present-but-
        unreadable schema file is a loud ``FileNotFoundError``/``OSError``.
        """
        archetypes_dir = self._root.parent / "archetypes"
        if not archetypes_dir.is_dir():
            return

        archetype_paths = sorted(
            p for p in archetypes_dir.glob("*.json") if p.name != _ARCHETYPE_SCHEMA_NAME
        )
        if not archetype_paths:
            return

        schema = json.loads((archetypes_dir / _ARCHETYPE_SCHEMA_NAME).read_text(encoding="utf-8"))
        for path in archetype_paths:
            raw = path.read_bytes()
            data = json.loads(raw)
            jsonschema.validate(instance=data, schema=schema)
            archetype = EventArchetype.model_validate(data)
            self._archetype_bytes[path.name] = raw
            for event_type in archetype.event_types:
                self._archetypes[event_type] = archetype

    def get(self, name: str) -> str:
        """Return narrator prompt text by artifact stem.

        :param name: Artifact stem (filename without the ``.txt`` suffix).
        :returns: The prompt text content.
        :raises KeyError: If no artifact with that stem was loaded.
        """
        return self._prompts[name]

    def archetype_for(self, event_type: str) -> EventArchetype | None:
        """Return the archetype registered for ``event_type``, if any.

        :param event_type: An ``EventType`` value string as it appears in an
            archetype JSON file's ``event_types`` list (uppercased, e.g.
            ``"UPRISING"``).
        :returns: The matching :class:`EventArchetype`, or ``None`` if no
            loaded archetype declares this event type.
        """
        return self._archetypes.get(event_type)

    def version(self) -> str:
        """Return a content-derived version covering prompts and archetypes.

        Hashes ``(name, bytes)`` pairs for every narrator prompt AND every
        archetype JSON file, sorted for determinism, so an edited artifact of
        either kind can never ship with a stale version pin.

        :returns: ``"sha256:<12 hex chars>"`` derived from artifact content.
        """
        h = hashlib.sha256()
        for name in sorted(self._prompts):
            h.update(name.encode("utf-8"))
            h.update(b"\x00")
            h.update(self._prompts[name].encode("utf-8"))
        for name in sorted(self._archetype_bytes):
            h.update(name.encode("utf-8"))
            h.update(b"\x00")
            h.update(self._archetype_bytes[name])
        return f"sha256:{h.hexdigest()[:12]}"


@lru_cache(maxsize=1)
def get_prompt_registry() -> PromptRegistry:
    """Return the process-wide registry over the default artifact directory.

    :returns: The cached :class:`PromptRegistry` singleton (narrator prompts
        + event archetypes).
    """
    return PromptRegistry()
