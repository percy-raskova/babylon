"""Declared invariants of the ``absence`` sentinel — every sqlite connect
site carries a cited disposition.

Founding incident (2026-07-20, G1 nightly): ``SubstrateSystem``'s lattice
build called ``get_reference_session()`` on a CI runner with no reference
database. ``sqlite3.connect``/SQLAlchemy's ``create_engine("sqlite:///path")``
both silently CREATE an empty file when the path is missing — the runner got
a lattice build against a brand-new, table-less SQLite file instead of a
loud "database not found", and the real failure only surfaced two systems
later as a baffling ``no such table: dim_county``. Part A of task #64 closed
the one constitutional entry point (``get_reference_session``, see
:mod:`babylon.reference.database`); this registry is the family-wide audit
trail that every OTHER sqlite connect site in ``src/babylon`` has been looked
at and classified, so a new unguarded site can never join the tree silently
again.

Every ``sqlite3.connect``/``create_engine("sqlite:///...")`` call site under
``src/babylon`` (found by :func:`babylon.sentinels.absence.checks.
find_connect_sites`) must be accounted for by exactly one row here, keyed by
its repo-relative file path. :data:`Disposition` is a closed taxonomy:

- ``"canonical"``: the file OWNS the constitutional absence guard (currently
  just ``reference/database.py`` — ``get_reference_session`` per part A).
- ``"guarded"``: an explicit ``if not path.exists(): raise FileNotFoundError``
  precedes every connect in this file (model:
  ``engine/headless_runner/scopes.py:170``).
- ``"readonly_uri"``: every connect in this file opens a ``file:...?mode=ro``
  URI — SQLite refuses to create a database file under a read-only-mode URI,
  so an absent file fails loudly on its own even without an explicit guard.
- ``"creates_own_store"``: creation IS the correct behavior here — this is
  the file's own runtime state, not immutable reference data (ADR030/031).
- ``"declared_debt"``: neither guarded nor read-only — a real, open absence
  risk, held here by name (Constitution III.11: loud, not silently fixed or
  silently ignored) with the remediation named in ``reason``.

Layer 0.5: imports nothing above the stdlib — no row here needs a live model
import (unlike the vocabulary sentinel's ``NodeType``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, get_args

#: The closed disposition taxonomy — see the module docstring for what each
#: value asserts and what evidence it demands.
Disposition = Literal["readonly_uri", "guarded", "creates_own_store", "canonical", "declared_debt"]

_VALID_DISPOSITIONS: Final[frozenset[str]] = frozenset(get_args(Disposition))


@dataclass(frozen=True)
class ConnectionDisposition:
    """One file's declared, evidence-cited sqlite-connection disposition.

    :ivar file: Repo-relative ``.py`` path — must equal the
        :data:`CONNECTION_DISPOSITIONS` dict key it is stored under.
    :ivar disposition: The disposition category, see :data:`Disposition`.
    :ivar reason: The cited evidence — line numbers, why this is safe (or
        not), and for ``declared_debt`` rows, the named remediation.
    """

    file: str
    disposition: Disposition
    reason: str

    def __post_init__(self) -> None:
        """Reject a malformed row loudly at import (Constitution III.11).

        :raises ValueError: If ``file``/``reason`` is blank, ``file`` is not
            a ``.py`` path, or ``disposition`` is not a member of
            :data:`Disposition`.
        """
        if not self.file.strip():
            raise ValueError("ConnectionDisposition.file must be non-empty")
        if not self.file.endswith(".py"):
            raise ValueError(f"{self.file!r}: file must be a .py path")
        if not self.reason.strip():
            raise ValueError(f"{self.file!r}: reason must be non-empty")
        if self.disposition not in _VALID_DISPOSITIONS:
            raise ValueError(
                f"{self.file!r}: disposition {self.disposition!r} not one of "
                f"{sorted(_VALID_DISPOSITIONS)}"
            )


def _build_registry(
    rows: tuple[ConnectionDisposition, ...],
) -> dict[str, ConnectionDisposition]:
    """Key declared rows by file, failing loudly on a duplicate.

    :param rows: The declared rows (single source of truth order).
    :returns: The rows keyed by :attr:`ConnectionDisposition.file`.
    :raises ValueError: If two rows declare the same file.
    """
    registry: dict[str, ConnectionDisposition] = {}
    for row in rows:
        if row.file in registry:
            raise ValueError(f"absence sentinel: duplicate registry row for {row.file!r}")
        registry[row.file] = row
    return registry


#: One row per audited file (task #64 census, 2026-07-20). Every claim below
#: was re-verified against the tree with ``rg`` before being written here —
#: three files a prior draft census reasoned were "unguarded writable"
#: (``hex_hydrator.py``, ``county_aggregation.py``, ``tiger_ingestion.py``)
#: turned out, on inspection, to carry the exact same
#: ``if not path.exists(): raise FileNotFoundError`` guard as
#: ``scopes.py`` — they are filed ``guarded``, not ``declared_debt`` (see
#: each row's own ``reason`` for the correction). Two files absent from that
#: draft census (``reference_data_cache.py``, ``natural_earth_reader.py``)
#: were found by the ``rg`` sweep and are filed here too.
_ROWS: Final[tuple[ConnectionDisposition, ...]] = (
    ConnectionDisposition(
        file="src/babylon/reference/database.py",
        disposition="canonical",
        reason=(
            "get_reference_session() (task #64 part A) raises FileNotFoundError before "
            "opening a session when NORMALIZED_DB_PATH is absent -- this file OWNS the "
            "constitutional reference-DB absence guard. get_normalized_engine()/"
            "get_source_engine() (create_engine at ~lines 100/127) legitimately auto-create "
            "via SQLAlchemy for loader tools (init_normalized_db, migration scripts) -- "
            "ADR098 loader doctrine: a loader writing the DB for the first time is supposed "
            "to create it."
        ),
    ),
    ConnectionDisposition(
        file="src/babylon/engine/headless_runner/scopes.py",
        disposition="guarded",
        reason=(
            "_load_national_fips raises FileNotFoundError at ~line 169 "
            "(`if not sqlite_path.exists(): raise ...`) immediately before "
            "sqlite3.connect at ~line 173 -- the model case part A's runtime guard is "
            "patterned on."
        ),
    ),
    ConnectionDisposition(
        file="src/babylon/engine/headless_runner/reference_data_cache.py",
        disposition="guarded",
        reason=(
            "Not in the original task census -- found by the rg sweep (task #64). "
            "ReferenceDataCache.hydrate() raises FileNotFoundError at ~line 178 "
            "(`if not self._sqlite_path.exists(): raise ...`) immediately before "
            "sqlite3.connect at ~line 204 -- the same in-function guard shape as scopes.py."
        ),
    ),
    ConnectionDisposition(
        file="src/babylon/domain/geography/natural_earth_reader.py",
        disposition="guarded",
        reason=(
            "Not in the original task census -- found by the rg sweep (task #64). "
            "NaturalEarthReader.__init__ raises FileNotFoundError at ~line 149 "
            "(`if not self._db_path.exists(): raise ...`) before any instance can call "
            "_connect() (~line 156); _connect() also opens a `file:...?mode=ro` URI, though "
            "that literal is one variable assignment away from the connect call and "
            "therefore invisible to this sentinel's own single-hop literal resolution -- the "
            "constructor guard is what this row rests on, not the (real but "
            "statically-unprovable) read-only mode."
        ),
    ),
    ConnectionDisposition(
        file="src/babylon/persistence/runtime_db.py",
        disposition="creates_own_store",
        reason=(
            "RuntimeDatabase creates a per-simulation-run tick-store SQLite file (or "
            ":memory: for tests) at ~lines 79/83 -- this is the RUN's own state (ADR030/031 "
            "Unified SQLite Runtime), never immutable reference data. Creation-on-first-use "
            "is the correct, intended behavior here, not an absence bug."
        ),
    ),
    ConnectionDisposition(
        file="src/babylon/persistence/postgres_initialization.py",
        disposition="declared_debt",
        reason=(
            "Four sqlite3.connect calls (~lines 136, 217, 276, 398) use `file:...?mode=ro` "
            "URIs -- safe, cannot auto-create. The bea_engine "
            "`create_engine(f'sqlite:///{sqlite_path}')` at ~line 850 is an unguarded, "
            "writable-mode read path (no existence check, no mode=ro) -- genuine debt. "
            "Remediation: convert to a read-only URI, mirroring this file's own four "
            "sqlite3.connect siblings."
        ),
    ),
    ConnectionDisposition(
        file="src/babylon/persistence/sqlite_hydrator.py",
        disposition="readonly_uri",
        reason="sqlite3.connect opens a `file:...?mode=ro` URI at ~line 45.",
    ),
    ConnectionDisposition(
        file="src/babylon/domain/economics/county_exposure.py",
        disposition="readonly_uri",
        reason="sqlite3.connect opens a `file:...?mode=ro` URI at ~line 105.",
    ),
    ConnectionDisposition(
        file="src/babylon/sentinels/coverage/db_probe.py",
        disposition="readonly_uri",
        reason="sqlite3.connect opens a `file:...?mode=ro` URI at ~line 75.",
    ),
    ConnectionDisposition(
        file="src/babylon/persistence/hex_hydrator.py",
        disposition="guarded",
        reason=(
            "Corrected from the original task census's 'declared_debt' (unguarded writable) "
            "-- rg verification (task #64) found hydrate_hex_state raises FileNotFoundError "
            "at ~line 161 (`if not sqlite_path_resolved.exists(): raise ...`) immediately "
            "before sqlite3.connect at ~line 175, the same guard shape as scopes.py. Still "
            "lacks a mode=ro URI (a real defense-in-depth gap), but the existence guard "
            "already prevents the auto-create-masks-absence bug this sentinel targets."
        ),
    ),
    ConnectionDisposition(
        file="src/babylon/persistence/county_aggregation.py",
        disposition="guarded",
        reason=(
            "Corrected from the original task census's 'declared_debt' (unguarded writable) "
            "-- rg verification (task #64) found BOTH sqlite3.connect call sites "
            "(~lines 303, 386) directly preceded, in the same function, by "
            "`if not sqlite_path.exists(): raise FileNotFoundError(...)` (~lines 298, 381) -- "
            "the same guard shape as scopes.py. Still lacks a mode=ro URI, same "
            "defense-in-depth note as hex_hydrator.py."
        ),
    ),
    ConnectionDisposition(
        file="src/babylon/persistence/tiger_ingestion.py",
        disposition="guarded",
        reason=(
            "Corrected from the original task census's 'declared_debt' (unguarded writable) "
            "-- rg verification (task #64) found the TIGER-geometry reader raises "
            "FileNotFoundError at ~lines 198-202 (`if not path.exists(): raise ...`) "
            "immediately before sqlite3.connect at ~line 219, the same guard shape as "
            "scopes.py -- this is a loader-ADJACENT reader (loads existing TIGER rows to "
            "insert into Postgres), not itself a table-creating loader, so ADR098 loader "
            "doctrine does not apply here; the existence guard is what makes this safe."
        ),
    ),
)

#: The audited registry, keyed by repo-relative file path.
CONNECTION_DISPOSITIONS: Final[dict[str, ConnectionDisposition]] = _build_registry(_ROWS)
