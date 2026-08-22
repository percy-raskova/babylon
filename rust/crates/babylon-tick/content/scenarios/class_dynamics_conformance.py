#!/usr/bin/env python3
"""Frozen mirror for the class-dynamics primary conformance world.

Plan: docs/superpowers/plans/2026-08-18-tickdynamics-port.md
Task: Task 2 Step 4 — the primary mirror.
Frozen source:
  - src/babylon/domain/economics/dynamics/transition_engine.py (346 lines)
  - src/babylon/domain/economics/dynamics/accumulation.py (106 lines)
  - src/babylon/domain/economics/dynamics/dispossession.py (127 lines)
  - src/babylon/domain/economics/dynamics/crisis.py (181 lines)
  - src/babylon/domain/economics/dynamics/savings_schedule.py (95 lines)
  - src/babylon/domain/economics/dynamics/types.py (321 lines)
  - src/babylon/domain/economics/dynamics/validation.py (300 lines)
  - caller: src/babylon/domain/economics/tick/system/__init__.py:2346-2458

Reproduction command (from the repository root):
  PYTHONPATH="$PWD/src" uv run python \
      rust/crates/babylon-tick/content/scenarios/class_dynamics_conformance.py

# ADR183 disclaimer

The frozen engine is the contract source for STRUCTURE and ORDERING, not a
byte oracle. Every numeric value this script prints is the frozen Python
engine's own output at full `repr` precision. Where the term-for-term
transcription disagrees with the `DefaultClassTransitionEngine` corroboration
pass, that disagreement is STOPped and classified against the closed list of
intended divergences this plan has already declared: F11's `wage·s²` →
`wage·s` repair, F10's degenerate-arm repair, R10's cumulative baseline — and
nothing else.
"""

from __future__ import annotations

from babylon.domain.economics.dynamics import (
    ClassDistribution,
    DefaultAccumulationCalculator,
    DefaultClassTransitionEngine,
    DefaultDispossessionCalculator,
    DefaultSavingsRateSchedule,
    EconomicConditions,
)
from babylon.domain.economics.dynamics.crisis import PhasedCrisisAmplifier
from babylon.domain.economics.tick.types import CrisisPhase

# ---------------------------------------------------------------------------
# Constants — the 46-constant canonical block (§4.5), mirrored literally.
# ---------------------------------------------------------------------------
WEALTH_THRESHOLD = 142_000.0
PRECARITIZATION_UNEMPLOYMENT_WEIGHT = 0.5
BASE_STABILIZATION = 0.15
MAX_ACCUMULATION_RATE = 0.08

HOURS_PER_YEAR = 2080
V_REPRODUCTION = 12.0
ACCUMULATION_HALT_FLOOR_RATIO = 0.8

PHI_CAP = 0.05
SAVINGS_PROLETARIAT = 0.03

DEFAULT_FORECLOSURE_RATE = 0.006
DEFAULT_BANKRUPTCY_RATE = 0.006
DEFAULT_EVICTION_RATE = 0.063

# Phased amplification table (crisis.py:24-55).
PHASED_PROFILES = {
    CrisisPhase.NORMAL: {
        "dispossession": 1.0,
        "precaritization": 1.0,
        "accumulation": 1.0,
        "stabilization": 1.0,
    },
    CrisisPhase.ONSET: {
        "dispossession": 1.2,
        "precaritization": 1.5,
        "accumulation": 0.8,
        "stabilization": 0.7,
    },
    CrisisPhase.EARLY: {
        "dispossession": 1.8,
        "precaritization": 2.5,
        "accumulation": 0.4,
        "stabilization": 0.4,
    },
    CrisisPhase.DEEP: {
        "dispossession": 3.0,
        "precaritization": 3.5,
        "accumulation": 0.1,
        "stabilization": 0.2,
    },
    CrisisPhase.RECOVERY: {
        "dispossession": 1.3,
        "precaritization": 1.2,
        "accumulation": 0.6,
        "stabilization": 0.5,
    },
}

