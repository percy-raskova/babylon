"""WealthDistributionSystem — the runtime wealth-share axis (Program 21 Phase 1).

Red-phase battery per the Data Constitution wealth-axis design brief
(``reports/data-constitution-wealth-axis-brief.md``):

- the formerly-orphaned ``formulas/class_dynamics`` ODE is WIRED (registered
  system, classified in the spec-056 partition);
- the axis exists and round-trips (``SocialClass.wealth_share`` is a declared
  field — the ``extra="forbid"`` landmine — and the national vector rides
  ``G.graph["wealth_distribution"]`` metadata);
- seeding matches the calibration defines (``equilibrium_w1..w4``);
- relaxation is mean-reverting and share-conserving (Σ == 1 every tick);
- byte-safety: a WorldState without the axis writes NO new metadata key
  (golden preservation, the EH ruling-6 pattern);
- determinism: identical inputs ⇒ identical per-tick vectors.

Phase 1 is an observe-only shadow: ``wealth_share`` feeds nothing back into
wealth/consciousness/bifurcation (Phase 2 is owner-gated), so the sampled
qa:regression checkpoints stay byte-identical.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, CONSEQUENCE_SYSTEMS
from babylon.engine.systems.wealth_distribution import (
    WealthDistributionSystem,
    bracket_of_role,
)
from babylon.models.enums import SocialRole
from babylon.models.wealth_distribution import WealthDistribution

pytestmark = pytest.mark.unit


def _services() -> SimpleNamespace:
    """Minimal service stub — the system reads only ``defines.class_dynamics``."""
    return SimpleNamespace(defines=GameDefines())


def _graph_with_classes():  # type: ignore[no-untyped-def]
    """A small BabylonGraph carrying one node per wealth bracket."""
    from babylon.topology.graph import BabylonGraph

    g = BabylonGraph()
    roles = {
        "c1": SocialRole.CORE_BOURGEOISIE,
        "c2": SocialRole.PETTY_BOURGEOISIE,
        "c3": SocialRole.LABOR_ARISTOCRACY,
        "c4": SocialRole.INTERNAL_PROLETARIAT,
    }
    for node_id, role in roles.items():
        g.add_node(
            node_id,
            _node_type="social_class",
            role=role.value,
            class_consciousness=0.2,
            population=1000,
        )
    return g


class TestWiring:
    """The orphan is wired: registered, classified, formula consumed."""

    def test_system_is_registered(self) -> None:
        assert any(isinstance(s, WealthDistributionSystem) for s in _DEFAULT_SYSTEMS)

    def test_system_is_classified_as_consequence(self) -> None:
        assert WealthDistributionSystem in CONSEQUENCE_SYSTEMS

    def test_ode_formula_is_the_engine(self) -> None:
        # Guards against re-orphaning: the system module must consume the
        # class_dynamics ODE, not reimplement it.
        import babylon.engine.systems.wealth_distribution as mod

        assert hasattr(mod, "calculate_full_dynamics")


class TestSeeding:
    """First tick seeds the national vector from the calibration defines."""

    def test_seed_matches_equilibrium_defines(self) -> None:
        graph = _graph_with_classes()
        services = _services()
        WealthDistributionSystem().step(graph, services, {"tick": 0})
        meta = graph.graph["wealth_distribution"]
        cd = services.defines.class_dynamics
        expected = (cd.equilibrium_w1, cd.equilibrium_w2, cd.equilibrium_w3, cd.equilibrium_w4)
        total = sum(expected)
        for got, raw in zip(meta["shares"], expected, strict=True):
            assert got == pytest.approx(raw / total, abs=1e-12)
        assert sum(meta["shares"]) == pytest.approx(1.0, abs=1e-9)
        assert meta["velocities"] == [0.0, 0.0, 0.0, 0.0]

    def test_nodes_get_bracket_projection(self) -> None:
        graph = _graph_with_classes()
        WealthDistributionSystem().step(graph, _services(), {"tick": 0})
        shares = graph.graph["wealth_distribution"]["shares"]
        node = graph.get_node("c1")
        assert node is not None
        assert node.attributes["wealth_share"] == pytest.approx(shares[0])
        node4 = graph.get_node("c4")
        assert node4 is not None
        assert node4.attributes["wealth_share"] == pytest.approx(shares[3])


class TestDynamics:
    """Relaxation is mean-reverting and conserving (property laws)."""

    def test_shares_sum_to_one_every_tick(self) -> None:
        graph = _graph_with_classes()
        services = _services()
        system = WealthDistributionSystem()
        for tick in range(20):
            system.step(graph, services, {"tick": tick})
            assert sum(graph.graph["wealth_distribution"]["shares"]) == pytest.approx(1.0, abs=1e-9)

    def test_perturbation_mean_reverts(self) -> None:
        from babylon.formulas.class_dynamics import calculate_equilibrium_deviation

        graph = _graph_with_classes()
        services = _services()
        system = WealthDistributionSystem()
        system.step(graph, services, {"tick": 0})
        # Perturb off-equilibrium (shift 5 points from w3 to w1).
        meta = graph.graph["wealth_distribution"]
        shares = list(meta["shares"])
        shares[0] += 0.05
        shares[2] -= 0.05
        graph.graph["wealth_distribution"] = {**meta, "shares": shares}
        d0 = calculate_equilibrium_deviation(tuple(shares))
        for tick in range(1, 60):
            system.step(graph, services, {"tick": tick})
        d_final = calculate_equilibrium_deviation(
            tuple(graph.graph["wealth_distribution"]["shares"])
        )
        assert d_final < d0, "ODE relaxation must reduce equilibrium deviation"

    def test_determinism_identical_runs(self) -> None:
        def run() -> list[list[float]]:
            graph = _graph_with_classes()
            services = _services()
            system = WealthDistributionSystem()
            out = []
            for tick in range(10):
                system.step(graph, services, {"tick": tick})
                out.append(list(graph.graph["wealth_distribution"]["shares"]))
            return out

        assert run() == run()


class TestRoundTrip:
    """The axis survives to_graph → from_graph (the extra='forbid' landmine)."""

    def test_wealth_distribution_metadata_round_trips(self) -> None:
        from babylon.models.world_state import WorldState

        wd = WealthDistribution(
            shares=(0.305, 0.382, 0.294, 0.019),
            velocities=(0.0, 0.0, 0.0, 0.0),
            tick=7,
        )
        state = WorldState(tick=1, wealth_distribution=wd)
        recovered = WorldState.from_graph(state.to_graph(), tick=1)
        assert recovered.wealth_distribution is not None
        assert recovered.wealth_distribution.shares == pytest.approx(wd.shares)
        assert recovered.wealth_distribution.tick == 7

    def test_absent_axis_writes_no_metadata_key(self) -> None:
        # Golden preservation (EH ruling-6 pattern): synthetic/headless graphs
        # without the axis stay byte-identical.
        from babylon.models.world_state import WorldState

        graph = WorldState(tick=1).to_graph()
        assert "wealth_distribution" not in graph.graph

    def test_wealth_share_is_a_declared_field(self) -> None:
        from babylon.models.entities.social_class import SocialClass

        assert "wealth_share" in SocialClass.model_fields
        entity = SocialClass(
            id="C001", name="t", role=SocialRole.LABOR_ARISTOCRACY, wealth_share=0.25
        )
        assert entity.wealth_share == 0.25


class TestBracketMapping:
    """The PROVISIONAL 8-role → 4-bracket fold (owner ruling pending)."""

    def test_all_roles_map(self) -> None:
        for role in SocialRole:
            assert bracket_of_role(role) in (0, 1, 2, 3)

    def test_hinted_mapping(self) -> None:
        assert bracket_of_role(SocialRole.CORE_BOURGEOISIE) == 0
        assert bracket_of_role(SocialRole.PETTY_BOURGEOISIE) == 1
        assert bracket_of_role(SocialRole.LABOR_ARISTOCRACY) == 2
        assert bracket_of_role(SocialRole.INTERNAL_PROLETARIAT) == 3
        assert bracket_of_role(SocialRole.LUMPENPROLETARIAT) == 3


class TestModel:
    """WealthDistribution is frozen and validates conservation."""

    def test_frozen(self) -> None:
        wd = WealthDistribution(shares=(0.25, 0.25, 0.25, 0.25), velocities=(0, 0, 0, 0), tick=0)
        with pytest.raises(Exception):  # noqa: B017 — pydantic frozen error class varies
            wd.tick = 1  # type: ignore[misc]

    def test_shares_must_conserve(self) -> None:
        with pytest.raises(ValueError, match="sum"):
            WealthDistribution(shares=(0.9, 0.5, 0.1, 0.1), velocities=(0, 0, 0, 0), tick=0)
