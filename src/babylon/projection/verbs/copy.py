"""Player-facing ineligibility copy for the nine verbs (spec-116 FR-4.8).

One ``(reason, remedy)`` pair per canonical verb, shown when the verb's
target-existence predicate is empty — the SAME predicates that yield the
per-verb empty target lists (:func:`babylon.projection.verbs.plate.build_verb_plate`).

Relocated from ``web/game/verb_copy.py`` by Program 24 P2 WO-38 (the web
module is now a re-export shim, same pattern as the fog relocation).
Stdlib-only so every client — TUI plate, legacy bridges — reads one table
and can never disagree on player-facing text. Copy is prose, not a
coefficient: it deliberately does NOT live in ``GameDefines``.

Verifiability (CLAUDE.md): every remedy names only capabilities that
exist. MOVE genuinely mutates ``territory_ids``
(``babylon/engine/actions/move.py`` — relocate/expand).

EDUCATE's remedy was rewritten 2026-07-18 (Track 1 / Task 8c). It
previously promised NO action, on the reasoning that nothing could create
an organized community: ``SocialClass`` has no ``territory_ids`` field, so
no social_class node ever matched the old ``_nodes_in_territory`` helper at
runtime. That was an accurate description of a BUG, not of the domain —
classes link to territory via TENANCY edges, and the plate resolves them
via the tenancy pass. EDUCATE returns real targets, so the honest remedy is
the same one AID gives: MOVE into a populated territory. Copy that
describes a defect as though it were a rule outlives the defect and
becomes a lie.
"""

from __future__ import annotations

#: verb -> (reason, remedy); read only when ``eligible`` is False.
VERB_INELIGIBILITY_COPY: dict[str, tuple[str, str]] = {
    "educate": (
        "No organized community in your territories yet.",
        "Expand your presence into a populated territory first (MOVE) — "
        "political education needs a class that lives where you operate.",
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
