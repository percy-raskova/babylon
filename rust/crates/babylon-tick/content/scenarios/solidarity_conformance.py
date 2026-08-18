#!/usr/bin/env python3
"""Dual-implementation conformance oracle for `solidarity/p0-transmit`
(the Solidarity @8.0 port train, issue #557 umbrella, Task 4).

STANDALONE and dependency-free — no `babylon` import, no pytest, stdlib
only. This is deliberate, not an oversight (ADR183 + D146 precedent, per
`task-4-brief.md`'s Global Constraints): the frozen engine
(`src/babylon/engine/systems/solidarity.py`) applies each edge's delta
SEQUENTIALLY, in place, so a literal run of the frozen system would print
the multi-inbound witness's FROZEN answer (0.478), not the port's own
answer (0.31) — the two implementations are known, accepted to diverge
there (D-record 2, `solidarity.bsl`'s own header). The oracle this script
computes is therefore a term-for-term Python transcription of
`content/rules/solidarity.bsl`'s own binding order and collect-then-apply
semantics, not a rerun of the frozen Python system — the same posture
`consciousness_ternary_conformance.py`'s header states for the same
reason.

Regenerate with, from the repository root::

    uv run python rust/crates/babylon-tick/content/scenarios/solidarity_conformance.py

The world below is a literal transcription of
`solidarity-conformance.bscn`, node for node, seed for seed, in the
scenario's own declaration order (Python dict insertion order fixes the
node-id assignment, 0..21, exactly as the `.bscn`'s own node census table
documents). The three defconsts are transcribed from the scenario's own
comment citations (`config/defines/consciousness.py:23-39`).

The engine semantics this script transcribes (ground truth: `run_tick` in
`rust/crates/babylon-bsl/src/tick.rs`, `collect_pass` +
`EffectExecutor::apply_pending_write` in `structural_verbs.rs`), NOT
frozen Python's in-place mutation:

Pass 1 (collect) — every SOCIAL_CLASS subject, in ascending node-id order,
is evaluated against the SAME pre-tick snapshot: no subject's guard or
effect can observe an earlier subject's write this tick, because
`collect_pass` holds only an immutable graph reference for the whole pass.
Within one firing subject, its outbound SOLIDARITY edges are visited in
ascending TARGET-id order (`memory.rs`'s `neighbors`: "a set, not a
multiset", sorted). Each qualifying edge's `update-node` effect computes
its FINAL value right here, at collect time (`set`'s operand is the
reduced value, `structural_verbs.rs::PendingWrite`'s own doc), and is
appended to one flat, subject-order list. `emit` writes straight to the
event sink during this same pass, in the same order — it never touches
the graph, so it is exempt from the pre-state discipline that gates
`update-node` (`tick.rs::collect_pass`'s own doc).

Pass 2 (apply) — every collected write applies in COLLECTION order.
Because each `set` write's value was already fixed in Pass 1, applying two
writes to the SAME target just overwrites: the LAST one in collection
order — i.e. the highest-node-id source among however many pushed to that
target — wins. This is exactly the multi-inbound witness's divergence
from frozen: both `multi-source-a` (id 13) and `multi-source-b` (id 14)
compute their delta against the SAME pre-tick `multi-target` reading
(0.1), and source-b's write, collected second, overwrites source-a's.

`clamp01` below transcribes the rule's own floor-then-ceiling `if` nesting
(`solidarity.bsl:207-245`) rather than a bare `min`/`max` call —
functionally identical (verified: the rule's nested `if` and
`max(0, min(1, x))` agree on every value, including exactly 1.0, where
both branches of the outer `if` already equal 1.0), transcribed this way
so a reader can compare this function line-for-line against the `.bsl`
source rather than trust an algebraic simplification.
"""

from __future__ import annotations

ACTIVATION_THRESHOLD = (
    0.3  # solidarity/activation-threshold (config/defines/consciousness.py:23-28)
)
MASS_AWAKENING_THRESHOLD = 0.6  # solidarity/mass-awakening-threshold (:29-34)
NEGLIGIBLE_TRANSMISSION = 0.01  # solidarity/negligible-transmission (:35-39)

