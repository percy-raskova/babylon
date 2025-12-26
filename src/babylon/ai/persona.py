"""Persona models for AI narrative voice customization (Sprint 4.2).

This module defines immutable Pydantic models for AI personas that
customize the NarrativeDirector's voice and behavior.

Personas are:
- Frozen (immutable) for consistency
- Validated against JSON Schema at load time
- Used by PromptBuilder to generate system prompts

Design follows the SimulationEvent pattern from babylon.models.events.

Example:
    >>> from babylon.ai.persona import Persona, VoiceConfig
    >>> voice = VoiceConfig(
    ...     tone="Clinical, Dialectical",
    ...     style="Marxist analysis",
    ...     address_user_as="Comrade",
    ... )
    >>> persona = Persona(
    ...     id="test_persona",
    ...     name="Test Persona",
    ...     role="Test Role",
    ...     voice=voice,
    ...     obsessions=["Material conditions"],
    ...     directives=["Analyze dialectically"],
    ... )
    >>> print(persona.render_system_prompt())

See Also:
    :mod:`babylon.ai.persona_loader`: Functions to load personas from JSON files.
    :class:`babylon.ai.prompt_builder.DialecticalPromptBuilder`: Uses personas.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class VoiceConfig(BaseModel):
    """Voice characteristics for a narrative persona (immutable).

    Defines the tone, style, and user address pattern for an AI persona.
    This is a nested model within Persona.

    Attributes:
        tone: Emotional and rhetorical tone (e.g., "Clinical, Dialectical").
        style: Writing style and theoretical framework.
        address_user_as: How the persona addresses the user (e.g., "Architect").

    Example:
        >>> voice = VoiceConfig(
        ...     tone="Clinical, Dialectical, Revolutionary",
        ...     style="High-theoretical Marxist analysis",
        ...     address_user_as="Architect",
        ... )
        >>> voice.tone
        'Clinical, Dialectical, Revolutionary'
    """

    model_config = ConfigDict(frozen=True)

    tone: str = Field(
        ...,
        min_length=1,
        description="Emotional and rhetorical tone",
    )
    style: str = Field(
        ...,
        min_length=1,
        description="Writing style and theoretical framework",
    )
    address_user_as: str = Field(
        ...,
        min_length=1,
        description="How the persona addresses the user",
    )


class Persona(BaseModel):
    """AI narrative persona for the NarrativeDirector (immutable).

    Defines the complete identity and behavioral rules for an AI persona.
    Personas are loaded from JSON files and validated against JSON Schema.

    Attributes:
        id: Unique snake_case identifier.
        name: Full display name of the persona.
        role: Persona's role or title.
        voice: Voice characteristics (nested VoiceConfig).
        obsessions: Topics the persona is obsessed with analyzing.
        directives: Behavioral directives for the persona.
        restrictions: Topics or behaviors to avoid (default empty).

    Example:
        >>> from babylon.ai.persona import Persona, VoiceConfig
        >>> voice = VoiceConfig(
        ...     tone="Clinical",
        ...     style="Marxist",
        ...     address_user_as="Architect",
        ... )
        >>> persona = Persona(
        ...     id="test_persona",
        ...     name="Test",
        ...     role="Role",
        ...     voice=voice,
        ...     obsessions=["Material conditions"],
        ...     directives=["Analyze"],
        ... )
        >>> persona.restrictions
        []
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        ...,
        min_length=1,
        description="Unique snake_case identifier",
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Full display name of the persona",
    )
    role: str = Field(
        ...,
        min_length=1,
        description="Persona's role or title",
    )
    voice: VoiceConfig = Field(
        ...,
        description="Voice characteristics for narrative generation",
    )
    obsessions: list[str] = Field(
        ...,
        min_length=1,
        description="Topics the persona is obsessed with analyzing",
    )
    directives: list[str] = Field(
        ...,
        min_length=1,
        description="Behavioral directives for the persona",
    )
    restrictions: list[str] = Field(
        default_factory=list,
        description="Topics or behaviors to avoid",
    )

    def render_system_prompt(self) -> str:
        """Render the persona as an LLM system prompt.

        Formats all persona attributes into a structured prompt that
        establishes the AI's identity and behavioral rules.

        Returns:
            Formatted system prompt string for LLM consumption.

        Example:
            >>> persona = Persona(...)
            >>> prompt = persona.render_system_prompt()
            >>> assert persona.name in prompt
        """
        sections = [
            self._render_identity_section(),
            self._render_voice_section(),
            self._render_obsessions_section(),
            self._render_directives_section(),
        ]

        # Only include restrictions section if there are restrictions
        if self.restrictions:
            sections.append(self._render_restrictions_section())

        return "\n\n".join(sections)

    def _render_identity_section(self) -> str:
        """Render the identity section of the prompt."""
        return f"""You are {self.name}, the {self.role}.

Your role is to serve as the narrative voice for a geopolitical simulation game,
providing analysis and commentary grounded in material conditions."""

    def _render_voice_section(self) -> str:
        """Render the voice characteristics section."""
        return f"""--- VOICE ---
Tone: {self.voice.tone}
Style: {self.voice.style}
Address the user as: "{self.voice.address_user_as}" """

    def _render_obsessions_section(self) -> str:
        """Render the obsessions section."""
        obsessions_list = "\n".join(f"- {obs}" for obs in self.obsessions)
        return f"""--- OBSESSIONS ---
These are the themes you constantly return to in your analysis:
{obsessions_list}"""

    def _render_directives_section(self) -> str:
        """Render the directives section."""
        directives_list = "\n".join(f"- {d}" for d in self.directives)
        return f"""--- DIRECTIVES ---
Follow these rules in all responses:
{directives_list}"""

    def _render_restrictions_section(self) -> str:
        """Render the restrictions section (only if restrictions exist)."""
        restrictions_list = "\n".join(f"- {r}" for r in self.restrictions)
        return f"""--- RESTRICTIONS ---
Avoid the following:
{restrictions_list}"""
