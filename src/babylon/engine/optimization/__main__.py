"""``python -m babylon.engine.optimization`` entry point.

Argparse CLI over the optimization package's four algorithms — ``sweep``,
``monte-carlo``, ``sensitivity``, and ``bayesian`` — each dispatching to its
module's single ``run_*`` entry point (:func:`~babylon.engine.optimization.sweep.run_sweep`,
:func:`~babylon.engine.optimization.monte_carlo.run_monte_carlo`,
:func:`~babylon.engine.optimization.sensitivity.run_sensitivity`,
:func:`~babylon.engine.optimization.bayesian.run_bayesian`). Every subcommand
shares a ``--backend {headless,in-memory}`` flag (translated to the
``"headless"``/``"in_memory"`` strings :func:`~babylon.engine.optimization.runner_api.run`
expects); ``sweep``'s ``--param``/``--param2`` and ``monte-carlo``'s repeated
``--param`` are validated eagerly through
:mod:`~babylon.engine.optimization.ranges` so a malformed spec fails at the
CLI boundary with a clean usage error, not deep inside a trial.

This module only builds the parser and maps parsed args to each ``run_*``
call's keyword arguments — no algorithm logic lives here.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from babylon.engine.optimization import (
    run_bayesian,
    run_monte_carlo,
    run_sensitivity,
    run_sweep,
)
from babylon.engine.optimization.objectives import Objective, carceral_objective, survival_objective
from babylon.engine.optimization.ranges import parse_override, parse_range

#: CLI-facing backend names, translated to runner_api's "headless"/"in_memory".
_BACKEND_CHOICES = ("headless", "in-memory")
_BACKEND_TRANSLATION = {"headless": "headless", "in-memory": "in_memory"}

#: CLI-facing objective names for the algorithms that accept one. Excludes
#: ``objectives.endgame_objective``, a documented Track-B stub that always
#: raises ``NotImplementedError`` when called — not offered as a selectable
#: choice until that wiring lands.
_OBJECTIVE_CHOICES: dict[str, Objective] = {
    "carceral": carceral_objective,
    "survival": survival_objective,
}


def _range_spec(spec: str) -> str:
    """Argparse ``type=`` validator for a ``"path=start:end:step"`` range spec.

    Delegates to :func:`~babylon.engine.optimization.ranges.parse_range` for
    validation only; the raw string (not the parsed tuple) is returned so it
    can still be passed straight through to :func:`~babylon.engine.optimization.sweep.run_sweep`,
    which parses it again itself.

    :param spec: Raw ``--param``/``--param2`` value.
    :returns: ``spec`` unchanged, once validated.
    :raises argparse.ArgumentTypeError: If ``spec`` is not ``"path=start:end:step"`` shaped.
    """
    try:
        parse_range(spec)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return spec


def _override_spec(spec: str) -> str:
    """Argparse ``type=`` validator for a ``"path=value"`` override spec.

    Mirrors :func:`_range_spec` but for :func:`~babylon.engine.optimization.ranges.parse_override`,
    used by ``monte-carlo``'s repeated ``--param`` flag.

    :param spec: Raw ``--param`` value.
    :returns: ``spec`` unchanged, once validated.
    :raises argparse.ArgumentTypeError: If ``spec`` is not ``"path=value"`` shaped.
    """
    try:
        parse_override(spec)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return spec


def _add_backend_arg(parser: argparse.ArgumentParser) -> None:
    """Add the shared ``--backend`` flag to a subcommand parser.

    :param parser: Subcommand parser to attach the flag to.
    """
    parser.add_argument(
        "--backend",
        type=str,
        default=None,
        choices=_BACKEND_CHOICES,
        help="Execution backend. Default: each algorithm's own default (headless).",
    )


def _add_scope_scenario_args(parser: argparse.ArgumentParser) -> None:
    """Add the shared ``--scope-name``/``--scenario`` flags to a subcommand parser.

    :param parser: Subcommand parser to attach the flags to.
    """
    parser.add_argument(
        "--scope-name",
        type=str,
        default=None,
        help="Headless scope label (backend=headless only). Default: detroit-tri-county.",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="In-memory scenario name (backend=in-memory only). Default: imperial_circuit.",
    )


def _add_objective_arg(parser: argparse.ArgumentParser) -> None:
    """Add the shared ``--objective`` flag to a subcommand parser.

    :param parser: Subcommand parser to attach the flag to.
    """
    parser.add_argument(
        "--objective",
        type=str,
        default=None,
        choices=sorted(_OBJECTIVE_CHOICES),
        help="Trial scoring function. Default: carceral (Carceral Equilibrium phase-timing).",
    )


def _add_sweep_subparser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Build the ``sweep`` subcommand parser.

    :param subparsers: The top-level parser's subparsers action.
    """
    parser = subparsers.add_parser(
        "sweep",
        help="1D or 2D coefficient sweep (run_sweep).",
        description="Sweep one or two GameDefines coefficients across a range of values.",
    )
    parser.add_argument(
        "--param",
        type=_range_spec,
        required=True,
        metavar="PATH=START:END:STEP",
        help="First (or only) swept parameter, e.g. 'economy.extraction_efficiency=0.1:0.3:0.1'.",
    )
    parser.add_argument(
        "--param2",
        type=_range_spec,
        default=None,
        metavar="PATH=START:END:STEP",
        help="Second swept parameter. If given, sweeps a 2D grid instead of a 1D line.",
    )
    parser.add_argument("--max-ticks", type=int, default=None, help="Maximum ticks per trial.")
    parser.add_argument(
        "--seed", type=int, default=None, help="RNG seed threaded through every trial."
    )
    _add_backend_arg(parser)
    _add_scope_scenario_args(parser)
    _add_objective_arg(parser)
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Write the sweep's CSV artifact here (1D: per-point; 2D: landscape grid).",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        default=False,
        help="Print the Playable Boundary report after a 1D sweep.",
    )


