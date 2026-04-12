"""Type registry for Dialectic subclass deserialization.

Maps ``type_tag`` strings to concrete ``Dialectic`` subclasses. Used by
the repository layer to hydrate the correct Pydantic class from JSONB
when loading dialectics from Postgres.

Usage::

    from babylon.engine.dialectics.registry import default_registry

    cls = default_registry.lookup("CommodityDialectic")
    instance = cls(**row_data)

See Also:
    :class:`babylon.engine.dialectics.base.Dialectic`: Base class with type_tag.
"""

from __future__ import annotations

from typing import Any

from babylon.engine.dialectics.base import Dialectic


class DialecticRegistry:
    """Maps type_tag discriminator strings to Dialectic subclasses.

    Thread-safe for reads after initialization. Registration should
    happen at import time, not during tick execution.
    """

    def __init__(self) -> None:
        self._registry: dict[str, type[Dialectic[Any, Any]]] = {}

    def register(self, cls: type[Dialectic[Any, Any]]) -> None:
        """Register a Dialectic subclass by its type_tag.

        Args:
            cls: A concrete Dialectic subclass with type_tag set.

        Raises:
            ValueError: If a class with the same type_tag is already registered.
        """
        # Get type_tag from class field default
        type_tag = cls.model_fields["type_tag"].default
        if type_tag in self._registry:
            raise ValueError(
                f"type_tag '{type_tag}' already registered to {self._registry[type_tag].__name__}"
            )
        self._registry[type_tag] = cls

    def lookup(self, type_tag: str) -> type[Dialectic[Any, Any]]:
        """Look up a Dialectic subclass by type_tag.

        Args:
            type_tag: The discriminator string.

        Returns:
            The registered Dialectic subclass.

        Raises:
            KeyError: If type_tag is not registered.
        """
        if type_tag not in self._registry:
            raise KeyError(f"Unknown dialectic type_tag: '{type_tag}'")
        return self._registry[type_tag]

    def registered_types(self) -> list[str]:
        """Return all registered type_tag strings.

        Returns:
            List of registered type_tag strings.
        """
        return list(self._registry.keys())


# ===========================================================================
# Module-level default registry with all known types
# ===========================================================================


def _build_default_registry() -> DialecticRegistry:
    """Build the default registry with all known dialectic types."""
    from babylon.engine.dialectics.accumulation import AccumulationDialectic
    from babylon.engine.dialectics.circulation import CirculationDialectic
    from babylon.engine.dialectics.commodity import CommodityDialectic
    from babylon.engine.dialectics.consciousness import ClassConsciousnessDialectic
    from babylon.engine.dialectics.consumption import ConsumptionDialectic
    from babylon.engine.dialectics.credit import CreditDialectic
    from babylon.engine.dialectics.crises import (
        DebtSpiralCrisisDialectic,
        DisproportionalityCrisisDialectic,
        FinancialCrisisDialectic,
        RealizationCrisisDialectic,
    )
    from babylon.engine.dialectics.distribution import DistributionDialectic
    from babylon.engine.dialectics.imperial import ImperialDialectic
    from babylon.engine.dialectics.labor_process import LaborProcessDialectic
    from babylon.engine.dialectics.primitive_accumulation import (
        PrimitiveAccumulationDialectic,
    )
    from babylon.engine.dialectics.production import ProductionDialectic
    from babylon.engine.dialectics.rent import RentDialectic
    from babylon.engine.dialectics.reproduction import ReproductionDialectic
    from babylon.engine.dialectics.surplus_distribution import (
        SurplusDistributionDialectic,
    )
    from babylon.engine.dialectics.trpf import TRPFDialectic
    from babylon.engine.dialectics.turnover import TurnoverDialectic
    from babylon.engine.dialectics.wage import WageDialectic

    registry = DialecticRegistry()

    # V1
    registry.register(CommodityDialectic)
    registry.register(LaborProcessDialectic)
    registry.register(ProductionDialectic)
    registry.register(WageDialectic)
    registry.register(AccumulationDialectic)
    registry.register(PrimitiveAccumulationDialectic)

    # V2
    registry.register(CirculationDialectic)
    registry.register(ConsumptionDialectic)
    registry.register(DistributionDialectic)
    registry.register(ReproductionDialectic)
    registry.register(TurnoverDialectic)

    # V3
    registry.register(SurplusDistributionDialectic)
    registry.register(TRPFDialectic)
    registry.register(CreditDialectic)
    registry.register(RentDialectic)
    registry.register(ImperialDialectic)

    # Consciousness
    registry.register(ClassConsciousnessDialectic)

    # Crises
    registry.register(RealizationCrisisDialectic)
    registry.register(DisproportionalityCrisisDialectic)
    registry.register(DebtSpiralCrisisDialectic)
    registry.register(FinancialCrisisDialectic)

    return registry


default_registry: DialecticRegistry = _build_default_registry()
