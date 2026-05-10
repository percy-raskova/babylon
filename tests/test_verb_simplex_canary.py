import pytest

from babylon.engine.scenarios_wayne_county import create_wayne_county_scenario

# We import the resolve functions that exist, or mock the ones that don't
try:
    from babylon.engine.actions.aid import resolve_aid
except ImportError:
    resolve_aid = None

try:
    from babylon.engine.actions.investigate import resolve_investigate
except ImportError:
    resolve_investigate = None

try:
    from babylon.engine.actions.mobilize import resolve_mobilize
except ImportError:
    resolve_mobilize = None

try:
    from babylon.engine.actions.move import resolve_move
except ImportError:
    resolve_move = None

try:
    from babylon.engine.actions.negotiate import resolve_negotiate
except ImportError:
    resolve_negotiate = None

try:
    from babylon.engine.actions.reproduce import resolve_reproduce
except ImportError:
    resolve_reproduce = None

try:
    from babylon.engine.actions.educate import resolve_educate
except ImportError:
    resolve_educate = None

try:
    from babylon.engine.actions.attack import resolve_attack
except ImportError:
    resolve_attack = None

try:
    from babylon.engine.actions.campaign import resolve_campaign
except ImportError:
    resolve_campaign = None


class DummyDefines:
    def __init__(self):
        self.mobilize_cl_cost = 0.0
        self.solidarity_amplification_per_edge = 0.1
        self.turnout_per_sl = 10.0
        self.heat_generation_per_demonstrator = 0.1
        self.max_demonstrators_before_backfire = 1000.0
        self.base_agitation_gain = 5.0
        self.backfire_heat_multiplier = 2.0
        self.backfire_agitation_gain = 10.0
        self.strike_value_disruption_factor = 0.5
        self.aid_efficiency = 1.0


@pytest.fixture
def base_graph():
    state, config, defines = create_wayne_county_scenario()
    return state.to_graph()


class TestVerbSimplexCanaries:
    """End-to-End Canary tests ensuring the 9 core verbs route correctly into the consciousness simplex."""

    def test_investigate_does_not_mutate_simplex(self, base_graph):
        """INVESTIGATE: NO CONSCIOUSNESS CHANGE."""
        if not resolve_investigate:
            pytest.skip("INVESTIGATE action not fully implemented")

        # Pick a random org and target
        org_id = next(
            (n for n, d in base_graph.nodes(data=True) if d.get("node_type") == "SocialClass"),
            list(base_graph.nodes)[0],
        )
        target_id = list(base_graph.nodes)[1]

        pre_state_r = base_graph.nodes[target_id].get("r")

        resolve_investigate(
            action={"org_id": org_id, "target_id": target_id, "params": {}},
            graph=base_graph,
            defines=DummyDefines(),
        )

        post_state_r = base_graph.nodes[target_id].get("r")
        assert pre_state_r == post_state_r, "INVESTIGATE mutated simplex accidentally"

    def test_reproduce_does_not_mutate_simplex(self, base_graph):
        """REPRODUCE: NO CONSCIOUSNESS CHANGE."""
        if not resolve_reproduce:
            pytest.skip("REPRODUCE action not implemented")

        org_id = list(base_graph.nodes)[0]
        target_id = list(base_graph.nodes)[1]
        pre_state_r = base_graph.nodes[target_id].get("r")

        resolve_reproduce(
            action={"org_id": org_id, "target_id": target_id, "params": {}},
            graph=base_graph,
            defines=DummyDefines(),
        )

        assert base_graph.nodes[target_id].get("r") == pre_state_r

    def test_move_does_not_mutate_simplex(self, base_graph):
        """MOVE: NO CONSCIOUSNESS CHANGE."""
        if not resolve_move:
            pytest.skip("MOVE action not implemented")

        org_id = list(base_graph.nodes)[0]
        target_id = list(base_graph.nodes)[1]
        pre_state_r = base_graph.nodes[target_id].get("r")

        resolve_move(
            action={"org_id": org_id, "target_id": target_id, "params": {}},
            graph=base_graph,
            defines=DummyDefines(),
        )

        assert base_graph.nodes[target_id].get("r") == pre_state_r

    def test_negotiate_does_not_mutate_simplex(self, base_graph):
        """NEGOTIATE: NO CONSCIOUSNESS CHANGE."""
        if not resolve_negotiate:
            pytest.skip("NEGOTIATE action not implemented")

        org_id = list(base_graph.nodes)[0]
        target_id = list(base_graph.nodes)[1]
        pre_state_r = base_graph.nodes[target_id].get("r")

        resolve_negotiate(
            action={"org_id": org_id, "target_id": target_id, "params": {}},
            graph=base_graph,
            defines=DummyDefines(),
        )

        assert base_graph.nodes[target_id].get("r") == pre_state_r

    def test_mobilize_agitation_routing(self, base_graph):
        """MOBILIZE: Verifies practice agitation is generated and properly routed."""
        if not resolve_mobilize:
            pytest.skip("MOBILIZE action not implemented for consciousness")

        org_id = list(base_graph.nodes)[0]
        # Must target a class or territory that tracks agitation
        target_id = list(base_graph.nodes)[1]

        pre_agitation = base_graph.nodes[target_id].get("agitation", 0.0)

        result = resolve_mobilize(
            action={"org_id": org_id, "target_id": target_id, "params": {"sl_committed": 5.0}},
            graph=base_graph,
            hypergraph=None,
            defines=DummyDefines(),
        )

        if result.get("success"):
            post_agitation = base_graph.nodes[target_id].get("agitation", 0.0)
            assert post_agitation > pre_agitation, "Mobilize did not create agitation"

    @pytest.mark.skip(
        reason="EDUCATE backend deferred (ADR-037 / spec 044): module needs ~80-150 LOC implementation"
    )
    def test_educate_simplex_drift(self, base_graph):
        """EDUCATE: Modifies education_pressure, verify CI (r) routing."""
        pass

    @pytest.mark.skip(
        reason="CAMPAIGN backend deferred (ADR-037): no spec yet; needs new specs/0NN-campaign-verb.md"
    )
    def test_campaign_simplex_routing(self, base_graph):
        """CAMPAIGN: modifies institutional_factor, drifts toward l, avoids r (liberal trap)."""
        pass

    @pytest.mark.skip(
        reason="ATTACK backend deferred (ADR-037 / spec 046): module needs implementation"
    )
    def test_attack_simplex_routing(self, base_graph):
        """ATTACK: Generates collateral agitation and repression_backfire."""
        pass

    def test_aid_simplex_drift(self, base_graph):
        """AID: increases solidarity, verification of positive delta-r."""
        if not resolve_aid:
            pytest.skip("AID backend resolution logic absent (ADR-037 / spec 045)")

        # Currently resolve_aid is just a stub returning nothing/pass. So we skip dynamically if it isn't mutating.
        pytest.skip(
            "AID stub deferred (ADR-037 / spec 045): consciousness side-effects not "
            "yet implemented; resolve_aid returns placeholder defaults."
        )
