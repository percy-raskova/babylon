"""Dead-formula-registration sensor — a static gate (VIII.12 / III.11).

Proves, statically via :mod:`ast` (no import of ``babylon.engine``, no
Django, no DB — the sentinels' layer-0.5 boundary forbids it; ``pyproject.toml``'s
import-linter contract enforces it), that every
:data:`~babylon.sentinels.formula_registration.registry.DECLARED_FORMULAS`
row's underlying ``symbol`` has a genuine production reference OTHER than its
own ``engine/formula_registry.py`` registration call — or a cited
:class:`~babylon.sentinels.exemptions.SentinelExemption`.

**The gap this closes.** :mod:`babylon.sentinels.inert`'s rule (b)
(``producers_without_production_caller``) treats ANY ``ast.Name``/``ast.
Attribute`` reference to a symbol as a satisfied reference — including the
``formulas.calculate_labor_aristocracy_ratio`` attribute access sitting right
inside ``registry.register("labor_aristocracy_ratio",
formulas.calculate_labor_aristocracy_ratio)``. That call IS a reference, but
it is the registration act itself, not downstream consumption: a formula can
be registered forever and never actually invoked anywhere else, and
``inert`` would call that clean. This sensor scans the SAME
``PRODUCTION_ROOTS`` ``inert`` does, but explicitly excludes
:data:`~babylon.sentinels.formula_registration.registry.FORMULA_REGISTRY_FILE`
from counting as a reference source.

**Import-alias resolution.** A formula can be imported under a local alias
(``from babylon.formulas.fundamental_theorem import is_labor_aristocracy as
_is_labor_aristocracy`` — the real, verified shape
``domain/dialectics/instances/value_form.py`` uses) and then called only
under that alias. A bare symbol-name scan would go blind to this and
false-positive a formula that is genuinely, actively called. :func:`
_local_alias` resolves any ``from <module> import <symbol> as <alias>`` in
the SAME file (scoped per-file, mirroring :mod:`babylon.sentinels.inert`'s
own single-file scope boundary for its writer-chain closure) and
:func:`formula_reference_sites` searches for either name. A module-qualified
form (``formulas.calculate_x``) is never affected by a symbol's OWN aliasing
(the attribute name on the RHS of the dot is always the real symbol), so
only the bare-``Name`` form needs alias resolution.

**Scope and known limitations (read before extending).**

- Like :mod:`babylon.sentinels.inert`'s own documented boundary, this does
  NOT resolve ``getattr(module, "symbol_name")`` string-keyed indirection or
  a registry-mediated call (``FormulaRegistry.default().get("key")(...)`` —
  the REGISTRY KEY, not the bare symbol, is what such a call site mentions).
  ``web/game/provenance.py`` resolves formulas exactly this way; it is
  therefore invisible to this sensor's reference scan by construction. This
  is intentionally conservative — the current :data:`DECLARED_FORMULAS`
  rows are all correctly classified without needing to trust that path (see
  the registry module's own docstring for the verified per-row reasoning),
  and trusting a bare string-literal mention would reintroduce a WEAKER
  version of the exact bug this sensor exists to fix (a docstring or
  ``concept_cards.py`` citation mentioning a formula's name is not a real
  caller either).
- Test files never count as callers (:func:`is_test_source`, regardless of
  which root they sit under) — a test-only caller would silently reproduce
  the false-liveness bug this sensor exists to catch.

Run: ``poetry run python tools/sentinel_check.py formula_registration --check``.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Final

from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor
from babylon.sentinels.exemptions import is_exempt
from babylon.sentinels.formula_registration.registry import (
    DECLARED_FORMULAS,
    FORMULA_EXEMPTIONS,
    FORMULA_REGISTRY_FILE,
    PRODUCTION_ROOTS,
    DeclaredFormula,
)

__all__ = [
    "formula_reference_sites",
    "formulas_without_production_caller",
    "is_test_source",
    "main",
]

#: Repo root (this file is ``<root>/src/babylon/sentinels/formula_registration/checks.py``).
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]

_WHY: Final[str] = (
    "WHY THIS FAILS: registering a formula in FormulaRegistry is an implied public API "
    "claim, not a usage claim -- a formula only its own registration/tests ever mention is "
    "dead code with a heartbeat (Constitution III.10, Earn-Its-Keep). The inert sentinel's "
    "own producer-reachability rule cannot see this class of gap: it counts "
    "'formulas.<symbol>' inside the register(...) call itself as a satisfied reference."
)


def is_test_source(path: Path) -> bool:
    """True iff ``path`` is a test file by pytest convention.

    Matches on the file's own name (``conftest.py``, ``test_*.py``,
    ``*_test.py``) OR any ancestor directory literally named ``tests`` —
    catching nested test trees the same way every sibling sentinel does.

    :param path: The file to classify.
    :returns: Whether the file is a test file (never counted as a caller).
    """
    return (
        path.name == "conftest.py"
        or path.stem.startswith("test_")
        or path.stem.endswith("_test")
        or "tests" in path.parts
    )


def _parse(path: Path) -> ast.Module:
    """Read and parse ``path`` with :mod:`ast`, raising loudly on failure.

    :param path: Source file to parse.
    :returns: The parsed module.
    :raises SentinelCheckError: If the file is missing or unparseable — an
        infrastructure failure, never swallowed into a false pass.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc
    try:
        return ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise SentinelCheckError(f"cannot parse {path}: {exc}") from exc


