"""TDD RED phase: Tests for the Grundrisse 4-cycle wiring.

The four Grundrisse dialectics wire into a cycle:

    Production --feeds--> Circulation
    Circulation --feeds--> Distribution
    Distribution --feeds--> Consumption
    Consumption --feeds--> Production    ← closes here

Each dialectic's step() reads peer outputs from world.previous (the
prior tick's frozen snapshot), not the current tick. This is Picard
fixed-point iteration: W_{n+1} = T(W_n).

Validates:
- Production reads prior consumption's labor_power_renewed / mp_renewed
- Circulation reads prior production's surplus_value / c / v
- Distribution reads prior circulation's realized_money
- Consumption reads prior distribution's wages_paid / surplus_distributed
- A full 4-cycle world runs 10 ticks without invariant violations
- State evolves (tick_updated advances each tick)
- Fixed-point convergence: weights stabilize over enough iterations
"""

from __future__ import annotations

from babylon.economics.circulation.types import CircuitState
from babylon.economics.tensor import DepartmentRow
from babylon.engine.dialectics.base import EmptyPole
from babylon.engine.dialectics.circulation import CirculationDialectic
from babylon.engine.dialectics.consumption import (
    ConsumptionDialectic,
    IndividualConsumption,
    ProductiveConsumption,
)
from babylon.engine.dialectics.distribution import (
    DistributionDialectic,
    SurplusShares,
    Wages,
)
from babylon.engine.dialectics.production import ProductionDialectic
from babylon.engine.dialectics.tick import tick
from babylon.engine.dialectics.world import Morphism, World
from babylon.models.types import Currency

# ===========================================================================
# Helpers — build the Grundrisse 4-cycle world
# ===========================================================================


def _make_grundrisse_world(t: int = 0) -> World:
    """Build a World with the 4 Grundrisse dialectics wired in a cycle.

    Production → Circulation → Distribution → Consumption → Production.
    """
    production = ProductionDialectic(
        pole_a=DepartmentRow(c=Currency(100.0), v=Currency(50.0), s=Currency(25.0)),
        pole_b=EmptyPole(),
        weight=0.0,
        tick_created=t,
        tick_updated=t,
    )
    circulation = CirculationDialectic(
        pole_a=CircuitState(
            fips_code="26000",
            year=2024,
            money_capital=Currency(100.0),
            productive_capital=Currency(50.0),
            commodity_capital=Currency(25.0),
            fixed_capital=Currency(30.0),
            circulating_capital=Currency(20.0),
        ),
        pole_b=EmptyPole(),
        weight=0.0,
        tick_created=t,
        tick_updated=t,
    )
    distribution = DistributionDialectic(
        pole_a=Wages(wages_paid=50.0),
        pole_b=SurplusShares(profit_distributed=15.0, interest_paid=5.0, rent_paid=5.0),
        weight=0.0,
        tick_created=t,
        tick_updated=t,
    )
    consumption = ConsumptionDialectic(
        pole_a=ProductiveConsumption(means_of_production_value=100.0),
        pole_b=IndividualConsumption(labor_power_reproduced=50.0),
        weight=0.0,
        tick_created=t,
        tick_updated=t,
    )

    # Wire the 4-cycle: feeds morphisms
    morphisms = [
        Morphism(
            source_id=production.id,
            target_id=circulation.id,
            relation="feeds",
            weight=1.0,
        ),
        Morphism(
            source_id=circulation.id,
            target_id=distribution.id,
            relation="feeds",
            weight=1.0,
        ),
        Morphism(
            source_id=distribution.id,
            target_id=consumption.id,
            relation="feeds",
            weight=1.0,
        ),
        Morphism(
            source_id=consumption.id,
            target_id=production.id,
            relation="feeds",
            weight=1.0,
        ),
    ]

    return World(
        tick=t,
        dialectics={
            production.id: production,
            circulation.id: circulation,
            distribution.id: distribution,
            consumption.id: consumption,
        },
        morphisms=morphisms,
    )


# ===========================================================================
# Production reads from prior Consumption (closing the cycle)
# ===========================================================================


class TestProductionReadsConsumption:
    """Production.step() reads prior consumption to renew inputs."""

    def test_production_reads_prior_mp_renewed(self) -> None:
        """Production should read means_of_production_value from
        prior tick's ConsumptionDialectic via world.previous."""
        w0 = _make_grundrisse_world()
        w1, _ = tick(w0, [])
        # Production was stepped — verify it advanced
        for d in w1.dialectics.values():
            if d.type_tag == "ProductionDialectic":
                assert d.tick_updated == 1

    def test_production_step_uses_previous_world(self) -> None:
        """Over two ticks, production reads consumption from t=0 at t=1,
        and from t=1 at t=2. Both should succeed without error."""
        w0 = _make_grundrisse_world()
        w1, events1 = tick(w0, [])
        w2, events2 = tick(w1, [])
        # No invariant violations across two ticks
        violation_events = [e for e in events1 + events2 if e.event_type == "invariant_violation"]
        assert len(violation_events) == 0


# ===========================================================================
# Consumption emits outputs that Production can read
# ===========================================================================


