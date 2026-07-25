"""Unit tests for the production opposition catalog (Phase C).

Pins the honest measure each of the fourteen oppositions is bound to, the
empty-input degeneracies, the tenancy rent-free guard, and the
atomization pole mapping — the contract the engine's ContradictionSystem
relies on when it fills :class:`GraphInputs` each tick.
"""

from __future__ import annotations

import pytest

from babylon.domain.dialectics.instances.catalog import GraphInputs, build_default_registry
from babylon.topology.graph import BabylonUGraph

pytestmark = [pytest.mark.unit, pytest.mark.math]


def _reg():  # type: ignore[no-untyped-def]
    return build_default_registry()


def _states(inputs: GraphInputs, tick: int = 0):  # type: ignore[no-untyped-def]
    return {s.key: s for s in _reg().step(inputs, tick=tick)}


class TestRegistryShape:
    def test_eighteen_oppositions_bound(self) -> None:
        assert _reg().keys == (
            "absolute_relative_surplus",
            "atomization",
            "capital_labor",
            "circulation",
            "credit",
            "debt_spiral",
            "disproportionality",
            "financial",
            "imperial",
            "labor_laborpower",
            "national",
            "price_value",
            "realization",
            "reproduction",
            "surplus_distribution",
            "tenancy",
            "value_usevalue",
            "wage",
        )

    def test_shadow_bindings(self) -> None:
        """task #42-C's ``national``, Vol I U6's three production-layer
        bindings and Vol II U5's four circulation-layer bindings all land
        shadow-first, on the same discipline price_value was born under
        (ADR077) before its ADR078 promotion."""
        assert _reg().shadow_keys == frozenset(
            {
                "national",
                "value_usevalue",
                "labor_laborpower",
                "absolute_relative_surplus",
                "circulation",
                "realization",
                "reproduction",
                "disproportionality",
            }
        )

    def test_capital_labor_is_antagonistic(self) -> None:
        assert _reg().spec_for("capital_labor").antagonistic is True

    def test_rate_weight_passthrough(self) -> None:
        reg = build_default_registry(rate_weight=3.0)
        assert reg._rate_weight == 3.0  # noqa: SLF001 - white-box knob check


class TestCapitalLabor:
    def test_mean_exploitation_gap(self) -> None:
        # Single EXPLOITATION edge, labor=10, capital=30 → gap 0.5, capital dominant.
        states = _states(GraphInputs(exploitation_pairs=((10.0, 30.0),)))
        assert states["capital_labor"].gap == pytest.approx(0.5)
        assert states["capital_labor"].balance == pytest.approx(0.5)  # >0 == capital (B)
        assert states["capital_labor"].leading_pole == "b"

    def test_labor_dominant_flips_leading_pole(self) -> None:
        # Worker overtakes capital (the empirical bridged crossover ~tick 8).
        states = _states(GraphInputs(exploitation_pairs=((30.0, 10.0),)))
        assert states["capital_labor"].balance == pytest.approx(-0.5)
        assert states["capital_labor"].leading_pole == "a"

    def test_mean_over_multiple_edges(self) -> None:
        states = _states(GraphInputs(exploitation_pairs=((0.0, 10.0), (10.0, 10.0))))
        # Wealth-weighted (owner ruling 2026-07-19): pair (0,10) has pole-sum
        # 10, |b-a| 10; pair (10,10) has pole-sum 20, |b-a| 0. gap = Σ|b-a| /
        # Σ(a+b) = (10+0) / (10+20) = 10/30 = 1/3.
        assert states["capital_labor"].gap == pytest.approx(1.0 / 3.0)

    def test_mean_asymmetry_is_wealth_weighted_not_pair_counted(self) -> None:
        """One enormous near-parity pair dominates one tiny fully-polarized pair.

        Pairs (4950, 4950) at parity (pole-sum 9900, gap_mass 0) and
        (0.0, 100.0) fully polarized (pole-sum 100, gap_mass 100): an
        unweighted mean reads gap ``(0 + 1.0) / 2 = 0.5``; the
        wealth-weighted field reads ``Σ|b−a| / Σ(a+b) = 100 / 10_000 =
        0.01``. The tiny pair must NOT swing the reading as hard as the
        enormous one (intensive-aggregation class, owner ruling 2026-07-19).

        Magnitudes are chosen so the exact weighted result (0.01) lands on
        the ``Intensity`` field's pre-existing 1e-6 precision grid
        (``babylon.kernel.math.quantize``, Epoch 0 gatekeeper) with no
        rounding remainder — the original 1e6-vs-1 demonstration produces a
        true gap of ~5e-7, which the SAME gatekeeper legitimately floors to
        0.0 (unrelated to this fix), so it is not usable as an exact
        ``pytest.approx`` pin.
        """
        inputs = GraphInputs(
            exploitation_pairs=((4950.0, 4950.0), (0.0, 100.0)),
        )
        reading = _states(inputs)["capital_labor"]
        assert reading.gap == pytest.approx(0.01)
        assert reading.balance == pytest.approx(0.01)

    def test_mean_asymmetry_all_pairs_degenerate_is_zero(self) -> None:
        # A pole-sum below the epsilon guard carries no wealth mass to weight
        # by, so it is skipped; an all-degenerate input reads absent (0, 0).
        states = _states(GraphInputs(exploitation_pairs=((0.0, 0.0),)))
        assert states["capital_labor"].gap == 0.0
        assert states["capital_labor"].balance == 0.0


