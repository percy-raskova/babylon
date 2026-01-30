"""ATUS Reference Data Loader for 3NF schema.

Loads BLS ATUS reproductive labor data from seed YAML into the normalized
3NF schema. This loader populates:
- dim_atus_activity_category: Activity code mappings
- fact_atus_reproductive_labor: National average hours per week

The data provides T³_v (reproductive labor hours) calibration coefficients
for Department III shadow labor calculations.

Usage:
    from babylon.data.atus import ATUSReferenceLoader
    from babylon.data.reference.database import get_normalized_session_factory

    loader = ATUSReferenceLoader()
    session_factory = get_normalized_session_factory()
    with session_factory() as session:
        stats = loader.load(session)

See Also:
    :mod:`babylon.data.atus.db_loader`: ATUSDBLoader reads this data.
    :mod:`babylon.economics.shadow_labor`: ShadowLaborService consumer.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from babylon.data.atus.mappings import ATUS_CODE_MAPPINGS
from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats
from babylon.data.loaders.dimension_loader import DimensionLoader
from babylon.data.reference.schema import (
    DimATUSActivityCategory,
    DimGender,
    FactATUSReproductiveLabor,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Default seed data path relative to this module
SEED_DATA_PATH = Path(__file__).parent / "seed_data.yaml"

# Conversion constant
DAILY_TO_WEEKLY = 7


class ATUSReferenceLoader(DataLoader):
    """Loader for ATUS reproductive labor reference data.

    Parses the seed_data.yaml file and loads activity category dimensions
    and fact values into the normalized schema.

    Attributes:
        config: LoaderConfig controlling operational settings.
        seed_data_path: Path to the seed YAML file.

    Example:
        loader = ATUSReferenceLoader()
        stats = loader.load(session, reset=True)
    """

    def __init__(
        self,
        config: LoaderConfig | None = None,
        seed_data_path: Path | None = None,
    ) -> None:
        """Initialize ATUS reference loader.

        Args:
            config: LoaderConfig for operational settings.
            seed_data_path: Path to seed YAML. Defaults to bundled seed_data.yaml.
        """
        super().__init__(config)
        self.seed_data_path = seed_data_path if seed_data_path is not None else SEED_DATA_PATH
        self._source_id: int | None = None
        self._category_cache: dict[str, int] = {}  # babylon_category -> category_id
        self._gender_cache: dict[str, int] = {}  # gender_code -> gender_id

    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates."""
        return [DimATUSActivityCategory]

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        return [FactATUSReproductiveLabor]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **_kwargs: object,
    ) -> LoadStats:
        """Load ATUS reference data into 3NF schema.

        Reads seed_data.yaml and populates dimension and fact tables with
        national average reproductive labor hours.

        Args:
            session: SQLAlchemy session for the normalized database.
            reset: If True, delete existing ATUS data before loading.
            verbose: If True, print progress information.
            **_kwargs: Additional parameters (unused).

        Returns:
            LoadStats with counts of loaded dimensions and facts.
        """
        stats = LoadStats(source="atus_reference")

        if verbose:
            logger.info("Loading ATUS reference data...")

        # Load seed data
        seed_data = self._load_seed_data()
        stats.files_processed = 1

        # Clear existing data if reset
        if reset:
            if verbose:
                logger.info("Clearing existing ATUS data...")
            self.clear_tables(session)
            session.flush()

        # Load data source dimension
        self._load_data_source(session, seed_data)
        stats.dimensions_loaded["dim_data_source"] = 1

        # Load activity category dimension from mappings
        category_count = self._load_activity_categories(session)
        stats.dimensions_loaded["dim_atus_activity_category"] = category_count

        # Ensure gender dimension exists
        self._ensure_genders(session)

        # Get year from seed data
        year = seed_data["metadata"]["source_year"]

        # Load fact data
        fact_count = self._load_reproductive_labor_facts(session, seed_data, year, verbose)
        stats.facts_loaded["fact_atus_reproductive_labor"] = fact_count

        session.commit()

        if verbose:
            logger.info(f"ATUS load complete: {stats}")

        return stats

    def _load_seed_data(self) -> dict[str, Any]:
        """Load and parse the seed YAML file.

        Returns:
            Parsed YAML data as dictionary.

        Raises:
            FileNotFoundError: If seed file doesn't exist.
            yaml.YAMLError: If YAML is malformed.
        """
        with open(self.seed_data_path) as f:
            data: dict[str, Any] = yaml.safe_load(f)
            return data

    def _load_data_source(self, session: Session, seed_data: dict[str, Any]) -> None:
        """Create or get the ATUS data source record.

        Args:
            session: SQLAlchemy session.
            seed_data: Parsed seed YAML.
        """
        metadata = seed_data["metadata"]

        self._source_id = self._get_or_create_data_source(
            session,
            source_code=metadata["source_code"],
            source_name=metadata["source_name"],
            source_url=metadata.get("source_url"),
            description=metadata.get("description"),
            source_agency=metadata.get("source_agency"),
            source_year=metadata.get("source_year"),
            coverage_start_year=metadata.get("coverage_start_year"),
            coverage_end_year=metadata.get("coverage_end_year"),
        )

    def _load_activity_categories(self, session: Session) -> int:
        """Load activity category dimension from mappings.

        Creates DimATUSActivityCategory records for each mapping defined
        in mappings.py.

        Args:
            session: SQLAlchemy session.

        Returns:
            Number of categories loaded.
        """
        loader = DimensionLoader(
            session=session,
            model_class=DimATUSActivityCategory,
            key_column="atus_code_prefix",
        )

        count = 0
        for mapping in ATUS_CODE_MAPPINGS:
            category_id = loader.get_or_create(
                atus_code_prefix=mapping.atus_code_prefix,
                atus_description=mapping.atus_description,
                babylon_category=mapping.babylon_category,
                major_category=mapping.major_category,
                is_reproductive=mapping.is_reproductive,
            )
            # Cache by babylon_category for fact loading
            self._category_cache[mapping.babylon_category] = category_id
            count += 1

        return count

    def _ensure_genders(self, session: Session) -> None:
        """Ensure required gender dimension records exist.

        Creates gender records if they don't exist. Caches gender_id values.

        Args:
            session: SQLAlchemy session.
        """
        gender_data = [
            ("T", "Total"),
            ("M", "Male"),
            ("F", "Female"),
        ]

        for gender_code, gender_label in gender_data:
            existing = session.query(DimGender).filter(DimGender.gender_code == gender_code).first()
            if existing:
                self._gender_cache[gender_code] = existing.gender_id
            else:
                gender = DimGender(gender_code=gender_code, gender_label=gender_label)
                session.add(gender)
                session.flush()
                self._gender_cache[gender_code] = gender.gender_id

    def _load_reproductive_labor_facts(
        self,
        session: Session,
        seed_data: dict[str, Any],
        year: int,
        verbose: bool,
    ) -> int:
        """Load reproductive labor fact records from seed data.

        Creates fact records for each category-gender combination with
        weekly hours converted from daily hours. Also creates occupation-
        disaggregated records using synthetic multipliers.

        Args:
            session: SQLAlchemy session.
            seed_data: Parsed seed YAML.
            year: Data year for time dimension.
            verbose: Print progress if True.

        Returns:
            Number of fact records loaded.
        """
        # Get or create time dimension for this year
        time_id = self._get_or_create_time(session, year)

        # Mapping from seed data gender keys to dimension codes
        gender_key_to_code = {
            "total": "T",
            "male": "M",
            "female": "F",
        }

        count = 0
        national_averages = seed_data["national_averages"]
        occupation_multipliers = seed_data.get("occupation_multipliers", {})

        for category_name, category_data in national_averages.items():
            # Get the first matching category_id (we aggregate at category level)
            category_id = self._get_category_id_for_babylon_category(session, category_name)
            if category_id is None:
                if verbose:
                    logger.warning(f"Skipping unmapped category: {category_name}")
                continue

            participation_rates = category_data.get("participation_rate", {})

            for gender_key, gender_code in gender_key_to_code.items():
                daily_hours = category_data.get(gender_key)
                if daily_hours is None:
                    continue

                # Convert daily to weekly
                base_weekly_hours = Decimal(str(daily_hours)) * DAILY_TO_WEEKLY

                # Get participation rate if available
                participation_rate = participation_rates.get(gender_key)
                if participation_rate is not None:
                    participation_rate = Decimal(str(participation_rate))

                gender_id = self._gender_cache[gender_code]

                # Create national average (occupation_group=NULL)
                fact = FactATUSReproductiveLabor(
                    category_id=category_id,
                    time_id=time_id,
                    gender_id=gender_id,
                    source_id=self._source_id,
                    hours_per_week=base_weekly_hours,
                    participation_rate=participation_rate,
                    sample_size=None,
                    occupation_group=None,
                    employment_status=None,
                )
                session.add(fact)
                count += 1

                # Create occupation-disaggregated records using multipliers
                for occ_group, occ_data in occupation_multipliers.items():
                    multipliers = occ_data.get("multipliers", {})
                    multiplier = multipliers.get(category_name, 1.0)

                    # Apply multiplier to base hours
                    occ_weekly_hours = base_weekly_hours * Decimal(str(multiplier))

                    occ_fact = FactATUSReproductiveLabor(
                        category_id=category_id,
                        time_id=time_id,
                        gender_id=gender_id,
                        source_id=self._source_id,
                        hours_per_week=occ_weekly_hours,
                        participation_rate=participation_rate,
                        sample_size=None,
                        occupation_group=occ_group,
                        employment_status=None,
                    )
                    session.add(occ_fact)
                    count += 1

        session.flush()
        return count

    def _get_category_id_for_babylon_category(
        self, session: Session, babylon_category: str
    ) -> int | None:
        """Get a single category_id for a babylon category.

        Since multiple ATUS codes map to the same babylon category,
        we return the first matching category_id for fact loading.

        Args:
            session: SQLAlchemy session.
            babylon_category: Babylon category name (e.g., "childcare").

        Returns:
            category_id or None if not found.
        """
        result = (
            session.query(DimATUSActivityCategory)
            .filter(DimATUSActivityCategory.babylon_category == babylon_category)
            .first()
        )
        return result.category_id if result else None


__all__ = [
    "ATUSReferenceLoader",
    "SEED_DATA_PATH",
]
