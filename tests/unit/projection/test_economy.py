"""Contract tests for :func:`babylon.projection.economy.project_economy`.

The economy dossier's behavioral contract (T3 spine-C prescription,
``ai/_inbox/PROGRAM_v1_0_0_playable_archive.md`` §C): the Fundamental
Theorem verdict read verbatim off the ``wage`` opposition's Balance (never a
parallel Φ), the per-class Φ readings from the ``fundamental_theorem`` graph
stash, Φ's tri-decomposition (genuinely absent tree-wide today), the Volume
III surplus split aggregated RATIO-OF-SUMS, and the metabolic matter-book.
Fixture-fed — no engine tick, no database — per the keel's fixture-first
discipline. Test class names mirror the intent of the retired
``TestEconomyDashboardFundamentalTheorem``/``TestEconomyDashboardChipContract``
GAP rows (``specs/24-archive/test-port-ledger.md`` rows 191-192).
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.tick.types import TickSummary
from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.entities.territory import Territory
from babylon.models.enums import SocialRole
from babylon.models.enums.territory import SectorType
from babylon.models.enums.topology import NodeType
from babylon.models.world_state import WorldState
from babylon.projection.economy import project_economy
from babylon.topology import BabylonGraph

WAYNE = "26163"

_WAYNE_SURPLUS_ATTRS = {
    "tick_total_surplus": 1000.0,
    "tick_profit_of_enterprise": 400.0,
    "tick_interest_burden": 100.0,
    "tick_ground_rent": 300.0,
    "tick_taxes_on_surplus": 200.0,
}
_OAKLAND_SURPLUS_ATTRS = {
    "tick_total_surplus": 500.0,
    "tick_profit_of_enterprise": 200.0,
    "tick_interest_burden": 50.0,
    "tick_ground_rent": 150.0,
    "tick_taxes_on_surplus": 100.0,
}

#: A minimal valid TickSummary carrying national_melt=65.0 — the ONE input
#: phi_domestic/phi_iii_report share, already live on the graph independent
#: of the Φ tri-decomposition wiring (see project_economy's own docstring).
_NATIONAL_MELT_SUMMARY = TickSummary(
    year=2020,
    counties_processed=1,
    phi_aggregate=0.0,
    national_melt=65.0,
    mean_profit_rate=0.1,
    mean_occ=1.0,
    mean_exploitation_rate=1.0,
    national_class_distribution={},
)

_GAMMA_BASKET_DUMP = {"year": 2022, "alpha": 0.35, "gamma_import": 0.65, "gamma_basket": 0.74}
_GAMMA_III_DUMP = {
    "year": 2022,
    "paid_care_hours": 16.5,
    "unpaid_care_hours": 33.0,
    "gamma_iii": 0.333,
    "fortunati_exploitation": 2.003,
}


def _territory(node_id: str, *, biocapacity: float, max_biocapacity: float) -> Territory:
    """Build a minimal Territory entity for matter-book tests."""
    return Territory(
        id=node_id,
        name=f"Test {node_id}",
        sector_type=SectorType.RESIDENTIAL,
        biocapacity=biocapacity,
        max_biocapacity=max_biocapacity,
    )


def _make_entity(
    eid: str,
    *,
    county_fips: str | None = None,
    population: int = 100,
) -> SocialClass:
    """Build a minimal SocialClass (default s_bio/s_class => consumption_needs=0.01)."""
    return SocialClass(
        id=eid,
        name=f"Test {eid}",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=1.0,
        ideology=IdeologicalProfile(class_consciousness=0.5, national_identity=0.5),
        population=population,
        county_fips=county_fips,
    )


class TestEconomyDashboardFundamentalTheorem:
    """The verdict is read verbatim off opposition_states['wage'].balance — never a parallel Φ."""

    def test_positive_balance_is_the_labor_aristocracy_verdict(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr(
            "opposition_states",
            {
                "wage": {
                    "key": "wage",
                    "tick": 1,
                    "gap": 0.4,
                    "balance": 0.25,
                    "rate": 0.0,
                    "leading_pole": "b",
                }
            },
        )
        view = project_economy("USA", graph=graph, world=WorldState(), tick=1)

        assert view.wage_balance == pytest.approx(0.25)
        assert view.labor_aristocracy_verdict is True

    def test_negative_balance_is_not_the_labor_aristocracy_verdict(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr(
            "opposition_states",
            {
                "wage": {
                    "key": "wage",
                    "tick": 1,
                    "gap": 0.4,
                    "balance": -0.1,
                    "rate": 0.0,
                    "leading_pole": "a",
                }
            },
        )
        view = project_economy("USA", graph=graph, world=WorldState(), tick=1)

        assert view.wage_balance == pytest.approx(-0.1)
        assert view.labor_aristocracy_verdict is False

    def test_unwired_registry_is_honest_absence(self) -> None:
        view = project_economy("USA", graph=BabylonGraph(), world=WorldState(), tick=1)

        assert view.wage_balance is None
        assert view.labor_aristocracy_verdict is None

    def test_wage_key_absent_from_a_populated_opposition_states_is_honest_absence(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr(
            "opposition_states",
            {"capital_labor": {"key": "capital_labor", "tick": 1, "gap": 0.1, "balance": 0.0}},
        )
        view = project_economy("USA", graph=graph, world=WorldState(), tick=1)

        assert view.wage_balance is None
        assert view.labor_aristocracy_verdict is None

    def test_per_class_phi_readings_hydrate_sorted_by_entity_id(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr(
            "fundamental_theorem",
            {
                "C002": {
                    "entity_id": "C002",
                    "w_paid": 50.0,
                    "v_produced": 60.0,
                    "phi_absolute": -10.0,
                    "phi_relative": -1.0 / 6.0,
                    "labor_aristocracy_ratio": 50.0 / 60.0,
                    "is_labor_aristocracy": False,
                },
                "C001": {
                    "entity_id": "C001",
                    "w_paid": 120.0,
                    "v_produced": 100.0,
                    "phi_absolute": 20.0,
                    "phi_relative": 0.2,
                    "labor_aristocracy_ratio": 1.2,
                    "is_labor_aristocracy": True,
                },
            },
        )
        view = project_economy("USA", graph=graph, world=WorldState(), tick=1)

        assert view.class_phi_readings is not None
        assert [r.entity_id for r in view.class_phi_readings] == ["C001", "C002"]
        assert view.class_phi_readings[0].is_labor_aristocracy is True
        assert view.class_phi_readings[1].phi_absolute == pytest.approx(-10.0)

    def test_zero_production_class_projects_none_ratio_subfields(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr(
            "fundamental_theorem",
            {
                "C001": {
                    "entity_id": "C001",
                    "w_paid": 10.0,
                    "v_produced": 0.0,
                    "phi_absolute": 10.0,
                }
            },
        )
        view = project_economy("USA", graph=graph, world=WorldState(), tick=1)

        assert view.class_phi_readings is not None
        reading = view.class_phi_readings[0]
        assert reading.phi_relative is None
        assert reading.labor_aristocracy_ratio is None
        assert reading.is_labor_aristocracy is None

    def test_fundamental_theorem_attr_absent_is_honest_none(self) -> None:
        view = project_economy("USA", graph=BabylonGraph(), world=WorldState(), tick=1)

        assert view.class_phi_readings is None

    def test_fundamental_theorem_present_but_empty_dict_is_a_real_empty_tuple(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr("fundamental_theorem", {})
        view = project_economy("USA", graph=graph, world=WorldState(), tick=1)

        assert view.class_phi_readings == ()

    def test_phi_tri_decomposition_is_honest_absence_tree_wide(self) -> None:
        """Wired-but-genuinely-absent: every conservation component and the total."""
        view = project_economy("USA", graph=BabylonGraph(), world=WorldState(), tick=1)

        assert view.phi_unequal_exchange is None
        assert view.phi_reproduction is None
        assert view.phi_domestic is None
        assert view.phi_iii_report is None
        assert view.phi_decomposition_total is None


class TestPhiTriDecomposition:
    """Each Φ tri-decomposition component reads its OWN named graph inputs.

    Fix-commit regression coverage: the tri-decomposition must have a real
    read site per component (each attempting ``graph.get_graph_attr`` for
    its own named inputs and calling the matching ``value_form`` builder
    only when all of them resolve) rather than five hardcoded ``None``
    literals — a future producer publishing any ONE component's inputs must
    make that component light up with no change to ``project_economy``.
    These tests exercise the lit-up path directly, giving the previously
    zero-caller ``value_form`` builders (and ``PhiDecomposition`` itself) a
    real call site.
    """

    def test_unequal_exchange_lights_up_from_gamma_basket_and_consumption(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr("gamma_basket", _GAMMA_BASKET_DUMP)
        graph.set_graph_attr("consumption", 1000.0)
        view = project_economy("USA", graph=graph, world=WorldState(), tick=1)

        assert view.phi_unequal_exchange == pytest.approx((1.0 - 0.74) * 1000.0)
        # The other components still lack THEIR OWN inputs — each reads
        # independently, so one lighting up must not fabricate the rest.
        assert view.phi_reproduction is None
        assert view.phi_domestic is None
        assert view.phi_iii_report is None
        assert view.phi_decomposition_total is None

    def test_reproduction_lights_up_from_p_g2_and_wage_paid(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr("p_g2_labor_value", 60000.0)
        graph.set_graph_attr("wage_paid_for_d_g2", 12000.0)
        view = project_economy("USA", graph=graph, world=WorldState(), tick=1)

        assert view.phi_reproduction == pytest.approx(48000.0)
        assert view.phi_unequal_exchange is None
        assert view.phi_decomposition_total is None

    def test_domestic_lights_up_from_l_unpaid_and_national_melt(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr("l_unpaid", 1000.0)
        graph.set_graph_attr("tick_dynamics", {"tick_summary": _NATIONAL_MELT_SUMMARY})
        view = project_economy("USA", graph=graph, world=WorldState(), tick=1)

        assert view.phi_domestic == pytest.approx(65.0 * 1000.0)
        assert view.phi_decomposition_total is None

    def test_domestic_stays_absent_without_national_melt_even_with_l_unpaid(self) -> None:
        """One input alone is not both inputs — τ must ALSO resolve."""
        graph = BabylonGraph()
        graph.set_graph_attr("l_unpaid", 1000.0)
        view = project_economy("USA", graph=graph, world=WorldState(), tick=1)

        assert view.phi_domestic is None

    def test_iii_report_lights_up_from_gamma_iii_and_national_melt(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr("gamma_iii", _GAMMA_III_DUMP)
        graph.set_graph_attr("tick_dynamics", {"tick_summary": _NATIONAL_MELT_SUMMARY})
        view = project_economy("USA", graph=graph, world=WorldState(), tick=1)

        assert view.phi_iii_report == pytest.approx((1.0 - 0.333) * 33.0 * 65.0)
        # phi_iii_report is report-only (D2 kernel-fork resolution) — it
        # never gates phi_decomposition_total on its own.
        assert view.phi_decomposition_total is None

    def test_decomposition_total_requires_all_three_conservation_components(self) -> None:
        graph = BabylonGraph()
        graph.set_graph_attr("gamma_basket", _GAMMA_BASKET_DUMP)
        graph.set_graph_attr("consumption", 1000.0)
        graph.set_graph_attr("p_g2_labor_value", 60000.0)
        graph.set_graph_attr("wage_paid_for_d_g2", 12000.0)
        graph.set_graph_attr("l_unpaid", 1000.0)
        graph.set_graph_attr("tick_dynamics", {"tick_summary": _NATIONAL_MELT_SUMMARY})
        view = project_economy("USA", graph=graph, world=WorldState(), tick=1)

        expected_unequal_exchange = (1.0 - 0.74) * 1000.0
        expected_reproduction = 48000.0
        expected_domestic = 65.0 * 1000.0
        assert view.phi_unequal_exchange == pytest.approx(expected_unequal_exchange)
        assert view.phi_reproduction == pytest.approx(expected_reproduction)
        assert view.phi_domestic == pytest.approx(expected_domestic)
        assert view.phi_decomposition_total == pytest.approx(
            expected_unequal_exchange + expected_reproduction + expected_domestic
        )

    def test_decomposition_total_missing_one_conservation_component_is_none(self) -> None:
        """Two of three conservation components present is still not enough."""
        graph = BabylonGraph()
        graph.set_graph_attr("gamma_basket", _GAMMA_BASKET_DUMP)
        graph.set_graph_attr("consumption", 1000.0)
        graph.set_graph_attr("p_g2_labor_value", 60000.0)
        graph.set_graph_attr("wage_paid_for_d_g2", 12000.0)
        # l_unpaid / national_melt deliberately absent — phi_domestic stays None.
        view = project_economy("USA", graph=graph, world=WorldState(), tick=1)

        assert view.phi_unequal_exchange is not None
        assert view.phi_reproduction is not None
        assert view.phi_domestic is None
        assert view.phi_decomposition_total is None

    def test_decomposition_total_excludes_iii_report(self) -> None:
        """Adding phi_iii_report's OWN inputs must not change the total (D2 fork)."""
        graph = BabylonGraph()
        graph.set_graph_attr("gamma_basket", _GAMMA_BASKET_DUMP)
        graph.set_graph_attr("consumption", 1000.0)
        graph.set_graph_attr("p_g2_labor_value", 60000.0)
        graph.set_graph_attr("wage_paid_for_d_g2", 12000.0)
        graph.set_graph_attr("l_unpaid", 1000.0)
        graph.set_graph_attr("gamma_iii", _GAMMA_III_DUMP)
        graph.set_graph_attr("tick_dynamics", {"tick_summary": _NATIONAL_MELT_SUMMARY})
        view = project_economy("USA", graph=graph, world=WorldState(), tick=1)

        assert view.phi_iii_report is not None
        without_iii_report = view.phi_unequal_exchange + view.phi_reproduction + view.phi_domestic
        assert view.phi_decomposition_total == pytest.approx(without_iii_report)


