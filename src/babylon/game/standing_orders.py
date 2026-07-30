"""Standing orders — the verb persists (ADR176 ruling 22).

The pacing model's prerequisite, not a convenience (the dossier's own
finding): the T1 decision cadence (one real choice per 4-8 ticks across a
5,200-tick century) presupposes that a chosen verb PERSISTS between
decisions. This module is that persistence — declared, deterministic, and
amendment-free:

- An order re-submits its verb each tick through the SAME pending-turns
  path a hand-submitted verb takes (``submit_turn`` -> ``get_pending_turns``
  -> the OODA resolvers) — zero new resolver surface, byte-identical
  mechanics. A fresh player verb for the same org SUPPRESSES the order
  that tick (the player's live hand always wins) without canceling it.
- Interrupts are MATERIAL and deterministic — never a ``cooldown_ticks``
  coefficient (ruling 24's coefficient-free law): the order's target
  leaving the graph cancels it; an autopause cancels every active order
  (something demanded the player's attention — persistence must not talk
  over it). An interrupted order surfaces legibly
  (:attr:`~babylon.game.session.GameSession.last_interrupted_order` + a
  log line): the honesty gate — the player always learns WHY their
  standing order stopped.

Orders are session-lifetime in this first cut: they do NOT survive a
quit or crash-resume (there is no persisted record to restore — a fresh
session simply starts with none). Store-side persistence lands with the
client's orders UI train.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StandingOrder(BaseModel):
    """One org's persistent verb (the ``submit_turn`` shape, frozen).

    :param org_id: The organization holding the order.
    :param verb: The verb re-submitted each tick.
    :param action_type: Optional resolver action type (``submit_turn``'s own
        optional).
    :param target_id: Optional target node — when set, the node leaving the
        graph is a material interrupt.
    :param target_community: Optional community target (pass-through).
    """

    model_config = ConfigDict(frozen=True)

    org_id: str
    verb: str
    action_type: str | None = None
    target_id: str | None = None
    target_community: str | None = None


__all__ = ["StandingOrder"]
