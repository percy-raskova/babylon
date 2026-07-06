"""Unit tests for the NAICS sector-code expansion helper (spec-098 adapter fix).

Pure-function coverage of ``_sector_codes_for``, which maps the adapter's
2-digit NAICS labels to the ``dim_industry.sector_code`` values used to
aggregate the post-spec-086 6-digit QCEW leaves.
"""

from __future__ import annotations

import pytest

from babylon.economics.throughput.adapters import (
    NAICS_2DIGIT_SECTORS,
    _sector_codes_for,
)

pytestmark = pytest.mark.unit


class TestSectorCodeExpansion:
    def test_plain_sector_maps_to_itself(self) -> None:
        assert _sector_codes_for("52") == ["52"]
        assert _sector_codes_for("92") == ["92"]

    def test_combined_labels_expand_to_components(self) -> None:
        assert _sector_codes_for("31-33") == ["31", "32", "33"]
        assert _sector_codes_for("44-45") == ["44", "45"]
        assert _sector_codes_for("48-49") == ["48", "49"]

    def test_unknown_label_passes_through(self) -> None:
        # An unknown code expands to itself; the DB join then matches no rows.
        assert _sector_codes_for("XX") == ["XX"]

    def test_every_adapter_label_expands_to_two_digit_codes(self) -> None:
        for label in NAICS_2DIGIT_SECTORS:
            codes = _sector_codes_for(label)
            assert codes, f"{label} expanded to nothing"
            assert all(len(c) == 2 and c.isdigit() for c in codes), (
                f"{label} -> {codes} produced a non-2-digit sector code"
            )
