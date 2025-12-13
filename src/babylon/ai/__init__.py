"""AI layer for narrative generation and game mastering.

This package contains the Ideological Superstructure - AI components
that observe the simulation but cannot modify its state.

The key principle: AI components are observers, not controllers.
They generate narrative from state changes but never influence
the Material Base (simulation mechanics).

Components:
- NarrativeDirector: AI Game Master that observes and narrates
- DialecticalPromptBuilder: Builds prompts following Marxist dialectical materialism
- LLMProvider: Protocol for swappable LLM backends
- MockLLM: Deterministic mock for testing
- DeepSeekClient: Production DeepSeek API client
- NarrativeCommissar: LLM-as-judge for narrative evaluation
- JudgmentResult: Evaluation metrics from Commissar
- MetaphorFamily: Metaphor category enum

Sprint 3.2: Added RAG integration for historical/theoretical context.
Sprint 3.3: Added LLM Provider strategy pattern for text generation.
Sprint 4.2: Added Persona system for customizable narrative voices.
Sprint 4.3: Added NarrativeCommissar for automated narrative evaluation.
"""

from babylon.ai.director import NarrativeDirector
from babylon.ai.judge import JudgmentResult, MetaphorFamily, NarrativeCommissar
from babylon.ai.llm_provider import DeepSeekClient, LLMProvider, MockLLM
from babylon.ai.persona import Persona, VoiceConfig
from babylon.ai.persona_loader import (
    PersonaLoadError,
    load_default_persona,
    load_persona,
)
from babylon.ai.prompt_builder import DialecticalPromptBuilder

__all__ = [
    "NarrativeDirector",
    "DialecticalPromptBuilder",
    "LLMProvider",
    "MockLLM",
    "DeepSeekClient",
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