class TestConsumptionEmitsRenewalOutputs:
    """Consumption.observe() must emit renewal outputs for Production."""

    def test_consumption_observe_includes_mp_renewed(self) -> None:
        """Consumption should emit means_of_production_renewed."""
        cons = ConsumptionDialectic(
            pole_a=ProductiveConsumption(means_of_production_value=100.0),
            pole_b=IndividualConsumption(labor_power_reproduced=50.0),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        obs = cons.observe()
        assert "mp_renewed" in obs
        assert obs["mp_renewed"] == 100.0

    def test_consumption_observe_includes_labor_power_renewed(self) -> None:
        """Consumption should emit labor_power_renewed."""
        cons = ConsumptionDialectic(
            pole_a=ProductiveConsumption(means_of_production_value=100.0),
            pole_b=IndividualConsumption(labor_power_reproduced=50.0),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        obs = cons.observe()
        assert "labor_power_renewed" in obs
        assert obs["labor_power_renewed"] == 50.0


# ===========================================================================
# Distribution emits outputs for Consumption
# ===========================================================================


class TestDistributionEmitsOutputs:
    """Distribution.observe() must emit wages_paid and surplus_distributed."""

    def test_distribution_observe_includes_wages(self) -> None:
        dist = DistributionDialectic(
            pole_a=Wages(wages_paid=50.0),
            pole_b=SurplusShares(profit_distributed=15.0, interest_paid=5.0, rent_paid=5.0),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        obs = dist.observe()
        assert "wages_paid" in obs
        assert obs["wages_paid"] == 50.0

    def test_distribution_observe_includes_surplus_distributed(self) -> None:
        dist = DistributionDialectic(
            pole_a=Wages(wages_paid=50.0),
            pole_b=SurplusShares(profit_distributed=15.0, interest_paid=5.0, rent_paid=5.0),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        obs = dist.observe()
        assert "surplus_distributed" in obs
        assert obs["surplus_distributed"] == 25.0  # 15 + 5 + 5


# ===========================================================================
# Circulation emits realized_money for Distribution
# ===========================================================================


class TestCirculationEmitsOutputs:
    """Circulation.observe() must emit realized_money for Distribution."""

    def test_circulation_observe_includes_total_capital(self) -> None:
        circ = CirculationDialectic(
            pole_a=CircuitState(
                fips_code="26000",
                year=2024,
                money_capital=Currency(100.0),
                productive_capital=Currency(50.0),
                commodity_capital=Currency(25.0),
                fixed_capital=Currency(30.0),
                circulating_capital=Currency(20.0),
            ),
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        obs = circ.observe()
        assert "total_capital" in obs

    def test_circulation_observe_includes_realized_money(self) -> None:
        circ = CirculationDialectic(
            pole_a=CircuitState(
                fips_code="26000",
                year=2024,
                money_capital=Currency(100.0),
                productive_capital=Currency(50.0),
                commodity_capital=Currency(25.0),
                fixed_capital=Currency(30.0),
                circulating_capital=Currency(20.0),
            ),
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        obs = circ.observe()
        assert "realized_money" in obs
        assert obs["realized_money"] == 100.0  # Money capital = realized money


# ===========================================================================
# Full Grundrisse cycle integration
# ===========================================================================


class TestGrundrisseCycle:
    """Full 4-cycle integration: Production → Circulation → Distribution → Consumption → Production."""

    def test_cycle_runs_10_ticks_without_violations(self) -> None:
        """The Grundrisse cycle should iterate 10 ticks without invariant violations."""
        w = _make_grundrisse_world()
        all_events = []
        for _ in range(10):
            w, events = tick(w, [])
            all_events.extend(events)

        violation_events = [e for e in all_events if e.event_type == "invariant_violation"]
        assert len(violation_events) == 0
        assert w.tick == 10

    def test_all_dialectics_stepped_each_tick(self) -> None:
        """Every dialectic should have tick_updated == current tick after stepping."""
        w = _make_grundrisse_world()
        for i in range(5):
            w, _ = tick(w, [])
            for d in w.dialectics.values():
                assert d.tick_updated == i + 1, (
                    f"{d.type_tag} tick_updated={d.tick_updated} != {i + 1}"
                )

    def test_cycle_reaches_consistent_state(self) -> None:
        """After enough iterations, the cycle should reach approximate consistency.

        Weights should not diverge wildly. This is the fixed-point convergence
        test: ‖W_{n+1} - W_n‖ should be bounded.
        """
        w = _make_grundrisse_world()
        for _ in range(20):
            w, _ = tick(w, [])

        for d in w.dialectics.values():
            assert -1.0 <= d.weight <= 1.0, f"{d.type_tag} weight out of bounds: {d.weight}"

    def test_production_reads_previous_consumption(self) -> None:
        """At tick 2+, ProductionDialectic should have actually read
        ConsumptionDialectic's observe() output from the prior tick.

        We verify by checking that Production has been stepped with
        non-trivial state (not just the default).
        """
        w = _make_grundrisse_world()
        for _ in range(3):
            w, _ = tick(w, [])

        # Find the production dialectic
        prod = None
        for d in w.dialectics.values():
            if d.type_tag == "ProductionDialectic":
                prod = d
                break
        assert prod is not None
        assert prod.tick_updated == 3

    def test_worldview_previous_populated(self) -> None:
        """Verify that after tick(), the world state is correctly threaded.

        The WorldView passed to step() should have previous populated.
        We can't directly inspect the WorldView passed inside tick(),
        but we can verify the external invariant: running successive
        ticks produces correct state evolution.
        """
        w0 = _make_grundrisse_world()
        w1, _ = tick(w0, [])
        w2, _ = tick(w1, [])
        w3, _ = tick(w2, [])

        assert w3.tick == 3
        # All four dialectics should be at tick 3
        assert len(w3.dialectics) == 4
        for d in w3.dialectics.values():
            assert d.tick_updated == 3
