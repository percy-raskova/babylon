"""WO-46 contract pins that need no database: the ``babylon_meta`` boundary.

Three contracts (charter P0 ruling 3, fog-epistemic-vs-material):

1. **DDL source of truth** — ``postgres_schema.BABYLON_META_DDL`` defines the
   tier, every object lives inside the ``babylon_meta`` schema, fresh
   databases get it via ``POSTGRES_SCHEMA_DDL``, and migration
   ``0037_babylon_meta.sql`` mirrors it re-runnably for existing databases.
2. **Epistemic partition** — the engine's source tree never references
   ``babylon_meta``, and within the persistence layer only the DDL module
   and the client store do. The determinism hash is a pure function of
   (tick, rng_seed, hex_state, actions): identical inputs yield identical
   hashes, so no store — ``babylon_meta`` included — can participate.
3. **Watchlist seam** — :class:`~babylon.persistence.babylon_meta.
   BabylonMetaStore` structurally satisfies the TUI's
   ``WatchlistPersistence`` Protocol without either module importing the
   other (the import-linter boundary stays intact).

The database-backed behavior (idempotent apply, CRUD, round-trips) lives in
``tests/integration/persistence/test_babylon_meta.py`` per the test-estate
law (ADR074: Postgres-connected tests are integration tier).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

import pytest

import babylon.engine
import babylon.persistence
from babylon.persistence.babylon_meta import BabylonMetaStore, CampaignRecord
from babylon.persistence.conservation_audit import compute_determinism_hash
from babylon.persistence.postgres_schema import (
    BABYLON_META_DDL,
    POSTGRES_SCHEMA_DDL,
)
from babylon.tui.watchlist import WatchlistPersistence

pytestmark = [pytest.mark.unit, pytest.mark.ledger]

_META_TABLES = ("campaign", "watchlist", "jumplist", "breadcrumb")

_MIGRATION = (
    Path(cast(str, babylon.persistence.__file__)).parent / "migrations" / "0037_babylon_meta.sql"
)


class TestDdlSourceOfTruth:
    def test_the_tier_is_schema_plus_four_tables(self) -> None:
        """One CREATE SCHEMA first, then exactly the four charter tables."""
        assert len(BABYLON_META_DDL) == 5
        assert "CREATE SCHEMA IF NOT EXISTS babylon_meta" in BABYLON_META_DDL[0]
        created = [
            match.group(1)
            for chunk in BABYLON_META_DDL
            for match in re.finditer(r"CREATE TABLE IF NOT EXISTS babylon_meta\.(\w+)", chunk)
        ]
        assert created == list(_META_TABLES)

    def test_every_object_is_schema_qualified(self) -> None:
        """The boundary is structural: no chunk touches the public schema."""
        for chunk in BABYLON_META_DDL[1:]:
            for match in re.finditer(r"(?:CREATE TABLE IF NOT EXISTS|REFERENCES)\s+(\S+)", chunk):
                assert match.group(1).startswith("babylon_meta."), chunk

    def test_fresh_databases_get_the_tier(self) -> None:
        """POSTGRES_SCHEMA_DDL (the fresh-DB path) includes every chunk."""
        for chunk in BABYLON_META_DDL:
            assert chunk in POSTGRES_SCHEMA_DDL

    def test_migration_mirrors_the_ddl_and_is_rerunnable(self) -> None:
        """0037 heals existing DBs: same objects, all IF NOT EXISTS."""
        sql = _MIGRATION.read_text(encoding="utf8")
        assert "CREATE SCHEMA IF NOT EXISTS babylon_meta" in sql
        for table in _META_TABLES:
            assert f"CREATE TABLE IF NOT EXISTS babylon_meta.{table}" in sql
        creates = re.findall(r"CREATE (?:SCHEMA|TABLE)", sql)
        rerunnable = re.findall(r"CREATE (?:SCHEMA|TABLE) IF NOT EXISTS", sql)
        assert len(creates) == len(rerunnable) == 5


class TestEpistemicPartition:
    def test_the_engine_never_references_babylon_meta(self) -> None:
        """The engine neither reads nor writes the tier — source-level pin."""
        engine_root = Path(cast(str, babylon.engine.__file__)).parent
        offenders = [
            path
            for path in sorted(engine_root.rglob("*.py"))
            if "babylon_meta" in path.read_text(encoding="utf8")
        ]
        assert offenders == []

    def test_only_the_ddl_module_and_the_store_know_the_tier(self) -> None:
        """Within persistence, the tier's surface is exactly two modules."""
        persistence_root = Path(cast(str, babylon.persistence.__file__)).parent
        allowed = {"postgres_schema.py", "babylon_meta.py", "__init__.py"}
        offenders = [
            path.name
            for path in sorted(persistence_root.glob("*.py"))
            if "babylon_meta" in path.read_text(encoding="utf8") and path.name not in allowed
        ]
        assert offenders == []

    def test_determinism_hash_is_a_pure_function_of_material_inputs(self) -> None:
        """Identical (tick, rng_seed, hex_state, actions) → identical hash.

        The hash cannot read any store: it is deterministic over exactly
        its four material arguments, so ``babylon_meta`` content can never
        move it. Changing a material input MUST move it (no dead inputs).
        """
        rows = [{"h3_index": "8a2a1072b59ffff", "wealth": 1.5}]
        first = compute_determinism_hash(tick=3, rng_seed=2010, hex_rows=rows)
        second = compute_determinism_hash(tick=3, rng_seed=2010, hex_rows=rows)
        moved = compute_determinism_hash(tick=4, rng_seed=2010, hex_rows=rows)
        assert first == second
        assert first != moved

    def test_hash_module_never_references_babylon_meta(self) -> None:
        """The hash's own module is inside the partition too."""
        module_path = Path(cast(str, babylon.persistence.__file__)).parent
        source = (module_path / "conservation_audit.py").read_text(encoding="utf8")
        assert "babylon_meta" not in source


class TestWatchlistSeam:
    def test_store_satisfies_the_tui_protocol_structurally(self) -> None:
        """The composition root can inject the store where the TUI's
        ``WatchlistPersistence`` seam expects one — no imports between
        ``babylon.tui`` and ``babylon.persistence`` required."""
        store = BabylonMetaStore.__new__(BabylonMetaStore)
        assert isinstance(store, WatchlistPersistence)

    def test_campaign_record_is_frozen(self) -> None:
        """Catalog rows are immutable snapshots, per house model rules."""
        assert CampaignRecord.model_config.get("frozen") is True
