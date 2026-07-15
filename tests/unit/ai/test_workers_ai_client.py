"""WorkersAIClient: Workers AI via AI Gateway, OpenAI-compatible (program-20)."""

from types import SimpleNamespace
from typing import Any

import pytest

from babylon.config import LLMConfig
from babylon.intelligence.ai.llm_provider import WorkersAIClient, build_llm_provider
from babylon.kernel.exceptions import LLMGenerationError


class _FakeCompletions:
    def __init__(self, content: str | None) -> None:
        self._content = content
        self.last_kwargs: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> Any:
        self.last_kwargs = kwargs
        msg = SimpleNamespace(content=self._content)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


def _fake_client(content: str | None) -> Any:
    return SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions(content)))


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


def test_empty_response_is_loud() -> None:
    client = WorkersAIClient(client=_fake_client(None))
    with pytest.raises(LLMGenerationError):
        client.generate("prompt")


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
