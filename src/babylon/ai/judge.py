"""Narrative evaluation via LLM-as-judge pattern.

The NarrativeCommissar evaluates narrative text quality using structured
prompting to extract consistent metrics. This enables automated verification
of the "Dialectical U-Curve" hypothesis - that narrative certainty follows
a U-shape across economic conditions (high at stability, low at inflection,
high at collapse).

Components:
    MetaphorFamily: Enum categorizing metaphorical language in narratives.
    JudgmentResult: Immutable Pydantic model holding evaluation metrics.
    NarrativeCommissar: LLM-powered judge that evaluates narrative quality.

The Commissar follows the same pattern as NarrativeDirector - it uses the
LLMProvider protocol for swappable LLM backends (MockLLM for testing,
DeepSeekClient for production).

Example:
    >>> from babylon.ai import MockLLM, NarrativeCommissar
    >>> mock = MockLLM(responses=['{"ominousness": 7, "certainty": 8, "drama": 6, "metaphor_family": "biological"}'])
    >>> commissar = NarrativeCommissar(llm=mock)
    >>> result = commissar.evaluate("The empire crumbles...")
    >>> result.ominousness
    7
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import TYPE_CHECKING, Any, Final

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from babylon.ai.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class MetaphorFamily(str, Enum):
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
    All metrics use a 1-10 scale for consistency.

    Attributes:
        ominousness: How threatening/foreboding the narrative (1-10).
        certainty: How confident/absolute the assertions (1-10).
        drama: Emotional intensity of the narrative (1-10).
        metaphor_family: Dominant metaphorical domain used.

    Example:
        >>> from babylon.ai.judge import JudgmentResult, MetaphorFamily
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
Return ONLY a JSON object with these fields:
- "ominousness": integer 1-10 (how threatening/foreboding)
- "certainty": integer 1-10 (how confident/absolute the assertions)
- "drama": integer 1-10 (emotional intensity)
- "metaphor_family": one of "biological", "physics", "mechanical", "none"

Respond with ONLY the JSON object, no other text."""


class NarrativeCommissar:
    """LLM-powered judge that evaluates narrative quality.

    The Commissar uses structured prompting to extract consistent metrics
    from narrative text. It follows the LLM-as-judge pattern where the
    LLM acts as a consistent evaluator rather than a generator.

    This enables automated verification of narrative hypotheses like the
    "Dialectical U-Curve" - that narrative certainty follows a U-shape
    across economic conditions.

    Attributes:
        name: Identifier for logging ("NarrativeCommissar").

    Example:
        >>> from babylon.ai import MockLLM
        >>> from babylon.ai.judge import NarrativeCommissar
        >>> mock = MockLLM(responses=['{"ominousness": 5, "certainty": 5, "drama": 5, "metaphor_family": "none"}'])
        >>> commissar = NarrativeCommissar(llm=mock)
        >>> result = commissar.evaluate("The workers unite.")
        >>> isinstance(result.ominousness, int)
        True
    """

    def __init__(self, llm: LLMProvider) -> None:
        """Initialize the NarrativeCommissar.

        Args:
            llm: LLMProvider implementation for text generation.
                 Use MockLLM for testing, DeepSeekClient for production.
        """
        self._llm = llm
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

        Sends the text to the LLM with a structured prompt requesting
        JSON output. Parses the response and returns a JudgmentResult.

        Args:
            text: The narrative text to evaluate.

        Returns:
            JudgmentResult containing the evaluation metrics.

        Raises:
            json.JSONDecodeError: If LLM response is not valid JSON.
            pydantic.ValidationError: If JSON values are out of bounds.

        Example:
            >>> from babylon.ai import MockLLM
            >>> from babylon.ai.judge import NarrativeCommissar
            >>> mock = MockLLM(responses=['{"ominousness": 7, "certainty": 8, "drama": 6, "metaphor_family": "biological"}'])
            >>> commissar = NarrativeCommissar(llm=mock)
            >>> result = commissar.evaluate("The crisis deepens.")
            >>> result.ominousness
            7
        """
        prompt = f"Evaluate this narrative:\n\n---\n{text}\n---\n\nReturn your evaluation as JSON."

        logger.debug(
            "[%s] Evaluating narrative (%d chars)",
            self.name,
            len(text),
        )

        response = self._llm.generate(
            prompt,
            system_prompt=COMMISSAR_SYSTEM_PROMPT,
            temperature=0.3,  # Lower temperature for consistent evaluation
        )

        logger.debug("[%s] LLM response: %s", self.name, response[:100])

        data = self._extract_json(response)
        return JudgmentResult(**data)

    def _extract_json(self, response: str) -> dict[str, Any]:
        """Extract JSON from LLM response, handling markdown blocks.

        LLMs sometimes wrap JSON in markdown code blocks (```json ... ```).
        This method strips those wrappers to extract the raw JSON.

        Args:
            response: Raw LLM response text.

        Returns:
            Parsed JSON as a dictionary.

        Raises:
            json.JSONDecodeError: If the response is not valid JSON.
        """
        text = response.strip()

        # Handle ```json ... ``` blocks
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        return dict(json.loads(text.strip()))