class TestWage:
    def test_wage_is_the_value_wage_counit_defect(self) -> None:
        # (w_paid=18, v_produced=2): the wage vastly exceeds value produced —
        # a large positive Φ (the imperial bribe). Reordered to (value=A, wage=B).
        states = _states(GraphInputs(wage_value_pairs=((18.0, 2.0),)))
        assert states["wage"].gap == pytest.approx(0.8)  # |18-2|/(18+2)
        assert states["wage"].balance == pytest.approx(0.8)  # wage exceeds value = bribe
        assert states["wage"].leading_pole == "b"  # price-of-labor-power dominant

    def test_wage_negative_when_value_exceeds_wage(self) -> None:
        # (w_paid=2, v_produced=18): super-exploited — wage below value produced.
        states = _states(GraphInputs(wage_value_pairs=((2.0, 18.0),)))
        assert states["wage"].balance == pytest.approx(-0.8)
        assert states["wage"].leading_pole == "a"  # value-produced dominant

    def test_wage_empty_pairs_is_zero_no_endpoint_fallback(self) -> None:
        # No (w, v) data → (0, 0); the old WAGES-endpoint proxy is removed.
        states = _states(GraphInputs())
        assert states["wage"].gap == 0.0
        assert states["wage"].balance == 0.0


class TestTenancy:
    def test_rent_free_edge_is_degenerate_zero(self) -> None:
        """A territory with rent_level ~ 0 must NOT saturate to 1.0."""
        states = _states(GraphInputs(tenancy_pairs=((5.0, 0.0),)))
        assert states["tenancy"].gap == 0.0
        assert states["tenancy"].balance == 0.0

    def test_rent_burden_measured_when_present(self) -> None:
        states = _states(GraphInputs(tenancy_pairs=((10.0, 30.0),)))
        assert states["tenancy"].gap == pytest.approx(0.5)
        assert states["tenancy"].balance == pytest.approx(0.5)  # rent (B) dominant


class TestAtomization:
    def test_fully_atomized_solidarity_graph(self) -> None:
        g = BabylonUGraph()
        g.add_nodes_from(["C001", "C002", "C003"])  # no SOLIDARITY edges
        states = _states(GraphInputs(solidarity_subgraph=g))
        assert states["atomization"].gap == pytest.approx(1.0)
        assert states["atomization"].balance == pytest.approx(-1.0)  # atomized pole

    def test_fully_unified_solidarity_graph(self) -> None:
        g = BabylonUGraph()
        g.add_edges_from([("C001", "C002"), ("C002", "C003"), ("C001", "C003")])
        states = _states(GraphInputs(solidarity_subgraph=g))
        assert states["atomization"].gap == pytest.approx(0.0)
        assert states["atomization"].balance == pytest.approx(1.0)  # unified pole

    def test_empty_subgraph_is_zero(self) -> None:
        states = _states(GraphInputs(solidarity_subgraph=BabylonUGraph()))
        assert states["atomization"].gap == 0.0
        assert states["atomization"].balance == 0.0


