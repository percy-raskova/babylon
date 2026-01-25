"""Base class for ArcGIS Feature Service loaders with streaming checkpoint support.

Provides two-phase loading with page-level checkpoints:
1. Fetch phase: Stream features from ArcGIS to staging table with checkpoints
2. Aggregate phase: GROUP BY staging data and insert facts

This architecture enables resume capability for loaders that fetch 100k+ features
from ArcGIS services where complete data loss occurred on API failure.

Usage:
    class HIFLDPoliceLoader(ArcGISStreamingLoader):
        def _get_source_code(self) -> str:
            return "hifld_police"

        def _get_service_url(self) -> str:
            return "https://services1.arcgis.com/.../FeatureServer/0"

        def _map_feature_to_staging(self, feature, fips_lookup):
            # Map feature attributes to staging record
            ...

        def _aggregate_and_insert_facts(self, session, source_id):
            # GROUP BY staging, insert facts
            ...
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from tqdm import tqdm

from babylon.data.loader_base import DataLoader, LoadStats
from babylon.data.reference.schema import (
    DimCoerciveType,
    DimDataSource,
    FactCoerciveInfrastructure,
    IngestCheckpoint,
    StagingArcGISFeature,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from babylon.data.external.arcgis.client import ArcGISClient

logger = logging.getLogger(__name__)


# Default page size matches ArcGIS server limit
DEFAULT_PAGE_SIZE = 2000


class ArcGISStreamingLoader(DataLoader):
    """Abstract base class for ArcGIS loaders with two-phase checkpoint support.

    Implements streaming to staging table with page-level checkpoints,
    then aggregates staging data to final fact tables.

    Subclasses must implement:
        - _get_source_code(): Return source identifier for checkpoints
        - _get_service_url(): Return ArcGIS FeatureServer URL
        - _get_out_fields(): Return comma-separated field names to fetch
        - _map_feature_to_staging(): Convert feature to staging record dict
        - _aggregate_and_insert_facts(): Aggregate staging and insert facts

    Optional overrides:
        - _get_page_size(): Return page size (default 2000)
        - _setup_dimensions(): Create dimension records before loading
        - _clear_fact_data(): Clear existing fact data on reset
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize loader with dimension caches."""
        super().__init__(*args, **kwargs)
        self._fips_to_county: dict[str, int] = {}
        self._type_to_id: dict[str, int] = {}
        self._source_id: int | None = None
        self._client: ArcGISClient | None = None

    # -------------------------------------------------------------------------
    # Abstract Methods (must be implemented by subclasses)
    # -------------------------------------------------------------------------

    @abstractmethod
    def _get_source_code(self) -> str:
        """Return source code for checkpoints (e.g., 'hifld_police', 'mirta').

        This identifies the data source in the IngestCheckpoint and staging tables.
        """
        ...

    @abstractmethod
    def _get_service_url(self) -> str:
        """Return ArcGIS FeatureServer URL.

        Example: 'https://services1.arcgis.com/.../FeatureServer/0'
        """
        ...

    @abstractmethod
    def _get_out_fields(self) -> str:
        """Return comma-separated field names to fetch from ArcGIS.

        Example: 'OBJECTID,COUNTYFIPS,TYPE,NAME,CAPACITY'
        """
        ...

    @abstractmethod
    def _map_feature_to_staging(
        self, feature: Any, fips_lookup: dict[str, int]
    ) -> dict[str, Any] | None:
        """Convert ArcGIS feature to staging record dictionary.

        Args:
            feature: ArcGIS feature with object_id and attributes.
            fips_lookup: Map of county FIPS code -> county_id.

        Returns:
            Dict with keys: object_id, county_fips, type_code, capacity (optional).
            Return None to skip the feature (invalid FIPS, closed facility, etc).
        """
        ...

    @abstractmethod
    def _aggregate_and_insert_facts(self, session: Session, source_id: int) -> int:
        """Aggregate staging data and insert into fact tables.

        Uses SQL GROUP BY on staging table to produce county-level aggregates,
        then inserts into FactCoerciveInfrastructure or similar.

        Args:
            session: SQLAlchemy session.
            source_id: DimDataSource.source_id for the data source.

        Returns:
            Number of fact records inserted.
        """
        ...

    # -------------------------------------------------------------------------
    # Optional Overrides
    # -------------------------------------------------------------------------

    def _get_page_size(self) -> int:
        """Return page size for ArcGIS pagination (default 2000)."""
        return DEFAULT_PAGE_SIZE

    def _setup_dimensions(self, session: Session, verbose: bool) -> None:
        """Set up dimension tables before loading (override in subclass).

        Called before fetch phase. Use this to create DimCoerciveType records,
        DimDataSource, and build lookup caches.
        """
        pass

    def _clear_fact_data(self, session: Session, verbose: bool) -> None:
        """Clear existing fact data on reset (override in subclass).

        Called when reset=True before starting the load. Use this to delete
        fact records for this source's coercive types.
        """
        pass

    def _query_features(self, offset: int) -> Iterator[Any]:
        """Query features from ArcGIS starting at offset.

        Default implementation uses ArcGISClient. Override for testing.

        Note:
            The offset parameter is used by test mocks to simulate resumption.
            The real ArcGIS client always fetches all features (offset is for
            tracking progress, not filtering the API call).
        """
        # Import here to avoid circular dependency
        from babylon.data.external.arcgis.client import ArcGISClient

        # offset is used by subclass overrides; real client fetches all
        _ = offset  # Silence unused parameter warning

        if self._client is None:
            self._client = ArcGISClient(self._get_service_url())

        return self._client.query_all(
            out_fields=self._get_out_fields(),
        )

    def _get_total_count(self) -> int:
        """Get total feature count from ArcGIS (for progress bar)."""
        from babylon.data.external.arcgis.client import ArcGISClient

        if self._client is None:
            self._client = ArcGISClient(self._get_service_url())

        return self._client.get_record_count()

    # -------------------------------------------------------------------------
    # DataLoader Interface
    # -------------------------------------------------------------------------

    def get_dimension_tables(self) -> list[type]:
        """Return dimension tables (DimCoerciveType, DimDataSource)."""
        return [DimCoerciveType, DimDataSource]

    def get_fact_tables(self) -> list[type]:
        """Return fact tables (FactCoerciveInfrastructure)."""
        return [FactCoerciveInfrastructure]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **_kwargs: object,
    ) -> LoadStats:
        """Two-phase loading with page-level checkpoints.

        Phase 1 (Fetch): Stream features to staging table with checkpoints.
        Phase 2 (Aggregate): GROUP BY staging data, insert facts.

        Args:
            session: SQLAlchemy session.
            reset: If True, clear staging/checkpoints and start fresh.
            verbose: If True, show progress bars.
            **kwargs: Additional loader-specific parameters.

        Returns:
            LoadStats with counts of loaded staging features and facts.
        """
        source_code = self._get_source_code()
        stats = LoadStats(source=source_code)

        try:
            # Build county lookup
            self._fips_to_county = self._build_county_lookup(session)

            # Reset if requested
            if reset:
                self._clear_staging(session)
                self._clear_phase_checkpoints(session)
                self._clear_fact_data(session, verbose)
                session.flush()

            # Set up dimensions (creates type records, data source, etc.)
            self._setup_dimensions(session, verbose)
            session.flush()

            # Phase 1: Fetch to staging (resumable)
            if not self._is_fetch_complete(session):
                staging_count = self._fetch_phase(session, verbose)
                stats.facts_loaded["staging"] = staging_count

            # Phase 2: Aggregate and insert facts
            if not self._is_aggregate_complete(session):
                fact_count = self._aggregate_phase(session, verbose)
                stats.facts_loaded["facts"] = fact_count

            session.commit()

        except Exception as e:
            stats.record_api_error(e, context=f"{source_code}:load")
            stats.errors.append(str(e))
            session.rollback()
            raise

        finally:
            # Clean up client if we created one
            if hasattr(self, "_client") and self._client is not None:
                self._client.close()
                self._client = None

        return stats

    # -------------------------------------------------------------------------
    # Phase 1: Fetch to Staging
    # -------------------------------------------------------------------------

    def _fetch_phase(self, session: Session, verbose: bool) -> int:
        """Stream features to staging with page-level checkpoints.

        Returns number of features staged.
        """
        source_code = self._get_source_code()
        page_size = self._get_page_size()

        # Get last completed offset (for resume)
        last_offset = self._get_last_fetch_offset(session)

        # Get total count for progress bar
        total_count = self._get_total_count()

        if verbose:
            print(f"\nFetching {source_code} features (starting at offset {last_offset})...")

        # Query features from ArcGIS
        features = self._query_features(last_offset)
        feature_iter = tqdm(
            features,
            total=total_count,
            initial=last_offset,
            desc=source_code,
            disable=not verbose,
        )

        row_count = last_offset
        page_features: list[dict[str, Any]] = []
        skipped_no_fips = 0
        skipped_not_in_db = 0

        for feature in feature_iter:
            staging_record = self._map_feature_to_staging(feature, self._fips_to_county)

            if staging_record is None:
                # Feature was skipped (no FIPS or not in DB)
                if hasattr(feature, "attributes"):
                    attrs = feature.attributes
                    if not attrs.get("COUNTYFIPS"):
                        skipped_no_fips += 1
                    else:
                        skipped_not_in_db += 1
                continue

            # Add source_code to staging record
            staging_record["source_code"] = source_code
            page_features.append(staging_record)
            row_count += 1

            # Commit page when full
            if len(page_features) >= page_size:
                self._upsert_staging_batch(session, page_features)
                self._mark_fetch_checkpoint(session, row_count)
                session.commit()
                page_features = []

        # Commit remaining features
        if page_features:
            self._upsert_staging_batch(session, page_features)
            session.commit()

        # Mark fetch complete
        self._mark_fetch_complete(session, row_count)
        session.commit()

        new_features = row_count - last_offset
        if verbose:
            print(f"Staged {new_features} features")
            if skipped_no_fips or skipped_not_in_db:
                print(f"Skipped: {skipped_no_fips} no FIPS, {skipped_not_in_db} not in DB")

        return new_features

    def _upsert_staging_batch(self, session: Session, records: list[dict[str, Any]]) -> None:
        """Upsert batch of staging records using ON CONFLICT UPDATE.

        Uses SQLAlchemy's insert with on_conflict_do_update for deduplication.
        """
        if not records:
            return

        # Use dialect-appropriate upsert
        dialect = session.get_bind().dialect.name

        if dialect == "duckdb":
            # DuckDB: Use PostgreSQL-compatible ON CONFLICT (duckdb-engine is PG-like)
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            pg_stmt = pg_insert(StagingArcGISFeature).values(records)
            pg_stmt = pg_stmt.on_conflict_do_update(
                index_elements=["source_code", "object_id"],
                set_={
                    "county_fips": pg_stmt.excluded.county_fips,
                    "type_code": pg_stmt.excluded.type_code,
                    "capacity": pg_stmt.excluded.capacity,
                },
            )
            session.execute(pg_stmt)
        else:
            # SQLite: Use INSERT OR REPLACE
            sq_stmt = sqlite_insert(StagingArcGISFeature).values(records)
            sq_stmt = sq_stmt.on_conflict_do_update(
                index_elements=["source_code", "object_id"],
                set_={
                    "county_fips": sq_stmt.excluded.county_fips,
                    "type_code": sq_stmt.excluded.type_code,
                    "capacity": sq_stmt.excluded.capacity,
                },
            )
            session.execute(sq_stmt)

        session.flush()

    # -------------------------------------------------------------------------
    # Phase 2: Aggregate to Facts
    # -------------------------------------------------------------------------

    def _aggregate_phase(self, session: Session, verbose: bool) -> int:
        """Aggregate staging data and insert facts.

        Returns number of facts inserted.
        """
        source_code = self._get_source_code()

        if verbose:
            print(f"\nAggregating {source_code} facts...")

        # Ensure source_id is set
        if self._source_id is None:
            # Query for data source
            data_source = (
                session.query(DimDataSource)
                .filter(DimDataSource.source_code.like(f"{source_code.upper()}%"))
                .first()
            )
            if data_source:
                self._source_id = data_source.source_id
            else:
                # Create a default source using parent's method
                self._source_id = self._get_or_create_data_source(
                    session,
                    source_code=f"{source_code.upper()}_2024",
                    source_name=f"{source_code.replace('_', ' ').title()}",
                    source_agency="HIFLD/MIRTA",  # keyword arg
                    source_year=2024,  # keyword arg
                )

        # Call subclass implementation
        fact_count = self._aggregate_and_insert_facts(session, self._source_id)

        # Mark aggregate complete
        self._mark_aggregate_complete(session, fact_count)
        session.commit()

        if verbose:
            print(f"Inserted {fact_count} facts")

        return fact_count

    # -------------------------------------------------------------------------
    # Checkpoint Helpers
    # -------------------------------------------------------------------------

    def _clear_staging(self, session: Session) -> None:
        """Clear staging table for this source."""
        source_code = self._get_source_code()
        session.execute(
            delete(StagingArcGISFeature).where(StagingArcGISFeature.source_code == source_code)
        )
        session.flush()

    def _clear_phase_checkpoints(self, session: Session) -> None:
        """Clear phase checkpoints for this source."""
        source_code = self._get_source_code()
        session.execute(
            delete(IngestCheckpoint).where(
                IngestCheckpoint.source_code == source_code,
                IngestCheckpoint.state_fips == "00",  # Phase checkpoints use "00"
            )
        )
        session.flush()

    def _get_last_fetch_offset(self, session: Session) -> int:
        """Get last completed fetch offset from checkpoint."""
        source_code = self._get_source_code()

        checkpoint = (
            session.query(IngestCheckpoint)
            .filter(
                IngestCheckpoint.source_code == source_code,
                IngestCheckpoint.state_fips == "00",
                IngestCheckpoint.table_id.like("fetch:%"),
            )
            .order_by(IngestCheckpoint.row_count.desc())
            .first()
        )

        if checkpoint and checkpoint.table_id != "fetch:complete":
            return checkpoint.row_count

        return 0

    def _is_fetch_complete(self, session: Session) -> bool:
        """Check if fetch phase is complete."""
        source_code = self._get_source_code()

        checkpoint = (
            session.query(IngestCheckpoint)
            .filter(
                IngestCheckpoint.source_code == source_code,
                IngestCheckpoint.state_fips == "00",
                IngestCheckpoint.table_id == "fetch:complete",
            )
            .first()
        )

        return checkpoint is not None

    def _is_aggregate_complete(self, session: Session) -> bool:
        """Check if aggregate phase is complete."""
        source_code = self._get_source_code()

        checkpoint = (
            session.query(IngestCheckpoint)
            .filter(
                IngestCheckpoint.source_code == source_code,
                IngestCheckpoint.state_fips == "00",
                IngestCheckpoint.table_id == "agg:complete",
            )
            .first()
        )

        return checkpoint is not None

    def _mark_fetch_checkpoint(self, session: Session, row_count: int) -> None:
        """Mark fetch progress checkpoint."""
        source_code = self._get_source_code()
        self._mark_completed(
            session,
            source_code=source_code,
            year=0,
            state_fips="00",
            table_id=f"fetch:{row_count}",
            race_code="T",
            row_count=row_count,
        )

    def _mark_fetch_complete(self, session: Session, row_count: int) -> None:
        """Mark fetch phase as complete."""
        source_code = self._get_source_code()
        self._mark_completed(
            session,
            source_code=source_code,
            year=0,
            state_fips="00",
            table_id="fetch:complete",
            race_code="T",
            row_count=row_count,
        )

    def _mark_aggregate_complete(self, session: Session, fact_count: int) -> None:
        """Mark aggregate phase as complete."""
        source_code = self._get_source_code()
        self._mark_completed(
            session,
            source_code=source_code,
            year=0,
            state_fips="00",
            table_id="agg:complete",
            race_code="T",
            row_count=fact_count,
        )


__all__ = ["ArcGISStreamingLoader", "DEFAULT_PAGE_SIZE"]
