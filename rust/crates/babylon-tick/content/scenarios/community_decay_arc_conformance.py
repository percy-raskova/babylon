#!/usr/bin/env python3
"""The Community @6.0 port train's DECAY-ARC mirror (issue #667, Task 10
Step 5 — plan docs/superpowers/plans/2026-08-18-community-port.md §9, the
D146/ADR183 convention).

STANDALONE, like every mirror: no `babylon` import, no pytest, no import
of the sibling mirror (`community_conformance.py` is the term-for-term
oracle for worlds 1-4; this file transcribes the SAME rules over the arc
world for THREE ticks — the multi-tick half, which is where c00's reset
and c09's reset stop being the identity and start being load-bearing).

Transcription notes specific to the arc:

1. The rule order within each tick is the main mirror's (c00 → … → c11);
   across ticks, the tick boundary is a full write-flush — every write a
   tick makes is visible to the next tick's FIRST read.
2. THE RESETS ARE THE POINT: c00 zeroes the per-tick accumulators and c09
   resets the cost modifier to 1 — deleting c09 makes c10's scale compound
   (tick 2 would read 0.875^2 = 0.765625; the arc proves 0.875 again).
3. The ternary recomputes from the static org landscape EVERY tick to
   (1.0, 0.0, 0.0) — idempotent, r = 1.0 clears the 0.136 floor — while
   heat/cohesion/education-pressure decay by their own α each tick:
   x_k = max(0, x_{k-1}·(1−α)) with x_0 the seed.
4. Unwritten fields: none in this world (its one class is active).
"""

from __future__ import annotations

# The arc world — community-decay-arc-conformance.bscn, transcribed.
SEED = {
    "heat": 0.5,
    "cohesion": 0.75,
    "education-pressure": 0.25,
    "reproduction-cost-modifier": 0.875,
    "revolutionary": 0.5,
    "liberal": 0.25,
    "fascist": 0.25,
}
# The static org landscape: one REVOLUTIONARY org, cadre 0.5 x cohesion
# 0.5 = 0.25 pushed onto the one active class, density 1.0.
ORG_WEIGHT = 0.25
FLOOR_NEW_AFRIKAN = 0.136  # ADR214 (measured; erratum 9)
HEAT_DECAY_ALPHA = 0.05
COHESION_DECAY_ALPHA = 0.03
EDUCATION_PRESSURE_DECAY = 0.1

TICKS = 3


def run() -> None:
    heat = SEED["heat"]
    cohesion = SEED["cohesion"]
    edu = SEED["education-pressure"]
    rcm = SEED["reproduction-cost-modifier"]

    print("community-decay-arc — mirror output (the three-tick oracle)")
    print(f"tick 0 (seed): heat = {heat!r} cohesion = {cohesion!r} edu = {edu!r}")
    for tick in range(1, TICKS + 1):
        # c00-c04: the census and the org-weight decomposition rebuild —
        # the world's content is static, so the accumulators land on the
        # same values every tick: member-count 1, r-raw 0.25, density 1.0.
        member_count = 1.0
        r_raw = ORG_WEIGHT / member_count  # the one class's push
        density_sum = 1.0 / member_count  # org-count 1 / member-count 1

        # c05: unorganized = max(0, 1 - 1.0) = 0; total = 0.25; normalize.
        unorganized = max(0.0, 1.0 - density_sum)
        l_raw = 0.0 + unorganized
        total = r_raw + l_raw + 0.0
        r, l_val, f = r_raw / total, l_raw / total, 0.0  # (1.0, 0.0, 0.0)

        # c06a/c06b: floor 0.136 never binds (r = 1.0) — a loud guard, not
        # an assert (S101): if the arc's ternary ever dips under the floor,
        # the world's own design broke.
        if r < FLOOR_NEW_AFRIKAN:
            raise ValueError(f"arc r {r!r} under the NEW_AFRIKAN floor — the world's design broke")

        # c09 + c10: reset to 1, then scale by the ONE membership's rcm —
        # per-tick, never compounding.
        cost_modifier = 1.0 * rcm

        # c11: the decay (the only cross-tick state that MOVES).
        heat = max(0.0, heat * (1.0 - HEAT_DECAY_ALPHA))
        cohesion = max(0.0, cohesion * (1.0 - COHESION_DECAY_ALPHA))
        edu = max(0.0, edu * (1.0 - EDUCATION_PRESSURE_DECAY))

        print(
            f"tick {tick}: heat = {heat!r} cohesion = {cohesion!r} edu = {edu!r} | "
            f"r = {r!r} l = {l_val!r} f = {f!r} | "
            f"cost-modifier = {cost_modifier!r} | member-count = {member_count!r} "
            f"density-sum = {density_sum!r}"
        )


if __name__ == "__main__":
    run()