# World 1 seeds, by county.  Shares sum to 1.0 within each county.
WORLD = {
    "wayne": {
        "fips": "26163",
        "dist_year": 2010,
        "shares": {
            "bourgeoisie": 0.01,
            "petit_bourgeoisie": 0.09,
            "labor_aristocracy": 0.40,
            "proletariat": 0.35,
            "lumpenproletariat": 0.15,
        },
        "median_wage_hourly": 21.0,
        "phi_hour": 0.0,
        "unemployment_rate": 0.05,
        "foreclosure_rate": DEFAULT_FORECLOSURE_RATE,
        "bankruptcy_rate": DEFAULT_BANKRUPTCY_RATE,
        "eviction_rate": DEFAULT_EVICTION_RATE,
        "crisis_phase": CrisisPhase.NORMAL,
    },
    "oakland": {
        "fips": "06001",
        "dist_year": 2010,
        "shares": {
            "bourgeoisie": 0.02,
            "petit_bourgeoisie": 0.08,
            "labor_aristocracy": 0.35,
            "proletariat": 0.40,
            "lumpenproletariat": 0.15,
        },
        "median_wage_hourly": 25.0,
        "phi_hour": 0.0,
        "unemployment_rate": 0.10,
        "foreclosure_rate": DEFAULT_FORECLOSURE_RATE,
        "bankruptcy_rate": DEFAULT_BANKRUPTCY_RATE,
        "eviction_rate": DEFAULT_EVICTION_RATE,
        "crisis_phase": CrisisPhase.NORMAL,
    },
}


# ---------------------------------------------------------------------------
# Term-for-term transcription of the frozen arithmetic.
# ---------------------------------------------------------------------------
def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _halt_floor_wage(median_wage_hourly: float) -> float:
    """FR-017 halt: zero effective wage when hourly wage is below floor."""
    floor = V_REPRODUCTION * ACCUMULATION_HALT_FLOOR_RATIO
    if median_wage_hourly < floor:
        return 0.0
    return median_wage_hourly * HOURS_PER_YEAR


def _phi_adjustment(phi_hour: float, effective_wage_annual: float) -> float:
    """Frozen savings_schedule.py:74-92, with the zero guards."""
    if effective_wage_annual == 0.0 or phi_hour == 0.0:
        return 0.0
    return min(phi_hour * HOURS_PER_YEAR / effective_wage_annual, PHI_CAP)


def _annual_accumulation_frozen(
    effective_wage_annual: float, effective_savings_rate: float
) -> float:
    """The frozen F11 bug: wage · s² (accumulation.py:39-41, :89-90)."""
    consumption = effective_wage_annual * (1.0 - effective_savings_rate)
    return (effective_wage_annual - consumption) * effective_savings_rate


def _annual_accumulation_repaired(
    effective_wage_annual: float, effective_savings_rate: float
) -> float:
    """The F11 repair: wage · s (the intended single application)."""
    return effective_wage_annual * effective_savings_rate


def _accumulation_rate(annual_accumulation: float) -> float:
    """transition_engine.py:200-217."""
    if annual_accumulation <= 0.0:
        return 0.0
    return min(annual_accumulation / WEALTH_THRESHOLD, MAX_ACCUMULATION_RATE)


def _dispossession_rate(county: dict) -> float:
    """dispossession.py:101-111, LA→P composite."""
    f = county["foreclosure_rate"]
    b = county["bankruptcy_rate"]
    e = county["eviction_rate"]
    return 0.6 * f + 0.3 * b + 0.1 * e


def _precaritization_rate(county: dict) -> float:
    """transition_engine.py:219-236."""
    u = county["unemployment_rate"]
    e = county["eviction_rate"]
    rate = u * PRECARITIZATION_UNEMPLOYMENT_WEIGHT + e * (1.0 - PRECARITIZATION_UNEMPLOYMENT_WEIGHT)
    return _clamp(rate, 0.0, 1.0)


