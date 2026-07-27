"""The domain-sync sentinel: the ledger DOMAINs must not drift from their source.

**The one rule.** For every domain the registry declares, the committed
``0039_domain_contracts.sql`` migration must carry a ``CREATE DOMAIN`` whose
``CHECK`` body equals the body derived live from the domain's single source of
truth — :mod:`babylon.models.types` for a numeric domain (its ``annotated_types``
range), the registry itself for a format domain (its declared pattern). A
mismatch, or a missing domain, is ``ledger-contract-drift``: the very disease
(two copies of one contract silently forking) the domains were created to cure.

Because the expected body is derived from ``types.py``/registry — not from a
cached copy of the generator's output — the gate reds on drift from EITHER side:
a ``types.py`` bound change the migration did not follow, OR a hand-edit of the
migration. This is what makes the sentinel a real guard rather than a
tautological "the file equals itself" check.

The gating function :func:`domain_bounds_out_of_sync` takes the committed SQL as
a parameter (defaulting to the real migration) so a test can feed it a
deliberately-tampered copy and prove the sensor reds — the mutation-validated
efficacy the "sentinel every error class" rule requires.

Read :mod:`babylon.sentinels.defines_passthrough.checks` first — this module
mirrors its shape (registry of watched things + a single gating rule +
injectable check function + :func:`~babylon.sentinels.base.run_sensor`).

Layer 0.5: imports :mod:`babylon.models` and stdlib only.
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Final

from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor
from babylon.sentinels.domain_sync.ddl import (
    format_check_predicate,
    numeric_check_predicate,
)
from babylon.sentinels.domain_sync.registry import (
    FORMAT_DOMAINS,
    MIGRATION_FILENAME,
    MIGRATION_PATH,
    NUMERIC_DOMAINS,
)
from babylon.sentinels.report import finding

__all__ = [
    "domain_bounds_out_of_sync",
    "main",
    "parse_committed_domains",
    "read_committed_migration",
]

#: Matches ``CREATE DOMAIN <name> AS <base...> CHECK ( <body> );`` and captures
#: the domain name and the CHECK body. Each generated statement is on ONE line
#: ending in ``);`` — with ``re.DOTALL`` OFF the greedy ``.*`` body cannot cross
#: a newline, so it captures up to that line's terminating ``)`` even when the
#: body itself contains a nested paren (``length(VALUE) = 15``).
_CREATE_DOMAIN_RE: Final[re.Pattern[str]] = re.compile(
    r"CREATE\s+DOMAIN\s+(\w+)\s+AS\s+[\w ]+?\s+CHECK\s*\((?P<body>.*)\)\s*;",
    re.IGNORECASE,
)


def read_committed_migration() -> str:
    """Return the committed ``0039_domain_contracts.sql`` text.

    :returns: The migration file text.
    :raises SentinelCheckError: If the migration file is absent — an
        infrastructure failure (the estate is structurally incomplete), never a
        silent "no drift found".
    """
    if not MIGRATION_PATH.is_file():
        raise SentinelCheckError(
            f"domain_sync: migration {MIGRATION_FILENAME} is missing at {MIGRATION_PATH} "
            "(regenerate with: uv run python tools/generate_domain_ddl.py)"
        )
    return MIGRATION_PATH.read_text(encoding="utf-8")


def _normalize(predicate: str) -> str:
    """Collapse whitespace so committed and expected bodies compare exactly.

    :param predicate: A raw CHECK body (as parsed, or as rendered).
    :returns: The body with runs of whitespace collapsed to single spaces and
        the ends stripped.
    """
    return " ".join(predicate.split())


def parse_committed_domains(sql_text: str) -> dict[str, str]:
    """Map each ``CREATE DOMAIN`` in ``sql_text`` to its normalized CHECK body.

    :param sql_text: The migration file text.
    :returns: ``{domain_name: normalized_check_body}`` for every domain found.
    """
    return {
        match.group(1).lower(): _normalize(match.group("body"))
        for match in _CREATE_DOMAIN_RE.finditer(sql_text)
    }


def domain_bounds_out_of_sync(sql_text: str | None = None) -> list[str]:
    """The gating rule: every committed domain's CHECK matches its source of truth.

    :param sql_text: The committed migration text to check. Defaults to the real
        :data:`MIGRATION_PATH`; injectable so a test can pass a tampered copy
        (mutation validation) or a synthetic one.
    :returns: One sorted violation string per drifted/missing domain (empty ==
        in sync).
    :raises SentinelCheckError: If the migration is absent, or a numeric source
        type is unresolved/unbounded (registry drift) — infrastructure failure,
        never a silent pass.
    """
    committed = parse_committed_domains(
        read_committed_migration() if sql_text is None else sql_text
    )
    violations: list[str] = []

    for numeric in NUMERIC_DOMAINS:
        expected = _normalize(numeric_check_predicate(numeric))
        _append_if_drifted(violations, numeric.name, committed, expected, "models/types.py")
    for fmt in FORMAT_DOMAINS:
        expected = _normalize(format_check_predicate(fmt))
        _append_if_drifted(
            violations,
            fmt.name,
            committed,
            expected,
            "domain_sync.registry.FORMAT_DOMAINS",
        )

    return sorted(violations)


def _append_if_drifted(
    violations: list[str],
    name: str,
    committed: dict[str, str],
    expected: str,
    source: str,
) -> None:
    """Record a finding if ``name``'s committed CHECK is absent or ``!= expected``.

    :param violations: The accumulator to append to.
    :param name: The domain name.
    :param committed: Parsed ``{name: body}`` from the committed migration.
    :param expected: The normalized CHECK body derived from the source of truth.
    :param source: Human-readable name of that source (for the remedy text).
    """
    actual = committed.get(name)
    if actual == expected:
        return
    problem = (
        f"CREATE DOMAIN {name} is absent from {MIGRATION_FILENAME}"
        if actual is None
        else (
            f"domain {name}'s committed CHECK ({actual!r}) has drifted from its source "
            f"of truth {source} (expected {expected!r})"
        )
    )
    violations.append(
        finding(
            error_class="ledger-contract-drift",
            symbol=name,
            file=f"src/babylon/persistence/migrations/{MIGRATION_FILENAME}",
            line=0,
            problem=problem,
            remedy=(
                "regenerate the migration from its single source of truth: "
                "uv run python tools/generate_domain_ddl.py (never hand-edit the "
                f"CHECK — change {source} and regenerate)"
            ),
        )
    )


#: The one gating rule: a drifted or missing domain CHECK is a live defect.
_GATING_CHECKS: Final[tuple[LabelledCheck, ...]] = (
    ("ledger-contract-drift", domain_bounds_out_of_sync),
)


def _summary(advisory_count: int) -> str:
    """Clean one-line summary: the domain count actually enforced.

    :param advisory_count: Number of advisory findings (0 — no advisory tier).
    :returns: The summary line.
    """
    _ = advisory_count  # This sentinel declares no advisory tier.
    total = len(NUMERIC_DOMAINS) + len(FORMAT_DOMAINS)
    return (
        f"DOMAIN_SYNC clean: {len(NUMERIC_DOMAINS)} numeric + {len(FORMAT_DOMAINS)} format "
        f"= {total} ledger domain(s) in {MIGRATION_FILENAME} match their single source of "
        "truth (models/types.py bounds / registry patterns)."
    )


def main(argv: list[str] | None = None) -> int:
    """Run the domain-sync gate and return the exit code.

    :param argv: CLI args (``--check`` is accepted as the CI-mode alias; the
        behavior is always to gate).
    :returns: 0 clean, 1 gating violations found, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description="Domain-sync gate: ledger CREATE DOMAINs must match models/types.py."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)
    return run_sensor("DOMAIN_SYNC", _GATING_CHECKS, (), _summary)


if __name__ == "__main__":
    sys.exit(main())
