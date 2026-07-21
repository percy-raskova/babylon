"""Tests for NarrativeCommissar - LLM-as-judge for narrative evaluation.

Behavioral contract on the pydantic-ai structured-output transport
(Amendment Y, ADR100): the judge runs an Agent with
``output_type=JudgmentResult`` — schema validation happens at the SDK
layer with a re-prompt on failure, replacing the former hand-rolled
markdown-fence stripping and ``json.loads`` parsing.

Test Classes:
    TestMetaphorFamilyEnum: Enum value validation.
    TestJudgmentResultModel: Pydantic model bounds (1-10 for metrics).
    TestNarrativeCommissarProtocol: Protocol compliance, has name property.
    TestNarrativeCommissarEvaluation: evaluate() returns JudgmentResult.
    TestStructuredOutputValidation: schema retry + loud failure behavior.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

if TYPE_CHECKING:
    from babylon.intelligence.ai.judge import NarrativeCommissar


# =============================================================================
# FIXTURES
# =============================================================================


VALID_ARGS = {
    "ominousness": 7,
    "certainty": 8,
    "drama": 6,
    "metaphor_family": "biological",
}


@pytest.fixture
def commissar_with_mock() -> NarrativeCommissar:
    """NarrativeCommissar backed by a deterministic TestModel."""
    from babylon.intelligence.ai.judge import NarrativeCommissar

    model = TestModel(custom_output_args=VALID_ARGS)
    return NarrativeCommissar(model_factory=lambda: model)


# =============================================================================
# TEST CLASS: MetaphorFamily Enum
# =============================================================================


@pytest.mark.unit
class TestMetaphorFamilyEnum:
    """Tests for MetaphorFamily enum values and validation."""

    def test_biological_value(self) -> None:
        """MetaphorFamily.BIOLOGICAL has value 'biological'."""
        from babylon.intelligence.ai.judge import MetaphorFamily

        assert MetaphorFamily.BIOLOGICAL.value == "biological"

    def test_physics_value(self) -> None:
        """MetaphorFamily.PHYSICS has value 'physics'."""
        from babylon.intelligence.ai.judge import MetaphorFamily

        assert MetaphorFamily.PHYSICS.value == "physics"

    def test_mechanical_value(self) -> None:
        """MetaphorFamily.MECHANICAL has value 'mechanical'."""
        from babylon.intelligence.ai.judge import MetaphorFamily

        assert MetaphorFamily.MECHANICAL.value == "mechanical"

    def test_none_value(self) -> None:
        """MetaphorFamily.NONE has value 'none'."""
        from babylon.intelligence.ai.judge import MetaphorFamily

        assert MetaphorFamily.NONE.value == "none"

    def test_invalid_family_raises(self) -> None:
        """Invalid string raises ValueError when converting to MetaphorFamily."""
        from babylon.intelligence.ai.judge import MetaphorFamily

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
        from babylon.intelligence.ai.judge import JudgmentResult, MetaphorFamily

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
        from babylon.intelligence.ai.judge import JudgmentResult, MetaphorFamily

        with pytest.raises(ValidationError) as exc_info:
            JudgmentResult(
                ominousness=0,
                certainty=5,
                drama=5,
                metaphor_family=MetaphorFamily.NONE,
            )

        errors = exc_info.value.errors()
        assert any("ominousness" in str(e.get("loc", ())) for e in errors)

    def test_ominousness_above_maximum_raises(self) -> None:
        """ominousness > 10 raises ValidationError."""
        from babylon.intelligence.ai.judge import JudgmentResult, MetaphorFamily

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
        from babylon.intelligence.ai.judge import JudgmentResult, MetaphorFamily

        with pytest.raises(ValidationError):
            JudgmentResult(
                ominousness=5,
                certainty=0,
                drama=5,
                metaphor_family=MetaphorFamily.NONE,
            )

        with pytest.raises(ValidationError):
            JudgmentResult(
                ominousness=5,
                certainty=11,
                drama=5,
                metaphor_family=MetaphorFamily.NONE,
            )

    def test_drama_bounds_validation(self) -> None:
        """drama must be 1-10, values outside raise ValidationError."""
        from babylon.intelligence.ai.judge import JudgmentResult, MetaphorFamily

        with pytest.raises(ValidationError):
            JudgmentResult(
                ominousness=5,
                certainty=5,
                drama=0,
                metaphor_family=MetaphorFamily.NONE,
            )

        with pytest.raises(ValidationError):
            JudgmentResult(
                ominousness=5,
                certainty=5,
                drama=11,
                metaphor_family=MetaphorFamily.NONE,
            )

    def test_judgment_result_is_immutable(self) -> None:
        """JudgmentResult is frozen (immutable)."""
        from babylon.intelligence.ai.judge import JudgmentResult, MetaphorFamily

        result = JudgmentResult(
            ominousness=5,
            certainty=5,
            drama=5,
            metaphor_family=MetaphorFamily.NONE,
        )

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
        from babylon.intelligence.ai.judge import NarrativeCommissar

        commissar = NarrativeCommissar(model_factory=lambda: TestModel())

        assert commissar.name == "NarrativeCommissar"

    def test_commissar_accepts_model_factory(self) -> None:
        """NarrativeCommissar constructor takes a pydantic-ai ModelFactory."""
        from babylon.intelligence.ai.judge import NarrativeCommissar

        commissar = NarrativeCommissar(model_factory=lambda: TestModel())
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
        from babylon.intelligence.ai.judge import JudgmentResult

        result = commissar_with_mock.evaluate("The proletariat rises.")

        assert isinstance(result, JudgmentResult)

    def test_evaluate_parses_ominousness(self, commissar_with_mock: NarrativeCommissar) -> None:
        """evaluate() correctly extracts ominousness from the model output."""
        result = commissar_with_mock.evaluate("Test narrative text.")

        assert result.ominousness == 7

    def test_evaluate_parses_metaphor_family(self, commissar_with_mock: NarrativeCommissar) -> None:
        """evaluate() correctly extracts MetaphorFamily from the model output."""
        from babylon.intelligence.ai.judge import MetaphorFamily

        result = commissar_with_mock.evaluate("Test narrative text.")

        assert result.metaphor_family == MetaphorFamily.BIOLOGICAL

    def test_evaluate_passes_text_to_model(self) -> None:
        """evaluate() passes the narrative text to the model."""
        from babylon.intelligence.ai.judge import NarrativeCommissar

        seen: dict[str, object] = {}

        def capture(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            user_parts = [
                p for p in messages[0].parts if getattr(p, "part_kind", "") == "user-prompt"
            ]
            seen["prompt"] = user_parts[0].content if user_parts else None
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, VALID_ARGS)])

        commissar = NarrativeCommissar(model_factory=lambda: FunctionModel(capture))

        test_text = "The bourgeoisie trembles as their empire crumbles."
        commissar.evaluate(test_text)

        assert isinstance(seen["prompt"], str)
        assert test_text in seen["prompt"]

    def test_evaluate_uses_system_prompt(self) -> None:
        """evaluate() provides the Commissar instructions to the model."""
        from babylon.intelligence.ai.judge import NarrativeCommissar

        seen: dict[str, object] = {}

        def capture(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            seen["instructions"] = info.instructions
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, VALID_ARGS)])

        commissar = NarrativeCommissar(model_factory=lambda: FunctionModel(capture))
        commissar.evaluate("Test text.")

        assert isinstance(seen["instructions"], str)
        assert "literary critic" in seen["instructions"]

    def test_evaluate_uses_low_temperature(self) -> None:
        """evaluate() pins a low sampling temperature for consistency."""
        from babylon.intelligence.ai.judge import NarrativeCommissar

        seen: dict[str, object] = {}

        def capture(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            seen["temperature"] = (info.model_settings or {}).get("temperature")
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, VALID_ARGS)])

        commissar = NarrativeCommissar(model_factory=lambda: FunctionModel(capture))
        commissar.evaluate("Test text.")

        assert seen["temperature"] == 0.3


# =============================================================================
# TEST CLASS: Structured Output Validation (replaces JSON extraction)
# =============================================================================


@pytest.mark.unit
class TestStructuredOutputValidation:
    """Schema validation happens at the SDK layer, with retry then loud failure.

    This replaces the retired markdown-fence/JSON-extraction tests: there is
    no hand-rolled parsing left to test — the contract is now that invalid
    model output is re-prompted once and a never-valid model fails loud.
    """

    def test_invalid_output_is_retried_then_succeeds(self) -> None:
        """An out-of-bounds first answer triggers a schema retry."""
        from babylon.intelligence.ai.judge import NarrativeCommissar

        calls = {"n": 0}

        def flaky(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            calls["n"] += 1
            args = dict(VALID_ARGS)
            if calls["n"] == 1:
                args["ominousness"] = 999  # out of the 1-10 bound
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args)])

        model = FunctionModel(flaky)
        commissar = NarrativeCommissar(model_factory=lambda: model)

        result = commissar.evaluate("Test text.")

        assert calls["n"] == 2
        assert result.ominousness == 7

    def test_never_valid_output_fails_loud(self) -> None:
        """A model that never validates raises LLMGenerationError (LLM_001)."""
        from babylon.intelligence.ai.judge import NarrativeCommissar
        from babylon.kernel.exceptions import LLMGenerationError

        def always_invalid(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            args = dict(VALID_ARGS)
            args["ominousness"] = 999
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args)])

        model = FunctionModel(always_invalid)
        commissar = NarrativeCommissar(model_factory=lambda: model)

        with pytest.raises(LLMGenerationError) as exc:
            commissar.evaluate("Test text.")

        assert exc.value.error_code == "LLM_001"

    def test_invalid_metaphor_family_is_retried(self) -> None:
        """An unknown metaphor_family string triggers a schema retry."""
        from babylon.intelligence.ai.judge import MetaphorFamily, NarrativeCommissar

        calls = {"n": 0}

        def flaky(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            calls["n"] += 1
            args = dict(VALID_ARGS)
            if calls["n"] == 1:
                args["metaphor_family"] = "astrological"
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args)])

        model = FunctionModel(flaky)
        commissar = NarrativeCommissar(model_factory=lambda: model)

        result = commissar.evaluate("Test text.")

        assert calls["n"] == 2
        assert result.metaphor_family == MetaphorFamily.BIOLOGICAL


# =============================================================================
# TEST CLASS: Module Exports
# =============================================================================


@pytest.mark.unit
class TestJudgeModuleExports:
    """Tests for module-level exports from babylon.intelligence.ai."""

    def test_narrative_commissar_exports_from_ai_module(self) -> None:
        """NarrativeCommissar can be imported from babylon.intelligence.ai."""
        from babylon.intelligence.ai import NarrativeCommissar

        assert NarrativeCommissar is not None

    def test_judgment_result_exports_from_ai_module(self) -> None:
        """JudgmentResult can be imported from babylon.intelligence.ai."""
        from babylon.intelligence.ai import JudgmentResult

        assert JudgmentResult is not None

    def test_metaphor_family_exports_from_ai_module(self) -> None:
        """MetaphorFamily can be imported from babylon.intelligence.ai."""
        from babylon.intelligence.ai import MetaphorFamily

        assert MetaphorFamily is not None
