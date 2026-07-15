"""Tests for RIOT-style event archetypes — AI-fillable narration templates.

Program 20 Track B (task B1b) / emergent-endgames ruling: structure without
scripting. An :class:`~babylon.intelligence.ai.prompt_registry.EventArchetype`
gives the narrator a fixed set of slots + guidance text keyed by EventType;
the AI fills the slots from *observed engine state*, it never invents
content (Constitution III.12 — durable spec artifacts; III.11 — loud
failure). This extends the versioned narrator-prompt registry landed in
Task B1 (``prompt_registry.py``, commit fa6b2ea8).

Real EventType verification (rg'd against
``src/babylon/models/enums/events.py`` — see Task B1b brief step: "verify
real EventType values before writing archetype event_types"): the brief's
illustrative ``event_types`` ("RIOT", "UNREST", "SPONTANEOUS_UPRISING") do
NOT exist as ``EventType`` members. Substituted real members, each also
verified present in ``SimulationEngine._convert_bus_event_to_pydantic``
(``src/babylon/engine/simulation_engine.py``) so the archetype can actually
be reached by a typed event at runtime, not just exist as an unused label:

- ``riot``        -> UPRISING (docstring: "The Explosion (Riot/Insurrection)"),
                     SPONTANEOUS_RIOT ("L_u volatility-gated undirected disorder")
- ``rupture``      -> RUPTURE ("Contradiction tension reached critical
                     threshold"), PERIPHERAL_REVOLT (PeripheralRevoltEvent
                     docstring, struggle_payloads.py: "Emitted when the
                     Periphery Proletariat's P(S|R) > P(S|A) (Terminal Crisis
                     Dynamics)" — the literal Survival Calculus rupture
                     condition from CLAUDE.md section 7)
- ``unrest_wave``  -> CLASS_DECOMPOSITION ("LA splits into enforcers +
                     internal proletariat"), DISPOSSESSION_CASCADE ("LA share
                     decline milestone"), RED_BROWN_COUP ("majority LA
                     defection captures the org") — three real, wired events
                     that together model a spreading Labor-Aristocracy
                     fracture, distinct from a single riot flashpoint or a
                     survival-calculus tipping point.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from babylon.intelligence.ai.prompt_registry import (
    EventArchetype,
    PromptRegistry,
    get_prompt_registry,
)
from babylon.models import (
    SocialClass,
    SocialRole,
    WorldState,
)
from babylon.models.entity_registry import COMPRADOR_ID, PERIPHERY_WORKER_ID
from babylon.models.events import (
    ExtractionEvent,
    PeripheralRevoltEvent,
    RuptureEvent,
    UprisingEvent,
)

# =============================================================================
# A minimal local mirror of archetype.schema.json's required-field contract.
# Kept separate from the real schema file so these tests exercise the
# validation BEHAVIOR (loud rejection) without coupling to the canonical
# schema's exact wording; the real schema is exercised end-to-end by the
# TestArchetypeLoading tests below, which load the actual project files via
# get_prompt_registry().
# =============================================================================
_TEST_ARCHETYPE_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": ["id", "event_types", "slots", "guidance"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "string"},
        "event_types": {"type": "array", "items": {"type": "string"}},
        "slots": {"type": "array", "items": {"type": "string"}},
        "guidance": {"type": "string"},
    },
}


def _write_schema(archetypes_dir: Path) -> None:
    (archetypes_dir / "archetype.schema.json").write_text(
        json.dumps(_TEST_ARCHETYPE_SCHEMA), encoding="utf-8"
    )


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def state_with_entities() -> WorldState:
    """WorldState with a worker/owner pair, no relationships."""
    worker = SocialClass(
        id=PERIPHERY_WORKER_ID,
        name="Worker",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=0.5,
        ideology=0.0,
        organization=0.1,
        repression_faced=0.5,
        subsistence_threshold=0.3,
    )
    owner = SocialClass(
        id=COMPRADOR_ID,
        name="Owner",
        role=SocialRole.CORE_BOURGEOISIE,
        wealth=10.0,
        ideology=0.5,
        organization=0.7,
        repression_faced=0.1,
        subsistence_threshold=0.1,
    )
    return WorldState(
        tick=5,
        entities={PERIPHERY_WORKER_ID: worker, COMPRADOR_ID: owner},
        relationships=[],
    )


# =============================================================================
# TEST ARCHETYPE LOADING + LOOKUP (real project archetypes/)
# =============================================================================


@pytest.mark.unit
class TestArchetypeLoading:
    """archetype_for() resolves real archetype files shipped in
    src/babylon/data/game/prompts/archetypes/.
    """

    def test_riot_archetype_matches_uprising(self) -> None:
        archetype = get_prompt_registry().archetype_for("UPRISING")
        assert archetype is not None
        assert archetype.id == "riot"

    def test_riot_archetype_matches_spontaneous_riot(self) -> None:
        archetype = get_prompt_registry().archetype_for("SPONTANEOUS_RIOT")
        assert archetype is not None
        assert archetype.id == "riot"

    def test_rupture_archetype_matches_rupture(self) -> None:
        archetype = get_prompt_registry().archetype_for("RUPTURE")
        assert archetype is not None
        assert archetype.id == "rupture"

    def test_rupture_archetype_matches_peripheral_revolt(self) -> None:
        archetype = get_prompt_registry().archetype_for("PERIPHERAL_REVOLT")
        assert archetype is not None
        assert archetype.id == "rupture"

    def test_unrest_wave_archetype_matches_class_decomposition(self) -> None:
        archetype = get_prompt_registry().archetype_for("CLASS_DECOMPOSITION")
        assert archetype is not None
        assert archetype.id == "unrest_wave"

    def test_unrest_wave_archetype_matches_dispossession_cascade(self) -> None:
        archetype = get_prompt_registry().archetype_for("DISPOSSESSION_CASCADE")
        assert archetype is not None
        assert archetype.id == "unrest_wave"

    def test_unrest_wave_archetype_matches_red_brown_coup(self) -> None:
        archetype = get_prompt_registry().archetype_for("RED_BROWN_COUP")
        assert archetype is not None
        assert archetype.id == "unrest_wave"

    def test_unknown_event_type_string_returns_none(self) -> None:
        assert get_prompt_registry().archetype_for("NOT_A_REAL_EVENT_TYPE") is None

    def test_real_but_unmapped_event_type_returns_none(self) -> None:
        """SURPLUS_EXTRACTION is a real EventType with no archetype."""
        assert get_prompt_registry().archetype_for("SURPLUS_EXTRACTION") is None

    def test_archetype_is_frozen_pydantic_model(self) -> None:
        archetype = get_prompt_registry().archetype_for("UPRISING")
        assert isinstance(archetype, EventArchetype)
        with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError on frozen model
            archetype.id = "mutated"  # type: ignore[misc]

    def test_every_declared_event_type_resolves_back_to_same_archetype(self) -> None:
        riot = get_prompt_registry().archetype_for("UPRISING")
        assert riot is not None
        for event_type in riot.event_types:
            assert get_prompt_registry().archetype_for(event_type) is riot


# =============================================================================
# TEST SCHEMA VALIDATION — loud failure (III.11)
# =============================================================================


@pytest.mark.unit
class TestArchetypeSchemaValidation:
    """Invalid archetype JSON fails loudly at load time; absent dir does not."""

    def test_invalid_archetype_json_missing_field_raises_loud(self, tmp_path: Path) -> None:
        narrator_dir = tmp_path / "prompts"
        narrator_dir.mkdir()
        (narrator_dir / "a.txt").write_text("hello", encoding="utf-8")

        archetypes_dir = tmp_path / "archetypes"
        archetypes_dir.mkdir()
        _write_schema(archetypes_dir)
        (archetypes_dir / "broken.json").write_text(
            json.dumps({"id": "broken", "event_types": ["UPRISING"], "slots": ["x"]}),
            encoding="utf-8",
        )  # missing required "guidance"

        with pytest.raises(jsonschema.exceptions.ValidationError):
            PromptRegistry(narrator_dir)

    def test_invalid_archetype_json_extra_field_raises_loud(self, tmp_path: Path) -> None:
        narrator_dir = tmp_path / "prompts"
        narrator_dir.mkdir()
        (narrator_dir / "a.txt").write_text("hello", encoding="utf-8")

        archetypes_dir = tmp_path / "archetypes"
        archetypes_dir.mkdir()
        _write_schema(archetypes_dir)
        (archetypes_dir / "broken.json").write_text(
            json.dumps(
                {
                    "id": "broken",
                    "event_types": ["UPRISING"],
                    "slots": ["x"],
                    "guidance": "g",
                    "invented_field": "not allowed",
                }
            ),
            encoding="utf-8",
        )  # additionalProperties: false

        with pytest.raises(jsonschema.exceptions.ValidationError):
            PromptRegistry(narrator_dir)

    def test_absent_archetypes_dir_is_tolerated(self, tmp_path: Path) -> None:
        """Data simply not present is not a failure (brief step 5)."""
        narrator_dir = tmp_path / "prompts"
        narrator_dir.mkdir()
        (narrator_dir / "a.txt").write_text("hello", encoding="utf-8")
        # Deliberately no sibling "archetypes" dir at all.

        reg = PromptRegistry(narrator_dir)

        assert reg.archetype_for("UPRISING") is None
        assert reg.version().startswith("sha256:")


# =============================================================================
# TEST LOUD FAILURE PATHS — narrator prompt dir (carried-over B1 minor #1)
# =============================================================================


@pytest.mark.unit
class TestNarratorDirLoudFailurePaths:
    """PromptRegistry's pre-existing loud-failure paths, now covered by tests."""

    def test_missing_prompt_dir_raises_file_not_found(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist"
        with pytest.raises(FileNotFoundError):
            PromptRegistry(missing)

    def test_empty_prompt_dir_raises_file_not_found(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty_prompts"
        empty.mkdir()
        with pytest.raises(FileNotFoundError):
            PromptRegistry(empty)


# =============================================================================
# TEST version() INCORPORATES ARCHETYPE BYTES
# =============================================================================


@pytest.mark.unit
class TestVersionIncorporatesArchetypes:
    """version() must change when archetype content changes (drift can't hide)."""

    def test_version_changes_when_archetype_content_changes(self, tmp_path: Path) -> None:
        narrator_dir = tmp_path / "prompts"
        narrator_dir.mkdir()
        (narrator_dir / "a.txt").write_text("alpha", encoding="utf-8")

        archetypes_dir = tmp_path / "archetypes"
        archetypes_dir.mkdir()
        _write_schema(archetypes_dir)
        archetype_path = archetypes_dir / "riot.json"
        archetype_path.write_text(
            json.dumps(
                {"id": "riot", "event_types": ["UPRISING"], "slots": ["location"], "guidance": "v1"}
            ),
            encoding="utf-8",
        )

        v1 = PromptRegistry(narrator_dir).version()

        archetype_path.write_text(
            json.dumps(
                {
                    "id": "riot",
                    "event_types": ["UPRISING"],
                    "slots": ["location"],
                    "guidance": "v2 CHANGED",
                }
            ),
            encoding="utf-8",
        )

        v2 = PromptRegistry(narrator_dir).version()

        assert v1 != v2

    def test_version_differs_with_vs_without_archetypes_dir(self, tmp_path: Path) -> None:
        narrator_dir = tmp_path / "prompts"
        narrator_dir.mkdir()
        (narrator_dir / "a.txt").write_text("alpha", encoding="utf-8")

        v_without = PromptRegistry(narrator_dir).version()

        archetypes_dir = tmp_path / "archetypes"
        archetypes_dir.mkdir()
        _write_schema(archetypes_dir)
        (archetypes_dir / "riot.json").write_text(
            json.dumps(
                {"id": "riot", "event_types": ["UPRISING"], "slots": ["location"], "guidance": "g"}
            ),
            encoding="utf-8",
        )

        v_with = PromptRegistry(narrator_dir).version()

        assert v_without != v_with

    def test_default_registry_version_still_content_hash_shaped(self) -> None:
        """The real, default-directory registry (narrator + archetypes) still
        produces the documented ``sha256:<12 hex>`` shape.
        """
        v = get_prompt_registry().version()
        assert v.startswith("sha256:") and len(v) == len("sha256:") + 12


# =============================================================================
# TEST prompt_builder INTEGRATION — _build_archetype_section
# =============================================================================


@pytest.mark.unit
class TestArchetypeSectionInContextBlock:
    """build_context_block() folds in an EVENT ARCHETYPE section only when a
    typed event's type matches a registered archetype (no unconditional
    prompt bloat).
    """

    def test_context_block_includes_archetype_guidance_and_slots(
        self,
        state_with_entities: WorldState,
    ) -> None:
        from babylon.intelligence.ai.prompt_builder import DialecticalPromptBuilder

        builder = DialecticalPromptBuilder()
        uprising = UprisingEvent(
            tick=5,
            node_id=PERIPHERY_WORKER_ID,
            trigger="spark",
            agitation=0.9,
            repression=0.6,
        )

        context = builder.build_context_block(
            state=state_with_entities,
            rag_context=["ctx"],
            events=[uprising],
        )

        archetype = get_prompt_registry().archetype_for("UPRISING")
        assert archetype is not None
        assert "EVENT ARCHETYPE: riot" in context
        assert archetype.guidance in context
        for slot in archetype.slots:
            assert slot in context

    def test_context_block_archetype_section_for_peripheral_revolt(
        self,
        state_with_entities: WorldState,
    ) -> None:
        from babylon.intelligence.ai.prompt_builder import DialecticalPromptBuilder

        builder = DialecticalPromptBuilder()
        revolt = PeripheralRevoltEvent(
            tick=5,
            node_id=PERIPHERY_WORKER_ID,
            edges_severed=3,
            p_acquiescence=0.2,
            p_revolution=0.8,
            capital_labor_gap=0.6,
            narrative_hint="periphery breaks",
        )

        context = builder.build_context_block(
            state=state_with_entities,
            rag_context=["ctx"],
            events=[revolt],
        )

        assert "EVENT ARCHETYPE: rupture" in context

    def test_context_block_omits_archetype_section_without_match(
        self,
        state_with_entities: WorldState,
    ) -> None:
        from babylon.intelligence.ai.prompt_builder import DialecticalPromptBuilder

        builder = DialecticalPromptBuilder()
        extraction = ExtractionEvent(
            tick=5,
            source_id=PERIPHERY_WORKER_ID,
            target_id=COMPRADOR_ID,
            amount=10.0,
        )

        context = builder.build_context_block(
            state=state_with_entities,
            rag_context=["ctx"],
            events=[extraction],
        )

        assert "EVENT ARCHETYPE" not in context

    def test_context_block_omits_archetype_section_with_no_events(
        self,
        state_with_entities: WorldState,
    ) -> None:
        from babylon.intelligence.ai.prompt_builder import DialecticalPromptBuilder

        builder = DialecticalPromptBuilder()

        context = builder.build_context_block(
            state=state_with_entities,
            rag_context=["ctx"],
            events=[],
        )

        assert "EVENT ARCHETYPE" not in context

    def test_context_block_uses_first_matching_event_only(
        self,
        state_with_entities: WorldState,
    ) -> None:
        """Only the FIRST event whose type has an archetype contributes a
        section — no stacking of multiple archetype blocks.
        """
        from babylon.intelligence.ai.prompt_builder import DialecticalPromptBuilder

        builder = DialecticalPromptBuilder()
        extraction = ExtractionEvent(
            tick=5,
            source_id=PERIPHERY_WORKER_ID,
            target_id=COMPRADOR_ID,
            amount=10.0,
        )
        uprising = UprisingEvent(
            tick=5,
            node_id=PERIPHERY_WORKER_ID,
            trigger="spark",
            agitation=0.9,
            repression=0.6,
        )
        rupture = RuptureEvent(tick=5, edge="A->B")

        context = builder.build_context_block(
            state=state_with_entities,
            rag_context=["ctx"],
            events=[extraction, uprising, rupture],
        )

        assert "EVENT ARCHETYPE: riot" in context
        assert "EVENT ARCHETYPE: rupture" not in context
        # Exactly one archetype section, not two.
        assert context.count("--- EVENT ARCHETYPE:") == 1
