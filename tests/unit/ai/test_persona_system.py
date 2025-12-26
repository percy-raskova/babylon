"""Tests for the Persona System (Sprint 4.2).

TDD test suite for JSON Schema-validated personas that provide
customizable AI narrative voices for the NarrativeDirector.

Test Classes:
- TestPersonaSchema: JSON Schema validation tests
- TestPersonaModel: Pydantic model construction and immutability
- TestRenderSystemPrompt: render_system_prompt() output formatting
- TestPersonaLoader: File loading and validation functions
- TestPromptBuilderPersonaIntegration: PromptBuilder integration
- TestNarrativeDirectorPersonaIntegration: Full integration with MockLLM
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from jsonschema import Draft202012Validator, ValidationError

if TYPE_CHECKING:
    pass

# ===========================================================================
# Schema Paths (for test setup before implementation exists)
# ===========================================================================

_SCHEMAS_DIR = Path(__file__).parent.parent.parent.parent / "src" / "babylon" / "schemas"
_PERSONA_SCHEMA_PATH = _SCHEMAS_DIR / "entities" / "persona.schema.json"


# ===========================================================================
# Test Fixtures
# ===========================================================================


@pytest.fixture
def valid_persona_data() -> dict[str, Any]:
    """Return valid persona data for testing."""
    return {
        "id": "persephone_raskova",
        "name": "Persephone 'Percy' Raskova",
        "role": "Senior Archivist / Narrative Director",
        "voice": {
            "tone": "Clinical, Dialectical, Revolutionary, slightly Ominous",
            "style": "High-theoretical Marxist analysis mixed with Cybernetic systems theory.",
            "address_user_as": "Architect",
        },
        "obsessions": [
            "The inevitable collapse of hegemonic systems",
            "The material basis of all political events",
        ],
        "directives": [
            "Never moralize; analyze power dynamics and material flows.",
            "Be concise. Do not offer hope without organization.",
        ],
    }


@pytest.fixture
def persona_schema() -> dict[str, Any]:
    """Load the persona schema from disk if it exists.

    This fixture will fail until the schema is created.
    """
    if not _PERSONA_SCHEMA_PATH.exists():
        pytest.skip("Persona schema does not exist yet (RED phase)")
    with open(_PERSONA_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def persona_validator(persona_schema: dict[str, Any]) -> Draft202012Validator:
    """Create a Draft202012 validator for the persona schema."""
    return Draft202012Validator(persona_schema)


# ===========================================================================
# TestPersonaSchema - JSON Schema Validation
# ===========================================================================


class TestPersonaSchema:
    """Test JSON Schema validation for persona data."""

    def test_valid_persona_passes_schema(
        self,
        persona_validator: Draft202012Validator,
        valid_persona_data: dict[str, Any],
    ) -> None:
        """Valid persona data should pass schema validation."""
        # Should not raise
        persona_validator.validate(valid_persona_data)

    def test_missing_required_field_fails_schema(
        self,
        persona_validator: Draft202012Validator,
        valid_persona_data: dict[str, Any],
    ) -> None:
        """Missing required fields should fail validation."""
        # Remove required field 'name'
        invalid_data = dict(valid_persona_data)
        del invalid_data["name"]

        with pytest.raises(ValidationError) as exc_info:
            persona_validator.validate(invalid_data)
        assert "name" in str(exc_info.value) or "'name'" in str(exc_info.value)

    def test_empty_obsessions_fails_schema(
        self,
        persona_validator: Draft202012Validator,
        valid_persona_data: dict[str, Any],
    ) -> None:
        """Empty obsessions array should fail (minItems: 1)."""
        invalid_data = dict(valid_persona_data)
        invalid_data["obsessions"] = []

        with pytest.raises(ValidationError) as exc_info:
            persona_validator.validate(invalid_data)
        # Schema should reject empty array due to minItems: 1
        assert "minItems" in str(exc_info.value) or "too short" in str(exc_info.value)

    def test_invalid_id_pattern_fails_schema(
        self,
        persona_validator: Draft202012Validator,
        valid_persona_data: dict[str, Any],
    ) -> None:
        """Invalid ID pattern should fail validation."""
        invalid_data = dict(valid_persona_data)
        # ID must match ^[a-z][a-z0-9_]*[a-z0-9]$ (lowercase, no special chars at start)
        invalid_data["id"] = "Invalid-ID-123"

        with pytest.raises(ValidationError) as exc_info:
            persona_validator.validate(invalid_data)
        assert "pattern" in str(exc_info.value).lower() or "Invalid" in str(exc_info.value)


# ===========================================================================
# TestPersonaModel - Pydantic Model
# ===========================================================================


class TestPersonaModel:
    """Test Persona Pydantic model construction and immutability."""

    def test_persona_model_construction(
        self,
        valid_persona_data: dict[str, Any],
    ) -> None:
        """Persona model should be constructable from valid data."""
        # Import will fail until implementation exists (RED phase)
        from babylon.ai.persona import Persona, VoiceConfig

        voice = VoiceConfig(
            tone=valid_persona_data["voice"]["tone"],
            style=valid_persona_data["voice"]["style"],
            address_user_as=valid_persona_data["voice"]["address_user_as"],
        )
        persona = Persona(
            id=valid_persona_data["id"],
            name=valid_persona_data["name"],
            role=valid_persona_data["role"],
            voice=voice,
            obsessions=valid_persona_data["obsessions"],
            directives=valid_persona_data["directives"],
        )

        assert persona.id == "persephone_raskova"
        assert persona.name == "Persephone 'Percy' Raskova"
        assert persona.role == "Senior Archivist / Narrative Director"
        assert persona.voice.tone == "Clinical, Dialectical, Revolutionary, slightly Ominous"

    def test_persona_model_is_frozen(
        self,
        valid_persona_data: dict[str, Any],
    ) -> None:
        """Persona model should be immutable (frozen)."""
        from pydantic import ValidationError as PydanticValidationError

        from babylon.ai.persona import Persona, VoiceConfig

        voice = VoiceConfig(
            tone=valid_persona_data["voice"]["tone"],
            style=valid_persona_data["voice"]["style"],
            address_user_as=valid_persona_data["voice"]["address_user_as"],
        )
        persona = Persona(
            id=valid_persona_data["id"],
            name=valid_persona_data["name"],
            role=valid_persona_data["role"],
            voice=voice,
            obsessions=valid_persona_data["obsessions"],
            directives=valid_persona_data["directives"],
        )

        # Attempting to modify should raise ValidationError
        with pytest.raises(PydanticValidationError):
            persona.name = "Modified Name"  # type: ignore[misc]

    def test_persona_restrictions_default_empty(
        self,
        valid_persona_data: dict[str, Any],
    ) -> None:
        """Persona restrictions should default to empty list."""
        from babylon.ai.persona import Persona, VoiceConfig

        voice = VoiceConfig(
            tone=valid_persona_data["voice"]["tone"],
            style=valid_persona_data["voice"]["style"],
            address_user_as=valid_persona_data["voice"]["address_user_as"],
        )
        persona = Persona(
            id=valid_persona_data["id"],
            name=valid_persona_data["name"],
            role=valid_persona_data["role"],
            voice=voice,
            obsessions=valid_persona_data["obsessions"],
            directives=valid_persona_data["directives"],
            # No restrictions provided
        )

        assert persona.restrictions == []


# ===========================================================================
# TestRenderSystemPrompt - Prompt Rendering
# ===========================================================================


class TestRenderSystemPrompt:
    """Test render_system_prompt() output formatting."""

    @pytest.fixture
    def percy_persona(self, valid_persona_data: dict[str, Any]) -> Any:
        """Create Percy persona for rendering tests."""
        from babylon.ai.persona import Persona, VoiceConfig

        voice = VoiceConfig(
            tone=valid_persona_data["voice"]["tone"],
            style=valid_persona_data["voice"]["style"],
            address_user_as=valid_persona_data["voice"]["address_user_as"],
        )
        return Persona(
            id=valid_persona_data["id"],
            name=valid_persona_data["name"],
            role=valid_persona_data["role"],
            voice=voice,
            obsessions=valid_persona_data["obsessions"],
            directives=valid_persona_data["directives"],
        )

    def test_render_includes_name_and_role(
        self,
        percy_persona: Any,
    ) -> None:
        """Rendered prompt should include persona name and role."""
        prompt = percy_persona.render_system_prompt()

        assert "Persephone 'Percy' Raskova" in prompt
        assert "Senior Archivist / Narrative Director" in prompt

    def test_render_includes_voice_attributes(
        self,
        percy_persona: Any,
    ) -> None:
        """Rendered prompt should include voice attributes."""
        prompt = percy_persona.render_system_prompt()

        assert "Clinical, Dialectical, Revolutionary" in prompt
        assert "Cybernetic systems theory" in prompt
        assert "Architect" in prompt

    def test_render_includes_obsessions(
        self,
        percy_persona: Any,
    ) -> None:
        """Rendered prompt should include obsessions."""
        prompt = percy_persona.render_system_prompt()

        assert "collapse of hegemonic systems" in prompt
        assert "material basis of all political events" in prompt

    def test_render_includes_directives(
        self,
        percy_persona: Any,
    ) -> None:
        """Rendered prompt should include directives."""
        prompt = percy_persona.render_system_prompt()

        assert "Never moralize" in prompt
        assert "Be concise" in prompt

    def test_render_includes_restrictions_when_present(
        self,
        valid_persona_data: dict[str, Any],
    ) -> None:
        """Rendered prompt should include restrictions when present."""
        from babylon.ai.persona import Persona, VoiceConfig

        voice = VoiceConfig(
            tone=valid_persona_data["voice"]["tone"],
            style=valid_persona_data["voice"]["style"],
            address_user_as=valid_persona_data["voice"]["address_user_as"],
        )
        persona = Persona(
            id=valid_persona_data["id"],
            name=valid_persona_data["name"],
            role=valid_persona_data["role"],
            voice=voice,
            obsessions=valid_persona_data["obsessions"],
            directives=valid_persona_data["directives"],
            restrictions=["Do not discuss specific real-world individuals"],
        )

        prompt = persona.render_system_prompt()
        assert "Do not discuss specific real-world individuals" in prompt

    def test_render_omits_restrictions_section_when_empty(
        self,
        percy_persona: Any,
    ) -> None:
        """Rendered prompt should omit restrictions section when empty."""
        prompt = percy_persona.render_system_prompt()

        # When restrictions is empty, the section header should not appear
        # This is a UX consideration - don't show empty sections
        assert "RESTRICTIONS" not in prompt or "restrictions" not in prompt.lower()


# ===========================================================================
# TestPersonaLoader - File Loading Functions
# ===========================================================================


class TestPersonaLoader:
    """Test persona loader functions."""

    def test_load_persona_from_valid_file(
        self,
        valid_persona_data: dict[str, Any],
    ) -> None:
        """load_persona() should load and validate a valid JSON file."""
        from babylon.ai.persona_loader import load_persona

        # Create temp file with valid data
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        ) as f:
            json.dump(valid_persona_data, f)
            temp_path = Path(f.name)

        try:
            persona = load_persona(temp_path)
            assert persona.id == "persephone_raskova"
            assert persona.name == "Persephone 'Percy' Raskova"
        finally:
            temp_path.unlink()

    def test_load_persona_raises_on_missing_file(self) -> None:
        """load_persona() should raise on missing file."""
        from babylon.ai.persona_loader import PersonaLoadError, load_persona

        nonexistent_path = Path("/nonexistent/path/persona.json")

        with pytest.raises(PersonaLoadError) as exc_info:
            load_persona(nonexistent_path)

        assert exc_info.value.path == nonexistent_path

    def test_load_persona_raises_on_invalid_json(self) -> None:
        """load_persona() should raise on invalid JSON."""
        from babylon.ai.persona_loader import PersonaLoadError, load_persona

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write("{ invalid json }")
            temp_path = Path(f.name)

        try:
            with pytest.raises(PersonaLoadError):
                load_persona(temp_path)
        finally:
            temp_path.unlink()

    def test_load_persona_raises_on_schema_violation(self) -> None:
        """load_persona() should raise on schema violation."""
        from babylon.ai.persona_loader import PersonaLoadError, load_persona

        invalid_data = {
            "id": "Invalid-ID",  # Invalid pattern
            "name": "Test",
            "role": "Test",
            "voice": {
                "tone": "Test",
                "style": "Test",
                "address_user_as": "Test",
            },
            "obsessions": [],  # Empty (minItems: 1 violation)
            "directives": ["Test"],
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        ) as f:
            json.dump(invalid_data, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(PersonaLoadError) as exc_info:
                load_persona(temp_path)
            # Should contain error details
            assert len(exc_info.value.errors) > 0
        finally:
            temp_path.unlink()

    def test_load_default_persona_returns_percy(self) -> None:
        """load_default_persona() should return Percy Raskova."""
        from babylon.ai.persona_loader import load_default_persona

        persona = load_default_persona()

        assert persona.id == "persephone_raskova"
        assert "Percy" in persona.name
        # Check structure exists, not specific content (which may change)
        assert len(persona.voice.style) > 0
        assert len(persona.voice.tone) > 0


# ===========================================================================
# TestPromptBuilderPersonaIntegration - PromptBuilder Integration
# ===========================================================================


class TestPromptBuilderPersonaIntegration:
    """Test PromptBuilder integration with Persona."""

    @pytest.fixture
    def percy_persona(self, valid_persona_data: dict[str, Any]) -> Any:
        """Create Percy persona for integration tests."""
        from babylon.ai.persona import Persona, VoiceConfig

        voice = VoiceConfig(
            tone=valid_persona_data["voice"]["tone"],
            style=valid_persona_data["voice"]["style"],
            address_user_as=valid_persona_data["voice"]["address_user_as"],
        )
        return Persona(
            id=valid_persona_data["id"],
            name=valid_persona_data["name"],
            role=valid_persona_data["role"],
            voice=voice,
            obsessions=valid_persona_data["obsessions"],
            directives=valid_persona_data["directives"],
        )

    def test_prompt_builder_uses_persona_when_provided(
        self,
        percy_persona: Any,
    ) -> None:
        """PromptBuilder should use persona for system prompt when provided."""
        from babylon.ai.prompt_builder import DialecticalPromptBuilder

        builder = DialecticalPromptBuilder(persona=percy_persona)
        system_prompt = builder.build_system_prompt()

        # Should use Percy's voice, not the default
        assert "Percy" in system_prompt or "Architect" in system_prompt
        assert "Cybernetic systems theory" in system_prompt

    def test_prompt_builder_uses_default_without_persona(self) -> None:
        """PromptBuilder should use default system prompt without persona."""
        from babylon.ai.prompt_builder import DialecticalPromptBuilder

        builder = DialecticalPromptBuilder()  # No persona
        system_prompt = builder.build_system_prompt()

        # Should use the default Marxist game master prompt
        assert "game master" in system_prompt.lower()
        assert "dialectical materialism" in system_prompt.lower()

    def test_prompt_builder_persona_property(
        self,
        percy_persona: Any,
    ) -> None:
        """PromptBuilder should expose persona via property."""
        from babylon.ai.prompt_builder import DialecticalPromptBuilder

        builder = DialecticalPromptBuilder(persona=percy_persona)

        assert builder.persona is not None
        assert builder.persona.id == "persephone_raskova"


# ===========================================================================
# TestNarrativeDirectorPersonaIntegration - Full Integration with MockLLM
# ===========================================================================


class TestNarrativeDirectorPersonaIntegration:
    """Test NarrativeDirector integration with Persona and MockLLM."""

    @pytest.fixture
    def percy_persona(self, valid_persona_data: dict[str, Any]) -> Any:
        """Create Percy persona for integration tests."""
        from babylon.ai.persona import Persona, VoiceConfig

        voice = VoiceConfig(
            tone=valid_persona_data["voice"]["tone"],
            style=valid_persona_data["voice"]["style"],
            address_user_as=valid_persona_data["voice"]["address_user_as"],
        )
        return Persona(
            id=valid_persona_data["id"],
            name=valid_persona_data["name"],
            role=valid_persona_data["role"],
            voice=voice,
            obsessions=valid_persona_data["obsessions"],
            directives=valid_persona_data["directives"],
        )

    def test_director_accepts_persona_parameter(
        self,
        percy_persona: Any,
    ) -> None:
        """NarrativeDirector should accept persona parameter."""
        from babylon.ai.director import NarrativeDirector

        # Should not raise
        director = NarrativeDirector(persona=percy_persona)

        # Director should have been created with persona-aware builder
        assert director is not None

    def test_director_uses_persona_prompt_with_llm(
        self,
        percy_persona: Any,
    ) -> None:
        """NarrativeDirector with persona should use persona's system prompt."""
        from babylon.ai.director import NarrativeDirector
        from babylon.ai.llm_provider import MockLLM

        mock_llm = MockLLM(default_response="Mock narrative response")
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            persona=percy_persona,
        )

        # Verify the internal builder uses the persona
        assert director._prompt_builder.persona is not None
        system_prompt = director._prompt_builder.build_system_prompt()

        # Should contain Percy's voice characteristics
        assert "Cybernetic systems theory" in system_prompt

    def test_director_without_persona_uses_default_prompt(self) -> None:
        """NarrativeDirector without persona should use default prompt."""
        from babylon.ai.director import NarrativeDirector
        from babylon.ai.llm_provider import MockLLM

        mock_llm = MockLLM(default_response="Mock narrative response")
        director = NarrativeDirector(
            use_llm=True,
            llm=mock_llm,
            # No persona
        )

        system_prompt = director._prompt_builder.build_system_prompt()

        # Should use default Marxist game master prompt
        assert "game master" in system_prompt.lower()
        # Should NOT contain Percy-specific content
        assert "Cybernetic systems theory" not in system_prompt
