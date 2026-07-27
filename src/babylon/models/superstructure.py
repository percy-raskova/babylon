"""The canonical superstructure-register set (P25 U13, ADR140).

The political superstructure (P25 U8-U12) lives in graph-level registers —
``set_graph_attr`` entries owned by single system files (the superstructure
sentinel's ``SUPERSTRUCTURE_ATTR_OWNERS`` licenses every write site). On the
headless runner's ONE persistent graph they are durable across ticks by
construction; through ``simulation_engine.step()``'s per-tick
``WorldState`` <-> graph round-trip they are durable ONLY because
``WorldState.superstructure_registers`` carries every name declared here
(the ``field_stack`` precedent).

This tuple is the models-layer single source of truth for that carriage.
The engine's per-system ``*_ATTR`` constants and the sentinel owner map must
cover exactly this set — pinned three ways by
``tests/unit/models/test_superstructure_registers.py``. Layering: models
imports nothing above itself (Program 14); the engine and the sentinels each
declare their own constants and the test proves correspondence.

Honest absence (Constitution III.11): a register that was never written is
NOT carried as an empty value — ``to_graph`` stamps only the names present
in the field, ``from_graph`` harvests only the names present on the graph.
The six party-less qa:regression scenarios therefore never see any of these
names at all.
"""

from __future__ import annotations

from typing import Final

#: Every graph-level superstructure register, grouped by owning system.
SUPERSTRUCTURE_REGISTERS: Final[tuple[str, ...]] = (
    # PolicySystem @17.47 (ADR135/ADR139)
    "policy_agenda",
    "policy_overlays",
    "sovereign_fiscal",
    "policy_delivery",
    "governance_endgame",
    # ElectoralSystem @17.45 (ADR136/ADR139)
    "electoral_governments",
    "electoral_disillusion",
    "electoral_derecognized",
    "popular_front",
    # DoctrineSystem @14.7 (ADR137)
    "political_form_org_positions",
    # AllegianceSystem @17.42 (ADR134)
    "political_labor_share",
)

__all__ = ["SUPERSTRUCTURE_REGISTERS"]