def _add_monte_carlo_subparser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Build the ``monte-carlo`` subcommand parser.

    :param subparsers: The top-level parser's subparsers action.
    """
    parser = subparsers.add_parser(
        "monte-carlo",
        help="Monte Carlo uncertainty quantification over N replications (run_monte_carlo).",
        description="Run N stochastic replications of one GameDefines configuration.",
    )
    parser.add_argument("--n-samples", type=int, default=None, help="Number of simulation samples.")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Base RNG seed each sample's seed is derived from. Default: random.",
    )
    parser.add_argument(
        "--param",
        dest="param_overrides",
        action="append",
        type=_override_spec,
        default=None,
        metavar="PATH=VALUE",
        help="Fixed coefficient override, e.g. 'economy.extraction_efficiency=0.5'. Repeatable.",
    )
    parser.add_argument("--max-ticks", type=int, default=None, help="Maximum ticks per sample.")
    _add_backend_arg(parser)
    _add_scope_scenario_args(parser)
    _add_objective_arg(parser)
    parser.add_argument("--csv-path", type=Path, default=None, help="Output CSV path.")
    parser.add_argument(
        "--report-path", type=Path, default=None, help="Optional markdown report output path."
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress progress and report printing to stdout.",
    )


def _add_sensitivity_subparser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Build the ``sensitivity`` subcommand parser.

    :param subparsers: The top-level parser's subparsers action.
    """
    parser = subparsers.add_parser(
        "sensitivity",
        help="Global sensitivity analysis via Morris/Sobol (run_sensitivity).",
        description="Rank GameDefines coefficients by influence on the objective (SALib).",
    )
    parser.add_argument(
        "--method",
        type=str,
        required=True,
        choices=("morris", "sobol", "both"),
        help="Morris screening, Sobol variance decomposition, or both (Morris then Sobol).",
    )
    parser.add_argument(
        "--param-names",
        type=str,
        default=None,
        metavar="PATH,PATH,...",
        help="Comma-separated parameter paths to analyze. Default: every known tunable parameter.",
    )
    parser.add_argument(
        "--trajectories",
        type=int,
        default=None,
        help="Morris trajectory count (method=morris/both).",
    )
    parser.add_argument(
        "--samples", type=int, default=None, help="Sobol base sample size (method=sobol/both)."
    )
    parser.add_argument("--max-ticks", type=int, default=None, help="Maximum ticks per trial.")
    parser.add_argument(
        "--seed", type=int, default=None, help="RNG seed threaded through every trial."
    )
    _add_backend_arg(parser)
    _add_scope_scenario_args(parser)
    _add_objective_arg(parser)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for morris.json/sobol.json when the explicit outputs aren't given.",
    )
    parser.add_argument(
        "--morris-output", type=Path, default=None, help="Explicit Morris JSON path."
    )
    parser.add_argument("--sobol-output", type=Path, default=None, help="Explicit Sobol JSON path.")
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress progress and report printing to stdout.",
    )