class TestImperial:
    def test_imperial_reads_the_wage_value_defect(self) -> None:
        # Rebound in D5: imperial reads the same (w_paid, v_produced) defect.
        states = _states(GraphInputs(wage_value_pairs=((18.0, 2.0),)))
        assert states["imperial"].gap == pytest.approx(0.8)
        assert states["imperial"].balance == pytest.approx(0.8)  # imperial-rent inflow

    def test_imperial_and_wage_share_the_same_defect(self) -> None:
        # Same inputs, same arithmetic — different poles/level only.
        inputs = GraphInputs(wage_value_pairs=((18.0, 2.0), (10.0, 8.0)))
        states = _states(inputs)
        assert states["imperial"].gap == pytest.approx(states["wage"].gap)
        assert states["imperial"].balance == pytest.approx(states["wage"].balance)

    def test_imperial_empty_is_zero(self) -> None:
        states = _states(GraphInputs())
        assert states["imperial"].gap == 0.0
        assert states["imperial"].balance == 0.0


class TestEmptyInputs:
    def test_all_gaps_zero_on_empty_inputs(self) -> None:
        states = _states(GraphInputs())
        assert all(s.gap == 0.0 for s in states.values())

    def test_step_is_pure(self) -> None:
        inputs = GraphInputs(exploitation_pairs=((1.0, 4.0),), wage_value_pairs=((3.0, 2.0),))
        reg = _reg()
        assert reg.step(inputs, tick=7) == reg.step(inputs, tick=7)


class TestLevelPlacement:
    """E1: each opposition is placed on a level-lattice rung (level_name)."""

    def test_level_names_match_the_catalog(self) -> None:
        reg = _reg()
        placement = {key: reg.spec_for(key).level_name for key in reg.keys}
        assert placement == {
            "capital_labor": "county",
            "wage": "county",
            "tenancy": "county",
            "atomization": "class",
            "imperial": "bloc",
            # Program 23: the national scissors sits on no county/bloc rung
            # yet — unplaced by design (empty = unplaced, opposition.py).
            "price_value": "",
            # Vol III (U5.2): the two county-keyed money axes and the two
            # national (unplaced) ones.
            "surplus_distribution": "county",
            "debt_spiral": "county",
            "credit": "",
            "financial": "",
            # task #42-C: the national axis aggregates faction stance
            # NATIONALLY (INFLUENCES reach, no county/class rung) — unplaced,
            # same as credit/financial.
            "national": "",
            # Vol I U6: value_usevalue and absolute_relative_surplus both
            # aggregate NATIONALLY (unplaced, same as credit/financial/
            # national); labor_laborpower shares wage's per-class/per-county
            # granularity, so it takes wage's own level.
            "value_usevalue": "",
            "labor_laborpower": "county",
            "absolute_relative_surplus": "",
            # Vol II circulation program (U5): all four circulation-layer
            # bindings are county-level material processes (CircuitState /
            # CirculationCrisisAssessment / DisproportionalityCrisis all
            # keyed per-county), aggregated nationally for the reading —
            # same placement convention as surplus_distribution/debt_spiral.
            "circulation": "county",
            "realization": "county",
            "reproduction": "county",
            "disproportionality": "county",
        }


class TestPriceValue:
    """The scissors binding (Program 23, ADR077): value (A) ⇄ price (B)."""

    def test_absent_market_axis_is_zero(self) -> None:
        state = _states(GraphInputs())["price_value"]
        assert state.gap == 0.0
        assert state.balance == 0.0

    def test_balance_passes_through_pre_derived_reading(self) -> None:
        state = _states(GraphInputs(market_balance=0.6))["price_value"]
        assert state.gap == pytest.approx(0.6)
        assert state.balance == pytest.approx(0.6)
        assert state.leading_pole == "b"  # price above value: the form pole leads

    def test_negative_balance_is_value_pole(self) -> None:
        state = _states(GraphInputs(market_balance=-0.3))["price_value"]
        assert state.gap == pytest.approx(0.3)
        assert state.balance == pytest.approx(-0.3)
        assert state.leading_pole == "a"

    def test_out_of_range_reading_is_clamped(self) -> None:
        state = _states(GraphInputs(market_balance=1.7))["price_value"]
        assert state.balance == 1.0

    def test_dominant_scissors_takes_the_principal_slot(self) -> None:
        """ADR078 promotion: with every other gap at zero, a fully-opened
        scissors IS the principal contradiction — crisis-as-principal."""
        states = _states(GraphInputs(market_balance=1.0))
        assert states["price_value"].is_principal is True

    def test_pole_measure_reads_the_labor_power_commodity(self) -> None:
        """Per-node price⟷value position via the ONE commodity carrying both
        a per-node price (w_paid) and value (v_produced): labor-power — the
        D5 shared-defect precedent (``_imperial_poles``), ADR078."""
        inputs = GraphInputs(
            wage_value_id_pairs=(
                ("bribed", 1.2, 1.0),  # wage above value: the price form leads
                ("exploited", 0.8, 1.0),  # value above wage: the substance leads
            )
        )
        readings = {
            r.entity_id: r for r in _reg().read_poles(inputs) if r.opposition_key == "price_value"
        }
        assert readings["bribed"].sigma > 0.0  # pole B (price)
        assert readings["exploited"].sigma < 0.0  # pole A (value)

    def test_unpositioned_nodes_are_absent_from_the_pole_channel(self) -> None:
        readings = [
            r for r in _reg().read_poles(GraphInputs()) if r.opposition_key == "price_value"
        ]
        assert readings == []


