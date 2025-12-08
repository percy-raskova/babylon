"""AI layer for narrative generation and game mastering.

This package contains the Ideological Superstructure - AI components
that observe the simulation but cannot modify its state.

The key principle: AI components are observers, not controllers.
They generate narrative from state changes but never influence
the Material Base (simulation mechanics).

Components:
- NarrativeDirector: AI Game Master that observes and narrates
- DialecticalPromptBuilder: Builds prompts following Marxist dialectical materialism

Sprint 3.2: Added RAG integration for historical/theoretical context.
"""

from babylon.ai.director import NarrativeDirector
from babylon.ai.prompt_builder import DialecticalPromptBuilder

__all__ = ["NarrativeDirector", "DialecticalPromptBuilder"]
