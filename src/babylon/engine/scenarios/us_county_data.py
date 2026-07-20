"""Committed county-seed artifact loader for USScenario (Amendment U / #39 T4).

``USScenario`` needs real per-county population + geography to re-key its
territories from res-3 H3 hexes to counties, but the scenario builder must
stay reference-DB-free at build/test time (deterministic-data-artifacts
doctrine: CI never touches the data drive; measured cost of a live national-
scope population query was ~6.6s, unaffordable at the >130 call sites across
the test suite that build a ``"default"``/``"us_nationwide"`` scenario). This
module reads the committed, hash-stamped
``src/babylon/data/game/us_county_territories.json`` -- precomputed offline by
``tools/generate_us_county_territories.py`` -- mirroring the
``business_seeds.py`` / ``business_seeds.json`` pattern used for the same
class of problem (real QCEW business-seed data, ADR086).

Only the raw reference-derived fields are baked into the artifact (fips,
county_name, state_abbrev, centroid lat/lon, population,
raw_material_value_millions -- #39 T6, schema_version 2); the pure in-memory
sector/rent/biocapacity/region classification stays runtime logic in
``_legacy.py`` (no DB access needed for it). Missing fields are explicit
``null`` in the artifact, with reasons recorded in its ``gaps`` list --
:func:`babylon.engine.scenarios._legacy._create_us_territories` handles them
with a documented loud-skip-to-baseline policy, never a fabricated default.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

#: Committed seed artifact (mirrors business_seeds.py's data-dir pattern:
#: ``<pkg>/data/game/<file>.json``).
ARTIFACT_PATH = Path(__file__).resolve().parents[2] / "data" / "game" / "us_county_territories.json"

#: The schema_version this loader (and _legacy.py's consumer) understands.
#: Bumped to 2 at #39 T6 (raw_material_value_millions added). content_hash
#: alone cannot catch a stale/mismatched schema_version -- it's computed the
#: same way regardless of version, so it stays self-consistent even over a
#: stale v1 artifact (#39 T6 M1 / LOW-2).
_EXPECTED_SCHEMA_VERSION: int = 2

__all__ = ["ARTIFACT_PATH", "load_county_data"]


def _verify_schema_version(data: dict[str, Any]) -> None:
    """Loud failure (Constitution III.11) on a stale/mismatched artifact schema.

    Raises:
        ValueError: the stamped ``schema_version`` does not match
            :data:`_EXPECTED_SCHEMA_VERSION` -- the artifact predates (or is
            newer than) a field this loader's consumer expects.
    """
    actual = data.get("schema_version")
    if actual != _EXPECTED_SCHEMA_VERSION:
        raise ValueError(
            f"{ARTIFACT_PATH.name} schema_version mismatch: expected "
            f"{_EXPECTED_SCHEMA_VERSION}, got {actual!r} -- regenerate via "
            "tools/generate_us_county_territories.py"
        )


def _verify_content_hash(data: dict[str, Any]) -> None:
    """Loud failure (Constitution III.11) on a tampered/stale artifact.

    Raises:
        ValueError: the stamped ``content_hash`` doesn't match the recomputed
            SHA-256 over ``counties`` -- the file was hand-edited or only
            partially regenerated.
    """
    canonical = json.dumps(data["counties"], sort_keys=True, separators=(",", ":"))
    recomputed = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if recomputed != data["content_hash"]:
        raise ValueError(
            f"{ARTIFACT_PATH.name} content_hash mismatch: stamped="
            f"{data['content_hash'][:16]}... recomputed={recomputed[:16]}... "
            "-- regenerate via tools/generate_us_county_territories.py"
        )


@lru_cache(maxsize=1)
def load_county_data() -> dict[str, Any]:
    """Load and cache the committed county-seed artifact.

    Returns:
        The parsed artifact payload (``schema_version``, ``source``,
        ``content_hash``, ``counties``, ``gaps``).

    Raises:
        FileNotFoundError: If the artifact is missing (regenerate with
            ``tools/generate_us_county_territories.py``).
        json.JSONDecodeError: If the artifact is not valid JSON.
        ValueError: If the stamped ``schema_version`` does not match
            :data:`_EXPECTED_SCHEMA_VERSION`, or the stamped ``content_hash``
            doesn't match the recomputed hash over ``counties``.
    """
    data = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    _verify_schema_version(data)
    _verify_content_hash(data)
    return data  # type: ignore[no-any-return]
