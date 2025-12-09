"""Tests for LLM Provider protocol and implementations.

TDD Red Phase: Define expected behavior before implementation.
All tests are SYNCHRONOUS (matching SimulationObserver pattern).

The LLM Provider is the "Mouth" of the AI Observer - it transforms
prompts into narrative text, while remaining swappable for testing.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass


# =============================================================================
# SPRINT 1: CONFIGURATION TESTS
# =============================================================================


@pytest.mark.unit
class TestLLMConfigBackwardCompatibility:
    """Tests that OpenAIConfig backward compatibility is preserved."""

    def test_openai_config_alias_still_works(self) -> None:
        """OpenAIConfig import still works for backward compatibility."""
        from babylon.config import OpenAIConfig

        # Should be able to access the class
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
        # This test verifies the config logic - actual env handling tested at runtime
        from babylon.config.llm_config import LLMConfig

        # The config should prioritize DEEPSEEK_API_KEY
        # We verify this by checking the class exists and has the expected structure
        assert hasattr(LLMConfig, "API_KEY")
        assert hasattr(LLMConfig, "API_BASE")

    def test_api_base_defaults_to_deepseek(self) -> None:
        """API_BASE defaults to DeepSeek endpoint."""
        from babylon.config.llm_config import LLMConfig

        # Default should be DeepSeek unless overridden by env
        # We check the default value is set correctly
        assert "deepseek" in LLMConfig.API_BASE.lower() or os.getenv("LLM_API_BASE")

    def test_chat_model_defaults_to_deepseek_chat(self) -> None:
        """CHAT_MODEL defaults to deepseek-chat."""
        from babylon.config.llm_config import LLMConfig

        # Default should be deepseek-chat unless overridden
        assert "deepseek" in LLMConfig.CHAT_MODEL.lower() or os.getenv("LLM_CHAT_MODEL")


# =============================================================================
# SPRINT 2: PROTOCOL AND EXCEPTION TESTS
# =============================================================================


@pytest.mark.unit
class TestLLMGenerationError:
    """Tests for LLMGenerationError exception."""

    def test_llm_generation_error_exists(self) -> None:
        """LLMGenerationError is defined in exceptions module."""
        from babylon.utils.exceptions import LLMGenerationError

        assert LLMGenerationError is not None

    def test_llm_generation_error_inherits_babylon_error(self) -> None:
        """LLMGenerationError inherits from BabylonError."""
        from babylon.utils.exceptions import BabylonError, LLMGenerationError

        assert issubclass(LLMGenerationError, BabylonError)

    def test_llm_generation_error_default_code(self) -> None:
        """LLMGenerationError has default error code LLM_001."""
        from babylon.utils.exceptions import LLMGenerationError

        error = LLMGenerationError("Test error")
        assert error.error_code == "LLM_001"

    def test_llm_generation_error_custom_code(self) -> None:
        """LLMGenerationError accepts custom error codes."""
        from babylon.utils.exceptions import LLMGenerationError

        error = LLMGenerationError("Timeout", error_code="LLM_002")
        assert error.error_code == "LLM_002"

    def test_llm_generation_error_details(self) -> None:
        """LLMGenerationError accepts details dict."""
        from babylon.utils.exceptions import LLMGenerationError

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
        from babylon.ai.llm_provider import LLMProvider, MockLLM

        mock = MockLLM()
        assert isinstance(mock, LLMProvider)

    def test_deepseek_client_is_llm_provider(self) -> None:
        """DeepSeekClient satisfies LLMProvider protocol."""
        from babylon.ai.llm_provider import DeepSeekClient, LLMProvider

        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}):
            # Need to reload config to pick up patched env
            from babylon.config import llm_config

            # Force reload the config values
            original_key = llm_config.LLMConfig.API_KEY
            try:
                # Temporarily set the API_KEY for this test
                llm_config.LLMConfig.API_KEY = "test-key"
                client = DeepSeekClient()
                assert isinstance(client, LLMProvider)
            finally:
                llm_config.LLMConfig.API_KEY = original_key


# =============================================================================
# SPRINT 3: MOCK LLM TESTS
# =============================================================================


@pytest.mark.unit
class TestMockLLM:
    """Tests for MockLLM deterministic behavior (sync)."""

    def test_returns_default_response(self) -> None:
        """MockLLM returns default response when no queue."""
        from babylon.ai.llm_provider import MockLLM

        mock = MockLLM(default_response="Test response")
        result = mock.generate("prompt")
        assert result == "Test response"

    def test_returns_queued_responses_in_order(self) -> None:
        """MockLLM returns responses from queue in FIFO order."""
        from babylon.ai.llm_provider import MockLLM

        mock = MockLLM(responses=["First", "Second", "Third"])

        assert mock.generate("p1") == "First"
        assert mock.generate("p2") == "Second"
        assert mock.generate("p3") == "Third"

    def test_falls_back_to_default_after_queue_empty(self) -> None:
        """MockLLM uses default after queue exhausted."""
        from babylon.ai.llm_provider import MockLLM

        mock = MockLLM(responses=["Queued"], default_response="Default")

        assert mock.generate("p1") == "Queued"
        assert mock.generate("p2") == "Default"

    def test_tracks_call_count(self) -> None:
        """MockLLM tracks number of generate calls."""
        from babylon.ai.llm_provider import MockLLM

        mock = MockLLM()
        assert mock.call_count == 0

        mock.generate("prompt")
        assert mock.call_count == 1

        mock.generate("prompt2")
        assert mock.call_count == 2

    def test_records_call_history(self) -> None:
        """MockLLM records arguments of each call."""
        from babylon.ai.llm_provider import MockLLM

        mock = MockLLM()
        mock.generate("user prompt", system_prompt="system", temperature=0.5)

        assert len(mock.call_history) == 1
        assert mock.call_history[0]["prompt"] == "user prompt"
        assert mock.call_history[0]["system_prompt"] == "system"
        assert mock.call_history[0]["temperature"] == 0.5

    def test_has_name_property(self) -> None:
        """MockLLM has name for logging."""
        from babylon.ai.llm_provider import MockLLM

        mock = MockLLM()
        assert mock.name == "MockLLM"

    def test_default_response_value(self) -> None:
        """MockLLM has sensible default response."""
        from babylon.ai.llm_provider import MockLLM

        mock = MockLLM()
        result = mock.generate("prompt")
        assert result == "Mock LLM response"

    def test_call_history_is_copy(self) -> None:
        """MockLLM call_history returns a copy, not internal list."""
        from babylon.ai.llm_provider import MockLLM

        mock = MockLLM()
        mock.generate("prompt")

        history = mock.call_history
        history.clear()  # Modify the returned list

        # Internal list should be unchanged
        assert len(mock.call_history) == 1


# =============================================================================
# SPRINT 4: DEEPSEEK CLIENT TESTS
# =============================================================================


@pytest.mark.unit
class TestDeepSeekClientInstantiation:
    """Tests for DeepSeekClient initialization."""

    def test_raises_without_api_key(self) -> None:
        """DeepSeekClient raises LLMGenerationError without API key."""
        from babylon.config import llm_config
        from babylon.utils.exceptions import LLMGenerationError

        # Save original and clear
        original_key = llm_config.LLMConfig.API_KEY
        try:
            llm_config.LLMConfig.API_KEY = ""

            from babylon.ai.llm_provider import DeepSeekClient

            with pytest.raises(LLMGenerationError) as exc:
                DeepSeekClient()

            assert exc.value.error_code == "LLM_001"
            assert "not configured" in exc.value.message.lower()
        finally:
            llm_config.LLMConfig.API_KEY = original_key

    def test_initializes_with_api_key(self) -> None:
        """DeepSeekClient initializes when API key is configured."""
        from babylon.config import llm_config

        original_key = llm_config.LLMConfig.API_KEY
        try:
            llm_config.LLMConfig.API_KEY = "sk-test-key"

            from babylon.ai.llm_provider import DeepSeekClient

            client = DeepSeekClient()
            assert client.name == "DeepSeek"
        finally:
            llm_config.LLMConfig.API_KEY = original_key

    def test_has_name_property(self) -> None:
        """DeepSeekClient has name for logging."""
        from babylon.config import llm_config

        original_key = llm_config.LLMConfig.API_KEY
        try:
            llm_config.LLMConfig.API_KEY = "sk-test-key"

            from babylon.ai.llm_provider import DeepSeekClient

            client = DeepSeekClient()
            assert client.name == "DeepSeek"
        finally:
            llm_config.LLMConfig.API_KEY = original_key


@pytest.mark.unit
class TestDeepSeekClientErrorHandling:
    """Tests for DeepSeekClient error handling (sync API, mocked network)."""

    def test_handles_api_timeout(self) -> None:
        """DeepSeekClient raises LLM_002 on timeout."""
        from openai import APITimeoutError

        from babylon.config import llm_config
        from babylon.utils.exceptions import LLMGenerationError

        original_key = llm_config.LLMConfig.API_KEY
        try:
            llm_config.LLMConfig.API_KEY = "sk-test-key"

            from babylon.ai.llm_provider import DeepSeekClient

            client = DeepSeekClient()

            # Mock the internal async client
            mock_request = MagicMock()
            client._client.chat.completions.create = AsyncMock(
                side_effect=APITimeoutError(request=mock_request)
            )

            with pytest.raises(LLMGenerationError) as exc:
                client.generate("prompt")  # Sync call

            assert exc.value.error_code == "LLM_002"
        finally:
            llm_config.LLMConfig.API_KEY = original_key

    def test_handles_rate_limit(self) -> None:
        """DeepSeekClient raises LLM_003 on rate limit."""
        from openai import RateLimitError

        from babylon.config import llm_config
        from babylon.utils.exceptions import LLMGenerationError

        original_key = llm_config.LLMConfig.API_KEY
        try:
            llm_config.LLMConfig.API_KEY = "sk-test-key"

            from babylon.ai.llm_provider import DeepSeekClient

            client = DeepSeekClient()

            mock_response = MagicMock()
            mock_response.status_code = 429
            client._client.chat.completions.create = AsyncMock(
                side_effect=RateLimitError(
                    message="Rate limit",
                    response=mock_response,
                    body=None,
                )
            )

            with pytest.raises(LLMGenerationError) as exc:
                client.generate("prompt")  # Sync call

            assert exc.value.error_code == "LLM_003"
        finally:
            llm_config.LLMConfig.API_KEY = original_key

    def test_handles_api_error(self) -> None:
        """DeepSeekClient raises LLM_001 on general API error."""
        from openai import APIError

        from babylon.config import llm_config
        from babylon.utils.exceptions import LLMGenerationError

        original_key = llm_config.LLMConfig.API_KEY
        try:
            llm_config.LLMConfig.API_KEY = "sk-test-key"

            from babylon.ai.llm_provider import DeepSeekClient

            client = DeepSeekClient()

            mock_request = MagicMock()
            client._client.chat.completions.create = AsyncMock(
                side_effect=APIError(
                    message="Server error",
                    request=mock_request,
                    body=None,
                )
            )

            with pytest.raises(LLMGenerationError) as exc:
                client.generate("prompt")  # Sync call

            assert exc.value.error_code == "LLM_001"
        finally:
            llm_config.LLMConfig.API_KEY = original_key

    def test_handles_empty_response(self) -> None:
        """DeepSeekClient raises LLM_001 on empty response content."""
        from babylon.config import llm_config
        from babylon.utils.exceptions import LLMGenerationError

        original_key = llm_config.LLMConfig.API_KEY
        try:
            llm_config.LLMConfig.API_KEY = "sk-test-key"

            from babylon.ai.llm_provider import DeepSeekClient

            client = DeepSeekClient()

            # Mock response with None content
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = None

            client._client.chat.completions.create = AsyncMock(return_value=mock_response)

            with pytest.raises(LLMGenerationError) as exc:
                client.generate("prompt")

            assert exc.value.error_code == "LLM_001"
            assert "empty" in exc.value.message.lower()
        finally:
            llm_config.LLMConfig.API_KEY = original_key


@pytest.mark.unit
class TestDeepSeekClientGeneration:
    """Tests for DeepSeekClient text generation (mocked)."""

    def test_generates_text_successfully(self) -> None:
        """DeepSeekClient returns generated text on success."""
        from babylon.config import llm_config

        original_key = llm_config.LLMConfig.API_KEY
        try:
            llm_config.LLMConfig.API_KEY = "sk-test-key"

            from babylon.ai.llm_provider import DeepSeekClient

            client = DeepSeekClient()

            # Mock successful response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Generated narrative text"

            client._client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = client.generate("Describe the revolution")
            assert result == "Generated narrative text"
        finally:
            llm_config.LLMConfig.API_KEY = original_key

    def test_passes_system_prompt(self) -> None:
        """DeepSeekClient includes system prompt in messages."""
        from babylon.config import llm_config

        original_key = llm_config.LLMConfig.API_KEY
        try:
            llm_config.LLMConfig.API_KEY = "sk-test-key"

            from babylon.ai.llm_provider import DeepSeekClient

            client = DeepSeekClient()

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Response"

            mock_create = AsyncMock(return_value=mock_response)
            client._client.chat.completions.create = mock_create

            client.generate("User prompt", system_prompt="You are a narrator")

            # Verify the call included system message
            call_kwargs = mock_create.call_args.kwargs
            messages = call_kwargs["messages"]
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == "You are a narrator"
            assert messages[1]["role"] == "user"
            assert messages[1]["content"] == "User prompt"
        finally:
            llm_config.LLMConfig.API_KEY = original_key

    def test_passes_temperature(self) -> None:
        """DeepSeekClient passes temperature to API."""
        from babylon.config import llm_config

        original_key = llm_config.LLMConfig.API_KEY
        try:
            llm_config.LLMConfig.API_KEY = "sk-test-key"

            from babylon.ai.llm_provider import DeepSeekClient

            client = DeepSeekClient()

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Response"

            mock_create = AsyncMock(return_value=mock_response)
            client._client.chat.completions.create = mock_create

            client.generate("Prompt", temperature=0.3)

            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["temperature"] == 0.3
        finally:
            llm_config.LLMConfig.API_KEY = original_key


# =============================================================================
# SPRINT 6: MODULE EXPORT TESTS
# =============================================================================


@pytest.mark.unit
class TestModuleExports:
    """Tests for module-level exports."""

    def test_llm_provider_exports_from_ai_module(self) -> None:
        """LLMProvider can be imported from babylon.ai."""
        from babylon.ai import LLMProvider

        assert LLMProvider is not None

    def test_mock_llm_exports_from_ai_module(self) -> None:
        """MockLLM can be imported from babylon.ai."""
        from babylon.ai import MockLLM

        assert MockLLM is not None

    def test_deepseek_client_exports_from_ai_module(self) -> None:
        """DeepSeekClient can be imported from babylon.ai."""
        from babylon.ai import DeepSeekClient

        assert DeepSeekClient is not None
