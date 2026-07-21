"""LLM Provider strategy pattern for text generation.

This module provides the "Mouth" of the AI Observer - the interface
through which the NarrativeDirector speaks. It follows the same
Protocol pattern as SimulationObserver for loose coupling.

Transport (Amendment Y, ADR100): generation runs on **pydantic-ai** — an
``Agent`` over an OpenAI-compatible endpoint (``OpenAIChatModel`` +
``OpenAIProvider``). The stock ``openai`` package remains underneath as the
wire client (and alone carries embeddings, which pydantic-ai does not); the
hand-rolled per-provider message assembly and duplicated exception ladders
this module used to contain are gone.

Components:
- LLMProvider: Protocol defining the text generation interface
- MockLLM: Deterministic mock for testing (protocol-level; no network)
- DeepSeekClient / WorkersAIClient: production lanes on pydantic-ai
- build_chat_model: the configured lane's pydantic-ai ``Model`` factory
  (for structured-output agents such as the NarrativeCommissar)
- build_llm_provider: factory selecting the provider from LLMConfig.PROVIDER

SYNC API: All providers implement synchronous generate() to match the
SimulationObserver pattern. ``Agent.run_sync`` manages its own event loop
per call; a fresh model (and ``AsyncOpenAI`` client) is built per
``generate()`` call so no httpx connection pool outlives the event loop it
was created on — the historical ``RuntimeError('Event loop is closed')``
failure class when interleaved with RAG's ``asyncio.run()`` cannot recur.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Final, Protocol, runtime_checkable

from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from babylon.config import LLMConfig
from babylon.kernel.exceptions import LLMGenerationError

logger = logging.getLogger(__name__)

ModelFactory = Callable[[], Model]
"""Zero-arg factory returning a fresh pydantic-ai ``Model``.

