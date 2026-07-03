"""E4: the fractal check (§9.4 honesty clause).

Two claims, both found CLEANLY EXPRESSIBLE with the Phase E operators (so no
``xfail`` — the ADR records this):

(a) The SAME ``{Core, Periphery} × {Bourgeoisie, Proletariat}`` recursion (C2's
    four-node fixture) is re-expressible at STATE zoom by rebinding the identical
    ``OppositionSpec``s over a state's field slice — the spatial lattice's
    county→state partition supplies the slice. The category STRUCTURE is
    scale-invariant; only the measured data changes.
(b) LUMPENPROLETARIAT appears only on zoom-in: the social lattice's
    community→class fold maps a lumpen-dominated community onto the proletarian
    pole, so at CLASS level lumpen is folded into the proletariat, while at
    COMMUNITY/INDIVIDUAL zoom the distinct lumpen pole is visible.
"""

from __future__ import annotations

import pytest

from babylon.dialectics.core.composition import sum_
from babylon.dialectics.core.opposition import (
    BoundOpposition,
    GapReading,
    OppositionRegistry,
    OppositionSpec,
    PoleBinding,
)
from babylon.dialectics.instances.levels import (
    social_lattice_from_memberships,
    spatial_lattice_for_counties,
)
from babylon.formulas.contradiction import (
    calculate_wealth_asymmetry_balance,
    calculate_wealth_asymmetry_gap,
)

pytestmark = pytest.mark.math


# ── (a) scale-invariant fractal recursion ──────────────────────────────


def _zone(key: str, pair: tuple[float, float]) -> BoundOpposition[object]:
    """A capital_labor zone whose measure reads a fixed (proletariat, bourgeoisie) pair."""

    def measure(_inputs: object) -> GapReading:
        return GapReading(
            gap=calculate_wealth_asymmetry_gap(*pair),
            balance=calculate_wealth_asymmetry_balance(*pair),
        )

    return BoundOpposition(
        spec=OppositionSpec(key=key, pole_a=f"{key}-P", pole_b=f"{key}-B", antagonistic=True),
        measure=measure,
    )


def _fractal(
    core_pair: tuple[float, float], periphery_pair: tuple[float, float]
) -> OppositionRegistry[object]:
    """The four-node recursion, rebindable over any (core, periphery) slice."""
    core = _zone("core_capital_labor", core_pair)
    periphery = _zone("periphery_capital_labor", periphery_pair)
    outer_spec = OppositionSpec(
        key="imperial_nested",
        pole_a="Core",
        pole_b="Periphery",
        binding_a=PoleBinding(label="Core", opposition_key="core_capital_labor"),
        binding_b=PoleBinding(label="Periphery", opposition_key="periphery_capital_labor"),
        level_name="bloc",
        antagonistic=True,
    )
    outer = sum_(outer_spec, core, periphery)
    return OppositionRegistry(bindings=[core, periphery, outer])


def _imperial_gap(reg: OppositionRegistry[object]) -> float:
    states = {s.key: s for s in reg.step(None, tick=0)}
    return states["imperial_nested"].gap


class TestFractalScaleInvariance:
    """(a) The same recursion is expressible at nation and at state zoom."""

    def test_structure_is_identical_across_zoom(self) -> None:
        nation = _fractal((10.0, 30.0), (5.0, 45.0))
        state = _fractal((10.0, 20.0), (8.0, 40.0))
        assert nation.keys == state.keys
        for key in ("core_capital_labor", "periphery_capital_labor", "imperial_nested"):
            assert nation.spec_for(key).antagonistic == state.spec_for(key).antagonistic
        outer = state.spec_for("imperial_nested")
        assert outer.composition == "sum"
        assert outer.component_keys == ("core_capital_labor", "periphery_capital_labor")

    def test_state_slice_from_the_lattice_rebinds_the_same_specs(self) -> None:
        # A county field; the spatial lattice's county->state partition IS the
        # slice. State 26's core counties {26001,26002}, periphery {26003,26004}.
        field = {"26001": 10.0, "26002": 10.0, "26003": 40.0, "26004": 40.0}
        lattice = spatial_lattice_for_counties(sorted(field))
        assert [lvl.name for lvl in lattice.levels] == ["county", "state", "nation"]
        core_counties = ("26001", "26002")
        periphery_counties = ("26003", "26004")
        core_mean = sum(field[c] for c in core_counties) / len(core_counties)
        periphery_mean = sum(field[c] for c in periphery_counties) / len(periphery_counties)

        # Rebind the SAME fractal specs over the state slice (proletariat vs the
        # zone mean standing in for the bourgeois pole).
        state_reg = _fractal((core_mean, 30.0), (periphery_mean, 30.0))
        nation_reg = _fractal((10.0, 30.0), (5.0, 45.0))
        assert state_reg.keys == nation_reg.keys
        # Different slices -> different computed imperial gap (rebound, not shared).
        assert _imperial_gap(state_reg) != pytest.approx(_imperial_gap(nation_reg))


# ── (b) lumpen appears only on zoom-in ─────────────────────────────────


class TestLumpenFold:
    """(b) LUMPENPROLETARIAT folds into the proletariat pole at class level."""

    def _lattice(self) -> object:
        # cProl and cLumpen BOTH fold onto the proletarian class pole; cBourg is
        # bourgeois. The fold is the community->class map (dominant SocialRole).
        return social_lattice_from_memberships(
            {"aP": "cProl", "aL": "cLumpen", "aB": "cBourg"},
            {"cProl": "proletarian", "cLumpen": "proletarian", "cBourg": "bourgeois"},
            {"proletarian": "periphery", "bourgeois": "core"},
        )

    def test_lumpen_distinct_at_community_folded_at_class(self) -> None:
        lattice = self._lattice()
        # A field where the lumpen agent differs from the proletarian agent.
        field = {"aP": 1.0, "aL": 5.0, "aB": 9.0}
        # At the COMMUNITY level each agent is its own community -> the lumpen
        # value is preserved distinct from the proletarian: NOT resolved at
        # individual (community smoothing changes nothing here, they are singletons
        # — so the live distinction is exposed one rung up, class).
        # At the CLASS level cProl+cLumpen fold into "proletarian": the class
        # smoothing BLENDS aP and aL, so the field is NOT resolved at community
        # (the lumpen/prole distinction still lives below class).
        assert not lattice.is_resolved_at(field, lower=1, higher=2)  # not resolved at community

    def test_lumpen_indistinct_once_it_equals_the_proletarian(self) -> None:
        lattice = self._lattice()
        # When the lumpen agent already matches the proletarian, the class fold
        # changes nothing: the community-level field IS resolved at class.
        field = {"aP": 3.0, "aL": 3.0, "aB": 9.0}
        assert lattice.is_resolved_at(field, lower=1, higher=2)  # resolved at community