Node = dict[str, float | int]
World = dict[str, Node]

# ---- the seed world, verbatim from solidarity-conformance.bscn's node
# forms, in declaration order (= ascending node id, 0..21). Every literal
# below is the exact decimal the .bscn's own p/i/c-suffixed atom parses to
# (unscaled/10^scale of exact integer operands — one correctly-rounded
# IEEE-754 division each, bit-identical to the plain Python decimal literal
# of the same text, since both round the same exact rational to the same
# nearest double). ----
WORLD: World = {
    "plain-source": {"revolutionary": 0.5, "active": 1},
    "plain-target": {"revolutionary": 0.25, "active": 1},
    "awaken-source": {"revolutionary": 0.875, "active": 1},
    "mass-awaken-cross-target": {"revolutionary": 0.5625, "active": 1},
    "mass-awaken-stays-target": {"revolutionary": 0.5, "active": 1},
    "mass-awaken-exact-source": {"revolutionary": 0.6, "active": 1},
    "mass-awaken-exact-target": {"revolutionary": 0.5, "active": 1},
    "zero-strength-source": {"revolutionary": 0.75, "active": 1},
    "zero-strength-target": {"revolutionary": 0.25, "active": 1},
    "at-threshold-source": {"revolutionary": 0.3, "active": 1},
    "at-threshold-target": {"revolutionary": 0.25, "active": 1},
    "negligible-source": {"revolutionary": 0.5, "active": 1},
    "negligible-target": {"revolutionary": 0.4375, "active": 1},
    "multi-source-a": {"revolutionary": 0.9, "active": 1},
    "multi-source-b": {"revolutionary": 0.8, "active": 1},
    "multi-target": {"revolutionary": 0.1, "active": 1},
    "inactive-source": {"revolutionary": 0.9, "active": 0},
    "inactive-source-target": {"revolutionary": 0.25, "active": 1},
    "inactive-target-source": {"revolutionary": 0.9, "active": 1},
    "inactive-target": {"revolutionary": 0.25, "active": 0},
    "clamp-source": {"revolutionary": 1.0, "active": 1},
    "clamp-target": {"revolutionary": 0.875, "active": 1},
}

#: Node id = declaration order, exactly as `solidarity_conformance.rs`'s own
#: `NodeId` constants (`PLAIN_SOURCE: u64 = 0`, …) already fix it.
NODE_IDS: dict[str, int] = {name: i for i, name in enumerate(WORLD)}

#: (source, target, solidarity/strength), in the `.bscn`'s own `(edge …)`
#: declaration order.
SOLIDARITY_EDGES: list[tuple[str, str, float]] = [
    ("plain-source", "plain-target", 0.5),
    ("awaken-source", "mass-awaken-cross-target", 0.5),
    ("awaken-source", "mass-awaken-stays-target", 0.125),
    ("mass-awaken-exact-source", "mass-awaken-exact-target", 1.0),
    ("zero-strength-source", "zero-strength-target", 0.0),
    ("at-threshold-source", "at-threshold-target", 0.5),
    ("negligible-source", "negligible-target", 0.125),
    ("multi-source-a", "multi-target", 0.3),
    ("multi-source-b", "multi-target", 0.3),
    ("inactive-source", "inactive-source-target", 0.5),
    ("inactive-target-source", "inactive-target", 0.5),
    ("clamp-source", "clamp-target", 2.0),
]


def outbound_edges() -> dict[str, list[tuple[str, float]]]:
    """Each source's own outbound SOLIDARITY edges, sorted by ascending
    TARGET node id — `(neighbors self EdgeType/SOLIDARITY :out …)`'s own
    contract (`memory.rs`). Already in that order by construction above;
    sorted explicitly anyway so this function, not the literal's
    declaration order, is what a reader has to trust."""
    by_source: dict[str, list[tuple[str, float]]] = {}
    for source, target, strength in SOLIDARITY_EDGES:
        by_source.setdefault(source, []).append((target, strength))
    for edges in by_source.values():
        edges.sort(key=lambda pair: NODE_IDS[pair[0]])
    return by_source


