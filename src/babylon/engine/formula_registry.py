"""Formula registry for hot-swappable mathematical functions.

This module provides a FormulaRegistry class that stores named callables,
enabling runtime replacement of formulas for testing and modding.

Sprint 3: Central Committee (Dependency Injection)
"""

from collections.abc import Callable
from typing import Any

from babylon.systems import formulas

# Type alias for formula functions
FormulaFunc = Callable[..., Any]


class FormulaRegistry:
    """Registry for named mathematical formulas.

    Provides a central lookup for all simulation formulas, enabling:
    - Hot-swapping formulas for testing with mocks
    - Modding support for custom formula implementations
    - Centralized formula management

    Example:
        >>> registry = FormulaRegistry.default()
        >>> rent = registry.get("imperial_rent")
        >>> result = rent(alpha=0.5, periphery_wages=0.4, periphery_consciousness=0.2)
    """

    def __init__(self) -> None:
        """Initialize an empty formula registry."""
        self._formulas: dict[str, FormulaFunc] = {}

    def register(self, name: str, func: FormulaFunc) -> None:
        """Register or replace a formula by name.

        Args:
            name: Unique identifier for the formula
            func: Callable implementing the formula
        """
        self._formulas[name] = func

    def get(self, name: str) -> FormulaFunc:
        """Retrieve a formula by name.

        Args:
            name: The formula identifier

        Returns:
            The registered formula callable

        Raises:
            KeyError: If no formula is registered with the given name
        """
        if name not in self._formulas:
            raise KeyError(f"No formula registered with name: {name}")
        return self._formulas[name]

    def list_formulas(self) -> list[str]:
        """List all registered formula names.

        Returns:
            List of formula names in arbitrary order
        """
        return list(self._formulas.keys())

    @classmethod
    def default(cls) -> "FormulaRegistry":
        """Create a registry pre-populated with all standard formulas.

        Registers all 12 formulas from babylon.systems.formulas:
        - imperial_rent
        - labor_aristocracy_ratio
        - is_labor_aristocracy
        - consciousness_drift
        - acquiescence_probability
        - revolution_probability
        - crossover_threshold
        - loss_aversion
        - exchange_ratio
        - exploitation_rate
        - value_transfer
        - prebisch_singer

        Returns:
            FormulaRegistry with all standard formulas registered
        """
        registry = cls()

        # Fundamental Theorem formulas
        registry.register("imperial_rent", formulas.calculate_imperial_rent)
        registry.register("labor_aristocracy_ratio", formulas.calculate_labor_aristocracy_ratio)
        registry.register("is_labor_aristocracy", formulas.is_labor_aristocracy)
        registry.register("consciousness_drift", formulas.calculate_consciousness_drift)

        # Survival Calculus formulas
        registry.register("acquiescence_probability", formulas.calculate_acquiescence_probability)
        registry.register("revolution_probability", formulas.calculate_revolution_probability)
        registry.register("crossover_threshold", formulas.calculate_crossover_threshold)
        registry.register("loss_aversion", formulas.apply_loss_aversion)

        # Unequal Exchange formulas
        registry.register("exchange_ratio", formulas.calculate_exchange_ratio)
        registry.register("exploitation_rate", formulas.calculate_exploitation_rate)
        registry.register("value_transfer", formulas.calculate_value_transfer)
        registry.register("prebisch_singer", formulas.prebisch_singer_effect)

        # Solidarity Transmission formulas (Sprint 3.4.2)
        registry.register("solidarity_transmission", formulas.calculate_solidarity_transmission)

        # Dynamic Balance formulas (Sprint 3.4.4)
        registry.register("bourgeoisie_decision", formulas.calculate_bourgeoisie_decision)

        return registry