A factory (not a ``Model`` instance) is the seam on purpose: each
``Agent.run_sync`` call runs in its own event loop, so the underlying
``AsyncOpenAI``/httpx client must be rebuilt per call to avoid stale
loop-bound connection pools. Tests inject ``lambda: TestModel(...)`` or
``lambda: FunctionModel(...)`` here — the factory may return the same
in-memory model every time, since test models never touch the network.
"""


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


def _openai_compat_model(
    *,
    model_name: str,
    base_url: str,
    api_key: str,
    timeout: float,
    max_retries: int,
    default_headers: dict[str, str] | None = None,
) -> Model:
    """Build a pydantic-ai model over any OpenAI-compatible ``/v1`` endpoint.

    The wire seam stays OpenAI-compatible (Amendment Y preserves the §A8
    protocol seam); pydantic-ai is the SDK on top, not a second protocol.

    Args:
        model_name: Chat model pin served by the endpoint
        base_url: OpenAI-compatible ``/v1`` base URL
        api_key: Bearer credential (a sentinel for credential-free lanes)
        timeout: Request timeout in seconds
        max_retries: Transport-level retry budget
        default_headers: Extra headers (e.g. the AI Gateway routing header)

    Returns:
        A fresh ``OpenAIChatModel`` bound to a fresh ``AsyncOpenAI`` client
    """
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
        default_headers=default_headers,
    )
    return OpenAIChatModel(model_name, provider=OpenAIProvider(openai_client=client))


class PydanticAIChatClient:
    """Shared pydantic-ai chat transport: one ``Agent`` run per generate().

    One implementation replaces the former per-provider clients; lanes
    (DeepSeek, Workers AI) differ only in the ``ModelFactory`` they carry.
    Error taxonomy is preserved: LLM_001 (API/behavior), LLM_002 (timeout),
    LLM_003 (rate limit).
    """

    def __init__(self, name: str, model_factory: ModelFactory) -> None:
        """Initialize the client.

        Args:
            name: Provider identifier for logging
            model_factory: Builds a fresh model per generate() call
        """
        self._name = name
        self._model_factory = model_factory

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
        """Generate text synchronously via a single pydantic-ai Agent run.

        Args:
            prompt: User prompt / context
            system_prompt: Optional system instructions
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            Generated text response (never empty — pydantic-ai refuses
            empty model output and it surfaces here as LLM_001)

        Raises:
            LLMGenerationError: On API or generation failure
        """
        agent: Agent[None, str] = Agent(self._model_factory(), instructions=system_prompt)
        try:
            result = agent.run_sync(prompt, model_settings=ModelSettings(temperature=temperature))
        except APITimeoutError as e:
            logger.error("[%s] LLM timeout: %s", self._name, e)
            raise LLMGenerationError(
                f"LLM request timed out: {e}",
                error_code="LLM_002",
            ) from e
        except RateLimitError as e:
            logger.error("[%s] LLM rate limit: %s", self._name, e)
            raise LLMGenerationError(
                f"LLM rate limit exceeded: {e}",
                error_code="LLM_003",
            ) from e
        except ModelHTTPError as e:
            logger.error("[%s] LLM HTTP error: %s", self._name, e)
            if e.status_code == 429:
                raise LLMGenerationError(
                    f"LLM rate limit exceeded: {e}",
                    error_code="LLM_003",
                ) from e
            raise LLMGenerationError(
                f"LLM API error: {e}",
                error_code="LLM_001",
                details={"status_code": e.status_code},
            ) from e
        except APIError as e:
            logger.error("[%s] LLM API error: %s", self._name, e)
            raise LLMGenerationError(
                f"LLM API error: {e}",
                error_code="LLM_001",
                details={"status_code": getattr(e, "status_code", None)},
            ) from e
        except UnexpectedModelBehavior as e:
            logger.error("[%s] LLM behavior error: %s", self._name, e)
            raise LLMGenerationError(
                f"LLM returned empty or invalid response: {e}",
                error_code="LLM_001",
            ) from e
        return result.output


class DeepSeekClient(PydanticAIChatClient):
    """DeepSeek lane: OpenAI-compatible API via pydantic-ai.

    Primary cloud LLM provider for Babylon narrative generation.
    """

    def __init__(
        self,
        config: type[LLMConfig] | None = None,
        model_factory: ModelFactory | None = None,
    ) -> None:
        """Initialize DeepSeekClient.

        Args:
            config: LLM configuration class (defaults to LLMConfig)
            model_factory: Test seam — replaces the network-bound model
                (inject ``lambda: TestModel(...)``/``FunctionModel``)

        Raises:
            LLMGenerationError: If API key is not configured
        """
        cfg = config or LLMConfig
        if model_factory is None and not cfg.is_configured():
            raise LLMGenerationError(
                "LLM API key not configured. Set DEEPSEEK_API_KEY or OPENAI_API_KEY.",
                error_code="LLM_001",
            )
        factory = model_factory or (
            lambda: _openai_compat_model(
                model_name=cfg.CHAT_MODEL,
                base_url=cfg.API_BASE,
                api_key=cfg.API_KEY,
                timeout=cfg.REQUEST_TIMEOUT,
                max_retries=cfg.MAX_RETRIES,
            )
        )
        super().__init__("DeepSeek", factory)


class WorkersAIClient(PydanticAIChatClient):
    """Cloudflare Workers AI lane via AI Gateway (OpenAI-compatible REST).

    Program 07 Decision 3 (owner, 2026-07-03): the narrator runs on Workers
    AI. Requests route through the babylon-narrator AI Gateway for logging/
    rate limiting (``cf-aig-gateway-id`` header).
    """

    def __init__(
        self,
        config: type[LLMConfig] | None = None,
        model_factory: ModelFactory | None = None,
    ) -> None:
        """Initialize WorkersAIClient.

        Args:
            config: LLM configuration class (defaults to LLMConfig)
            model_factory: Test seam — replaces the network-bound model

        Raises:
            LLMGenerationError: If the Workers AI token is not configured
        """
        cfg = config or LLMConfig
        if model_factory is None and not cfg.WORKERS_AI_TOKEN:
            raise LLMGenerationError(
                "Workers AI token not configured. Set WORKERS_AI_TOKEN.",
                error_code="LLM_001",
            )
        factory = model_factory or (
            lambda: _openai_compat_model(
                model_name=cfg.WORKERS_AI_MODEL,
                base_url=cfg.workers_ai_base_url(),
                api_key=cfg.WORKERS_AI_TOKEN,
                timeout=cfg.WORKERS_AI_TIMEOUT,
                max_retries=cfg.MAX_RETRIES,
                default_headers={"cf-aig-gateway-id": cfg.WORKERS_AI_GATEWAY_ID},
            )
        )
        super().__init__("WorkersAI", factory)


def build_chat_model(config: type[LLMConfig] | None = None) -> ModelFactory:
    """The configured lane's pydantic-ai model factory (loud on unknown).

    For structured-output agents (e.g. the NarrativeCommissar) that need a
    ``Model`` rather than the text-only :class:`LLMProvider` seam. The
    ``mock`` lane returns pydantic-ai's deterministic ``TestModel`` —
    schema-valid output, no network.

    Args:
        config: LLM configuration class (defaults to LLMConfig)

    Returns:
        A :data:`ModelFactory` for the lane selected by ``config.PROVIDER``

    Raises:
        LLMGenerationError: If ``config.PROVIDER`` is not one of
            ``deepseek``/``workers_ai``/``mock``
    """
    cfg = config or LLMConfig
    if cfg.is_workers_ai():
        return lambda: _openai_compat_model(
            model_name=cfg.WORKERS_AI_MODEL,
            base_url=cfg.workers_ai_base_url(),
            api_key=cfg.WORKERS_AI_TOKEN,
            timeout=cfg.WORKERS_AI_TIMEOUT,
            max_retries=cfg.MAX_RETRIES,
            default_headers={"cf-aig-gateway-id": cfg.WORKERS_AI_GATEWAY_ID},
        )
    provider = cfg.PROVIDER.lower()
    if provider == "deepseek":
        return lambda: _openai_compat_model(
            model_name=cfg.CHAT_MODEL,
            base_url=cfg.API_BASE,
            api_key=cfg.API_KEY,
            timeout=cfg.REQUEST_TIMEOUT,
            max_retries=cfg.MAX_RETRIES,
        )
    if provider == "mock":
        return lambda: TestModel()
    raise LLMGenerationError(
        f"Unknown LLM_PROVIDER: {cfg.PROVIDER!r} (expected deepseek|workers_ai|mock)",
        error_code="LLM_001",
    )


def build_llm_provider(config: type[LLMConfig] | None = None) -> LLMProvider:
    """Select the chat provider from ``LLMConfig.PROVIDER`` (loud on unknown).

    Args:
        config: LLM configuration class (defaults to LLMConfig)

    Returns:
        The LLMProvider implementation matching ``config.PROVIDER``

    Raises:
        LLMGenerationError: If ``config.PROVIDER`` is not one of
            ``deepseek``/``workers_ai``/``mock``
    """
    cfg = config or LLMConfig
    if cfg.is_workers_ai():
        return WorkersAIClient(config=cfg)
    provider = cfg.PROVIDER.lower()
    if provider == "deepseek":
        return DeepSeekClient(config=cfg)
    if provider == "mock":
        return MockLLM()
    raise LLMGenerationError(
        f"Unknown LLM_PROVIDER: {cfg.PROVIDER!r} (expected deepseek|workers_ai|mock)",
        error_code="LLM_001",
    )
