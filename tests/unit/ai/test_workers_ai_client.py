"""WorkersAIClient: Workers AI via AI Gateway on the pydantic-ai transport.

Behavioral contract (Amendment Y, ADR100): the lane's config validation,
error taxonomy, and factory selection — exercised through the
``ModelFactory`` seam with pydantic-ai test models, no network.
"""

from unittest.mock import MagicMock

import pytest
from openai import APIError, APITimeoutError, RateLimitError
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from babylon.config import LLMConfig
from babylon.intelligence.ai.llm_provider import (
    LLMProvider,
    WorkersAIClient,
    build_llm_provider,
)
from babylon.kernel.exceptions import LLMGenerationError


def _raising_model(exc: Exception) -> FunctionModel:
    def raise_it(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise exc

    return FunctionModel(raise_it)


@pytest.fixture(autouse=True)
def _configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(LLMConfig, "WORKERS_AI_ACCOUNT_ID", "acct123")
    monkeypatch.setattr(LLMConfig, "WORKERS_AI_TOKEN", "tok")


def test_generate_returns_content() -> None:
    seen: dict[str, object] = {}

    def capture(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen["instructions"] = info.instructions
        return ModelResponse(parts=[TextPart("narrated text")])

    client = WorkersAIClient(model_factory=lambda: FunctionModel(capture))
    assert client.generate("prompt", system_prompt="sys") == "narrated text"
    assert seen["instructions"] == "sys"


def test_passes_temperature() -> None:
    seen: dict[str, object] = {}

    def capture(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen["temperature"] = (info.model_settings or {}).get("temperature")
        return ModelResponse(parts=[TextPart("ok")])

    client = WorkersAIClient(model_factory=lambda: FunctionModel(capture))
    client.generate("prompt", temperature=0.3)
    assert seen["temperature"] == 0.3


def test_workers_ai_client_is_llm_provider() -> None:
    client = WorkersAIClient(model_factory=lambda: TestModel(custom_output_text="x"))
    assert isinstance(client, LLMProvider)


def test_empty_response_is_loud() -> None:
    def empty(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart("")])

    client = WorkersAIClient(model_factory=lambda: FunctionModel(empty))
    with pytest.raises(LLMGenerationError) as exc:
        client.generate("prompt")
    assert exc.value.error_code == "LLM_001"


def test_timeout_maps_to_llm_002() -> None:
    client = WorkersAIClient(
        model_factory=lambda: _raising_model(APITimeoutError(request=MagicMock()))
    )
    with pytest.raises(LLMGenerationError) as exc:
        client.generate("prompt")
    assert exc.value.error_code == "LLM_002"


def test_rate_limit_maps_to_llm_003() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 429
    client = WorkersAIClient(
        model_factory=lambda: _raising_model(
            RateLimitError(message="Rate limit", response=mock_response, body=None)
        )
    )
    with pytest.raises(LLMGenerationError) as exc:
        client.generate("prompt")
    assert exc.value.error_code == "LLM_003"


def test_api_error_maps_to_llm_001() -> None:
    client = WorkersAIClient(
        model_factory=lambda: _raising_model(
            APIError(message="Server error", request=MagicMock(), body=None)
        )
    )
    with pytest.raises(LLMGenerationError) as exc:
        client.generate("prompt")
    assert exc.value.error_code == "LLM_001"


def test_missing_token_is_loud(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(LLMConfig, "WORKERS_AI_TOKEN", "")
    with pytest.raises(LLMGenerationError):
        WorkersAIClient()


def test_factory_selects_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(LLMConfig, "PROVIDER", "workers_ai")
    provider = build_llm_provider()
    assert provider.name == "WorkersAI"
    monkeypatch.setattr(LLMConfig, "PROVIDER", "mock")
    assert build_llm_provider().name == "MockLLM"


def test_factory_unknown_provider_is_loud(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(LLMConfig, "PROVIDER", "nonsense")
    with pytest.raises(LLMGenerationError) as exc:
        build_llm_provider()
    assert exc.value.error_code == "LLM_001"