class TestNational:
    """The national axis (task #42-C): national-chauvinism (A) ⇄ internationalism (B).

    Shadow-first, on the same discipline ``price_value`` was born under
    (ADR077): measured every tick, never principal, absent input reads zero.
    """

    def test_absent_national_axis_is_zero(self) -> None:
        state = _states(GraphInputs())["national"]
        assert state.gap == 0.0
        assert state.balance == 0.0

    def test_balance_passes_through_pre_derived_reading(self) -> None:
        state = _states(GraphInputs(national_balance=0.6))["national"]
        assert state.gap == pytest.approx(0.6)
        assert state.balance == pytest.approx(0.6)
        assert state.leading_pole == "b"  # internationalism dominant

    def test_negative_balance_is_chauvinism_pole(self) -> None:
        state = _states(GraphInputs(national_balance=-0.3))["national"]
        assert state.gap == pytest.approx(0.3)
        assert state.balance == pytest.approx(-0.3)
        assert state.leading_pole == "a"  # national-chauvinism dominant

    def test_out_of_range_reading_is_clamped(self) -> None:
        state = _states(GraphInputs(national_balance=1.7))["national"]
        assert state.balance == 1.0

    def test_never_principal_even_at_full_gap(self) -> None:
        """Shadow bindings never lead (ADR077) — promotion is a later, separate decision."""
        states = _states(GraphInputs(national_balance=1.0))
        assert states["national"].is_principal is False

    def test_national_is_antagonistic(self) -> None:
        # A genuine class-rupturing contradiction (the fascist bifurcation
        # theory this engine models), same flag as capital_labor/imperial.
        assert _reg().spec_for("national").antagonistic is True


class TestValueUseValue:
    """Ch. 1's commodity dialectic (Vol I U6): use-value (A) vs value (B).

    Shares ``_ratio_reading`` with the Vol III money family: natural zero
    point at exact parity (wealth == subsistence).
    """

    def test_absent_ratio_is_zero(self) -> None:
        state = _states(GraphInputs())["value_usevalue"]
        assert state.gap == 0.0
        assert state.balance == 0.0

    def test_unity_point_is_the_balance_zero_crossing(self) -> None:
        state = _states(GraphInputs(wealth_subsistence_ratio=1.0))["value_usevalue"]
        assert state.balance == pytest.approx(0.0)
        assert state.gap == pytest.approx(0.5)

    def test_wealth_exceeding_subsistence_is_the_value_pole(self) -> None:
        state = _states(GraphInputs(wealth_subsistence_ratio=3.0))["value_usevalue"]
        assert state.balance == pytest.approx(0.5)  # (3-1)/(3+1)
        assert state.leading_pole == "b"

    def test_wealth_below_subsistence_is_the_use_value_pole(self) -> None:
        # ratio 0.5: wealth is half of subsistence — real deprivation.
        state = _states(GraphInputs(wealth_subsistence_ratio=0.5))["value_usevalue"]
        assert state.balance == pytest.approx(-1.0 / 3.0)
        assert state.leading_pole == "a"

    def test_is_shadow_and_never_antagonistic(self) -> None:
        reg = _reg()
        assert "value_usevalue" in reg.shadow_keys
        assert reg.spec_for("value_usevalue").antagonistic is False

    def test_poles_are_named_as_specified(self) -> None:
        spec = _reg().spec_for("value_usevalue")
        assert spec.pole_a == "use-value"
        assert spec.pole_b == "value"


