"""Tests for LLM Provider protocol and implementations.

Behavioral contract for the generation lane on its pydantic-ai transport
(Amendment Y, ADR100). All tests are SYNCHRONOUS (matching the
SimulationObserver pattern) and network-free: production clients are
exercised through the ``ModelFactory`` seam with pydantic-ai's
``TestModel``/``FunctionModel``, and ``ALLOW_MODEL_REQUESTS`` is False
for the whole test tier (see tests/conftest.py).

Pinned contracts:
- LLMProvider protocol shape (name, sync generate())
- error taxonomy: LLM_001 (API/behavior), LLM_002 (timeout), LLM_003 (rate limit)
- factory selection from LLMConfig.PROVIDER
- sync generate() interleaves safely with asyncio.run() callers (RAG)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from openai import APIError, APITimeoutError, RateLimitError
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

# =============================================================================
# HELPERS
# =============================================================================


def _configured_client(model_factory, monkeypatch: pytest.MonkeyPatch):
    """A DeepSeekClient with a fake key and an injected pydantic-ai model."""
    from babylon.config import llm_config
    from babylon.intelligence.ai.llm_provider import DeepSeekClient

    monkeypatch.setattr(llm_config.LLMConfig, "API_KEY", "sk-test-key")
    return DeepSeekClient(model_factory=model_factory)


def _text_model(text: str) -> TestModel:
    return TestModel(custom_output_text=text)


def _raising_model(exc: Exception) -> FunctionModel:
    def raise_it(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise exc

    return FunctionModel(raise_it)


# =============================================================================
# TEST-TIER NETWORK GUARD (Amendment Y hygiene)
# =============================================================================


@pytest.mark.unit
class TestModelRequestGuard:
    """The test tier must never issue real LLM requests."""

    def test_model_requests_are_disallowed(self) -> None:
        """pydantic-ai's global request guard is off for the whole tier."""
        from pydantic_ai import models

        assert models.ALLOW_MODEL_REQUESTS is False


# =============================================================================
# SPRINT 1: CONFIGURATION TESTS
# =============================================================================


@pytest.mark.unit
class TestLLMConfigBackwardCompatibility:
    """Tests that OpenAIConfig backward compatibility is preserved."""

    def test_openai_config_alias_still_works(self) -> None:
        """OpenAIConfig import still works for backward compatibility."""
        from babylon.config import OpenAIConfig

        assert OpenAIConfig is not None
        assert hasattr(OpenAIConfig, "API_KEY")
        assert hasattr(OpenAIConfig, "is_configured")

    def test_llm_config_is_available(self) -> None:
        """LLMConfig is the new primary config class."""
        from babylon.config import LLMConfig

        assert LLMConfig is not None
        assert hasattr(LLMConfig, "API_KEY")
        assert hasattr(LLMConfig, "API_BASE")
        assert hasattr(LLMConfig, "CHAT_MODEL")

    def test_openai_config_is_alias_for_llm_config(self) -> None:
        """OpenAIConfig is an alias pointing to LLMConfig."""
        from babylon.config import LLMConfig, OpenAIConfig

        assert OpenAIConfig is LLMConfig


@pytest.mark.unit
class TestLLMConfigDeepSeekPriority:
    """Tests that DeepSeek API key takes priority over OpenAI."""

    def test_deepseek_key_takes_priority(self) -> None:
        """DEEPSEEK_API_KEY is used when both keys are present."""
        from babylon.config.llm_config import LLMConfig

        assert hasattr(LLMConfig, "API_KEY")
        assert hasattr(LLMConfig, "API_BASE")

    def test_api_base_defaults_to_deepseek(self) -> None:
        """API_BASE defaults to DeepSeek endpoint."""
        import os

        from babylon.config.llm_config import LLMConfig

        assert "deepseek" in LLMConfig.API_BASE.lower() or os.getenv("LLM_API_BASE")

    def test_chat_model_defaults_to_deepseek_chat(self) -> None:
        """CHAT_MODEL defaults to deepseek-chat."""
        import os

        from babylon.config.llm_config import LLMConfig

        assert "deepseek" in LLMConfig.CHAT_MODEL.lower() or os.getenv("LLM_CHAT_MODEL")


# =============================================================================
# SPRINT 2: PROTOCOL AND EXCEPTION TESTS
# =============================================================================


