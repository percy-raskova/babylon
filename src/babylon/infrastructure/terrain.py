"""Terrain classification and biocapacity extraction (Feature 036, US1).

Implements ``TerrainClassifier`` and ``BiocapacityStore`` protocols using
Natural Earth geographic data for spatial classification and mutable
biocapacity stock tracking.

See Also:
    :mod:`babylon.infrastructure.protocols`: TerrainClassifier, BiocapacityStore.
    ``specs/036-infrastructure-topology/spec.md``: FR-001 through FR-008.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import h3

from babylon.config.defines import InfraTerrainDefines
from babylon.infrastructure.natural_earth_reader import RESOURCE_FEATURECLA
from babylon.infrastructure.types import (
    BiocapacityStockState,
    ExtractionResult,
    TerrainClassification,
)
from babylon.models.enums import BiocapacityType, TerrainType

if TYPE_CHECKING:
    from babylon.infrastructure.natural_earth_reader import NaturalEarthReader

logger = logging.getLogger(__name__)

# Biocapacity stock types by terrain type
_WATER_STOCKS = (
    BiocapacityType.FRESHWATER,
    BiocapacityType.FISHERY,
    BiocapacityType.SHIPPING_ACCESS,
)
_RESOURCE_STOCKS = (BiocapacityType.MINERAL, BiocapacityType.TIMBER, BiocapacityType.HYDROELECTRIC)


# ---------------------------------------------------------------------------
# DefaultTerrainClassifier
# ---------------------------------------------------------------------------


class DefaultTerrainClassifier:
    """Classifies H3 hexes by terrain type using Natural Earth data.

    Algorithm:
    1. Convert H3 cell boundary to Shapely polygon (lat/lon -> lon/lat swap)
    2. Intersect with cached NE lakes and geographic region polygons
    3. Coverage = intersection_area / hex_area
    4. WATER if water_coverage >= threshold, else RESOURCE if resource >= threshold, else LAND

    Args:
        reader: NaturalEarthReader for loading geographic features.
        defines: TerrainDefines for classification thresholds.
    """

    def __init__(
        self,
        reader: NaturalEarthReader,
        defines: InfraTerrainDefines,
    ) -> None:
        self._reader = reader
        self._defines = defines
        self._cached_lakes: list[object] | None = None
        self._cached_regions: list[object] | None = None
        self._cached_bbox: tuple[float, float, float, float] | None = None

    def classify_hex(self, h3_index: str) -> TerrainClassification:
        """Classify a single hex by terrain type.

        Args:
            h3_index: H3 cell identifier.

        Returns:
            TerrainClassification with terrain_type and coverage fractions.
        """
        from shapely.geometry import Polygon  # type: ignore[import-untyped]

        # H3 boundary returns (lat, lon) — Shapely needs (lon, lat)
        boundary = h3.cell_to_boundary(h3_index)
        hex_poly = Polygon([(lon, lat) for lat, lon in boundary])
        hex_area = hex_poly.area

        if hex_area == 0.0:
            return TerrainClassification(
                h3_index=h3_index,
                terrain_type=TerrainType.LAND,
            )

        # Compute bbox for feature loading
        bounds = hex_poly.bounds  # (minx, miny, maxx, maxy) = (min_lon, min_lat, ...)
        bbox = (bounds[0], bounds[1], bounds[2], bounds[3])

        # Load features (use cached if available)
        lakes = self._reader.load_lakes(bbox)
        regions = self._reader.load_geography_regions(bbox)

        # Compute water coverage
        water_coverage = 0.0
        source_features: list[str] = []
        for lake in lakes:
            intersection = hex_poly.intersection(lake.geometry)
            if not intersection.is_empty:
                water_coverage += intersection.area / hex_area
                if lake.name:
                    source_features.append(lake.name)

        # Compute resource coverage (only RESOURCE_FEATURECLA regions)
        resource_coverage = 0.0
        for region in regions:
            if region.featurecla in RESOURCE_FEATURECLA:
                intersection = hex_poly.intersection(region.geometry)
                if not intersection.is_empty:
                    resource_coverage += intersection.area / hex_area
                    if region.name:
                        source_features.append(region.name)

        # Clamp to [0, 1]
        water_coverage = min(water_coverage, 1.0)
        resource_coverage = min(resource_coverage, 1.0)

        # Classification with majority coverage threshold
        threshold = self._defines.majority_coverage_threshold
        if water_coverage >= threshold:
            terrain_type = TerrainType.WATER
        elif resource_coverage >= threshold:
            terrain_type = TerrainType.RESOURCE
        else:
            terrain_type = TerrainType.LAND

        return TerrainClassification(
            h3_index=h3_index,
            terrain_type=terrain_type,
            water_coverage_fraction=water_coverage,
            resource_coverage_fraction=resource_coverage,
            source_features=source_features,
        )

    def classify_mesh(
        self,
        h3_indices: Sequence[str],
    ) -> dict[str, TerrainClassification]:
        """Classify all hexes in a mesh.

        Loads NE features once for the entire mesh bbox, then classifies
        each hex against the cached features.

        Args:
            h3_indices: Collection of H3 cell identifiers.

        Returns:
            Dict mapping h3_index to TerrainClassification.
        """
        result: dict[str, TerrainClassification] = {}
        for h3_index in h3_indices:
            result[h3_index] = self.classify_hex(h3_index)
        return result


# ---------------------------------------------------------------------------
# DefaultBiocapacityStore
# ---------------------------------------------------------------------------


@dataclass
class _MutableStock:
    """Internal mutable stock state for tracking depletion."""

    stock_type: str
    initial_value: float
    current_value: float
    depletion_history: list[float] = field(default_factory=list)


class DefaultBiocapacityStore:
    """Manages biocapacity stocks on WATER and RESOURCE hexes.

    Internally mutable; returns frozen DTOs via protocol methods.

    Args:
        defines: TerrainDefines for initial stock values and depletion rates.
    """

    def __init__(self, defines: InfraTerrainDefines) -> None:
        self._defines = defines
        self._stocks: dict[str, dict[str, _MutableStock]] = {}

    def initialize_stocks(
        self,
        classifications: dict[str, TerrainClassification],
    ) -> dict[str, list[BiocapacityStockState]]:
        """Initialize biocapacity stocks for all non-LAND hexes.

        Args:
            classifications: Terrain classifications for the mesh.

        Returns:
            Dict mapping h3_index to list of BiocapacityStockState.
        """
        result: dict[str, list[BiocapacityStockState]] = {}

        for h3_index, classification in classifications.items():
            terrain = classification.terrain_type
            if terrain == TerrainType.LAND:
                continue

            stock_types = _WATER_STOCKS if terrain == TerrainType.WATER else _RESOURCE_STOCKS
            hex_stocks: dict[str, _MutableStock] = {}
            stock_states: list[BiocapacityStockState] = []

            for stock_type in stock_types:
                initial = self._defines.get_initial_stock(stock_type.value)
                stock = _MutableStock(
                    stock_type=stock_type.value,
                    initial_value=initial,
                    current_value=initial,
                )
                hex_stocks[stock_type.value] = stock
                stock_states.append(self._to_dto(h3_index, stock))

            self._stocks[h3_index] = hex_stocks
            result[h3_index] = stock_states

        return result

    def get_stock(
        self,
        h3_index: str,
        stock_type: str,
    ) -> BiocapacityStockState | None:
        """Get current stock state for a hex and type.

        Args:
            h3_index: H3 cell identifier.
            stock_type: BiocapacityType value.

        Returns:
            Current stock state, or None if no stock of this type.
        """
        hex_stocks = self._stocks.get(h3_index)
        if hex_stocks is None:
            return None
        stock = hex_stocks.get(stock_type)
        if stock is None:
            return None
        return self._to_dto(h3_index, stock)

    def extract(
        self,
        source_h3: str,
        target_h3: str,
        stock_type: str,
        infrastructure_capacity: float,
        depletion_rate: float,
    ) -> ExtractionResult:
        """Extract biocapacity from a resource hex through an edge.

        Extraction = min(infrastructure_capacity, depletion_rate * current, current).

        Args:
            source_h3: Resource hex (WATER/RESOURCE).
            target_h3: Extracting LAND hex.
            stock_type: BiocapacityType value.
            infrastructure_capacity: Max extraction from edge infrastructure.
            depletion_rate: Per-tick depletion rate.

        Returns:
            ExtractionResult with amount extracted and remaining stock.

        Raises:
            KeyError: If source hex or stock type not found.
        """
        hex_stocks = self._stocks.get(source_h3)
        if hex_stocks is None:
            msg = f"No stocks for hex {source_h3}"
            raise KeyError(msg)
        stock = hex_stocks.get(stock_type)
        if stock is None:
            msg = f"No {stock_type} stock for hex {source_h3}"
            raise KeyError(msg)

        # FR-007: extraction = min(infra_cap, depletion_rate * current, current)
        rate_limited = depletion_rate * stock.current_value
        amount = min(infrastructure_capacity, rate_limited, stock.current_value)
        amount = max(amount, 0.0)

        # Update mutable state
        stock.current_value -= amount
        stock.depletion_history.append(amount)

        return ExtractionResult(
            source_h3=source_h3,
            target_h3=target_h3,
            stock_type=stock_type,
            amount_extracted=amount,
            remaining_stock=stock.current_value,
            infrastructure_constraint=infrastructure_capacity,
        )

    def to_dict(self) -> dict[str, list[dict[str, object]]]:
        """Serialize store state for tick-snapshot compatibility.

        Returns:
            Dict mapping h3_index to list of stock state dicts.
        """
        result: dict[str, list[dict[str, object]]] = {}
        for h3_index, hex_stocks in self._stocks.items():
            states: list[dict[str, object]] = []
            for stock in hex_stocks.values():
                dto = self._to_dto(h3_index, stock)
                states.append(dto.model_dump())
            result[h3_index] = states
        return result

    @classmethod
    def from_dict(
        cls,
        data: dict[str, list[dict[str, object]]],
        defines: InfraTerrainDefines,
    ) -> DefaultBiocapacityStore:
        """Deserialize store state from tick-snapshot data.

        Args:
            data: Serialized stock state from ``to_dict()``.
            defines: TerrainDefines instance.

        Returns:
            Reconstructed DefaultBiocapacityStore.
        """
        store = cls(defines)
        for h3_index, stock_dicts in data.items():
            hex_stocks: dict[str, _MutableStock] = {}
            for stock_dict in stock_dicts:
                stock = _MutableStock(
                    stock_type=str(stock_dict["stock_type"]),
                    initial_value=float(stock_dict["initial_value"]),  # type: ignore[arg-type]
                    current_value=float(stock_dict["current_value"]),  # type: ignore[arg-type]
                    depletion_history=[
                        float(x)
                        for x in stock_dict.get("depletion_history", [])  # type: ignore[attr-defined]
                    ],
                )
                hex_stocks[stock.stock_type] = stock
            store._stocks[h3_index] = hex_stocks
        return store

    @staticmethod
    def _to_dto(h3_index: str, stock: _MutableStock) -> BiocapacityStockState:
        """Convert internal mutable stock to frozen DTO."""
        return BiocapacityStockState(
            h3_index=h3_index,
            stock_type=stock.stock_type,
            initial_value=stock.initial_value,
            current_value=stock.current_value,
            depletion_history=list(stock.depletion_history),
            depleted=stock.current_value == 0.0,
        )