def _stabilization_rate(county: dict) -> float:
    """transition_engine.py:238-253."""
    u = county["unemployment_rate"]
    rate = BASE_STABILIZATION * (1.0 - u)
    return _clamp(rate, 0.0, 1.0)


def _amplify(rates: dict, crisis_phase: CrisisPhase) -> dict:
    """Phased amplification (crisis.py:153-178), passthrough for NORMAL."""
    profile = PHASED_PROFILES[crisis_phase]
    return {
        "dispossession": _clamp(rates["dispossession"] * profile["dispossession"], 0.0, 1.0),
        "precaritization": _clamp(rates["precaritization"] * profile["precaritization"], 0.0, 1.0),
        "accumulation": _clamp(rates["accumulation"] * profile["accumulation"], 0.0, 1.0),
        "stabilization": _clamp(rates["stabilization"] * profile["stabilization"], 0.0, 1.0),
    }


def _apply_flows(shares: dict, rates: dict) -> dict:
    """transition_engine.py:255-289."""
    la = shares["labor_aristocracy"]
    prol = shares["proletariat"]
    lumpen = shares["lumpenproletariat"]
    new_la = la - rates["dispossession"] * la + rates["accumulation"] * prol
    new_prol = (
        prol
        + rates["dispossession"] * la
        - rates["accumulation"] * prol
        - rates["precaritization"] * prol
        + rates["stabilization"] * lumpen
    )
    new_lumpen = lumpen + rates["precaritization"] * prol - rates["stabilization"] * lumpen
    return {
        "labor_aristocracy": new_la,
        "proletariat": new_prol,
        "lumpenproletariat": new_lumpen,
    }


def _normalize(raw: dict, fixed_share: float) -> dict:
    """transition_engine.py:291-331."""
    la = max(raw["labor_aristocracy"], 0.0)
    prol = max(raw["proletariat"], 0.0)
    lumpen = max(raw["lumpenproletariat"], 0.0)
    total_dynamic = la + prol + lumpen
    target = 1.0 - fixed_share
    if total_dynamic > 0.0:
        scale = target / total_dynamic
        return {
            "labor_aristocracy": la * scale,
            "proletariat": prol * scale,
            "lumpenproletariat": lumpen * scale,
        }
    # Degenerate branch (F10): equal-thirds reset in frozen engine.
    return {
        "labor_aristocracy": target / 3.0,
        "proletariat": target / 3.0,
        "lumpenproletariat": target / 3.0,
    }


def _compute_county_transcription(county: dict, accumulation_variant: str) -> dict:
    """One full term-for-term transition for a county."""
    fixed = county["shares"]["bourgeoisie"] + county["shares"]["petit_bourgeoisie"]
    effective_wage_annual = _halt_floor_wage(county["median_wage_hourly"])
    phi_adj = _phi_adjustment(county["phi_hour"], effective_wage_annual)
    s = min(SAVINGS_PROLETARIAT + phi_adj, 1.0)

    if accumulation_variant == "frozen":
        annual_acc = _annual_accumulation_frozen(effective_wage_annual, s)
    elif accumulation_variant == "repaired":
        annual_acc = _annual_accumulation_repaired(effective_wage_annual, s)
    else:
        raise ValueError(accumulation_variant)

    acc_rate = _accumulation_rate(annual_acc)
    disp_rate = _dispossession_rate(county)
    prec_rate = _precaritization_rate(county)
    stab_rate = _stabilization_rate(county)

    base_rates = {
        "dispossession": disp_rate,
        "accumulation": acc_rate,
        "precaritization": prec_rate,
        "stabilization": stab_rate,
    }
    amplified = _amplify(base_rates, county["crisis_phase"])
    raw = _apply_flows(county["shares"], amplified)
    normalized = _normalize(raw, fixed)
    return {
        "county": county["fips"],
        "variant": accumulation_variant,
        "wage_hourly": county["median_wage_hourly"],
        "wage_annual": effective_wage_annual,
        "phi_per_hour": county["phi_hour"],
        "phi_adjustment": phi_adj,
        "effective_savings_rate": s,
        "annual_accumulation_dollars": annual_acc,
        "rate_accumulation_per_year": acc_rate,
        "rate_dispossession_per_year": disp_rate,
        "rate_precaritization_per_year": prec_rate,
        "rate_stabilization_per_year": stab_rate,
        "shares_before": county["shares"],
        "shares_after": normalized,
    }


