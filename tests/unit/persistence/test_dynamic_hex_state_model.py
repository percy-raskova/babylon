"""Frozen-model and constraint tests for :class:`DynamicHexState` (T021)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from babylon.persistence.hex_state import DynamicHexState


def _valid_kwargs() -> dict[str, object]:
    return {
        "session_id": uuid4(),
        "tick": 0,
        "h3_index": "872d34a89ffffff",  # 15-char H3 res-7
        "county_fips": "26163",
        "state_fips": "26",
        "region_id": "east_north_central",
        "c": 10.0,
        "v": 5.0,
        "s": 3.0,
        "k": 100.0,
        "biocapacity_stock": 50.0,
        "energy_stock": 20.0,
        "raw_material_stock": 10.0,
        "internet_access_pct": 0.85,
        "surveillance_coupling": 0.4,
    }


@pytest.mark.cross_scale
class TestDynamicHexStateModel:
    def test_valid_construction(self) -> None:
        row = DynamicHexState(**_valid_kwargs())
        assert row.tick == 0
        assert row.h3_index == "872d34a89ffffff"

    def test_h3_index_length_enforced(self) -> None:
        kw = _valid_kwargs()
        kw["h3_index"] = "too_short"
        with pytest.raises(ValidationError):
            DynamicHexState(**kw)

    def test_county_fips_pattern(self) -> None:
        kw = _valid_kwargs()
        kw["county_fips"] = "ABCDE"
        with pytest.raises(ValidationError):
            DynamicHexState(**kw)

    def test_state_fips_pattern(self) -> None:
        kw = _valid_kwargs()
        kw["state_fips"] = "AB"
        with pytest.raises(ValidationError):
            DynamicHexState(**kw)

    def test_negative_value_substance_rejected(self) -> None:
        for field in ("c", "v", "s", "k"):
            kw = _valid_kwargs()
            kw[field] = -1.0
            with pytest.raises(ValidationError):
                DynamicHexState(**kw)

    def test_negative_substrate_stock_rejected(self) -> None:
        for field in ("biocapacity_stock", "energy_stock", "raw_material_stock"):
            kw = _valid_kwargs()
            kw[field] = -1.0
            with pytest.raises(ValidationError):
                DynamicHexState(**kw)

    def test_internet_access_pct_bounded_unit(self) -> None:
        kw = _valid_kwargs()
        kw["internet_access_pct"] = 1.5
        with pytest.raises(ValidationError):
            DynamicHexState(**kw)

    def test_surveillance_coupling_bounded_unit(self) -> None:
        kw = _valid_kwargs()
        kw["surveillance_coupling"] = -0.1
        with pytest.raises(ValidationError):
            DynamicHexState(**kw)

    def test_is_frozen(self) -> None:
        row = DynamicHexState(**_valid_kwargs())
        with pytest.raises(ValidationError):
            row.tick = 1  # type: ignore[misc]
