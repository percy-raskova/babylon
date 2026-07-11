"""Unit tests for ``game.provenance`` (spec-113 Lane D).

Manifest contract test + functional resolution tests against a real
tick-0 ``wayne_county`` ``WorldState``/graph (via
``game.engine_bridge._build_initial_state_for_scenario`` — the same
scenario-seeding pipeline the bridge itself uses, no mocking of engine
internals).
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = pytest.mark.unit


def _wayne_state_and_graph() -> tuple[object, object]:
    from game.engine_bridge import _build_initial_state_for_scenario

    state = _build_initial_state_for_scenario("wayne_county")
    return state, state.to_graph()


class TestManifestContract:
    """Every entry names a registered formula (when it names one at all);
    extractor input names match ``inspect.signature`` of that callable."""

    def test_every_set_formula_name_is_registered(self) -> None:
        from babylon.engine.formula_registry import FormulaRegistry
        from game.provenance import METRIC_PROVENANCE

        registered = set(FormulaRegistry.default().list_formulas())
        for metric, provenance in METRIC_PROVENANCE.items():
            if provenance.formula_name is None:
                continue
            assert provenance.formula_name in registered, (
                f"{metric!r}'s formula_name {provenance.formula_name!r} is not "
                f"a FormulaRegistry.default() entry"
            )

    def test_formula_backed_entries_input_names_match_signature(self) -> None:
        """inputs_fn's returned names == the callable's real parameter names."""
        from babylon.engine.formula_registry import FormulaRegistry
        from game.provenance import METRIC_PROVENANCE, ExplainContext, ExplainScope

        state, graph = _wayne_state_and_graph()
        registry = FormulaRegistry.default()
        for metric, provenance in METRIC_PROVENANCE.items():
            if provenance.formula_name is None:
                continue
            fn = registry.get(provenance.formula_name)
            expected_names = set(inspect.signature(fn).parameters)
            for scope_kind in provenance.supported_scopes:
                entity_id = "C002" if scope_kind == "org" else None
                ctx = ExplainContext(
                    state=state, graph=graph, scope=ExplainScope(scope_kind, entity_id)
                )
                actual_names = {i.name for i in provenance.inputs_fn(ctx)}
                assert actual_names == expected_names, (
                    f"{metric!r} ({scope_kind}) inputs {actual_names} != "
                    f"signature params {expected_names}"
                )

    def test_at_least_the_required_metrics_are_covered(self) -> None:
        """architecture.md §2.4 TASKS: exploitation_rate/profit_rate/occ/
        imperial_rent, plus 4+ more that FormulaRegistry actually registers."""
        from game.provenance import METRIC_PROVENANCE

        required = {"exploitation_rate", "profit_rate", "occ", "imperial_rent"}
        assert required.issubset(METRIC_PROVENANCE.keys())
        formula_backed = {m for m, p in METRIC_PROVENANCE.items() if p.formula_name is not None}
        assert len(formula_backed - {"exploitation_rate"}) >= 4

    def test_every_entry_expression_is_nonempty(self) -> None:
        from game.provenance import METRIC_PROVENANCE

        for metric, provenance in METRIC_PROVENANCE.items():
            assert provenance.expression, f"{metric!r} has an empty expression"

    def test_consciousness_drift_expression_matches_architecture_example(self) -> None:
        """architecture.md §2.4's own worked example string."""
        from game.provenance import METRIC_PROVENANCE

        assert (
            METRIC_PROVENANCE["consciousness_drift"].expression
            == "dPsi/dt = k(1 - Wc/Vc) - lambda*Psi + bifurcation."
        )


class TestParseScope:
    def test_global_has_no_entity_id(self) -> None:
        from game.provenance import parse_scope

        scope = parse_scope("global")
        assert scope.kind == "global"
        assert scope.entity_id is None

    def test_hex_scope_extracts_h3_id(self) -> None:
        from game.provenance import parse_scope

        scope = parse_scope("hex:872a30d8affffff")
        assert scope.kind == "hex"
        assert scope.entity_id == "872a30d8affffff"

    def test_org_scope_extracts_entity_id(self) -> None:
        from game.provenance import parse_scope

        scope = parse_scope("org:C002")
        assert scope.kind == "org"
        assert scope.entity_id == "C002"

    def test_format_scope_round_trips(self) -> None:
        from game.provenance import format_scope, parse_scope

        for raw in ("global", "hex:872a30d8affffff", "org:C002"):
            assert format_scope(parse_scope(raw)) == raw