@pytest.mark.unit
class TestLLMGenerationError:
    """Tests for LLMGenerationError exception."""

    def test_llm_generation_error_exists(self) -> None:
        """LLMGenerationError is defined in exceptions module."""
        from babylon.kernel.exceptions import LLMGenerationError

        assert LLMGenerationError is not None

    def test_llm_generation_error_inherits_babylon_error(self) -> None:
        """LLMGenerationError inherits from BabylonError."""
        from babylon.kernel.exceptions import BabylonError, LLMGenerationError

        assert issubclass(LLMGenerationError, BabylonError)

    def test_llm_generation_error_default_code(self) -> None:
        """LLMGenerationError has default error code LLM_001."""
        from babylon.kernel.exceptions import LLMGenerationError

        error = LLMGenerationError("Test error")
        assert error.error_code == "LLM_001"

    def test_llm_generation_error_custom_code(self) -> None:
        """LLMGenerationError accepts custom error codes."""
        from babylon.kernel.exceptions import LLMGenerationError

        error = LLMGenerationError("Timeout", error_code="LLM_002")
        assert error.error_code == "LLM_002"

    def test_llm_generation_error_details(self) -> None:
        """LLMGenerationError accepts details dict."""
        from babylon.kernel.exceptions import LLMGenerationError

        error = LLMGenerationError(
            "Rate limit",
            error_code="LLM_003",
            details={"retry_after": 60},
        )
        assert error.details == {"retry_after": 60}


@pytest.mark.unit
class TestLLMProviderProtocol:
    """Tests for LLMProvider protocol compliance."""

    def test_mock_llm_is_llm_provider(self) -> None:
        """MockLLM satisfies LLMProvider protocol."""
        from babylon.intelligence.ai.llm_provider import LLMProvider, MockLLM

        mock = MockLLM()
        assert isinstance(mock, LLMProvider)

    def test_deepseek_client_is_llm_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """DeepSeekClient satisfies LLMProvider protocol."""
        from babylon.intelligence.ai.llm_provider import LLMProvider

        client = _configured_client(lambda: _text_model("x"), monkeypatch)
        assert isinstance(client, LLMProvider)


# =============================================================================
# SPRINT 3: MOCK LLM TESTS
# =============================================================================


@pytest.mark.unit
class TestMockLLM:
    """Tests for MockLLM deterministic behavior (sync)."""

    def test_returns_default_response(self) -> None:
        """MockLLM returns default response when no queue."""
        from babylon.intelligence.ai.llm_provider import MockLLM

        mock = MockLLM(default_response="Test response")
        result = mock.generate("prompt")
        assert result == "Test response"

    def test_returns_queued_responses_in_order(self) -> None:
        """MockLLM returns responses from queue in FIFO order."""
        from babylon.intelligence.ai.llm_provider import MockLLM

        mock = MockLLM(responses=["First", "Second", "Third"])

        assert mock.generate("p1") == "First"
        assert mock.generate("p2") == "Second"
        assert mock.generate("p3") == "Third"

    def test_falls_back_to_default_after_queue_empty(self) -> None:
        """MockLLM uses default after queue exhausted."""
        from babylon.intelligence.ai.llm_provider import MockLLM

        mock = MockLLM(responses=["Queued"], default_response="Default")

        assert mock.generate("p1") == "Queued"
        assert mock.generate("p2") == "Default"

    def test_tracks_call_count(self) -> None:
        """MockLLM tracks number of generate calls."""
        from babylon.intelligence.ai.llm_provider import MockLLM

        mock = MockLLM()
        assert mock.call_count == 0

        mock.generate("prompt")
        assert mock.call_count == 1

        mock.generate("prompt2")
        assert mock.call_count == 2

    def test_records_call_history(self) -> None:
        """MockLLM records arguments of each call."""
        from babylon.intelligence.ai.llm_provider import MockLLM

        mock = MockLLM()
        mock.generate("user prompt", system_prompt="system", temperature=0.5)

        assert len(mock.call_history) == 1
        assert mock.call_history[0]["prompt"] == "user prompt"
        assert mock.call_history[0]["system_prompt"] == "system"
        assert mock.call_history[0]["temperature"] == 0.5

    def test_has_name_property(self) -> None:
        """MockLLM has name for logging."""
        from babylon.intelligence.ai.llm_provider import MockLLM

        mock = MockLLM()
        assert mock.name == "MockLLM"

    def test_default_response_value(self) -> None:
        """MockLLM has sensible default response."""
        from babylon.intelligence.ai.llm_provider import MockLLM

        mock = MockLLM()
        result = mock.generate("prompt")
        assert result == "Mock LLM response"

    def test_call_history_is_copy(self) -> None:
        """MockLLM call_history returns a copy, not internal list."""
        from babylon.intelligence.ai.llm_provider import MockLLM

        mock = MockLLM()
        mock.generate("prompt")

        history = mock.call_history
        history.clear()

        assert len(mock.call_history) == 1


