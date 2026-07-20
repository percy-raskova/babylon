"""Unit tests for the production opposition catalog (Phase C).

Pins the honest measure each of the five oppositions is bound to, the
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
    def test_ten_oppositions_bound(self) -> None:
        assert _reg().keys == (
            "atomization",
            "capital_labor",
            "credit",
            "debt_spiral",
            "financial",
            "imperial",
            "price_value",
            "surplus_distribution",
            "tenancy",
            "wage",
        )

    def test_no_shadow_bindings_after_the_promotion(self) -> None:
        """ADR078: price_value is canonical; the shadow mechanism stays,
        empty, as the Amendment T landing surface."""
        assert _reg().shadow_keys == frozenset()

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
