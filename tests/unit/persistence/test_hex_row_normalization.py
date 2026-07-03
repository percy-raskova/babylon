"""Unit tests for hex-row spatial-key normalization (spec-088 S3, FR-007).

The in-memory :class:`DynamicHexState` model keeps its required spatial
fields (the determinism-hash input and bridge logic are untouched); only
the SQL parameter layer (``_hex_row_dict``) stops writing them — the
``hex_map`` side table becomes the single stored copy.
"""

from __future__ import annotations

from uuid import UUID

from babylon.persistence.hex_state import DynamicHexState
from babylon.persistence.postgres_runtime._spec_062 import _hex_row_dict


def _row() -> DynamicHexState:
    return DynamicHexState(
        session_id=UUID("01234567-89ab-cdef-0123-456789abcdef"),
        tick=3,
        h3_index="872a91055ffffff",
        county_fips="26163",
        state_fips="26",
        region_id="midwest",
        c=1.0,
        v=2.0,
        s=3.0,
        k=4.0,
        biocapacity_stock=5.0,
        energy_stock=6.0,
        raw_material_stock=7.0,
        internet_access_pct=0.5,
        surveillance_coupling=0.25,
    )


class TestHexRowDictNormalization:
    def test_spatial_keys_write_null(self) -> None:
        """hex_map is the single stored copy of the immutable mapping."""
        params = _hex_row_dict(_row())
        assert params["county_fips"] is None
        assert params["state_fips"] is None
        assert params["region_id"] is None

    def test_value_payload_and_keys_unchanged(self) -> None:
        params = _hex_row_dict(_row())
        assert params["session_id"] == "01234567-89ab-cdef-0123-456789abcdef"
        assert params["tick"] == 3
        assert params["h3_index"] == "872a91055ffffff"
        assert params["c"] == 1.0
        assert params["k"] == 4.0
        assert params["surveillance_coupling"] == 0.25

    def test_in_memory_model_still_carries_spatial_keys(self) -> None:
        """Bridge/county logic and the hash input read the model, not SQL."""
        row = _row()
        assert row.county_fips == "26163"
        assert row.state_fips == "26"
        assert row.region_id == "midwest"
