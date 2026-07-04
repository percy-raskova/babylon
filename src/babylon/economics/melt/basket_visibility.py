"""BasketVisibilityCalculator service for computing γ_basket.

Feature: 013-melt-basket-visibility
Date: 2026-02-01

This module implements the basket visibility (γ_basket) computation
per TVT Axiom D3: γ_basket = 1 / (α/γ_import + (1-α)).

TVT Axiom Reference:
    - D3: Basket visibility derivation
    - D4: τ_effective = τ × γ_basket

Spec-102 (2026-07-04): ``DefaultBasketVisibilityCalculator`` accepts an
optional :class:`~babylon.economics.melt.gamma_hydration.GammaHydrationSource`
that hydrates real, per-year α and γ_import from the reference database
when the caller does not pass them explicitly. The MVP constants below
remain the documented degrade path for years the hydration source cannot
cover (or when no source is injected at all) — see
``specs/102-gamma-shocks/spec.md`` FR-102-2 for the disclosed data-coverage
gap.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from babylon.core.protocol_kit import CachedSource

if TYPE_CHECKING:
    from babylon.economics.melt.gamma_hydration import GammaHydrationSource

# MVP constants (derived from Hickel et al. methodology)
# α ≈ 0.25: Import share per Hickel et al. (2022) unequal exchange analysis
# γ_import ≈ 0.35: Trade-weighted average ERDI of US trading partners
# γ_basket = 1 / (0.25/0.35 + 0.75) = 1/1.464 ≈ 0.683
# Retained as the disclosed MVP degrade path (spec-102 FR-102-2): used only
# when no GammaHydrationSource is injected, or the injected source has no
# data for the requested year.
MVP_ALPHA: float = 0.25
MVP_GAMMA_IMPORT: float = 0.35
MVP_GAMMA_BASKET: float = 0.68

# Sanity range constants
EXPECTED_GAMMA_MIN: float = 0.60
EXPECTED_GAMMA_MAX: float = 0.80
WARNING_GAMMA_MIN: float = 0.40
WARNING_GAMMA_MAX: float = 0.95
FAIL_GAMMA_MIN: float = 0.10
FAIL_GAMMA_MAX: float = 1.0


class BasketVisibilityCalculator(Protocol):
    """Protocol for basket visibility (γ_basket) computation.

    Basket visibility measures the imperial subsidy on the US consumption
    basket per TVT Axiom D3:

        γ_basket = 1 / (α/γ_import + (1-α))

    where:
        - α = import share of consumption basket [0, 1]
        - γ_import = weighted average visibility of imported goods (0, 1]

    Interpretation:
        - γ_basket = 1.0: No imperial subsidy (α = 0, no imports)
        - γ_basket < 1.0: Consumption subsidized by compressed peripheral labor
        - γ_basket ≈ 0.68: Typical US value (~32% consumption subsidy)

    MVP Mode:
        When import/ERDI data is unavailable, returns hardcoded γ_basket = 0.68
        with estimated=True flag. This enables class position analysis without
        requiring Penn World Tables loader.

    TVT Axiom Reference:
        - D3: γ_basket formula
        - D4: τ_effective = τ × γ_basket

    Example:
        >>> calculator = DefaultBasketVisibilityCalculator()
        >>> gamma, estimated = calculator.get_gamma_basket(2022)
        >>> if estimated:
        ...     print(f"MVP estimate: γ_basket = {gamma}")
        ... else:
        ...     print(f"Computed: γ_basket = {gamma}")

    See Also:
        :class:`NationalParameters`: Uses γ_basket as a field
        :class:`MELTCalculator`: Companion service for τ
    """

    def get_gamma_basket(
        self,
        year: int,
        alpha: float | None = None,
        gamma_import: float | None = None,
    ) -> tuple[float, bool]:
        """Compute basket visibility for a given year.

        Formula: γ_basket = 1 / (α/γ_import + (1-α))

        Edge Cases:
            - α = 0: Returns γ_basket = 1.0 (no imports, no subsidy)
            - α = 1: Returns γ_basket = γ_import (100% imports)

        Args:
            year: Calendar year (for data lookup if params not provided)
            alpha: Import share [0, 1] (optional, uses data source if None)
            gamma_import: Peripheral visibility (0, 1] (optional, uses data if None)

        Returns:
            Tuple of (γ_basket, estimated) where:
            - γ_basket: Visibility coefficient (0, 1]
            - estimated: True if using MVP hardcoded value (data unavailable)

        Example:
            >>> # With explicit parameters
            >>> calculator.get_gamma_basket(2022, alpha=0.25, gamma_import=0.35)
            (0.683, False)

            >>> # MVP mode (no data available)
            >>> calculator.get_gamma_basket(2022)
            (0.68, True)

            >>> # Edge case: no imports
            >>> calculator.get_gamma_basket(2022, alpha=0.0, gamma_import=0.35)
            (1.0, False)

            >>> # Edge case: 100% imports
            >>> calculator.get_gamma_basket(2022, alpha=1.0, gamma_import=0.35)
            (0.35, False)
        """
        ...

    def validate_gamma_basket(self, gamma: float) -> tuple[bool, str | None]:
        """Validate γ_basket against sanity ranges per FR-010.

        Sanity Ranges:
            - Expected: 0.60-0.80 (typical US basket visibility)
            - Warning: 0.40-0.95 (unusual but possible)
            - Fail: <0.1 or >1.0 (indicates error)

        Args:
            gamma: Basket visibility to validate

        Returns:
            Tuple of (valid, message):
            - valid=True, message=None: Within expected range
            - valid=True, message=str: Warning (unusual value)
            - valid=False, message=str: Fail (invalid value)

        Example:
            >>> calculator.validate_gamma_basket(0.68)
            (True, None)
            >>> calculator.validate_gamma_basket(0.50)
            (True, 'WARNING: γ_basket=0.50 outside expected range [0.60, 0.80]')
            >>> calculator.validate_gamma_basket(0.05)
            (False, 'γ_basket=0.05 outside valid range [0.1, 1.0]')
        """
        ...

    @property
    def mvp_gamma_basket(self) -> float:
        """MVP hardcoded value for γ_basket.

        Returns:
            0.68 (derived from α ≈ 0.25, γ_import ≈ 0.35 per A-004)
        """
        ...

    @property
    def mvp_alpha(self) -> float:
        """MVP hardcoded value for import share α.

        Returns:
            0.25 (25% import share per Hickel et al. methodology)
        """
        ...

    @property
    def mvp_gamma_import(self) -> float:
        """MVP hardcoded value for peripheral visibility γ_import.

        Returns:
            0.35 (weighted average ERDI of US trading partners)
        """
        ...


class DefaultBasketVisibilityCalculator(CachedSource[float]):
    """Default implementation of BasketVisibilityCalculator.

    This calculator supports three modes: explicit-parameter (caller passes
    α and γ_import directly), hydrated (spec-102 — an injected
    :class:`~babylon.economics.melt.gamma_hydration.GammaHydrationSource`
    supplies real per-year values), and MVP (hardcoded fallback, when no
    source is injected or the source has no data for the requested year).

    MVP Derivation (A-004):
        - α ≈ 0.25: Import share per Hickel et al. (2022) methodology
        - γ_import ≈ 0.35: Trade-weighted average ERDI of US partners
        - γ_basket = 1 / (0.25/0.35 + 0.75) = 1/1.464 ≈ 0.68

    TVT Axiom Reference:
        - D3: γ_basket = 1 / (α/γ_import + (1-α))

    Example:
        >>> calculator = DefaultBasketVisibilityCalculator()
        >>> gamma, estimated = calculator.get_gamma_basket(2022)
        >>> print(f"γ_basket = {gamma}, estimated = {estimated}")
        γ_basket = 0.68, estimated = True

    See Also:
        :mod:`babylon.economics.melt.gamma_hydration`: Optional hydration source.
    """

    def __init__(
        self,
        hydration_source: GammaHydrationSource | None = None,
        *,
        max_entries: int = 1024,
    ) -> None:
        """Initialize the calculator.

        Args:
            hydration_source: Optional spec-102 hydration source supplying
                real per-year α/γ_import. When ``None`` (the default —
                identical to pre-spec-102 construction), the calculator
                behaves exactly as before: any call without explicit
                ``alpha``/``gamma_import`` falls straight into MVP mode.
            max_entries: Passed through to :class:`CachedSource`.
        """
        super().__init__(max_entries=max_entries)
        self._hydration_source = hydration_source

    def get_gamma_basket(
        self,
        year: int,
        alpha: float | None = None,
        gamma_import: float | None = None,
    ) -> tuple[float, bool]:
        """Compute basket visibility for a given year.

        Args:
            year: Calendar year. Used to query the injected hydration
                source when ``alpha``/``gamma_import`` are not supplied.
            alpha: Import share [0, 1] (optional — explicit value always
                wins over hydration).
            gamma_import: Peripheral visibility (0, 1] (optional — explicit
                value always wins over hydration).

        Returns:
            Tuple of (γ_basket, estimated). ``estimated`` is ``False`` only
            when both α and γ_import are either caller-supplied or
            successfully hydrated for ``year``; ``True`` (MVP hardcode)
            otherwise.
        """
        resolved_alpha = alpha
        resolved_gamma_import = gamma_import

        if self._hydration_source is not None:
            if resolved_alpha is None:
                resolved_alpha = self._hydration_source.get_alpha(year)
            if resolved_gamma_import is None:
                resolved_gamma_import = self._hydration_source.get_gamma_import(year)

        # If either parameter is still missing (no source injected, or the
        # source had no data for this year), use MVP mode.
        if resolved_alpha is None or resolved_gamma_import is None:
            return (MVP_GAMMA_BASKET, True)

        alpha = resolved_alpha
        gamma_import = resolved_gamma_import

        # Edge case: no imports (α = 0)
        if alpha == 0.0:
            return (1.0, False)

        # Edge case: 100% imports (α = 1)
        if alpha == 1.0:
            return (gamma_import, False)

        # Standard formula: γ_basket = 1 / (α/γ_import + (1-α))
        denominator = alpha / gamma_import + (1 - alpha)
        gamma_basket = 1.0 / denominator

        return (gamma_basket, False)

    def validate_gamma_basket(self, gamma: float) -> tuple[bool, str | None]:
        """Validate γ_basket against sanity ranges per FR-010.

        Args:
            gamma: Basket visibility to validate

        Returns:
            Tuple of (valid, message)
        """
        # Fail range: <0.1 or >1.0
        if gamma < FAIL_GAMMA_MIN or gamma > FAIL_GAMMA_MAX:
            return (
                False,
                f"γ_basket={gamma:.2f} outside valid range [{FAIL_GAMMA_MIN}, {FAIL_GAMMA_MAX}]",
            )

        # Warning range: 0.40-0.95 but outside expected
        if gamma < EXPECTED_GAMMA_MIN or gamma > EXPECTED_GAMMA_MAX:
            return (
                True,
                f"WARNING: γ_basket={gamma:.2f} outside expected range "
                f"[{EXPECTED_GAMMA_MIN}, {EXPECTED_GAMMA_MAX}]",
            )

        # Expected range: 0.60-0.80
        return (True, None)

    @property
    def mvp_gamma_basket(self) -> float:
        """MVP hardcoded value for γ_basket."""
        return MVP_GAMMA_BASKET

    @property
    def mvp_alpha(self) -> float:
        """MVP hardcoded value for import share α."""
        return MVP_ALPHA

    @property
    def mvp_gamma_import(self) -> float:
        """MVP hardcoded value for peripheral visibility γ_import."""
        return MVP_GAMMA_IMPORT


__all__ = ["BasketVisibilityCalculator", "DefaultBasketVisibilityCalculator"]