class TestLaborLaborPower:
    """Ch. 6's wage-form mystification (Vol I U6): labor (A) vs labor-power (B).

    Reads the IDENTICAL ``(w_paid, v_produced)`` defect as ``wage``/``imperial``
    (the "shared defect, different poles" design note) — a third framing of
    the same arithmetic.
    """

    def test_reads_the_same_wage_value_defect(self) -> None:
        inputs = GraphInputs(wage_value_pairs=((18.0, 2.0),))
        states = _states(inputs)
        assert states["labor_laborpower"].gap == pytest.approx(states["wage"].gap)
        assert states["labor_laborpower"].balance == pytest.approx(states["wage"].balance)

    def test_labor_exceeding_labor_power_price_is_the_labor_pole(self) -> None:
        # (w_paid=2, v_produced=18): labor's product vastly exceeds what was
        # paid for the labor-power that performed it — "the secret of
        # profit-making". Reordered to (value=A="labor", wage=B="labor-power").
        state = _states(GraphInputs(wage_value_pairs=((2.0, 18.0),)))["labor_laborpower"]
        assert state.balance == pytest.approx(-0.8)
        assert state.leading_pole == "a"

    def test_empty_pairs_is_zero(self) -> None:
        state = _states(GraphInputs())["labor_laborpower"]
        assert state.gap == 0.0
        assert state.balance == 0.0

    def test_is_shadow_and_placed_at_county_level(self) -> None:
        reg = _reg()
        assert "labor_laborpower" in reg.shadow_keys
        assert reg.spec_for("labor_laborpower").level_name == "county"
        assert reg.spec_for("labor_laborpower").antagonistic is False

    def test_poles_are_named_as_specified(self) -> None:
        spec = _reg().spec_for("labor_laborpower")
        assert spec.pole_a == "labor"
        assert spec.pole_b == "labor-power"


class TestAbsoluteRelativeSurplus:
    """Chs. 10, 12, 15's two surplus-value strategies (Vol I U6):
    absolute-surplus-value (A) vs relative-surplus-value (B).

    Shares ``_ratio_reading`` with the Vol III money family: natural zero
    point at exact parity (intensity/hours reference ratios both at 1.0).
    """

    def test_absent_ratio_is_zero(self) -> None:
        state = _states(GraphInputs())["absolute_relative_surplus"]
        assert state.gap == 0.0
        assert state.balance == 0.0

    def test_unity_point_is_the_balance_zero_crossing(self) -> None:
        state = _states(GraphInputs(surplus_strategy_ratio=1.0))["absolute_relative_surplus"]
        assert state.balance == pytest.approx(0.0)

    def test_relative_dominant_ratio_is_the_relative_pole(self) -> None:
        state = _states(GraphInputs(surplus_strategy_ratio=3.0))["absolute_relative_surplus"]
        assert state.balance == pytest.approx(0.5)
        assert state.leading_pole == "b"

    def test_absolute_dominant_ratio_is_the_absolute_pole(self) -> None:
        state = _states(GraphInputs(surplus_strategy_ratio=0.5))["absolute_relative_surplus"]
        assert state.balance == pytest.approx(-1.0 / 3.0)
        assert state.leading_pole == "a"

    def test_is_shadow_and_never_antagonistic(self) -> None:
        reg = _reg()
        assert "absolute_relative_surplus" in reg.shadow_keys
        assert reg.spec_for("absolute_relative_surplus").antagonistic is False

    def test_poles_are_named_as_specified(self) -> None:
        spec = _reg().spec_for("absolute_relative_surplus")
        assert spec.pole_a == "absolute-surplus-value"
        assert spec.pole_b == "relative-surplus-value"


