"""FFI contract: babylon_tui.run drives a headless frame and records host calls."""

from __future__ import annotations

import json

import pytest

babylon_tui = pytest.importorskip(
    "babylon_tui",
    reason="opt-in tui group not installed (uv sync --group tui + maturin develop)",
)


class _FakeHost:
    """The M1 host surface, minimally faked (full row shape — LobbyRow is
    strict, so a three-field M0-era row would render an empty catalog)."""

    def lobby_catalog_json(self) -> str:
        return json.dumps(
            [
                {
                    "campaign_id": "c1",
                    "name": "campaign-a3f9b2c1d0e5",
                    "codename": "Wayne County",
                    "tick": 0,
                    "status": "ACTIVE",
                    "defines_hash": "dh1",
                    "engine_version": "ev1",
                }
            ]
        )

    def load_campaign(self, campaign_id: str) -> str:
        return json.dumps({"ok": True, "campaign_id": campaign_id})

    def read_page_json(self, subject: str) -> str:
        if subject == "briefing/c1":
            return json.dumps("# Briefing\n\nOperation begins.")
        return "null"

    def known_subjects_json(self) -> str:
        return json.dumps(["Detroit"])

    def backlinks_json(self, subject: str) -> str:
        return "[]"

    def subject_view_json(self, subject: str) -> str:
        return "null"

    def watchlist_json(self) -> str:
        return "[]"


def _config(**overrides: object) -> str:
    cfg: dict[str, object] = {
        "campaign_id": "c1",
        "campaign_name": "Wayne County",
        "render_tier": "glyph",
        "tutorial_enabled": False,
        "narrator_enabled": False,
        "headless": True,
    }
    cfg.update(overrides)
    return json.dumps(cfg)


def test_run_headless_renders_and_records_calls() -> None:
    transcript = json.loads(babylon_tui.run(_FakeHost(), _config()))
    assert "lobby_catalog_json" in transcript["host_calls"]
    assert "Wayne County" in transcript["frames"][0]


def test_run_headless_scripted_flow_lobby_to_briefing_to_quit() -> None:
    """Task 19's BDD-harness foundation: script steps replay through the
    real FFI, each appending a frame; host-call order pins the seam."""
    transcript = json.loads(
        babylon_tui.run(
            _FakeHost(),
            _config(script=[{"key": "enter"}, {"key": "q"}, {"key": "q"}]),
        )
    )
    # Frames: initial lobby, briefing after enter, lobby after first q;
    # the final q quits (no frame after quit).
    assert len(transcript["frames"]) == 3
    assert "Wayne County" in transcript["frames"][0]
    assert "Briefing" in transcript["frames"][1]
    assert "CAMPAIGNS" in transcript["frames"][2]
    assert transcript["host_calls"] == [
        "lobby_catalog_json",
        "load_campaign",
        "known_subjects_json",
        "read_page_json",
        "backlinks_json",
    ]
