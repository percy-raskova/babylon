"""Behavioral contract tests for the Observability Spine (T1.2 / K1).

Pins the four acceptance criteria from
``ai/_inbox/PROGRAM_v1_0_0_playable_archive.md`` §F "Observability Spine":

1. Central ``dictConfig`` applies cleanly for the ``babylon.*`` logger tree.
2. The rotating file handler emits structured, parseable JSONL records.
3. Per-subsystem level overrides (the ``LoggingConfig`` surface — an infra
   config seam, NOT a ``GameDefines`` category) still work after the
   ``dictConfig`` conversion.
4. Engine hot-path modules gained no new ``import logging`` as a side effect
   of this unit (a regression sentinel against sneaking logging into the
   deterministic tick loop).

Plus two supporting contracts this unit's sweep depends on:

* the shared player-data-dir (XDG) resolution used by both model
  provisioning and log file placement,
* the ad-hoc ``logging.basicConfig`` sweep across ``tools/*.py`` and the two
  ``src/`` entry points is complete (no stragglers left behind).

Superseded in part by T1.1's seam-algebra "config-less-logging" sentinel
once that lane lands (see the plan's spine A) — this file is the K1-local
pin until then.
"""

from __future__ import annotations

import ast
import json
import logging
import logging.config
from pathlib import Path

import pytest

from babylon.config.logging_config import (
    LoggingConfig,
    _build_dict_config,
    setup_logging,
)
from babylon.config.paths import player_data_dir

REPO_ROOT = Path(__file__).resolve().parents[3]

#: Tool/entry-point files swept off ad-hoc `logging.basicConfig` onto the
#: central spine by this unit. Kept explicit (not a glob) so a new tool
#: script added later that reintroduces `basicConfig` is caught by the
#: "no basicConfig anywhere in this list" assertion below, and so a NEW
#: ad-hoc call site elsewhere is a conscious addition to this list, not a
#: silent regression.
SWEPT_ENTRY_POINTS: tuple[Path, ...] = (
    REPO_ROOT / "tools" / "validate_bea_io_against_shaikh.py",
    REPO_ROOT / "tools" / "validate_detroit.py",
    REPO_ROOT / "tools" / "vertical_slice.py",
    REPO_ROOT / "tools" / "load_bea_io.py",
    REPO_ROOT / "tools" / "ingest_tiger_geometry.py",
    REPO_ROOT / "tools" / "narrative_sweep.py",
    REPO_ROOT / "tools" / "ingest_corpus.py",
    REPO_ROOT / "tools" / "demo_substrate.py",
    REPO_ROOT / "src" / "babylon" / "persistence" / "tiger_ingestion.py",
    REPO_ROOT / "src" / "babylon" / "engine" / "headless_runner" / "runner.py",
)

#: Baseline of engine/formulas files that already imported `logging` before
#: this unit (captured 2026-07-21, pre-K1). A file appearing here is fine;
#: any OTHER engine/formulas file importing `logging` is new and must be
#: added here deliberately (or removed if it was retired) — never silently.
ENGINE_HOT_PATH_LOGGING_BASELINE: frozenset[str] = frozenset(
    {
        "engine/bifurcation_monitor.py",
        "engine/field_registry.py",
        "engine/headless_runner/bridge.py",
        "engine/headless_runner/runner.py",
        "engine/headless_runner/storage_probe.py",
        "engine/hydration/reference.py",
        "engine/observer_adapter.py",
        "engine/observers/causal.py",
        "engine/observers/economic.py",
        "engine/observers/endgame_detector.py",
        "engine/observers/session_recorder.py",
        "engine/optimization/bayesian.py",
        "engine/scenarios/_legacy.py",
        "engine/simulation_engine.py",
        "engine/simulation/_legacy.py",
        "engine/systems/community.py",
        "engine/systems/contradiction_field.py",
        "engine/systems/cross_border_commute.py",
        "engine/systems/distribution.py",
        "engine/systems/edge_transition/_legacy.py",
        "engine/systems/event_template.py",
        "engine/systems/field_derivative.py",
        "engine/systems/lifecycle.py",
        "engine/systems/phi_distribution.py",
        "engine/systems/production.py",
        "engine/systems/substrate.py",
        "engine/systems/vol2_circulation.py",
        "engine/topology_monitor.py",
        "formulas/consciousness.py",
    }
)


def _imports_logging(source: str) -> bool:
    """True if the module imports the stdlib ``logging`` package at all."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(a.name == "logging" for a in node.names):
            return True
        if isinstance(node, ast.ImportFrom) and node.module == "logging":
            return True
    return False


def _basicconfig_calls(source: str) -> list[str]:
    """Return a description of every `logging.basicConfig(...)`/`basicConfig(...)` call."""
    tree = ast.parse(source)
    findings: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "basicConfig":
            findings.append("logging.basicConfig(...)")
        elif isinstance(func, ast.Name) and func.id == "basicConfig":
            findings.append("basicConfig(...)")
    return findings


@pytest.fixture(autouse=True)
def _reset_root_logger() -> None:
    """Every test in this module configures the real root logger; restore
    a clean slate afterward so later test modules aren't affected."""
    yield
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    root.setLevel(logging.WARNING)


