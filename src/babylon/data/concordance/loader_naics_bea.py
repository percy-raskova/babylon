"""NAICS to BEA industry concordance loader for 3NF schema.

Loads the BEA Industry-NAICS concordance from an Excel file into the
bridge_naics_bea table, enabling linkage between QCEW employment data
(NAICS-based) and BEA GDP data.

The concordance file maps BEA Detail codes to NAICS codes. Since our
DimBEAIndustry contains Summary-level industries, we trace each Detail
row back to its parent Summary code for mapping.

Usage:
    from babylon.data.concordance import NAICSBEAConcordanceLoader
    from babylon.data.reference.database import get_normalized_session_factory

    loader = NAICSBEAConcordanceLoader()
    session_factory = get_normalized_session_factory()
    with session_factory() as session:
        stats = loader.load(session)
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd  # type: ignore[import-untyped]
from tqdm import tqdm

from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats
from babylon.data.reference.schema import (
    BridgeNAICSBEA,
    DimBEAIndustry,
    DimIndustry,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Default data directory relative to project root
DEFAULT_DATA_DIR = Path("data")

# Concordance filename
CONCORDANCE_FILE = "BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx"


def expand_naics_codes(naics_str: str | None) -> list[str]:
    """Expand NAICS code patterns into individual codes.

    Handles patterns like:
    - Single codes: "1112"
    - Ranges: "11111-2" (means 11111, 11112)
    - Comma-separated: "11113-6, 11119"
    - Complex: "1122, 1124-5, 1129"

    Args:
        naics_str: NAICS code pattern string from concordance.

    Returns:
        List of individual NAICS code strings.
    """
    if naics_str is None or pd.isna(naics_str) or not str(naics_str).strip():
        return []

    codes: list[str] = []
    for part in str(naics_str).split(","):
        part = part.strip()
        if "-" in part:
            # Range like '11111-2' means 11111, 11112
            match = re.match(r"(\d+)-(\d+)", part)
            if match:
                base = match.group(1)
                suffix = match.group(2)
                # The suffix replaces last N digits where N = len(suffix)
                prefix = base[: -len(suffix)]
                start = int(base[-len(suffix) :])
                end = int(suffix)
                for i in range(start, end + 1):
                    codes.append(prefix + str(i).zfill(len(suffix)))
        else:
            codes.append(part)
    return codes


class NAICSBEAConcordanceLoader(DataLoader):
    """Loader for NAICS-BEA industry concordance into 3NF schema.

    Parses the BEA Excel concordance file and creates bridge records
    linking DimIndustry (NAICS codes) to DimBEAIndustry.

    Attributes:
        config: LoaderConfig controlling operational settings.
        data_dir: Path to data directory containing concordance/.

    Example:
        loader = NAICSBEAConcordanceLoader()
        stats = loader.load(session, reset=True)
    """

    def __init__(
        self,
        config: LoaderConfig | None = None,
        data_dir: Path | None = None,
    ) -> None:
        """Initialize NAICS-BEA concordance loader.

        Args:
            config: LoaderConfig for operational settings.
            data_dir: Path to data directory. Defaults to "data" in project root.
        """
        super().__init__(config)
        self.data_dir = data_dir if data_dir is not None else DEFAULT_DATA_DIR

    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates."""
        return []  # Bridge table only

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        return []  # Bridge table, not a fact

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **_kwargs: object,
    ) -> LoadStats:
        """Load NAICS-BEA concordance into bridge table.

        Args:
            session: SQLAlchemy session for the normalized database.
            reset: If True, delete existing bridge data before loading.
            verbose: If True, print progress information.
            **_kwargs: Additional parameters (unused).

        Returns:
            LoadStats with counts of loaded bridge records.
        """
        stats = LoadStats(source="naics_bea_concordance")

        if verbose:
            print("Loading NAICS-BEA concordance...")

        try:
            # Check prerequisites
            naics_count = session.query(DimIndustry).count()
            if naics_count == 0:
                stats.errors.append("DimIndustry is empty - run QCEWLoader first")
                return stats

            bea_count = session.query(DimBEAIndustry).count()
            if bea_count == 0:
                stats.errors.append("DimBEAIndustry is empty - run BEANationalLoader first")
                return stats

            # Find concordance file
            concordance_path = self.data_dir / "concordance" / CONCORDANCE_FILE
            if not concordance_path.exists():
                stats.errors.append(f"Concordance file not found: {concordance_path}")
                return stats

            # Clear existing data if reset
            if reset:
                if verbose:
                    print("Clearing existing bridge data...")
                session.query(BridgeNAICSBEA).delete()
                session.commit()

            # Build lookup caches
            bea_by_name = self._build_bea_name_cache(session)
            naics_to_id = self._build_naics_cache(session)

            if verbose:
                print(f"  BEA industries: {len(bea_by_name)}")
                print(f"  NAICS industries: {len(naics_to_id)}")

            # Parse concordance and create bridge records
            bridge_count = self._load_concordance(
                session, concordance_path, bea_by_name, naics_to_id, verbose
            )

            stats.dimensions_loaded["bridge_naics_bea"] = bridge_count
            stats.files_processed = 1

            session.commit()

            if verbose:
                print(f"\n{stats}")

        except Exception as e:
            stats.errors.append(str(e))
            session.rollback()
            raise

        return stats

    def _build_bea_name_cache(self, session: Session) -> dict[str, tuple[int, int]]:
        """Build BEA industry name -> (bea_industry_id, line_number) cache."""
        industries = session.query(
            DimBEAIndustry.bea_industry_id,
            DimBEAIndustry.industry_name,
            DimBEAIndustry.line_number,
        ).all()
        return {name.lower().strip(): (bea_id, line_num) for bea_id, name, line_num in industries}

    def _build_naics_cache(self, session: Session) -> dict[str, int]:
        """Build NAICS code -> industry_id cache."""
        industries = session.query(DimIndustry.industry_id, DimIndustry.naics_code).all()
        return {naics: ind_id for ind_id, naics in industries}

    def _load_concordance(
        self,
        session: Session,
        concordance_path: Path,
        bea_by_name: dict[str, tuple[int, int]],
        naics_to_id: dict[str, int],
        verbose: bool,
    ) -> int:
        """Parse concordance Excel and create bridge records.

        Args:
            session: SQLAlchemy session.
            concordance_path: Path to Excel concordance file.
            bea_by_name: BEA industry name -> (id, line_number) mapping.
            naics_to_id: NAICS code -> industry_id mapping.
            verbose: Enable progress output.

        Returns:
            Number of bridge records created.
        """
        # Read concordance Excel
        df = pd.read_excel(concordance_path, sheet_name="NAICS Codes", skiprows=4)
        df.columns = [
            "Sector",
            "Summary",
            "U_Summary",
            "Detail",
            "Industry_Title",
            "Notes",
            "NAICS_Codes",
        ]

        # Build Summary code -> BEA mapping
        # For Summary rows, the industry name is in U_Summary column
        summary_to_bea: dict[str, tuple[int, int]] = {}
        summary_rows = df[df["Summary"].notna() & df["Sector"].isna()]

        for _, row in summary_rows.iterrows():
            bea_code = str(row["Summary"]).strip()
            name = str(row["U_Summary"]).lower().strip() if pd.notna(row["U_Summary"]) else ""
            if name in bea_by_name:
                summary_to_bea[bea_code] = bea_by_name[name]

        if verbose:
            print(f"  Matched {len(summary_to_bea)} BEA summary codes")

        # Process Detail rows to create bridge mappings
        current_summary: str | None = None
        count = 0
        skipped_no_summary = 0
        skipped_no_naics = 0

        row_iter = tqdm(df.iterrows(), total=len(df), desc="Concordance", disable=not verbose)

        for _idx, row in row_iter:
            # Update current Summary when we see a Summary row
            if pd.notna(row["Summary"]) and pd.isna(row["Sector"]):
                current_summary = str(row["Summary"]).strip()

            # Process Detail rows with NAICS codes
            if pd.notna(row["Detail"]) and pd.notna(row["NAICS_Codes"]):
                if current_summary is None or current_summary not in summary_to_bea:
                    skipped_no_summary += 1
                    continue

                bea_id, _ = summary_to_bea[current_summary]
                naics_codes = expand_naics_codes(row["NAICS_Codes"])

                for naics in naics_codes:
                    if naics not in naics_to_id:
                        skipped_no_naics += 1
                        continue

                    bridge = BridgeNAICSBEA(
                        industry_id=naics_to_id[naics],
                        bea_industry_id=bea_id,
                        mapping_quality="exact",
                        weight=None,
                    )
                    session.add(bridge)
                    count += 1

                    if count % 100 == 0:
                        session.flush()

        session.flush()

        if verbose:
            if skipped_no_summary > 0:
                print(f"  Skipped {skipped_no_summary} rows - no matching BEA summary")
            if skipped_no_naics > 0:
                print(f"  Skipped {skipped_no_naics} NAICS codes - not in DimIndustry")

        return count


__all__ = [
    "NAICSBEAConcordanceLoader",
    "expand_naics_codes",
]
