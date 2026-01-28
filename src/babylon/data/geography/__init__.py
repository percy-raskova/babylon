"""Geographic hierarchy data loading infrastructure.

Provides loaders for populating DimGeographicHierarchy with state-to-county
allocation weights derived from Census population and QCEW employment data.
"""

from babylon.data.geography.loader import GeographicHierarchyLoader

__all__ = ["GeographicHierarchyLoader"]