def _add_bayesian_subparser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Build the ``bayesian`` subcommand parser.

    :param subparsers: The top-level parser's subparsers action.
    """
    parser = subparsers.add_parser(
        "bayesian",
        help="Bayesian (Optuna TPE + Hyperband) Carceral Equilibrium tuning (run_bayesian).",
        description="Search GameDefines coefficients for the Carceral Equilibrium objective (Optuna).",
    )
    parser.add_argument(
        "--study-name", type=str, default=None, help="Name for the optimization study."
    )
    parser.add_argument(
        "--storage", type=str, default=None, help="SQLite (or other Optuna-supported) storage URL."
    )
    parser.add_argument(
        "--n-trials",
        type=int,
        default=None,
        help="Number of new trials to run (ignored if --show-best).",
    )
    parser.add_argument("--max-ticks", type=int, default=None, help="Maximum ticks per trial.")
    _add_backend_arg(parser)
    parser.add_argument(
        "--seed", type=int, default=None, help="RNG seed threaded into every trial."
    )
    parser.add_argument(
        "--categories",
        type=str,
        default=None,
        metavar="CATEGORY,CATEGORY,...",
        help="Comma-separated GameDefines categories to search over. Default: TUNING_CATEGORIES.",
    )
    parser.add_argument(
        "--show-best",
        action="store_true",
        default=False,
        help="Skip running new trials; only load and report the existing study.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Construct the argparse parser for the optimization package CLI.

    :returns: Parser with ``sweep``/``monte-carlo``/``sensitivity``/``bayesian`` subcommands.
    """
    parser = argparse.ArgumentParser(
        prog="babylon.engine.optimization",
        description="Babylon GameDefines coefficient optimization: sweep, Monte Carlo, "
        "sensitivity analysis, and Bayesian search over simulation trials.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_sweep_subparser(subparsers)
    _add_monte_carlo_subparser(subparsers)
    _add_sensitivity_subparser(subparsers)
    _add_bayesian_subparser(subparsers)
    return parser


def _kwargs_from(args: argparse.Namespace, *names: str) -> dict[str, Any]:
    """Collect non-``None`` attributes of ``args`` into a kwargs dict.

    Omitting ``None`` values lets each ``run_*`` function's own default
    (declared once, as a ``Final`` constant in its own module) apply when a
    flag wasn't given on the command line, instead of the CLI duplicating
    those defaults.

    :param args: Parsed CLI namespace.
    :param names: Attribute names to collect.
    :returns: ``{name: value}`` for every ``name`` whose value is not ``None``.
    """
    return {name: value for name in names if (value := getattr(args, name)) is not None}


def _dispatch_sweep(args: argparse.Namespace) -> int:
    """Run the ``sweep`` subcommand.

    :param args: Parsed CLI namespace.
    :returns: Process exit code.
    """
    kwargs = _kwargs_from(
        args, "param2", "max_ticks", "seed", "scope_name", "scenario", "output_csv"
    )
    if args.backend is not None:
        kwargs["backend"] = _BACKEND_TRANSLATION[args.backend]
    if args.objective is not None:
        kwargs["objective"] = _OBJECTIVE_CHOICES[args.objective]
    run_sweep(param=args.param, report=args.report, **kwargs)
    return 0


def _dispatch_monte_carlo(args: argparse.Namespace) -> int:
    """Run the ``monte-carlo`` subcommand.

    :param args: Parsed CLI namespace.
    :returns: Process exit code.
    """
    kwargs = _kwargs_from(
        args,
        "n_samples",
        "param_overrides",
        "max_ticks",
        "scope_name",
        "scenario",
        "csv_path",
        "report_path",
    )
    if args.seed is not None:
        kwargs["base_seed"] = args.seed
    if args.backend is not None:
        kwargs["backend"] = _BACKEND_TRANSLATION[args.backend]
    if args.objective is not None:
        kwargs["objective"] = _OBJECTIVE_CHOICES[args.objective]
    run_monte_carlo(progress=not args.quiet, **kwargs)
    return 0


def _dispatch_sensitivity(args: argparse.Namespace) -> int:
    """Run the ``sensitivity`` subcommand.

    :param args: Parsed CLI namespace.
    :returns: Process exit code.
    :raises SystemExit: If SALib is not installed (:data:`run_sensitivity` is ``None``).
    """
    if run_sensitivity is None:
        raise SystemExit(
            "sensitivity analysis requires SALib, which is not installed. "
            "Install the dev dependency group: `poetry install --with dev`."
        )
    kwargs = _kwargs_from(
        args,
        "trajectories",
        "samples",
        "max_ticks",
        "seed",
        "scope_name",
        "scenario",
        "output_dir",
        "morris_output",
        "sobol_output",
    )
    if args.param_names is not None:
        kwargs["param_names"] = [p.strip() for p in args.param_names.split(",") if p.strip()]
    if args.backend is not None:
        kwargs["backend"] = _BACKEND_TRANSLATION[args.backend]
    if args.objective is not None:
        kwargs["objective"] = _OBJECTIVE_CHOICES[args.objective]
    run_sensitivity(args.method, progress=not args.quiet, **kwargs)
    return 0


def _dispatch_bayesian(args: argparse.Namespace) -> int:
    """Run the ``bayesian`` subcommand.

    :param args: Parsed CLI namespace.
    :returns: Process exit code.
    :raises SystemExit: If Optuna is not installed (:data:`run_bayesian` is ``None``).
    """
    if run_bayesian is None:
        raise SystemExit(
            "Bayesian tuning requires optuna, which is not installed. "
            "Install the dev dependency group: `poetry install --with dev`."
        )
    kwargs = _kwargs_from(args, "study_name", "storage", "n_trials", "max_ticks", "seed")
    if args.backend is not None:
        kwargs["backend"] = _BACKEND_TRANSLATION[args.backend]
    if args.categories is not None:
        kwargs["categories"] = [c.strip() for c in args.categories.split(",") if c.strip()]
    run_bayesian(show_best=args.show_best, **kwargs)
    return 0


_DISPATCH = {
    "sweep": _dispatch_sweep,
    "monte-carlo": _dispatch_monte_carlo,
    "sensitivity": _dispatch_sensitivity,
    "bayesian": _dispatch_bayesian,
}


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``python -m babylon.engine.optimization``.

    :param argv: Argument list to parse; defaults to ``sys.argv[1:]`` when ``None``.
    :returns: Process exit code (``0`` on success).
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    return _DISPATCH[args.command](args)


if __name__ == "__main__":  # pragma: no cover - module-execution wrapper
    sys.exit(main())
