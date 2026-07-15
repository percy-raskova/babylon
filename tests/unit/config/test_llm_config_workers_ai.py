"""Workers AI config surface (program-20 Track B, Program 07 Decision 3)."""

import pytest

from babylon.config import LLMConfig


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    assert LLMConfig.PROVIDER in {"deepseek", "workers_ai", "mock"}
    assert LLMConfig.WORKERS_AI_MODEL == "@cf/openai/gpt-oss-20b"
    assert LLMConfig.WORKERS_AI_GATEWAY_ID == "babylon-narrator"


def test_base_url_requires_account_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(LLMConfig, "WORKERS_AI_ACCOUNT_ID", "")
    with pytest.raises(ValueError):
        LLMConfig.workers_ai_base_url()


def test_base_url_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(LLMConfig, "WORKERS_AI_ACCOUNT_ID", "acct123")
    assert (
        LLMConfig.workers_ai_base_url()
        == "https://api.cloudflare.com/client/v4/accounts/acct123/ai/v1"
    )
