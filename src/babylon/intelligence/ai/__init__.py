"""AI layer for narrative generation and game mastering.

This package contains the Ideological Superstructure - AI components
that observe the simulation but cannot modify its state.

The key principle: AI components are observers, not controllers.
They generate narrative from state changes but never influence
the Material Base (simulation mechanics).

Components:
- NarrativeDirector: AI Game Master that observes and narrates
- DialecticalPromptBuilder: Builds prompts following Marxist dialectical materialism
- NarrativeCommissar: LLM-as-judge for narrative evaluation
- JudgmentResult: Evaluation metrics from Commissar
- MetaphorFamily: Metaphor category enum

Transport (ADR101): this package has NO client stack of its own — the one
LLM transport seam is ``babylon.intelligence.providers`` (NarratorProvider,
resolve_provider, MockNarrator). The former ``llm_provider`` module
(LLMProvider/MockLLM/DeepSeekClient/WorkersAIClient) was retired; git
history is the archive.

Sprint 3.2: Added RAG integration for historical/theoretical context.
Sprint 4.2: Added Persona system for customizable narrative voices.
Sprint 4.3: Added NarrativeCommissar for automated narrative evaluation.
"""

from babylon.intelligence.ai.director import NarrativeDirector
from babylon.intelligence.ai.judge import JudgmentResult, MetaphorFamily, NarrativeCommissar
from babylon.intelligence.ai.persona import Persona, VoiceConfig
from babylon.intelligence.ai.persona_loader import (
    PersonaLoadError,
    load_default_persona,
    load_persona,
)
from babylon.intelligence.ai.prompt_builder import DialecticalPromptBuilder

__all__ = [
    "NarrativeDirector",
    "DialecticalPromptBuilder",
    # Sprint 4.2: Persona system
    "Persona",
    "VoiceConfig",
    "PersonaLoadError",
    "load_persona",
    "load_default_persona",
    # Sprint 4.3: Narrative evaluation (Automated Commissar)
    "NarrativeCommissar",
    "JudgmentResult",
    "MetaphorFamily",
]