# ---------------------------------------------------------------------------
# Corroboration pass through the frozen DefaultClassTransitionEngine.
# ---------------------------------------------------------------------------
class _DefaultDispossessionDataSource:
    """Returns the scenario-seeded default rates, matching a02's per-node
    field read rather than the hardcoded national source the frozen caller
    optionally substitutes."""

    def get_foreclosure_rate(self, _fips: str, _year: int) -> float:
        return DEFAULT_FORECLOSURE_RATE

    def get_bankruptcy_rate(self, _fips: str, _year: int) -> float:
        return DEFAULT_BANKRUPTCY_RATE

    def get_eviction_rate(self, _fips: str, _year: int) -> float:
        return DEFAULT_EVICTION_RATE


def _run_engine(county: dict, accumulation_variant: str) -> dict:
    """Drive the actual frozen engine over the same inputs."""
    savings = DefaultSavingsRateSchedule(phi_cap=PHI_CAP)
    accumulation = DefaultAccumulationCalculator(savings, wealth_threshold=WEALTH_THRESHOLD)
    # The default calculator uses wage·s² in the frozen code.  To obtain the
    # repaired wage·s result, we monkey-patch its compute method for this
    # corroboration pass only — the engine's own structure is unchanged.
    if accumulation_variant == "repaired":
        original_compute = accumulation.compute

        def repaired_compute(wage, phi_hour, class_position):
            result = original_compute(wage, phi_hour, class_position)
            # Replace the double-application with the single one.
            repaired_annual = wage * result.savings_rate
            return result.model_copy(update={"annual_accumulation": repaired_annual})

        accumulation.compute = repaired_compute

    dispossession = DefaultDispossessionCalculator(_DefaultDispossessionDataSource())
    amplifier = PhasedCrisisAmplifier()  # matches the BSL a05 phased table
    engine = DefaultClassTransitionEngine(
        accumulation,
        dispossession,
        amplifier,
        wealth_threshold=WEALTH_THRESHOLD,
        eviction_weight=PRECARITIZATION_UNEMPLOYMENT_WEIGHT,
        base_stabilization=BASE_STABILIZATION,
    )

    effective_wage = _halt_floor_wage(county["median_wage_hourly"])
    conditions = EconomicConditions(
        fips=county["fips"],
        year=county["dist_year"],
        unemployment_rate=county["unemployment_rate"],
        median_wage=effective_wage,
        melt=60.0,  # dummy; the dynamics engine does not read melt
        phi_hour=county["phi_hour"],
        foreclosure_rate=county["foreclosure_rate"],
        bankruptcy_rate=county["bankruptcy_rate"],
        eviction_rate=county["eviction_rate"],
        crisis=county["crisis_phase"] != CrisisPhase.NORMAL,
    )
    dist = ClassDistribution(
        fips=county["fips"],
        year=county["dist_year"],
        bourgeoisie_share=county["shares"]["bourgeoisie"],
        petit_bourgeoisie_share=county["shares"]["petit_bourgeoisie"],
        labor_aristocracy_share=county["shares"]["labor_aristocracy"],
        proletariat_share=county["shares"]["proletariat"],
        lumpenproletariat_share=county["shares"]["lumpenproletariat"],
    )
    result = engine.simulate_transitions(dist, conditions, crisis_phase=county["crisis_phase"])
    return {
        "county": county["fips"],
        "variant": accumulation_variant,
        "shares_after": {
            "labor_aristocracy": result.labor_aristocracy_share,
            "proletariat": result.proletariat_share,
            "lumpenproletariat": result.lumpenproletariat_share,
        },
    }


