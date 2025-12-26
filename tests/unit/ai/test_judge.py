"""Tests for NarrativeCommissar - LLM-as-judge for narrative evaluation.

TDD Red Phase: Define expected behavior before implementation.

The NarrativeCommissar evaluates narrative quality using structured prompting
to extract consistent metrics. This enables automated verification of the
"Dialectical U-Curve" hypothesis - that narrative certainty follows a U-shape
across economic conditions.

Test Classes:
    TestMetaphorFamilyEnum: Enum value validation.
    TestJudgmentResultModel: Pydantic model bounds (1-10 for metrics).
    TestNarrativeCommissarProtocol: Protocol compliance, has name property.
    TestNarrativeCommissarEvaluation: evaluate() returns JudgmentResult.
    TestJSONExtraction: Handles markdown code blocks, plain JSON.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

if TYPE_CHECKING:
    from babylon.ai.judge import NarrativeCommissar


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_json_response() -> str:
    """Valid JSON response from LLM."""
    return '{"ominousness": 7, "certainty": 8, "drama": 6, "metaphor_family": "biological"}'


@pytest.fixture
def commissar_with_mock(mock_json_response: str) -> NarrativeCommissar:
    """NarrativeCommissar with MockLLM returning valid JSON."""
    from babylon.ai import MockLLM
    from babylon.ai.judge import NarrativeCommissar

    mock_llm = MockLLM(responses=[mock_json_response])
    return NarrativeCommissar(llm=mock_llm)


# =============================================================================
# TEST CLASS: MetaphorFamily Enum
# =============================================================================


@pytest.mark.unit
class TestMetaphorFamilyEnum:
    """Tests for MetaphorFamily enum values and validation."""

    def test_biological_value(self) -> None:
        """MetaphorFamily.BIOLOGICAL has value 'biological'."""
        from babylon.ai.judge import MetaphorFamily

        assert MetaphorFamily.BIOLOGICAL.value == "biological"

    def test_physics_value(self) -> None:
        """MetaphorFamily.PHYSICS has value 'physics'."""
        from babylon.ai.judge import MetaphorFamily

        assert MetaphorFamily.PHYSICS.value == "physics"

    def test_mechanical_value(self) -> None:
        """MetaphorFamily.MECHANICAL has value 'mechanical'."""
        from babylon.ai.judge import MetaphorFamily

        assert MetaphorFamily.MECHANICAL.value == "mechanical"

    def test_none_value(self) -> None:
        """MetaphorFamily.NONE has value 'none'."""
        from babylon.ai.judge import MetaphorFamily

        assert MetaphorFamily.NONE.value == "none"

    def test_invalid_family_raises(self) -> None:
        """Invalid string raises ValueError when converting to MetaphorFamily."""
        from babylon.ai.judge import MetaphorFamily

        with pytest.raises(ValueError):
            MetaphorFamily("invalid_family")


# =============================================================================
# TEST CLASS: JudgmentResult Model
# =============================================================================


@pytest.mark.unit
class TestJudgmentResultModel:
    """Tests for JudgmentResult Pydantic model bounds and immutability."""

    def test_valid_judgment_result_construction(self) -> None:
        """JudgmentResult accepts valid values within bounds."""
        from babylon.ai.judge import JudgmentResult, MetaphorFamily

        result = JudgmentResult(
            ominousness=7,
            certainty=8,
            drama=6,
            metaphor_family=MetaphorFamily.BIOLOGICAL,
        )

        assert result.ominousness == 7
        assert result.certainty == 8
        assert result.drama == 6
        assert result.metaphor_family == MetaphorFamily.BIOLOGICAL

    def test_ominousness_below_minimum_raises(self) -> None:
        """ominousness < 1 raises ValidationError."""
        from babylon.ai.judge import JudgmentResult, MetaphorFamily

        with pytest.raises(ValidationError) as exc_info:
            JudgmentResult(
                ominousness=0,
                certainty=5,
                drama=5,
                metaphor_family=MetaphorFamily.NONE,
            )

        # Verify the error is about ominousness
        errors = exc_info.value.errors()
        assert any("ominousness" in str(e.get("loc", ())) for e in errors)

    def test_ominousness_above_maximum_raises(self) -> None:
        """ominousness > 10 raises ValidationError."""
        from babylon.ai.judge import JudgmentResult, MetaphorFamily

        with pytest.raises(ValidationError) as exc_info:
            JudgmentResult(
                ominousness=11,
                certainty=5,
                drama=5,
                metaphor_family=MetaphorFamily.NONE,
            )

        errors = exc_info.value.errors()
        assert any("ominousness" in str(e.get("loc", ())) for e in errors)

    def test_certainty_bounds_validation(self) -> None:
        """certainty must be 1-10, values outside raise ValidationError."""
        from babylon.ai.judge import JudgmentResult, MetaphorFamily

        # Below minimum
        with pytest.raises(ValidationError):
            JudgmentResult(
                ominousness=5,
                certainty=0,
                drama=5,
                metaphor_family=MetaphorFamily.NONE,
            )

        # Above maximum
        with pytest.raises(ValidationError):
            JudgmentResult(
                ominousness=5,
                certainty=11,
                drama=5,
                metaphor_family=MetaphorFamily.NONE,
            )

    def test_drama_bounds_validation(self) -> None:
        """drama must be 1-10, values outside raise ValidationError."""
        from babylon.ai.judge import JudgmentResult, MetaphorFamily

        # Below minimum
        with pytest.raises(ValidationError):
            JudgmentResult(
                ominousness=5,
                certainty=5,
                drama=0,
                metaphor_family=MetaphorFamily.NONE,
            )

        # Above maximum
        with pytest.raises(ValidationError):
            JudgmentResult(
                ominousness=5,
                certainty=5,
                drama=11,
                metaphor_family=MetaphorFamily.NONE,
            )

    def test_judgment_result_is_immutable(self) -> None:
        """JudgmentResult is frozen (immutable)."""
        from babylon.ai.judge import JudgmentResult, MetaphorFamily

        result = JudgmentResult(
            ominousness=5,
            certainty=5,
            drama=5,
            metaphor_family=MetaphorFamily.NONE,
        )

        # Attempting to modify should raise an error
        with pytest.raises((ValidationError, TypeError, AttributeError)):
            result.ominousness = 10  # type: ignore[misc]


# =============================================================================
# TEST CLASS: NarrativeCommissar Protocol
# =============================================================================


@pytest.mark.unit
class TestNarrativeCommissarProtocol:
    """Tests for NarrativeCommissar protocol compliance."""

    def test_commissar_has_name_property(self) -> None:
        """NarrativeCommissar has name property returning 'NarrativeCommissar'."""
        from babylon.ai import MockLLM
        from babylon.ai.judge import NarrativeCommissar

        mock_llm = MockLLM()
        commissar = NarrativeCommissar(llm=mock_llm)

        assert commissar.name == "NarrativeCommissar"

    def test_commissar_accepts_llm_provider(self) -> None:
        """NarrativeCommissar constructor takes LLMProvider."""
        from babylon.ai import MockLLM
        from babylon.ai.judge import NarrativeCommissar

        mock_llm = MockLLM()
        # Should not raise
        commissar = NarrativeCommissar(llm=mock_llm)
        assert commissar is not None


# =============================================================================
# TEST CLASS: NarrativeCommissar Evaluation
# =============================================================================


@pytest.mark.unit
class TestNarrativeCommissarEvaluation:
    """Tests for NarrativeCommissar.evaluate() method."""

    def test_evaluate_returns_judgment_result(
        self, commissar_with_mock: NarrativeCommissar
    ) -> None:
        """evaluate() returns a JudgmentResult instance."""
        from babylon.ai.judge import JudgmentResult

        result = commissar_with_mock.evaluate("The proletariat rises.")

        assert isinstance(result, JudgmentResult)

    def test_evaluate_parses_ominousness(self, commissar_with_mock: NarrativeCommissar) -> None:
        """evaluate() correctly extracts ominousness from LLM response."""
        result = commissar_with_mock.evaluate("Test narrative text.")

        assert result.ominousness == 7

    def test_evaluate_parses_metaphor_family(self, commissar_with_mock: NarrativeCommissar) -> None:
        """evaluate() correctly extracts MetaphorFamily from LLM response."""
        from babylon.ai.judge import MetaphorFamily

        result = commissar_with_mock.evaluate("Test narrative text.")

        assert result.metaphor_family == MetaphorFamily.BIOLOGICAL

    def test_evaluate_passes_text_to_llm(self) -> None:
        """evaluate() passes the input text to the LLM provider."""
        from babylon.ai import MockLLM
        from babylon.ai.judge import NarrativeCommissar

        json_response = '{"ominousness": 5, "certainty": 5, "drama": 5, "metaphor_family": "none"}'
        mock_llm = MockLLM(responses=[json_response])
        commissar = NarrativeCommissar(llm=mock_llm)

        test_text = "The bourgeoisie trembles as their empire crumbles."
        commissar.evaluate(test_text)

        # Verify the text was passed to the LLM
        assert len(mock_llm.call_history) == 1
        assert test_text in mock_llm.call_history[0]["prompt"]

    def test_evaluate_uses_system_prompt(self) -> None:
        """evaluate() provides a system prompt to the LLM."""
        from babylon.ai import MockLLM
        from babylon.ai.judge import NarrativeCommissar

        json_response = '{"ominousness": 5, "certainty": 5, "drama": 5, "metaphor_family": "none"}'
        mock_llm = MockLLM(responses=[json_response])
        commissar = NarrativeCommissar(llm=mock_llm)

        commissar.evaluate("Test text.")

        # Verify system prompt was provided
        assert mock_llm.call_history[0]["system_prompt"] is not None


# =============================================================================
# TEST CLASS: JSON Extraction
# =============================================================================


@pytest.mark.unit
class TestJSONExtraction:
    """Tests for JSON extraction from various LLM response formats."""

    def test_extracts_json_from_markdown_block(self) -> None:
        """Handles LLM response wrapped in ```json ... ``` block."""
        from babylon.ai import MockLLM
        from babylon.ai.judge import NarrativeCommissar

        markdown_response = """```json
{"ominousness": 3, "certainty": 9, "drama": 2, "metaphor_family": "physics"}
```"""
        mock_llm = MockLLM(responses=[markdown_response])
        commissar = NarrativeCommissar(llm=mock_llm)

        result = commissar.evaluate("Test text.")

        assert result.ominousness == 3
        assert result.certainty == 9

    def test_extracts_plain_json(self) -> None:
        """Handles raw JSON response without markdown."""
        from babylon.ai import MockLLM
        from babylon.ai.judge import NarrativeCommissar

        plain_response = (
            '{"ominousness": 8, "certainty": 4, "drama": 9, "metaphor_family": "mechanical"}'
        )
        mock_llm = MockLLM(responses=[plain_response])
        commissar = NarrativeCommissar(llm=mock_llm)

        result = commissar.evaluate("Test text.")

        assert result.ominousness == 8
        assert result.drama == 9

    def test_handles_json_with_whitespace(self) -> None:
        """Handles JSON with leading/trailing whitespace."""
        from babylon.ai import MockLLM
        from babylon.ai.judge import NarrativeCommissar

        whitespace_response = """

  {"ominousness": 6, "certainty": 6, "drama": 6, "metaphor_family": "none"}

"""
        mock_llm = MockLLM(responses=[whitespace_response])
        commissar = NarrativeCommissar(llm=mock_llm)

        result = commissar.evaluate("Test text.")

        assert result.ominousness == 6
        assert result.metaphor_family.value == "none"


# =============================================================================
# TEST CLASS: Module Exports
# =============================================================================


@pytest.mark.unit
class TestJudgeModuleExports:
    """Tests for module-level exports from babylon.ai."""

    def test_narrative_commissar_exports_from_ai_module(self) -> None:
        """NarrativeCommissar can be imported from babylon.ai."""
        from babylon.ai import NarrativeCommissar

        assert NarrativeCommissar is not None

    def test_judgment_result_exports_from_ai_module(self) -> None:
        """JudgmentResult can be imported from babylon.ai."""
        from babylon.ai import JudgmentResult

        assert JudgmentResult is not None

    def test_metaphor_family_exports_from_ai_module(self) -> None:
        """MetaphorFamily can be imported from babylon.ai."""
        from babylon.ai import MetaphorFamily

        assert MetaphorFamily is not None
