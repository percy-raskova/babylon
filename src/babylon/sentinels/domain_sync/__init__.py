"""Domain-sync sentinel: the ledger CREATE DOMAINs must not drift from their source.

The error class (``ledger-contract-drift``): a PostgreSQL ``CREATE DOMAIN`` in
``0039_domain_contracts.sql`` whose ``CHECK`` range/format has forked from its
single source of truth — :mod:`babylon.models.types` for the numeric domains
(``probability``/``currency``/``ratio``/``labor_hours``), the registry itself
for the format domains (``fips5``/``fips2``/``h3index``). Registry = the domain
specs + their backing-column evidence; checks = a single static rule that
re-derives every expected ``CHECK`` body from the source and compares it against
the committed migration's parsed body, so a drift on either side reds the gate.

The domains lift what were ~128 inline ``CHECK`` clauses (the 5-digit FIPS regex
alone duplicated across seven migrations) into single, language-agnostic,
byte-checkable objects — and this sentinel keeps the lifted contract honest.
"""

from babylon.sentinels.domain_sync.checks import (
    domain_bounds_out_of_sync,
    main,
    parse_committed_domains,
    read_committed_migration,
)
from babylon.sentinels.domain_sync.ddl import (
    Bounds,
    build_migration_sql,
    format_check_predicate,
    numeric_check_predicate,
    types_py_bounds,
)
from babylon.sentinels.domain_sync.registry import (
    DEFERRED_DOMAINS,
    FORMAT_DOMAINS,
    MIGRATION_FILENAME,
    MIGRATION_PATH,
    NUMERIC_DOMAINS,
    FormatDomainSpec,
    NumericDomainSpec,
)

__all__ = [
    "DEFERRED_DOMAINS",
    "FORMAT_DOMAINS",
    "MIGRATION_FILENAME",
    "MIGRATION_PATH",
    "NUMERIC_DOMAINS",
    "Bounds",
    "FormatDomainSpec",
    "NumericDomainSpec",
    "build_migration_sql",
    "domain_bounds_out_of_sync",
    "format_check_predicate",
    "main",
    "numeric_check_predicate",
    "parse_committed_domains",
    "read_committed_migration",
    "types_py_bounds",
]
