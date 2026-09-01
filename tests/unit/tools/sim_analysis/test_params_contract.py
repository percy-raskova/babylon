"""Behavioral contract for analysis parameter introspection and injection.

:func:`get_tunable_parameters` is the single source of truth every
optimization algorithm (sweep, Monte Carlo, sensitivity, Bayesian) relies on
to know which ``GameDefines`` dot-paths exist and what range is safe to
explore. If it ever returns a path that doesn't resolve on a real
``GameDefines`` instance, or bounds where ``lo > hi``, every algorithm built
on top of it silently breaks. :func:`inject_parameter` is the corresponding
write-side contract: whatever path enumeration promises exists, injection
must be able to set.
"""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError
from tools.devtools.sim_analysis.params import (
    get_parameter_type,
    get_tunable_parameters,
    inject_parameter,
)

from babylon.config.defines import GameDefines


class TestGetTunableParameters:
    """Every enumerated path must be a real, resolvable GameDefines field."""

    def test_returns_nonempty(self) -> None:
        params = get_tunable_parameters()
        assert len(params) > 0

    def test_every_path_is_category_dot_field(self) -> None:
        params = get_tunable_parameters()
        for path in params:
            parts = path.split(".")
            assert len(parts) == 2, f"expected 'category.field', got: {path!r}"

    def test_every_path_resolves_on_default_defines(self) -> None:
        """Every enumerated path must ``getattr`` cleanly on ``GameDefines()``.

        This is the anti-drift guard: if a category submodel is renamed or a
        field removed, ``get_tunable_parameters`` must not keep advertising
        a dead path.
        """
        defines = GameDefines()
        params = get_tunable_parameters()
        for path in params:
            category, field = path.split(".")
            category_model = getattr(defines, category, None)
            assert category_model is not None, f"unknown category in path: {path!r}"
            assert hasattr(category_model, field), f"unknown field in path: {path!r}"

    def test_bounds_satisfy_lo_le_hi(self) -> None:
        params = get_tunable_parameters()
        violations = {k: v for k, v in params.items() if v[0] > v[1]}
        assert violations == {}, f"lo > hi for: {violations}"

    def test_category_filter_scopes_results(self) -> None:
        params = get_tunable_parameters(categories=["economy"])
        assert len(params) > 0
        assert all(k.startswith("economy.") for k in params)

    def test_known_path_present_with_expected_bounds(self) -> None:
        """Anchor on a specific, well-known path (regression pin).

        ``economy.base_subsistence`` carries explicit ``ge=0.0, le=0.5``
        Pydantic Field constraints (see
        ``src/babylon/config/defines/economy_basic.py``) — if introspection
        ever stops finding the explicit bound and falls back to the 10x-default
        heuristic, this test catches it.
        """
        params = get_tunable_parameters()
        assert "economy.base_subsistence" in params
        lo, hi = params["economy.base_subsistence"]
        assert lo == 0.0
        assert hi == 0.5

    def test_integer_parameter_bounds_remain_native_integers(self) -> None:
        lo, hi = get_tunable_parameters(categories=["crisis"])["crisis.crisis_period_ticks"]
        assert type(lo) is int
        assert type(hi) is int
        assert (lo, hi) == (1, 52)

    def test_strict_float_bounds_exclude_unsampleable_endpoints(self) -> None:
        params = get_tunable_parameters(categories=["crisis"])

        threshold_lo, threshold_hi = params["crisis.r_threshold"]
        assert threshold_lo == math.nextafter(0.0, math.inf)
        assert threshold_hi == 1.0

        hysteresis_lo, hysteresis_hi = params["crisis.hysteresis_coefficient"]
        assert hysteresis_lo == math.nextafter(0.0, math.inf)
        assert hysteresis_hi == math.nextafter(1.0, -math.inf)

        defines_at_lower = inject_parameter(GameDefines(), "crisis.r_threshold", threshold_lo)
        defines_at_upper = inject_parameter(
            GameDefines(), "crisis.hysteresis_coefficient", hysteresis_hi
        )
        assert defines_at_lower.crisis.r_threshold == threshold_lo
        assert defines_at_upper.crisis.hysteresis_coefficient == hysteresis_hi


class TestInjectParameter:
    """inject_parameter must round-trip for every path get_tunable_parameters names."""

    def test_round_trips_single_known_path(self) -> None:
        base = GameDefines()
        updated = inject_parameter(base, "economy.base_subsistence", 0.25)
        assert updated.economy.base_subsistence == 0.25

    def test_does_not_mutate_base(self) -> None:
        base = GameDefines()
        original_value = base.economy.base_subsistence
        inject_parameter(base, "economy.base_subsistence", 0.25)
        assert base.economy.base_subsistence == original_value

    def test_round_trips_every_tunable_path(self) -> None:
        """Reinject each field's valid current value and read it straight back.

        This is the contract that makes sweep/Monte Carlo/sensitivity safe to
        run over the *entire* enumerated surface: every path
        ``get_tunable_parameters`` promises must be settable via
        ``inject_parameter``. Some fields participate in cross-field model
        invariants, so an arbitrary independent midpoint is not necessarily a
        valid whole-model configuration; reinjecting the current value proves
        path/type support while retaining those invariants.
        """
        base = GameDefines()
        params = get_tunable_parameters()
        for path in params:
            category, field = path.split(".")
            current_value = getattr(getattr(base, category), field)
            updated = inject_parameter(base, path, current_value)
            actual = getattr(getattr(updated, category), field)
            assert actual == current_value, (
                f"{path}: injected {current_value} but read back {actual}"
            )
            assert type(actual) is get_parameter_type(path)

    def test_fractional_integer_parameter_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="crisis_period_ticks"):
            inject_parameter(GameDefines(), "crisis.crisis_period_ticks", 7.5)

    def test_integer_parameter_remains_an_integer(self) -> None:
        updated = inject_parameter(GameDefines(), "crisis.crisis_period_ticks", 7)
        assert updated.crisis.crisis_period_ticks == 7
        assert type(updated.crisis.crisis_period_ticks) is int

    def test_integral_float_is_normalized_before_strict_validation(self) -> None:
        updated = inject_parameter(GameDefines(), "crisis.crisis_period_ticks", 7.0)
        assert updated.crisis.crisis_period_ticks == 7
        assert type(updated.crisis.crisis_period_ticks) is int

    def test_invalid_category_raises_value_error(self) -> None:
        base = GameDefines()
        with pytest.raises(ValueError, match="Unknown category"):
            inject_parameter(base, "not_a_real_category.field", 1.0)

    def test_invalid_field_raises_value_error(self) -> None:
        base = GameDefines()
        with pytest.raises(ValueError, match="Unknown field"):
            inject_parameter(base, "economy.not_a_real_field", 1.0)
