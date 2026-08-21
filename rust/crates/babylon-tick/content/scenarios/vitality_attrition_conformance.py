"""Independent conformance oracle for the #491 rung-ladder dual measure —
``clearing`` / ``failing_certain`` / ``straddle_band``, the within-class
subsistence measure that stands in for P(S|A) (#491 T5, Phase 3a).

This script is the PROVENANCE of every "Measure arithmetic" vector pinned in
``rust/crates/babylon-tick/tests/vitality_attrition_conformance.rs``.

**This is NOT a frozen-engine replay.** Unlike ``vitality_conformance.py``
(this directory's sibling, which imports and calls the frozen
``VitalitySystem``), this script imports nothing from ``babylon.engine`` or
``babylon.formulas`` and calls no frozen system. ADR183 rules the frozen
engine a STRUCTURE contract, not a correctness oracle, for a measure it never
computed at all; ADR173 rules that P(S|A) is the MEASURE of within-class
wealth dispersion clearing subsistence, never the frozen logistic
(``survival_calculus.py``'s sigmoid) transcribed forward. This script
re-derives ``clearing``/``failing_certain``/``straddle_band`` from first
principles, against the H2' dual-measure definition
(``docs/superpowers/plans/2026-08-17-491-rung-ladder.md`` §6.2, and
``reports/subsistence-unit-reconciliation-2026-08-17.md``): sixteen
per-class wealth-mass shares against a fifteen-cut grid, STEP comparisons at
opposite edges of the SAME grid, complement for the straddling band. No
exponent, no steepness, no sigmoid, no interpolation anywhere in this file —
the S-7 derivation this measure ships in the BSL rule's own
``:material-basis`` and header (§8/T5.5).

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/vitality_attrition_conformance.py

The level set. ``S = s_bio + s_class`` — ADR210 R13's ACQUIESCENCE level set
(register row D188), the same level set the frozen engine's own
``coverage_ratio`` uses. This is the P(S|A) reading; R13's separate
MORTALITY level set (``s_bio`` alone) is Grinding Attrition's business
(T6), not this measure's.

The four classes below are the ones the BSL rule's guard actually admits:
``active = 1`` AND ``population > 0`` AND the sixteen wealth-mass shares
sum to a positive total (the sum-guard — H1's own citation, the UNPOSITIONED
idiom). ``remnant`` (no masses seeded at all, sum = 0) and ``dissolved``
(``active = 0``) are guard-excluded, so no oracle vector exists for either —
"no reading," matching the RED "Absence" vector family (#491 T5.1(4)).
"""

from __future__ import annotations

from typing import NamedTuple

#: The fifteen grid cuts, ratios to the class's own mean wealth — HAND-
#: AUTHORED FIXTURE values transcribed verbatim from
#: ``content/scenarios/vitality-attrition-conformance.bscn``'s
#: ``wealth-sketch/cut-01``..``cut-15`` defconsts (T4, ADR194 R1). Not the
#: ruled universal grid (that is DP-4-gated, T7/T8, unrelated to this
#: measure's own correctness).
CUTS: list[float] = [
    0.18,
    0.25,
    0.32,
    0.40,
    0.50,
    0.62,
    0.75,
    0.90,
    1.05,
    1.22,
    1.40,
    1.60,
    1.85,
    2.15,
    2.50,
]

#: tau, the subsistence horizon — DP-5 = A now (ruled #491, 2026-08-18):
#: the tick's own accounting period, one tick, invoking no frozen authority.
TAU: float = 1.0


class ClassFixture(NamedTuple):
    """One social class, transcribed verbatim from
    ``vitality-attrition-conformance.bscn`` (T4) — the Currency-lane
    ``wealth``/``s-bio``/``s-class`` seeds and the sixteen
    ``wealth-mass-01``..``-16`` shares, rung 1 through rung 16.
    """

    name: str
    wealth: float
    population: int
    s_bio: float
    s_class: float
    masses: list[float]