def _print_county(label: str, result: dict) -> None:
    print(f"== {label} ({result['variant']}) ==")
    print(f"  county_fips = {result['county']}")
    if "wage_hourly" in result:
        print(f"  wage_hourly = {result['wage_hourly']!r}")
        print(f"  wage_annual = {result['wage_annual']!r}")
        print(f"  phi_per_hour = {result['phi_per_hour']!r}")
        print(f"  phi_adjustment = {result['phi_adjustment']!r}")
        print(f"  effective_savings_rate = {result['effective_savings_rate']!r}")
        print(f"  annual_accumulation_dollars = {result['annual_accumulation_dollars']!r}")
        print(f"  rate_accumulation_per_year = {result['rate_accumulation_per_year']!r}")
        print(f"  rate_dispossession_per_year = {result['rate_dispossession_per_year']!r}")
        print(f"  rate_precaritization_per_year = {result['rate_precaritization_per_year']!r}")
        print(f"  rate_stabilization_per_year = {result['rate_stabilization_per_year']!r}")
    before = result.get("shares_before")
    if before:
        print(f"  la_before = {before['labor_aristocracy']!r}")
        print(f"  prol_before = {before['proletariat']!r}")
        print(f"  lumpen_before = {before['lumpenproletariat']!r}")
    after = result["shares_after"]
    print(f"  la_after = {after['labor_aristocracy']!r}")
    print(f"  prol_after = {after['proletariat']!r}")
    print(f"  lumpen_after = {after['lumpenproletariat']!r}")
    total = (
        result.get("shares_before", {}).get("bourgeoisie", 0.0)
        + result.get("shares_before", {}).get("petit_bourgeoisie", 0.0)
        + after["labor_aristocracy"]
        + after["proletariat"]
        + after["lumpenproletariat"]
    )
    print(f"  total_share_check = {total!r}")


def _assert_agreement(transcription: dict, engine: dict) -> None:
    """STOP-first agreement check; only declared divergences are allowed."""
    for key in ("labor_aristocracy", "proletariat", "lumpenproletariat"):
        t = transcription["shares_after"][key]
        e = engine["shares_after"][key]
        if t != e:
            raise AssertionError(
                f"{transcription['county']} {transcription['variant']} {key}: "
                f"transcription {t!r} != engine {e!r}"
            )


def main() -> None:
    print("class-dynamics-conformance — frozen mirror (world 1)")
    print()
    for name, county in WORLD.items():
        for variant in ("frozen", "repaired"):
            tx = _compute_county_transcription(county, variant)
            eng = _run_engine(county, variant)
            _assert_agreement(tx, eng)
            _print_county(name, tx)
            print()

    # F11 headline: the 33× factor at the proletariat's 0.03 savings rate.
    wayne = WORLD["wayne"]
    effective_wage = _halt_floor_wage(wayne["median_wage_hourly"])
    s = SAVINGS_PROLETARIAT  # phi = 0 here
    frozen_acc = _annual_accumulation_frozen(effective_wage, s)
    repaired_acc = _annual_accumulation_repaired(effective_wage, s)
    print("F11 headline (wayne, phi=0, savings=0.03):")
    print(f"  frozen annual accumulation (wage·s²)   = {frozen_acc!r}")
    print(f"  repaired annual accumulation (wage·s)  = {repaired_acc!r}")
    print(f"  ratio repaired/frozen                  = {repaired_acc / frozen_acc!r}")


if __name__ == "__main__":
    main()
