"""Contract compliance tests for infrastructure topology protocols (T045).

Verifies that all concrete implementations satisfy their ``@runtime_checkable``
Protocol interfaces via ``isinstance()`` checks.

See Also:
    :mod:`babylon.infrastructure.protocols`: 7 Protocol definitions.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import InfrastructureDefines, InfraTerrainDefines
from babylon.infrastructure.capacity import DefaultEdgeCapacityCalculator
from babylon.infrastructure.internet import (
    DefaultInternetAccessManager,
    DefaultInternetFieldOperator,
)
from babylon.infrastructure.inventory import DefaultInfrastructureInventory
from babylon.infrastructure.protocols import (
    BiocapacityStore,
    EdgeCapacityCalculator,
    InfrastructureInventory,
    InternetAccessManager,
    InternetFieldOperator,
    SpatialSnapper,
    TerrainClassifier,
)
from babylon.infrastructure.terrain import (
    DefaultBiocapacityStore,
    DefaultTerrainClassifier,
)


@pytest.mark.unit
class TestProtocolCompliance:
    """Verify all 7 protocol implementations via isinstance()."""

    def test_terrain_classifier(self) -> None:
        """DefaultTerrainClassifier satisfies TerrainClassifier protocol."""

        class _MockReader:
            """Minimal mock to satisfy constructor."""

            def load_lakes(self, bbox: object) -> list[object]:
                return []

            def load_geography_regions(self, bbox: object) -> list[object]:
                return []

        defines = InfraTerrainDefines()
        classifier = DefaultTerrainClassifier(reader=_MockReader(), defines=defines)  # type: ignore[arg-type]
        assert isinstance(classifier, TerrainClassifier)

    def test_biocapacity_store(self) -> None:
        """DefaultBiocapacityStore satisfies BiocapacityStore protocol."""
        defines = InfraTerrainDefines()
        store = DefaultBiocapacityStore(defines=defines)
        assert isinstance(store, BiocapacityStore)

    def test_infrastructure_inventory(self) -> None:
        """DefaultInfrastructureInventory satisfies InfrastructureInventory protocol."""
        inventory = DefaultInfrastructureInventory()
        assert isinstance(inventory, InfrastructureInventory)

    def test_edge_capacity_calculator(self) -> None:
        """DefaultEdgeCapacityCalculator satisfies EdgeCapacityCalculator protocol."""
        defines = InfrastructureDefines()
        calculator = DefaultEdgeCapacityCalculator(defines=defines)
        assert isinstance(calculator, EdgeCapacityCalculator)

    def test_spatial_snapper(self) -> None:
        """DefaultSpatialSnapper satisfies SpatialSnapper protocol."""
        from babylon.infrastructure.snapping import DefaultSpatialSnapper

        class _MockReader:
            """Minimal mock to satisfy constructor."""

            def load_roads(self, bbox: object) -> list[object]:
                return []

            def load_railroads(self, bbox: object) -> list[object]:
                return []

            def load_airports(self, bbox: object) -> list[object]:
                return []

            def load_ports(self, bbox: object) -> list[object]:
                return []

        defines = InfrastructureDefines()
        snapper = DefaultSpatialSnapper(reader=_MockReader(), defines=defines)  # type: ignore[arg-type]
        assert isinstance(snapper, SpatialSnapper)

    def test_internet_access_manager(self) -> None:
        """DefaultInternetAccessManager satisfies InternetAccessManager protocol."""
        defines = InfraTerrainDefines()
        manager = DefaultInternetAccessManager(defines=defines)
        assert isinstance(manager, InternetAccessManager)

    def test_internet_field_operator(self) -> None:
        """DefaultInternetFieldOperator satisfies InternetFieldOperator protocol."""
        defines = InfraTerrainDefines()
        manager = DefaultInternetAccessManager(defines=defines)
        operator = DefaultInternetFieldOperator(manager=manager)
        assert isinstance(operator, InternetFieldOperator)