class TestVolumeThreeInputFields:
    """The four Vol III money fields are optional and absent by default.

    Absence is the normal steady state for ~85% of a campaign (the FRED
    series terminate at 2024), so ``None`` must be the DEFAULT, never a
    fabricated 0.0 (Constitution III.11).
    """

    def test_all_four_default_to_none(self) -> None:
        inputs = GraphInputs()
        assert inputs.rentier_share is None
        assert inputs.debt_ratio is None
        assert inputs.credit_fragility is None
        assert inputs.financialization_index is None

    def test_all_four_are_settable_floats(self) -> None:
        inputs = GraphInputs(
            rentier_share=0.4,
            debt_ratio=1.5,
            credit_fragility=2.0,
            financialization_index=3.5,
        )
        assert inputs.rentier_share == pytest.approx(0.4)
        assert inputs.debt_ratio == pytest.approx(1.5)
        assert inputs.credit_fragility == pytest.approx(2.0)
        assert inputs.financialization_index == pytest.approx(3.5)

    def test_graph_inputs_stays_frozen(self) -> None:
        inputs = GraphInputs(rentier_share=0.4)
        with pytest.raises(AttributeError):
            inputs.rentier_share = 0.9  # type: ignore[misc]


class TestVolumeThreeOppositions:
    """The four Vol III bindings: shared ratio family, honest absence.

    Every one reads a NON-NEGATIVE ratio against its own material unity
    point (claims == substance) and maps it with the same zero-parameter
    saturating family: ``gap = x/(1+x)``, ``balance = (x-1)/(x+1)``. So the
    balance crosses zero exactly where the claim equals the substance it
    claims, and the gap is 0 only when the claim is absent altogether.
    """

    @pytest.mark.parametrize(
        "key",
        ["surplus_distribution", "debt_spiral", "credit", "financial"],
    )
    def test_absent_input_reads_zero_zero(self, key: str) -> None:
        # No Vol III data (the ~85%-of-campaign steady state): no claim,
        # no contradiction — never a fabricated value.
        states = _states(GraphInputs())
        assert states[key].gap == pytest.approx(0.0)
        assert states[key].balance == pytest.approx(0.0)

    @pytest.mark.parametrize(
        "key",
        ["surplus_distribution", "debt_spiral", "credit", "financial"],
    )
    def test_none_of_them_is_antagonistic(self, key: str) -> None:
        # The catalog reserves antagonistic=True for capital_labor and
        # imperial alone: the division of surplus AMONG capitals is real
        # conflict but intra-class, and mislabelling it would corrupt
        # principal-contradiction ranking.
        assert _reg().spec_for(key).antagonistic is False

    def test_levels_are_county_for_the_two_county_axes(self) -> None:
        assert _reg().spec_for("surplus_distribution").level_name == "county"
        assert _reg().spec_for("debt_spiral").level_name == "county"

    def test_the_two_national_axes_are_unplaced(self) -> None:
        assert _reg().spec_for("credit").level_name == ""
        assert _reg().spec_for("financial").level_name == ""

    def test_poles_are_named_as_specified(self) -> None:
        reg = _reg()
        assert (reg.spec_for("surplus_distribution").pole_a) == "enterprise"
        assert (reg.spec_for("surplus_distribution").pole_b) == "rentier"
        assert (reg.spec_for("debt_spiral").pole_a) == "solvent"
        assert (reg.spec_for("debt_spiral").pole_b) == "indebted"
        assert (reg.spec_for("credit").pole_a) == "accommodation"
        assert (reg.spec_for("credit").pole_b) == "fragility"
        assert (reg.spec_for("financial").pole_a) == "real"
        assert (reg.spec_for("financial").pole_b) == "fictitious"

    def test_zero_claim_is_no_contradiction_not_maximal(self) -> None:
        # Rentiers claim nothing: the functioning capitalist retains the
        # whole surplus. That is the ABSENCE of the conflict, not its peak.
        states = _states(GraphInputs(rentier_share=0.0, debt_ratio=0.0))
        assert states["surplus_distribution"].gap == pytest.approx(0.0)
        assert states["surplus_distribution"].balance == pytest.approx(-1.0)
        assert states["surplus_distribution"].leading_pole == "a"
        assert states["debt_spiral"].gap == pytest.approx(0.0)
        assert states["debt_spiral"].balance == pytest.approx(-1.0)

    def test_unity_point_is_the_balance_zero_crossing(self) -> None:
        # x == 1: claims exactly equal the surplus they claim (p == 0);
        # fragility exactly at its crisis reference; fictitious exactly at
        # parity with real. Neither pole leads.
        states = _states(
            GraphInputs(
                rentier_share=1.0,
                debt_ratio=1.0,
                credit_fragility=1.0,
                financialization_index=1.0,
            )
        )
        for key in ("surplus_distribution", "debt_spiral", "credit", "financial"):
            assert states[key].balance == pytest.approx(0.0)
            assert states[key].gap == pytest.approx(0.5)

    def test_claims_exceeding_surplus_puts_the_rentier_pole_in_the_lead(self) -> None:
        # (i + r + t) = 3s: interest, rent and taxes consume three times the
        # surplus produced. Enterprise profit is deeply negative.
        states = _states(GraphInputs(rentier_share=3.0))
        assert states["surplus_distribution"].gap == pytest.approx(0.75)
        assert states["surplus_distribution"].balance == pytest.approx(0.5)
        assert states["surplus_distribution"].leading_pole == "b"

    def test_financialization_bubble_reads_fictitious_dominant(self) -> None:
        # 3.5 is the FRED TCMDO/GDP overaccumulation reading (~2008 peak).
        states = _states(GraphInputs(financialization_index=3.5))
        assert states["financial"].balance == pytest.approx(2.5 / 4.5)
        assert states["financial"].leading_pole == "b"

    def test_negative_ratios_are_rejected_as_absent(self) -> None:
        # A ratio of a non-negative claim to a non-negative substance can
        # never be negative; a negative reading is corrupt input, and the
        # honest response is the absent reading, not a clamped fiction.
        states = _states(GraphInputs(debt_ratio=-2.0))
        assert states["debt_spiral"].gap == pytest.approx(0.0)
        assert states["debt_spiral"].balance == pytest.approx(0.0)


