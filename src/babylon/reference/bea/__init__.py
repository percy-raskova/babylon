"""BEA national-economic-accounts subsystem.

Owns the BEA I-O reference data: fact_bea_national_industry,
fact_bea_io_coefficient, and bridge_naics_bea. Per constitution II.11
(Subsystem Table Ownership), cross-subsystem reads MUST go through
the BEAShareLookupService Protocol exported here.

Spec: 068-bea-national-io-ingest.
"""

from __future__ import annotations

__all__: list[str] = []
