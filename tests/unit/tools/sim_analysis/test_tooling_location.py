"""Location contract for the development-only simulation analysis suite."""

from __future__ import annotations

import tomllib
from importlib.util import find_spec
from pathlib import Path

import pytest
from tools.devtools.sim_analysis.__main__ import build_parser


def test_sim_analysis_is_tooling_not_an_installable_game_package() -> None:
    """Analysis code lives under ``tools`` and leaves no game-package alias."""
    repository_root = Path(__file__).resolve().parents[4]
    tooling_root = repository_root / "tools" / "devtools" / "sim_analysis"

    tooling_spec = find_spec("tools.devtools.sim_analysis")

    assert tooling_spec is not None
    assert tooling_spec.origin == str(tooling_root / "__init__.py")
    assert find_spec("babylon.engine.optimization") is None
    project = tomllib.loads((repository_root / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == ["src/babylon"]


@pytest.mark.parametrize(
    ("argv", "command"),
    [
        (["sweep", "--param", "economy.base_subsistence=0.1:0.2:0.1"], "sweep"),
        (["monte-carlo"], "monte-carlo"),
        (["sensitivity", "--method", "morris"], "sensitivity"),
        (["sensitivity", "--method", "sobol"], "sensitivity"),
        (["bayesian"], "bayesian"),
    ],
)
def test_cli_keeps_each_analysis_capability(argv: list[str], command: str) -> None:
    """The moved CLI retains sweep, Monte Carlo, Morris/Sobol, and Optuna entry points."""
    assert build_parser().parse_args(argv).command == command


def test_sensitivity_cli_exposes_final_wealth_objective() -> None:
    args = build_parser().parse_args(
        ["sensitivity", "--method", "both", "--objective", "final-wealth"]
    )

    assert args.objective == "final-wealth"


def test_final_wealth_cli_choice_is_scoped_to_sensitivity() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            [
                "sweep",
                "--param",
                "economy.base_subsistence=0.1:0.2:0.1",
                "--objective",
                "final-wealth",
            ]
        )


def test_bayesian_cli_accepts_an_artifact_output_directory(tmp_path: Path) -> None:
    args = build_parser().parse_args(["bayesian", "--output-dir", str(tmp_path)])

    assert args.output_dir == tmp_path


def test_bayesian_cli_rejects_ambiguous_storage_and_output_directory(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            [
                "bayesian",
                "--storage",
                "sqlite:///study.sqlite3",
                "--output-dir",
                str(tmp_path),
            ]
        )
