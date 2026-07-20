"""The defines-passthrough sentinel: a production call must thread live defines through.

**The one rule.** For every :data:`~babylon.sentinels.defines_passthrough.
registry.WatchedFunction` row, find that function's OPTIONAL ``defines``
parameter's positional slot (:func:`~babylon.sentinels._ast.
optional_defines_param_index` — a function whose ``defines`` parameter is
required, or absent, is silently skipped: it is out of this sentinel's scope
by construction, see the registry module's own docstring), then scan every
production call site (:data:`~babylon.sentinels.defines_passthrough.registry.
PRODUCTION_ROOTS`, minus :data:`~babylon.sentinels.defines_passthrough.
registry.EXCLUDED_DIRS`, tests excluded) for a call that supplies neither the
keyword nor the correctly-positioned positional argument
(:func:`~babylon.sentinels._ast.calls_missing_keyword_or_positional_arg`). A
hit is a call that will silently use the function's own schema-default
coefficients regardless of the run's actual ``services.defines``/
``defines.yaml`` — defeating the modding path the repo's own configuration
doc promises.

Read :mod:`babylon.sentinels.dangling.checks` first — this module mirrors
its shape (registry of watched things + a single gating rule +
:class:`~babylon.sentinels.exemptions.SentinelExemption` governance)
deliberately, per the family's established convention of each sentinel
package staying self-contained.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Final

from babylon.sentinels._ast import (
    calls_missing_keyword_or_positional_arg,
    optional_defines_param_index,
)
from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor
from babylon.sentinels.defines_passthrough.registry import (
    DEFINES_PASSTHROUGH_EXEMPTIONS,
    EXCLUDED_DIRS,
    PRODUCTION_ROOTS,
    WATCHED_FUNCTIONS,
    WatchedFunction,
)
from babylon.sentinels.exemptions import is_exempt
from babylon.sentinels.report import finding

__all__ = [
    "is_test_source",
    "main",
    "missing_defines_passthrough",
]

#: Repo root (this file is ``<root>/src/babylon/sentinels/defines_passthrough/checks.py``).
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]


def is_test_source(path: Path) -> bool:
    """True iff ``path`` is a test file by pytest convention.

    Verbatim mirror of :func:`babylon.sentinels.dangling.checks.is_test_source`
    (see that module's docstring for why each sentinel package stays
    self-contained rather than importing a sibling's internals).

    :param path: The file to classify.
    :returns: Whether the file is a test file (and must never count as a
        production call site).
    """
    return (
        path.name == "conftest.py"
        or path.stem.startswith("test_")
        or path.stem.endswith("_test")
        or "tests" in path.parts
    )


def _production_files(roots: tuple[str, ...] = PRODUCTION_ROOTS) -> Iterator[Path]:
    """Yield every non-test, non-excluded ``.py`` file under ``roots``, sorted.

    :param roots: Repo-relative root directories to walk.
    :returns: Production (non-test, non-excluded) Python files, in a stable order.
    :raises SentinelCheckError: If a root directory is missing.
    """
    for root in roots:
        base = _REPO_ROOT / root
        if not base.is_dir():
            raise SentinelCheckError(f"scan root missing: {base} (cannot verify passthrough)")
        for path in sorted(base.rglob("*.py")):
            if is_test_source(path):
                continue
            rel_posix = path.relative_to(_REPO_ROOT).as_posix()
            if any(rel_posix.startswith(excluded) for excluded in EXCLUDED_DIRS):
                continue
            if "__pycache__" in path.parts:
                continue
            yield path


def missing_defines_passthrough(
    functions: tuple[WatchedFunction, ...] = WATCHED_FUNCTIONS,
) -> list[str]:
    """The gating rule: every call to a watched function must pass ``defines``.

    :param functions: The watched-function rows to check (defaults to the
        real :data:`WATCHED_FUNCTIONS`; injectable so tests can supply a
        deliberately-narrowed set to prove the sensor reds/greens).
    :returns: One violation string per offending call site, sorted.
    :raises SentinelCheckError: If a scan root is missing/unparseable, or a
        row's declared function no longer resolves to the OPTIONAL-``defines``
        shape this sentinel watches (registry drift — the row itself would
        need updating, not a silently-shrinking check).
    """
    violations: list[str] = []
    for row in functions:
        index = optional_defines_param_index(_REPO_ROOT / row.def_file, row.func_name)
        if index is None:
            raise SentinelCheckError(
                f"{row.name}: {row.def_file}::{row.func_name} no longer declares an "
                "OPTIONAL 'defines' parameter -- WATCHED_FUNCTIONS registry drift "
                "(update or remove this row)"
            )
        for path in _production_files():
            rel = path.relative_to(_REPO_ROOT).as_posix()
            for lineno in calls_missing_keyword_or_positional_arg(
                path, row.func_name, "defines", index
            ):
                key = ("defines_passthrough", rel, row.func_name)
                if is_exempt(key, DEFINES_PASSTHROUGH_EXEMPTIONS):
                    continue
                violations.append(
                    finding(
                        error_class="defines-passthrough-omitted",
                        symbol=row.func_name,
                        file=rel,
                        line=lineno,
                        problem=(
                            f"calls {row.func_name}(...) without defines= -- silently "
                            f"falls back to {row.def_file}'s own schema-default "
                            "coefficients, ignoring services.defines/defines.yaml -- "
                            "this is exactly the pattern that hid task #42's "
                            "review MEDIUM-1 (ideology.py's route_agitation_to_ternary "
                            "and compute_exploitation_visibility calls) until this "
                            "sentinel's own repo-wide survey found it"
                        ),
                        remedy=(
                            "pass defines=services.defines.<category> (the defines "
                            f"sub-model {row.func_name} declares), or -- if this call "
                            "site genuinely has no services/defines object reachable "
                            "(e.g. a Pydantic computed_field) -- add a reasoned "
                            "SentinelExemption (key=('defines_passthrough', rel_path, "
                            "func_name), reason, owner, date, tracking_task) to "
                            "DEFINES_PASSTHROUGH_EXEMPTIONS"
                        ),
                    )
                )
    return sorted(violations)


#: The one gating rule: a missing defines= passthrough is a live defect.
_GATING_CHECKS: Final[tuple[LabelledCheck, ...]] = (
    ("defines-passthrough-omitted", missing_defines_passthrough),
)


def _summary(advisory_count: int) -> str:
    """Clean one-line summary: the watched-function count actually enforced.

    :param advisory_count: Number of advisory findings (0 — no advisory tier).
    :returns: The summary line.
    """
    _ = advisory_count  # This sentinel declares no advisory tier.
    return (
        f"DEFINES_PASSTHROUGH clean: {len(WATCHED_FUNCTIONS)} watched formulas-layer "
        "function(s) — every production call passes the run's live defines= "
        "(keyword or correctly-positioned positional), or is a cited exemption."
    )


def main(argv: list[str] | None = None) -> int:
    """Run the defines-passthrough gate and return the exit code.

    :param argv: CLI args (``--check`` is accepted as the CI-mode alias; the
        behavior is always to gate).
    :returns: 0 clean, 1 gating violations found, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description="Defines-passthrough gate: formulas-layer defines= must reach every call."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)
    return run_sensor("DEFINES_PASSTHROUGH", _GATING_CHECKS, (), _summary)


if __name__ == "__main__":
    sys.exit(main())
