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

Sprint 3.2: Added RAG integration for historical/theoretical context.
Sprint 3.3: Added LLM Provider strategy pattern for text generation.
Sprint 4.2: Added Persona system for customizable narrative voices.
"""

from babylon.ai.director import NarrativeDirector
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
]
