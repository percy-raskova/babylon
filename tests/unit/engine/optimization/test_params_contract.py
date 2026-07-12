"""Behavioral contract: parameter introspection/injection (ADR038).

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

from babylon.config.defines import GameDefines
from babylon.engine.optimization.params import (
    get_tunable_parameters,
    inject_parameter,
)


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
        """Inject the midpoint of each (lo, hi) bound and read it straight back.

        This is the contract that makes sweep/Monte Carlo/sensitivity safe to
        run over the *entire* enumerated surface: every path
        ``get_tunable_parameters`` promises must be settable via
        ``inject_parameter``, and the value that comes back must be exactly
        what was set (Pydantic ``model_copy`` semantics, no silent coercion
        surprises beyond int/float).
        """
        base = GameDefines()
        params = get_tunable_parameters()
        for path, (lo, hi) in params.items():
            midpoint = (lo + hi) / 2.0
            updated = inject_parameter(base, path, midpoint)
            category, field = path.split(".")
            actual = getattr(getattr(updated, category), field)
            assert actual == midpoint or actual == int(midpoint), (
                f"{path}: injected {midpoint} but read back {actual}"
            )

    def test_invalid_category_raises_value_error(self) -> None:
        import pytest

        base = GameDefines()
        with pytest.raises(ValueError, match="Unknown category"):
            inject_parameter(base, "not_a_real_category.field", 1.0)

    def test_invalid_field_raises_value_error(self) -> None:
        import pytest

        base = GameDefines()
        with pytest.raises(ValueError, match="Unknown field"):
            inject_parameter(base, "economy.not_a_real_field", 1.0)
