"""External data sources package.

Contains modules for accessing external reality data:
- census: US Census Bureau ACS data
- fred: Federal Reserve Economic Data
- bls: Bureau of Labor Statistics

These modules will fetch real-world data to ground the simulation
in material reality.

See ai-docs/game-data.yaml for full documentation of data sources.

Submodules:
    base: Base classes and utilities for data ingestion
    census: Census Bureau data ingestion
    fred: Federal Reserve economic data ingestion
    bls: Bureau of Labor Statistics data ingestion
"""

from babylon.data.external.base import DataIngester, IngestResult

__all__ = ["DataIngester", "IngestResult"]