class TestEconomyDashboardChipContract:
    """Surplus-split + matter-book aggregate quantities: extensive ratio-of-sums."""

    def test_surplus_split_sums_extensively_across_territories(self) -> None:
        graph = BabylonGraph()
        graph.add_node("T001", NodeType.TERRITORY, county_fips=WAYNE, **_WAYNE_SURPLUS_ATTRS)
        graph.add_node("T002", NodeType.TERRITORY, county_fips="26125", **_OAKLAND_SURPLUS_ATTRS)
        view = project_economy("USA", graph=graph, world=WorldState(), tick=1)

        assert view.surplus_produced == pytest.approx(1500.0)
        assert view.profit_of_enterprise == pytest.approx(600.0)
        assert view.interest_burden == pytest.approx(150.0)
        assert view.ground_rent == pytest.approx(450.0)
        assert view.taxes_on_surplus == pytest.approx(300.0)

    def test_surplus_identity_holds_on_the_summed_totals(self) -> None:
        graph = BabylonGraph()
        graph.add_node("T001", NodeType.TERRITORY, county_fips=WAYNE, **_WAYNE_SURPLUS_ATTRS)
        graph.add_node("T002", NodeType.TERRITORY, county_fips="26125", **_OAKLAND_SURPLUS_ATTRS)
        view = project_economy("USA", graph=graph, world=WorldState(), tick=1)

        total = (
            view.profit_of_enterprise
            + view.interest_burden
            + view.ground_rent
            + view.taxes_on_surplus
        )
        assert total == pytest.approx(view.surplus_produced)

    def test_shares_are_ratio_of_sums_not_mean_of_ratios(self) -> None:
        """A tiny territory's extreme per-territory ratio must not swing the national share."""
        graph = BabylonGraph()
        graph.add_node("T001", NodeType.TERRITORY, **_WAYNE_SURPLUS_ATTRS)
        graph.add_node(
            "T002",
            NodeType.TERRITORY,
            tick_total_surplus=1.0,
            tick_profit_of_enterprise=0.0,
            tick_interest_burden=1.0,
            tick_ground_rent=0.0,
            tick_taxes_on_surplus=0.0,
        )
        view = project_economy("USA", graph=graph, world=WorldState(), tick=1)

        expected = (100.0 + 1.0) / (1000.0 + 1.0)
        assert view.financialization_share == pytest.approx(expected)
        # A naive mean of per-territory ratios would be (0.10 + 1.0) / 2 = 0.55.
        assert view.financialization_share < 0.5

    def test_profit_of_enterprise_may_be_negative_in_a_debt_spiral(self) -> None:
        graph = BabylonGraph()
        graph.add_node(
            "T001",
            NodeType.TERRITORY,
            tick_total_surplus=100.0,
            tick_profit_of_enterprise=-50.0,
            tick_interest_burden=80.0,
            tick_ground_rent=50.0,
            tick_taxes_on_surplus=20.0,
        )
        view = project_economy("USA", graph=graph, world=WorldState(), tick=1)

        assert view.profit_of_enterprise == pytest.approx(-50.0)

    def test_no_territory_carries_the_attr_is_honest_absence(self) -> None:
        view = project_economy("USA", graph=BabylonGraph(), world=WorldState(), tick=1)

        assert view.surplus_produced is None
        assert view.profit_of_enterprise is None
        assert view.interest_burden is None
        assert view.ground_rent is None
        assert view.taxes_on_surplus is None
        assert view.rentier_share is None
        assert view.financialization_share is None

    def test_zero_surplus_is_honest_absence_for_the_two_shares_only(self) -> None:
        graph = BabylonGraph()
        graph.add_node(
            "T001",
            NodeType.TERRITORY,
            tick_total_surplus=0.0,
            tick_profit_of_enterprise=0.0,
            tick_interest_burden=0.0,
            tick_ground_rent=0.0,
            tick_taxes_on_surplus=0.0,
        )
        view = project_economy("USA", graph=graph, world=WorldState(), tick=1)

        assert view.surplus_produced == pytest.approx(0.0)
        assert view.rentier_share is None
        assert view.financialization_share is None

    def test_matter_book_extensive_sums(self) -> None:
        world = WorldState(
            territories={
                "T001": _territory("T001", biocapacity=40.0, max_biocapacity=100.0),
                "T002": _territory("T002", biocapacity=60.0, max_biocapacity=120.0),
            },
            entities={"C001": _make_entity("C001")},
        )
        view = project_economy("USA", graph=BabylonGraph(), world=world, tick=1)

        assert view.total_biocapacity == pytest.approx(100.0)
        assert view.biocapacity_ceiling == pytest.approx(220.0)
        assert view.total_consumption == pytest.approx(0.01)
        assert view.overshoot_ratio == pytest.approx(0.01 / 100.0)

    def test_zero_biocapacity_yields_honest_none_overshoot(self) -> None:
        world = WorldState(
            territories={"T001": _territory("T001", biocapacity=0.0, max_biocapacity=0.0)}
        )
        view = project_economy("USA", graph=BabylonGraph(), world=world, tick=1)

        assert view.total_biocapacity == pytest.approx(0.0)
        assert view.overshoot_ratio is None

    def test_no_territories_is_honest_absence_for_the_whole_matter_book(self) -> None:
        view = project_economy("USA", graph=BabylonGraph(), world=WorldState(), tick=1)

        assert view.total_consumption is None
        assert view.total_biocapacity is None
        assert view.overshoot_ratio is None
        assert view.biocapacity_ceiling is None

    def test_matter_book_never_reads_the_static_biocapacity_sum_seed(self) -> None:
        """Regression: the matter-book must never source from a Postgres view row."""
        world = WorldState(
            territories={"T001": _territory("T001", biocapacity=5.0, max_biocapacity=5.0)}
        )
        view = project_economy("USA", graph=BabylonGraph(), world=world, tick=1)

        assert view.total_biocapacity == pytest.approx(5.0)

    def test_energy_beta_j_is_always_absent(self) -> None:
        view = project_economy("USA", graph=BabylonGraph(), world=WorldState(), tick=1)

        assert view.energy_beta_j is None


class TestDeterminism:
    """Identical inputs yield identical frozen dossiers."""

    def test_double_projection_is_identical(self) -> None:
        graph = BabylonGraph()
        graph.add_node("T001", NodeType.TERRITORY, county_fips=WAYNE, **_WAYNE_SURPLUS_ATTRS)
        graph.set_graph_attr(
            "opposition_states",
            {"wage": {"key": "wage", "tick": 1, "gap": 0.4, "balance": 0.25, "rate": 0.0}},
        )
        world = WorldState(entities={"C001": _make_entity("C001", county_fips=WAYNE)})

        first = project_economy("USA", graph=graph, world=world, tick=847)
        second = project_economy("USA", graph=graph, world=world, tick=847)

        assert first == second
        assert first.model_dump() == second.model_dump()