class TestExplainMetricErrors:
    def test_unknown_metric_raises(self) -> None:
        from game.provenance import ExplainScope, UnknownMetricError, explain_metric

        state, graph = _wayne_state_and_graph()
        with pytest.raises(UnknownMetricError):
            explain_metric(state, graph, "not_a_real_metric", ExplainScope("global"))

    def test_unsupported_scope_raises_with_supported_list(self) -> None:
        from game.provenance import ExplainScope, UnsupportedScopeError, explain_metric

        state, graph = _wayne_state_and_graph()
        with pytest.raises(UnsupportedScopeError) as excinfo:
            explain_metric(state, graph, "imperial_rent", ExplainScope("org", "C001"))
        assert excinfo.value.supported == frozenset({"global"})

    def test_unknown_org_id_raises_not_found(self) -> None:
        from game.provenance import ExplainScope, ScopeEntityNotFoundError, explain_metric

        state, graph = _wayne_state_and_graph()
        with pytest.raises(ScopeEntityNotFoundError):
            explain_metric(state, graph, "revolution_probability", ExplainScope("org", "NOT_REAL"))

    def test_unknown_hex_id_raises_not_found(self) -> None:
        from game.provenance import ExplainScope, ScopeEntityNotFoundError, explain_metric

        state, graph = _wayne_state_and_graph()
        with pytest.raises(ScopeEntityNotFoundError):
            explain_metric(state, graph, "profit_rate", ExplainScope("hex", "notarealh3cell"))

    def test_org_scope_with_no_entity_id_raises_not_found(self) -> None:
        from game.provenance import ExplainScope, ScopeEntityNotFoundError, explain_metric

        state, graph = _wayne_state_and_graph()
        with pytest.raises(ScopeEntityNotFoundError):
            explain_metric(state, graph, "revolution_probability", ExplainScope("org", None))


class TestExploitationRateGlobal:
    def test_value_matches_aggregate_graph_economy(self) -> None:
        """No independent re-derivation: same number /economy/ shows."""
        from game.engine_bridge import _aggregate_graph_economy
        from game.provenance import ExplainScope, explain_metric

        state, graph = _wayne_state_and_graph()
        result = explain_metric(state, graph, "exploitation_rate", ExplainScope("global"))
        expected = _aggregate_graph_economy(graph)["exploitation_rate"]
        assert result.value == expected
        assert result.formula_name == "exploitation_rate"
        assert result.scope == "global"

    def test_exchange_ratio_input_is_a_recursive_metric_ref(self) -> None:
        from game.provenance import ExplainScope, explain_metric

        state, graph = _wayne_state_and_graph()
        result = explain_metric(state, graph, "exploitation_rate", ExplainScope("global"))
        assert len(result.inputs) == 1
        ratio_input = result.inputs[0]
        assert ratio_input.name == "exchange_ratio"
        assert ratio_input.kind == "metric"
        assert ratio_input.ref == "value_extraction_ratio"

    def test_value_extraction_ratio_recurses_to_a_terminal_state_frame(self) -> None:
        """metric -> formula -> input-metric -> explain (recursion depth test)."""
        from game.provenance import ExplainScope, explain_metric

        state, graph = _wayne_state_and_graph()
        outer = explain_metric(state, graph, "exploitation_rate", ExplainScope("global"))
        ref = outer.inputs[0].ref
        assert ref is not None
        inner = explain_metric(state, graph, ref, ExplainScope("global"))
        assert inner.formula_name is None  # terminal — a raw graph aggregate
        assert inner.inputs  # but still explains itself via state inputs
        assert {i.kind for i in inner.inputs} == {"state"}