# =============================================================================
# 1. player_data_dir — the shared XDG resolution this unit's JSONL handler
#    and model provisioning both reuse.
# =============================================================================


@pytest.mark.unit
class TestPlayerDataDir:
    def test_prefers_xdg_data_home(self, tmp_path: Path) -> None:
        got = player_data_dir({"XDG_DATA_HOME": str(tmp_path)})
        assert got == tmp_path / "babylon"

    def test_falls_back_to_local_share(self) -> None:
        got = player_data_dir({})
        assert got.name == "babylon"
        assert got.parent.name == "share"
        assert got.parent.parent.name == ".local"

    def test_models_dir_and_log_dir_share_one_player_data_root(self, tmp_path: Path) -> None:
        """Model weights and logs both live under one player-data root — the
        exact "find the existing convention and reuse it" contract."""
        from babylon.intelligence.provision import default_models_dir

        env = {"XDG_DATA_HOME": str(tmp_path)}
        assert default_models_dir(env).parent == player_data_dir(env)


# =============================================================================
# 2. dictConfig applies cleanly
# =============================================================================


@pytest.mark.unit
class TestDictConfigAppliesCleanly:
    def test_build_dict_config_is_accepted_by_dictconfig(self, tmp_path: Path) -> None:
        """The dict `_build_dict_config` produces must be a valid dictConfig
        payload — this IS "dictConfig applies cleanly": a malformed dict
        (bad class path, missing required key, bad level name) would raise
        here, not silently degrade."""
        config = LoggingConfig(console_level="INFO", file_level="DEBUG")

        logging.config.dictConfig(_build_dict_config(config, tmp_path))

        root = logging.getLogger()
        assert len(root.handlers) == 3
        handler_classes = {type(h).__name__ for h in root.handlers}
        assert handler_classes == {"StreamHandler", "RotatingFileHandler"}

    def test_file_handlers_use_the_configured_directory(self, tmp_path: Path) -> None:
        config = LoggingConfig()
        logging.config.dictConfig(_build_dict_config(config, tmp_path))

        from logging.handlers import RotatingFileHandler

        file_handlers = [
            h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler)
        ]
        assert len(file_handlers) == 2
        for handler in file_handlers:
            assert Path(handler.baseFilename).parent == tmp_path

    def test_setup_logging_default_path_goes_through_dictconfig(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`setup_logging()` with no `config_path` (the default, most-used
        path) is wired through `logging.config.dictConfig`, not a hand-rolled
        handler-by-handler construction — this is the "central" in "central
        dictConfig for the babylon.* logger tree"."""
        monkeypatch.setattr("babylon.config.logging_config.BaseConfig.LOG_DIR", tmp_path)
        calls: list[dict[str, object]] = []
        real_dictconfig = logging.config.dictConfig

        def _spy(cfg: dict[str, object]) -> None:
            calls.append(cfg)
            real_dictconfig(cfg)

        monkeypatch.setattr(logging.config, "dictConfig", _spy)

        setup_logging()

        assert len(calls) == 1
        assert calls[0]["version"] == 1
        assert "root" in calls[0]

    def test_logging_yaml_override_applies_cleanly(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The repo-root ``logging.yaml`` operator override (referenced by
        ``setup_logging(config_path=...)``) is itself a dictConfig payload
        that must apply without raising. Regression guard for a real bug
        found during the K1 sweep: it pointed ``json.class`` at
        ``babylon.utils.log.JSONFormatter``, a module retired by the kernel
        absorption refactor (now ``babylon.kernel.log``) — dictConfig would
        raise ``ImportError`` the moment anyone actually used this file."""
        monkeypatch.setattr("babylon.config.logging_config.BaseConfig.LOG_DIR", tmp_path)
        setup_logging(config_path=REPO_ROOT / "logging.yaml")

        root = logging.getLogger()
        assert len(root.handlers) == 3


# =============================================================================
# 3. Structured JSONL file handler emits parseable records
# =============================================================================


@pytest.mark.unit
class TestJSONLHandlerEmitsParseableRecords:
    def test_every_line_of_the_main_log_is_valid_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("babylon.config.logging_config.BaseConfig.LOG_DIR", tmp_path)
        setup_logging(default_level="DEBUG")

        logger = logging.getLogger("test.observability_spine.jsonl")
        logger.info("first record", extra={"tick": 7})
        logger.warning("second record")
        logger.error("third record", extra={"correlation_id": "abc-123"})

        main_log = tmp_path / "babylon.log"
        assert main_log.exists()
        lines = [line for line in main_log.read_text().splitlines() if line.strip()]
        assert len(lines) >= 3

        parsed = [json.loads(line) for line in lines]  # raises if any line isn't valid JSON
        messages = {record["msg"] for record in parsed}
        assert {"first record", "second record", "third record"} <= messages

        tick_record = next(r for r in parsed if r["msg"] == "first record")
        assert tick_record["tick"] == 7
        assert tick_record["level"] == "INFO"
        assert tick_record["logger"] == "test.observability_spine.jsonl"

        correlation_record = next(r for r in parsed if r["msg"] == "third record")
        assert correlation_record["correlation_id"] == "abc-123"

    def test_error_only_log_contains_only_error_and_above(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("babylon.config.logging_config.BaseConfig.LOG_DIR", tmp_path)
        setup_logging(default_level="DEBUG")

        logger = logging.getLogger("test.observability_spine.errors_only")
        logger.info("should not appear in errors.log")
        logger.error("should appear in errors.log")

        error_log = tmp_path / "errors.log"
        lines = [line for line in error_log.read_text().splitlines() if line.strip()]
        parsed = [json.loads(line) for line in lines]
        messages = {record["msg"] for record in parsed}
        assert "should appear in errors.log" in messages
        assert "should not appear in errors.log" not in messages


# =============================================================================
# 4. Per-subsystem level override survives the dictConfig conversion
# =============================================================================


@pytest.mark.unit
class TestPerSubsystemLevelOverride:
    def test_module_level_override_applies_after_dictconfig(self, tmp_path: Path) -> None:
        config = LoggingConfig(
            modules={"test.observability_spine.subsystem": "ERROR"},
        )
        logging.config.dictConfig(_build_dict_config(config, tmp_path))

        from babylon.config.logging_config import _apply_module_levels

        _apply_module_levels(config.modules)

        assert logging.getLogger("test.observability_spine.subsystem").level == logging.ERROR
        # An untouched logger is unaffected by the override.
        assert logging.getLogger("test.observability_spine.other").level == logging.NOTSET

    def test_setup_logging_applies_pyproject_modules_end_to_end(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.babylon.logging.modules]\n"test.observability_spine.e2e" = "CRITICAL"\n'
        )
        log_dir = tmp_path / "logs"
        monkeypatch.setattr("babylon.config.logging_config.BaseConfig.LOG_DIR", log_dir)
        monkeypatch.delenv("LOG_LEVEL", raising=False)

        setup_logging(pyproject_path=pyproject)

        assert logging.getLogger("test.observability_spine.e2e").level == logging.CRITICAL


# =============================================================================
# Sweep completeness: no ad-hoc basicConfig left in the swept entry points
# =============================================================================


@pytest.mark.unit
class TestBasicConfigSweepComplete:
    @pytest.mark.parametrize("path", SWEPT_ENTRY_POINTS, ids=lambda p: p.name)
    def test_entry_point_has_no_basicconfig_call(self, path: Path) -> None:
        assert path.exists(), f"expected swept entry point not found: {path}"
        findings = _basicconfig_calls(path.read_text())
        assert not findings, f"{path} still calls basicConfig: {findings}"

    def test_cli_root_wires_the_central_setup_logging_call(self) -> None:
        """The real shipped entry point (`babylon` = `babylon.cli:app`) must
        call the central `setup_logging()` — this was the actual gap K1
        closed (the old `babylon.__main__` demo already did this; the real
        Typer app never did)."""
        cli_init = REPO_ROOT / "src" / "babylon" / "cli" / "__init__.py"
        tree = ast.parse(cli_init.read_text())
        module_level_calls = {
            node.value.func.id
            for node in tree.body
            if isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
        }
        assert "setup_logging" in module_level_calls


# =============================================================================
# No new `import logging` in engine hot paths
# =============================================================================


@pytest.mark.unit
class TestNoNewLoggingImportsInEngineHotPaths:
    def test_baseline_files_still_import_logging(self) -> None:
        """Sanity check the baseline itself hasn't silently gone stale."""
        for rel in sorted(ENGINE_HOT_PATH_LOGGING_BASELINE):
            path = REPO_ROOT / "src" / "babylon" / rel
            assert path.exists(), f"baseline file vanished: {rel}"
            assert _imports_logging(path.read_text()), (
                f"baseline file no longer imports logging: {rel}"
            )

    def test_no_engine_or_formulas_file_gained_a_new_logging_import(self) -> None:
        """Every `src/babylon/engine/**` and `src/babylon/formulas/**` file
        that imports `logging` must be in the pre-K1 baseline. A new entry
        means this unit (or a future one) added `import logging` to the
        deterministic tick loop's hot path — a decision that must be made
        deliberately (update the baseline), never as a silent side effect."""
        offenders: list[str] = []
        for root_dir in ("engine", "formulas"):
            base = REPO_ROOT / "src" / "babylon" / root_dir
            for path in sorted(base.rglob("*.py")):
                rel = str(path.relative_to(REPO_ROOT / "src" / "babylon"))
                if (
                    _imports_logging(path.read_text())
                    and rel not in ENGINE_HOT_PATH_LOGGING_BASELINE
                ):
                    offenders.append(rel)
        assert not offenders, (
            f"new `import logging` in engine/formulas hot path(s) not in the K1 baseline: {offenders}"
        )
