"""Tests for FormulaRegistry.

RED Phase: These tests define the contract for the formula registry.
The FormulaRegistry enables hot-swappable formulas for testing and modding.

Test Intent:
- FormulaRegistry stores named callable functions
- default() pre-registers all 12 standard formulas
- Formulas can be replaced for testing/modding
"""

import pytest


@pytest.mark.math
class TestFormulaRegistry:
    """Test FormulaRegistry behavior."""

    def test_register_and_get_works(self) -> None:
        """Can register a formula and retrieve it by name."""
        from babylon.engine.formula_registry import FormulaRegistry

        registry = FormulaRegistry()

        def my_formula(x: float) -> float:
            return x * 2

        registry.register("double", my_formula)
        retrieved = registry.get("double")

        assert retrieved is my_formula
        assert retrieved(5.0) == 10.0

    def test_get_unknown_raises_key_error(self) -> None:
        """Getting an unregistered formula raises KeyError."""
        from babylon.engine.formula_registry import FormulaRegistry

        registry = FormulaRegistry()

        with pytest.raises(KeyError) as exc_info:
            registry.get("nonexistent")

        assert "nonexistent" in str(exc_info.value)

    def test_list_formulas_returns_all_names(self) -> None:
        """list_formulas returns names of all registered formulas."""
        from babylon.engine.formula_registry import FormulaRegistry

        registry = FormulaRegistry()
        registry.register("alpha", lambda: None)
        registry.register("beta", lambda: None)
        registry.register("gamma", lambda: None)

        names = registry.list_formulas()

        assert set(names) == {"alpha", "beta", "gamma"}

    def test_list_formulas_empty_registry(self) -> None:
        """list_formulas returns empty list for new registry."""
        from babylon.engine.formula_registry import FormulaRegistry

        registry = FormulaRegistry()

        assert registry.list_formulas() == []

    def test_can_replace_formula(self) -> None:
        """Registering the same name replaces the formula (hot-swap)."""
        from babylon.engine.formula_registry import FormulaRegistry

        registry = FormulaRegistry()

        def original(x: float) -> float:
            return x

        def replacement(x: float) -> float:
            return x * 10

        registry.register("formula", original)
        assert registry.get("formula")(5.0) == 5.0

        # Hot-swap
        registry.register("formula", replacement)
        assert registry.get("formula")(5.0) == 50.0

    def test_default_registers_all_twelve_formulas(self) -> None:
        """default() factory creates registry with all 12 standard formulas."""
        from babylon.engine.formula_registry import FormulaRegistry

        registry = FormulaRegistry.default()
        formulas = registry.list_formulas()

        expected_formulas = [
            "imperial_rent",
            "labor_aristocracy_ratio",
            "is_labor_aristocracy",
            "consciousness_drift",
            "acquiescence_probability",
            "revolution_probability",
            "crossover_threshold",
            "loss_aversion",
            "exchange_ratio",
            "exploitation_rate",
            "value_transfer",
            "prebisch_singer",
        ]

        assert len(formulas) == 12
        for name in expected_formulas:
            assert name in formulas, f"Missing formula: {name}"

    def test_default_imperial_rent_works(self) -> None:
        """default() registry's imperial_rent formula is functional."""
        from babylon.engine.formula_registry import FormulaRegistry

        registry = FormulaRegistry.default()
        imperial_rent = registry.get("imperial_rent")

        # Test with known values: alpha=0.5, wages=0.4, consciousness=0.2
        # Expected: 0.5 * 0.4 * (1 - 0.2) = 0.5 * 0.4 * 0.8 = 0.16
        result = imperial_rent(alpha=0.5, periphery_wages=0.4, periphery_consciousness=0.2)
        assert result == pytest.approx(0.16)

    def test_default_acquiescence_probability_works(self) -> None:
        """default() registry's acquiescence_probability formula is functional."""
        from babylon.engine.formula_registry import FormulaRegistry

        registry = FormulaRegistry.default()
        p_acquiescence = registry.get("acquiescence_probability")

        # At threshold, probability should be 0.5
        result = p_acquiescence(wealth=0.5, subsistence_threshold=0.5, steepness_k=10.0)
        assert result == pytest.approx(0.5)

    def test_default_revolution_probability_works(self) -> None:
        """default() registry's revolution_probability formula is functional."""
        from babylon.engine.formula_registry import FormulaRegistry

        registry = FormulaRegistry.default()
        p_revolution = registry.get("revolution_probability")

        # With cohesion=0.5, repression=0.5: 0.5 / (0.5 + epsilon) ~ 1.0
        result = p_revolution(cohesion=0.5, repression=0.5)
        assert result == pytest.approx(1.0, rel=0.01)

    def test_default_formulas_match_module_functions(self) -> None:
        """default() registry formulas are the actual module functions."""
        from babylon.engine.formula_registry import FormulaRegistry
        from babylon.systems import formulas

        registry = FormulaRegistry.default()

        # Spot check a few
        assert registry.get("imperial_rent") is formulas.calculate_imperial_rent
        assert registry.get("loss_aversion") is formulas.apply_loss_aversion
        assert registry.get("prebisch_singer") is formulas.prebisch_singer_effect

    def test_hot_swap_for_testing(self) -> None:
        """Demonstrates hot-swap use case for testing."""
        from babylon.engine.formula_registry import FormulaRegistry

        registry = FormulaRegistry.default()

        # Original formula
        original_result = registry.get("loss_aversion")(-10.0)
        assert original_result == pytest.approx(-22.5)  # -10 * 2.25

        # Hot-swap with mock for testing
        def mock_loss_aversion(value: float) -> float:
            return value  # No loss aversion

        registry.register("loss_aversion", mock_loss_aversion)

        # Now uses mock
        mock_result = registry.get("loss_aversion")(-10.0)
        assert mock_result == -10.0
