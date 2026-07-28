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

    # --- M2 surface (contract: 2026-07-27-m2-seam-contracts.md). The shell
    # pulls all of these on bind + saves nav on quit, so the fake must speak
    # them (a missing method would raise → panic across the FFI, III.11).

    def pacing_state_json(self) -> str:
        return json.dumps(
            {
                "attached": False,
                "locked": False,
                "lock_reason": None,
                "awaiting_ack": False,
                "pause_summary": None,
                "busy": False,
            }
        )

    def chronicle_rail_json(self) -> str:
        return json.dumps({"autopause_line": None, "rows": []})

    def verb_plate_view_json(self) -> str:
        return "null"

    def endgame_status_json(self) -> str:
        return "null"

    def nav_state_json(self) -> str:
        return json.dumps({"jumplist": [], "breadcrumbs": []})

    def save_nav_state(self, nav_json: str) -> str:
        return json.dumps({"ok": True})

    # --- M3 surface (contract: 2026-07-27-m3-tutorial-contracts.md). This
    # fake never wires a tutorial (every fixture below keeps
    # `tutorial_enabled: False`), so `tutorial_state_json` stays honestly
    # inactive; `new_campaign` is the loud not-implemented envelope (this
    # M0-era fake never mints a real lobby row).

    def tutorial_state_json(self, view_state_json: str) -> str:
        return json.dumps({"active": False})

    def new_campaign(self) -> str:
        return json.dumps({"ok": False, "error": "new_campaign not implemented on _FakeHost"})


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


def test_default_config_keeps_tutorial_disabled() -> None:
    """M3: extending ``_FakeHost`` with ``tutorial_state_json``/
    ``new_campaign`` must not perturb the 12-call pin below — its own
    fixture default keeps ``tutorial_enabled: False``, so no tutorial call
    appears in that list either way."""
    assert json.loads(_config())["tutorial_enabled"] is False


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
    # M2: the bind pulls nav state + the five chrome feeds after the page
    # read, and leaving the campaign (first q) persists nav.
    assert transcript["host_calls"] == [
        "lobby_catalog_json",
        "load_campaign",
        "known_subjects_json",
        "nav_state_json",
        "read_page_json",
        "backlinks_json",
        "endgame_status_json",
        "pacing_state_json",
        "verb_plate_view_json",
        "chronicle_rail_json",
        "watchlist_json",
        "save_nav_state",
    ]