def clamp01(raw: float) -> float:
    """`max(0.0, min(1.0, target + delta))`, transcribed as the rule's own
    floor-then-ceiling `if` nesting (`solidarity.bsl:207-245`,
    `formulas/solidarity.py:164-165`)."""
    floored = raw if raw > 0 else 0.0
    return floored if floored < 1 else 1.0


def run_tick(world: World) -> tuple[int, list[tuple[str, dict[str, object]]]]:
    """One tick of `solidarity/p0-transmit`, collect-then-apply, exactly as
    `run_tick`/`collect_pass` (`rust/crates/babylon-bsl/src/tick.rs`) drive
    the compiled rule. Returns the fired-subject count and the ordered
    event list; mutates `world` in place with the applied writes."""
    by_source = outbound_edges()
    # Pass 1 reads ONLY this snapshot — `world` itself is never read again
    # until Pass 2 applies, so no subject can observe another subject's
    # write from this same tick (the §4.2 chapter C4 pre-state law).
    pretick = {name: dict(node) for name, node in world.items()}

    fired = 0
    pending_writes: list[tuple[str, float]] = []
    events: list[tuple[str, dict[str, object]]] = []

    for name in world:  # ascending node id
        subject = pretick[name]
        r = subject["revolutionary"]
        active = subject["active"]
        if not (active == 1 and r > ACTIVATION_THRESHOLD):
            continue
        fired += 1
        for target, strength in by_source.get(name, []):
            target_node = pretick[target]
            if not (target_node["active"] == 1 and strength > 0):
                continue
            old = target_node["revolutionary"]
            delta = strength * (r - old)
            if abs(delta) < NEGLIGIBLE_TRANSMISSION:
                continue
            new = clamp01(old + delta)
            pending_writes.append((target, new))
            events.append(
                (
                    "CONSCIOUSNESS_TRANSMISSION",
                    {
                        "source-id": NODE_IDS[name],
                        "target-id": NODE_IDS[target],
                        "delta": delta,
                        "solidarity-strength": strength,
                        "source-consciousness": r,
                        "old-target-consciousness": old,
                        "new-target-consciousness": new,
                    },
                )
            )
            if old < MASS_AWAKENING_THRESHOLD and new >= MASS_AWAKENING_THRESHOLD:
                events.append(
                    (
                        "MASS_AWAKENING",
                        {
                            "target-id": NODE_IDS[target],
                            "old-consciousness": old,
                            "new-consciousness": new,
                            "triggering-source": NODE_IDS[name],
                        },
                    )
                )

    # Pass 2: apply in collection order — subject order outer, per-source
    # target order inner. `set`'s value was already fixed in Pass 1, so the
    # LAST write to a given target in this order wins (no re-read of
    # `world`'s current value, unlike `add`/`sub`/`scale`).
    for target, new in pending_writes:
        world[target]["revolutionary"] = new

    return fired, events


def main() -> None:
    world: World = {name: dict(fields) for name, fields in WORLD.items()}

    print("defines (config/defines/consciousness.py:23-39):")
    print(f"  solidarity/activation-threshold      = {ACTIVATION_THRESHOLD!r}")
    print(f"  solidarity/mass-awakening-threshold   = {MASS_AWAKENING_THRESHOLD!r}")
    print(f"  solidarity/negligible-transmission    = {NEGLIGIBLE_TRANSMISSION!r}")
    print()

    fired, events = run_tick(world)

    print("fired-count table (guard-passed subjects per rule):")
    print(f"  solidarity/p0-transmit = {fired}")
    print(f"  total                  = {fired}")
    print()

    print("post-tick social-class/revolutionary (repr):")
    for name, node in world.items():
        print(f"  {name:<28} id={NODE_IDS[name]:<3} = {node['revolutionary']!r}")
    print()

    print(f"events ({len(events)}):")
    for i, (event_type, payload) in enumerate(events, start=1):
        rendered = " ".join(f"{key}={value!r}" for key, value in payload.items())
        print(f"  {i}. {event_type} {rendered}")
    if not events:
        print("  (none)")


if __name__ == "__main__":
    main()
