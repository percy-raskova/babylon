"""Gate-coverage sentinel: qa:regression's estate is declared and complete.

The 2026-07-19 U9 inertness episode proved the byte-identical gate can run
green over a dead feature when no scenario exercises it. This sentinel is the
existing ``gate-blindness`` error class pointed at the gate itself: the
scenario estate (``tools/regression_scenarios.py``) DECLARES what it covers,
and this sensor proves the declaration set is complete over the engine's 30
Systems — statically, by AST, at layer 0.5. The companion dynamic probe
(``tools/gate_coverage_probe.py``, CLI key ``gate-coverage-truth``) proves
each declaration is TRUE at runtime.

**Scope — STATIC coherence only**: reads source files and committed baseline
JSON; NEVER imports the engine, NEVER runs a scenario.
"""

from babylon.sentinels.gate_coverage.checks import (
    check_bundle_evidence,
    check_declared_names_exist,
    check_union_covers_all_systems,
    engine_system_names,
    main,
)

__all__ = [
    "check_bundle_evidence",
    "check_declared_names_exist",
    "check_union_covers_all_systems",
    "engine_system_names",
    "main",
]
