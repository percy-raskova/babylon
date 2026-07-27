"""FFI contract: babylon_tui.run drives a headless frame and records host calls."""

from __future__ import annotations

import json

import pytest

babylon_tui = pytest.importorskip(
    "babylon_tui",
    reason="opt-in tui group not installed (uv sync --group tui + maturin develop)",
)


class _FakeHost:
    def lobby_catalog_json(self) -> str:
        return json.dumps([{"campaign_id": "c1", "name": "Wayne County", "tick": 0}])


def test_run_headless_renders_and_records_calls() -> None:
    transcript = json.loads(
        babylon_tui.run(
            _FakeHost(),
            json.dumps(
                {
                    "campaign_id": "c1",
                    "campaign_name": "Wayne County",
                    "render_tier": "glyph",
                    "tutorial_enabled": False,
                    "narrator_enabled": False,
                    "headless": True,
                }
            ),
        )
    )
    assert "lobby_catalog_json" in transcript["host_calls"]
    assert "Wayne County" in transcript["frames"][0]