class TestProfitRateAndOccHonestGaps:
    """profit_rate/occ have no live engine source anywhere — always None,
    never a fabricated number (Constitution III.11)."""

    @pytest.mark.parametrize("metric", ["profit_rate", "occ"])
    @pytest.mark.parametrize("scope_kind", ["global", "hex"])
    def test_value_is_always_none(self, metric: str, scope_kind: str) -> None:
        from game.provenance import ExplainScope, explain_metric

        state, graph = _wayne_state_and_graph()
        entity_id = None
        if scope_kind == "hex":
            entity_id = next(iter(state.territories.values())).h3_index
        result = explain_metric(state, graph, metric, ExplainScope(scope_kind, entity_id))
        assert result.value is None
        assert result.formula_name is None
        assert result.inputs == ()


class TestImperialRent:
    def test_value_is_the_real_ledger_balance(self) -> None:
        from game.provenance import ExplainScope, explain_metric

        state, graph = _wayne_state_and_graph()
        result = explain_metric(state, graph, "imperial_rent", ExplainScope("global"))
        assert result.value == pytest.approx(state.economy.imperial_rent_pool)
        assert result.formula_name is None
        assert result.inputs == ()


class TestLaborAristocracyRatioOrgScope:
    def test_real_entity_yields_a_computed_value(self) -> None:
        from game.provenance import ExplainScope, explain_metric

        state, graph = _wayne_state_and_graph()
        result = explain_metric(
            state, graph, "labor_aristocracy_ratio", ExplainScope("org", "C002")
        )
        entity = state.entities["C002"]
        assert result.value == pytest.approx(0.0 / float(entity.wealth))
        names = {i.name for i in result.inputs}
        assert names == {"core_wages", "value_produced"}
        value_produced_input = next(i for i in result.inputs if i.name == "value_produced")
        assert value_produced_input.value == pytest.approx(float(entity.wealth))


class TestRevolutionProbabilityOrgScope:
    def test_real_entity_matches_formula_call(self) -> None:
        from babylon.engine.formula_registry import FormulaRegistry
        from game.provenance import ExplainScope, explain_metric

        state, graph = _wayne_state_and_graph()
        result = explain_metric(state, graph, "revolution_probability", ExplainScope("org", "C001"))
        entity = state.entities["C001"]
        formula = FormulaRegistry.default().get("revolution_probability")
        expected = float(
            formula(cohesion=float(entity.organization), repression=float(entity.repression_faced))
        )
        assert result.value == pytest.approx(expected)


class TestAcquiescenceProbabilityMissingConstant:
    """steepness_k lives in GameDefines, out of this module's import
    surface — value stays honestly None even with real wealth/subsistence."""

    def test_value_is_none_but_state_inputs_are_real(self) -> None:
        from game.provenance import ExplainScope, explain_metric

        state, graph = _wayne_state_and_graph()
        result = explain_metric(
            state, graph, "acquiescence_probability", ExplainScope("org", "C001")
        )
        assert result.value is None
        entity = state.entities["C001"]
        wealth_input = next(i for i in result.inputs if i.name == "wealth")
        assert wealth_input.value == pytest.approx(float(entity.wealth))
        steepness_input = next(i for i in result.inputs if i.name == "steepness_k")
        assert steepness_input.value is None
        assert steepness_input.kind == "constant"


class TestConsciousnessDriftMissingConstants:
    def test_value_is_none_state_inputs_real_defaults_present(self) -> None:
        from game.provenance import ExplainScope, explain_metric

        state, graph = _wayne_state_and_graph()
        result = explain_metric(state, graph, "consciousness_drift", ExplainScope("org", "C002"))
        assert result.value is None
        by_name = {i.name: i for i in result.inputs}
        entity = state.entities["C002"]
        assert by_name["current_consciousness"].value == pytest.approx(
            float(entity.ideology.class_consciousness)
        )
        assert by_name["sensitivity_k"].value is None
        assert by_name["decay_lambda"].value is None
        assert by_name["solidarity_pressure"].value == 0.0
        assert by_name["wage_change"].value == 0.0