class TestVolumeTwoInputFields:
    """The four Vol II circulation fields are optional and absent by default.

    Absence is the normal steady state until Vol II data hydration (task
    #46) lands, so ``None`` must be the DEFAULT, never a fabricated 0.0
    (Constitution III.11).
    """

    def test_all_four_default_to_none(self) -> None:
        inputs = GraphInputs()
        assert inputs.commodity_overhang_share is None
        assert inputs.realization_crisis_share is None
        assert inputs.reproduction_crisis_share is None
        assert inputs.disproportionality_imbalance is None

    def test_all_four_are_settable_floats(self) -> None:
        inputs = GraphInputs(
            commodity_overhang_share=0.4,
            realization_crisis_share=0.2,
            reproduction_crisis_share=0.1,
            disproportionality_imbalance=-0.3,
        )
        assert inputs.commodity_overhang_share == pytest.approx(0.4)
        assert inputs.realization_crisis_share == pytest.approx(0.2)
        assert inputs.reproduction_crisis_share == pytest.approx(0.1)
        assert inputs.disproportionality_imbalance == pytest.approx(-0.3)

    def test_graph_inputs_stays_frozen(self) -> None:
        inputs = GraphInputs(commodity_overhang_share=0.4)
        with pytest.raises(AttributeError):
            inputs.commodity_overhang_share = 0.9  # type: ignore[misc]