def _production_files(roots: tuple[str, ...] = PRODUCTION_ROOTS) -> list[Path]:
    """Every non-test ``.py`` file under ``roots``, sorted (deterministic).

    :param roots: Repo-relative root directories to walk.
    :returns: Production (non-test) Python files, in a stable order.
    :raises SentinelCheckError: If a root directory is missing.
    """
    files: list[Path] = []
    for root in roots:
        base = _REPO_ROOT / root
        if not base.is_dir():
            raise SentinelCheckError(f"scan root missing: {base} (cannot verify reachability)")
        for path in sorted(base.rglob("*.py")):
            if is_test_source(path):
                continue
            if "node_modules" in path.parts or "__pycache__" in path.parts:
                continue
            files.append(path)
    return files


def _local_alias(tree: ast.Module, symbol: str) -> str | None:
    """The local name ``symbol`` is bound to, if imported under an alias.

    Resolves ``from <module> import <symbol> as <alias>`` — the shape
    ``value_form.py`` uses for ``is_labor_aristocracy`` (imported as
    ``_is_labor_aristocracy`` to avoid colliding with the
    :class:`~babylon.domain.dialectics.instances.value_form.ClassPhiReading`
    field of the same bare name). Scoped to a single file (module-level
    ``ImportFrom`` only) — mirrors :mod:`babylon.sentinels.inert`'s own
    single-file scope boundary.

    :param tree: A parsed module.
    :param symbol: The bare symbol name to look for.
    :returns: The local alias name if ``symbol`` is imported ``as`` one;
        ``None`` if ``symbol`` is not imported under an alias in this file
        (including "not imported at all" and "imported under its own name").
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        for alias in node.names:
            if alias.name == symbol and alias.asname is not None:
                return alias.asname
    return None


def formula_reference_sites(path: Path, symbol: str) -> list[int]:
    """Line numbers in ``path`` where ``symbol`` is referenced as production code.

    Counts any :class:`ast.Name` (matching ``symbol`` OR its same-file
    import alias, see :func:`_local_alias`) or :class:`ast.Attribute`
    (matching ``symbol`` as the attribute name — the module-qualified form,
    e.g. ``formulas.calculate_x``, which is never affected by a LOCAL alias)
    in a ``Load`` context. A bare string-literal mention (a docstring, an
    ``__all__`` entry, a ``concept_cards.py`` citation) is never a match —
    see the module docstring's Scope note for why that exclusion is
    deliberate.

    :param path: Source file to parse.
    :param symbol: The formula's bare module-level function name.
    :returns: Sorted, de-duplicated line numbers of matching reference sites.
    :raises SentinelCheckError: If ``path`` is missing or unparseable.
    """
    tree = _parse(path)
    alias = _local_alias(tree, symbol)
    name_targets = {symbol} if alias is None else {symbol, alias}
    sites: set[int] = set()
    for node in ast.walk(tree):
        # Two distinct node shapes both count as a reference (module-qualified
        # ``formulas.symbol`` attribute access is never affected by a LOCAL
        # import alias, so it is checked against the bare ``symbol`` only) --
        # kept as separate isinstance-narrowed branches (not merged via `or`)
        # so mypy narrows ``node`` to a type that actually declares
        # ``.lineno`` at each ``sites.add`` call.
        if (  # noqa: SIM114 -- see comment above; merging loses type narrowing
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id in name_targets
        ):
            sites.add(node.lineno)
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.ctx, ast.Load)
            and node.attr == symbol
        ):
            sites.add(node.lineno)
    return sorted(sites)


def formulas_without_production_caller(
    registry: tuple[DeclaredFormula, ...] = DECLARED_FORMULAS,
) -> list[str]:
    """Every declared formula's symbol needs a real production caller.

    :param registry: The rows to check (defaults to the real
        :data:`DECLARED_FORMULAS`; injectable so tests can supply a
        deliberately-uncalled row to prove the sensor reds).
    :returns: One violation string per unreferenced formula (empty when
        every row is reachable or exempted). Reads
        :data:`~babylon.sentinels.formula_registration.registry.FORMULA_EXEMPTIONS`
        as a live module global (not a bound default) so tests can
        ``monkeypatch`` it for the mutation-validation cases.
    :raises SentinelCheckError: If a scan root is missing or a file is
        unparseable (exit 2 — infrastructure failure, never a silent pass).
    """
    files = [
        path
        for path in _production_files()
        if path.relative_to(_REPO_ROOT).as_posix() != FORMULA_REGISTRY_FILE
    ]
    violations: list[str] = []
    for row in registry:
        if is_exempt(("formula", row.name), FORMULA_EXEMPTIONS):
            continue
        sites: list[str] = []
        for path in files:
            for lineno in formula_reference_sites(path, row.symbol):
                sites.append(f"{path.relative_to(_REPO_ROOT).as_posix()}:{lineno}")
        if sites:
            continue
        violations.append(
            f"formula {row.name!r} ({row.symbol} in {row.def_file}) has NO production "
            f"reference anywhere in {PRODUCTION_ROOTS} other than its own "
            f"{FORMULA_REGISTRY_FILE} registration.\n"
            f"    what it computes: {row.what_it_computes}\n"
            "    fix: wire a real production caller, or add a reasoned SentinelExemption "
            "(key=('formula', name), reason, owner, date, tracking_task) to "
            "FORMULA_EXEMPTIONS -- never a silent registry removal.\n"
            f"    {_WHY}"
        )
    return sorted(violations)


_GATING_CHECKS: Final[tuple[LabelledCheck, ...]] = (
    ("dead-formula-registration", formulas_without_production_caller),
)


def _summary(advisory_count: int) -> str:
    """Clean one-line summary: the counts actually enforced.

    :param advisory_count: Number of advisory findings (0 — no advisory tier).
    :returns: The summary line.
    """
    _ = advisory_count  # This sentinel declares no advisory tier.
    return (
        f"FORMULA_REGISTRATION clean: {len(DECLARED_FORMULAS)} declared formula(s) all have "
        "a production caller or a recorded exemption."
    )


def main(argv: list[str] | None = None) -> int:
    """Run the dead-formula-registration check and return the exit code.

    :param argv: CLI args (``--check`` is accepted as the CI-mode alias; the
        behavior is always to gate).
    :returns: 0 clean, 1 gating violations found, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description="Dead-formula-registration -- static gate (III.10 / III.11 / VIII.12)."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)
    return run_sensor("FORMULA_REGISTRATION", _GATING_CHECKS, (), _summary)


if __name__ == "__main__":
    sys.exit(main())
