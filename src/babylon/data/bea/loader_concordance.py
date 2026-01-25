"""BEA-NAICS concordance loader for 3NF schema.

Loads the BEA-to-NAICS concordance from the official BEA Excel file into the
bridge_naics_bea table. This enables linking QCEW employment data (NAICS-based)
to BEA gross output/value added data for value tensor construction.

The concordance maps BEA industry codes to NAICS codes at multiple levels:
- Sector (~21 industries)
- Summary (~71 industries) - matches our GDP-by-industry data
- Underlying Summary (~138 industries)
- Detail (~402 industries)

Usage:
    from babylon.data.bea import BEAConcordanceLoader
    from babylon.data.normalize.database import get_normalized_session_factory

    loader = BEAConcordanceLoader()
    session_factory = get_normalized_session_factory()
    with session_factory() as session:
        stats = loader.load(session)
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from tqdm import tqdm

from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats
from babylon.data.normalize.schema import (
    BridgeNAICSBEA,
    DimBEAIndustry,
    DimIndustry,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Concordance file location
CONCORDANCE_FILE = "concordance/BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx"
CONCORDANCE_SHEET = "NAICS Codes"

# Data starts after headers
DATA_START_ROW = 5


def expand_naics_codes(naics_str: str) -> list[str]:
    """Expand NAICS code string to list of individual codes.

    Handles patterns like:
    - "1112" -> ["1112"]
    - "11111-2" -> ["11111", "11112"]
    - "11113-6, 11119" -> ["11113", "11114", "11115", "11116", "11119"]

    Args:
        naics_str: NAICS code string from concordance file.

    Returns:
        List of individual NAICS codes.
    """
    if not naics_str or naics_str.strip() == "":
        return []

    codes: list[str] = []

    # Split by comma first
    parts = [p.strip() for p in str(naics_str).split(",")]

    for part in parts:
        if not part:
            continue

        # Check for range pattern like "11111-2"
        range_match = re.match(r"^(\d+)-(\d+)$", part)
        if range_match:
            base = range_match.group(1)
            end_digit = range_match.group(2)
            # Generate range by replacing last N digits
            prefix = base[: -len(end_digit)]
            start = int(base[-len(end_digit) :])
            end = int(end_digit)
            for i in range(start, end + 1):
                codes.append(prefix + str(i).zfill(len(end_digit)))
        else:
            # Single code - strip any non-digit characters except leading zeros
            code = re.sub(r"[^\d]", "", str(part))
            if code:
                codes.append(code)

    return codes


def normalize_industry_name(name: str) -> str:
    """Normalize industry name for matching.

    Args:
        name: Industry name from either source.

    Returns:
        Normalized name (lowercase, stripped, reduced whitespace).
    """
    if not name:
        return ""
    # Lowercase, strip, reduce multiple spaces
    normalized = " ".join(name.lower().strip().split())
    return normalized


class BEAConcordanceLoader(DataLoader):
    """Loader for BEA-NAICS concordance into bridge table.

    Parses the official BEA concordance Excel file and creates mappings
    between DimIndustry (NAICS) and DimBEAIndustry records.

    The matching is done by industry name since our DimBEAIndustry uses
    synthetic codes (BEA001, etc.) from the GDP-by-industry tables.

    Attributes:
        config: LoaderConfig controlling operational settings.
        data_dir: Path to data directory containing concordance/.
    """

    def __init__(
        self,
        config: LoaderConfig | None = None,
        data_dir: Path | None = None,
    ) -> None:
        """Initialize concordance loader.

        Args:
            config: LoaderConfig for operational settings.
            data_dir: Path to data directory. Defaults to "data" in project root.
        """
        super().__init__(config)
        self.data_dir = data_dir if data_dir is not None else Path("data")

    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates."""
        return []  # No dimensions, only bridge table

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        return [BridgeNAICSBEA]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **_kwargs: object,
    ) -> LoadStats:
        """Load BEA-NAICS concordance into bridge table.

        Args:
            session: SQLAlchemy session for the normalized database.
            reset: If True, delete existing bridge data before loading.
            verbose: If True, print progress information.
            **_kwargs: Additional parameters (unused).

        Returns:
            LoadStats with counts of loaded records.
        """
        stats = LoadStats(source="bea_concordance")

        if verbose:
            print("Loading BEA-NAICS concordance...")

        try:
            # Clear existing bridge data if reset
            if reset:
                if verbose:
                    print("Clearing existing concordance data...")
                session.query(BridgeNAICSBEA).delete()
                session.commit()

            # Build lookup dictionaries
            bea_lookup = self._build_bea_lookup(session)
            naics_lookup = self._build_naics_lookup(session)

            if verbose:
                print(f"BEA industries available: {len(bea_lookup)}")
                print(f"NAICS industries available: {len(naics_lookup)}")

            # Parse concordance and create mappings
            mappings = self._parse_concordance(bea_lookup, naics_lookup, verbose)

            if verbose:
                print(f"Creating {len(mappings)} bridge records...")

            # Insert bridge records
            count = 0
            for industry_id, bea_industry_id, quality in tqdm(
                mappings, desc="Bridge records", disable=not verbose
            ):
                bridge = BridgeNAICSBEA(
                    industry_id=industry_id,
                    bea_industry_id=bea_industry_id,
                    mapping_quality=quality,
                )
                session.add(bridge)
                count += 1

                if count % 1000 == 0:
                    session.flush()

            session.commit()
            stats.facts_loaded["bridge_naics_bea"] = count
            stats.files_processed = 1

            if verbose:
                print(f"\n{stats}")

        except Exception as e:
            stats.errors.append(str(e))
            session.rollback()
            raise

        return stats

    def _build_bea_lookup(self, session: Session) -> dict[str, int]:
        """Build normalized name -> bea_industry_id lookup.

        Returns:
            Dictionary mapping normalized industry names to bea_industry_id.
        """
        lookup: dict[str, int] = {}
        bea_industries = session.query(DimBEAIndustry).all()

        for bea in bea_industries:
            normalized = normalize_industry_name(bea.industry_name)
            lookup[normalized] = bea.bea_industry_id

        return lookup

    def _build_naics_lookup(self, session: Session) -> dict[str, int]:
        """Build NAICS code -> industry_id lookup.

        Returns:
            Dictionary mapping NAICS codes to industry_id.
        """
        lookup: dict[str, int] = {}
        naics_industries = session.query(DimIndustry).all()

        for naics in naics_industries:
            if naics.naics_code:
                lookup[naics.naics_code] = naics.industry_id

        return lookup

    def _extract_industry_name(self, row: tuple[object, ...]) -> str | None:
        """Extract industry name from concordance row.

        Args:
            row: Row tuple from the worksheet.

        Returns:
            Industry name or None if not found.
        """
        for col in [4, 1, 2, 3]:
            if col < len(row) and row[col]:
                val = str(row[col]).strip()
                # Skip numeric codes (BEA codes are in other columns)
                if val and not val.replace(".", "").replace("-", "").isdigit():
                    return val
        return None

    def _find_naics_industry(
        self, naics_code: str, naics_lookup: dict[str, int]
    ) -> tuple[int | None, str]:
        """Find industry_id for NAICS code, with prefix fallback.

        Args:
            naics_code: NAICS code to look up.
            naics_lookup: NAICS code -> industry_id mapping.

        Returns:
            Tuple of (industry_id or None, mapping_quality).
        """
        # Try exact match first
        industry_id = naics_lookup.get(naics_code)
        if industry_id:
            return industry_id, "exact"

        # Try prefix matching (from longest to shortest)
        for prefix_len in range(len(naics_code) - 1, 1, -1):
            prefix = naics_code[:prefix_len]
            industry_id = naics_lookup.get(prefix)
            if industry_id:
                return industry_id, "aggregated"

        return None, "exact"

    def _parse_concordance(
        self,
        bea_lookup: dict[str, int],
        naics_lookup: dict[str, int],
        verbose: bool,
    ) -> list[tuple[int, int, str]]:
        """Parse concordance file and generate mappings.

        Args:
            bea_lookup: Normalized name -> bea_industry_id.
            naics_lookup: NAICS code -> industry_id.
            verbose: Print progress.

        Returns:
            List of (industry_id, bea_industry_id, mapping_quality) tuples.
        """
        import openpyxl  # type: ignore[import-untyped]

        filepath = self.data_dir / CONCORDANCE_FILE
        if not filepath.exists():
            raise FileNotFoundError(f"Concordance file not found: {filepath}")

        wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
        ws = wb[CONCORDANCE_SHEET]
        rows = list(ws.iter_rows(values_only=True))
        wb.close()

        mappings: list[tuple[int, int, str]] = []
        seen_pairs: set[tuple[int, int]] = set()
        current_bea_id: int | None = None
        unmatched_bea = 0
        unmatched_naics = 0

        for row in rows[DATA_START_ROW:]:
            if not row or all(c is None for c in row):
                continue

            # Update current BEA industry from name
            industry_name = self._extract_industry_name(row)
            if industry_name:
                normalized = normalize_industry_name(industry_name)
                bea_id = bea_lookup.get(normalized)
                if bea_id:
                    current_bea_id = bea_id
                else:
                    unmatched_bea += 1

            # Create mappings for NAICS codes in column 6
            naics_str = str(row[6]) if len(row) > 6 and row[6] else ""
            if not current_bea_id or not naics_str:
                continue

            for naics_code in expand_naics_codes(naics_str):
                industry_id, quality = self._find_naics_industry(naics_code, naics_lookup)
                if industry_id:
                    pair = (industry_id, current_bea_id)
                    if pair not in seen_pairs:
                        mappings.append((industry_id, current_bea_id, quality))
                        seen_pairs.add(pair)
                else:
                    unmatched_naics += 1

        if verbose:
            print(f"Unmatched BEA names: {unmatched_bea}")
            print(f"Unmatched NAICS codes: {unmatched_naics}")

        return mappings


__all__ = [
    "BEAConcordanceLoader",
    "expand_naics_codes",
]
