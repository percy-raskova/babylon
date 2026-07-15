"""WorkersAIClient: Workers AI via AI Gateway, OpenAI-compatible (program-20)."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from openai import APIError, APITimeoutError, RateLimitError

from babylon.config import LLMConfig
from babylon.intelligence.ai.llm_provider import (
    LLMProvider,
    WorkersAIClient,
    build_llm_provider,
)
from babylon.kernel.exceptions import LLMGenerationError


class _FakeCompletions:
    def __init__(self, content: str | None) -> None:
        self._content = content
        self.last_kwargs: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> Any:
        self.last_kwargs = kwargs
        msg = SimpleNamespace(content=self._content)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


class _RaisingCompletions:
    """Fake completions endpoint that raises.

    Mirrors how test_llm_provider.py's DeepSeekClient error-taxonomy tests
    fake APITimeoutError/RateLimitError/APIError via a raising create().
    """

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def create(self, **kwargs: Any) -> Any:
        raise self._exc


def _fake_client(content: str | None) -> Any:
    return SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions(content)))


def _raising_client(exc: Exception) -> Any:
    return SimpleNamespace(chat=SimpleNamespace(completions=_RaisingCompletions(exc)))


@pytest.fixture(autouse=True)
def _configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(LLMConfig, "WORKERS_AI_ACCOUNT_ID", "acct123")
    monkeypatch.setattr(LLMConfig, "WORKERS_AI_TOKEN", "tok")


def test_generate_returns_content() -> None:
    fake = _fake_client("narrated text")
    client = WorkersAIClient(client=fake)
    assert client.generate("prompt", system_prompt="sys") == "narrated text"
    kwargs = fake.chat.completions.last_kwargs
    assert kwargs["model"] == LLMConfig.WORKERS_AI_MODEL
    assert kwargs["messages"][0] == {"role": "system", "content": "sys"}
    assert kwargs["messages"][1] == {"role": "user", "content": "prompt"}


def test_passes_temperature() -> None:
    fake = _fake_client("ok")
    client = WorkersAIClient(client=fake)
    client.generate("prompt", temperature=0.3)
    kwargs = fake.chat.completions.last_kwargs
    assert kwargs["temperature"] == 0.3


def test_workers_ai_client_is_llm_provider() -> None:
    client = WorkersAIClient(client=_fake_client("x"))
    assert isinstance(client, LLMProvider)


def test_empty_response_is_loud() -> None:
    client = WorkersAIClient(client=_fake_client(None))
    with pytest.raises(LLMGenerationError) as exc:
        client.generate("prompt")
    assert exc.value.error_code == "LLM_001"


def test_timeout_maps_to_llm_002() -> None:
    client = WorkersAIClient(client=_raising_client(APITimeoutError(request=MagicMock())))
    with pytest.raises(LLMGenerationError) as exc:
        client.generate("prompt")
    assert exc.value.error_code == "LLM_002"


def test_rate_limit_maps_to_llm_003() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 429
    client = WorkersAIClient(
        client=_raising_client(
            RateLimitError(message="Rate limit", response=mock_response, body=None)
        )
    )
    with pytest.raises(LLMGenerationError) as exc:
        client.generate("prompt")
    assert exc.value.error_code == "LLM_003"


def test_api_error_maps_to_llm_001() -> None:
    client = WorkersAIClient(
        client=_raising_client(APIError(message="Server error", request=MagicMock(), body=None))
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
