"""The undeclared-coupling sensor (static, advisory, BOTH directions).

Reads the declared ``Coupling(...)`` literals out of the dialectics catalog with
:mod:`ast` and the declared measurement dependencies out of
:mod:`babylon.sentinels.coupling.registry`, then diffs the two:

- :func:`check_declared_edges_are_grounded` — declared-but-absent;
- :func:`check_real_dependencies_are_declared` — present-but-undeclared.

Only edges whose BOTH endpoints are registered are judged; an unregistered
endpoint yields no claim in either direction (the sensor never invents a
dependency it cannot see). ``contains`` edges are excluded: they are auto-derived
from pole nesting, not authored, so they make no claim about reads.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from babylon.sentinels._ast import coupling_edges, referenced_names
from babylon.sentinels.base import LabelledCheck, run_sensor
from babylon.sentinels.coupling.registry import (
    MEASUREMENT_DEPENDENCIES,
    MeasurementDependency,
)
from babylon.sentinels.report import finding

#: Repo root (this file is ``<root>/src/babylon/sentinels/coupling/checks.py``).
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]

#: The module declaring ``_DEFAULT_COUPLINGS``.
_CATALOG_FILE: str = "src/babylon/domain/dialectics/instances/catalog.py"

#: Kinds that assert a real read. ``contains`` is auto-derived from nesting and
#: ``antagonizes`` asserts mutual antagonism, not a measurement dependency.
_READ_KINDS: frozenset[str] = frozenset({"feeds", "constrains", "transforms"})


def _declared_edges() -> tuple[tuple[str, str, str], ...]:
    """Read the production catalog's declared coupling edges.

    :returns: ``(source, target, kind)`` triples from ``_DEFAULT_COUPLINGS``.
    :raises SentinelCheckError: If the catalog is missing or unparseable.
    """
    return coupling_edges(_REPO_ROOT / _CATALOG_FILE)


def _index(
    dependencies: tuple[MeasurementDependency, ...],
) -> dict[str, MeasurementDependency]:
    """Index declared dependencies by opposition key.

    :param dependencies: The declared rows.
    :returns: A mapping of opposition key to its row.
    """
    return {row.opposition_key: row for row in dependencies}


def _reads(target: MeasurementDependency, source: MeasurementDependency) -> bool:
    """Whether ``target``'s producer actually reads something ``source`` publishes.

    :param target: The downstream opposition's declared dependency.
    :param source: The upstream opposition's declared dependency.
    :returns: Whether the target's producer file mentions any of the source's
        ``produces_symbols``.
    :raises SentinelCheckError: If the target's producer file is missing or
        unparseable.
    """
    mentioned = referenced_names(_REPO_ROOT / target.producer_file)
    return any(symbol in mentioned for symbol in source.produces_symbols)


def check_declared_edges_are_grounded(
    edges: tuple[tuple[str, str, str], ...] | None = None,
    dependencies: tuple[MeasurementDependency, ...] = MEASUREMENT_DEPENDENCIES,
) -> list[str]:
    """Direction A — every declared edge must map to a real read (declared-but-absent).

    For each declared ``feeds``/``constrains``/``transforms`` edge whose both
    endpoints are registered, assert the target's producer file mentions at least
    one symbol the source's producer publishes. An edge that fails is a claim
    about the code the code does not support — the state the four reserved edges
    sat in for months.

    :param edges: Edge triples to judge (defaults to the real catalog's;
        injectable so the efficacy tests can supply an injected defect).
    :param dependencies: Declared measurement dependencies (injectable).
    :returns: Sorted agent-legible finding strings (empty when every edge is
        grounded).
    :raises SentinelCheckError: If the catalog or a producer file is missing or
        unparseable.
    """
    triples = _declared_edges() if edges is None else edges
    index = _index(dependencies)
    findings: list[str] = []
    for source_key, target_key, kind in triples:
        if kind not in _READ_KINDS:
            continue
        source = index.get(source_key)
        target = index.get(target_key)
        if source is None or target is None:
            continue
        if _reads(target, source):
            continue
        findings.append(
            finding(
                error_class="undeclared-coupling",
                symbol=f"{source_key} -> {target_key} ({kind})",
                file=_CATALOG_FILE,
                line=0,
                problem=(
                    f"declared edge is not grounded: {target.producer_file} mentions "
                    f"none of {source_key}'s published symbols "
                    f"({', '.join(source.produces_symbols)})"
                ),
                remedy=(
                    "either wire the dependency the edge claims (make the target's "
                    "producer read the source's output) or delete the edge from "
                    "_DEFAULT_COUPLINGS — a coupling graph that outruns the code is "
                    "vocabulary, not structure"
                ),
            )
        )
    return sorted(findings)


def check_real_dependencies_are_declared(
    edges: tuple[tuple[str, str, str], ...] | None = None,
    dependencies: tuple[MeasurementDependency, ...] = MEASUREMENT_DEPENDENCIES,
) -> list[str]:
    """Direction B — every real read must carry a declaring edge (present-but-undeclared).

    For each ordered pair of registered oppositions with DIFFERENT producer files
    (a same-file pair is judged by direction A alone, where mentions are trivially
    present), if the target's producer reads a symbol the source publishes, an
    edge ``source -> target`` of a reading kind must be declared. A real
    dependency nobody wrote down is the ``momentum_coupling`` failure.

    :param edges: Declared edge triples (defaults to the real catalog's).
    :param dependencies: Declared measurement dependencies (injectable).
    :returns: Sorted agent-legible finding strings (empty when every real
        dependency is declared).
    :raises SentinelCheckError: If the catalog or a producer file is missing or
        unparseable.
    """
    triples = _declared_edges() if edges is None else edges
    declared = {(source, target) for source, target, kind in triples if kind in _READ_KINDS}
    findings: list[str] = []
    for source in sorted(dependencies, key=lambda row: row.opposition_key):
        for target in sorted(dependencies, key=lambda row: row.opposition_key):
            if source.opposition_key == target.opposition_key:
                continue
            if source.producer_file == target.producer_file:
                continue
            if not _reads(target, source):
                continue
            if (source.opposition_key, target.opposition_key) in declared:
                continue
            shared = sorted(
                symbol
                for symbol in source.produces_symbols
                if symbol in referenced_names(_REPO_ROOT / target.producer_file)
            )
            findings.append(
                finding(
                    error_class="undeclared-coupling",
                    symbol=f"{source.opposition_key} -> {target.opposition_key}",
                    file=target.producer_file,
                    line=0,
                    problem=(
                        f"reads {source.opposition_key}'s published symbol(s) "
                        f"{', '.join(shared)} but no coupling edge declares it"
                    ),
                    remedy=(
                        "add the edge to _DEFAULT_COUPLINGS with the kind that "
                        "matches the real relation (feeds = the target reads the "
                        "source's observation; constrains = the source limits the "
                        "target's reachable state; transforms = the source's output "
                        "becomes the target's input prices), citing the read site"
                    ),
                )
            )
    return sorted(findings)


#: Nothing gates — advisory and local/on-demand per the standing owner ruling.
_GATING_CHECKS: tuple[LabelledCheck, ...] = ()

#: Both directions report advisorily.
_ADVISORY_CHECKS: tuple[LabelledCheck, ...] = (
    (
        "declared coupling edge has no real measurement dependency",
        check_declared_edges_are_grounded,
    ),
    (
        "real measurement dependency has no declared coupling edge",
        check_real_dependencies_are_declared,
    ),
)


def _summary(advisory_count: int) -> str:
    """Build the clean one-line summary printed when nothing gated.

    :param advisory_count: Number of advisory findings emitted above.
    :returns: The summary line naming the sizes of both sides of the diff.
    """
    summary = (
        f"Coupling (static, advisory): {len(MEASUREMENT_DEPENDENCIES)} declared "
        f"measurement dependencies diffed against {len(_declared_edges())} declared "
        "coupling edges, both directions."
    )
    if advisory_count:
        summary += f" ({advisory_count} advisory findings above.)"
    return summary


def main(argv: list[str] | None = None) -> int:
    """Run both coupling directions and return the process exit code.

    :param argv: CLI args (``--check`` accepted for family symmetry; advisory).
    :returns: 0 clean or advisory-only, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description="Coupling — declared edges vs real dependencies, both ways (advisory).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Accepted for family symmetry; this sensor is advisory and never gates.",
    )
    parser.parse_args(argv)
    return run_sensor("COUPLING", _GATING_CHECKS, _ADVISORY_CHECKS, _summary)


if __name__ == "__main__":
    sys.exit(main())
