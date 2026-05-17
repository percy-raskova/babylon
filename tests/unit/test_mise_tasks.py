"""Unit tests for mise task discoverability (T034a, spec-064 SC-005)."""

from __future__ import annotations

from pathlib import Path

import pytest

MISE_TOML = Path(".mise.toml")


@pytest.mark.skipif(not MISE_TOML.exists(), reason=".mise.toml not present")
class TestMiseTaskDiscoverability:
    """Required mise tasks exist with non-empty descriptions."""

    def test_sim_e2e_michigan_declared(self) -> None:
        contents = MISE_TOML.read_text()
        assert '[tasks."sim:e2e-michigan"]' in contents

    def _e2e_block(self) -> str:
        contents = MISE_TOML.read_text()
        header = '[tasks."sim:e2e-michigan"]'
        block_start = contents.index(header) + len(header)
        # Block runs until the next "[tasks." heading.
        following = contents[block_start:]
        next_heading = following.find("\n[tasks.")
        return following[:next_heading] if next_heading != -1 else following

    def test_sim_e2e_michigan_has_description(self) -> None:
        block = self._e2e_block()
        match = [line for line in block.splitlines() if line.startswith("description = ")]
        assert match, "sim:e2e-michigan has no description"
        assert len(match[0].split()) >= 4

    def test_sim_e2e_michigan_invokes_runner_module(self) -> None:
        block = self._e2e_block()
        assert "babylon.engine.headless_runner" in block
