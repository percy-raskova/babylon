"""Generic data loader utilities.

This package provides reusable components for building data loaders:

- DimensionLoader: Generic get-or-create pattern with caching for dimension tables
- BatchDimensionBuilder: Orchestrates multiple dimension loaders

Usage:
    from babylon.data.loaders import DimensionLoader

    loader = DimensionLoader(session, DimIndustry, "naics_code")
    loader.initialize_from_db()
    industry_id = loader.get_or_create(naics_code="11", naics_title="Agriculture")
"""

from babylon.data.loaders.dimension_loader import DimensionLoader

__all__ = ["DimensionLoader"]
