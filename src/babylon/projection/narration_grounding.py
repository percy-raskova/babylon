"""The production grounding filter (Standard §5; rulings 26/27's guardrail).

Narration may use ONLY the proper nouns and numbers its grounded inputs
supplied: the system/prompt text (built from real chronicle summaries),
the tick envelope's ``entities[]`` dictionary, and its numeric deltas. A
generation that invents either is REJECTED — the caller records it through
the narrator cache's existing degraded machinery, which renders as a
visible ``{absence}`` page NAMING the offender (III.11: honest absence,
never smoothed-over invention; ruling 27's prompt-pins guard the register,
THIS guards the facts).

Deterministic set arithmetic over tokens — no linguistics, no model in the
validation loop. The filter is deliberately strict about DATA (multi-digit
and decimal numbers, capitalized identifier-like tokens) and deliberately
permissive about PROSE MECHANICS (sentence-initial capitals, small counting
integers): the target is invented data, not style.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = ["GroundingContext", "ground_check", "grounding_from_inputs"]

#: Tokens that look like DATA: decimals, or integers of 2+ digits.
_NUMBER = re.compile(r"\d+\.\d+|\d{2,}")

#: Tokens that look like PROPER NOUNS / identifiers: a capitalized word or
#: an identifier-ish token carrying an underscore or internal capital.
_NOUNISH = re.compile(r"[A-Z][A-Za-z0-9_]*")

#: Common sentence-mechanics words a capitalized position must never flag.
_PROSE_STOPWORDS = frozenset(
    {
        "A",
        "An",
        "And",
        "As",
        "At",
        "But",
        "By",
        "For",
        "If",
        "In",
        "It",
        "Its",
        "No",
        "Nothing",
        "Of",
        "On",
        "One",
        "Or",
        "The",
        "Then",
        "This",
        "That",
        "These",
        "Those",
        "To",
        "Two",
        "Three",
        "When",
        "While",
        "With",
    }
)


class GroundingContext(BaseModel):
    """The allowed vocabulary one tick's narration may draw on."""

    model_config = ConfigDict(frozen=True)

    allowed_tokens: frozenset[str]
    allowed_numbers: frozenset[str]


def _number_forms(value: float | int) -> set[str]:
    """Every rendering a grounded number legitimately takes in prose."""
    forms = {str(value)}
    if isinstance(value, float):
        if value == int(value):
            forms.add(str(int(value)))
        forms.update({f"{value:.1f}", f"{value:.2f}", f"{value:.4f}"})
    return forms


def grounding_from_inputs(
    *,
    system: str,
    prompt: str,
    entities: Iterable[str] = (),
    numbers: Iterable[float | int] = (),
) -> GroundingContext:
    """Build the context from a tick's real inputs.

    Everything in the system/prompt text is grounded by construction (it
    was built from committed chronicle content); the envelope's entities
    and numeric deltas extend it.
    """
    source = f"{system} {prompt}"
    tokens: set[str] = set(_NOUNISH.findall(source))
    tokens.update(entities)
    allowed_numbers: set[str] = set(_NUMBER.findall(source))
    for value in numbers:
        allowed_numbers.update(form for form in _number_forms(value) if _NUMBER.fullmatch(form))
    return GroundingContext(
        allowed_tokens=frozenset(tokens), allowed_numbers=frozenset(allowed_numbers)
    )


def ground_check(text: str, context: GroundingContext) -> str | None:
    """Validate one generation. ``None`` = grounded; else the offense.

    :returns: a human-readable offense string naming the FIRST invented
        token found (the degraded page's error line), or ``None``.
    """
    for number in _NUMBER.findall(text):  # loop bound: numbers in one generation
        if number not in context.allowed_numbers:
            return f"invented number {number!r} — not in the tick's grounded data"
    for noun in _NOUNISH.findall(text):  # loop bound: tokens in one generation
        if noun in _PROSE_STOPWORDS or noun in context.allowed_tokens:
            continue
        return f"invented proper noun {noun!r} — not in the tick's grounded vocabulary"
    return None
