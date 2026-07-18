"""Player-facing ineligibility copy for the nine verbs (spec-116 FR-4.8).

One ``(reason, remedy)`` pair per canonical verb, shown when the verb's
target-existence predicate is empty — the SAME predicates that yield the
per-verb empty target lists (``EngineBridge.get_verb_eligibility``).

Kept in its own stdlib-only module so BOTH bridges (``engine_bridge`` and
``stub_bridge``) read one table and can never disagree on player-facing
text (``stub_bridge`` may not import engine modules — see
``tests/unit/web/test_import_boundary.py``). Copy is prose, not a
coefficient: it deliberately does NOT live in ``GameDefines``.

Verifiability (CLAUDE.md): every remedy names only capabilities that
exist. MOVE genuinely mutates ``territory_ids``
(``babylon/engine/actions/move.py`` — relocate/expand). EDUCATE's remedy
promises no action, because none can create an organized community today:
``SocialClass`` has no ``territory_ids`` field, so no social_class node
ever matches ``_nodes_in_territory`` at runtime — the honest structural
gap the educate payload's own notes name.
"""

from __future__ import annotations

#: verb -> (reason, remedy); read only when ``eligible`` is False.
VERB_INELIGIBILITY_COPY: dict[str, tuple[str, str]] = {
    "educate": (
        "No organized community in your territories yet.",
        "No action can organize a community yet — political education "
        "unlocks the moment an organized class appears where you operate.",
    ),
    "aid": (
        "No community or organization within your territories to aid.",
        "Expand your presence into a populated territory first (MOVE).",
    ),
    "attack": (
        "No hostile organization or institution within your reach.",
        "Expand your presence (MOVE), or wait for state forces to enter your territories.",
    ),
    "mobilize": (
        "No business or civil-society organization within your territories to mobilize against.",
        "Expand toward workplaces and civil society (MOVE), or wait for "
        "new organizations to emerge.",
    ),
    "campaign": (
        "No territories exist in this session yet.",
        "Campaign targets appear once the scenario map is seeded.",
    ),
    "move": (
        "No territory exists to relocate into.",
        "Territories appear once the scenario map is seeded.",
    ),
    "investigate": (
        "Your organization has no territorial presence to scan from.",
        "Establish presence in a territory first (MOVE).",
    ),
    "reproduce": (
        "Your organization is not present in the world graph.",
        "Reload the session — this indicates a corrupted game state.",
    ),
    "negotiate": (
        "No other organization exists to negotiate with.",
        "Rival and allied organizations emerge as the simulation unfolds.",
    ),
}
