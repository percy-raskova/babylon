#!/usr/bin/env python3
"""P27 Phase 0 Task 13 Step 1 — mechanical stochastic-family trace.

Derives which graph attribute names are DETERMINISTIC vs STOCHASTIC by
starting from the RNG call sites named in
``reports/p27-porting-contract-table.md`` (Task 10's RNG-usage column) and
propagating the taint exactly ONE step to systems that read a tainted
attribute.

Deliberately CONSERVATIVE / OVER-APPROXIMATING, per the plan's Task 13
Step 1 instruction:

* the "write-set" extraction matches ANY bracket-string graph access
  (``node["attr"]``) in an RNG-touched system's file, not only genuine
  writes — a read of a stochastic-adjacent attribute gets tainted too;
* propagation stops after one hop, not a full transitive closure;
* stdlib-only (``re`` + ``pathlib``), no AST, so it cannot tell a read
  from a write or resolve aliasing — it is a cheap, reproducible,
  hand-auditable rule, not a precise dataflow analysis.

False positives (marking a family stochastic when it never actually
depends on an RNG draw) are the accepted cost of this rule; the failure
mode it guards against — silently treating a stochastic family as
deterministic and tolerance-bounding it — would be worse (spec §8.5).

Usage::

    python3 tools/stochastic_family_trace.py
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SYSTEMS_DIR = REPO / "src" / "babylon" / "engine" / "systems"
OODA_DIR = SYSTEMS_DIR / "ooda"

# RNG-tainted systems and their home files, transcribed from Task 10's
# porting-contract table (reports/p27-porting-contract-table.md rows
# 16-24) — the single named artifact for RNG-usage-per-system.
RNG_SYSTEMS: dict[str, dict[str, object]] = {
    "FactionInfluenceSystem": {
        "files": [SYSTEMS_DIR / "faction_influence.py"],
        "rng": "direct: resolve_rng(services, tick) @ faction_influence.py:68",
    },
    "DoctrineSystem": {
        "files": [SYSTEMS_DIR / "doctrine.py"],
        "rng": "direct: resolve_rng(services, tick) @ doctrine.py:673",
    },
    "StruggleSystem": {
        "files": [SYSTEMS_DIR / "struggle.py"],
        "rng": "direct: resolve_rng(services, tick) @ struggle.py:299",
    },
    "ElectoralSystem": {
        "files": [SYSTEMS_DIR / "electoral.py"],
        "rng": "direct: resolve_rng(services, tick) typed as random.Random @ electoral.py:841",
    },
    "FascistFactionSystem": {
        "files": [SYSTEMS_DIR / "reactionary.py"],
        "rng": "direct: resolve_rng(services, tick) @ reactionary.py:241",
    },
    "OODASystem": {
        "files": (
            [SYSTEMS_DIR / "ooda.py"]
            + (
                [
                    OODA_DIR / "npc_stub.py",
                    OODA_DIR / "state_ai" / "decision.py",
                    OODA_DIR / "state_ai" / "repress_effects.py",
                    OODA_DIR / "state_ai" / "administer_effects.py",
                ]
                if OODA_DIR.is_dir()
                else []
            )
        ),
        "rng": (
            "transitive: ooda/npc_stub.py::select_npc_actions -> "
            "ooda/state_ai/{decision,repress_effects,administer_effects}.py "
            "(random.Random(rng_seed))"
        ),
    },
}

# Mechanical extraction patterns (conservative, per module docstring above).
BRACKET_STRING = re.compile(r"""\[\s*["']([A-Za-z_][A-Za-z0-9_]*)["']\s*\]""")
UPDATE_NODE_CALL = re.compile(r"update_node\([^)]*?\{([^}]*)\}", re.S)
DICT_KEY = re.compile(r"""["']([A-Za-z_][A-Za-z0-9_]*)["']\s*:""")
GET_CALL = re.compile(r"""\.get\(\s*["']([A-Za-z_][A-Za-z0-9_]*)["']""")


def extract_attrs(path: Path) -> set[str]:
    """Every graph attribute name mechanically touched in ``path``.

    Matches bracket-string access, ``update_node({...})`` dict-literal keys,
    and ``.get("...")`` calls. Does not distinguish read from write —
    intentional, see module docstring.
    """
    if not path.is_file():
        return set()
    text = path.read_text()
    attrs = set(BRACKET_STRING.findall(text))
    attrs |= set(GET_CALL.findall(text))
    for block in UPDATE_NODE_CALL.findall(text):
        attrs |= set(DICT_KEY.findall(block))
    return attrs


def find_all_system_files() -> dict[str, Path]:
    """Every ``engine/systems/*.py`` file (excluding ``__init__.py``), by stem.

    Scope note: this mechanical pass covers the ``engine/systems/`` package
    only. Three systems are hosted outside it (TickDynamicsSystem in
    ``domain/economics/tick/system/``, ConsciousnessSystem in
    ``domain/bifurcation/consciousness.py``, ImperialRentSystem's home file
    is ``economic.py`` inside this package so it IS covered) — the two
    domain-hosted exceptions are out of this scaffold's one-hop scope,
    named here rather than silently skipped.
    """
    return {p.stem: p for p in SYSTEMS_DIR.glob("*.py") if p.name != "__init__.py"}


def main() -> None:
    all_files = find_all_system_files()
    rng_paths = {f for info in RNG_SYSTEMS.values() for f in info["files"]}  # type: ignore[misc]

    # Step 0: seed taint directly from every RNG-touched file's attribute set.
    tainted: dict[str, str] = {}
    for sysname, info in RNG_SYSTEMS.items():
        for f in info["files"]:  # type: ignore[union-attr]
            for attr in extract_attrs(f):
                tainted.setdefault(attr, f"STOCHASTIC({sysname})")

    # Step 1: propagate ONE hop — any other engine/systems file that
    # mentions a tainted attribute name anywhere gets its OWN attribute set
    # tainted too, attributed to the originating RNG system.
    propagated: dict[str, str] = {}
    for stem, path in sorted(all_files.items()):
        if path in rng_paths:
            continue
        text = path.read_text()
        hit_taints = [a for a in tainted if re.search(rf"""["']{re.escape(a)}["']""", text)]
        if not hit_taints:
            continue
        source_label = tainted[hit_taints[0]]
        for attr in extract_attrs(path):
            propagated.setdefault(
                attr, f"{source_label} -> propagated via {stem} (reads {hit_taints[0]!r})"
            )

    combined: dict[str, str] = {**tainted}
    for k, v in propagated.items():
        combined.setdefault(k, v)

    deterministic: set[str] = set()
    for _stem, path in sorted(all_files.items()):
        for attr in extract_attrs(path):
            if attr not in combined:
                deterministic.add(attr)

    print("# Stochastic family trace (mechanical, conservative, one-hop)")
    print()
    print("| attribute | classification |")
    print("|---|---|")
    for attr in sorted(combined):
        print(f"| `{attr}` | {combined[attr]} |")
    for attr in sorted(deterministic):
        print(f"| `{attr}` | DETERMINISTIC |")
    print()
    print(f"Total attributes seen: {len(combined) + len(deterministic)}")
    print(f"  STOCHASTIC (direct or one-hop propagated): {len(combined)}")
    print(f"  DETERMINISTIC: {len(deterministic)}")


if __name__ == "__main__":
    main()
