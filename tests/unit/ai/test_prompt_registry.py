"""Prompt registry: versioned narrator prompt artifacts (Constitution III.6/III.12)."""

from pathlib import Path

import pytest

from babylon.intelligence.ai.prompt_registry import PromptRegistry, get_prompt_registry


def test_registry_loads_known_prompts() -> None:
    reg = get_prompt_registry()
    for name in ("corporate_system", "liberated_system", "default_system"):
        text = reg.get(name)
        assert isinstance(text, str) and len(text) > 50


def test_unknown_prompt_fails_loud() -> None:
    reg = get_prompt_registry()
    with pytest.raises(KeyError):
        reg.get("does_not_exist")


def test_version_is_content_hash(tmp_path: Path) -> None:
    d = tmp_path / "prompts"
    d.mkdir()
    (d / "a.txt").write_text("alpha")
    reg1 = PromptRegistry(d)
    v1 = reg1.version()
    assert v1.startswith("sha256:") and len(v1) == len("sha256:") + 12
    (d / "a.txt").write_text("alpha CHANGED")
    assert PromptRegistry(d).version() != v1  # drift is impossible to hide


def test_director_prompts_come_from_registry() -> None:
    from babylon.intelligence.ai import director

    reg = get_prompt_registry()
    assert reg.get("corporate_system") == director.CORPORATE_SYSTEM_PROMPT
    assert reg.get("liberated_system") == director.LIBERATED_SYSTEM_PROMPT
