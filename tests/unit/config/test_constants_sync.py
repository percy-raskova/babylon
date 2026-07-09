"""Verify TestConstants stays in sync with GameDefines.

This test ensures that the YAML-first constants architecture is working correctly.
TestConstants values should be loaded from GameDefines, which loads from defines.yaml.

If this test fails, it means:
1. A value was changed in defines.yaml but not in TestConstants
2. A new constant was added to GameDefines but not exposed in TestConstants
3. The import path has changed
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from babylon.config.defines import GameDefines
from tests.constants import TestConstants

TC = TestConstants

_REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.unit
class TestConstantsSync:
    """Verify TestConstants matches GameDefines values."""

    def test_pool_thresholds_match(self) -> None:
        """Pool ratio thresholds should match GameDefines.economy."""
        defines = GameDefines.load_default()

        assert defines.economy.pool_high_threshold == TC.Canon.POOL_HIGH
        assert defines.economy.pool_low_threshold == TC.Canon.POOL_LOW
        assert defines.economy.pool_critical_threshold == TC.Canon.POOL_CRITICAL

    def test_economic_baselines_match(self) -> None:
        """Economic baseline values should match GameDefines."""
        defines = GameDefines.load_default()

        assert defines.economy.initial_rent_pool == TC.Canon.INITIAL_RENT_POOL
        assert defines.survival.default_repression == TC.Canon.DEFAULT_REPRESSION
        assert defines.economy.extraction_efficiency == TC.Canon.DEFAULT_EXTRACTION

    def test_behavioral_constants_match(self) -> None:
        """Behavioral economics constants should match GameDefines."""
        defines = GameDefines.load_default()

        assert defines.behavioral.loss_aversion_lambda == TC.Behavioral.LOSS_AVERSION

    def test_solidarity_constants_match(self) -> None:
        """Solidarity constants should match GameDefines."""
        defines = GameDefines.load_default()

        assert defines.solidarity.activation_threshold == TC.Solidarity.ACTIVATION_THRESHOLD
        assert defines.solidarity.mass_awakening_threshold == TC.Solidarity.MASS_AWAKENING_THRESHOLD

    def test_bourgeoisie_decision_constants_match(self) -> None:
        """Bourgeoisie decision constants should match GameDefines.economy."""
        defines = GameDefines.load_default()

        assert (
            defines.economy.bribery_tension_threshold
            == TC.BourgeoisieDecision.BRIBERY_TENSION_THRESHOLD
        )
        assert (
            defines.economy.iron_fist_tension_threshold
            == TC.BourgeoisieDecision.IRON_FIST_TENSION_THRESHOLD
        )
        assert defines.economy.bribery_wage_delta == TC.BourgeoisieDecision.BRIBERY_WAGE_DELTA
        assert defines.economy.austerity_wage_delta == TC.BourgeoisieDecision.AUSTERITY_WAGE_DELTA
        assert (
            defines.economy.iron_fist_repression_delta
            == TC.BourgeoisieDecision.IRON_FIST_REPRESSION_DELTA
        )
        assert defines.economy.crisis_wage_delta == TC.BourgeoisieDecision.CRISIS_WAGE_DELTA
        assert (
            defines.economy.crisis_repression_delta
            == TC.BourgeoisieDecision.CRISIS_REPRESSION_DELTA
        )

    def test_trpf_constants_match(self) -> None:
        """TRPF constants should match GameDefines.economy."""
        defines = GameDefines.load_default()

        assert defines.economy.trpf_coefficient == TC.TRPF.TRPF_COEFFICIENT
        assert defines.economy.rent_pool_decay == TC.TRPF.RENT_POOL_DECAY
        assert defines.economy.trpf_efficiency_floor == TC.TRPF.EFFICIENCY_FLOOR

    def test_timescale_constants_match(self) -> None:
        """Timescale constants should match GameDefines.timescale."""
        defines = GameDefines.load_default()

        assert defines.timescale.weeks_per_year == TC.Timescale.TICKS_PER_YEAR
        assert defines.timescale.tick_duration_days == TC.Timescale.DAYS_PER_TICK

    def test_metabolic_rift_constants_match(self) -> None:
        """Metabolic rift constants should match GameDefines.metabolism."""
        defines = GameDefines.load_default()

        assert defines.metabolism.entropy_factor == TC.MetabolicRift.ENTROPY_FACTOR
        assert defines.metabolism.max_overshoot_ratio == TC.MetabolicRift.MAX_OVERSHOOT_RATIO

    def test_quantization_constants_match(self) -> None:
        """Quantization constants should match GameDefines.precision."""
        defines = GameDefines.load_default()

        assert defines.precision.decimal_places == TC.Quantization.DECIMAL_PLACES
        assert defines.precision.epsilon == TC.Quantization.EPSILON
        assert 10 ** (-defines.precision.decimal_places) == TC.Quantization.GRID_PRECISION
        # Verify epsilon hierarchy: GRID (1e-6) > EPSILON (1e-9) > COMPARISON (1e-10)
        assert defines.precision.epsilon < TC.Quantization.GRID_PRECISION
        assert defines.precision.epsilon > defines.precision.comparison_epsilon


@pytest.mark.unit
class TestFormulasConstantsSync:
    """Verify formula module re-exports match GameDefines."""

    def test_epsilon_matches_game_defines(self) -> None:
        """EPSILON in formulas package should match GameDefines.precision.epsilon."""
        from babylon.formulas import EPSILON

        defines = GameDefines.load_default()
        assert defines.precision.epsilon == EPSILON

    def test_loss_aversion_matches_game_defines(self) -> None:
        """LOSS_AVERSION_COEFFICIENT should match GameDefines.behavioral."""
        from babylon.formulas import LOSS_AVERSION_COEFFICIENT

        defines = GameDefines.load_default()
        assert defines.behavioral.loss_aversion_lambda == LOSS_AVERSION_COEFFICIENT

    def test_hours_per_year_matches_game_defines(self) -> None:
        """HOURS_PER_YEAR re-export should match GameDefines.timescale."""
        from babylon.formulas.constants import HOURS_PER_YEAR

        defines = GameDefines.load_default()
        assert defines.timescale.hours_per_year == HOURS_PER_YEAR

    def test_weeks_per_year_matches_game_defines(self) -> None:
        """WEEKS_PER_YEAR re-export should match GameDefines.timescale."""
        from babylon.formulas.constants import WEEKS_PER_YEAR

        defines = GameDefines.load_default()
        assert defines.timescale.weeks_per_year == WEEKS_PER_YEAR

    def test_topology_monitor_fields_in_game_defines(self) -> None:
        """New TopologyDefines fields should have expected defaults."""
        defines = GameDefines.load_default()
        topo = defines.topology
        assert topo.brittle_multiplier == 2.0
        assert topo.solidarity_sympathizer_threshold == 0.1
        assert topo.solidarity_cadre_threshold == 0.5
        assert topo.resilience_removal_rate == 0.2
        assert topo.resilience_survival_threshold == 0.4


@pytest.mark.unit
class TestDefinesYamlSingleSourceOfTruth:
    """Guard the canonical player-editable ``defines.yaml`` against silent re-forking.

    Phase B of the src/ simplification sweep made ``src/babylon/data/defines.yaml``
    the single, documented, player-editable source of truth for every game
    coefficient (generated from the ``GameDefines`` schema by
    ``tools/generate_defines_config.py``). These tests ensure the shipped file
    stays a faithful render of the schema defaults and that timescale constants
    are not re-declared ad hoc outside the canon.
    """

    def test_shipped_defines_yaml_roundtrips_to_defaults(self) -> None:
        """The shipped defines.yaml must reconstruct GameDefines() exactly."""
        path = GameDefines.default_yaml_path()
        assert path.exists(), "canonical defines.yaml is missing"
        assert GameDefines.load_from_yaml(path) == GameDefines()

    def test_load_default_matches_schema_defaults(self) -> None:
        """load_default() (which now reads the yaml) must equal the schema defaults.

        This is the anti-drift guard: if a schema default changes but the shipped
        yaml is not regenerated (or vice versa), the two diverge and this fails.
        """
        assert GameDefines.load_default() == GameDefines()

    def test_defines_yaml_in_sync_with_schema(self) -> None:
        """The committed defines.yaml must match a fresh render of the schema.

        Runs the generator's ``--check`` mode; a non-zero exit means the schema
        changed (new field, changed default, updated description) without
        regenerating ``defines.yaml``.
        """
        tool = _REPO_ROOT / "tools" / "generate_defines_config.py"
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell, trusted path
            [sys.executable, str(tool), "--check"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            "defines.yaml is stale — regenerate with "
            "'poetry run python tools/generate_defines_config.py'.\n"
            f"stderr:\n{result.stderr}"
        )

    def test_no_readded_timescale_constants(self) -> None:
        """No module may re-declare HOURS_PER_YEAR / WEEKS_PER_YEAR outside the canon.

        The canonical definitions live in formulas/constants.py (sourced from
        GameDefines.timescale) plus the documented sim_clock.py leaf-module copy.
        A re-declaration anywhere else re-forks the constant the sweep centralized.
        """
        src_root = _REPO_ROOT / "src" / "babylon"
        allowed = {"formulas/constants.py", "sim_clock.py"}
        pattern = re.compile(r"^\s*_?(?:HOURS_PER_YEAR|WEEKS_PER_YEAR)\s*[:=]")
        offenders: list[str] = []
        for py in src_root.rglob("*.py"):
            rel = py.relative_to(src_root).as_posix()
            if rel in allowed:
                continue
            for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                if pattern.match(line):
                    offenders.append(f"{rel}:{lineno}: {line.strip()}")
        assert not offenders, "Re-declared timescale constant outside the canon:\n" + "\n".join(
            offenders
        )
