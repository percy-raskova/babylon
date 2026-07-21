"""Narrative evaluation via LLM-as-judge pattern.

The NarrativeCommissar evaluates narrative text quality using pydantic-ai
structured output to extract consistent metrics. This enables automated
verification of the "Dialectical U-Curve" hypothesis - that narrative
certainty follows a U-shape across economic conditions (high at stability,
low at inflection, high at collapse).

Components:
    MetaphorFamily: Enum categorizing metaphorical language in narratives.
    JudgmentResult: Immutable Pydantic model holding evaluation metrics.
    NarrativeCommissar: LLM-powered judge that evaluates narrative quality.

Structured output (Amendment Y, ADR100): the judge runs a pydantic-ai
``Agent`` with ``output_type=JudgmentResult`` — the model's answer is
validated against the schema at the SDK layer and the model is re-prompted
on validation failure. The former hand-rolled markdown-fence stripping and
``json.loads`` parsing are gone; a response that never validates surfaces
as a loud :class:`~babylon.kernel.exceptions.LLMGenerationError`.

Example:
    >>> from pydantic_ai.models.test import TestModel
    >>> from babylon.intelligence.ai.judge import NarrativeCommissar
    >>> model = TestModel(custom_output_args={
    ...     "ominousness": 7, "certainty": 8, "drama": 6,
    ...     "metaphor_family": "biological",
    ... })
    >>> commissar = NarrativeCommissar(model_factory=lambda: model)
    >>> result = commissar.evaluate("The empire crumbles...")
    >>> result.ominousness
    7
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.settings import ModelSettings

from babylon.intelligence.ai.llm_provider import ModelFactory, build_chat_model
from babylon.kernel.exceptions import LLMGenerationError

logger = logging.getLogger(__name__)


class MetaphorFamily(StrEnum):
    """Categories of metaphorical language in narratives.

    Narratives about economic crisis tend to cluster around certain
    metaphorical domains. Tracking these helps identify rhetorical
    patterns in how the AI describes class struggle.

    Attributes:
        BIOLOGICAL: Bodies, organs, disease, parasites, health.
        PHYSICS: Pressure, tension, phase transitions, energy.
        MECHANICAL: Gears, machines, breaking, grinding.
        NONE: No strong metaphorical clustering detected.
    """

    BIOLOGICAL = "biological"
    PHYSICS = "physics"
    MECHANICAL = "mechanical"
    NONE = "none"


class JudgmentResult(BaseModel):
    """Result of narrative evaluation by the Commissar.

    An immutable record of how the LLM-judge evaluated a narrative text.
    All metrics use a 1-10 scale for consistency. Doubles as the
    structured-output schema the judge's Agent validates against.

    Attributes:
        ominousness: How threatening/foreboding the narrative (1-10).
        certainty: How confident/absolute the assertions (1-10).
        drama: Emotional intensity of the narrative (1-10).
        metaphor_family: Dominant metaphorical domain used.

    Example:
        >>> from babylon.intelligence.ai.judge import JudgmentResult, MetaphorFamily
        >>> result = JudgmentResult(
        ...     ominousness=8,
        ...     certainty=9,
        ...     drama=7,
        ...     metaphor_family=MetaphorFamily.BIOLOGICAL,
        ... )
        >>> result.ominousness
        8
    """

    model_config = ConfigDict(frozen=True)

    ominousness: int = Field(
        ...,
        ge=1,
        le=10,
        description="How threatening/foreboding the narrative (1-10)",
    )
    certainty: int = Field(
        ...,
        ge=1,
        le=10,
        description="How confident/absolute the assertions (1-10)",
    )
    drama: int = Field(
        ...,
        ge=1,
        le=10,
        description="Emotional intensity of the narrative (1-10)",
    )
    metaphor_family: MetaphorFamily = Field(
        ...,
        description="Dominant metaphorical domain used in narrative",
    )


COMMISSAR_SYSTEM_PROMPT: Final[str] = """You are a literary critic analyzing narrative text.
Evaluate the narrative on these metrics:
- ominousness: integer 1-10 (how threatening/foreboding)
- certainty: integer 1-10 (how confident/absolute the assertions)
- drama: integer 1-10 (emotional intensity)
- metaphor_family: one of "biological", "physics", "mechanical", "none"
  (the dominant metaphorical domain used)"""

#: Lower temperature for consistent evaluation.
_JUDGE_TEMPERATURE: Final[float] = 0.3

#: Schema-validation retry budget: one re-prompt before failing loud.
_JUDGE_RETRIES: Final[int] = 1


class NarrativeCommissar:
    """LLM-powered judge that evaluates narrative quality.

    The Commissar uses pydantic-ai structured output to extract consistent
    metrics from narrative text. It follows the LLM-as-judge pattern where
    the LLM acts as a consistent evaluator rather than a generator.

    This enables automated verification of narrative hypotheses like the
    "Dialectical U-Curve" - that narrative certainty follows a U-shape
    across economic conditions.

    Attributes:
        name: Identifier for logging ("NarrativeCommissar").

    Example:
        >>> from pydantic_ai.models.test import TestModel
        >>> from babylon.intelligence.ai.judge import NarrativeCommissar
        >>> model = TestModel(custom_output_args={
        ...     "ominousness": 5, "certainty": 5, "drama": 5,
        ...     "metaphor_family": "none",
        ... })
        >>> commissar = NarrativeCommissar(model_factory=lambda: model)
        >>> result = commissar.evaluate("The workers unite.")
        >>> isinstance(result.ominousness, int)
        True
    """

    def __init__(self, model_factory: ModelFactory | None = None) -> None:
        """Initialize the NarrativeCommissar.

        Args:
            model_factory: Builds a fresh pydantic-ai ``Model`` per
                evaluation (fresh per call for event-loop hygiene — see
                :data:`~babylon.intelligence.ai.llm_provider.ModelFactory`).
                Defaults to the configured lane via
                :func:`~babylon.intelligence.ai.llm_provider.build_chat_model`.
                Tests inject ``lambda: TestModel(...)``.
        """
        self._model_factory = model_factory if model_factory is not None else build_chat_model()
        self._name: Final[str] = "NarrativeCommissar"

    @property
    def name(self) -> str:
        """Return identifier for logging.

        Returns:
            The string "NarrativeCommissar".
        """
        return self._name

    def evaluate(self, text: str) -> JudgmentResult:
        """Evaluate a narrative text and return structured metrics.

        Runs a pydantic-ai Agent with ``output_type=JudgmentResult``: the
        model's response is schema-validated by the SDK, which re-prompts
        the model once on validation failure before failing loud.

        Args:
            text: The narrative text to evaluate.

        Returns:
            JudgmentResult containing the evaluation metrics.

        Raises:
            LLMGenerationError: If the model never produces a response
                that validates against the JudgmentResult schema.

        Example:
            >>> from pydantic_ai.models.test import TestModel
            >>> from babylon.intelligence.ai.judge import NarrativeCommissar
            >>> model = TestModel(custom_output_args={
            ...     "ominousness": 7, "certainty": 8, "drama": 6,
            ...     "metaphor_family": "biological",
            ... })
            >>> commissar = NarrativeCommissar(model_factory=lambda: model)
            >>> result = commissar.evaluate("The crisis deepens.")
            >>> result.ominousness
            7
        """
        prompt = f"Evaluate this narrative:\n\n---\n{text}\n---"

        logger.debug(
            "[%s] Evaluating narrative (%d chars)",
            self.name,
            len(text),
        )

        agent: Agent[None, JudgmentResult] = Agent(
            self._model_factory(),
            output_type=JudgmentResult,
            instructions=COMMISSAR_SYSTEM_PROMPT,
            retries=_JUDGE_RETRIES,
        )
        try:
            result = agent.run_sync(
                prompt,
                model_settings=ModelSettings(temperature=_JUDGE_TEMPERATURE),
            )
        except UnexpectedModelBehavior as e:
            logger.error("[%s] structured evaluation failed: %s", self.name, e)
            raise LLMGenerationError(
                f"Judge failed structured evaluation: {e}",
                error_code="LLM_001",
            ) from e

        logger.debug("[%s] judgment: %s", self.name, result.output)
        return result.output
