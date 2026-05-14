"""Static FIPS state code → Census division mapping.

Used by the hex hydrator (spec-063 closure, 2026-05-14) to populate the
``DynamicHexState.region_id`` field. Maps 50 states + DC + 5 territories
to the 9 Census divisions per `data.census.gov <https://www.census.gov/
programs-surveys/cps/data/data-tables/geography.html>`_.

Michigan (FIPS 26) → "east_north_central" matches the quickstart_062
walkthrough precedent.

See Also:
    :class:`babylon.persistence.hex_state.DynamicHexState`
    ``specs/063-vol-ii-circulation/data-model.md`` §1.2 (DynamicHexState fields)
"""

from __future__ import annotations

# Census Bureau 9-division mapping (data.census.gov, 2024 vintage).
# Division IDs are lowercase snake_case to match downstream consumers.
STATE_FIPS_TO_CENSUS_DIVISION: dict[str, str] = {
    # ── Northeast ───────────────────────────────────────────────────────
    "09": "new_england",  # CT
    "23": "new_england",  # ME
    "25": "new_england",  # MA
    "33": "new_england",  # NH
    "44": "new_england",  # RI
    "50": "new_england",  # VT
    "34": "middle_atlantic",  # NJ
    "36": "middle_atlantic",  # NY
    "42": "middle_atlantic",  # PA
    # ── Midwest ─────────────────────────────────────────────────────────
    "17": "east_north_central",  # IL
    "18": "east_north_central",  # IN
    "26": "east_north_central",  # MI
    "39": "east_north_central",  # OH
    "55": "east_north_central",  # WI
    "19": "west_north_central",  # IA
    "20": "west_north_central",  # KS
    "27": "west_north_central",  # MN
    "29": "west_north_central",  # MO
    "31": "west_north_central",  # NE
    "38": "west_north_central",  # ND
    "46": "west_north_central",  # SD
    # ── South ───────────────────────────────────────────────────────────
    "10": "south_atlantic",  # DE
    "11": "south_atlantic",  # DC
    "12": "south_atlantic",  # FL
    "13": "south_atlantic",  # GA
    "24": "south_atlantic",  # MD
    "37": "south_atlantic",  # NC
    "45": "south_atlantic",  # SC
    "51": "south_atlantic",  # VA
    "54": "south_atlantic",  # WV
    "01": "east_south_central",  # AL
    "21": "east_south_central",  # KY
    "28": "east_south_central",  # MS
    "47": "east_south_central",  # TN
    "05": "west_south_central",  # AR
    "22": "west_south_central",  # LA
    "40": "west_south_central",  # OK
    "48": "west_south_central",  # TX
    # ── West ────────────────────────────────────────────────────────────
    "04": "mountain",  # AZ
    "08": "mountain",  # CO
    "16": "mountain",  # ID
    "30": "mountain",  # MT
    "32": "mountain",  # NV
    "35": "mountain",  # NM
    "49": "mountain",  # UT
    "56": "mountain",  # WY
    "02": "pacific",  # AK
    "06": "pacific",  # CA
    "15": "pacific",  # HI
    "41": "pacific",  # OR
    "53": "pacific",  # WA
    # ── Territories ─────────────────────────────────────────────────────
    "60": "territory",  # American Samoa
    "66": "territory",  # Guam
    "69": "territory",  # Northern Mariana Islands
    "72": "territory",  # Puerto Rico
    "78": "territory",  # US Virgin Islands
}
"""Read-only static table. 56 entries cover the 50 states + DC + 5
territories that LODES/QCEW/TIGER datasets canonically enumerate."""


def region_for_state_fips(state_fips: str) -> str:
    """Return the Census-division identifier for a 2-digit FIPS state code.

    Args:
        state_fips: 2-character zero-padded FIPS state code (e.g., ``"26"``).

    Returns:
        Lowercase snake_case Census division identifier (e.g.,
        ``"east_north_central"``). Returns ``"unknown"`` for codes outside
        the canonical FIPS-55 set (defensive default).
    """
    return STATE_FIPS_TO_CENSUS_DIVISION.get(state_fips, "unknown")


__all__ = ["STATE_FIPS_TO_CENSUS_DIVISION", "region_for_state_fips"]
