"""Integration tests for Detroit scenario preflight validation.

These tests validate the end-to-end preflight system for the Detroit scenario,
ensuring all four data sources (QCEW, LODES, ACS, TIGER) are properly checked
before simulation starts.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.data.preflight import run_scenario_preflight


class TestDetroitScenarioPreflight:
    """Integration tests for Detroit scenario data validation."""

    def test_detroit_preflight_validates_all_four_sources(self, tmp_path: Path) -> None:
        """SC-002: Preflight checks QCEW, LODES, ACS, TIGER for Detroit."""
        (tmp_path / "data").mkdir(parents=True)

        result = run_scenario_preflight("detroit", base_dir=tmp_path)

        # Extract check_id prefixes to verify all sources are checked
        check_ids = {c.check_id for c in result.checks}

        # VerificationProtocol-based checks
        assert any("lodes" in cid for cid in check_ids), "LODES not checked"
        assert any("tiger" in cid for cid in check_ids), "TIGER not checked"
        assert any("census" in cid for cid in check_ids), "Census not checked"

        # Existing _check_* based checks (qcew uses _check_qcew)
        assert any("qcew" in cid for cid in check_ids), "QCEW not checked"

    def test_detroit_partial_data_reports_mixed_results(self, tmp_path: Path) -> None:
        """Story 3, Scenario 3: Partial data shows success + failure mix."""
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True)

        # Set up only QCEW data (via existing _check_qcew pattern)
        qcew_dir = data_dir / "qcew"
        qcew_dir.mkdir(parents=True)
        (qcew_dir / "test.csv").write_text("header\ndata\n")

        # Set up LODES data
        lodes_dir = data_dir / "lodes"
        lodes_dir.mkdir(parents=True)
        (lodes_dir / "us_xwalk.csv").write_text("header\ndata\n")

        result = run_scenario_preflight("detroit", base_dir=tmp_path)

        # Overall fails (missing TIGER, Census CBSA)
        assert not result.ok

        # But some checks pass
        lodes_check = next((c for c in result.checks if c.check_id == "lodes:crosswalk"), None)
        assert lodes_check is not None
        assert lodes_check.status == "ok"

        # QCEW also passes
        qcew_check = next((c for c in result.checks if c.check_id == "qcew:files"), None)
        assert qcew_check is not None
        assert qcew_check.status == "ok"

        # TIGER fails
        tiger_check = next((c for c in result.checks if "tiger" in c.check_id), None)
        assert tiger_check is not None
        assert tiger_check.status == "fail"

    def test_detroit_all_data_present_passes_preflight(self, tmp_path: Path) -> None:
        """Story 1, Scenario 3: All data present passes silently."""
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True)

        # Set up all required data files

        # QCEW (checked via _check_qcew, needs CSV/XLSX files)
        qcew_dir = data_dir / "qcew"
        qcew_dir.mkdir(parents=True)
        (qcew_dir / "test.csv").write_text("header\ndata\n")

        # LODES crosswalk
        lodes_dir = data_dir / "lodes"
        lodes_dir.mkdir(parents=True)
        (lodes_dir / "us_xwalk.csv").write_text("header\ndata\n")

        # TIGER shapefile
        tiger_dir = data_dir / "tiger" / "county"
        tiger_dir.mkdir(parents=True)
        (tiger_dir / "tl_2024_us_county.shp").write_bytes(b"shapefile content")

        # Census CBSA file (must not be LFS pointer)
        census_dir = data_dir / "census"
        census_dir.mkdir(parents=True)
        (census_dir / "cbsa_delineation_2023.xlsx").write_bytes(b"valid xlsx content")

        result = run_scenario_preflight("detroit", base_dir=tmp_path)

        # No failures (may have warnings for optional items like API key)
        failures = [c for c in result.checks if c.status == "fail"]
        assert len(failures) == 0, f"Unexpected failures: {[c.check_id for c in failures]}"

        # Verify ok property
        assert result.ok

    @pytest.mark.skip(reason="Requires full Detroit data - run manually")
    def test_detroit_simulation_runs_after_preflight_passes(self) -> None:
        """SC-004: Zero crashes after preflight passes.

        This test requires actual Detroit data files and runs a simulation tick.
        Skip by default; run manually with real data.
        """
        from babylon.data.preflight import run_scenario_preflight
        from babylon.engine.scenarios import create_two_node_scenario
        from babylon.engine.simulation import Simulation

        # Preflight with real data
        result = run_scenario_preflight("detroit")
        assert result.ok, f"Preflight failed: {[c.message for c in result.failures]}"

        # Simulation should run first tick without FileNotFoundError
        initial_state, config, _defines = create_two_node_scenario()
        sim = Simulation(initial_state=initial_state, config=config)
        sim.step()  # Should not raise
        assert sim.current_state.tick == 1
