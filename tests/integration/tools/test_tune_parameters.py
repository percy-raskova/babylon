"""Integration tests for tune_parameters.py parameter sensitivity analysis tool.

Extracted from tests/unit/tools/test_tune_parameters.py.
These tests run actual simulations and are marked @pytest.mark.integration.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

from babylon.engine.headless_runner.runner import PostgresUnreachableError

pytestmark = pytest.mark.requires_postgres

# Path to the tune_parameters tool
TUNE_PARAMETERS_PATH = Path(__file__).parent.parent.parent.parent / "tools" / "tune_parameters.py"


def load_tune_parameters_module() -> Any:
    """Load the tune_parameters module dynamically.

    Returns:
        The loaded module object

    Raises:
        FileNotFoundError: If tune_parameters.py does not exist
    """
    if not TUNE_PARAMETERS_PATH.exists():
        pytest.skip(f"tune_parameters.py not found at {TUNE_PARAMETERS_PATH}")

    spec = importlib.util.spec_from_file_location("tune_parameters", TUNE_PARAMETERS_PATH)
    if spec is None or spec.loader is None:
        pytest.fail("Failed to load tune_parameters module spec")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestIntegration:
    """Integration tests that run actual simulations (slower)."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_actual_sweep_with_low_extraction(self) -> None:
        """Verify sweep runs actual simulation with low extraction values."""
        module = load_tune_parameters_module()

        # Run a minimal sweep with low extraction (should survive longer)
        try:
            results = module.run_sweep(
                "economy.extraction_efficiency",
                start=0.1,
                end=0.2,
                step=0.1,
            )
        except PostgresUnreachableError as exc:
            pytest.skip(str(exc))

        assert len(results) >= 2, "Expected at least 2 results"

        # With low extraction, periphery should survive longer
        low_extraction_result = results[0]  # 0.1
        assert low_extraction_result["ticks_survived"] > 0, (
            "Periphery should survive some ticks with low extraction"
        )

    @pytest.mark.integration
    @pytest.mark.slow
    def test_high_extraction_causes_earlier_death(self) -> None:
        """Verify high extraction causes death sooner than low extraction."""
        module = load_tune_parameters_module()

        try:
            results = module.run_sweep(
                "economy.extraction_efficiency",
                start=0.1,
                end=0.9,
                step=0.4,  # Test 0.1, 0.5, 0.9
            )
        except PostgresUnreachableError as exc:
            pytest.skip(str(exc))

        # Find results for low and high extraction
        low_result = next((r for r in results if r["value"] == 0.1), None)
        high_result = next((r for r in results if r["value"] == 0.9), None)

        assert low_result is not None, "Missing result for extraction=0.1"
        assert high_result is not None, "Missing result for extraction=0.9"

        # High extraction should cause death sooner (fewer ticks survived)
        assert low_result["ticks_survived"] >= high_result["ticks_survived"], (
            f"Low extraction ({low_result['ticks_survived']} ticks) should survive >= "
            f"high extraction ({high_result['ticks_survived']} ticks)"
        )