class TestVolumeTwoOppositions:
    """The four Vol II circulation bindings (U5 Oppositions): SHADOW-first,
    on the same discipline ``national``/``price_value`` were born under
    (ADR077) — measured every tick, never principal, absent input reads
    zero. ``circulation``/``realization``/``reproduction`` share the
    ``2x-1`` bounded-share family (their inputs are already extensive
    shares in ``[0, 1]``); ``disproportionality`` reads its already-signed
    ``[-1, 1]`` input directly.
    """

    @pytest.mark.parametrize(
        "key",
        ["circulation", "realization", "reproduction", "disproportionality"],
    )
    def test_absent_input_reads_zero_zero(self, key: str) -> None:
        states = _states(GraphInputs())
        assert states[key].gap == pytest.approx(0.0)
        assert states[key].balance == pytest.approx(0.0)

    @pytest.mark.parametrize(
        "key",
        ["circulation", "realization", "reproduction", "disproportionality"],
    )
    def test_none_of_them_is_antagonistic(self, key: str) -> None:
        assert _reg().spec_for(key).antagonistic is False

    @pytest.mark.parametrize(
        "key",
        ["circulation", "realization", "reproduction", "disproportionality"],
    )
    def test_all_four_are_shadow_and_never_principal(self, key: str) -> None:
        assert _reg().shadow_keys >= {key}

    def test_all_four_are_county_level(self) -> None:
        for key in ("circulation", "realization", "reproduction", "disproportionality"):
            assert _reg().spec_for(key).level_name == "county"

    def test_poles_are_named_as_specified(self) -> None:
        reg = _reg()
        assert reg.spec_for("circulation").pole_a == "money-capital"
        assert reg.spec_for("circulation").pole_b == "commodity-capital"
        assert reg.spec_for("realization").pole_a == "realized"
        assert reg.spec_for("realization").pole_b == "unrealized"
        assert reg.spec_for("reproduction").pole_a == "balanced"
        assert reg.spec_for("reproduction").pole_b == "unbalanced"
        assert reg.spec_for("disproportionality").pole_a == "means-of-production"
        assert reg.spec_for("disproportionality").pole_b == "means-of-consumption"

    def test_zero_share_is_pole_a_dominant_not_neutral(self) -> None:
        # A share of 0.0 (no overhang / no crisis anywhere / fully balanced)
        # is the pole-A extreme, not the midpoint: balance = 2*0 - 1 = -1.
        states = _states(
            GraphInputs(
                commodity_overhang_share=0.0,
                realization_crisis_share=0.0,
                reproduction_crisis_share=0.0,
            )
        )
        for key in ("circulation", "realization", "reproduction"):
            assert states[key].balance == pytest.approx(-1.0)
            assert states[key].gap == pytest.approx(1.0)
            assert states[key].leading_pole == "a"

    def test_full_share_is_pole_b_dominant(self) -> None:
        states = _states(
            GraphInputs(
                commodity_overhang_share=1.0,
                realization_crisis_share=1.0,
                reproduction_crisis_share=1.0,
            )
        )
        for key in ("circulation", "realization", "reproduction"):
            assert states[key].balance == pytest.approx(1.0)
            assert states[key].gap == pytest.approx(1.0)
            assert states[key].leading_pole == "b"

    def test_half_share_is_the_neutral_midpoint(self) -> None:
        states = _states(
            GraphInputs(
                commodity_overhang_share=0.5,
                realization_crisis_share=0.5,
                reproduction_crisis_share=0.5,
            )
        )
        for key in ("circulation", "realization", "reproduction"):
            assert states[key].gap == pytest.approx(0.0)
            assert states[key].balance == pytest.approx(0.0)

    def test_disproportionality_reads_the_signed_imbalance_directly(self) -> None:
        states = _states(GraphInputs(disproportionality_imbalance=0.15))
        assert states["disproportionality"].balance == pytest.approx(0.15)
        assert states["disproportionality"].gap == pytest.approx(0.15)
        assert states["disproportionality"].leading_pole == "b"  # over-industrialized

    def test_disproportionality_negative_imbalance_is_pole_a(self) -> None:
        states = _states(GraphInputs(disproportionality_imbalance=-0.2))
        assert states["disproportionality"].balance == pytest.approx(-0.2)
        assert states["disproportionality"].leading_pole == "a"  # under-industrialized

    def test_disproportionality_is_clamped_to_unit_interval(self) -> None:
        states = _states(GraphInputs(disproportionality_imbalance=1.7))
        assert states["disproportionality"].balance == pytest.approx(1.0)

    def test_circulation_and_reproduction_transforms_couplings_are_reserved(self) -> None:
        """ADR103's two dead ``transforms`` slots name exactly these keys —
        pinned here so a rename of either side silently breaking the
        coupling is caught at the opposition-catalog layer too (the
        coupling-graph layer already pins it in test_coupling.py)."""
        reg = _reg()
        assert "circulation" in reg.keys
        assert "realization" in reg.keys
        assert "reproduction" in reg.keys
        assert "disproportionality" in reg.keys


class TestCatalogDocstringAccuracy:
    """The module docstring is a claim about the registry; pin it to the code.

    It went stale twice already — it still said "five bound contradictions"
    and omitted ``price_value`` for the whole period during which
    ``price_value`` was CANONICAL (ADR078). Documentation that describes a
    registry can be checked against that registry, so it is.
    """

    def test_docstring_names_every_registered_key(self) -> None:
        import babylon.domain.dialectics.instances.catalog as catalog_module

        docstring = catalog_module.__doc__ or ""
        for key in build_default_registry().keys:
            assert f"``{key}``" in docstring, f"docstring never mentions {key!r}"

    def test_docstring_does_not_claim_five(self) -> None:
        import babylon.domain.dialectics.instances.catalog as catalog_module

        docstring = catalog_module.__doc__ or ""
        assert "five bound contradictions" not in docstring
        assert "The five oppositions" not in docstring
