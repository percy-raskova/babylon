"""Register pins — rulings 26/27 (#381, ADR176) made byte-checkable.

The narrator's registers live as PROMPT DATA (Constitution III.12,
``src/babylon/data/game/prompts/narrator/``); these pins assert the
Director's ruled phrases survive every future prompt edit:

- **ruling 26** (the earned epistemic position): the wire
  (``corporate_system``) is the default because the player is inside the
  core's information order; the underground register
  (``liberated_system``) is achieved materially; the Bondi Algorithm
  voice (``bondi_system``, adopted from ``ai/observer-layer.yaml``)
  serves carceral/repression surfaces.
- **ruling 27** (honesty): THE WIRE FLATTERS the failing reformist —
  dramatic irony the deterministic dossiers contradict; theory's own
  vocabulary arrives BLUNT through the underground register — imperial
  rent, the labor aristocracy, the settler bargain — prompt-pinned
  against model liberalization.
- **carried Standard §5 repair**: ``default_system`` no longer
  adjudicates — "escalate or de-escalate contradictions" and "generate
  realistic consequences" are adjudication instructions shipped as data,
  contra Amendment V / II.5; the narrator observes and narrates only.

Register SELECTION mechanics (press organ, cadre correspondents, the
carceral surface routing) ride a later train — these pins govern the
artifacts' CONTENT, which must hold whatever selects them.
"""

from __future__ import annotations

import pytest

from babylon.intelligence.ai.prompt_registry import get_prompt_registry

pytestmark = [pytest.mark.unit]


class TestDefaultObservesNeverAdjudicates:
    """Standard §5's constitutional repair (contra Amendment V / II.5)."""

    def test_adjudication_instruction_retired(self) -> None:
        text = get_prompt_registry().get("default_system").lower()
        assert "escalate" not in text
        assert "realistic consequences" not in text

    def test_game_master_framing_retired(self) -> None:
        """The engine adjudicates; the narrator is never the game master."""
        assert "game master" not in get_prompt_registry().get("default_system").lower()

    def test_observe_and_narrate_language_present(self) -> None:
        text = get_prompt_registry().get("default_system").lower()
        assert "observ" in text
        assert "simulation" in text  # the narrative-pipeline contract keys on this

    def test_never_invents_outcomes(self) -> None:
        """The repaired prompt states the Amendment V line explicitly."""
        text = get_prompt_registry().get("default_system").lower()
        assert "adjudicat" in text  # "...the engine adjudicates; you never do"


class TestWireFlattersTheFailingReformist:
    """Ruling 27, first clause — dramatic irony the dossiers contradict."""

    def test_flattery_clause_present(self) -> None:
        text = get_prompt_registry().get("corporate_system").lower()
        assert "reformist" in text
        assert "responsible" in text
        assert "flatter" in text

    def test_wire_keeps_its_hegemonic_frame(self) -> None:
        """The pre-ruling DNA survives: passive voice, obscured agency."""
        text = get_prompt_registry().get("corporate_system").lower()
        assert "passive voice" in text
        assert "stability" in text
        assert "downplays" in text


class TestUndergroundSpeaksTheoryBlunt:
    """Ruling 27, second clause — theory's own vocabulary, unsoftened."""

    def test_theory_vocabulary_pinned_verbatim(self) -> None:
        text = get_prompt_registry().get("liberated_system").lower()
        assert "imperial rent" in text
        assert "labor aristocracy" in text
        assert "settler bargain" in text

    def test_anti_liberalization_pin(self) -> None:
        """An 8B model softens theory into liberal mush unless pinned."""
        text = get_prompt_registry().get("liberated_system").lower()
        assert "soften" in text

    def test_underground_keeps_its_register(self) -> None:
        text = get_prompt_registry().get("liberated_system").lower()
        assert "solidarity" in text
        assert "active voice" in text


class TestBondiVoiceForCarceralSurfaces:
    """Ruling 26, third register — adopted from ai/observer-layer.yaml."""

    def test_bondi_artifact_exists_in_registry(self) -> None:
        assert len(get_prompt_registry().get("bondi_system")) > 0

    def test_algorithmic_detachment(self) -> None:
        text = get_prompt_registry().get("bondi_system").lower()
        assert "algorithmic detachment" in text
        assert "emotional" in text  # "No emotional language"

    def test_cold_topology_vocabulary(self) -> None:
        text = get_prompt_registry().get("bondi_system").lower()
        assert "centrality" in text
        assert "network fragmentation" in text