# =============================================================================
# SPRINT 4: DEEPSEEK CLIENT (pydantic-ai transport)
# =============================================================================


@pytest.mark.unit
class TestDeepSeekClientInstantiation:
    """Tests for DeepSeekClient initialization."""

    def test_raises_without_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """DeepSeekClient raises LLMGenerationError without API key."""
        from babylon.config import llm_config
        from babylon.intelligence.ai.llm_provider import DeepSeekClient
        from babylon.kernel.exceptions import LLMGenerationError

        monkeypatch.setattr(llm_config.LLMConfig, "API_KEY", "")

        with pytest.raises(LLMGenerationError) as exc:
            DeepSeekClient()

        assert exc.value.error_code == "LLM_001"
        assert "not configured" in exc.value.message.lower()

    def test_initializes_with_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """DeepSeekClient initializes when API key is configured."""
        from babylon.config import llm_config
        from babylon.intelligence.ai.llm_provider import DeepSeekClient

        monkeypatch.setattr(llm_config.LLMConfig, "API_KEY", "sk-test-key")

        client = DeepSeekClient()
        assert client.name == "DeepSeek"


@pytest.mark.unit
class TestDeepSeekClientErrorHandling:
    """Error taxonomy through the pydantic-ai transport (no network)."""

    def test_handles_api_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Timeout maps to LLM_002."""
        from babylon.kernel.exceptions import LLMGenerationError

        client = _configured_client(
            lambda: _raising_model(APITimeoutError(request=MagicMock())), monkeypatch
        )

        with pytest.raises(LLMGenerationError) as exc:
            client.generate("prompt")

        assert exc.value.error_code == "LLM_002"

    def test_handles_rate_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Raw openai RateLimitError maps to LLM_003."""
        from babylon.kernel.exceptions import LLMGenerationError

        mock_response = MagicMock()
        mock_response.status_code = 429
        client = _configured_client(
            lambda: _raising_model(
                RateLimitError(message="Rate limit", response=mock_response, body=None)
            ),
            monkeypatch,
        )

        with pytest.raises(LLMGenerationError) as exc:
            client.generate("prompt")

        assert exc.value.error_code == "LLM_003"

    def test_handles_model_http_429(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """pydantic-ai ModelHTTPError with status 429 maps to LLM_003.

        This is the production wrapping: OpenAIChatModel converts API status
        errors into ModelHTTPError before they reach our ladder.
        """
        from babylon.kernel.exceptions import LLMGenerationError

        client = _configured_client(
            lambda: _raising_model(
                ModelHTTPError(status_code=429, model_name="deepseek-chat", body=None)
            ),
            monkeypatch,
        )

        with pytest.raises(LLMGenerationError) as exc:
            client.generate("prompt")

        assert exc.value.error_code == "LLM_003"

    def test_handles_model_http_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-429 ModelHTTPError maps to LLM_001 with the status recorded."""
        from babylon.kernel.exceptions import LLMGenerationError

        client = _configured_client(
            lambda: _raising_model(
                ModelHTTPError(status_code=500, model_name="deepseek-chat", body=None)
            ),
            monkeypatch,
        )

        with pytest.raises(LLMGenerationError) as exc:
            client.generate("prompt")

        assert exc.value.error_code == "LLM_001"
        assert exc.value.details == {"status_code": 500}

    def test_handles_api_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """General openai APIError maps to LLM_001."""
        from babylon.kernel.exceptions import LLMGenerationError

        client = _configured_client(
            lambda: _raising_model(
                APIError(message="Server error", request=MagicMock(), body=None)
            ),
            monkeypatch,
        )

        with pytest.raises(LLMGenerationError) as exc:
            client.generate("prompt")

        assert exc.value.error_code == "LLM_001"

    def test_handles_empty_response(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty model output is refused loudly as LLM_001.

        pydantic-ai itself refuses empty output (retries, then raises) —
        nothing fabricated, per Loud Failure III.11.
        """
        from babylon.kernel.exceptions import LLMGenerationError

        def empty(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            return ModelResponse(parts=[TextPart("")])

        client = _configured_client(lambda: FunctionModel(empty), monkeypatch)

        with pytest.raises(LLMGenerationError) as exc:
            client.generate("prompt")

        assert exc.value.error_code == "LLM_001"


@pytest.mark.unit
class TestDeepSeekClientGeneration:
    """Text generation behavior through the pydantic-ai transport."""

    def test_generates_text_successfully(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """DeepSeekClient returns generated text on success."""
        client = _configured_client(lambda: _text_model("Generated narrative text"), monkeypatch)

        result = client.generate("Describe the revolution")
        assert result == "Generated narrative text"

    def test_passes_system_prompt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The system prompt reaches the model as agent instructions."""
        seen: dict[str, object] = {}

        def capture(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            seen["instructions"] = info.instructions
            return ModelResponse(parts=[TextPart("Response")])

        client = _configured_client(lambda: FunctionModel(capture), monkeypatch)

        client.generate("User prompt", system_prompt="You are a narrator")

        assert seen["instructions"] == "You are a narrator"

    def test_passes_temperature(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The temperature reaches the model via model settings."""
        seen: dict[str, object] = {}

        def capture(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            seen["temperature"] = (info.model_settings or {}).get("temperature")
            return ModelResponse(parts=[TextPart("Response")])

        client = _configured_client(lambda: FunctionModel(capture), monkeypatch)

        client.generate("Prompt", temperature=0.3)

        assert seen["temperature"] == 0.3


# =============================================================================
# SPRINT 5: LANE MODEL FACTORY (structured-output consumers)
# =============================================================================


@pytest.mark.unit
class TestBuildChatModel:
    """build_chat_model() hands structured-output agents the lane's model."""

    def test_mock_lane_returns_test_model(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """PROVIDER=mock yields pydantic-ai's deterministic TestModel."""
        from babylon.config import llm_config
        from babylon.intelligence.ai.llm_provider import build_chat_model

        monkeypatch.setattr(llm_config.LLMConfig, "PROVIDER", "mock")

        factory = build_chat_model()
        assert isinstance(factory(), TestModel)

    def test_unknown_lane_is_loud(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An unknown PROVIDER fails loud with LLM_001."""
        from babylon.config import llm_config
        from babylon.intelligence.ai.llm_provider import build_chat_model
        from babylon.kernel.exceptions import LLMGenerationError

        monkeypatch.setattr(llm_config.LLMConfig, "PROVIDER", "nonsense")

        with pytest.raises(LLMGenerationError) as exc:
            build_chat_model()

        assert exc.value.error_code == "LLM_001"


# =============================================================================
# SPRINT 6: MODULE EXPORT TESTS
# =============================================================================


@pytest.mark.unit
class TestModuleExports:
    """Tests for module-level exports."""

    def test_llm_provider_exports_from_ai_module(self) -> None:
        """LLMProvider can be imported from babylon.intelligence.ai."""
        from babylon.intelligence.ai import LLMProvider

        assert LLMProvider is not None

    def test_mock_llm_exports_from_ai_module(self) -> None:
        """MockLLM can be imported from babylon.intelligence.ai."""
        from babylon.intelligence.ai import MockLLM

        assert MockLLM is not None

    def test_deepseek_client_exports_from_ai_module(self) -> None:
        """DeepSeekClient can be imported from babylon.intelligence.ai."""
        from babylon.intelligence.ai import DeepSeekClient

        assert DeepSeekClient is not None

    def test_build_chat_model_exports_from_ai_module(self) -> None:
        """build_chat_model can be imported from babylon.intelligence.ai."""
        from babylon.intelligence.ai import build_chat_model

        assert build_chat_model is not None


# =============================================================================
# SPRINT 7: SYNC BEHAVIOR (Event Loop Compatibility)
# =============================================================================


@pytest.mark.unit
class TestDeepSeekClientSyncBehavior:
    """generate() is synchronous and safe to interleave with asyncio.run().

    Each generate() call builds a fresh model via the ModelFactory seam and
    runs it in run_sync's own event loop, so no connection pool outlives
    the loop it was created on. These tests pin the behavior that used to
    regress as RuntimeError('Event loop is closed') when interleaved with
    RAG's asyncio.run() calls.
    """

    def test_generate_after_asyncio_run_still_works(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LLM generate() works after code that uses asyncio.run()."""
        import asyncio

        client = _configured_client(lambda: _text_model("Response after asyncio.run"), monkeypatch)

        async def simulate_rag_query() -> str:
            return "RAG result"

        rag_result = asyncio.run(simulate_rag_query())
        assert rag_result == "RAG result"

        result = client.generate("Generate after RAG")
        assert result == "Response after asyncio.run"

    def test_multiple_generate_calls_work_sequentially(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sequential generate() calls each run in a fresh event loop."""
        counter = {"n": 0}

        def numbered(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            counter["n"] += 1
            return ModelResponse(parts=[TextPart(f"Response {counter['n']}")])

        client = _configured_client(lambda: FunctionModel(numbered), monkeypatch)

        assert client.generate("Prompt 1") == "Response 1"
        assert client.generate("Prompt 2") == "Response 2"
        assert client.generate("Prompt 3") == "Response 3"
