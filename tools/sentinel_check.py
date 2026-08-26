#!/usr/bin/env python3
"""CLI dispatcher for the ``babylon.sentinels`` family (VIII.12 / III.11 gates).

Each sentinel is a declared-invariant registry plus a set of loud static checks;
this thin shim just routes ``sentinel_check.py <sensor> --check`` to the chosen
sentinel's ``main``. The check logic lives in the importable package
(``babylon.sentinels.*``) so it is unit-testable and mutation-testable without a
``sys.path`` hack — this file carries no logic of its own.

Run: ``uv run python tools/sentinel_check.py coverage --check``. Exit codes are
the sentinel's own contract: 0 clean, 1 gating violations, 2 infrastructure
failure (source missing/unparseable — never swallowed into a false pass).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from babylon.sentinels.absence.checks import main as absence_main
from babylon.sentinels.aggregation.checks import main as aggregation_intensive_main
from babylon.sentinels.coupling.checks import main as coupling_main
from babylon.sentinels.coverage.checks import main as coverage_main
from babylon.sentinels.dangling.checks import main as dangling_main
from babylon.sentinels.defines_passthrough.checks import main as defines_passthrough_main
from babylon.sentinels.domain_sync.checks import main as domain_sync_main
from babylon.sentinels.fallback_coverage.checks import main as fallback_coverage_main
from babylon.sentinels.formula_registration.checks import main as formula_registration_main
from babylon.sentinels.gate_coverage.checks import main as gate_coverage_main
from babylon.sentinels.inert.checks import main as inert_main
from babylon.sentinels.liveness.checks import main as liveness_main
from babylon.sentinels.reachability.checks import main as reachability_main
from babylon.sentinels.seam_algebra.checks import main as seam_algebra_main
from babylon.sentinels.superstructure.checks import main as superstructure_main
from babylon.sentinels.surface.checks import main as surface_main
from babylon.sentinels.synthetic.checks import main as synthetic_main
from babylon.sentinels.tutorial_coverage.checks import main as tutorial_coverage_main
from babylon.sentinels.unconsumed.checks import main as unconsumed_main
from babylon.sentinels.vocabulary.checks import main as vocabulary_main


def _catalog_main(argv: list[str] | None) -> int:
    """Route to the catalog DB probe (Program 21) — lazy import.

    The probe opens sqlite3 against the reference DB, which the fast-gate must
    never do, so its module loads only when selected (refdata lane).
    """
    from babylon.sentinels.coverage.db_probe import main as catalog_main

    return catalog_main(argv)


def _gate_coverage_truth_main(argv: list[str] | None) -> int:
    """Route to the dynamic gate-coverage truth probe (E1 check-a) — lazy import.

    The probe imports the engine (``babylon.engine.simulation_engine.step``),
    which the layer-0.5 ``babylon.sentinels`` package may not import, so it
    lives beside this file in ``tools/`` (``gate_coverage_probe.py``) and
    loads only when selected — the runtime twin of ``gate-coverage``'s static
    estate-completeness check (proves each declaration is TRUE, not just that
    the estate is complete).
    """
    from gate_coverage_probe import (
        main as gate_coverage_truth_main,  # type: ignore[import-not-found]
    )

    return gate_coverage_truth_main(argv)


def _partition_main(argv: list[str] | None) -> int:
    """Route to the partition probe (Program 19, ADR070) — lazy import.

    The partition sentinel's harness runs the engine, which the layer-0.5
    package may not import, so it lives beside this file in ``tools/``
    (``partition_probe.py``) and loads only when selected.
    """
    from partition_probe import main as partition_main  # type: ignore[import-not-found]

    return partition_main(argv)


#: Registered sentinels: name -> its ``main(argv)`` entry point.
_SENSORS: dict[str, Callable[[list[str] | None], int]] = {
    "absence": absence_main,
    "seam-algebra": seam_algebra_main,
    "coverage": coverage_main,
    "gate-coverage": gate_coverage_main,
    "gate-coverage-truth": _gate_coverage_truth_main,
    "partition": _partition_main,
    "synthetic": synthetic_main,
    "catalog": _catalog_main,
    "vocabulary": vocabulary_main,
    "inert": inert_main,
    "dangling": dangling_main,
    "defines_passthrough": defines_passthrough_main,
    "domain_sync": domain_sync_main,
    "formula_registration": formula_registration_main,
    "unconsumed": unconsumed_main,
    "reachability": reachability_main,
    "fallback-coverage": fallback_coverage_main,
    "aggregation-intensive": aggregation_intensive_main,
    "liveness": liveness_main,
    "coupling": coupling_main,
    "superstructure": superstructure_main,
    "surface": surface_main,
    "tutorial-coverage": tutorial_coverage_main,
}


def main(argv: list[str] | None = None) -> int:
    """Route to the chosen sentinel's ``main`` and return its exit code.

    :param argv: CLI args; first positional selects the sensor, ``--check`` is
        the CI-mode alias forwarded to the sentinel (which always gates).
    :returns: The selected sentinel's exit code (0 clean / 1 gating / 2 infra).
    """
    parser = argparse.ArgumentParser(
        description="Babylon Sentinels — run a declared-invariant sensor (VIII.12 / III.11).",
    )
    parser.add_argument("sensor", choices=sorted(_SENSORS), help="which sentinel to run")
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the sentinel always gates (exit 1 on violations).",
    )
    args = parser.parse_args(argv)
    return _SENSORS[args.sensor](["--check"] if args.check else [])


if __name__ == "__main__":
    sys.exit(main())
