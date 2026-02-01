"""TensorConsumer mixin for hexagon visualization.

This module provides the TensorConsumer protocol implementation for the
visualization layer. Components inheriting from TensorConsumerMixin can
access cached tensor data without database queries.

Feature: 011-fundamental-tensor-primitive
Implements: T042, T043 from tasks.md

The TensorConsumer pattern ensures hexagon visualization receives data
exclusively from the tensor primitive, never touching the database directly.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from babylon.economics.tensor import NoDataSentinel, ValueTensor4x3


logger = logging.getLogger(__name__)


@runtime_checkable
class TensorPrimitive(Protocol):
    """Protocol for read-only tensor access.

    This is the interface that TensorRegistry implements. Consumers use this
    protocol for type hints to avoid depending on the full TensorRegistry
    implementation.
    """

    def get(self, fips: str, year: int) -> ValueTensor4x3 | NoDataSentinel:
        """Get tensor for a specific county and year.

        Args:
            fips: 5-digit FIPS code.
            year: Calendar year.

        Returns:
            ValueTensor4x3 if data exists, NoDataSentinel otherwise.
        """
        ...


@runtime_checkable
class TensorConsumer(Protocol):
    """Protocol for components that consume tensor data.

    Consumers receive a TensorPrimitive reference and use it for read-only access.
    They MUST NOT import database modules or perform direct database queries.

    This protocol is implemented by visualization components that need economic
    tensor data (profit_rate, exploitation_rate, etc.) for rendering.

    Example:
        >>> class HexRenderer(TensorConsumerMixin):
        ...     def render(self, territory: TerritoryState) -> None:
        ...         if tensor := self.get_tensor(territory.territory_id, territory.tensor_year):
        ...             color = self._profit_rate_to_color(tensor.profit_rate)
    """

    def set_tensor_source(self, source: TensorPrimitive) -> None:
        """Set the tensor data source.

        Args:
            source: TensorPrimitive implementation (typically TensorRegistry).
        """
        ...


class TensorConsumerMixin:
    """Mixin providing tensor data access for visualization components.

    This mixin implements the TensorConsumer protocol, providing a clean
    interface for visualization components to access cached tensor data
    without database dependencies.

    Visualization components should inherit from this mixin to gain tensor
    access capabilities while maintaining isolation from the database layer.

    Attributes:
        _tensor_source: The tensor data source (TensorRegistry or compatible).

    Example:
        >>> class EnhancedMapViewport(TensorConsumerMixin, MapViewport):
        ...     def render_territory(self, territory_id: str, year: int) -> None:
        ...         if tensor := self.get_tensor(territory_id, year):
        ...             self._display_tensor_data(tensor)
        ...         else:
        ...             self._display_no_data(tensor.reason)
    """

    def __init__(self) -> None:
        """Initialize the mixin with no tensor source."""
        self._tensor_source: TensorPrimitive | None = None

    def set_tensor_source(self, source: TensorPrimitive) -> None:
        """Set the tensor data source.

        This method should be called during component initialization or
        when the simulation is loaded. After setting the source, tensor
        data can be accessed via get_tensor().

        Args:
            source: TensorPrimitive implementation (typically TensorRegistry).
                    Pass None to clear the tensor source.

        Example:
            >>> viewport = EnhancedMapViewport()
            >>> viewport.set_tensor_source(sim.tensor_registry)
        """
        self._tensor_source = source
        logger.debug(
            "Tensor source %s",
            "set" if source is not None else "cleared",
        )

    @property
    def has_tensor_source(self) -> bool:
        """Check if a tensor source is available.

        Returns:
            True if a tensor source is set, False otherwise.
        """
        return self._tensor_source is not None

    def get_tensor(self, fips: str, year: int | None) -> ValueTensor4x3 | NoDataSentinel | None:
        """Get tensor data for a county and year.

        This method provides cached tensor access without database queries.
        If no tensor source is set, returns None.

        Args:
            fips: 5-digit FIPS code for the county.
            year: Calendar year for the tensor data. If None, returns None.

        Returns:
            - ValueTensor4x3 if data exists
            - NoDataSentinel if data is missing (falsy, with reason)
            - None if no tensor source is set or year is None

        Example:
            >>> if tensor := component.get_tensor("26163", 2022):
            ...     print(f"Profit rate: {tensor.profit_rate}")
            ... else:
            ...     if tensor is None:
            ...         print("No tensor source configured")
            ...     else:
            ...         print(f"No data: {tensor.reason}")
        """
        if self._tensor_source is None:
            logger.debug("get_tensor: No tensor source configured")
            return None

        if year is None:
            logger.debug("get_tensor: year is None")
            return None

        return self._tensor_source.get(fips, year)


__all__ = [
    "TensorConsumer",
    "TensorConsumerMixin",
    "TensorPrimitive",
]
