"""ATUS (American Time Use Survey) data loading infrastructure.

This package provides data loading infrastructure for reproductive labor
hours from the American Time Use Survey (ATUS). These hours feed into
the shadow labor calculations in Department III.

**Package Contents:**

Models:
    - ATUSActivityRecord: Single time diary entry
    - ATUSHouseholdSummary: Aggregated reproductive labor hours

Protocol:
    - ReproductionLoaderProtocol: Abstract base class for data loaders

Loaders:
    - MockReproductionLoader: Mock data for testing (national averages)
    - ATUSReferenceLoader: DataLoader for ETL from seed data to database
    - ATUSDBLoader: Protocol implementation querying database

Mappings:
    - ATUSActivityMapping: Dataclass for code-to-category mapping
    - ATUS_CODE_MAPPING: Dict of ATUS codes to Babylon categories
    - get_babylon_category: Helper to map ATUS codes

**Data Flow:**

    seed_data.yaml -> ATUSReferenceLoader -> Database -> ATUSDBLoader -> ShadowLaborService

**Usage Examples:**

Mock data (for testing):

    >>> from babylon.data.atus import MockReproductionLoader
    >>> loader = MockReproductionLoader()
    >>> summary = loader.load_county_summary("06001", 2022)
    >>> summary.unpaid_care_hours_weekly
    21.0

Database-backed (for production):

    >>> from babylon.data.atus import ATUSReferenceLoader, create_atus_loader
    >>> from babylon.data.reference.database import get_normalized_session_factory
    >>> # First, load reference data
    >>> session_factory = get_normalized_session_factory()
    >>> with session_factory() as session:
    ...     ref_loader = ATUSReferenceLoader()
    ...     stats = ref_loader.load(session)
    ...     # Then use the DB loader
    ...     db_loader = create_atus_loader(session, use_database=True)
    ...     summary = db_loader.load_county_summary("06001", 2022)

See Also:
    :mod:`babylon.economics.shadow_labor`: Shadow labor service.
    :mod:`babylon.economics.reproduction`: Imperial rent calculation.
"""

from babylon.data.atus.db_loader import ATUSDBLoader, create_atus_db_loader
from babylon.data.atus.loader import SEED_DATA_PATH, ATUSReferenceLoader
from babylon.data.atus.mappings import (
    ATUS_CODE_MAPPING,
    ATUS_CODE_MAPPINGS,
    BABYLON_CATEGORIES,
    BABYLON_OCCUPATION_GROUPS,
    OCCUPATION_GROUP_MAPPINGS,
    SOC_TO_OCCUPATION_GROUP,
    ATUSActivityMapping,
    OccupationGroupMapping,
    get_babylon_category,
    get_mapping,
    get_occupation_group,
)
from babylon.data.atus.mock_loader import (
    NATIONAL_AVG_UNPAID_CARE_WEEKLY,
    REPLACEMENT_COST_HOURLY,
    MockReproductionLoader,
)
from babylon.data.atus.models import (
    ATUSActivityRecord,
    ATUSHouseholdSummary,
    VisibilityDecomposition,
)
from babylon.data.atus.protocol import ReproductionLoaderProtocol
from babylon.data.atus.visibility import DataSourceUnavailableError, VisibilityComputer


def create_atus_loader(
    session: object | None = None,
    defines: object | None = None,
    use_database: bool = False,
) -> ReproductionLoaderProtocol:
    """Factory function to create appropriate ATUS loader.

    Creates either a MockReproductionLoader (default) or ATUSDBLoader
    depending on configuration.

    Args:
        session: SQLAlchemy session (required if use_database=True).
        defines: GameDefines for configuration.
        use_database: If True, return ATUSDBLoader; else MockReproductionLoader.

    Returns:
        ReproductionLoaderProtocol implementation.

    Raises:
        ValueError: If use_database=True but session is None.

    Example:
        >>> loader = create_atus_loader()  # Mock loader
        >>> loader = create_atus_loader(session, use_database=True)  # DB loader
    """
    if use_database:
        if session is None:
            msg = "session is required when use_database=True"
            raise ValueError(msg)
        return create_atus_db_loader(session, defines)  # type: ignore[arg-type]
    return MockReproductionLoader()


__all__ = [
    # Models
    "ATUSActivityRecord",
    "ATUSHouseholdSummary",
    "VisibilityDecomposition",
    # Protocol
    "ReproductionLoaderProtocol",
    # Visibility computation (Feature 005)
    "VisibilityComputer",
    "DataSourceUnavailableError",
    # Mock implementation
    "MockReproductionLoader",
    # Database loaders
    "ATUSReferenceLoader",
    "ATUSDBLoader",
    # Factory functions
    "create_atus_loader",
    "create_atus_db_loader",
    # Activity Mappings
    "ATUSActivityMapping",
    "ATUS_CODE_MAPPING",
    "ATUS_CODE_MAPPINGS",
    "BABYLON_CATEGORIES",
    "get_babylon_category",
    "get_mapping",
    # Occupation Group Mappings
    "OccupationGroupMapping",
    "OCCUPATION_GROUP_MAPPINGS",
    "BABYLON_OCCUPATION_GROUPS",
    "SOC_TO_OCCUPATION_GROUP",
    "get_occupation_group",
    # Constants
    "NATIONAL_AVG_UNPAID_CARE_WEEKLY",
    "REPLACEMENT_COST_HOURLY",
    "SEED_DATA_PATH",
]
