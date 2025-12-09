"""LLM Provider strategy pattern for text generation.

This module provides the "Mouth" of the AI Observer - the interface
through which the NarrativeDirector speaks. It follows the same
Protocol pattern as SimulationObserver for loose coupling.

Components:
- LLMProvider: Protocol defining the text generation interface
- MockLLM: Deterministic mock for testing
- DeepSeekClient: Production client using DeepSeek API

SYNC API: All providers implement synchronous generate() to match
the SimulationObserver pattern. Async implementations wrap internally.
"""

from __future__ import annotations

import logging
from typing import Any, Final, Protocol, runtime_checkable

from openai import APIError, APITimeoutError, OpenAI, RateLimitError
from openai.types.chat import ChatCompletionMessageParam

from babylon.config import LLMConfig
from babylon.utils.exceptions import LLMGenerationError

logger = logging.getLogger(__name__)


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM text generation providers.

    Follows the same pattern as SimulationObserver - loose coupling
    via Protocol enables easy testing and provider swapping.

    SYNC API: All implementations use synchronous interfaces to avoid
    event loop conflicts with other asyncio.run() callers (e.g., RAG).
    """

    @property
    def name(self) -> str:
        """Provider identifier for logging."""
        ...

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Generate text from prompt (synchronous).

        Args:
            prompt: User prompt / context
            system_prompt: Optional system instructions
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            Generated text response

        Raises:
            LLMGenerationError: On API or generation failure
        """
        ...


class MockLLM:
    """Deterministic mock LLM for testing.

    Returns pre-configured responses in queue order,
    or a fixed default response. Synchronous API.

    This is the primary testing tool for NarrativeDirector -
    it allows tests to verify behavior without network calls.
    """

    def __init__(
        self,
        responses: list[str] | None = None,
        default_response: str = "Mock LLM response",
    ) -> None:
        """Initialize MockLLM.

        Args:
            responses: Queue of responses to return in FIFO order
            default_response: Response when queue is empty
        """
        self._name: Final[str] = "MockLLM"
        self._responses: list[str] = list(responses) if responses else []
        self._default: str = default_response
        self._call_count: int = 0
        self._call_history: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        """Provider identifier for logging."""
        return self._name

    @property
    def call_count(self) -> int:
        """Number of times generate() was called."""
        return self._call_count

    @property
    def call_history(self) -> list[dict[str, Any]]:
        """History of all calls with arguments.

        Returns a copy to prevent external modification.
        """
        return list(self._call_history)

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Generate response synchronously.

        Args:
            prompt: User prompt / context
            system_prompt: Optional system instructions
            temperature: Sampling temperature (ignored by mock)

        Returns:
            Next queued response or default response
        """
        self._call_count += 1
        self._call_history.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "temperature": temperature,
            }
        )

        if self._responses:
            return self._responses.pop(0)
        return self._default


class DeepSeekClient:
    """DeepSeek LLM client using OpenAI-compatible API.

    Primary LLM provider for Babylon narrative generation.
    Uses the openai Python package with custom base_url.

    SYNC API: Uses synchronous OpenAI client to avoid event loop
    conflicts with RAG queries that use asyncio.run().
    """

    def __init__(self, config: type[LLMConfig] | None = None) -> None:
        """Initialize DeepSeekClient.

        Args:
            config: LLM configuration class (defaults to LLMConfig)

        Raises:
            LLMGenerationError: If API key is not configured
        """
        self._config = config or LLMConfig
        self._name: Final[str] = "DeepSeek"

        if not self._config.is_configured():
            raise LLMGenerationError(
                "LLM API key not configured. Set DEEPSEEK_API_KEY or OPENAI_API_KEY.",
                error_code="LLM_001",
            )

        self._client = OpenAI(
            api_key=self._config.API_KEY,
            base_url=self._config.API_BASE,
            timeout=self._config.REQUEST_TIMEOUT,
            max_retries=self._config.MAX_RETRIES,
        )

    @property
    def name(self) -> str:
        """Provider identifier for logging."""
        return self._name

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Generate text synchronously.

        Uses the sync OpenAI client directly, avoiding event loop
        conflicts with other code that uses asyncio.run().

        Args:
            prompt: User prompt / context
            system_prompt: Optional system instructions
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            Generated text response

        Raises:
            LLMGenerationError: On API or generation failure
        """
        messages: list[ChatCompletionMessageParam] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self._client.chat.completions.create(
                model=self._config.CHAT_MODEL,
                messages=messages,
                temperature=temperature,
            )

            content: str | None = response.choices[0].message.content
            if content is None:
                raise LLMGenerationError(
                    "LLM returned empty response",
                    error_code="LLM_001",
                )
            return content

        except APITimeoutError as e:
            logger.error("LLM timeout: %s", e)
            raise LLMGenerationError(
                f"LLM request timed out: {e}",
                error_code="LLM_002",
                details={"timeout": self._config.REQUEST_TIMEOUT},
            ) from e

        except RateLimitError as e:
            logger.error("LLM rate limit: %s", e)
            raise LLMGenerationError(
                f"LLM rate limit exceeded: {e}",
                error_code="LLM_003",
            ) from e

        except APIError as e:
            logger.error("LLM API error: %s", e)
            raise LLMGenerationError(
                f"LLM API error: {e}",
                error_code="LLM_001",
                details={"status_code": getattr(e, "status_code", None)},
            ) from e
