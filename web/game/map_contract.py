"""Single source of truth for the ``/map/`` metric contract (spec-109 A3).

Before this module existed the contract had three divergent copies:
``api.VALID_MAP_LAYERS`` advertised 11 layers, the map snapshot's
``metadata.available_metrics`` advertised 6, and the emitted feature
properties defined the truth. Requesting a lens for a never-emitted metric
(``consciousness``/``wealth``/``rent``/``biocapacity``) filtered features
down to no value key at all — a silently blank overlay, which Constitution
III.11 forbids.

The rule: **every name below is emitted as a numeric property on both hex-
and county-zoom ``/map/`` features** (``_hex_feature_properties`` /
``EngineBridge._aggregate_hex_features``), advertised via
``metadata.available_metrics``, and accepted by the API's ``lens`` filter.
A metric that is not actually emitted MUST NOT be listed. ``habitability``
joins this tuple when its ``hex_latest`` column + serializer projection land
(spec-109 A2).

Kept dependency-free so both ``api`` and ``engine_bridge`` can import it at
module level without Django/engine import weight.
"""

from __future__ import annotations

MAP_METRIC_PROPERTIES: tuple[str, ...] = (
    "profit_rate",
    "exploitation_rate",
    "occ",
    "imperial_rent",
    "heat",
    "org_presence",
    "population",
    # Spec-109 A2: MetabolismSystem's Sovereign-driven habitability, read
    # live off the graph node (Territory model excludes it — see
    # TERRITORY_EXCLUDED_FIELDS) and projected into hex_latest's JSONB
    # ``attributes`` column (no dedicated column needed).
    "habitability",
)
