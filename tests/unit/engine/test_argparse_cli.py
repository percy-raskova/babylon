"""Unit tests for the headless runner argparse CLI (T020, spec-064).

Validates every flag in ``contracts/cli_contract.yaml`` is accepted and
that conflicting / malformed inputs surface as argparse errors. Wrapped
in ``pytest-timeout`` to enforce SC-006 (< 30 s per CLI invocation).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.engine.headless_runner.argparse_cli import build_parser

pytestmark = pytest.mark.timeout(30)


class TestArgparseFlags:
    """Every flag from cli_contract.yaml is accepted with correct types."""

    def test_defaults_match_contract(self) -> None:
        args = build_parser().parse_args([])
        assert args.ticks == 1000
        assert args.start_year == 2010
        assert args.seed == 2010
        assert args.scope == "michigan-canada"
        assert args.fips is None
        assert args.external == "canada"
        assert args.output_dir is None
        assert args.defines is None
        assert args.verbose == "INFO"
        assert args.dry_run is False
        assert args.sqlite_path == Path("data/sqlite/marxist-data-3NF.sqlite")

    def test_ticks_accepts_int(self) -> None:
        args = build_parser().parse_args(["--ticks", "42"])
        assert args.ticks == 42

    def test_start_year_accepts_int(self) -> None:
        args = build_parser().parse_args(["--start-year", "2015"])
        assert args.start_year == 2015

    def test_seed_accepts_int(self) -> None:
        args = build_parser().parse_args(["--seed", "31337"])
        assert args.seed == 31337

    @pytest.mark.parametrize(
        "scope",
        [
            "michigan-canada",
            "michigan-statewide-no-canada",
            "detroit-tri-county",
            "national",
        ],
    )
    def test_scope_accepts_predefined_names(self, scope: str) -> None:
        args = build_parser().parse_args(["--scope", scope])
        assert args.scope == scope

    def test_fips_accepts_comma_separated_string(self) -> None:
        args = build_parser().parse_args(["--fips", "26163,26125,26099"])
        assert args.fips == "26163,26125,26099"

    def test_output_dir_accepts_path(self, tmp_path: Path) -> None:
        target = tmp_path / "custom"
        args = build_parser().parse_args(["--output-dir", str(target)])
        assert args.output_dir == target

    def test_defines_accepts_path(self, tmp_path: Path) -> None:
        overlay = tmp_path / "overlay.toml"
        args = build_parser().parse_args(["--defines", str(overlay)])
        assert args.defines == overlay

    def test_verbose_accepts_short_flag(self) -> None:
        args = build_parser().parse_args(["-v", "DEBUG"])
        assert args.verbose == "DEBUG"

    def test_dry_run_is_boolean_flag(self) -> None:
        args = build_parser().parse_args(["--dry-run"])
        assert args.dry_run is True

    def test_unknown_scope_rejected(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            build_parser().parse_args(["--scope", "atlantis"])
        # argparse raises SystemExit(2) on usage errors
        assert exc_info.value.code == 2

    def test_invalid_verbose_rejected(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            build_parser().parse_args(["-v", "LOUD"])
        assert exc_info.value.code == 2


class TestScopeFipsMutuallyExclusive:
    """--scope and --fips are mutually exclusive (spec FR / cli_contract.yaml)."""

    def test_both_specified_rejected(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            build_parser().parse_args(
                ["--scope", "detroit-tri-county", "--fips", "26163,26125"],
            )
        assert exc_info.value.code == 2
