"""Declared data for the superstructure-direction sentinel (I-ORD, ADR135).

The I-ORD invariant (the-electoral-question.md §2.4; charter U9(b)): the
superstructure acts on the base only through the next cycle of production.
Call ORDER is already proven dynamically (INV-013's ``SystemCallSpy``), and
base systems reading a register necessarily see the prior tick's value by
pipeline position — so the STATIC content of I-ORD is write OWNERSHIP: each
political-superstructure graph register has a declared owner set, and no
MATERIAL_BASE-partition file may ever write one (a base-side write would be
readable by later base systems the SAME tick, corrupting the direction).

Registry only — no logic (the vocabulary-family shape). The sentinel package
is layer 0.5 and may not import the engine (import-linter), so the
material-base file list is HAND-DECLARED here and kept honest by the citing
test ``tests/unit/sentinels/test_superstructure.py``, which imports
``simulation_engine.MATERIAL_BASE_SYSTEMS`` from the test layer and asserts
the two lists agree.
"""

from __future__ import annotations

from typing import Final

#: Repo-relative scan root — production code only (tests seed registers
#: freely; ``web/`` is legacy and gate-exempt, Amendment V).
SCAN_ROOT: Final[str] = "src/babylon"

#: Each superstructure graph register → the repo-relative files licensed to
#: write it (``set_graph_attr``). The OODA dispatch's LEGISLATE enqueue seam
#: routes through ``policy.enqueue_agenda_item``, so the agenda's only WRITE
#: SITE is policy.py — owners are files with licensed sites, never callers.
SUPERSTRUCTURE_ATTR_OWNERS: Final[dict[str, frozenset[str]]] = {
    "policy_agenda": frozenset({"src/babylon/engine/systems/policy.py"}),
    "policy_overlays": frozenset({"src/babylon/engine/systems/policy.py"}),
    "sovereign_fiscal": frozenset({"src/babylon/engine/systems/policy.py"}),
    "policy_delivery": frozenset({"src/babylon/engine/systems/policy.py"}),
    "political_labor_share": frozenset({"src/babylon/engine/systems/allegiance.py"}),
    # P25 U10 (ADR136): ElectoralSystem owns the electoral registers.
    "electoral_governments": frozenset({"src/babylon/engine/systems/electoral.py"}),
    "electoral_disillusion": frozenset({"src/babylon/engine/systems/electoral.py"}),
    # P25 U12 (ADR139): ElectoralSystem owns the popular-front conjuncture
    # register (ConsciousnessSystem @17.0 and AllegianceSystem @17.42 read
    # it one tick stale — never write it).
    "popular_front": frozenset({"src/babylon/engine/systems/electoral.py"}),
    # P25 U11 (ADR137): DoctrineSystem @14.7 owns the organizational
    # political-form positions ContradictionSystem @18.0 reads one tick later.
    "political_form_org_positions": frozenset({"src/babylon/engine/systems/doctrine.py"}),
    # P25 U12 (ADR139): PolicySystem detects the ceiling contact, so it owns
    # the absorbing governance-endgame register; ElectoralSystem @17.45
    # consumes it one tick stale (Allende coup / synthesis hope) — never
    # writes it.
    "governance_endgame": frozenset({"src/babylon/engine/systems/policy.py"}),
}

#: Module-level constant names that alias a declared register (the scanner
#: resolves ``set_graph_attr(POLICY_AGENDA_ATTR, ...)`` through this map —
#: static AST cannot do cross-module value flow, so the aliases are declared).
SUPERSTRUCTURE_CONSTANT_ALIASES: Final[dict[str, str]] = {
    "POLICY_AGENDA_ATTR": "policy_agenda",
    "POLICY_OVERLAYS_ATTR": "policy_overlays",
    "SOVEREIGN_FISCAL_ATTR": "sovereign_fiscal",
    "POLICY_DELIVERY_ATTR": "policy_delivery",
    "ELECTORAL_GOVERNMENTS_ATTR": "electoral_governments",
    "ELECTORAL_DISILLUSION_ATTR": "electoral_disillusion",
    "POPULAR_FRONT_ATTR": "popular_front",
    "POLITICAL_FORM_POSITIONS_ATTR": "political_form_org_positions",
    "GOVERNANCE_ENDGAME_ATTR": "governance_endgame",
}

#: The MATERIAL_BASE partition's system files (positions 1–13 + Substrate
#: @2.5), hand-declared (layer 0.5 cannot import the engine). The citing
#: test keeps this in lockstep with ``simulation_engine.MATERIAL_BASE_SYSTEMS``
#: — a drift here is a red test, not a silent hole.
MATERIAL_BASE_SYSTEM_FILES: Final[frozenset[str]] = frozenset(
    {
        "src/babylon/engine/systems/vitality.py",
        "src/babylon/engine/systems/territory.py",
        "src/babylon/engine/systems/substrate.py",
        "src/babylon/engine/systems/production.py",
        "src/babylon/domain/economics/tick/system/__init__.py",
        "src/babylon/engine/systems/reserve_army.py",
        "src/babylon/engine/systems/community.py",
        "src/babylon/engine/systems/lifecycle.py",
        "src/babylon/engine/systems/solidarity.py",
        "src/babylon/engine/systems/economic.py",
        "src/babylon/engine/systems/dispossession_events.py",
        "src/babylon/engine/systems/decomposition.py",
        "src/babylon/engine/systems/control_ratio.py",
        "src/babylon/engine/systems/metabolism.py",
    }
)