#: The four guard-admitted classes, in scenario declaration order (core=0,
#: bourgeoisie=1, hermit=2, last-worker=3). ``remnant`` (id 4, all sixteen
#: masses absent) and ``dissolved`` (id 5, ``active = 0``) are guard-
#: excluded — see this module's own docstring.
SUBJECTS: list[ClassFixture] = [
    ClassFixture(
        "core",
        wealth=1000.0,
        population=100,
        s_bio=1.0,
        s_class=1.0,
        # all mass in ONE rung (rung 8) — the "all-mass-in-one-rung" case.
        masses=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    ),
    ClassFixture(
        "bourgeoisie",
        wealth=500.0,
        population=4,
        s_bio=2.0,
        s_class=8.0,
        # all mass at the TOP, open rung 16.
        masses=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
    ),
    ClassFixture(
        "hermit",
        wealth=100.0,
        population=1,
        s_bio=1.0,
        s_class=1.0,
        # the ONE-MEMBER class — all mass in rung 4.
        masses=[0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    ),
    ClassFixture(
        "last-worker",
        wealth=1.0,
        population=1,
        s_bio=1.0,
        s_class=1.0,
        # mass SPLIT across the threshold rung, rungs 1/2, 0.5 each.
        masses=[0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    ),
]


def clearing_failing_straddle(
    masses: list[float], cuts: list[float], w_bar: float, s_stock: float
) -> tuple[float, float, float]:
    """H2' verbatim: the dual measure over the SAME 15-cut grid, at
    opposite edges.

    ``c_k = 1 iff cut_{k-1} * w_bar >= s_stock`` for rung *k* = 2..16 (rung
    1's lower edge is the implicit, unspellable 0 — ``0.0r`` is
    ``E-LEX-027`` — so rung 1 never contributes to ``clearing`` by
    construction, not by omission).

    ``f_k = 1 iff cut_k * w_bar < s_stock`` for rung *k* = 1..15 (rung 16 is
    open above — nothing establishes its failure, ``f_16 == 0`` always).

    ``straddle_band = mass_sum - clearing - failing_certain`` — the mass
    of the ONE rung the threshold actually cuts through, published rather
    than silently folded into either side, complemented against the BOUND
    total (matching the BSL rule's C-7 repair) so a partially-seeded mass
    vector cannot fabricate unseeded mass.
    """
    edges = [cut * w_bar for cut in cuts]  # edges[i] is cut_{i+1}'s dollar edge
    clearing = 0.0
    for k in range(2, 17):  # rungs 2..16
        if edges[k - 2] >= s_stock:  # cut_{k-1} -> edges[(k-1)-1]
            clearing += masses[k - 1]
    failing_certain = 0.0
    for k in range(1, 16):  # rungs 1..15
        if edges[k - 1] < s_stock:  # cut_k -> edges[k-1]
            failing_certain += masses[k - 1]
    mass_sum = sum(masses)
    straddle_band = mass_sum - clearing - failing_certain
    return clearing, failing_certain, straddle_band


def main() -> None:
    """Print the four guard-admitted classes' measure vectors."""
    print("measure vectors (S = s_bio + s_class, ADR210 R13 acquiescence level set; tau=1.0):")
    for subj in SUBJECTS:
        w_bar = subj.wealth / subj.population
        s = subj.s_bio + subj.s_class
        s_stock = s * TAU
        clearing, failing_certain, straddle_band = clearing_failing_straddle(
            subj.masses, CUTS, w_bar, s_stock
        )
        total = clearing + failing_certain + straddle_band
        if total != 1.0:
            raise SystemExit(f"{subj.name}: the dual-plus-straddle identity failed, got {total!r}")
        print(
            f"  {subj.name:<12} w_bar={w_bar!r} s_stock={s_stock!r} "
            f"clearing={clearing!r} failing_certain={failing_certain!r} "
            f"straddle_band={straddle_band!r}"
        )


if __name__ == "__main__":
    main()
